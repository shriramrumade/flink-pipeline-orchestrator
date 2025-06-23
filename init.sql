CREATE TABLE IF NOT EXISTS pipelines (
    id SERIAL PRIMARY KEY,
    pipeline_id TEXT UNIQUE NOT NULL,
    source_type TEXT,
    source_path TEXT,
    source_format TEXT,
    sink_type TEXT,
    sink_index TEXT,
    transformations JSONB,
    schedule TEXT
);
