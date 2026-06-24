import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useWatchlist } from '../context/WatchlistContext';
import MovieCard from '../components/MovieCard';
import MovieModal from '../components/MovieModal';

function IconBookmark() {
  return (
    <svg className="state-container__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </svg>
  );
}

export default function WatchlistPage() {
  const { watchlist }               = useWatchlist();
  const [selectedMovie, setSelected] = useState(null);

  return (
    <div className="watchlist-page">
      <div className="watchlist-page__header">
        <h1 className="watchlist-page__title">My Watchlist</h1>
        <p className="watchlist-page__subtitle">
          {watchlist.length === 0
            ? 'No movies saved yet'
            : `${watchlist.length} movie${watchlist.length !== 1 ? 's' : ''} saved`}
        </p>
      </div>

      {watchlist.length === 0 ? (
        <div className="state-container">
          <IconBookmark />
          <p className="state-container__title">Your Watchlist is Empty</p>
          <p className="state-container__text">
            Search for a movie and click "+ Watchlist" on any card to save it here.
          </p>
          <Link to="/" className="btn btn--primary" style={{ marginTop: 28 }}>
            Discover Movies
          </Link>
        </div>
      ) : (
        <div className="search-grid">
          {watchlist.map((movie, i) => (
            <MovieCard
              key={`${movie.title}-${i}`}
              movie={movie}
              onClick={setSelected}
              gridMode
            />
          ))}
        </div>
      )}

      {selectedMovie && (
        <MovieModal movie={selectedMovie} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
