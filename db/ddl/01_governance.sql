-- =========================================================
-- 01_governance.sql
-- Tablas de gobierno y trazabilidad:
--   - source_system
--   - source_run
--   - raw_asset
-- =========================================================

SET search_path TO hidden_gems, public;

-- =========================================================
-- 1) source_system
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.source_system (
    source_system_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_code            VARCHAR(100) NOT NULL UNIQUE,
    source_name            VARCHAR(255) NOT NULL,
    source_type            hidden_gems.source_type_enum NOT NULL,
    description            TEXT,
    base_url               VARCHAR(500),
    auth_type              hidden_gems.auth_type_enum,
    data_format_default    VARCHAR(50),
    refresh_mode_default   hidden_gems.refresh_mode_enum,
    supports_incremental   BOOLEAN NOT NULL DEFAULT FALSE,
    is_active              BOOLEAN NOT NULL DEFAULT TRUE,
    notes                  TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_source_system_source_code_format
        CHECK (source_code ~ '^[a-z0-9_]+$')
);

CREATE INDEX IF NOT EXISTS idx_source_system_type
    ON hidden_gems.source_system (source_type);

CREATE INDEX IF NOT EXISTS idx_source_system_is_active
    ON hidden_gems.source_system (is_active);

DROP TRIGGER IF EXISTS trg_source_system_updated_at ON hidden_gems.source_system;
CREATE TRIGGER trg_source_system_updated_at
BEFORE UPDATE ON hidden_gems.source_system
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

-- =========================================================
-- 2) source_run
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.source_run (
    source_run_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_code                   VARCHAR(150) NOT NULL UNIQUE,
    source_system_id           UUID NOT NULL,
    run_type                   hidden_gems.run_type_enum NOT NULL,
    trigger_type               hidden_gems.run_trigger_enum NOT NULL,
    status                     hidden_gems.run_status_enum NOT NULL DEFAULT 'pending',
    started_at                 TIMESTAMPTZ,
    finished_at                TIMESTAMPTZ,
    duration_seconds           INTEGER,
    records_extracted_count    BIGINT NOT NULL DEFAULT 0,
    records_staged_count       BIGINT NOT NULL DEFAULT 0,
    records_rejected_count     BIGINT NOT NULL DEFAULT 0,
    raw_asset_count            BIGINT NOT NULL DEFAULT 0,
    error_count                BIGINT NOT NULL DEFAULT 0,
    warning_count              BIGINT NOT NULL DEFAULT 0,
    config_snapshot_hash       CHAR(64),
    request_summary            JSONB,
    notes                      TEXT,
    parent_run_id              UUID,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_source_run_source_system
        FOREIGN KEY (source_system_id)
        REFERENCES hidden_gems.source_system (source_system_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_source_run_parent_run
        FOREIGN KEY (parent_run_id)
        REFERENCES hidden_gems.source_run (source_run_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_source_run_duration_non_negative
        CHECK (duration_seconds IS NULL OR duration_seconds >= 0),

    CONSTRAINT chk_source_run_counts_non_negative
        CHECK (
            records_extracted_count >= 0
            AND records_staged_count >= 0
            AND records_rejected_count >= 0
            AND raw_asset_count >= 0
            AND error_count >= 0
            AND warning_count >= 0
        ),

    CONSTRAINT chk_source_run_finished_after_started
        CHECK (
            finished_at IS NULL
            OR started_at IS NULL
            OR finished_at >= started_at
        )
);

CREATE INDEX IF NOT EXISTS idx_source_run_source_system
    ON hidden_gems.source_run (source_system_id);

CREATE INDEX IF NOT EXISTS idx_source_run_status
    ON hidden_gems.source_run (status);

CREATE INDEX IF NOT EXISTS idx_source_run_started_at
    ON hidden_gems.source_run (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_source_run_source_started
    ON hidden_gems.source_run (source_system_id, started_at DESC);

DROP TRIGGER IF EXISTS trg_source_run_updated_at ON hidden_gems.source_run;
CREATE TRIGGER trg_source_run_updated_at
BEFORE UPDATE ON hidden_gems.source_run
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

-- =========================================================
-- 3) raw_asset
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.raw_asset (
    raw_asset_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_code               VARCHAR(150) NOT NULL UNIQUE,
    source_system_id         UUID NOT NULL,
    source_run_id            UUID NOT NULL,
    asset_name               VARCHAR(255) NOT NULL,
    asset_type               hidden_gems.asset_type_enum NOT NULL,
    storage_path             TEXT NOT NULL,
    file_format              VARCHAR(50) NOT NULL,
    compression_type         VARCHAR(20),
    mime_type                VARCHAR(100),
    file_size_bytes          BIGINT,
    record_count_estimated   BIGINT,
    checksum_sha256          CHAR(64),
    query_name               VARCHAR(255),
    request_signature_hash   CHAR(64),
    content_created_at       TIMESTAMPTZ,
    retention_class          hidden_gems.retention_class_enum,
    is_available             BOOLEAN NOT NULL DEFAULT TRUE,
    notes                    TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_raw_asset_source_system
        FOREIGN KEY (source_system_id)
        REFERENCES hidden_gems.source_system (source_system_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_raw_asset_source_run
        FOREIGN KEY (source_run_id)
        REFERENCES hidden_gems.source_run (source_run_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_raw_asset_file_size_non_negative
        CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0),

    CONSTRAINT chk_raw_asset_record_count_non_negative
        CHECK (record_count_estimated IS NULL OR record_count_estimated >= 0),

    CONSTRAINT chk_raw_asset_sha256_format
        CHECK (
            checksum_sha256 IS NULL
            OR checksum_sha256 ~ '^[0-9a-fA-F]{64}$'
        ),

    CONSTRAINT chk_raw_asset_request_signature_hash_format
        CHECK (
            request_signature_hash IS NULL
            OR request_signature_hash ~ '^[0-9a-fA-F]{64}$'
        ),

    CONSTRAINT uq_raw_asset_run_path
        UNIQUE (source_run_id, storage_path)
);

CREATE INDEX IF NOT EXISTS idx_raw_asset_source_system
    ON hidden_gems.raw_asset (source_system_id);

CREATE INDEX IF NOT EXISTS idx_raw_asset_source_run
    ON hidden_gems.raw_asset (source_run_id);

CREATE INDEX IF NOT EXISTS idx_raw_asset_asset_type
    ON hidden_gems.raw_asset (asset_type);

CREATE INDEX IF NOT EXISTS idx_raw_asset_is_available
    ON hidden_gems.raw_asset (is_available);

CREATE INDEX IF NOT EXISTS idx_raw_asset_query_name
    ON hidden_gems.raw_asset (query_name);

CREATE INDEX IF NOT EXISTS idx_raw_asset_checksum
    ON hidden_gems.raw_asset (checksum_sha256);

DROP TRIGGER IF EXISTS trg_raw_asset_updated_at ON hidden_gems.raw_asset;
CREATE TRIGGER trg_raw_asset_updated_at
BEFORE UPDATE ON hidden_gems.raw_asset
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

-- =========================================================
-- 4) Comentarios (opcional pero profesional)
-- =========================================================

COMMENT ON TABLE hidden_gems.source_system IS 'Catálogo maestro de fuentes de datos del sistema.';
COMMENT ON TABLE hidden_gems.source_run IS 'Registro de ejecuciones del pipeline por fuente.';
COMMENT ON TABLE hidden_gems.raw_asset IS 'Artefactos raw generados o descargados por una ejecución.';

-- =========================================================
-- 5) Seed opcional de fuentes
--    Descomenta esto si quieres cargar las 4 fuentes base.
-- =========================================================
/*
INSERT INTO hidden_gems.source_system (
    source_code,
    source_name,
    source_type,
    description,
    base_url,
    auth_type,
    data_format_default,
    refresh_mode_default,
    supports_incremental,
    is_active
)
VALUES
(
    'google_places',
    'Google Places',
    'api',
    'Fuente dinámica principal para locales y reseñas recientes.',
    'https://maps.googleapis.com/',
    'api_key',
    'json',
    'incremental',
    TRUE,
    TRUE
),
(
    'osm_overpass',
    'OSM / Overpass',
    'api',
    'Fuente abierta para POIs y enriquecimiento espacial.',
    'https://overpass-api.de/',
    'none',
    'json',
    'full_refresh',
    TRUE,
    TRUE
),
(
    'sevilla_geo',
    'Sevilla Geo',
    'geo_dataset',
    'Capas geográficas oficiales de distritos y barrios de Sevilla.',
    NULL,
    'none',
    'geojson',
    'manual_snapshot',
    FALSE,
    TRUE
),
(
    'yelp_open_dataset',
    'Yelp Open Dataset',
    'bulk_dataset',
    'Snapshot de apoyo para NLP y pruebas de pipeline.',
    NULL,
    'none',
    'json',
    'manual_snapshot',
    FALSE,
    TRUE
)
ON CONFLICT (source_code) DO NOTHING;
*/