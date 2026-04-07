-- =========================================================
-- 04_classification_and_geo_assignment.sql
-- Clasificación y asignación geográfica:
--   - category
--   - place_category
--   - place_neighborhood_assignment
-- =========================================================

SET search_path TO hidden_gems, public;

-- =========================================================
-- 1) category
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.category (
    category_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_code       VARCHAR(100) NOT NULL,
    category_name       VARCHAR(255) NOT NULL,
    normalized_name     VARCHAR(255) NOT NULL,
    display_name        VARCHAR(255),
    description         TEXT,
    parent_category_id  UUID,
    category_level      INTEGER,
    is_food_related     BOOLEAN NOT NULL DEFAULT TRUE,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order          INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_category_parent
        FOREIGN KEY (parent_category_id)
        REFERENCES hidden_gems.category (category_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_category_code_not_blank
        CHECK (BTRIM(category_code) <> ''),

    CONSTRAINT chk_category_name_not_blank
        CHECK (BTRIM(category_name) <> ''),

    CONSTRAINT chk_category_normalized_name_not_blank
        CHECK (BTRIM(normalized_name) <> ''),

    CONSTRAINT chk_category_code_format
        CHECK (category_code ~ '^[a-z0-9_]+$'),

    CONSTRAINT chk_category_level_non_negative
        CHECK (category_level IS NULL OR category_level >= 0),

    CONSTRAINT chk_category_not_self_parent
        CHECK (parent_category_id IS NULL OR parent_category_id <> category_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_category_code
    ON hidden_gems.category (category_code);

CREATE UNIQUE INDEX IF NOT EXISTS uq_category_normalized_name
    ON hidden_gems.category (normalized_name);

CREATE INDEX IF NOT EXISTS idx_category_parent_category_id
    ON hidden_gems.category (parent_category_id);

CREATE INDEX IF NOT EXISTS idx_category_is_active
    ON hidden_gems.category (is_active);

CREATE INDEX IF NOT EXISTS idx_category_is_food_related
    ON hidden_gems.category (is_food_related);

DROP TRIGGER IF EXISTS trg_category_updated_at ON hidden_gems.category;
CREATE TRIGGER trg_category_updated_at
BEFORE UPDATE ON hidden_gems.category
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.category IS
'Taxonomía canónica interna para clasificar locales del sistema.';

COMMENT ON COLUMN hidden_gems.category.parent_category_id IS
'Relación jerárquica opcional con una categoría padre.';

-- =========================================================
-- 2) place_category
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.place_category (
    place_category_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    place_id               UUID NOT NULL,
    category_id            UUID NOT NULL,
    source_system_id       UUID,
    assignment_method      hidden_gems.assignment_method_enum NOT NULL,
    is_primary             BOOLEAN NOT NULL DEFAULT FALSE,
    assignment_confidence  NUMERIC(5,4),
    is_active              BOOLEAN NOT NULL DEFAULT TRUE,
    notes                  TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_place_category_place
        FOREIGN KEY (place_id)
        REFERENCES hidden_gems.place (place_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_place_category_category
        FOREIGN KEY (category_id)
        REFERENCES hidden_gems.category (category_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_place_category_source_system
        FOREIGN KEY (source_system_id)
        REFERENCES hidden_gems.source_system (source_system_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_place_category_confidence_range
        CHECK (
            assignment_confidence IS NULL
            OR (assignment_confidence >= 0 AND assignment_confidence <= 1)
        )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_place_category_place_category_method
    ON hidden_gems.place_category (place_id, category_id, assignment_method);

-- Solo una categoría principal activa por place
CREATE UNIQUE INDEX IF NOT EXISTS uq_place_category_one_active_primary_per_place
    ON hidden_gems.place_category (place_id)
    WHERE is_primary = TRUE AND is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_place_category_place_id
    ON hidden_gems.place_category (place_id);

CREATE INDEX IF NOT EXISTS idx_place_category_category_id
    ON hidden_gems.place_category (category_id);

CREATE INDEX IF NOT EXISTS idx_place_category_source_system_id
    ON hidden_gems.place_category (source_system_id);

CREATE INDEX IF NOT EXISTS idx_place_category_is_primary
    ON hidden_gems.place_category (is_primary);

CREATE INDEX IF NOT EXISTS idx_place_category_is_active
    ON hidden_gems.place_category (is_active);

DROP TRIGGER IF EXISTS trg_place_category_updated_at ON hidden_gems.place_category;
CREATE TRIGGER trg_place_category_updated_at
BEFORE UPDATE ON hidden_gems.place_category
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.place_category IS
'Relación entre un Place y una Category, con método de asignación y prioridad.';

COMMENT ON COLUMN hidden_gems.place_category.assignment_method IS
'Método por el que la categoría fue asignada al local.';

COMMENT ON COLUMN hidden_gems.place_category.is_primary IS
'Marca si esta es la categoría principal activa del local.';

-- =========================================================
-- 3) Refuerzo de integridad para neighborhood
--    Necesario para poder validar la coherencia entre
--    neighborhood_id y district_id en place_neighborhood_assignment
-- =========================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_neighborhood_id_district_id'
          AND connamespace = 'hidden_gems'::regnamespace
    ) THEN
        ALTER TABLE hidden_gems.neighborhood
        ADD CONSTRAINT uq_neighborhood_id_district_id
        UNIQUE (neighborhood_id, district_id);
    END IF;
END$$;

-- =========================================================
-- 4) place_neighborhood_assignment
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.place_neighborhood_assignment (
    place_neighborhood_assignment_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    place_id                          UUID NOT NULL,
    neighborhood_id                   UUID NOT NULL,
    district_id                       UUID,
    assignment_method                 hidden_gems.assignment_method_enum NOT NULL,
    assignment_confidence             NUMERIC(5,4),
    source_geometry_used              VARCHAR(50),
    distance_to_centroid_m            NUMERIC(12,2),
    is_current                        BOOLEAN NOT NULL DEFAULT TRUE,
    is_manually_verified              BOOLEAN NOT NULL DEFAULT FALSE,
    valid_from                        TIMESTAMPTZ,
    valid_to                          TIMESTAMPTZ,
    notes                             TEXT,
    created_at                        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_place_neighborhood_assignment_place
        FOREIGN KEY (place_id)
        REFERENCES hidden_gems.place (place_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_place_neighborhood_assignment_neighborhood
        FOREIGN KEY (neighborhood_id)
        REFERENCES hidden_gems.neighborhood (neighborhood_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_place_neighborhood_assignment_district
        FOREIGN KEY (district_id)
        REFERENCES hidden_gems.district (district_id)
        ON DELETE SET NULL,

    -- Si district_id viene informado, debe ser coherente con el neighborhood
    CONSTRAINT fk_place_neighborhood_assignment_neighborhood_district
        FOREIGN KEY (neighborhood_id, district_id)
        REFERENCES hidden_gems.neighborhood (neighborhood_id, district_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_place_neighborhood_assignment_confidence_range
        CHECK (
            assignment_confidence IS NULL
            OR (assignment_confidence >= 0 AND assignment_confidence <= 1)
        ),

    CONSTRAINT chk_place_neighborhood_assignment_distance_non_negative
        CHECK (
            distance_to_centroid_m IS NULL
            OR distance_to_centroid_m >= 0
        ),

    CONSTRAINT chk_place_neighborhood_assignment_valid_dates
        CHECK (
            valid_to IS NULL
            OR valid_from IS NULL
            OR valid_to >= valid_from
        )
);

-- Un solo barrio actual por place
CREATE UNIQUE INDEX IF NOT EXISTS uq_place_neighborhood_assignment_one_current_per_place
    ON hidden_gems.place_neighborhood_assignment (place_id)
    WHERE is_current = TRUE;

CREATE INDEX IF NOT EXISTS idx_place_neighborhood_assignment_place_id
    ON hidden_gems.place_neighborhood_assignment (place_id);

CREATE INDEX IF NOT EXISTS idx_place_neighborhood_assignment_neighborhood_id
    ON hidden_gems.place_neighborhood_assignment (neighborhood_id);

CREATE INDEX IF NOT EXISTS idx_place_neighborhood_assignment_district_id
    ON hidden_gems.place_neighborhood_assignment (district_id);

CREATE INDEX IF NOT EXISTS idx_place_neighborhood_assignment_method
    ON hidden_gems.place_neighborhood_assignment (assignment_method);

CREATE INDEX IF NOT EXISTS idx_place_neighborhood_assignment_is_current
    ON hidden_gems.place_neighborhood_assignment (is_current);

CREATE INDEX IF NOT EXISTS idx_place_neighborhood_assignment_is_manually_verified
    ON hidden_gems.place_neighborhood_assignment (is_manually_verified);

DROP TRIGGER IF EXISTS trg_place_neighborhood_assignment_updated_at
    ON hidden_gems.place_neighborhood_assignment;

CREATE TRIGGER trg_place_neighborhood_assignment_updated_at
BEFORE UPDATE ON hidden_gems.place_neighborhood_assignment
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.place_neighborhood_assignment IS
'Asignación geográfica entre un Place y un Neighborhood, con soporte para confianza, revisión manual e histórico.';

COMMENT ON COLUMN hidden_gems.place_neighborhood_assignment.assignment_method IS
'Método usado para asignar el local al barrio.';

COMMENT ON COLUMN hidden_gems.place_neighborhood_assignment.is_current IS
'Indica si esta es la asignación geográfica vigente del local.';

COMMENT ON COLUMN hidden_gems.place_neighborhood_assignment.is_manually_verified IS
'Indica si la asignación ha sido revisada y validada manualmente.';