-- =========================================================
-- 03_core_places.sql
-- Núcleo del dominio:
--   - place
--   - place_source_ref
--   - review
-- =========================================================

SET search_path TO hidden_gems, public;

-- =========================================================
-- 1) Función para derivar latitude/longitude desde geom_point
--    o construir geom_point desde latitude/longitude
-- =========================================================

CREATE OR REPLACE FUNCTION hidden_gems.set_place_geo_fields()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Si no viene geom_point pero sí lat/lon, construirlo
    IF NEW.geom_point IS NULL
       AND NEW.latitude IS NOT NULL
       AND NEW.longitude IS NOT NULL THEN
        NEW.geom_point := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    END IF;

    -- Si existe geom_point, derivar lat/lon
    IF NEW.geom_point IS NOT NULL THEN
        NEW.latitude  := ROUND(ST_Y(NEW.geom_point)::NUMERIC, 6);
        NEW.longitude := ROUND(ST_X(NEW.geom_point)::NUMERIC, 6);
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION hidden_gems.set_place_source_ref_geo_fields()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Si no viene source_geom_point pero sí lat/lon, construirlo
    IF NEW.source_geom_point IS NULL
       AND NEW.source_latitude IS NOT NULL
       AND NEW.source_longitude IS NOT NULL THEN
        NEW.source_geom_point := ST_SetSRID(ST_MakePoint(NEW.source_longitude, NEW.source_latitude), 4326);
    END IF;

    -- Si existe source_geom_point, derivar lat/lon
    IF NEW.source_geom_point IS NOT NULL THEN
        NEW.source_latitude  := ROUND(ST_Y(NEW.source_geom_point)::NUMERIC, 6);
        NEW.source_longitude := ROUND(ST_X(NEW.source_geom_point)::NUMERIC, 6);
    END IF;

    RETURN NEW;
END;
$$;

-- =========================================================
-- 2) Función para derivar campos técnicos en review
-- =========================================================

CREATE OR REPLACE FUNCTION hidden_gems.set_review_derived_fields()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Longitud del texto raw
    IF NEW.review_text_raw IS NOT NULL THEN
        NEW.text_length_chars := LENGTH(NEW.review_text_raw);
    END IF;

    -- Hash del autor si existe nombre raw y no viene hash
    IF NEW.author_name_hash IS NULL
       AND NEW.author_name_raw IS NOT NULL
       AND BTRIM(NEW.author_name_raw) <> '' THEN
        NEW.author_name_hash := ENCODE(
            DIGEST(LOWER(BTRIM(NEW.author_name_raw)), 'sha256'),
            'hex'
        );
    END IF;

    RETURN NEW;
END;
$$;

-- =========================================================
-- 3) place
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.place (
    place_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name       VARCHAR(255) NOT NULL,
    normalized_name      VARCHAR(255) NOT NULL,
    display_name         VARCHAR(255),
    address_text         VARCHAR(500),
    address_normalized   VARCHAR(500),
    geom_point           GEOMETRY(Point, 4326) NOT NULL,
    latitude             NUMERIC(9,6),
    longitude            NUMERIC(9,6),
    website_url          VARCHAR(500),
    phone_number         VARCHAR(50),
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    place_confidence     NUMERIC(5,4),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_place_canonical_name_not_blank
        CHECK (BTRIM(canonical_name) <> ''),

    CONSTRAINT chk_place_normalized_name_not_blank
        CHECK (BTRIM(normalized_name) <> ''),

    CONSTRAINT chk_place_geom_not_empty
        CHECK (NOT ST_IsEmpty(geom_point)),

    CONSTRAINT chk_place_geom_valid
        CHECK (ST_IsValid(geom_point)),

    CONSTRAINT chk_place_latitude_range
        CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90)),

    CONSTRAINT chk_place_longitude_range
        CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180)),

    CONSTRAINT chk_place_confidence_range
        CHECK (place_confidence IS NULL OR (place_confidence >= 0 AND place_confidence <= 1))
);

CREATE INDEX IF NOT EXISTS idx_place_is_active
    ON hidden_gems.place (is_active);

CREATE INDEX IF NOT EXISTS idx_place_updated_at
    ON hidden_gems.place (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_place_geom_point
    ON hidden_gems.place
    USING GIST (geom_point);

CREATE INDEX IF NOT EXISTS idx_place_normalized_name_trgm
    ON hidden_gems.place
    USING GIN (normalized_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_place_canonical_name_trgm
    ON hidden_gems.place
    USING GIN (canonical_name gin_trgm_ops);

DROP TRIGGER IF EXISTS trg_place_updated_at ON hidden_gems.place;
CREATE TRIGGER trg_place_updated_at
BEFORE UPDATE ON hidden_gems.place
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

DROP TRIGGER IF EXISTS trg_place_geo_fields ON hidden_gems.place;
CREATE TRIGGER trg_place_geo_fields
BEFORE INSERT OR UPDATE OF geom_point, latitude, longitude
ON hidden_gems.place
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_place_geo_fields();

COMMENT ON TABLE hidden_gems.place IS
'Entidad canónica interna que representa un local real consolidado por el sistema.';

COMMENT ON COLUMN hidden_gems.place.geom_point IS
'Punto geográfico canónico del local en SRID 4326.';

COMMENT ON COLUMN hidden_gems.place.place_confidence IS
'Confianza del sistema en la consolidación del local como entidad canónica.';

-- =========================================================
-- 4) place_source_ref
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.place_source_ref (
    place_source_ref_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    place_id                    UUID NOT NULL,
    source_system_id            UUID NOT NULL,
    source_run_id               UUID,
    raw_asset_id                UUID,
    source_entity_type          VARCHAR(50) NOT NULL,
    source_record_id            VARCHAR(255) NOT NULL,
    source_name_raw             VARCHAR(255) NOT NULL,
    source_address_raw          VARCHAR(500),
    source_geom_point           GEOMETRY(Point, 4326),
    source_latitude             NUMERIC(9,6),
    source_longitude            NUMERIC(9,6),
    source_url                  VARCHAR(500),
    source_rating               NUMERIC(3,2),
    source_review_count         INTEGER,
    source_primary_category_raw VARCHAR(255),
    source_categories_raw       JSONB,
    source_status_raw           VARCHAR(100),
    source_payload_hash         CHAR(64),
    match_method                VARCHAR(50) NOT NULL,
    match_confidence            NUMERIC(5,4),
    is_current                  BOOLEAN NOT NULL DEFAULT TRUE,
    is_deleted_in_source        BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_run_id           UUID NOT NULL,
    last_seen_run_id            UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_place_source_ref_place
        FOREIGN KEY (place_id)
        REFERENCES hidden_gems.place (place_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_place_source_ref_source_system
        FOREIGN KEY (source_system_id)
        REFERENCES hidden_gems.source_system (source_system_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_place_source_ref_source_run
        FOREIGN KEY (source_run_id)
        REFERENCES hidden_gems.source_run (source_run_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_place_source_ref_raw_asset
        FOREIGN KEY (raw_asset_id)
        REFERENCES hidden_gems.raw_asset (raw_asset_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_place_source_ref_first_seen_run
        FOREIGN KEY (first_seen_run_id)
        REFERENCES hidden_gems.source_run (source_run_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_place_source_ref_last_seen_run
        FOREIGN KEY (last_seen_run_id)
        REFERENCES hidden_gems.source_run (source_run_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_place_source_ref_entity_type_not_blank
        CHECK (BTRIM(source_entity_type) <> ''),

    CONSTRAINT chk_place_source_ref_record_id_not_blank
        CHECK (BTRIM(source_record_id) <> ''),

    CONSTRAINT chk_place_source_ref_name_not_blank
        CHECK (BTRIM(source_name_raw) <> ''),

    CONSTRAINT chk_place_source_ref_geom_valid
        CHECK (
            source_geom_point IS NULL
            OR (NOT ST_IsEmpty(source_geom_point) AND ST_IsValid(source_geom_point))
        ),

    CONSTRAINT chk_place_source_ref_latitude_range
        CHECK (source_latitude IS NULL OR (source_latitude >= -90 AND source_latitude <= 90)),

    CONSTRAINT chk_place_source_ref_longitude_range
        CHECK (source_longitude IS NULL OR (source_longitude >= -180 AND source_longitude <= 180)),

    CONSTRAINT chk_place_source_ref_rating_range
        CHECK (source_rating IS NULL OR (source_rating >= 0 AND source_rating <= 5)),

    CONSTRAINT chk_place_source_ref_review_count_non_negative
        CHECK (source_review_count IS NULL OR source_review_count >= 0),

    CONSTRAINT chk_place_source_ref_payload_hash_format
        CHECK (
            source_payload_hash IS NULL
            OR source_payload_hash ~ '^[0-9a-fA-F]{64}$'
        ),

    CONSTRAINT chk_place_source_ref_match_confidence_range
        CHECK (match_confidence IS NULL OR (match_confidence >= 0 AND match_confidence <= 1)),

    CONSTRAINT uq_place_source_ref_source_record
        UNIQUE (source_system_id, source_entity_type, source_record_id),

    CONSTRAINT uq_place_source_ref_id_place
        UNIQUE (place_source_ref_id, place_id)
);

CREATE INDEX IF NOT EXISTS idx_place_source_ref_place_id
    ON hidden_gems.place_source_ref (place_id);

CREATE INDEX IF NOT EXISTS idx_place_source_ref_source_system_id
    ON hidden_gems.place_source_ref (source_system_id);

CREATE INDEX IF NOT EXISTS idx_place_source_ref_source_run_id
    ON hidden_gems.place_source_ref (source_run_id);

CREATE INDEX IF NOT EXISTS idx_place_source_ref_first_seen_run_id
    ON hidden_gems.place_source_ref (first_seen_run_id);

CREATE INDEX IF NOT EXISTS idx_place_source_ref_last_seen_run_id
    ON hidden_gems.place_source_ref (last_seen_run_id);

CREATE INDEX IF NOT EXISTS idx_place_source_ref_is_current
    ON hidden_gems.place_source_ref (is_current);

CREATE INDEX IF NOT EXISTS idx_place_source_ref_source_geom_point
    ON hidden_gems.place_source_ref
    USING GIST (source_geom_point);

CREATE INDEX IF NOT EXISTS idx_place_source_ref_source_name_raw_trgm
    ON hidden_gems.place_source_ref
    USING GIN (source_name_raw gin_trgm_ops);

DROP TRIGGER IF EXISTS trg_place_source_ref_updated_at ON hidden_gems.place_source_ref;
CREATE TRIGGER trg_place_source_ref_updated_at
BEFORE UPDATE ON hidden_gems.place_source_ref
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

DROP TRIGGER IF EXISTS trg_place_source_ref_geo_fields ON hidden_gems.place_source_ref;
CREATE TRIGGER trg_place_source_ref_geo_fields
BEFORE INSERT OR UPDATE OF source_geom_point, source_latitude, source_longitude
ON hidden_gems.place_source_ref
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_place_source_ref_geo_fields();

COMMENT ON TABLE hidden_gems.place_source_ref IS
'Representación de un local canónico en una fuente externa concreta.';

COMMENT ON COLUMN hidden_gems.place_source_ref.source_record_id IS
'Identificador externo del registro en la fuente.';

COMMENT ON COLUMN hidden_gems.place_source_ref.match_method IS
'Método de vinculación entre el registro fuente y el Place canónico.';

COMMENT ON COLUMN hidden_gems.place_source_ref.match_confidence IS
'Confianza del matching entre el registro fuente y el Place canónico.';

-- =========================================================
-- 5) review
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.review (
    review_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    place_id                 UUID NOT NULL,
    place_source_ref_id      UUID,
    source_system_id         UUID NOT NULL,
    source_run_id            UUID,
    source_review_id         VARCHAR(255),
    author_name_raw          VARCHAR(255),
    author_name_hash         CHAR(64),
    rating_value             NUMERIC(3,2),
    review_title             VARCHAR(255),
    review_text_raw          TEXT NOT NULL,
    review_text_normalized   TEXT,
    review_language          VARCHAR(10),
    review_created_at        TIMESTAMPTZ,
    review_updated_at        TIMESTAMPTZ,
    source_review_url        VARCHAR(500),
    helpful_count            INTEGER,
    translated_text          TEXT,
    text_length_chars        INTEGER,
    is_active                BOOLEAN NOT NULL DEFAULT TRUE,
    is_deleted_in_source     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_review_place
        FOREIGN KEY (place_id)
        REFERENCES hidden_gems.place (place_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_review_place_source_ref
        FOREIGN KEY (place_source_ref_id, place_id)
        REFERENCES hidden_gems.place_source_ref (place_source_ref_id, place_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_review_source_system
        FOREIGN KEY (source_system_id)
        REFERENCES hidden_gems.source_system (source_system_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_review_source_run
        FOREIGN KEY (source_run_id)
        REFERENCES hidden_gems.source_run (source_run_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_review_text_raw_not_blank
        CHECK (BTRIM(review_text_raw) <> ''),

    CONSTRAINT chk_review_rating_range
        CHECK (rating_value IS NULL OR (rating_value >= 0 AND rating_value <= 5)),

    CONSTRAINT chk_review_helpful_count_non_negative
        CHECK (helpful_count IS NULL OR helpful_count >= 0),

    CONSTRAINT chk_review_text_length_non_negative
        CHECK (text_length_chars IS NULL OR text_length_chars >= 0),

    CONSTRAINT chk_review_author_name_hash_format
        CHECK (
            author_name_hash IS NULL
            OR author_name_hash ~ '^[0-9a-fA-F]{64}$'
        ),

    CONSTRAINT chk_review_dates_order
        CHECK (
            review_updated_at IS NULL
            OR review_created_at IS NULL
            OR review_updated_at >= review_created_at
        )
);

-- Unique parcial: solo si la fuente aporta source_review_id
CREATE UNIQUE INDEX IF NOT EXISTS uq_review_source_review_id
    ON hidden_gems.review (source_system_id, source_review_id)
    WHERE source_review_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_review_place_id
    ON hidden_gems.review (place_id);

CREATE INDEX IF NOT EXISTS idx_review_place_source_ref_id
    ON hidden_gems.review (place_source_ref_id);

CREATE INDEX IF NOT EXISTS idx_review_source_system_id
    ON hidden_gems.review (source_system_id);

CREATE INDEX IF NOT EXISTS idx_review_source_run_id
    ON hidden_gems.review (source_run_id);

CREATE INDEX IF NOT EXISTS idx_review_review_created_at
    ON hidden_gems.review (review_created_at DESC);

CREATE INDEX IF NOT EXISTS idx_review_is_active
    ON hidden_gems.review (is_active);

CREATE INDEX IF NOT EXISTS idx_review_language
    ON hidden_gems.review (review_language);

CREATE INDEX IF NOT EXISTS idx_review_text_raw_fts
    ON hidden_gems.review
    USING GIN (to_tsvector('simple', coalesce(review_text_raw, '')));

DROP TRIGGER IF EXISTS trg_review_updated_at ON hidden_gems.review;
CREATE TRIGGER trg_review_updated_at
BEFORE UPDATE ON hidden_gems.review
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

DROP TRIGGER IF EXISTS trg_review_derived_fields ON hidden_gems.review;
CREATE TRIGGER trg_review_derived_fields
BEFORE INSERT OR UPDATE OF review_text_raw, author_name_raw
ON hidden_gems.review
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_review_derived_fields();

COMMENT ON TABLE hidden_gems.review IS
'Reseña textual individual asociada a un Place y a una fuente concreta.';

COMMENT ON COLUMN hidden_gems.review.review_text_raw IS
'Texto original de la reseña tal y como llega desde la fuente.';

COMMENT ON COLUMN hidden_gems.review.review_text_normalized IS
'Versión normalizada del texto para procesos técnicos, sin sustituir al raw.';

COMMENT ON COLUMN hidden_gems.review.author_name_hash IS
'Hash SHA-256 del nombre del autor para trazabilidad sin depender del valor raw.';