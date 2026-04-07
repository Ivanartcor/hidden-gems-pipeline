-- =========================================================
-- 02_geo_reference.sql
-- Tablas de referencia geográfica:
--   - district
--   - neighborhood
-- =========================================================

SET search_path TO hidden_gems, public;

-- =========================================================
-- 1) Función para derivar centroid_point y area_m2
-- =========================================================

CREATE OR REPLACE FUNCTION hidden_gems.set_geo_derived_fields()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.geometry IS NOT NULL THEN
        NEW.centroid_point := ST_Centroid(NEW.geometry);
        NEW.area_m2 := ROUND(ST_Area(NEW.geometry::geography)::NUMERIC, 2);
    END IF;

    RETURN NEW;
END;
$$;

-- =========================================================
-- 2) district
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.district (
    district_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    official_code     VARCHAR(100),
    official_name     VARCHAR(255) NOT NULL,
    normalized_name   VARCHAR(255) NOT NULL,
    display_name      VARCHAR(255),
    geometry          GEOMETRY(MultiPolygon, 4326) NOT NULL,
    centroid_point    GEOMETRY(Point, 4326),
    area_m2           NUMERIC(15,2),
    alias_names       JSONB,
    source_version    VARCHAR(100),
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_district_official_name_not_blank
        CHECK (BTRIM(official_name) <> ''),

    CONSTRAINT chk_district_normalized_name_not_blank
        CHECK (BTRIM(normalized_name) <> ''),

    CONSTRAINT chk_district_area_positive
        CHECK (area_m2 IS NULL OR area_m2 > 0),

    CONSTRAINT chk_district_geometry_not_empty
        CHECK (NOT ST_IsEmpty(geometry)),

    CONSTRAINT chk_district_geometry_valid
        CHECK (ST_IsValid(geometry))
);

-- Unique parcial sobre official_code, solo si existe
CREATE UNIQUE INDEX IF NOT EXISTS uq_district_official_code
    ON hidden_gems.district (official_code)
    WHERE official_code IS NOT NULL;

-- Nombres normalizados únicos a nivel distrito
CREATE UNIQUE INDEX IF NOT EXISTS uq_district_normalized_name
    ON hidden_gems.district (normalized_name);

CREATE INDEX IF NOT EXISTS idx_district_is_active
    ON hidden_gems.district (is_active);

CREATE INDEX IF NOT EXISTS idx_district_official_name
    ON hidden_gems.district (official_name);

CREATE INDEX IF NOT EXISTS idx_district_centroid_point
    ON hidden_gems.district
    USING GIST (centroid_point);

CREATE INDEX IF NOT EXISTS idx_district_geometry
    ON hidden_gems.district
    USING GIST (geometry);

DROP TRIGGER IF EXISTS trg_district_updated_at ON hidden_gems.district;
CREATE TRIGGER trg_district_updated_at
BEFORE UPDATE ON hidden_gems.district
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

DROP TRIGGER IF EXISTS trg_district_geo_derived_fields ON hidden_gems.district;
CREATE TRIGGER trg_district_geo_derived_fields
BEFORE INSERT OR UPDATE OF geometry
ON hidden_gems.district
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_geo_derived_fields();

COMMENT ON TABLE hidden_gems.district IS
'Entidad maestra geográfica de nivel distrito para Sevilla.';

COMMENT ON COLUMN hidden_gems.district.geometry IS
'Geometría oficial del distrito en SRID 4326.';

COMMENT ON COLUMN hidden_gems.district.centroid_point IS
'Centroide geométrico derivado automáticamente desde la geometría.';

COMMENT ON COLUMN hidden_gems.district.area_m2 IS
'Área del distrito en metros cuadrados, derivada automáticamente desde la geometría.';

-- =========================================================
-- 3) neighborhood
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.neighborhood (
    neighborhood_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    district_id       UUID NOT NULL,
    official_code     VARCHAR(100),
    official_name     VARCHAR(255) NOT NULL,
    normalized_name   VARCHAR(255) NOT NULL,
    display_name      VARCHAR(255),
    geometry          GEOMETRY(MultiPolygon, 4326) NOT NULL,
    centroid_point    GEOMETRY(Point, 4326),
    area_m2           NUMERIC(15,2),
    alias_names       JSONB,
    source_version    VARCHAR(100),
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_neighborhood_district
        FOREIGN KEY (district_id)
        REFERENCES hidden_gems.district (district_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_neighborhood_official_name_not_blank
        CHECK (BTRIM(official_name) <> ''),

    CONSTRAINT chk_neighborhood_normalized_name_not_blank
        CHECK (BTRIM(normalized_name) <> ''),

    CONSTRAINT chk_neighborhood_area_positive
        CHECK (area_m2 IS NULL OR area_m2 > 0),

    CONSTRAINT chk_neighborhood_geometry_not_empty
        CHECK (NOT ST_IsEmpty(geometry)),

    CONSTRAINT chk_neighborhood_geometry_valid
        CHECK (ST_IsValid(geometry))
);

-- Unique parcial sobre official_code, solo si existe
CREATE UNIQUE INDEX IF NOT EXISTS uq_neighborhood_official_code
    ON hidden_gems.neighborhood (official_code)
    WHERE official_code IS NOT NULL;

-- Nombre normalizado único dentro del distrito
CREATE UNIQUE INDEX IF NOT EXISTS uq_neighborhood_district_normalized_name
    ON hidden_gems.neighborhood (district_id, normalized_name);

CREATE INDEX IF NOT EXISTS idx_neighborhood_district_id
    ON hidden_gems.neighborhood (district_id);

CREATE INDEX IF NOT EXISTS idx_neighborhood_is_active
    ON hidden_gems.neighborhood (is_active);

CREATE INDEX IF NOT EXISTS idx_neighborhood_official_name
    ON hidden_gems.neighborhood (official_name);

CREATE INDEX IF NOT EXISTS idx_neighborhood_centroid_point
    ON hidden_gems.neighborhood
    USING GIST (centroid_point);

CREATE INDEX IF NOT EXISTS idx_neighborhood_geometry
    ON hidden_gems.neighborhood
    USING GIST (geometry);

DROP TRIGGER IF EXISTS trg_neighborhood_updated_at ON hidden_gems.neighborhood;
CREATE TRIGGER trg_neighborhood_updated_at
BEFORE UPDATE ON hidden_gems.neighborhood
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

DROP TRIGGER IF EXISTS trg_neighborhood_geo_derived_fields ON hidden_gems.neighborhood;
CREATE TRIGGER trg_neighborhood_geo_derived_fields
BEFORE INSERT OR UPDATE OF geometry
ON hidden_gems.neighborhood
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_geo_derived_fields();

COMMENT ON TABLE hidden_gems.neighborhood IS
'Entidad maestra geográfica de nivel barrio para Sevilla.';

COMMENT ON COLUMN hidden_gems.neighborhood.district_id IS
'FK al distrito oficial al que pertenece el barrio.';

COMMENT ON COLUMN hidden_gems.neighborhood.geometry IS
'Geometría oficial del barrio en SRID 4326.';

COMMENT ON COLUMN hidden_gems.neighborhood.centroid_point IS
'Centroide geométrico derivado automáticamente desde la geometría.';

COMMENT ON COLUMN hidden_gems.neighborhood.area_m2 IS
'Área del barrio en metros cuadrados, derivada automáticamente desde la geometría.';