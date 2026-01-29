PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS team (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL,
  country       TEXT,
  source        TEXT,
  source_team_id TEXT,
  UNIQUE(source, source_team_id)
);

CREATE TABLE IF NOT EXISTS player (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL,
  birth_date    TEXT,
  nationality   TEXT,
  source        TEXT,
  source_player_id TEXT,
  UNIQUE(source, source_player_id)
);

CREATE TABLE IF NOT EXISTS match (
  id            INTEGER PRIMARY KEY,
  match_date    TEXT NOT NULL,      -- ISO date
  season        TEXT,               -- "2021/22" etc if available
  competition   TEXT,
  home_team_id  INTEGER REFERENCES team(id),
  away_team_id  INTEGER REFERENCES team(id),
  source        TEXT,
  source_match_id TEXT,
  UNIQUE(source, source_match_id)
);

-- One row per player appearance in a match (starter or sub)
CREATE TABLE IF NOT EXISTS appearance (
  match_id      INTEGER NOT NULL REFERENCES match(id) ON DELETE CASCADE,
  player_id     INTEGER NOT NULL REFERENCES player(id),
  team_id       INTEGER NOT NULL REFERENCES team(id),
  is_starter    INTEGER NOT NULL DEFAULT 0,
  minutes       INTEGER,
  position      TEXT,
  PRIMARY KEY(match_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_appearance_match ON appearance(match_id);
CREATE INDEX IF NOT EXISTS idx_appearance_player ON appearance(player_id);
CREATE INDEX IF NOT EXISTS idx_match_date ON match(match_date);
