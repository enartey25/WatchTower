import { useState } from 'react';
import { useWatchlist } from '../context/WatchlistContext';

/* --------------------------------------------------------------------------
   Genre → gradient fallback (used when no poster_url is available)
   -------------------------------------------------------------------------- */
const GENRE_GRADIENTS = {
  Action:      'linear-gradient(150deg, #1a0000 0%, #6b0f0f 45%, #c41010 100%)',
  Drama:       'linear-gradient(150deg, #0a0a20 0%, #1a1a60 45%, #3636aa 100%)',
  Comedy:      'linear-gradient(150deg, #1a1200 0%, #6b4e00 45%, #d4920e 100%)',
  Thriller:    'linear-gradient(150deg, #080808 0%, #1e1e1e 45%, #444444 100%)',
  Science:     'linear-gradient(150deg, #000e1a 0%, #00305e 45%, #0066cc 100%)',
  Horror:      'linear-gradient(150deg, #030303 0%, #280010 45%, #800020 100%)',
  Romance:     'linear-gradient(150deg, #180010 0%, #600040 45%, #bb0070 100%)',
  Adventure:   'linear-gradient(150deg, #001208 0%, #004e22 45%, #009944 100%)',
  Animation:   'linear-gradient(150deg, #0f0025 0%, #3d0075 45%, #8000ee 100%)',
  Fantasy:     'linear-gradient(150deg, #000d1a 0%, #00264d 45%, #004d99 100%)',
  Crime:       'linear-gradient(150deg, #080600 0%, #302400 45%, #6b5200 100%)',
  Mystery:     'linear-gradient(150deg, #03030f 0%, #0e0e30 45%, #1e1e6e 100%)',
  Family:      'linear-gradient(150deg, #1a0a00 0%, #6b3000 45%, #d45c0c 100%)',
  History:     'linear-gradient(150deg, #100800 0%, #4a2800 45%, #8c4e00 100%)',
  War:         'linear-gradient(150deg, #080808 0%, #282828 45%, #484848 100%)',
  Music:       'linear-gradient(150deg, #001518 0%, #004a55 45%, #009aab 100%)',
  Western:     'linear-gradient(150deg, #120700 0%, #4e2200 45%, #8c3e00 100%)',
  Documentary: 'linear-gradient(150deg, #0a0a0a 0%, #1e2e1e 45%, #2e4e2e 100%)',
};
const DEFAULT_GRADIENT = 'linear-gradient(150deg, #0e0e0e 0%, #1a1a1a 45%, #2a2a2a 100%)';

function getGradient(genres) {
  if (!genres || genres.length === 0) return DEFAULT_GRADIENT;
  const key = Object.keys(GENRE_GRADIENTS).find((k) =>
    genres[0].toLowerCase().startsWith(k.toLowerCase())
  );
  return GENRE_GRADIENTS[key] || DEFAULT_GRADIENT;
}

/* --------------------------------------------------------------------------
   MovieCard
   -------------------------------------------------------------------------- */
export default function MovieCard({ movie, onClick, gridMode = false }) {
  const { toggleWatchlist, isInWatchlist } = useWatchlist();
  const [imgError, setImgError] = useState(false);

  const saved       = isInWatchlist(movie.title);
  const gradient    = getGradient(movie.genres);
  const hasPoster   = movie.poster_url && !imgError;
  const firstGenre  = movie.genres?.[0] ?? '';
  const releaseYear = movie.release_year ?? '';

  const handleWatchlist = (e) => {
    e.stopPropagation();
    toggleWatchlist(movie);
  };

  return (
    <div
      className={`movie-card${gridMode ? ' movie-card--grid' : ''}`}
      onClick={() => onClick?.(movie)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.(movie)}
      aria-label={`View details for ${movie.title}`}
    >
      {/* Poster */}
      <div
        className="movie-card__poster"
        style={hasPoster ? {} : { background: gradient }}
      >
        {hasPoster ? (
          <img
            src={movie.poster_url}
            alt={movie.title}
            className="movie-card__poster-img"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        ) : (
          <span className="movie-card__poster-letter">
            {movie.title.charAt(0).toUpperCase()}
          </span>
        )}

        <div className="movie-card__poster-overlay" />

        {/* Rating badge */}
        {movie.vote_average > 0 && (
          <div className="movie-card__rating">
            {movie.vote_average.toFixed(1)}
          </div>
        )}

        {/* Hover reveal info */}
        <div className="movie-card__info">
          <div className="movie-card__title">{movie.title}</div>
          <div className="movie-card__meta">
            {releaseYear && <span className="movie-card__year">{releaseYear}</span>}
            {firstGenre  && <span className="movie-card__genre">{firstGenre}</span>}
          </div>
          <button
            className={`movie-card__watchlist-btn${saved ? ' movie-card__watchlist-btn--saved' : ''}`}
            onClick={handleWatchlist}
            aria-label={saved ? `Remove ${movie.title} from watchlist` : `Add ${movie.title} to watchlist`}
          >
            {saved ? 'Saved' : '+ Watchlist'}
          </button>
        </div>
      </div>

      {/* Always-visible label below poster */}
      <div className="movie-card__label">
        <div className="movie-card__label-title">{movie.title}</div>
        <div className="movie-card__label-meta">
          {[releaseYear, firstGenre].filter(Boolean).join(' • ')}
        </div>
      </div>
    </div>
  );
}
