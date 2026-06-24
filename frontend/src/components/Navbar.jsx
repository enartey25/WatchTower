import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useWatchlist } from '../context/WatchlistContext';
import { checkHealth } from '../lib/api';

function IconSearch() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

export default function Navbar() {
  const [isScrolled, setIsScrolled]   = useState(false);
  const [searchOpen, setSearchOpen]   = useState(false);
  const [query, setQuery]             = useState('');
  const [backendOk, setBackendOk]     = useState(null); // null=checking, true=online, false=offline
  const inputRef                      = useRef(null);
  const { watchlist }                 = useWatchlist();
  const navigate                      = useNavigate();

  /* Scroll detection */
  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 30);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  /* Auto-focus search input */
  useEffect(() => {
    if (searchOpen && inputRef.current) inputRef.current.focus();
  }, [searchOpen]);

  /* Backend health ping on mount */
  useEffect(() => {
    checkHealth()
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    navigate(`/search?q=${encodeURIComponent(query.trim())}`);
    setQuery('');
    setSearchOpen(false);
  };

  const statusClass =
    backendOk === null  ? 'navbar__status--checking' :
    backendOk           ? 'navbar__status--online'   :
                          'navbar__status--offline';

  const statusTitle =
    backendOk === null  ? 'Connecting to backend...' :
    backendOk           ? 'Backend online'            :
                          'Backend offline — start the FastAPI server';

  return (
    <nav className={`navbar${isScrolled ? ' navbar--scrolled' : ''}`}>
      <div className="navbar__inner">
        <Link to="/" className="navbar__logo">WatchTower</Link>

        <div className="navbar__right">
          <div className={`navbar__status ${statusClass}`} title={statusTitle} />

          <form
            className={`navbar__search-form${searchOpen ? ' navbar__search-form--open' : ''}`}
            onSubmit={handleSearch}
          >
            <button
              type="button"
              className="navbar__search-btn"
              onClick={() => setSearchOpen((v) => !v)}
              aria-label="Toggle search"
            >
              <IconSearch />
            </button>
            {searchOpen && (
              <input
                ref={inputRef}
                type="text"
                className="navbar__search-input"
                placeholder="Titles, actors, genres..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            )}
          </form>

          <Link to="/watchlist" className="navbar__watchlist-link">
            Watchlist
            {watchlist.length > 0 && (
              <span className="navbar__badge">{watchlist.length}</span>
            )}
          </Link>
        </div>
      </div>
    </nav>
  );
}
