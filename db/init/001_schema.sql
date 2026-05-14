CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE activities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strava_id       BIGINT UNIQUE NOT NULL,
    sport           VARCHAR(20) NOT NULL,
    start_time      TIMESTAMPTZ NOT NULL,
    duration_secs   INT NOT NULL,
    distance_m      FLOAT,
    elevation_m     FLOAT,
    avg_hr          INT,
    max_hr          INT,
    avg_pace_spm    FLOAT,
    calories        INT,
    sport_data      JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_activities_start_time ON activities (start_time DESC);
CREATE INDEX idx_activities_sport ON activities (sport);

CREATE TABLE activity_streams (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_id     UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    recorded_at     TIMESTAMPTZ NOT NULL,
    hr_bpm          INT,
    pace_spm        FLOAT,
    altitude_m      FLOAT,
    distance_m      FLOAT,
    cadence         INT
);

CREATE INDEX idx_streams_activity_time ON activity_streams (activity_id, recorded_at);

CREATE TABLE body_metrics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    measured_at     DATE NOT NULL UNIQUE,
    weight_kg       FLOAT,
    body_fat_pct    FLOAT,
    bmi             FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_body_metrics_date ON body_metrics (measured_at DESC);

CREATE TABLE resting_hr_daily (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date            DATE NOT NULL UNIQUE,
    resting_hr_bpm  INT NOT NULL,
    source          VARCHAR(20) NOT NULL CHECK (source IN ('withings', 'derived'))
);

CREATE INDEX idx_resting_hr_date ON resting_hr_daily (date DESC);

CREATE TABLE max_hr_estimates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estimated_at    DATE NOT NULL,
    max_hr_bpm      INT NOT NULL,
    method          VARCHAR(40) NOT NULL DEFAULT 'rolling_30d_peak',
    window_start    DATE,
    window_end      DATE
);

CREATE INDEX idx_max_hr_date ON max_hr_estimates (estimated_at DESC);

CREATE TABLE hr_zone_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calculated_at   DATE NOT NULL,
    max_hr          INT NOT NULL,
    resting_hr      INT NOT NULL,
    z1_min          INT, z1_max INT,
    z2_min          INT, z2_max INT,
    z3_min          INT, z3_max INT,
    z4_min          INT, z4_max INT,
    z5_min          INT, z5_max INT,
    method          VARCHAR(20) NOT NULL DEFAULT 'karvonen'
);

CREATE INDEX idx_hr_zones_date ON hr_zone_history (calculated_at DESC);

CREATE TABLE daily_metrics (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date                DATE NOT NULL UNIQUE,
    z1_mins             INT NOT NULL DEFAULT 0,
    z2_mins             INT NOT NULL DEFAULT 0,
    z3_mins             INT NOT NULL DEFAULT 0,
    z4_mins             INT NOT NULL DEFAULT 0,
    z5_mins             INT NOT NULL DEFAULT 0,
    total_distance_m    FLOAT NOT NULL DEFAULT 0,
    total_duration_secs INT NOT NULL DEFAULT 0
);

CREATE INDEX idx_daily_metrics_date ON daily_metrics (date DESC);

CREATE TABLE training_load (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date    DATE NOT NULL UNIQUE,
    tss     FLOAT,
    atl     FLOAT,
    ctl     FLOAT,
    tsb     FLOAT
);

CREATE INDEX idx_training_load_date ON training_load (date DESC);

CREATE TABLE recommendations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    category        VARCHAR(30) NOT NULL CHECK (category IN ('training', 'recovery', 'weight', 'pace')),
    message         TEXT NOT NULL,
    supporting_data JSONB DEFAULT '{}'
);

CREATE INDEX idx_recommendations_generated ON recommendations (generated_at DESC);

CREATE TABLE sync_state (
    key     VARCHAR(50) PRIMARY KEY,
    value   TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
