# 🎬 WatchTower

> TF-IDF powered movie recommendation engine with a React frontend and FastAPI backend.

---

## Quick Start (Development)

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- [Supabase account](https://supabase.com) (free tier — optional for local dev)

### 2. Backend setup

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Copy the env template and fill in your keys:
```bash
cp .env.example .env
# Edit .env with your real values
```

Add your data CSVs to `backend/data/`:
- `tmdb_5000_movies.csv`
- `tmdb_5000_credits.csv`

Start the API:
```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
# Edit frontend/.env if you have a deployed backend URL
npm run dev
```

Open http://localhost:5173

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `OMDB_API_KEY` | Recommended | Movie poster images. [Free key here](https://www.omdbapi.com/apikey.aspx) |
| `SUPABASE_URL` | Optional | Supabase project URL (for watchlist persistence) |
| `SUPABASE_KEY` | Optional | Supabase service-role key (kept server-side only) |
| `ALLOWED_ORIGINS` | **Production required** | Your frontend domain, e.g. `https://watchtower.vercel.app` |
| `WEB_CONCURRENCY` | Optional | Gunicorn worker count. Default: `2`. Rule of thumb: `(2 × cores) + 1` |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | Production only | Deployed backend URL, e.g. `https://api.watchtower.app` |
| `VITE_SUPABASE_URL` | Optional | Same as backend `SUPABASE_URL` |
| `VITE_SUPABASE_ANON_KEY` | Optional | Supabase **anon** key (safe to expose publicly) |

---

## Supabase Setup (Watchlist Persistence)

1. Create a free project at [supabase.com](https://supabase.com)
2. Go to **Settings → API** and copy your Project URL and keys
3. Open the **SQL Editor** and run:

```sql
create table watchlist (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null,
  movie_title text not null,
  movie       jsonb not null,
  saved_at    timestamptz default now(),
  unique (user_id, movie_title)
);

-- Enable Row Level Security (anonymous demo policy)
alter table watchlist enable row level security;
create policy "allow_all" on watchlist for all using (true) with check (true);
```

4. Add credentials to `backend/.env` and `frontend/.env`

> **Note:** Each visitor gets a stable anonymous UUID stored in `localStorage`. No login required. Watchlists persist across browser sessions and devices if the same UUID is used.

---

## API Cost Estimate

| Service | Free Tier | Estimated Cost |
|---|---|---|
| **OMDB** (posters) | 1,000 req/day | **Free** with caching (24h TTL). Paid: $1/mo for 100k req |
| **Supabase** (watchlist) | 500k API calls/mo | **Free** for typical usage. Paid: $25/mo |

---

## Deployment

### Option A: Full-Stack Docker Compose (VPS / Railway / Render)

The compose file runs **both** services — the FastAPI backend and the nginx-served React frontend.

```bash
# 1. Fill in your backend secrets
cp backend/.env.example backend/.env
# Edit backend/.env

# 2. Set your backend's public URL (Vite bakes this in at build time)
export VITE_API_URL=https://api.yourdomain.com  # or your server IP:8000

# 3. Build & launch
docker compose up -d --build
```

- Frontend: `http://your-server` (port 80)
- Backend API: `http://your-server:8000`
- Health check: `http://your-server:8000/api/health`

> **CORS**: Remember to set `ALLOWED_ORIGINS=https://your-frontend-domain` in `backend/.env`.

---

### Option B: Split Deployment (Recommended for production scale)

| Part | Platform | Notes |
|---|---|---|
| Backend | [Railway](https://railway.app) | Point at `backend/`, set env vars in dashboard |
| Backend | [Render](https://render.com) | Web service, Docker runtime, set env vars |
| Backend | [Fly.io](https://fly.io) | `fly launch` in `backend/`, set secrets with `fly secrets set` |
| Frontend | [Vercel](https://vercel.com) | Import repo, set root to `frontend/`, add `VITE_API_URL` env var |
| Frontend | [Netlify](https://netlify.com) | Base dir: `frontend/`, build: `npm run build`, publish: `dist/` |

**SPA routing** is handled automatically:
- Vercel: via `frontend/vercel.json`
- Netlify: via `frontend/public/_redirects`
- Docker/nginx: via `frontend/nginx.conf`

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check + model status |
| `/api/recommend` | POST | `{ "query": "..." }` → matches + recommendations |
| `/api/trending` | GET | `?limit=20` top movies by popularity |
| `/api/top-rated` | GET | `?limit=20` top movies by rating |
| `/api/watchlist` | GET | `?user_id=<uuid>` fetch user's watchlist |
| `/api/watchlist` | POST | `{ "user_id": "...", "movie": {...} }` add to watchlist |
| `/api/watchlist/{title}` | DELETE | `?user_id=<uuid>` remove from watchlist |
