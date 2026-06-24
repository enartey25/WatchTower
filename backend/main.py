"""
WatchTower FastAPI Backend
Run with: uvicorn main:app --reload --port 8000
"""

import os
import json
import time
import threading
import concurrent.futures
from typing import Optional

import requests as http_requests
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from movie_recommender import (
    load_and_preprocess_data,
    train_tfidf_and_similarity,
    recommend_structured,
)

# Load .env from the same directory as this file (reliable regardless of CWD)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(_BASE_DIR, ".env"))

app = FastAPI(
    title="WatchTower API",
    description="TF-IDF Movie Recommendation Engine",
    version="1.0.0",
)

# Read allowed origins from env — supports both dev and production
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
)
ALLOWED_ORIGINS_LIST = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Supabase client (optional — gracefully disabled if keys not set)
# ---------------------------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

_supabase = None
if SUPABASE_URL and SUPABASE_KEY and "your-project-ref" not in SUPABASE_URL:
    try:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[WATCHTOWER] Supabase connected — watchlist persistence enabled.")
    except Exception as _sb_err:
        print(f"[WATCHTOWER] Supabase init failed: {_sb_err} — watchlist will be in-memory only.")
else:
    print("[WATCHTOWER] No Supabase credentials — watchlist endpoints disabled.")

# ---------------------------------------------------------------------------
# Persistent poster cache (JSON, 24-hour TTL)
# ---------------------------------------------------------------------------

OMDB_API_KEY  = os.getenv("OMDB_API_KEY", "")
OMDB_BASE_URL = "http://www.omdbapi.com/"
CACHE_FILE    = os.path.join(_BASE_DIR, "data", "poster_cache.json")
CACHE_TTL     = 86_400          # 24 hours in seconds
CACHE_LOCK    = threading.Lock()

# Format stored per entry: { "url": "https://..." | null, "ts": <unix timestamp> }


def _load_cache() -> dict:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict) -> None:
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except Exception as exc:
        print(f"[WATCHTOWER] Warning: could not save poster cache — {exc}")


POSTER_CACHE: dict = _load_cache()
print(f"[WATCHTOWER] Loaded {len(POSTER_CACHE)} cached poster entries from disk.")


def _omdb_request(title: str, year=None) -> str | None:
    """Single OMDB HTTP request. Returns poster URL or None."""
    params = {"apikey": OMDB_API_KEY, "t": title}
    if year:
        params["y"] = year
    resp = http_requests.get(OMDB_BASE_URL, params=params, timeout=6)
    resp.raise_for_status()
    data = resp.json()
    poster = data.get("Poster", "")
    return poster if (poster and poster != "N/A") else None


def fetch_poster(title: str, year=None) -> str | None:
    """
    Return a poster URL for the given movie title.
    Strategy:
      1. Try title + year
      2. If nothing found, retry with title only (OMDB is strict about years)
    Hits are cached for 24 hours. Failures are cached for 1 hour only so
    transient errors (wrong year, network blip) are retried quickly.
    """
    if not OMDB_API_KEY or OMDB_API_KEY == "your_key_here":
        return None

    cache_key = f"{title}|{year}"
    HIT_TTL  = CACHE_TTL   # 24 hours for real posters
    MISS_TTL = 3_600        # 1 hour for nulls — retry sooner

    with CACHE_LOCK:
        entry = POSTER_CACHE.get(cache_key)
        if entry is not None:
            age = time.time() - entry.get("ts", 0)
            ttl = HIT_TTL if entry.get("url") else MISS_TTL
            if age < ttl:
                return entry.get("url")          # still fresh

    # Fetch from OMDB
    url = None
    try:
        url = _omdb_request(title, year)
        # If year-specific lookup returned nothing, retry without year
        if url is None and year:
            url = _omdb_request(title, None)
    except Exception as exc:
        print(f"[WATCHTOWER] Poster fetch failed for '{title}': {exc}")

    new_entry = {"url": url, "ts": time.time()}

    with CACHE_LOCK:
        POSTER_CACHE[cache_key] = new_entry
        cache_snapshot = dict(POSTER_CACHE)

    threading.Thread(target=_save_cache, args=(cache_snapshot,), daemon=True).start()

    return url


def enrich_with_posters(movies: list[dict]) -> list[dict]:
    """Fetch posters for a batch of movies in parallel."""
    if not OMDB_API_KEY or OMDB_API_KEY == "your_key_here":
        for m in movies:
            m["poster_url"] = None
        return movies

    def _fetch(movie):
        return fetch_poster(movie["title"], movie.get("release_year"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(_fetch, m): i for i, m in enumerate(movies)}
        for future, idx in futures.items():
            try:
                movies[idx]["poster_url"] = future.result(timeout=8)
            except Exception:
                movies[idx]["poster_url"] = None

    return movies


# Posters are fetched on-demand (when trending/search endpoints are hit)
# and cached to disk — no startup pre-fetch needed.


# ---------------------------------------------------------------------------
# Global model state
# ---------------------------------------------------------------------------

movie_df          = None
tfidf_vectorizer  = None
tfidf_matrix_data = None
cosine_sim        = None


@app.on_event("startup")
async def startup_event():
    global movie_df, tfidf_vectorizer, tfidf_matrix_data, cosine_sim

    print("[WATCHTOWER] Loading dataset...")
    movie_df = load_and_preprocess_data()
    print(f"[WATCHTOWER] {len(movie_df)} movies loaded.")

    print("[WATCHTOWER] Training TF-IDF model (this may take a moment)...")
    tfidf_vectorizer, tfidf_matrix_data, cosine_sim = train_tfidf_and_similarity(movie_df)
    print("[WATCHTOWER] Model ready.")

    if OMDB_API_KEY and OMDB_API_KEY != "your_key_here":
        print("[WATCHTOWER] OMDB key detected — posters enabled (fetched on demand, cached 24h).")
    else:
        print("[WATCHTOWER] No OMDB key in .env — gradient fallback active.")
        print("[WATCHTOWER] Get a free key at https://www.omdbapi.com/apikey.aspx")


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------

def serialize_movie(row, final_score=None, similarity_score=None) -> dict:
    genres_raw  = str(row.get("genres", ""))
    genres_list = [g for g in genres_raw.split(" ") if g.strip()]

    release = row.get("release_date")
    try:
        release_year = int(release) if pd.notna(release) else None
    except (ValueError, TypeError):
        release_year = None

    def safe_str(val):
        s = str(val) if val is not None else ""
        return "" if s == "nan" else s

    return {
        "title":            safe_str(row.get("original_title", "")),
        "overview":         safe_str(row.get("overview", "")),
        "genres":           genres_list,
        "vote_average":     round(float(row.get("vote_average", 0) or 0), 1),
        "vote_count":       int(row.get("vote_count", 0) or 0),
        "popularity":       round(float(row.get("popularity", 0) or 0), 2),
        "release_year":     release_year,
        "tagline":          safe_str(row.get("tagline", "")),
        "final_score":      round(float(final_score), 3) if final_score is not None else None,
        "similarity_score": round(float(similarity_score), 3) if similarity_score is not None else None,
        "poster_url":       None,    # filled by enrich_with_posters()
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class RecommendRequest(BaseModel):
    query: str


class WatchlistAddRequest(BaseModel):
    user_id: str
    movie: dict


@app.get("/api/health")
def health_check():
    return {
        "status":          "ok",
        "movies_loaded":   len(movie_df) if movie_df is not None else 0,
        "model_ready":     tfidf_vectorizer is not None,
        "posters_enabled": bool(OMDB_API_KEY and OMDB_API_KEY != "your_key_here"),
        "cache_entries":   len(POSTER_CACHE),
    }


@app.get("/api/poster-test")
def poster_test(title: str = "Inception", year: int = None):
    """Quick diagnostic: fetch a single poster and return the result."""
    if not OMDB_API_KEY or OMDB_API_KEY == "your_key_here":
        return {"error": "OMDB_API_KEY not set in backend/.env"}
    url = fetch_poster(title, year)
    return {"title": title, "poster_url": url, "found": url is not None}


@app.post("/api/recommend")
def get_recommendations(req: RecommendRequest):
    if movie_df is None or tfidf_vectorizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet. Please wait.")

    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    matches, recommendations = recommend_structured(
        query, movie_df, tfidf_vectorizer, tfidf_matrix_data, cosine_sim, serialize_movie,
    )

    all_movies = matches + recommendations
    enrich_with_posters(all_movies)

    return {
        "query":           query,
        "matches":         all_movies[:len(matches)],
        "recommendations": all_movies[len(matches):],
    }


@app.get("/api/trending")
def get_trending(limit: int = Query(default=20, ge=1, le=50)):
    if movie_df is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet.")
    top    = movie_df.nlargest(limit, "popularity")
    movies = [serialize_movie(row) for _, row in top.iterrows()]
    enrich_with_posters(movies)
    return {"results": movies}


@app.get("/api/top-rated")
def get_top_rated(limit: int = Query(default=20, ge=1, le=50)):
    if movie_df is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet.")
    filtered = movie_df[movie_df["vote_count"] >= 100]
    top      = filtered.nlargest(limit, "vote_average")
    movies   = [serialize_movie(row) for _, row in top.iterrows()]
    enrich_with_posters(movies)
    return {"results": movies}


# ---------------------------------------------------------------------------
# Watchlist routes (Supabase-backed)
#
# Run this SQL in your Supabase SQL editor to create the table:
#
#   create table watchlist (
#     id          uuid primary key default gen_random_uuid(),
#     user_id     text not null,
#     movie_title text not null,
#     movie       jsonb not null,
#     saved_at    timestamptz default now(),
#     unique (user_id, movie_title)
#   );
#
#   -- Enable Row Level Security and allow all (anonymous demo mode):
#   alter table watchlist enable row level security;
#   create policy "allow_all" on watchlist for all using (true) with check (true);
# ---------------------------------------------------------------------------


@app.get("/api/watchlist")
def get_watchlist(user_id: str = Query(..., description="Anonymous device UUID")):
    """Fetch a user's watchlist from Supabase."""
    if _supabase is None:
        return {"watchlist": [], "supabase_enabled": False}
    try:
        result = (
            _supabase.table("watchlist")
            .select("movie, saved_at")
            .eq("user_id", user_id)
            .order("saved_at", desc=True)
            .execute()
        )
        return {"watchlist": result.data, "supabase_enabled": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase error: {e}")


@app.post("/api/watchlist")
def add_to_watchlist(req: WatchlistAddRequest):
    """Add a movie to the user's watchlist."""
    if _supabase is None:
        raise HTTPException(status_code=503, detail="Supabase not configured.")
    try:
        _supabase.table("watchlist").upsert(
            {
                "user_id":     req.user_id,
                "movie_title": req.movie.get("title", ""),
                "movie":       req.movie,
            },
            on_conflict="user_id,movie_title",
        ).execute()
        return {"status": "added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase error: {e}")


@app.delete("/api/watchlist/{movie_title}")
def remove_from_watchlist(
    movie_title: str,
    user_id: str = Query(..., description="Anonymous device UUID"),
):
    """Remove a movie from the user's watchlist."""
    if _supabase is None:
        raise HTTPException(status_code=503, detail="Supabase not configured.")
    try:
        _supabase.table("watchlist").delete().eq("user_id", user_id).eq(
            "movie_title", movie_title
        ).execute()
        return {"status": "removed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase error: {e}")
