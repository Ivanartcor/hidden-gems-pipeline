-- =========================================================
-- 00_foundation.sql
-- Base técnica para Hidden Gems
-- PostgreSQL + PostGIS
-- =========================================================

-- 1) Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2) Schema principal
CREATE SCHEMA IF NOT EXISTS hidden_gems;

SET search_path TO hidden_gems, public;

-- =========================================================
-- 3) Tipos ENUM
-- =========================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'source_type_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.source_type_enum AS ENUM (
            'api',
            'bulk_dataset',
            'geo_dataset',
            'manual_import'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'auth_type_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.auth_type_enum AS ENUM (
            'none',
            'api_key',
            'oauth',
            'manual'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'refresh_mode_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.refresh_mode_enum AS ENUM (
            'incremental',
            'full_refresh',
            'manual_snapshot'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'run_type_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.run_type_enum AS ENUM (
            'seed',
            'incremental',
            'full_refresh',
            'backfill',
            'manual_import'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'run_trigger_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.run_trigger_enum AS ENUM (
            'manual',
            'scheduled',
            'cli',
            'api',
            'retry'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'run_status_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.run_status_enum AS ENUM (
            'pending',
            'running',
            'completed',
            'completed_with_warnings',
            'failed',
            'cancelled'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'asset_type_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.asset_type_enum AS ENUM (
            'api_response',
            'bulk_file',
            'geo_file',
            'query_result',
            'raw_export'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'retention_class_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.retention_class_enum AS ENUM (
            'ephemeral',
            'short_term',
            'long_term',
            'permanent'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'assignment_method_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.assignment_method_enum AS ENUM (
            'source_raw',
            'normalized',
            'manual',
            'rule_based',
            'point_in_polygon',
            'nearest_polygon',
            'manual_review',
            'fallback_rule'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'validation_issue_type_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.validation_issue_type_enum AS ENUM (
            'validation',
            'quality',
            'matching',
            'geospatial',
            'schema'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'validation_severity_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.validation_severity_enum AS ENUM (
            'info',
            'warning',
            'error',
            'critical'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'validation_status_enum'
          AND n.nspname = 'hidden_gems'
    ) THEN
        CREATE TYPE hidden_gems.validation_status_enum AS ENUM (
            'open',
            'resolved',
            'ignored'
        );
    END IF;
END$$;

-- =========================================================
-- 4) Función genérica para updated_at
-- =========================================================

CREATE OR REPLACE FUNCTION hidden_gems.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;