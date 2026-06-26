#!/usr/bin/env python3
"""
WatchTower — TMDB API Movie Fetcher & Database Synchronizer
Discovers popular movies from 2017 to 2026, fetches their details (genres, keywords, cast, crew),
and inserts/upserts them to the Supabase PostgreSQL database, and appends them to local fallback CSV files.
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import requests
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.gwxtzjirauflnkvcbkyj:redx309667!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
)
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
DATA_DIR = os.path.join(_BASE_DIR, "data")
MOVIES_CSV = os.path.join(DATA_DIR, "tmdb_5000_movies.csv")
CREDITS_CSV = os.path.join(DATA_DIR, "tmdb_5000_credits.csv")

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def safe_str(val):
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("nan", "nat") else s

def safe_int(val, default=0):
    try:
        if pd.isna(val) or val is None:
            return default
        return int(val)
    except Exception:
        return default

def safe_float(val, default=0.0):
    try:
        if pd.isna(val) or val is None:
            return default
        return float(val)
    except Exception:
        return default

def fetch_movie_ids_for_year(api_key, year, limit=50):
    """
    Discover the most popular movie IDs for a specific year.
    Each discover page returns 20 movies.
    """
    movie_ids = []
    page = 1
    max_pages = (limit + 19) // 20  # Ceil division to get required pages

    while len(movie_ids) < limit and page <= max_pages:
        url = f"https://api.themoviedb.org/3/discover/movie"
        params = {
            "api_key": api_key,
            "primary_release_year": year,
            "sort_by": "popularity.desc",
            "page": page,
            "include_adult": "false"
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if not results:
                break
            for movie in results:
                if movie.get("id"):
                    movie_ids.append(movie["id"])
                    if len(movie_ids) >= limit:
                        break
            page += 1
        except Exception as e:
            log(f"Error discovering movies for year {year} page {page}: {e}")
            break
        time.sleep(0.1)  # Respect rate limits

    return movie_ids[:limit]

def fetch_movie_details(api_key, movie_id):
    """
    Fetch full movie details, credits, and keywords in one API call.
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {
        "api_key": api_key,
        "append_to_response": "keywords,credits"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log(f"Error fetching movie details for ID {movie_id}: {e}")
        return None

def process_movie_response(data):
    """
    Process raw TMDB API response into DB and CSV schema-compatible dict.
    """
    # 1. Basic properties
    mid = safe_int(data.get("id"))
    if mid == 0:
        return None

    # 2. Extract keywords, genres, production, spoken languages
    genres = [{"id": g.get("id"), "name": g.get("name")} for g in data.get("genres", []) if g.get("name")]
    keywords = [{"id": k.get("id"), "name": k.get("name")} for k in data.get("keywords", {}).get("keywords", []) if k.get("name")]
    
    prod_companies = [{"name": pc.get("name"), "id": pc.get("id")} for pc in data.get("production_companies", []) if pc.get("name")]
    prod_countries = [{"iso_3166_1": pc.get("iso_3166_1"), "name": pc.get("name")} for pc in data.get("production_countries", []) if pc.get("name")]
    
    spoken_languages = [{"iso_639_1": sl.get("iso_639_1"), "name": sl.get("name")} for sl in data.get("spoken_languages", []) if sl.get("name")]

    # 3. Clean cast and crew to match TMDB CSV columns
    raw_cast = data.get("credits", {}).get("cast", [])
    clean_cast = []
    for c in raw_cast:
        clean_cast.append({
            "cast_id": safe_int(c.get("cast_id")),
            "character": safe_str(c.get("character")),
            "credit_id": safe_str(c.get("credit_id")),
            "gender": safe_int(c.get("gender")),
            "id": safe_int(c.get("id")),
            "name": safe_str(c.get("name")),
            "order": safe_int(c.get("order"))
        })

    raw_crew = data.get("credits", {}).get("crew", [])
    clean_crew = []
    for c in raw_crew:
        clean_crew.append({
            "credit_id": safe_str(c.get("credit_id")),
            "department": safe_str(c.get("department")),
            "gender": safe_int(c.get("gender")),
            "id": safe_int(c.get("id")),
            "job": safe_str(c.get("job")),
            "name": safe_str(c.get("name"))
        })

    # Return standard fields mapped to postgres & CSV schema
    return {
        # Movies table / tmdb_5000_movies.csv columns
        "id": mid,
        "title": safe_str(data.get("title")),
        "original_title": safe_str(data.get("original_title")),
        "original_language": safe_str(data.get("original_language")),
        "overview": safe_str(data.get("overview")),
        "tagline": safe_str(data.get("tagline")),
        "release_date": safe_str(data.get("release_date")) or None,
        "status": safe_str(data.get("status")),
        "homepage": safe_str(data.get("homepage")),
        "budget": safe_int(data.get("budget")),
        "revenue": safe_int(data.get("revenue")),
        "runtime": safe_int(data.get("runtime")) or None,
        "popularity": safe_float(data.get("popularity")),
        "vote_average": safe_float(data.get("vote_average")),
        "vote_count": safe_int(data.get("vote_count")),
        
        # Stored as string representation of lists of dicts
        "genres": str(genres),
        "keywords": str(keywords),
        "production_companies": str(prod_companies),
        "production_countries": str(prod_countries),
        "spoken_languages": str(spoken_languages),
        
        # Credits columns
        "cast": str(clean_cast),
        "crew": str(clean_crew)
    }

def main():
    parser = argparse.ArgumentParser(description="Fetch recent popular movies from TMDB API.")
    parser.add_argument("--limit-per-year", type=int, default=50, help="Number of popular movies to fetch per year (default: 50)")
    parser.add_argument("--start-year", type=int, default=2017, help="Start year (default: 2017)")
    parser.add_argument("--end-year", type=int, default=2026, help="End year (default: 2026)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch data but do not write to DB or CSVs")
    args = parser.parse_args()

    # Verify TMDB Key
    if not TMDB_API_KEY or TMDB_API_KEY == "your_tmdb_key_here":
        log("ERROR: TMDB_API_KEY is not set in backend/.env!")
        log("Please register for a free key at https://www.themoviedb.org/ and put it in .env.")
        sys.exit(1)

    log(f"TMDB Ingestion started for years {args.start_year} to {args.end_year}...")
    log(f"Limit: {args.limit_per_year} popular movies per year.")

    # 1. Discover all movie IDs
    all_movie_ids = []
    for year in range(args.start_year, args.end_year + 1):
        log(f"Discovering top {args.limit_per_year} movies for year {year}...")
        ids = fetch_movie_ids_for_year(TMDB_API_KEY, year, args.limit_per_year)
        log(f"  Found {len(ids)} movie IDs.")
        all_movie_ids.extend(ids)

    # Remove potential duplicates
    all_movie_ids = list(set(all_movie_ids))
    log(f"Total unique movies to fetch: {len(all_movie_ids)}")

    if not all_movie_ids:
        log("No movies found to fetch. Exiting.")
        sys.exit(0)

    # 2. Fetch all movie details in parallel
    processed_movies = []
    log(f"Fetching movie details using a ThreadPoolExecutor (max_workers=10)...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_movie_details, TMDB_API_KEY, mid): mid for mid in all_movie_ids}
        completed_count = 0
        for future in as_completed(futures):
            mid = futures[future]
            completed_count += 1
            if completed_count % 50 == 0 or completed_count == len(all_movie_ids):
                log(f"  Progress: {completed_count}/{len(all_movie_ids)} fetched...")
            try:
                data = future.result()
                if data:
                    processed = process_movie_response(data)
                    if processed:
                        processed_movies.append(processed)
            except Exception as e:
                log(f"Exception fetching movie details for ID {mid}: {e}")

    log(f"Successfully fetched and processed {len(processed_movies)} movies.")

    if args.dry_run:
        log("DRY-RUN enabled. Exiting without writing to database or CSV files.")
        if processed_movies:
            log(f"Sample movie processed: {processed_movies[0]['title']} ({processed_movies[0]['release_date']})")
        sys.exit(0)

    # 3. Write to PostgreSQL (Supabase)
    if processed_movies:
        log("Connecting to Supabase PostgreSQL database...")
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = True
            cur = conn.cursor()

            log(f"Upserting {len(processed_movies)} movies to database...")
            
            insert_data = []
            for m in processed_movies:
                # Convert release date string to Python date object safely
                rdate = None
                if m["release_date"]:
                    try:
                        rdate = datetime.strptime(m["release_date"], "%Y-%m-%d").date()
                    except ValueError:
                        pass

                insert_data.append((
                    m["id"],
                    m["title"],
                    m["original_title"],
                    m["original_language"],
                    m["overview"],
                    m["tagline"],
                    rdate,
                    m["status"],
                    m["homepage"],
                    m["budget"],
                    m["revenue"],
                    m["runtime"],
                    m["popularity"],
                    m["vote_average"],
                    m["vote_count"],
                    m["genres"],
                    m["keywords"],
                    m["production_companies"],
                    m["production_countries"],
                    m["spoken_languages"],
                    m["cast"],
                    m["crew"]
                ))

            # execute_values runs a highly optimized bulk insert
            execute_values(cur, """
                insert into movies (
                    id, title, original_title, original_language, overview, tagline,
                    release_date, status, homepage, budget, revenue, runtime,
                    popularity, vote_average, vote_count, genres, keywords,
                    production_companies, production_countries, spoken_languages,
                    cast_data, crew
                ) values %s
                on conflict (id) do update set
                    title = excluded.title,
                    original_title = excluded.original_title,
                    overview = excluded.overview,
                    tagline = excluded.tagline,
                    release_date = excluded.release_date,
                    status = excluded.status,
                    homepage = excluded.homepage,
                    budget = excluded.budget,
                    revenue = excluded.revenue,
                    runtime = excluded.runtime,
                    popularity = excluded.popularity,
                    vote_average = excluded.vote_average,
                    vote_count = excluded.vote_count,
                    genres = excluded.genres,
                    keywords = excluded.keywords,
                    production_companies = excluded.production_companies,
                    production_countries = excluded.production_countries,
                    spoken_languages = excluded.spoken_languages,
                    cast_data = excluded.cast_data,
                    crew = excluded.crew
            """, insert_data)

            log("Supabase database load completed successfully!")
            cur.close()
            conn.close()
        except Exception as db_err:
            log(f"ERROR: Database upload failed: {db_err}")

    # 4. Append to local fallback CSV files
    if processed_movies:
        log("Updating local fallback CSV files...")
        try:
            # Load current CSV files
            if os.path.exists(MOVIES_CSV):
                movies_df = pd.read_csv(MOVIES_CSV)
            else:
                movies_df = pd.DataFrame(columns=[
                    'budget', 'genres', 'homepage', 'id', 'keywords', 'original_language',
                    'original_title', 'overview', 'popularity', 'production_companies',
                    'production_countries', 'release_date', 'revenue', 'runtime',
                    'spoken_languages', 'status', 'tagline', 'title', 'vote_average', 'vote_count'
                ])

            if os.path.exists(CREDITS_CSV):
                credits_df = pd.read_csv(CREDITS_CSV)
            else:
                credits_df = pd.DataFrame(columns=['movie_id', 'title', 'cast', 'crew'])

            log(f"Current local CSV movies count: {len(movies_df)}")
            log(f"Current local CSV credits count: {len(credits_df)}")

            movies_to_append = []
            credits_to_append = []

            existing_movie_ids = set(movies_df["id"].values)
            existing_credit_ids = set(credits_df["movie_id"].values)

            for m in processed_movies:
                # Add to movies_df list if not existing
                if m["id"] not in existing_movie_ids:
                    movies_to_append.append({
                        "budget": m["budget"],
                        "genres": m["genres"],
                        "homepage": m["homepage"],
                        "id": m["id"],
                        "keywords": m["keywords"],
                        "original_language": m["original_language"],
                        "original_title": m["original_title"],
                        "overview": m["overview"],
                        "popularity": m["popularity"],
                        "production_companies": m["production_companies"],
                        "production_countries": m["production_countries"],
                        "release_date": m["release_date"],
                        "revenue": m["revenue"],
                        "runtime": m["runtime"],
                        "spoken_languages": m["spoken_languages"],
                        "status": m["status"],
                        "tagline": m["tagline"],
                        "title": m["title"],
                        "vote_average": m["vote_average"],
                        "vote_count": m["vote_count"]
                    })

                # Add to credits_df list if not existing
                if m["id"] not in existing_credit_ids:
                    credits_to_append.append({
                        "movie_id": m["id"],
                        "title": m["title"],
                        "cast": m["cast"],
                        "crew": m["crew"]
                    })

            if movies_to_append:
                new_movies_df = pd.DataFrame(movies_to_append)
                movies_df = pd.concat([movies_df, new_movies_df], ignore_index=True)
                movies_df.to_csv(MOVIES_CSV, index=False)
                log(f"Appended {len(movies_to_append)} new records to {os.path.basename(MOVIES_CSV)}.")
            else:
                log(f"No new records to append to {os.path.basename(MOVIES_CSV)}.")

            if credits_to_append:
                new_credits_df = pd.DataFrame(credits_to_append)
                credits_df = pd.concat([credits_df, new_credits_df], ignore_index=True)
                credits_df.to_csv(CREDITS_CSV, index=False)
                log(f"Appended {len(credits_to_append)} new records to {os.path.basename(CREDITS_CSV)}.")
            else:
                log(f"No new records to append to {os.path.basename(CREDITS_CSV)}.")

            log(f"Updated CSV movies count: {len(movies_df)}")
            log(f"Updated CSV credits count: {len(credits_df)}")

        except Exception as csv_err:
            log(f"ERROR: Appending to local CSV files failed: {csv_err}")

    log("Completed successfully!")

if __name__ == "__main__":
    main()
