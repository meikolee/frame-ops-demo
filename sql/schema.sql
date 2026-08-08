-- FRAME ops schema (SQLite dialect; comments map 1:1 to Postgres habits)
-- Interview talking points: covering indexes, EXPLAIN, transaction boundaries.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id            TEXT PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE,
  name          TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Hot path: login by email
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS videos (
  id            TEXT PRIMARY KEY,
  slug          TEXT NOT NULL UNIQUE,
  title         TEXT NOT NULL,
  summary       TEXT NOT NULL DEFAULT '',
  status        TEXT NOT NULL CHECK (status IN ('draft', 'processing', 'ready', 'published')),
  duration_sec  INTEGER NOT NULL DEFAULT 0,
  hls_path      TEXT,
  poster_url    TEXT,
  view_count    INTEGER NOT NULL DEFAULT 0,
  published_at  TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Public listing: published only, newest first
CREATE INDEX IF NOT EXISTS idx_videos_status_published
  ON videos(status, published_at DESC);

-- Slug lookup for SSR detail pages
CREATE INDEX IF NOT EXISTS idx_videos_slug ON videos(slug);

CREATE TABLE IF NOT EXISTS analytics_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL,
  path        TEXT NOT NULL,
  visitor_id  TEXT NOT NULL,
  session_id  TEXT NOT NULL,
  video_id    TEXT,
  meta_json   TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- PV/UV range scans + retention cohort joins
CREATE INDEX IF NOT EXISTS idx_analytics_created ON analytics_events(created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_visitor_day
  ON analytics_events(visitor_id, created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_name_created
  ON analytics_events(name, created_at);

CREATE TABLE IF NOT EXISTS uploads (
  id            TEXT PRIMARY KEY,
  object_key    TEXT NOT NULL,
  filename      TEXT NOT NULL,
  mime_type     TEXT NOT NULL,
  size_bytes    INTEGER NOT NULL,
  chunk_size    INTEGER NOT NULL,
  total_chunks  INTEGER NOT NULL,
  received_mask TEXT NOT NULL, -- bitstring of received chunks
  status        TEXT NOT NULL CHECK (status IN ('pending', 'assembling', 'complete', 'aborted')),
  created_by    TEXT NOT NULL REFERENCES users(id),
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  completed_at  TEXT
);

CREATE TABLE IF NOT EXISTS crawl_jobs (
  id               TEXT PRIMARY KEY,
  url              TEXT NOT NULL,
  status           TEXT NOT NULL,
  attempts         INTEGER NOT NULL DEFAULT 0,
  last_error       TEXT,
  extracted_title  TEXT,
  created_at       TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_crawl_status ON crawl_jobs(status, created_at);

-- Example EXPLAIN (run in sqlite3 / psql):
-- EXPLAIN QUERY PLAN
-- SELECT slug, title FROM videos
-- WHERE status = 'published'
-- ORDER BY published_at DESC
-- LIMIT 20;
-- Expect: SEARCH videos USING INDEX idx_videos_status_published
