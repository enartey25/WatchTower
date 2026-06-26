from movie_recommender import load_and_preprocess_data, train_tfidf_and_similarity, _compute_scores

df = load_and_preprocess_data()
tfidf, matrix, _ = train_tfidf_and_similarity(df)
print("Total movies loaded:", len(df))

for query in ["Spider-Man", "Marvel", "Love", "Action"]:
    top_idx, sim, final, matches = _compute_scores(query, df, tfidf, matrix, None)
    recs_preview = [df.iloc[i]["original_title"] for i in top_idx[:5]]
    print(f"Query [{query}]: {len(matches)} direct matches, {len(top_idx)} recommendations")
    print("  Top 5 recs:", recs_preview)
