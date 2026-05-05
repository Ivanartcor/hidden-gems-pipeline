-- =========================================================
-- 06_review_enrichment.sql
-- Extensión de review para Google Places Reviews y NLP futuro
-- =========================================================

SET search_path TO hidden_gems, public;

-- =========================================================
-- 1) Nuevas columnas de trazabilidad y enriquecimiento
-- =========================================================

ALTER TABLE hidden_gems.review
    ADD COLUMN IF NOT EXISTS raw_asset_id UUID,
    ADD COLUMN IF NOT EXISTS source_place_record_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS author_uri VARCHAR(500),
    ADD COLUMN IF NOT EXISTS relative_publish_time_description VARCHAR(100),
    ADD COLUMN IF NOT EXISTS source_payload_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS is_operational_review BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS is_training_eligible BOOLEAN NOT NULL DEFAULT TRUE;

-- =========================================================
-- 2) Foreign key hacia raw_asset
-- =========================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_schema = 'hidden_gems'
          AND table_name = 'review'
          AND constraint_name = 'fk_review_raw_asset'
    ) THEN
        ALTER TABLE hidden_gems.review
            ADD CONSTRAINT fk_review_raw_asset
            FOREIGN KEY (raw_asset_id)
            REFERENCES hidden_gems.raw_asset (raw_asset_id)
            ON DELETE SET NULL;
    END IF;
END;
$$;

-- =========================================================
-- 3) Constraints de calidad
-- =========================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_schema = 'hidden_gems'
          AND table_name = 'review'
          AND constraint_name = 'chk_review_source_payload_hash_format'
    ) THEN
        ALTER TABLE hidden_gems.review
            ADD CONSTRAINT chk_review_source_payload_hash_format
            CHECK (
                source_payload_hash IS NULL
                OR source_payload_hash ~ '^[0-9a-fA-F]{64}$'
            );
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_schema = 'hidden_gems'
          AND table_name = 'review'
          AND constraint_name = 'chk_review_source_place_record_id_not_blank'
    ) THEN
        ALTER TABLE hidden_gems.review
            ADD CONSTRAINT chk_review_source_place_record_id_not_blank
            CHECK (
                source_place_record_id IS NULL
                OR BTRIM(source_place_record_id) <> ''
            );
    END IF;
END;
$$;

-- =========================================================
-- 4) Índices nuevos
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_review_raw_asset_id
    ON hidden_gems.review (raw_asset_id);

CREATE INDEX IF NOT EXISTS idx_review_source_place_record_id
    ON hidden_gems.review (source_place_record_id);

CREATE INDEX IF NOT EXISTS idx_review_is_operational_review
    ON hidden_gems.review (is_operational_review);

CREATE INDEX IF NOT EXISTS idx_review_is_training_eligible
    ON hidden_gems.review (is_training_eligible);

CREATE INDEX IF NOT EXISTS idx_review_source_payload_hash
    ON hidden_gems.review (source_payload_hash);

-- =========================================================
-- 5) Unique recomendado para evitar duplicados de reviews
-- =========================================================
-- Si la fuente aporta o generamos source_review_id, esta combinación evita
-- duplicar la misma reseña del mismo local fuente.
-- Es más precisa que usar solo (source_system_id, source_review_id).

CREATE UNIQUE INDEX IF NOT EXISTS uq_review_source_place_review
    ON hidden_gems.review (
        source_system_id,
        source_place_record_id,
        source_review_id
    )
    WHERE source_place_record_id IS NOT NULL
      AND source_review_id IS NOT NULL;

-- =========================================================
-- 6) Comentarios
-- =========================================================

COMMENT ON COLUMN hidden_gems.review.raw_asset_id IS
'Artefacto raw concreto del que procede la reseña cuando aplica.';

COMMENT ON COLUMN hidden_gems.review.source_place_record_id IS
'Identificador del local en la fuente de origen. En Google Places corresponde al Google Place ID.';

COMMENT ON COLUMN hidden_gems.review.author_uri IS
'URL o URI pública del autor en la fuente, si existe.';

COMMENT ON COLUMN hidden_gems.review.relative_publish_time_description IS
'Descripción relativa de publicación entregada por la fuente, por ejemplo: hace 2 meses.';

COMMENT ON COLUMN hidden_gems.review.source_payload_hash IS
'Hash SHA-256 del payload o representación fuente de la reseña.';

COMMENT ON COLUMN hidden_gems.review.is_operational_review IS
'Indica si la reseña está asociada a un local operativo del modelo canónico.';

COMMENT ON COLUMN hidden_gems.review.is_training_eligible IS
'Indica si la reseña puede utilizarse como corpus para entrenamiento o evaluación NLP.';