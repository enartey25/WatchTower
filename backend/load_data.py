#!/usr/bin/env python3
"""
WatchTower — CSV → PostgreSQL loader (Simplified)
Reads tmdb_5000_movies.csv + tmdb_5000_credits.csv from ./data/
and populates the single `movies` table in schema.sql.
"""

import os
import sys
from datetime import datetime
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.gwxtzjirauflnkvcbkyj:redx309667!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres",
)
DATA_DIR = os.path.join(_BASE_DIR, "data")

MOVIES_CSV  = os.path.join(DATA_DIR, "tmdb_5000_movies.csv")
CREDITS_CSV = os.path.join(DATA_DIR, "tmdb_5000_credits.csv")

def safe_date(val):
    if not val or str(val).strip() in ("", "nan", "NaT"):
        return None
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None

def safe_int(val, default=0):
    try:
        v = int(val)
        return v if not pd.isna(val) else default
    except Exception:
        return default

def safe_float(val, default=0.0):
    try:
        v = float(val)
        return v if not pd.isna(val) else default
    except Exception:
        return default

def safe_str(val):
    s = str(val).strip() if val is not None else ""
    return None if s in ("nan", "NaT", "") else s

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def main():
    log("Connecting to database…")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    log("Reading tmdb_5000_movies.csv…")
    movies_df = pd.read_csv(MOVIES_CSV)
    log(f"  {len(movies_df)} rows")

    log("Reading tmdb_5000_credits.csv…")
    credits_df = pd.read_csv(CREDITS_CSV)
    log(f"  {len(credits_df)} rows")

    log("Merging datasets on id and movie_id…")
    # Merge movies and credits
    merged = pd.merge(movies_df, credits_df, left_on='id', right_on='movie_id', how='inner')
    log(f"  Merged size: {len(merged)} rows")

    # Clear existing rows
    log("Truncating movies table…")
    cur.execute("truncate table movies")

    log("Preparing rows for bulk insert…")
    insert_data = []
    for _, row in merged.iterrows():
        mid = safe_int(row["id"])
        if mid == 0:
            continue

        insert_data.append((
            mid,
            safe_str(row.get("title_x")) or safe_str(row.get("title_y")) or "",
            safe_str(row.get("original_title")) or "",
            safe_str(row.get("original_language")),
            safe_str(row.get("overview")),
            safe_str(row.get("tagline")),
            safe_date(row.get("release_date")),
            safe_str(row.get("status")),
            safe_str(row.get("homepage")),
            safe_int(row.get("budget")),
            safe_int(row.get("revenue")),
            safe_int(row.get("runtime")) or None,
            safe_float(row.get("popularity")),
            safe_float(row.get("vote_average")),
            safe_int(row.get("vote_count")),
            safe_str(row.get("genres")),
            safe_str(row.get("keywords")),
            safe_str(row.get("production_companies")),
            safe_str(row.get("production_countries")),
            safe_str(row.get("spoken_languages")),
            safe_str(row.get("cast")),
            safe_str(row.get("crew"))
        ))

    log(f"Inserting {len(insert_data)} movies to Supabase in chunks...")
    CHUNK_SIZE = 250
    for offset in range(0, len(insert_data), CHUNK_SIZE):
        chunk = insert_data[offset : offset + CHUNK_SIZE]
        log(f"  Inserting chunk {offset} to {offset + len(chunk)} / {len(insert_data)}...")
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
                popularity = excluded.popularity,
                vote_average = excluded.vote_average,
                vote_count = excluded.vote_count
        """, chunk)

    log("Database loading completed successfully!")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
