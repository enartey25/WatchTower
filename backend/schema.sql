-- ===========================================================================
-- WatchTower — Simplified PostgreSQL Schema (Merged Movies & Credits)
-- Run this in the Supabase SQL Editor or let the script apply it.
-- ===========================================================================

drop table if exists movie_genres cascade;
drop table if exists movie_keywords cascade;
drop table if exists movie_production_companies cascade;
drop table if exists movie_production_countries cascade;
drop table if exists movie_spoken_languages cascade;
drop table if exists cast_members cascade;
drop table if exists crew_members cascade;
drop table if exists genres cascade;
drop table if exists keywords cascade;
drop table if exists production_companies cascade;
drop table if exists production_countries cascade;
drop table if exists spoken_languages cascade;
drop table if exists people cascade;
drop table if exists movies cascade;

-- Create the single merged movies table
create table movies (
    id                  integer primary key,
    title               text not null,
    original_title      text,
    original_language   text,
    overview            text,
    tagline             text,
    release_date        date,
    status              text,
    homepage            text,
    budget              bigint,
    revenue             bigint,
    runtime             integer,
    popularity          numeric,
    vote_average        numeric,
    vote_count          integer,
    genres              text,         -- Store as text/JSON string
    keywords            text,         -- Store as text/JSON string
    production_companies text,        -- Store as text/JSON string
    production_countries text,        -- Store as text/JSON string
    spoken_languages    text,         -- Store as text/JSON string
    cast_data           text,         -- Store as text/JSON string (renamed to avoid SQL 'cast' reserved keyword)
    crew                text          -- Store as text/JSON string
);

-- Watchlist table (used by the frontend)
create table if not exists watchlist (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null,
  movie_title text not null,
  movie       jsonb not null,
  saved_at    timestamptz default now(),
  unique (user_id, movie_title)
);

-- Enable RLS and setup policy
alter table watchlist enable row level security;

drop policy if exists "allow_all" on watchlist;
create policy "allow_all" on watchlist for all using (true) with check (true);
