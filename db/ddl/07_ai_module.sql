-- =========================================================
-- 07_ai_module.sql
-- Capa IA para Hidden Gems:
--   - ai_model_version
--   - ai_pipeline_run
--   - dish
--   - dish_alias
--   - dish_mention
--   - dish_mention_sentiment
--   - dish_place_signal
--   - hidden_gem_candidate
-- =========================================================

SET search_path TO hidden_gems, public;

-- =========================================================
-- 0) Refuerzos de integridad necesarios para la capa IA
-- =========================================================
-- Permite validar que dish_mention.place_id coincide con el place_id
-- de la review referenciada.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_review_id_place_id_for_ai'
          AND connamespace = 'hidden_gems'::regnamespace
    ) THEN
        ALTER TABLE hidden_gems.review
        ADD CONSTRAINT uq_review_id_place_id_for_ai
        UNIQUE (review_id, place_id);
    END IF;
END$$;

-- =========================================================
-- 1) ai_model_version
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.ai_model_version (
    ai_model_version_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_code             VARCHAR(150) NOT NULL UNIQUE,
    model_name             VARCHAR(255) NOT NULL,
    model_type             VARCHAR(50) NOT NULL,
    task_name              VARCHAR(100) NOT NULL,
    version_label          VARCHAR(50) NOT NULL,
    description            TEXT,
    framework_name         VARCHAR(100),
    base_model_name        VARCHAR(255),
    language_scope         VARCHAR(50),
    training_dataset_name  VARCHAR(255),
    training_artifact_path TEXT,
    metrics_json           JSONB NOT NULL DEFAULT '{}'::jsonb,
    config_json            JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_ai_model_version_model_code_not_blank
        CHECK (BTRIM(model_code) <> ''),

    CONSTRAINT chk_ai_model_version_model_code_format
        CHECK (model_code ~ '^[a-z0-9_]+$'),

    CONSTRAINT chk_ai_model_version_model_name_not_blank
        CHECK (BTRIM(model_name) <> ''),

    CONSTRAINT chk_ai_model_version_type_allowed
        CHECK (
            model_type IN (
                'transformer',
                'rule_based',
                'hybrid',
                'aggregation',
                'ranking',
                'embedding',
                'manual'
            )
        ),

    CONSTRAINT chk_ai_model_version_task_allowed
        CHECK (
            task_name IN (
                'dish_detection',
                'dish_normalization',
                'mention_sentiment',
                'signal_aggregation',
                'hidden_gems_ranking',
                'manual_review',
                'other'
            )
        ),

    CONSTRAINT chk_ai_model_version_version_label_not_blank
        CHECK (BTRIM(version_label) <> ''),

    CONSTRAINT chk_ai_model_version_metrics_is_object
        CHECK (jsonb_typeof(metrics_json) = 'object'),

    CONSTRAINT chk_ai_model_version_config_is_object
        CHECK (jsonb_typeof(config_json) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_ai_model_version_task_name
    ON hidden_gems.ai_model_version (task_name);

CREATE INDEX IF NOT EXISTS idx_ai_model_version_model_type
    ON hidden_gems.ai_model_version (model_type);

CREATE INDEX IF NOT EXISTS idx_ai_model_version_is_active
    ON hidden_gems.ai_model_version (is_active);

DROP TRIGGER IF EXISTS trg_ai_model_version_updated_at ON hidden_gems.ai_model_version;
CREATE TRIGGER trg_ai_model_version_updated_at
BEFORE UPDATE ON hidden_gems.ai_model_version
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.ai_model_version IS
'Registro versionado de modelos, reglas y métodos IA utilizados por Hidden Gems.';

COMMENT ON COLUMN hidden_gems.ai_model_version.model_code IS
'Código estable en snake_case de la versión del modelo o método IA.';

COMMENT ON COLUMN hidden_gems.ai_model_version.model_type IS
'Tipo técnico del método: transformer, rule_based, hybrid, aggregation, ranking, embedding o manual.';

COMMENT ON COLUMN hidden_gems.ai_model_version.task_name IS
'Tarea cubierta por el modelo o método: detección de platos, normalización, sentimiento, agregación o ranking.';

-- =========================================================
-- 2) ai_pipeline_run
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.ai_pipeline_run (
    ai_pipeline_run_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_code              VARCHAR(150) NOT NULL UNIQUE,
    run_type              VARCHAR(50) NOT NULL,
    status                hidden_gems.run_status_enum NOT NULL DEFAULT 'pending',
    started_at            TIMESTAMPTZ,
    finished_at           TIMESTAMPTZ,
    duration_seconds      INTEGER,
    parent_ai_run_id      UUID,
    source_run_id         UUID,
    input_artifacts_json  JSONB NOT NULL DEFAULT '[]'::jsonb,
    output_artifacts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    config_json           JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics_json          JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes                 TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ai_pipeline_run_parent
        FOREIGN KEY (parent_ai_run_id)
        REFERENCES hidden_gems.ai_pipeline_run (ai_pipeline_run_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_ai_pipeline_run_source_run
        FOREIGN KEY (source_run_id)
        REFERENCES hidden_gems.source_run (source_run_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_ai_pipeline_run_code_not_blank
        CHECK (BTRIM(run_code) <> ''),

    CONSTRAINT chk_ai_pipeline_run_code_format
        CHECK (run_code ~ '^[a-z0-9_]+$'),

    CONSTRAINT chk_ai_pipeline_run_type_allowed
        CHECK (
            run_type IN (
                'dish_detection',
                'dish_normalization',
                'mention_sentiment',
                'signal_aggregation',
                'hidden_gems_ranking',
                'full_ai_pipeline',
                'manual_import',
                'artifact_import',
                'other'
            )
        ),

    CONSTRAINT chk_ai_pipeline_run_duration_non_negative
        CHECK (duration_seconds IS NULL OR duration_seconds >= 0),

    CONSTRAINT chk_ai_pipeline_run_finished_after_started
        CHECK (
            finished_at IS NULL
            OR started_at IS NULL
            OR finished_at >= started_at
        ),

    CONSTRAINT chk_ai_pipeline_run_input_artifacts_array
        CHECK (jsonb_typeof(input_artifacts_json) = 'array'),

    CONSTRAINT chk_ai_pipeline_run_output_artifacts_array
        CHECK (jsonb_typeof(output_artifacts_json) = 'array'),

    CONSTRAINT chk_ai_pipeline_run_config_object
        CHECK (jsonb_typeof(config_json) = 'object'),

    CONSTRAINT chk_ai_pipeline_run_metrics_object
        CHECK (jsonb_typeof(metrics_json) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_ai_pipeline_run_type
    ON hidden_gems.ai_pipeline_run (run_type);

CREATE INDEX IF NOT EXISTS idx_ai_pipeline_run_status
    ON hidden_gems.ai_pipeline_run (status);

CREATE INDEX IF NOT EXISTS idx_ai_pipeline_run_started_at
    ON hidden_gems.ai_pipeline_run (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_pipeline_run_parent_ai_run_id
    ON hidden_gems.ai_pipeline_run (parent_ai_run_id);

CREATE INDEX IF NOT EXISTS idx_ai_pipeline_run_source_run_id
    ON hidden_gems.ai_pipeline_run (source_run_id);

DROP TRIGGER IF EXISTS trg_ai_pipeline_run_updated_at ON hidden_gems.ai_pipeline_run;
CREATE TRIGGER trg_ai_pipeline_run_updated_at
BEFORE UPDATE ON hidden_gems.ai_pipeline_run
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.ai_pipeline_run IS
'Ejecución trazable de un proceso IA o de una fase del módulo IA de Hidden Gems.';

COMMENT ON COLUMN hidden_gems.ai_pipeline_run.source_run_id IS
'Ejecución de ingesta fuente asociada cuando el procesamiento IA deriva directamente de una extracción externa.';

COMMENT ON COLUMN hidden_gems.ai_pipeline_run.input_artifacts_json IS
'Lista JSON de artefactos de entrada utilizados por la ejecución IA.';

COMMENT ON COLUMN hidden_gems.ai_pipeline_run.output_artifacts_json IS
'Lista JSON de artefactos generados por la ejecución IA.';

-- =========================================================
-- 3) dish
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.dish (
    dish_id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dish_code                VARCHAR(150) NOT NULL UNIQUE,
    canonical_name           VARCHAR(255) NOT NULL,
    normalized_name          VARCHAR(255) NOT NULL,
    display_name             VARCHAR(255),
    language_code            VARCHAR(10) NOT NULL DEFAULT 'en',
    dish_family              VARCHAR(100),
    description              TEXT,
    source_ai_run_id         UUID,
    source_model_version_id  UUID,
    is_active                BOOLEAN NOT NULL DEFAULT TRUE,
    is_reviewed              BOOLEAN NOT NULL DEFAULT FALSE,
    review_status            VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_dish_source_ai_run
        FOREIGN KEY (source_ai_run_id)
        REFERENCES hidden_gems.ai_pipeline_run (ai_pipeline_run_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_dish_source_model_version
        FOREIGN KEY (source_model_version_id)
        REFERENCES hidden_gems.ai_model_version (ai_model_version_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_dish_code_not_blank
        CHECK (BTRIM(dish_code) <> ''),

    CONSTRAINT chk_dish_code_format
        CHECK (dish_code ~ '^[a-z0-9_]+$'),

    CONSTRAINT chk_dish_canonical_name_not_blank
        CHECK (BTRIM(canonical_name) <> ''),

    CONSTRAINT chk_dish_normalized_name_not_blank
        CHECK (BTRIM(normalized_name) <> ''),

    CONSTRAINT chk_dish_language_code_not_blank
        CHECK (BTRIM(language_code) <> ''),

    CONSTRAINT chk_dish_review_status_allowed
        CHECK (
            review_status IN (
                'pending',
                'approved',
                'rejected',
                'needs_merge',
                'needs_split'
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_dish_normalized_name
    ON hidden_gems.dish (normalized_name);

CREATE INDEX IF NOT EXISTS idx_dish_language_code
    ON hidden_gems.dish (language_code);

CREATE INDEX IF NOT EXISTS idx_dish_is_active
    ON hidden_gems.dish (is_active);

CREATE INDEX IF NOT EXISTS idx_dish_review_status
    ON hidden_gems.dish (review_status);

CREATE INDEX IF NOT EXISTS idx_dish_source_ai_run_id
    ON hidden_gems.dish (source_ai_run_id);

CREATE INDEX IF NOT EXISTS idx_dish_source_model_version_id
    ON hidden_gems.dish (source_model_version_id);

CREATE INDEX IF NOT EXISTS idx_dish_normalized_name_trgm
    ON hidden_gems.dish
    USING GIN (normalized_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_dish_canonical_name_trgm
    ON hidden_gems.dish
    USING GIN (canonical_name gin_trgm_ops);

DROP TRIGGER IF EXISTS trg_dish_updated_at ON hidden_gems.dish;
CREATE TRIGGER trg_dish_updated_at
BEFORE UPDATE ON hidden_gems.dish
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.dish IS
'Catálogo canónico interno de platos detectados o mantenidos por Hidden Gems.';

COMMENT ON COLUMN hidden_gems.dish.dish_code IS
'Código técnico estable del plato en snake_case.';

COMMENT ON COLUMN hidden_gems.dish.normalized_name IS
'Nombre normalizado utilizado para matching, búsqueda y agrupación.';

-- =========================================================
-- 4) dish_alias
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.dish_alias (
    dish_alias_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dish_id                 UUID NOT NULL,
    alias_text              VARCHAR(255) NOT NULL,
    alias_normalized        VARCHAR(255) NOT NULL,
    alias_language_code     VARCHAR(10) NOT NULL DEFAULT 'en',
    alias_type              VARCHAR(50) NOT NULL,
    alias_source            VARCHAR(100),
    mention_count           INTEGER,
    review_count            INTEGER,
    business_count          INTEGER,
    avg_confidence          NUMERIC(6,5),
    source_ai_run_id        UUID,
    source_model_version_id UUID,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_reviewed             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_dish_alias_dish
        FOREIGN KEY (dish_id)
        REFERENCES hidden_gems.dish (dish_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_dish_alias_source_ai_run
        FOREIGN KEY (source_ai_run_id)
        REFERENCES hidden_gems.ai_pipeline_run (ai_pipeline_run_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_dish_alias_source_model_version
        FOREIGN KEY (source_model_version_id)
        REFERENCES hidden_gems.ai_model_version (ai_model_version_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_dish_alias_text_not_blank
        CHECK (BTRIM(alias_text) <> ''),

    CONSTRAINT chk_dish_alias_normalized_not_blank
        CHECK (BTRIM(alias_normalized) <> ''),

    CONSTRAINT chk_dish_alias_language_code_not_blank
        CHECK (BTRIM(alias_language_code) <> ''),

    CONSTRAINT chk_dish_alias_type_allowed
        CHECK (
            alias_type IN (
                'canonical',
                'surface_variant',
                'translation',
                'manual_alias',
                'synonym',
                'misspelling'
            )
        ),

    CONSTRAINT chk_dish_alias_counts_non_negative
        CHECK (
            (mention_count IS NULL OR mention_count >= 0)
            AND (review_count IS NULL OR review_count >= 0)
            AND (business_count IS NULL OR business_count >= 0)
        ),

    CONSTRAINT chk_dish_alias_avg_confidence_range
        CHECK (avg_confidence IS NULL OR (avg_confidence >= 0 AND avg_confidence <= 1)),

    CONSTRAINT uq_dish_alias_dish_alias_language
        UNIQUE (dish_id, alias_normalized, alias_language_code)
);

CREATE INDEX IF NOT EXISTS idx_dish_alias_dish_id
    ON hidden_gems.dish_alias (dish_id);

CREATE INDEX IF NOT EXISTS idx_dish_alias_alias_normalized
    ON hidden_gems.dish_alias (alias_normalized);

CREATE INDEX IF NOT EXISTS idx_dish_alias_language_code
    ON hidden_gems.dish_alias (alias_language_code);

CREATE INDEX IF NOT EXISTS idx_dish_alias_type
    ON hidden_gems.dish_alias (alias_type);

CREATE INDEX IF NOT EXISTS idx_dish_alias_is_active
    ON hidden_gems.dish_alias (is_active);

CREATE INDEX IF NOT EXISTS idx_dish_alias_source_ai_run_id
    ON hidden_gems.dish_alias (source_ai_run_id);

CREATE INDEX IF NOT EXISTS idx_dish_alias_source_model_version_id
    ON hidden_gems.dish_alias (source_model_version_id);

CREATE INDEX IF NOT EXISTS idx_dish_alias_alias_normalized_trgm
    ON hidden_gems.dish_alias
    USING GIN (alias_normalized gin_trgm_ops);

DROP TRIGGER IF EXISTS trg_dish_alias_updated_at ON hidden_gems.dish_alias;
CREATE TRIGGER trg_dish_alias_updated_at
BEFORE UPDATE ON hidden_gems.dish_alias
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.dish_alias IS
'Variantes textuales, traducciones o alias que apuntan a un plato canónico.';

COMMENT ON COLUMN hidden_gems.dish_alias.alias_type IS
'Tipo de alias: canonical, surface_variant, translation, manual_alias, synonym o misspelling.';

-- =========================================================
-- 5) dish_mention
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.dish_mention (
    dish_mention_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id                UUID NOT NULL,
    place_id                 UUID NOT NULL,
    dish_id                  UUID,
    dish_alias_id            UUID,
    ai_pipeline_run_id       UUID NOT NULL,
    model_version_id         UUID,
    mention_text             TEXT NOT NULL,
    mention_normalized       VARCHAR(255),
    start_char               INTEGER,
    end_char                 INTEGER,
    start_token              INTEGER,
    end_token                INTEGER,
    token_count              INTEGER,
    ner_confidence_mean      NUMERIC(6,5),
    ner_confidence_min       NUMERIC(6,5),
    ner_confidence_max       NUMERIC(6,5),
    normalization_status     VARCHAR(50),
    normalization_method     VARCHAR(100),
    normalization_confidence NUMERIC(6,5),
    is_active                BOOLEAN NOT NULL DEFAULT TRUE,
    human_review_status      VARCHAR(50) NOT NULL DEFAULT 'not_reviewed',
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_dish_mention_review_place
        FOREIGN KEY (review_id, place_id)
        REFERENCES hidden_gems.review (review_id, place_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_dish_mention_place
        FOREIGN KEY (place_id)
        REFERENCES hidden_gems.place (place_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_dish_mention_dish
        FOREIGN KEY (dish_id)
        REFERENCES hidden_gems.dish (dish_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_dish_mention_dish_alias
        FOREIGN KEY (dish_alias_id)
        REFERENCES hidden_gems.dish_alias (dish_alias_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_dish_mention_ai_pipeline_run
        FOREIGN KEY (ai_pipeline_run_id)
        REFERENCES hidden_gems.ai_pipeline_run (ai_pipeline_run_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_dish_mention_model_version
        FOREIGN KEY (model_version_id)
        REFERENCES hidden_gems.ai_model_version (ai_model_version_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_dish_mention_text_not_blank
        CHECK (BTRIM(mention_text) <> ''),

    CONSTRAINT chk_dish_mention_char_offsets
        CHECK (
            start_char IS NULL
            OR end_char IS NULL
            OR (start_char >= 0 AND end_char >= start_char)
        ),

    CONSTRAINT chk_dish_mention_token_offsets
        CHECK (
            start_token IS NULL
            OR end_token IS NULL
            OR (start_token >= 0 AND end_token >= start_token)
        ),

    CONSTRAINT chk_dish_mention_token_count_non_negative
        CHECK (token_count IS NULL OR token_count >= 0),

    CONSTRAINT chk_dish_mention_ner_confidence_range
        CHECK (
            (ner_confidence_mean IS NULL OR (ner_confidence_mean >= 0 AND ner_confidence_mean <= 1))
            AND (ner_confidence_min IS NULL OR (ner_confidence_min >= 0 AND ner_confidence_min <= 1))
            AND (ner_confidence_max IS NULL OR (ner_confidence_max >= 0 AND ner_confidence_max <= 1))
        ),

    CONSTRAINT chk_dish_mention_ner_confidence_order
        CHECK (
            ner_confidence_min IS NULL
            OR ner_confidence_max IS NULL
            OR ner_confidence_max >= ner_confidence_min
        ),

    CONSTRAINT chk_dish_mention_normalization_confidence_range
        CHECK (normalization_confidence IS NULL OR (normalization_confidence >= 0 AND normalization_confidence <= 1)),

    CONSTRAINT chk_dish_mention_normalization_status_allowed
        CHECK (
            normalization_status IS NULL
            OR normalization_status IN (
                'normalized_rule_based_v1',
                'normalized_rule_based_v2',
                'normalized_model_based',
                'excluded_or_pending_review',
                'excluded_or_pending_review_v2',
                'manual_normalized',
                'unknown'
            )
        ),

    CONSTRAINT chk_dish_mention_human_review_status_allowed
        CHECK (
            human_review_status IN (
                'not_reviewed',
                'pending',
                'approved',
                'rejected',
                'corrected'
            )
        ),

    CONSTRAINT uq_dish_mention_review_offsets_run
        UNIQUE (review_id, start_char, end_char, mention_normalized, ai_pipeline_run_id)
);

CREATE INDEX IF NOT EXISTS idx_dish_mention_review_id
    ON hidden_gems.dish_mention (review_id);

CREATE INDEX IF NOT EXISTS idx_dish_mention_place_id
    ON hidden_gems.dish_mention (place_id);

CREATE INDEX IF NOT EXISTS idx_dish_mention_dish_id
    ON hidden_gems.dish_mention (dish_id);

CREATE INDEX IF NOT EXISTS idx_dish_mention_dish_alias_id
    ON hidden_gems.dish_mention (dish_alias_id);

CREATE INDEX IF NOT EXISTS idx_dish_mention_ai_pipeline_run_id
    ON hidden_gems.dish_mention (ai_pipeline_run_id);

CREATE INDEX IF NOT EXISTS idx_dish_mention_model_version_id
    ON hidden_gems.dish_mention (model_version_id);

CREATE INDEX IF NOT EXISTS idx_dish_mention_place_dish
    ON hidden_gems.dish_mention (place_id, dish_id);

CREATE INDEX IF NOT EXISTS idx_dish_mention_review_dish
    ON hidden_gems.dish_mention (review_id, dish_id);

CREATE INDEX IF NOT EXISTS idx_dish_mention_normalization_status
    ON hidden_gems.dish_mention (normalization_status);

CREATE INDEX IF NOT EXISTS idx_dish_mention_human_review_status
    ON hidden_gems.dish_mention (human_review_status);

CREATE INDEX IF NOT EXISTS idx_dish_mention_mention_normalized_trgm
    ON hidden_gems.dish_mention
    USING GIN (mention_normalized gin_trgm_ops);

DROP TRIGGER IF EXISTS trg_dish_mention_updated_at ON hidden_gems.dish_mention;
CREATE TRIGGER trg_dish_mention_updated_at
BEFORE UPDATE ON hidden_gems.dish_mention
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.dish_mention IS
'Mención concreta de un plato detectada dentro de una review.';

COMMENT ON COLUMN hidden_gems.dish_mention.place_id IS
'Place canónico asociado a la review. Se mantiene redundante para acelerar agregaciones place + dish.';

COMMENT ON COLUMN hidden_gems.dish_mention.ai_pipeline_run_id IS
'Ejecución IA que generó la mención.';

-- =========================================================
-- 6) dish_mention_sentiment
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.dish_mention_sentiment (
    dish_mention_sentiment_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dish_mention_id            UUID NOT NULL,
    ai_pipeline_run_id         UUID NOT NULL,
    model_version_id           UUID,
    sentiment_label            VARCHAR(20) NOT NULL,
    sentiment_score            NUMERIC(8,5),
    sentiment_confidence       NUMERIC(6,5),
    sentiment_reliability_tier VARCHAR(20),
    sentiment_reason           VARCHAR(100),
    sentiment_method           VARCHAR(100) NOT NULL,
    context_sentence           TEXT,
    context_window             TEXT,
    target_clause_context      TEXT,
    near_mention_context       TEXT,
    positive_terms             JSONB NOT NULL DEFAULT '[]'::jsonb,
    negative_terms             JSONB NOT NULL DEFAULT '[]'::jsonb,
    flags                      JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_training_candidate      BOOLEAN NOT NULL DEFAULT FALSE,
    human_review_status        VARCHAR(50) NOT NULL DEFAULT 'not_reviewed',
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_dish_mention_sentiment_mention
        FOREIGN KEY (dish_mention_id)
        REFERENCES hidden_gems.dish_mention (dish_mention_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_dish_mention_sentiment_ai_pipeline_run
        FOREIGN KEY (ai_pipeline_run_id)
        REFERENCES hidden_gems.ai_pipeline_run (ai_pipeline_run_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_dish_mention_sentiment_model_version
        FOREIGN KEY (model_version_id)
        REFERENCES hidden_gems.ai_model_version (ai_model_version_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_dish_mention_sentiment_label_allowed
        CHECK (sentiment_label IN ('positive', 'neutral', 'negative')),

    CONSTRAINT chk_dish_mention_sentiment_score_range
        CHECK (sentiment_score IS NULL OR (sentiment_score >= -5 AND sentiment_score <= 5)),

    CONSTRAINT chk_dish_mention_sentiment_confidence_range
        CHECK (sentiment_confidence IS NULL OR (sentiment_confidence >= 0 AND sentiment_confidence <= 1)),

    CONSTRAINT chk_dish_mention_sentiment_reliability_allowed
        CHECK (
            sentiment_reliability_tier IS NULL
            OR sentiment_reliability_tier IN ('high', 'medium', 'low')
        ),

    CONSTRAINT chk_dish_mention_sentiment_method_not_blank
        CHECK (BTRIM(sentiment_method) <> ''),

    CONSTRAINT chk_dish_mention_sentiment_positive_terms_array
        CHECK (jsonb_typeof(positive_terms) = 'array'),

    CONSTRAINT chk_dish_mention_sentiment_negative_terms_array
        CHECK (jsonb_typeof(negative_terms) = 'array'),

    CONSTRAINT chk_dish_mention_sentiment_flags_array
        CHECK (jsonb_typeof(flags) = 'array'),

    CONSTRAINT chk_dish_mention_sentiment_human_review_status_allowed
        CHECK (
            human_review_status IN (
                'not_reviewed',
                'pending',
                'approved',
                'rejected',
                'corrected'
            )
        ),

    CONSTRAINT uq_dish_mention_sentiment_method_run
        UNIQUE (dish_mention_id, ai_pipeline_run_id, sentiment_method)
);

CREATE INDEX IF NOT EXISTS idx_dish_mention_sentiment_mention_id
    ON hidden_gems.dish_mention_sentiment (dish_mention_id);

CREATE INDEX IF NOT EXISTS idx_dish_mention_sentiment_ai_pipeline_run_id
    ON hidden_gems.dish_mention_sentiment (ai_pipeline_run_id);

CREATE INDEX IF NOT EXISTS idx_dish_mention_sentiment_model_version_id
    ON hidden_gems.dish_mention_sentiment (model_version_id);

CREATE INDEX IF NOT EXISTS idx_dish_mention_sentiment_label
    ON hidden_gems.dish_mention_sentiment (sentiment_label);

CREATE INDEX IF NOT EXISTS idx_dish_mention_sentiment_reliability
    ON hidden_gems.dish_mention_sentiment (sentiment_reliability_tier);

CREATE INDEX IF NOT EXISTS idx_dish_mention_sentiment_training_candidate
    ON hidden_gems.dish_mention_sentiment (is_training_candidate);

CREATE INDEX IF NOT EXISTS idx_dish_mention_sentiment_human_review_status
    ON hidden_gems.dish_mention_sentiment (human_review_status);

DROP TRIGGER IF EXISTS trg_dish_mention_sentiment_updated_at ON hidden_gems.dish_mention_sentiment;
CREATE TRIGGER trg_dish_mention_sentiment_updated_at
BEFORE UPDATE ON hidden_gems.dish_mention_sentiment
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.dish_mention_sentiment IS
'Sentimiento aspect-based calculado para una mención concreta de plato.';

COMMENT ON COLUMN hidden_gems.dish_mention_sentiment.sentiment_reliability_tier IS
'Nivel de fiabilidad de la etiqueta calculada: high, medium o low.';

-- =========================================================
-- 7) dish_place_signal
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.dish_place_signal (
    dish_place_signal_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    place_id                      UUID NOT NULL,
    dish_id                       UUID NOT NULL,
    ai_pipeline_run_id            UUID NOT NULL,
    signal_version                VARCHAR(50) NOT NULL,
    mention_count                 INTEGER NOT NULL DEFAULT 0,
    review_count                  INTEGER NOT NULL DEFAULT 0,
    positive_mentions             INTEGER NOT NULL DEFAULT 0,
    neutral_mentions              INTEGER NOT NULL DEFAULT 0,
    negative_mentions             INTEGER NOT NULL DEFAULT 0,
    positive_ratio                NUMERIC(7,6),
    negative_ratio                NUMERIC(7,6),
    avg_ner_confidence            NUMERIC(6,5),
    avg_sentiment_confidence      NUMERIC(6,5),
    avg_signal_weight             NUMERIC(8,5),
    total_signal_weight           NUMERIC(12,5),
    avg_rating                    NUMERIC(4,2),
    avg_sentiment_score_raw       NUMERIC(8,5),
    confidence_weighted_sentiment NUMERIC(8,5),
    bayesian_sentiment_score      NUMERIC(8,5),
    reliability_high_ratio        NUMERIC(7,6),
    high_reliability_mentions     INTEGER NOT NULL DEFAULT 0,
    medium_reliability_mentions   INTEGER NOT NULL DEFAULT 0,
    low_reliability_mentions      INTEGER NOT NULL DEFAULT 0,
    aggregate_quality_tier        VARCHAR(20),
    evidence_tier                 VARCHAR(20),
    is_rankable_candidate         BOOLEAN NOT NULL DEFAULT FALSE,
    quality_flags                 JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_dish_place_signal_place
        FOREIGN KEY (place_id)
        REFERENCES hidden_gems.place (place_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_dish_place_signal_dish
        FOREIGN KEY (dish_id)
        REFERENCES hidden_gems.dish (dish_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_dish_place_signal_ai_pipeline_run
        FOREIGN KEY (ai_pipeline_run_id)
        REFERENCES hidden_gems.ai_pipeline_run (ai_pipeline_run_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_dish_place_signal_version_not_blank
        CHECK (BTRIM(signal_version) <> ''),

    CONSTRAINT chk_dish_place_signal_counts_non_negative
        CHECK (
            mention_count >= 0
            AND review_count >= 0
            AND positive_mentions >= 0
            AND neutral_mentions >= 0
            AND negative_mentions >= 0
            AND high_reliability_mentions >= 0
            AND medium_reliability_mentions >= 0
            AND low_reliability_mentions >= 0
        ),

    CONSTRAINT chk_dish_place_signal_sentiment_counts_consistency
        CHECK (positive_mentions + neutral_mentions + negative_mentions <= mention_count),

    CONSTRAINT chk_dish_place_signal_reliability_counts_consistency
        CHECK (high_reliability_mentions + medium_reliability_mentions + low_reliability_mentions <= mention_count),

    CONSTRAINT chk_dish_place_signal_ratios_range
        CHECK (
            (positive_ratio IS NULL OR (positive_ratio >= 0 AND positive_ratio <= 1))
            AND (negative_ratio IS NULL OR (negative_ratio >= 0 AND negative_ratio <= 1))
            AND (reliability_high_ratio IS NULL OR (reliability_high_ratio >= 0 AND reliability_high_ratio <= 1))
        ),

    CONSTRAINT chk_dish_place_signal_confidence_range
        CHECK (
            (avg_ner_confidence IS NULL OR (avg_ner_confidence >= 0 AND avg_ner_confidence <= 1))
            AND (avg_sentiment_confidence IS NULL OR (avg_sentiment_confidence >= 0 AND avg_sentiment_confidence <= 1))
        ),

    CONSTRAINT chk_dish_place_signal_weights_non_negative
        CHECK (
            (avg_signal_weight IS NULL OR avg_signal_weight >= 0)
            AND (total_signal_weight IS NULL OR total_signal_weight >= 0)
        ),

    CONSTRAINT chk_dish_place_signal_avg_rating_range
        CHECK (avg_rating IS NULL OR (avg_rating >= 0 AND avg_rating <= 5)),

    CONSTRAINT chk_dish_place_signal_score_ranges
        CHECK (
            (confidence_weighted_sentiment IS NULL OR (confidence_weighted_sentiment >= -1 AND confidence_weighted_sentiment <= 1))
            AND (bayesian_sentiment_score IS NULL OR (bayesian_sentiment_score >= -1 AND bayesian_sentiment_score <= 1))
        ),

    CONSTRAINT chk_dish_place_signal_quality_tier_allowed
        CHECK (
            aggregate_quality_tier IS NULL
            OR aggregate_quality_tier IN ('high', 'medium', 'low')
        ),

    CONSTRAINT chk_dish_place_signal_evidence_tier_allowed
        CHECK (
            evidence_tier IS NULL
            OR evidence_tier IN ('strong', 'solid', 'emerging', 'weak')
        ),

    CONSTRAINT chk_dish_place_signal_quality_flags_array
        CHECK (jsonb_typeof(quality_flags) = 'array'),

    CONSTRAINT uq_dish_place_signal_place_dish_run_version
        UNIQUE (place_id, dish_id, ai_pipeline_run_id, signal_version)
);

CREATE INDEX IF NOT EXISTS idx_dish_place_signal_place_id
    ON hidden_gems.dish_place_signal (place_id);

CREATE INDEX IF NOT EXISTS idx_dish_place_signal_dish_id
    ON hidden_gems.dish_place_signal (dish_id);

CREATE INDEX IF NOT EXISTS idx_dish_place_signal_place_dish
    ON hidden_gems.dish_place_signal (place_id, dish_id);

CREATE INDEX IF NOT EXISTS idx_dish_place_signal_ai_pipeline_run_id
    ON hidden_gems.dish_place_signal (ai_pipeline_run_id);

CREATE INDEX IF NOT EXISTS idx_dish_place_signal_evidence_tier
    ON hidden_gems.dish_place_signal (evidence_tier);

CREATE INDEX IF NOT EXISTS idx_dish_place_signal_quality_tier
    ON hidden_gems.dish_place_signal (aggregate_quality_tier);

CREATE INDEX IF NOT EXISTS idx_dish_place_signal_is_rankable
    ON hidden_gems.dish_place_signal (is_rankable_candidate);

CREATE INDEX IF NOT EXISTS idx_dish_place_signal_conf_weighted_sentiment
    ON hidden_gems.dish_place_signal (confidence_weighted_sentiment DESC);

CREATE INDEX IF NOT EXISTS idx_dish_place_signal_bayesian_sentiment
    ON hidden_gems.dish_place_signal (bayesian_sentiment_score DESC);

DROP TRIGGER IF EXISTS trg_dish_place_signal_updated_at ON hidden_gems.dish_place_signal;
CREATE TRIGGER trg_dish_place_signal_updated_at
BEFORE UPDATE ON hidden_gems.dish_place_signal
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.dish_place_signal IS
'Señales agregadas por combinación place + dish, derivadas de menciones y sentimiento.';

COMMENT ON COLUMN hidden_gems.dish_place_signal.confidence_weighted_sentiment IS
'Sentimiento medio ponderado por confianza y fiabilidad de las menciones.';

COMMENT ON COLUMN hidden_gems.dish_place_signal.bayesian_sentiment_score IS
'Sentimiento suavizado con prior neutral para evitar sobrevalorar baja evidencia.';

-- =========================================================
-- 8) hidden_gem_candidate
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.hidden_gem_candidate (
    hidden_gem_candidate_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    place_id                       UUID NOT NULL,
    dish_id                        UUID NOT NULL,
    dish_place_signal_id           UUID,
    neighborhood_id                UUID,
    district_id                    UUID,
    ai_pipeline_run_id             UUID NOT NULL,
    ranking_version                VARCHAR(50) NOT NULL,
    ranking_scope                  VARCHAR(50) NOT NULL,
    hidden_gem_score               NUMERIC(8,5) NOT NULL,
    hidden_gem_score_base          NUMERIC(8,5),
    hidden_gem_rank                INTEGER,
    hidden_gem_selected_rank       INTEGER,
    hidden_gem_tier                VARCHAR(50) NOT NULL,
    is_selected                    BOOLEAN NOT NULL DEFAULT FALSE,
    local_sentiment_component      NUMERIC(7,6),
    evidence_component             NUMERIC(7,6),
    confidence_component           NUMERIC(7,6),
    positive_balance_component     NUMERIC(7,6),
    rarity_component               NUMERIC(7,6),
    local_outperformance_component NUMERIC(7,6),
    hiddenness_component           NUMERIC(7,6),
    preliminary_component          NUMERIC(7,6),
    negative_penalty_factor        NUMERIC(7,6),
    beverage_penalty_factor        NUMERIC(7,6),
    noise_penalty_factor           NUMERIC(7,6),
    low_evidence_penalty_factor    NUMERIC(7,6),
    ranking_explanation            TEXT,
    ranking_config_json            JSONB NOT NULL DEFAULT '{}'::jsonb,
    quality_flags                  JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_production_ready            BOOLEAN NOT NULL DEFAULT FALSE,
    human_review_status            VARCHAR(50) NOT NULL DEFAULT 'not_reviewed',
    created_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_hidden_gem_candidate_place
        FOREIGN KEY (place_id)
        REFERENCES hidden_gems.place (place_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_hidden_gem_candidate_dish
        FOREIGN KEY (dish_id)
        REFERENCES hidden_gems.dish (dish_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_hidden_gem_candidate_dish_place_signal
        FOREIGN KEY (dish_place_signal_id)
        REFERENCES hidden_gems.dish_place_signal (dish_place_signal_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_hidden_gem_candidate_neighborhood
        FOREIGN KEY (neighborhood_id)
        REFERENCES hidden_gems.neighborhood (neighborhood_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_hidden_gem_candidate_district
        FOREIGN KEY (district_id)
        REFERENCES hidden_gems.district (district_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_hidden_gem_candidate_neighborhood_district
        FOREIGN KEY (neighborhood_id, district_id)
        REFERENCES hidden_gems.neighborhood (neighborhood_id, district_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_hidden_gem_candidate_ai_pipeline_run
        FOREIGN KEY (ai_pipeline_run_id)
        REFERENCES hidden_gems.ai_pipeline_run (ai_pipeline_run_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_hidden_gem_candidate_ranking_version_not_blank
        CHECK (BTRIM(ranking_version) <> ''),

    CONSTRAINT chk_hidden_gem_candidate_scope_allowed
        CHECK (
            ranking_scope IN (
                'yelp_prototype',
                'sevilla_global',
                'sevilla_neighborhood',
                'manual_review',
                'other'
            )
        ),

    CONSTRAINT chk_hidden_gem_candidate_score_range
        CHECK (hidden_gem_score >= 0 AND hidden_gem_score <= 100),

    CONSTRAINT chk_hidden_gem_candidate_base_score_range
        CHECK (hidden_gem_score_base IS NULL OR (hidden_gem_score_base >= 0 AND hidden_gem_score_base <= 100)),

    CONSTRAINT chk_hidden_gem_candidate_rank_positive
        CHECK (hidden_gem_rank IS NULL OR hidden_gem_rank >= 1),

    CONSTRAINT chk_hidden_gem_candidate_selected_rank_positive
        CHECK (hidden_gem_selected_rank IS NULL OR hidden_gem_selected_rank >= 1),

    CONSTRAINT chk_hidden_gem_candidate_tier_allowed
        CHECK (
            hidden_gem_tier IN (
                'top_hidden_gem',
                'strong_hidden_gem',
                'promising_hidden_gem',
                'exploratory_hidden_gem',
                'not_selected'
            )
        ),

    CONSTRAINT chk_hidden_gem_candidate_components_range
        CHECK (
            (local_sentiment_component IS NULL OR (local_sentiment_component >= 0 AND local_sentiment_component <= 1))
            AND (evidence_component IS NULL OR (evidence_component >= 0 AND evidence_component <= 1))
            AND (confidence_component IS NULL OR (confidence_component >= 0 AND confidence_component <= 1))
            AND (positive_balance_component IS NULL OR (positive_balance_component >= 0 AND positive_balance_component <= 1))
            AND (rarity_component IS NULL OR (rarity_component >= 0 AND rarity_component <= 1))
            AND (local_outperformance_component IS NULL OR (local_outperformance_component >= 0 AND local_outperformance_component <= 1))
            AND (hiddenness_component IS NULL OR (hiddenness_component >= 0 AND hiddenness_component <= 1))
            AND (preliminary_component IS NULL OR (preliminary_component >= 0 AND preliminary_component <= 1))
        ),

    CONSTRAINT chk_hidden_gem_candidate_penalty_factors_range
        CHECK (
            (negative_penalty_factor IS NULL OR (negative_penalty_factor >= 0 AND negative_penalty_factor <= 1))
            AND (beverage_penalty_factor IS NULL OR (beverage_penalty_factor >= 0 AND beverage_penalty_factor <= 1))
            AND (noise_penalty_factor IS NULL OR (noise_penalty_factor >= 0 AND noise_penalty_factor <= 1))
            AND (low_evidence_penalty_factor IS NULL OR (low_evidence_penalty_factor >= 0 AND low_evidence_penalty_factor <= 1))
        ),

    CONSTRAINT chk_hidden_gem_candidate_selected_consistency
        CHECK (
            (is_selected = FALSE)
            OR (is_selected = TRUE AND hidden_gem_selected_rank IS NOT NULL AND hidden_gem_tier <> 'not_selected')
        ),

    CONSTRAINT chk_hidden_gem_candidate_config_object
        CHECK (jsonb_typeof(ranking_config_json) = 'object'),

    CONSTRAINT chk_hidden_gem_candidate_quality_flags_array
        CHECK (jsonb_typeof(quality_flags) = 'array'),

    CONSTRAINT chk_hidden_gem_candidate_human_review_status_allowed
        CHECK (
            human_review_status IN (
                'not_reviewed',
                'pending',
                'approved',
                'rejected',
                'corrected'
            )
        ),

    CONSTRAINT uq_hidden_gem_candidate_place_dish_run_version_scope
        UNIQUE (place_id, dish_id, ai_pipeline_run_id, ranking_version, ranking_scope)
);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_place_id
    ON hidden_gems.hidden_gem_candidate (place_id);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_dish_id
    ON hidden_gems.hidden_gem_candidate (dish_id);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_dish_place_signal_id
    ON hidden_gems.hidden_gem_candidate (dish_place_signal_id);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_neighborhood_id
    ON hidden_gems.hidden_gem_candidate (neighborhood_id);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_district_id
    ON hidden_gems.hidden_gem_candidate (district_id);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_ai_pipeline_run_id
    ON hidden_gems.hidden_gem_candidate (ai_pipeline_run_id);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_scope
    ON hidden_gems.hidden_gem_candidate (ranking_scope);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_tier
    ON hidden_gems.hidden_gem_candidate (hidden_gem_tier);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_is_selected
    ON hidden_gems.hidden_gem_candidate (is_selected);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_score
    ON hidden_gems.hidden_gem_candidate (hidden_gem_score DESC);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_neighborhood_score
    ON hidden_gems.hidden_gem_candidate (neighborhood_id, hidden_gem_score DESC);

CREATE INDEX IF NOT EXISTS idx_hidden_gem_candidate_place_score
    ON hidden_gems.hidden_gem_candidate (place_id, hidden_gem_score DESC);

DROP TRIGGER IF EXISTS trg_hidden_gem_candidate_updated_at ON hidden_gems.hidden_gem_candidate;
CREATE TRIGGER trg_hidden_gem_candidate_updated_at
BEFORE UPDATE ON hidden_gems.hidden_gem_candidate
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.hidden_gem_candidate IS
'Candidato final del ranking Hidden Gems para una combinación place + dish.';

COMMENT ON COLUMN hidden_gems.hidden_gem_candidate.ranking_scope IS
'Ámbito del ranking: yelp_prototype, sevilla_global, sevilla_neighborhood, manual_review u other.';

COMMENT ON COLUMN hidden_gems.hidden_gem_candidate.is_production_ready IS
'Indica si el candidato puede tratarse como salida productiva. El prototipo Yelp debe mantenerse como false.';

COMMENT ON COLUMN hidden_gems.hidden_gem_candidate.ranking_explanation IS
'Explicación textual generada para justificar el resultado del ranking.';

-- =========================================================
-- 9) Ampliación de validation_issue.entity_type
-- =========================================================
-- La relación entity_type + entity_id sigue siendo polimórfica. Se amplía
-- la lista permitida para poder registrar incidencias sobre entidades IA.

ALTER TABLE hidden_gems.validation_issue
    DROP CONSTRAINT IF EXISTS chk_validation_issue_entity_type_allowed;

ALTER TABLE hidden_gems.validation_issue
    ADD CONSTRAINT chk_validation_issue_entity_type_allowed
    CHECK (
        entity_type IN (
            'source_system',
            'source_run',
            'raw_asset',
            'place',
            'place_source_ref',
            'review',
            'category',
            'place_category',
            'district',
            'neighborhood',
            'place_neighborhood_assignment',
            'ai_model_version',
            'ai_pipeline_run',
            'dish',
            'dish_alias',
            'dish_mention',
            'dish_mention_sentiment',
            'dish_place_signal',
            'hidden_gem_candidate'
        )
    );
