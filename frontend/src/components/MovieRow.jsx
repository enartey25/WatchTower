import { useRef, useState } from 'react';
import MovieCard from './MovieCard';
import MovieModal from './MovieModal';

function IconChevronLeft() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15,18 9,12 15,6" />
    </svg>
  );
}

function IconChevronRight() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9,18 15,12 9,6" />
    </svg>
  );
}

export default function MovieRow({ title, movies, isLoading }) {
  const trackRef                    = useRef(null);
  const [selectedMovie, setSelected] = useState(null);

  const scroll = (dir) => {
    trackRef.current?.scrollBy({
      left: dir === 'left' ? -640 : 640,
      behavior: 'smooth',
    });
  };

  /* Loading skeleton */
  if (isLoading) {
    return (
      <div className="movie-row">
        <div className="movie-row__header">
          <h2 className="movie-row__title">{title}</h2>
        </div>
        <div className="movie-row__track">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} style={{ flexShrink: 0, width: 180 }}>
              <div className="skeleton skeleton-card" />
              <div className="skeleton skeleton-label" style={{ width: '75%' }} />
              <div className="skeleton skeleton-label" style={{ width: '50%', marginTop: 5 }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!movies || movies.length === 0) return null;

  return (
    <>
      <div className="movie-row">
        <div className="movie-row__header">
          <h2 className="movie-row__title">{title}</h2>
        </div>

        <div className="movie-row__scroll-container">
          <button
            className="movie-row__arrow movie-row__arrow--left"
            onClick={() => scroll('left')}
            aria-label="Scroll left"
          >
            <IconChevronLeft />
          </button>

          <div className="movie-row__track" ref={trackRef}>
            {movies.map((movie, i) => (
              <MovieCard
                key={`${movie.title}-${i}`}
                movie={movie}
                onClick={setSelected}
              />
            ))}
          </div>

          <button
            className="movie-row__arrow movie-row__arrow--right"
            onClick={() => scroll('right')}
            aria-label="Scroll right"
          >
            <IconChevronRight />
          </button>
        </div>
      </div>

      {selectedMovie && (
        <MovieModal movie={selectedMovie} onClose={() => setSelected(null)} />
      )}
    </>
  );
}
