-- DURAKA SONI GAMES PostgreSQL schema (stage 1). Currency is virtual only.
CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, pw_hash TEXT, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE profiles (user_id TEXT PRIMARY KEY REFERENCES users(id), avatar TEXT, level INT DEFAULT 1, xp INT DEFAULT 0, wins INT DEFAULT 0, losses INT DEFAULT 0, language TEXT DEFAULT 'tg');
CREATE TABLE wallets (user_id TEXT PRIMARY KEY REFERENCES users(id), coins BIGINT NOT NULL DEFAULT 0 CHECK (coins >= 0));
CREATE TABLE transactions (id BIGSERIAL PRIMARY KEY, user_id TEXT REFERENCES users(id), amount BIGINT NOT NULL, reason TEXT NOT NULL, idempotency_key TEXT UNIQUE NOT NULL, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE matches (id TEXT PRIMARY KEY, mode TEXT NOT NULL, variant TEXT NOT NULL, result JSONB, started_at TIMESTAMPTZ DEFAULT now(), finished_at TIMESTAMPTZ);
CREATE TABLE match_players (match_id TEXT REFERENCES matches(id), seat INT, user_id TEXT, is_bot BOOL DEFAULT false, team INT, place INT, PRIMARY KEY (match_id, seat));
CREATE TABLE teams (id BIGSERIAL PRIMARY KEY, match_id TEXT REFERENCES matches(id), team_no INT, won BOOL);
CREATE TABLE rankings (user_id TEXT REFERENCES users(id), mode TEXT, points INT DEFAULT 0, league TEXT DEFAULT 'bronze', PRIMARY KEY (user_id, mode));
CREATE TABLE shop_items (id TEXT PRIMARY KEY, category TEXT NOT NULL, price INT NOT NULL CHECK (price >= 0));
CREATE TABLE inventory (user_id TEXT REFERENCES users(id), item_id TEXT REFERENCES shop_items(id), equipped BOOL DEFAULT false, PRIMARY KEY (user_id, item_id));
CREATE TABLE friends (user_id TEXT REFERENCES users(id), friend_id TEXT REFERENCES users(id), status TEXT DEFAULT 'pending', PRIMARY KEY (user_id, friend_id));
CREATE TABLE missions (id TEXT PRIMARY KEY, kind TEXT, target INT, reward INT);
CREATE TABLE user_missions (user_id TEXT REFERENCES users(id), mission_id TEXT REFERENCES missions(id), day DATE, progress INT DEFAULT 0, claimed BOOL DEFAULT false, PRIMARY KEY (user_id, mission_id, day));
CREATE TABLE achievements (user_id TEXT REFERENCES users(id), code TEXT, unlocked_at TIMESTAMPTZ DEFAULT now(), PRIMARY KEY (user_id, code));
CREATE TABLE tournaments (id BIGSERIAL PRIMARY KEY, name TEXT, mode TEXT, starts_at TIMESTAMPTZ, reward_coins INT);
