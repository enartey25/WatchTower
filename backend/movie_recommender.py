"""
WatchTower - TF-IDF Movie Recommender
Adapted from the original notebook version.
Data CSVs must be placed in the ./data/ directory.
"""

import os
import ast

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

pd.set_option('display.max_columns', 200)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


# ---------------------------------------------------------------------------
# Data loading & preprocessing
# ---------------------------------------------------------------------------

def load_and_preprocess_data():
    from dotenv import load_dotenv
    # Load env explicitly first so we have the DATABASE_URL
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

    # 1. Try loading from database if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    loaded_from_db = False

    if database_url:
        try:
            import psycopg2

            conn = psycopg2.connect(database_url)
            conn.autocommit = True

            # Set a longer statement timeout for the data-loading connection (5 minutes)
            cur = conn.cursor()
            cur.execute("SET statement_timeout = '300000'")
            cur.close()

            # Load in paginated chunks to avoid timeout on large datasets
            CHUNK = 2000
            df1_chunks, df2_chunks = [], []
            offset = 0
            while True:
                chunk = pd.read_sql_query(
                    f"SELECT id, original_title, title, original_language, overview, tagline, "
                    f"release_date, popularity, vote_average, vote_count, genres, keywords, "
                    f"production_companies, production_countries, spoken_languages "
                    f"FROM movies ORDER BY id LIMIT {CHUNK} OFFSET {offset}",
                    conn
                )
                if chunk.empty:
                    break
                df1_chunks.append(chunk)
                offset += CHUNK
            df1 = pd.concat(df1_chunks, ignore_index=True)

            offset = 0
            while True:
                chunk = pd.read_sql_query(
                    f"SELECT id as movie_id, title, cast_data as cast, crew "
                    f"FROM movies ORDER BY id LIMIT {CHUNK} OFFSET {offset}",
                    conn
                )
                if chunk.empty:
                    break
                df2_chunks.append(chunk)
                offset += CHUNK
            df2 = pd.concat(df2_chunks, ignore_index=True)

            conn.close()

            # Map release_date to release_year
            df1['release_date'] = pd.to_datetime(df1['release_date'], errors='coerce').dt.year
            loaded_from_db = True
            print(f"[WATCHTOWER] Successfully loaded {len(df1)} movies from Supabase database.")
        except Exception as exc:
            print(f"[WATCHTOWER] Database load failed: {exc}. Falling back to CSVs...")

    if not loaded_from_db:
        # Fallback to local CSV files
        df1 = pd.read_csv(os.path.join(DATA_DIR, 'tmdb_5000_movies.csv'))
        df2 = pd.read_csv(os.path.join(DATA_DIR, 'tmdb_5000_credits.csv'))
        df1 = df1.drop(['budget', 'homepage', 'revenue', 'runtime'], axis=1)
        df1['release_date'] = pd.to_datetime(df1['release_date'], errors='coerce').dt.year

    def extract_words(text):
        if pd.isna(text):
            return ''
        try:
            keywords = ast.literal_eval(text)
            return ' '.join([keyword['name'] for keyword in keywords])
        except (ValueError, SyntaxError):
            return ''

    df1['keywords']             = df1['keywords'].apply(extract_words)
    df1['genres']               = df1['genres'].apply(extract_words)
    df1['production_companies'] = df1['production_companies'].apply(extract_words)
    df1['production_countries'] = df1['production_countries'].apply(extract_words)
    df1['spoken_languages']     = df1['spoken_languages'].apply(extract_words)

    def extract_characters(text):
        if pd.isna(text):
            return ''
        try:
            character = ast.literal_eval(text)
            return ' '.join(char['character'] for char in character[:5])
        except (ValueError, SyntaxError):
            return ''

    def extract_actors(text):
        if pd.isna(text):
            return ''
        try:
            actor = ast.literal_eval(text)
            return ' '.join(act['name'] for act in actor[:5])
        except (ValueError, SyntaxError):
            return ''

    def extract_names(text):
        if pd.isna(text):
            return ''
        try:
            name = ast.literal_eval(text)
            return ' '.join(n['name'] for n in name[:5])
        except (ValueError, SyntaxError):
            return ''

    df2['character'] = df2['cast'].apply(extract_characters)
    df2['actor']     = df2['cast'].apply(extract_actors)
    df2['crew']      = df2['crew'].apply(extract_names)

    df = pd.merge(df1, df2, left_on='id', right_on='movie_id', how='left').drop(['id'], axis=1)

    def combine_titles(row):
        titles = [str(row['original_title']), str(row['title_x']), str(row['title_y'])]
        return ' '.join(dict.fromkeys(t for t in titles if t != 'nan'))

    df['all_titles'] = df.apply(combine_titles, axis=1)

    df['tags'] = (
        df['all_titles'] + " " +
        df['all_titles'] + " " +
        df['all_titles'] + " " +
        df['genres'] + " " +
        df['genres'] + " " +
        df['genres'] + " " +
        df['character'] + " " +
        df['character'] + " " +
        df['actor'] + " " +
        df['actor'] + " " +
        df['keywords'] + " " +
        df['keywords'] +
        df['overview'].fillna('') + " " +
        df['tagline'].fillna('')
    )
    df['tags'] = df['tags'].fillna('')

    return df


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

def train_tfidf_and_similarity(df):
    """
    Build and return only the TF-IDF vectorizer and sparse matrix.
    The full N×N cosine-similarity matrix is NOT precomputed — it costs
    ~200 MB per worker for 5 000 movies and causes OOM on free-tier hosts.
    Per-query row similarity is computed on-demand in _compute_scores.
    """
    tfidf        = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['tags'])
    return tfidf, tfidf_matrix, None   # third value kept for API compatibility


# ---------------------------------------------------------------------------
# Core scoring logic (shared between CLI and API)
# ---------------------------------------------------------------------------

def _compute_scores(query, df, tfidf, tfidf_matrix, _similarity_unused):
    """
    Returns (top_idx, sim_scores, final_scores, match_indices).
    top_idx is a list of up to 12 integer row positions.

    Similarity is computed on-demand from the sparse tfidf_matrix using
    efficient dot-product slices — no precomputed N×N matrix is needed.
    """
    query_lower = query.lower()
    matches = df[df['tags'].str.lower().str.contains(query_lower, na=False)]

    if not matches.empty:
        match_indices = [df.index.get_loc(i) for i in matches.index[:15]]

        # Compute similarity only for matched rows (sparse → dense slice)
        candidate_scores = np.zeros(len(df))
        for match_idx in match_indices:
            row_vec = tfidf_matrix[match_idx]           # (1, vocab) sparse
            candidate_scores += cosine_similarity(row_vec, tfidf_matrix)[0]
        sim_scores = candidate_scores / len(match_indices)

        target_genres = set()
        for i in match_indices:
            genres = df.iloc[i]['genres']
            if isinstance(genres, str):
                target_genres.update(genres.split(', '))

    else:
        match_indices = []
        query_vector = tfidf.transform([query])
        sim_scores   = cosine_similarity(query_vector, tfidf_matrix)[0]
        idx          = int(np.argmax(sim_scores))

        genres = df.iloc[idx]['genres']
        target_genres = set(genres.split(', ')) if isinstance(genres, str) else set()

    all_genres = df['genres'].fillna('').str.split(', ')
    genre_scores = all_genres.apply(
        lambda g: len(target_genres.intersection(g)) / len(target_genres)
        if len(target_genres) > 0 else 0
    ).values

    ratings    = df['vote_average'].fillna(0).values / 10
    popularity = df['popularity'].fillna(0).values / df['popularity'].max()

    final_scores = (
        0.60 * sim_scores +
        0.30 * genre_scores +
        0.05 * ratings +
        0.05 * popularity
    )

    top_idx = np.argsort(final_scores)[::-1]

    if match_indices:
        top_idx = [i for i in top_idx if i not in match_indices][:30]
    else:
        fallback_idx = int(np.argmax(sim_scores))
        top_idx = [i for i in top_idx if i != fallback_idx][:30]

    return top_idx, sim_scores, final_scores, match_indices


# ---------------------------------------------------------------------------
# API-facing function (returns structured dicts)
# ---------------------------------------------------------------------------

def recommend_structured(query, df, tfidf, tfidf_matrix, similarity, serialize_fn):
    """
    Returns both direct matches and recommendations, mirroring the original
    notebook behaviour which prints both sections separately.
    """
    top_idx, sim_scores, final_scores, match_indices = _compute_scores(
        query, df, tfidf, tfidf_matrix, similarity
    )

    matches = [
        serialize_fn(df.iloc[i], final_score=final_scores[i], similarity_score=sim_scores[i])
        for i in match_indices
    ]

    recommendations = [
        serialize_fn(df.iloc[i], final_score=final_scores[i], similarity_score=sim_scores[i])
        for i in top_idx
    ]

    return matches, recommendations


# ---------------------------------------------------------------------------
# CLI-facing function (prints results)
# ---------------------------------------------------------------------------

def recommend(query, df, tfidf, tfidf_matrix, similarity):
    """Original CLI recommendation function with print output."""
    top_idx, sim_scores, final_scores, match_indices = _compute_scores(
        query, df, tfidf, tfidf_matrix, similarity
    )

    if match_indices:
        print("Found direct matches:")
        for i in match_indices:
            print(" -", df.iloc[i]['original_title'])

    print(f"\nRecommendations for '{query}':")
    for i in top_idx:
        print(
            df.iloc[i]['original_title'],
            "->", round(final_scores[i], 3),
            "| Similarity:", round(sim_scores[i], 3),
            "| Rating:", df.iloc[i]['vote_average'],
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("Loading dataset...")
    movie_df = load_and_preprocess_data()
    print(f"{len(movie_df)} movies loaded.")
    print("Training TF-IDF model...")
    tfidf_vectorizer, tfidf_matrix_data, cosine_sim = train_tfidf_and_similarity(movie_df)
    print("Ready.\n")

    while True:
        query_movie = input("What movie are you looking for? (exit to quit): ")
        if query_movie.lower() == 'exit':
            break
        recommend(query_movie, movie_df, tfidf_vectorizer, tfidf_matrix_data, cosine_sim)
