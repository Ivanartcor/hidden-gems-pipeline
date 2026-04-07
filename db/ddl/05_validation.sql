-- =========================================================
-- 05_validation.sql
-- Control de calidad y validación:
--   - validation_issue
-- =========================================================

SET search_path TO hidden_gems, public;

-- =========================================================
-- 1) validation_issue
-- =========================================================

CREATE TABLE IF NOT EXISTS hidden_gems.validation_issue (
    validation_issue_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_run_id         UUID NOT NULL,
    raw_asset_id          UUID,
    entity_type           VARCHAR(50) NOT NULL,
    entity_id             UUID,
    issue_code            VARCHAR(100) NOT NULL,
    issue_type            hidden_gems.validation_issue_type_enum NOT NULL,
    severity              hidden_gems.validation_severity_enum NOT NULL,
    message               TEXT NOT NULL,
    field_name            VARCHAR(100),
    received_value        TEXT,
    expected_rule         TEXT,
    status                hidden_gems.validation_status_enum NOT NULL DEFAULT 'open',
    resolution_notes      TEXT,
    detected_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at           TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_validation_issue_source_run
        FOREIGN KEY (source_run_id)
        REFERENCES hidden_gems.source_run (source_run_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_validation_issue_raw_asset
        FOREIGN KEY (raw_asset_id)
        REFERENCES hidden_gems.raw_asset (raw_asset_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_validation_issue_entity_type_not_blank
        CHECK (BTRIM(entity_type) <> ''),

    CONSTRAINT chk_validation_issue_entity_type_allowed
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
                'place_neighborhood_assignment'
            )
        ),

    CONSTRAINT chk_validation_issue_issue_code_not_blank
        CHECK (BTRIM(issue_code) <> ''),

    CONSTRAINT chk_validation_issue_issue_code_format
        CHECK (issue_code ~ '^[a-z0-9_]+$'),

    CONSTRAINT chk_validation_issue_message_not_blank
        CHECK (BTRIM(message) <> ''),

    CONSTRAINT chk_validation_issue_resolved_after_detected
        CHECK (
            resolved_at IS NULL
            OR resolved_at >= detected_at
        ),

    CONSTRAINT chk_validation_issue_status_resolved_consistency
        CHECK (
            (status <> 'resolved')
            OR (status = 'resolved' AND resolved_at IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_validation_issue_source_run_id
    ON hidden_gems.validation_issue (source_run_id);

CREATE INDEX IF NOT EXISTS idx_validation_issue_raw_asset_id
    ON hidden_gems.validation_issue (raw_asset_id);

CREATE INDEX IF NOT EXISTS idx_validation_issue_entity_type
    ON hidden_gems.validation_issue (entity_type);

CREATE INDEX IF NOT EXISTS idx_validation_issue_entity_type_entity_id
    ON hidden_gems.validation_issue (entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_validation_issue_issue_code
    ON hidden_gems.validation_issue (issue_code);

CREATE INDEX IF NOT EXISTS idx_validation_issue_issue_type
    ON hidden_gems.validation_issue (issue_type);

CREATE INDEX IF NOT EXISTS idx_validation_issue_severity
    ON hidden_gems.validation_issue (severity);

CREATE INDEX IF NOT EXISTS idx_validation_issue_status
    ON hidden_gems.validation_issue (status);

CREATE INDEX IF NOT EXISTS idx_validation_issue_detected_at
    ON hidden_gems.validation_issue (detected_at DESC);

DROP TRIGGER IF EXISTS trg_validation_issue_updated_at ON hidden_gems.validation_issue;
CREATE TRIGGER trg_validation_issue_updated_at
BEFORE UPDATE ON hidden_gems.validation_issue
FOR EACH ROW
EXECUTE FUNCTION hidden_gems.set_updated_at();

COMMENT ON TABLE hidden_gems.validation_issue IS
'Registro estructurado de incidencias de calidad, validación, matching, geografía o esquema detectadas por el sistema.';

COMMENT ON COLUMN hidden_gems.validation_issue.entity_type IS
'Tipo de entidad afectada por la incidencia. Relación polimórfica controlada por entity_type + entity_id.';

COMMENT ON COLUMN hidden_gems.validation_issue.entity_id IS
'UUID de la entidad afectada cuando aplica. No tiene FK directa por ser una relación polimórfica.';

COMMENT ON COLUMN hidden_gems.validation_issue.issue_code IS
'Código técnico estable de la incidencia, en snake_case.';

COMMENT ON COLUMN hidden_gems.validation_issue.status IS
'Estado de la incidencia: open, resolved o ignored.';