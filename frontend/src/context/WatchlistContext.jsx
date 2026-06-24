import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getWatchlist, addToWatchlist, removeFromWatchlist } from '../lib/api';

// ---------------------------------------------------------------------------
// Anonymous device identity
// Each visitor gets a stable UUID stored in localStorage.
// This is used as the row key in Supabase — no login required.
// ---------------------------------------------------------------------------

const STORAGE_KEY   = 'watchtower_watchlist';
const USER_ID_KEY   = 'watchtower_user_id';

function getOrCreateUserId() {
  let id = localStorage.getItem(USER_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(USER_ID_KEY, id);
  }
  return id;
}

const USER_ID = getOrCreateUserId();

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const WatchlistContext = createContext(null);

export function WatchlistProvider({ children }) {
  const [watchlist, setWatchlist] = useState(() => {
    // Optimistic local seed while we fetch from Supabase
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch {
      return [];
    }
  });

  const [loading, setLoading] = useState(false);
  const [supabaseReady, setSupabaseReady] = useState(false);

  // On mount, pull the real watchlist from Supabase (if backend is configured)
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    getWatchlist(USER_ID)
      .then((data) => {
        if (cancelled) return;
        // data = { watchlist: [ { movie: {...}, saved_at: '...' }, ... ] }
        const movies = (data.watchlist || []).map((row) => ({
          ...row.movie,
          savedAt: new Date(row.saved_at).getTime(),
        }));
        setWatchlist(movies);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(movies));
        setSupabaseReady(true);
      })
      .catch(() => {
        // Backend not configured or offline — fall back to localStorage silently
        if (!cancelled) setSupabaseReady(false);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  const toggleWatchlist = useCallback((movie) => {
    const exists = watchlist.some((m) => m.title === movie.title);

    // Optimistic update first so UI is instant
    setWatchlist((prev) => {
      const updated = exists
        ? prev.filter((m) => m.title !== movie.title)
        : [{ ...movie, savedAt: Date.now() }, ...prev];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });

    // Persist to Supabase in the background (if available)
    if (supabaseReady) {
      if (exists) {
        removeFromWatchlist(USER_ID, movie.title).catch(console.warn);
      } else {
        addToWatchlist(USER_ID, movie).catch(console.warn);
      }
    }
  }, [watchlist, supabaseReady]);

  const isInWatchlist = useCallback(
    (title) => watchlist.some((m) => m.title === title),
    [watchlist],
  );

  return (
    <WatchlistContext.Provider value={{ watchlist, toggleWatchlist, isInWatchlist, loading, userId: USER_ID }}>
      {children}
    </WatchlistContext.Provider>
  );
}

export function useWatchlist() {
  const ctx = useContext(WatchlistContext);
  if (!ctx) throw new Error('useWatchlist must be used within WatchlistProvider');
  return ctx;
}
