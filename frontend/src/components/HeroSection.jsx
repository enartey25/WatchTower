import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const SUGGESTIONS = ['Inception', 'The Dark Knight', 'Interstellar', 'Parasite', 'Avengers'];

// Deterministic particles so SSR / re-renders are stable
const PARTICLES = Array.from({ length: 18 }, (_, i) => ({
  id: i,
  size:  (((i * 13) % 4) + 2),
  left:  ((i * 17 + 5) % 100),
  top:   ((i * 23 + 10) % 100),
  color: i % 4 === 0 ? '#e50914' : 'rgba(255,255,255,0.55)',
  dur:   ((i % 4) + 4),
  delay: ((i * 0.4) % 5),
}));

function IconSearch() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

export default function HeroSection() {
  const [query, setQuery] = useState('');
  const navigate          = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query.trim())}`);
  };

  const handleSuggestion = (s) => navigate(`/search?q=${encodeURIComponent(s)}`);

  return (
    <section className="hero" aria-label="Search hero">
      <div className="hero__backdrop" />
      <div className="hero__scanlines" />

      <div className="hero__particles" aria-hidden="true">
        {PARTICLES.map((p) => (
          <div
            key={p.id}
            className="hero__particle"
            style={{
              width:  p.size,
              height: p.size,
              left:   `${p.left}%`,
              top:    `${p.top}%`,
              background: p.color,
              '--dur':   `${p.dur}s`,
              '--delay': `${p.delay}s`,
            }}
          />
        ))}
      </div>

      <div className="hero__content">
        <p className="hero__eyebrow">AI-Powered Discovery</p>

        <h1 className="hero__title">
          Your Next Favourite
          <span className="hero__title-accent">Movie Awaits.</span>
        </h1>

        <p className="hero__subtitle">
          Describe a movie, an actor, or a feeling. Our TF-IDF engine surfaces
          what you will love from 5,000 titles.
        </p>

        <div className="hero__search-wrapper">
          <form className="hero__search" onSubmit={handleSubmit}>
            <span className="hero__search-icon">
              <IconSearch />
            </span>
            <input
              id="hero-search-input"
              type="text"
              placeholder='Try "space thriller" or "Brad Pitt crime"...'
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoComplete="off"
              autoCorrect="off"
              spellCheck="false"
            />
            <button type="submit" className="hero__search-submit">
              Find Movies
            </button>
          </form>

          <p className="hero__hint">
            <span className="hero__hint-label">Quick search:</span>
            {SUGGESTIONS.map((s, i) => (
              <span key={s}>
                <button className="hero__hint-chip" onClick={() => handleSuggestion(s)}>
                  {s}
                </button>
                {i < SUGGESTIONS.length - 1 && <span className="hero__hint-sep">,</span>}
              </span>
            ))}
          </p>
        </div>
      </div>
    </section>
  );
}
