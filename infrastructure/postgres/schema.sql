-- Not applied. No PostgreSQL server was started.
CREATE TABLE device (
  device_id TEXT PRIMARY KEY,
  rack_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  protocol TEXT NOT NULL
);

CREATE TABLE reading (
  device_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  value DOUBLE PRECISION NOT NULL,
  unit TEXT NOT NULL,
  quality TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL
);
