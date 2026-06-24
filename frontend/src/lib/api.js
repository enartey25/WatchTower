import axios from 'axios';

// In dev, VITE_API_URL is empty — Vite proxy forwards /api → localhost:8000
// In production, set VITE_API_URL to your deployed backend URL (no trailing slash)
const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 45000,
  headers: { 'Content-Type': 'application/json' },
});

export const checkHealth = () => api.get('/health').then((r) => r.data);

export const getRecommendations = (query) =>
  api.post('/recommend', { query }).then((r) => r.data);

export const getTrending = (limit = 20) =>
  api.get(`/trending?limit=${limit}`).then((r) => r.data);

export const getTopRated = (limit = 20) =>
  api.get(`/top-rated?limit=${limit}`).then((r) => r.data);

// --- Watchlist (Supabase-backed via backend) ---
export const getWatchlist = (userId) =>
  api.get(`/watchlist?user_id=${userId}`).then((r) => r.data);

export const addToWatchlist = (userId, movie) =>
  api.post('/watchlist', { user_id: userId, movie }).then((r) => r.data);

export const removeFromWatchlist = (userId, movieTitle) =>
  api.delete(`/watchlist/${encodeURIComponent(movieTitle)}?user_id=${userId}`).then((r) => r.data);

export default api;
