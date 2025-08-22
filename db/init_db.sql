-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create main tables
CREATE TABLE issuer (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  ticker TEXT UNIQUE,
  cik TEXT,
  sector TEXT,
  country TEXT DEFAULT 'US',
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- Price data table (time-series)
CREATE TABLE price (
  id SERIAL,
  issuer_id INT REFERENCES issuer(id) ON DELETE CASCADE,
  ts TIMESTAMP NOT NULL,
  open NUMERIC(10,4),
  high NUMERIC(10,4),
  low NUMERIC(10,4),
  close NUMERIC(10,4),
  volume BIGINT,
  adj_close NUMERIC(10,4),
  created_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (id, ts)
);

-- Create TimescaleDB hypertable for price data
SELECT create_hypertable('price', 'ts', if_not_exists => TRUE);

-- Feature snapshot table (time-series)
CREATE TABLE feature_snapshot (
  id SERIAL,
  issuer_id INT REFERENCES issuer(id) ON DELETE CASCADE,
  ts TIMESTAMP NOT NULL,
  feature_name TEXT NOT NULL,
  value DOUBLE PRECISION,
  source TEXT,
  created_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (id, ts)
);

-- Create TimescaleDB hypertable for feature data
SELECT create_hypertable('feature_snapshot', 'ts', if_not_exists => TRUE);

-- Score table (time-series)
CREATE TABLE score (
  id SERIAL,
  issuer_id INT REFERENCES issuer(id) ON DELETE CASCADE,
  ts TIMESTAMP NOT NULL,
  score DOUBLE PRECISION NOT NULL,
  bucket TEXT NOT NULL,
  base DOUBLE PRECISION,
  market DOUBLE PRECISION,
  event_delta DOUBLE PRECISION,
  macro_adj DOUBLE PRECISION,
  model_version TEXT,
  explanation JSONB,
  created_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (id, ts)
);

-- Create TimescaleDB hypertable for score data
SELECT create_hypertable('score', 'ts', if_not_exists => TRUE);

-- Event table (time-series)
CREATE TABLE event (
  id SERIAL,
  issuer_id INT REFERENCES issuer(id) ON DELETE CASCADE,
  ts TIMESTAMP NOT NULL,
  type TEXT NOT NULL,
  sentiment DOUBLE PRECISION,
  weight DOUBLE PRECISION,
  headline TEXT,
  url TEXT,
  raw_hash TEXT,
  decay_factor DOUBLE PRECISION DEFAULT 1.0,
  source TEXT,
  created_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (id, ts)
);

-- Create index on raw_hash (not unique due to TimescaleDB constraints)
CREATE INDEX idx_event_raw_hash ON event(raw_hash);

-- Create TimescaleDB hypertable for event data
SELECT create_hypertable('event', 'ts', if_not_exists => TRUE);

-- Macro data table (time-series)
CREATE TABLE macro (
  id SERIAL,
  ts TIMESTAMP NOT NULL,
  key TEXT NOT NULL,
  value DOUBLE PRECISION,
  source TEXT,
  created_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (id, ts)
);

-- Create TimescaleDB hypertable for macro data
SELECT create_hypertable('macro', 'ts', if_not_exists => TRUE);

-- Alert subscriptions table
CREATE TABLE alert_subscription (
  id SERIAL PRIMARY KEY,
  issuer_id INT REFERENCES issuer(id) ON DELETE CASCADE,
  email TEXT,
  webhook_url TEXT,
  threshold DOUBLE PRECISION DEFAULT 5.0,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- Alert history table
CREATE TABLE alert_history (
  id SERIAL PRIMARY KEY,
  subscription_id INT REFERENCES alert_subscription(id) ON DELETE CASCADE,
  issuer_id INT REFERENCES issuer(id) ON DELETE CASCADE,
  alert_type TEXT NOT NULL,
  message TEXT,
  score_change DOUBLE PRECISION,
  triggered_at TIMESTAMP DEFAULT now()
);

-- Model metadata table
CREATE TABLE model_metadata (
  id SERIAL PRIMARY KEY,
  model_version TEXT UNIQUE NOT NULL,
  model_type TEXT NOT NULL,
  training_date TIMESTAMP,
  performance_metrics JSONB,
  feature_importance JSONB,
  hyperparameters JSONB,
  created_at TIMESTAMP DEFAULT now()
);

-- Task queue status table
CREATE TABLE task_status (
  id SERIAL PRIMARY KEY,
  task_name TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  error_message TEXT,
  task_metadata JSONB,
  created_at TIMESTAMP DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX idx_issuer_ticker ON issuer(ticker);
CREATE INDEX idx_issuer_cik ON issuer(cik);
CREATE INDEX idx_issuer_sector ON issuer(sector);

CREATE INDEX idx_price_issuer_ts ON price(issuer_id, ts DESC);
CREATE INDEX idx_price_ts ON price(ts DESC);

CREATE INDEX idx_feature_issuer_ts ON feature_snapshot(issuer_id, ts DESC);
CREATE INDEX idx_feature_name ON feature_snapshot(feature_name);

CREATE INDEX idx_score_issuer_ts ON score(issuer_id, ts DESC);
CREATE INDEX idx_score_ts ON score(ts DESC);
CREATE INDEX idx_score_bucket ON score(bucket);

CREATE INDEX idx_event_issuer_ts ON event(issuer_id, ts DESC);
CREATE INDEX idx_event_type ON event(type);
CREATE INDEX idx_event_ts ON event(ts DESC);
CREATE INDEX idx_event_hash ON event(raw_hash);

CREATE INDEX idx_macro_key_ts ON macro(key, ts DESC);

CREATE INDEX idx_alert_subscription_issuer ON alert_subscription(issuer_id);
CREATE INDEX idx_alert_history_issuer ON alert_history(issuer_id);

-- Create functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_issuer_updated_at BEFORE UPDATE ON issuer
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alert_subscription_updated_at BEFORE UPDATE ON alert_subscription
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to get latest score for an issuer
CREATE OR REPLACE FUNCTION get_latest_score(issuer_id_param INT)
RETURNS TABLE (
    score DOUBLE PRECISION,
    bucket TEXT,
    ts TIMESTAMP,
    base DOUBLE PRECISION,
    market DOUBLE PRECISION,
    event_delta DOUBLE PRECISION,
    macro_adj DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT s.score, s.bucket, s.ts, s.base, s.market, s.event_delta, s.macro_adj
    FROM score s
    WHERE s.issuer_id = issuer_id_param
    ORDER BY s.ts DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to get score change over time period
CREATE OR REPLACE FUNCTION get_score_change(
    issuer_id_param INT,
    hours_back INT DEFAULT 24
)
RETURNS TABLE (
    score_change DOUBLE PRECISION,
    current_score DOUBLE PRECISION,
    previous_score DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    WITH current_score AS (
        SELECT score, ts
        FROM score
        WHERE issuer_id = issuer_id_param
        ORDER BY ts DESC
        LIMIT 1
    ),
    previous_score AS (
        SELECT score
        FROM score
        WHERE issuer_id = issuer_id_param
        AND ts <= (SELECT ts FROM current_score) - INTERVAL '1 hour' * hours_back
        ORDER BY ts DESC
        LIMIT 1
    )
    SELECT 
        (cs.score - COALESCE(ps.score, cs.score)) as score_change,
        cs.score as current_score,
        COALESCE(ps.score, cs.score) as previous_score
    FROM current_score cs
    CROSS JOIN previous_score ps;
END;
$$ LANGUAGE plpgsql;

-- Function to get active events for an issuer
CREATE OR REPLACE FUNCTION get_active_events(
    issuer_id_param INT,
    hours_back INT DEFAULT 168  -- 7 days
)
RETURNS TABLE (
    event_id INT,
    event_type TEXT,
    headline TEXT,
    sentiment DOUBLE PRECISION,
    weight DOUBLE PRECISION,
    decay_factor DOUBLE PRECISION,
    ts TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.type,
        e.headline,
        e.sentiment,
        e.weight,
        e.decay_factor,
        e.ts
    FROM event e
    WHERE e.issuer_id = issuer_id_param
    AND e.ts >= now() - INTERVAL '1 hour' * hours_back
    AND e.decay_factor > 0.1  -- Only events with significant remaining impact
    ORDER BY e.ts DESC;
END;
$$ LANGUAGE plpgsql;

-- Insert default model metadata
INSERT INTO model_metadata (model_version, model_type, training_date, hyperparameters)
VALUES (
    'v1.0',
    'EBM',
    now(),
    '{"scoring_weights": {"base": 0.55, "market": 0.25, "event": 0.12, "macro": 0.08}}'
);

-- Create views for common queries
CREATE VIEW issuer_summary AS
SELECT 
    i.id,
    i.name,
    i.ticker,
    i.sector,
    i.country,
    s.score as latest_score,
    s.bucket as latest_bucket,
    s.ts as latest_score_ts,
    s.base,
    s.market,
    s.event_delta,
    s.macro_adj
FROM issuer i
LEFT JOIN LATERAL (
    SELECT score, bucket, ts, base, market, event_delta, macro_adj
    FROM score
    WHERE issuer_id = i.id
    ORDER BY ts DESC
    LIMIT 1
) s ON true;

-- Create view for recent alerts
CREATE VIEW recent_alerts AS
SELECT 
    ah.id,
    ah.alert_type,
    ah.message,
    ah.score_change,
    ah.triggered_at,
    i.name as issuer_name,
    i.ticker,
    asub.email,
    asub.webhook_url
FROM alert_history ah
JOIN issuer i ON ah.issuer_id = i.id
LEFT JOIN alert_subscription asub ON ah.subscription_id = asub.id
WHERE ah.triggered_at >= now() - INTERVAL '24 hours'
ORDER BY ah.triggered_at DESC;
