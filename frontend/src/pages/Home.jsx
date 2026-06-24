import { useState, useEffect } from 'react';
import HeroSection from '../components/HeroSection';
import MovieRow from '../components/MovieRow';
import { getTrending, getTopRated } from '../lib/api';

function IconAlert() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

export default function Home() {
  const [trending,        setTrending]        = useState([]);
  const [topRated,        setTopRated]        = useState([]);
  const [loadingTrending, setLoadingTrending] = useState(true);
  const [loadingTopRated, setLoadingTopRated] = useState(true);
  const [backendError,    setBackendError]    = useState(false);

  useEffect(() => {
    getTrending(20)
      .then((data) => setTrending(data.results))
      .catch(() => setBackendError(true))
      .finally(() => setLoadingTrending(false));

    getTopRated(20)
      .then((data) => setTopRated(data.results))
      .finally(() => setLoadingTopRated(false));
  }, []);

  return (
    <div>
      <HeroSection />

      <div className="movie-rows-container">
        {backendError && (
          <div className="backend-banner">
            <span className="backend-banner__icon"><IconAlert /></span>
            <div className="backend-banner__text">
              <p className="backend-banner__title">Backend not detected</p>
              <p className="backend-banner__body">
                Start the FastAPI server so trending movies can load and recommendations work.
              </p>
              <code className="backend-banner__code">
                cd backend &amp;&amp; uvicorn main:app --reload --port 8000
              </code>
            </div>
          </div>
        )}

        <MovieRow title="Trending Now"  movies={trending} isLoading={loadingTrending} />
        <MovieRow title="Top Rated"     movies={topRated} isLoading={loadingTopRated} />
      </div>
    </div>
  );
}
