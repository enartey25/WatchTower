import { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import MovieCard from '../components/MovieCard';
import MovieModal from '../components/MovieModal';
import { getRecommendations } from '../lib/api';

function IconSearch() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function IconEmpty() {
  return (
    <svg className="state-container__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  );
}

function IconError() {
  return (
    <svg className="state-container__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

export default function SearchPage() {
  const [searchParams]               = useSearchParams();
  const navigate                     = useNavigate();
  const query                        = searchParams.get('q') || '';

  const [localQuery,   setLocalQuery]   = useState(query);
  const [matches,      setMatches]      = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState(null);
  const [selectedMovie, setSelected]   = useState(null);

  const prevQuery = useRef('');

  useEffect(() => {
    setLocalQuery(query);

    if (!query || query === prevQuery.current) return;
    prevQuery.current = query;

    setLoading(true);
    setError(null);
    setMatches([]);
    setRecommendations([]);

    getRecommendations(query)
      .then((data) => {
        setMatches(data.matches || []);
        setRecommendations(data.recommendations || []);
      })
      .catch((err) => {
        const detail = err.response?.data?.detail;
        setError(detail || 'Could not connect to the backend. Make sure the FastAPI server is running on port 8000.');
      })
      .finally(() => setLoading(false));
  }, [query]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (localQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(localQuery.trim())}`);
    }
  };

  const hasResults = matches.length > 0 || recommendations.length > 0;

  return (
    <div className="search-page">
      <div className="search-page__header">
        <p className="search-page__eyebrow">TF-IDF Recommendations</p>
        <h1 className="search-page__title">
          Results for <span>"{query}"</span>
        </h1>
        {!loading && !error && hasResults && (
          <p className="search-page__count">
            {matches.length > 0 && `${matches.length} direct match${matches.length !== 1 ? 'es' : ''}`}
            {matches.length > 0 && recommendations.length > 0 && '  —  '}
            {recommendations.length > 0 && `${recommendations.length} recommendations`}
          </p>
        )}

        {/* Inline refine search */}
        <form className="search-page__searchbar" onSubmit={handleSearch} style={{ marginTop: 20 }}>
          <IconSearch />
          <input
            type="text"
            placeholder="Refine your search..."
            value={localQuery}
            onChange={(e) => setLocalQuery(e.target.value)}
            autoComplete="off"
          />
          <button type="submit">Search</button>
        </form>
      </div>

      {/* Loading skeletons */}
      {loading && (
        <>
          <div className="search-page__section-label">Direct Matches</div>
          <div className="search-grid">
            {Array.from({ length: 15 }).map((_, i) => (
              <div key={i}>
                <div className="skeleton skeleton-card" />
                <div className="skeleton skeleton-label" style={{ width: '72%' }} />
                <div className="skeleton skeleton-label" style={{ width: '50%', marginTop: 5 }} />
              </div>
            ))}
          </div>
          <div className="search-page__section-label" style={{ marginTop: 40 }}>Recommendations</div>
          <div className="search-grid">
            {Array.from({ length: 30 }).map((_, i) => (
              <div key={i}>
                <div className="skeleton skeleton-card" />
                <div className="skeleton skeleton-label" style={{ width: '72%' }} />
                <div className="skeleton skeleton-label" style={{ width: '50%', marginTop: 5 }} />
              </div>
            ))}
          </div>
        </>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="state-container">
          <IconError />
          <p className="state-container__title">Could Not Load Results</p>
          <p className="state-container__text">{error}</p>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && !hasResults && query && (
        <div className="state-container">
          <IconEmpty />
          <p className="state-container__title">No Results Found</p>
          <p className="state-container__text">
            Try a different title, actor name, or genre to find matches.
          </p>
          <Link to="/" className="btn btn--primary" style={{ marginTop: 28 }}>
            Back to Home
          </Link>
        </div>
      )}

      {/* Direct matches section */}
      {!loading && matches.length > 0 && (
        <>
          <div className="search-page__section-label">
            Direct Matches
            <span className="search-page__section-badge">{matches.length}</span>
          </div>
          <div className="search-grid search-grid--matches">
            {matches.map((movie, i) => (
              <MovieCard
                key={`match-${movie.title}-${i}`}
                movie={movie}
                onClick={setSelected}
                gridMode
              />
            ))}
          </div>

          {recommendations.length > 0 && (
            <div className="search-page__section-divider" />
          )}
        </>
      )}

      {/* Recommendations section */}
      {!loading && recommendations.length > 0 && (
        <>
          <div className="search-page__section-label">
            {matches.length > 0 ? 'You Might Also Like' : 'Recommendations'}
            <span className="search-page__section-badge">{recommendations.length}</span>
          </div>
          <div className="search-grid">
            {recommendations.map((movie, i) => (
              <MovieCard
                key={`rec-${movie.title}-${i}`}
                movie={movie}
                onClick={setSelected}
                gridMode
              />
            ))}
          </div>
        </>
      )}

      {selectedMovie && (
        <MovieModal movie={selectedMovie} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
