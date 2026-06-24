import { useState, useEffect } from 'react';
import { useWatchlist } from '../context/WatchlistContext';

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
};
const DEFAULT_GRADIENT = 'linear-gradient(150deg, #0e0e0e 0%, #1a1a1a 45%, #2a2a2a 100%)';

function getGradient(genres) {
  if (!genres || genres.length === 0) return DEFAULT_GRADIENT;
  const key = Object.keys(GENRE_GRADIENTS).find((k) =>
    genres[0].toLowerCase().startsWith(k.toLowerCase())
  );
  return GENRE_GRADIENTS[key] || DEFAULT_GRADIENT;
}

function IconClose() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6"  y1="6" x2="18" y2="18" />
    </svg>
  );
}

export default function MovieModal({ movie, onClose }) {
  const { toggleWatchlist, isInWatchlist } = useWatchlist();
  const [imgError, setImgError] = useState(false);

  const saved      = isInWatchlist(movie.title);
  const gradient   = getGradient(movie.genres);
  const hasPoster  = movie.poster_url && !imgError;

  /* Close on Escape, lock body scroll */
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Details for ${movie.title}`}
    >
      <div className="modal" onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div className="modal__header">
          {/* Background: real poster or gradient */}
          {hasPoster ? (
            <img
              src={movie.poster_url}
              alt={movie.title}
              className="modal__header-poster"
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="modal__header-bg" style={{ background: gradient }} />
          )}

          {/* Gradient scrim so title is always readable */}
          <div className="modal__header-overlay" />

          {/* Faint letter watermark shown only when no poster */}
          {!hasPoster && (
            <span className="modal__header-letter" aria-hidden="true">
              {movie.title.charAt(0).toUpperCase()}
            </span>
          )}

          <button className="modal__close" onClick={onClose} aria-label="Close modal">
            <IconClose />
          </button>

          <h2 className="modal__title">{movie.title}</h2>
        </div>

        {/* Body */}
        <div className="modal__body">
          <div className="modal__badges">
            {movie.vote_average > 0 && (
              <span className="badge badge--rating">
                {movie.vote_average.toFixed(1)} / 10
              </span>
            )}
            {movie.release_year && (
              <span className="badge badge--year">{movie.release_year}</span>
            )}
            {movie.genres?.map((g) => (
              <span key={g} className="badge badge--genre">{g}</span>
            ))}
            {movie.final_score != null && (
              <span className="badge badge--match">
                {Math.round(movie.final_score * 100)}% match
              </span>
            )}
          </div>

          {movie.tagline && (
            <p className="modal__tagline">"{movie.tagline}"</p>
          )}

          {movie.overview && (
            <p className="modal__overview">{movie.overview}</p>
          )}

          <div className="modal__actions">
            <button
              className={`btn ${saved ? 'btn--secondary' : 'btn--primary'}`}
              onClick={() => toggleWatchlist(movie)}
            >
              {saved ? 'Remove from Watchlist' : '+ Add to Watchlist'}
            </button>
            <button className="btn btn--secondary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
