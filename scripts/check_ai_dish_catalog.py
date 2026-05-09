"""
check_ai_dish_catalog.py

Validation/check script for the Hidden Gems AI dish catalog import.

It checks the first persisted AI layer created by scripts/load_ai_dish_catalog.py:

- hidden_gems.ai_model_version
- hidden_gems.ai_pipeline_run
- hidden_gems.dish
- hidden_gems.dish_alias

Recommended execution from the repository root, PowerShell:

python -m scripts.check_ai_dish_catalog `
  --catalog-path data/artifacts/ai/normalization/dish_catalog_seed_v2.csv `
  --aliases-path data/artifacts/ai/normalization/dish_aliases_seed_v2.csv

Basic execution:

python -m scripts.check_ai_dish_catalog
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.config.settings import settings
from src.db.database import engine


ALLOWED_SCHEMA_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

DEFAULT_RUN_CODE = "ai_run_yelp_dish_normalization_v2_catalog_import"

EXPECTED_MODEL_CODES = [
    "dish_ner_transformer_v1",
    "dish_normalization_rule_based_v2",
    "mention_sentiment_hybrid_v1_1",
    "signal_aggregation_v1",
    "hidden_gems_ranking_v1",
]


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------

def validate_schema_name(schema: str) -> str:
    schema = str(schema).strip()
    if not ALLOWED_SCHEMA_PATTERN.match(schema):
        raise ValueError(f"Invalid PostgreSQL schema name: {schema!r}")
    return schema


def qname(schema: str, table: str) -> str:
    schema = validate_schema_name(schema)
    return f'"{schema}"."{table}"'


def normalize_space(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def rows_to_dicts(rows: list[Any]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        item = dict(row)
        result.append({key: json_safe(value) for key, value in item.items()})
    return result


def scalar(conn: Connection, sql: str, params: dict[str, Any] | None = None) -> Any:
    return conn.execute(text(sql), params or {}).scalar_one()


def mappings(conn: Connection, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = conn.execute(text(sql), params or {}).mappings().all()
    return rows_to_dicts(rows)


def print_section(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def print_table(rows: list[dict[str, Any]], *, empty_message: str = "No rows.") -> None:
    if not rows:
        print(empty_message)
        return

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


def read_expected_catalog_count(path: Path | None) -> int | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"Catalog CSV not found: {path}")

    df = pd.read_csv(path)
    if "canonical_dish_name" not in df.columns:
        raise ValueError("Catalog CSV must contain column 'canonical_dish_name'.")

    df["canonical_dish_name_clean"] = df["canonical_dish_name"].apply(normalize_space).str.lower()
    df = df[df["canonical_dish_name_clean"].str.len() > 0].copy()
    df = df.drop_duplicates(subset=["canonical_dish_name_clean"], keep="first")
    return int(len(df))


def read_expected_alias_count(path: Path | None) -> int | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"Aliases CSV not found: {path}")

    df = pd.read_csv(path)
    required = {"canonical_dish_name", "alias_text"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Aliases CSV is missing required columns: {missing}")

    df["canonical_dish_name_clean"] = df["canonical_dish_name"].apply(normalize_space).str.lower()
    df["alias_text_clean"] = df["alias_text"].apply(normalize_space)
    df["alias_normalized_clean"] = df["alias_text_clean"].str.lower()

    df = df[
        (df["canonical_dish_name_clean"].str.len() > 0)
        & (df["alias_text_clean"].str.len() > 0)
        & (df["alias_normalized_clean"].str.len() > 0)
    ].copy()

    df = df.drop_duplicates(
        subset=["canonical_dish_name_clean", "alias_normalized_clean"],
        keep="first",
    )
    return int(len(df))


# -----------------------------------------------------------------------------
# Checks
# -----------------------------------------------------------------------------

def fetch_run(conn: Connection, schema: str, run_code: str) -> dict[str, Any] | None:
    rows = mappings(
        conn,
        f"""
        SELECT
            ai_pipeline_run_id::text AS ai_pipeline_run_id,
            run_code,
            run_type,
            status::text AS status,
            started_at,
            finished_at,
            metrics_json,
            config_json
        FROM {qname(schema, 'ai_pipeline_run')}
        WHERE run_code = :run_code;
        """,
        {"run_code": run_code},
    )
    return rows[0] if rows else None


def run_checks(
    *,
    schema: str,
    run_code: str,
    catalog_path: Path | None,
    aliases_path: Path | None,
    top_n: int,
) -> tuple[dict[str, Any], list[str], list[str]]:
    schema = validate_schema_name(schema)

    errors: list[str] = []
    warnings: list[str] = []
    report: dict[str, Any] = {
        "schema": schema,
        "run_code": run_code,
        "expected_inputs": {
            "catalog_path": str(catalog_path) if catalog_path else None,
            "aliases_path": str(aliases_path) if aliases_path else None,
        },
    }

    expected_catalog_count = read_expected_catalog_count(catalog_path)
    expected_alias_count = read_expected_alias_count(aliases_path)

    report["expected_inputs"]["catalog_unique_rows"] = expected_catalog_count
    report["expected_inputs"]["alias_unique_rows"] = expected_alias_count

    with engine.connect() as conn:
        print_section("1. AI pipeline run")
        run = fetch_run(conn, schema, run_code)
        report["ai_pipeline_run"] = run

        if run is None:
            errors.append(f"ai_pipeline_run not found for run_code={run_code!r}.")
            print(f"ERROR: no ai_pipeline_run found for run_code={run_code!r}")
            run_id = None
        else:
            run_id = run["ai_pipeline_run_id"]
            print_table([run])

        print_section("2. AI model versions")
        model_rows = mappings(
            conn,
            f"""
            SELECT
                model_code,
                model_type,
                task_name,
                version_label,
                framework_name,
                language_scope,
                is_active
            FROM {qname(schema, 'ai_model_version')}
            WHERE model_code = ANY(:model_codes)
            ORDER BY task_name, model_code;
            """,
            {"model_codes": EXPECTED_MODEL_CODES},
        )
        report["ai_model_versions"] = model_rows
        print_table(model_rows)

        found_model_codes = {row["model_code"] for row in model_rows}
        missing_models = sorted(set(EXPECTED_MODEL_CODES) - found_model_codes)
        if missing_models:
            warnings.append(f"Missing expected ai_model_version rows: {missing_models}")

        print_section("3. Core catalog counts")
        count_rows = mappings(
            conn,
            f"""
            WITH run_ref AS (
                SELECT ai_pipeline_run_id
                FROM {qname(schema, 'ai_pipeline_run')}
                WHERE run_code = :run_code
            )
            SELECT
                (SELECT COUNT(*) FROM {qname(schema, 'dish')})::int AS total_dishes,
                (SELECT COUNT(*) FROM {qname(schema, 'dish')} WHERE is_active)::int AS active_dishes,
                (SELECT COUNT(*) FROM {qname(schema, 'dish')} WHERE source_ai_run_id = (SELECT ai_pipeline_run_id FROM run_ref))::int AS dishes_from_run,
                (SELECT COUNT(*) FROM {qname(schema, 'dish_alias')})::int AS total_aliases,
                (SELECT COUNT(*) FROM {qname(schema, 'dish_alias')} WHERE is_active)::int AS active_aliases,
                (SELECT COUNT(*) FROM {qname(schema, 'dish_alias')} WHERE source_ai_run_id = (SELECT ai_pipeline_run_id FROM run_ref))::int AS aliases_from_run,
                (SELECT COUNT(*) FROM {qname(schema, 'dish_alias')} WHERE alias_type = 'canonical')::int AS canonical_aliases;
            """,
            {"run_code": run_code},
        )
        counts = count_rows[0]
        report["counts"] = counts
        print_table(count_rows)

        if expected_catalog_count is not None and run_id is not None:
            if counts["dishes_from_run"] != expected_catalog_count:
                warnings.append(
                    "Dish count from run does not match cleaned catalog rows: "
                    f"db={counts['dishes_from_run']} expected={expected_catalog_count}"
                )

        if expected_alias_count is not None and run_id is not None:
            if counts["aliases_from_run"] != expected_alias_count:
                warnings.append(
                    "Alias count from run does not match cleaned alias rows: "
                    f"db={counts['aliases_from_run']} expected={expected_alias_count}"
                )

        print_section("4. Distribution checks")
        language_rows = mappings(
            conn,
            f"""
            SELECT language_code, COUNT(*)::int AS count
            FROM {qname(schema, 'dish')}
            GROUP BY language_code
            ORDER BY count DESC, language_code;
            """,
        )
        review_status_rows = mappings(
            conn,
            f"""
            SELECT review_status, COUNT(*)::int AS count
            FROM {qname(schema, 'dish')}
            GROUP BY review_status
            ORDER BY count DESC, review_status;
            """,
        )
        alias_type_rows = mappings(
            conn,
            f"""
            SELECT alias_type, COUNT(*)::int AS count
            FROM {qname(schema, 'dish_alias')}
            GROUP BY alias_type
            ORDER BY count DESC, alias_type;
            """,
        )

        report["distributions"] = {
            "dish_language": language_rows,
            "dish_review_status": review_status_rows,
            "alias_type": alias_type_rows,
        }

        print("Dish languages:")
        print_table(language_rows)
        print("\nDish review status:")
        print_table(review_status_rows)
        print("\nAlias types:")
        print_table(alias_type_rows)

        print_section("5. Integrity checks")
        integrity = mappings(
            conn,
            f"""
            SELECT
                (
                    SELECT COUNT(*)
                    FROM {qname(schema, 'dish_alias')} da
                    LEFT JOIN {qname(schema, 'dish')} d ON d.dish_id = da.dish_id
                    WHERE d.dish_id IS NULL
                )::int AS orphan_aliases,
                (
                    SELECT COUNT(*)
                    FROM {qname(schema, 'dish')} d
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM {qname(schema, 'dish_alias')} da
                        WHERE da.dish_id = d.dish_id
                    )
                )::int AS dishes_without_aliases,
                (
                    SELECT COUNT(*)
                    FROM {qname(schema, 'dish')} d
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM {qname(schema, 'dish_alias')} da
                        WHERE da.dish_id = d.dish_id
                          AND da.alias_type = 'canonical'
                    )
                )::int AS dishes_without_canonical_alias,
                (
                    SELECT COUNT(*)
                    FROM {qname(schema, 'dish')}
                    WHERE BTRIM(canonical_name) = '' OR BTRIM(normalized_name) = ''
                )::int AS blank_dish_names,
                (
                    SELECT COUNT(*)
                    FROM {qname(schema, 'dish_alias')}
                    WHERE BTRIM(alias_text) = '' OR BTRIM(alias_normalized) = ''
                )::int AS blank_aliases;
            """,
        )
        integrity_counts = integrity[0]
        report["integrity"] = integrity_counts
        print_table(integrity)

        if integrity_counts["orphan_aliases"] != 0:
            errors.append(f"Found orphan aliases: {integrity_counts['orphan_aliases']}")
        if integrity_counts["blank_dish_names"] != 0:
            errors.append(f"Found blank dish names: {integrity_counts['blank_dish_names']}")
        if integrity_counts["blank_aliases"] != 0:
            errors.append(f"Found blank aliases: {integrity_counts['blank_aliases']}")
        if integrity_counts["dishes_without_aliases"] != 0:
            warnings.append(f"Found dishes without aliases: {integrity_counts['dishes_without_aliases']}")
        if integrity_counts["dishes_without_canonical_alias"] != 0:
            warnings.append(
                f"Found dishes without canonical alias: {integrity_counts['dishes_without_canonical_alias']}"
            )

        print_section("6. Duplicate and ambiguity checks")
        duplicate_normalized_dishes = mappings(
            conn,
            f"""
            SELECT normalized_name, COUNT(*)::int AS count
            FROM {qname(schema, 'dish')}
            GROUP BY normalized_name
            HAVING COUNT(*) > 1
            ORDER BY count DESC, normalized_name
            LIMIT :top_n;
            """,
            {"top_n": top_n},
        )
        cross_dish_aliases = mappings(
            conn,
            f"""
            SELECT
                alias_normalized,
                COUNT(*)::int AS alias_rows,
                COUNT(DISTINCT da.dish_id)::int AS distinct_dishes,
                STRING_AGG(DISTINCT d.canonical_name, ' | ' ORDER BY d.canonical_name) AS dishes
            FROM {qname(schema, 'dish_alias')} da
            JOIN {qname(schema, 'dish')} d ON d.dish_id = da.dish_id
            GROUP BY alias_normalized
            HAVING COUNT(DISTINCT da.dish_id) > 1
            ORDER BY distinct_dishes DESC, alias_rows DESC, alias_normalized
            LIMIT :top_n;
            """,
            {"top_n": top_n},
        )

        report["duplicates"] = {
            "duplicate_normalized_dishes": duplicate_normalized_dishes,
            "cross_dish_aliases": cross_dish_aliases,
        }

        print("Duplicate normalized dishes:")
        print_table(duplicate_normalized_dishes, empty_message="No duplicate normalized dish names.")
        print("\nAliases mapped to multiple dishes:")
        print_table(cross_dish_aliases, empty_message="No cross-dish aliases found.")

        if duplicate_normalized_dishes:
            warnings.append(f"Found duplicate normalized dish names: {len(duplicate_normalized_dishes)} shown.")
        if cross_dish_aliases:
            warnings.append(f"Found aliases mapped to multiple dishes: {len(cross_dish_aliases)} shown.")

        print_section("7. Alias coverage stats")
        alias_coverage_rows = mappings(
            conn,
            f"""
            WITH alias_counts AS (
                SELECT
                    d.dish_id,
                    COUNT(da.dish_alias_id)::int AS alias_count,
                    COALESCE(SUM(da.mention_count), 0)::int AS alias_mention_count,
                    COALESCE(SUM(da.review_count), 0)::int AS alias_review_count,
                    COALESCE(SUM(da.business_count), 0)::int AS alias_business_count
                FROM {qname(schema, 'dish')} d
                LEFT JOIN {qname(schema, 'dish_alias')} da ON da.dish_id = d.dish_id
                GROUP BY d.dish_id
            )
            SELECT
                COUNT(*)::int AS dish_count,
                MIN(alias_count)::int AS min_aliases_per_dish,
                ROUND(AVG(alias_count)::numeric, 3)::float AS avg_aliases_per_dish,
                MAX(alias_count)::int AS max_aliases_per_dish,
                MIN(alias_mention_count)::int AS min_alias_mentions,
                ROUND(AVG(alias_mention_count)::numeric, 3)::float AS avg_alias_mentions,
                MAX(alias_mention_count)::int AS max_alias_mentions
            FROM alias_counts;
            """,
        )
        report["alias_coverage_stats"] = alias_coverage_rows[0]
        print_table(alias_coverage_rows)

        print_section(f"8. Top {top_n} dishes by alias mention count")
        top_dishes = mappings(
            conn,
            f"""
            SELECT
                d.dish_code,
                d.canonical_name,
                d.review_status,
                COUNT(da.dish_alias_id)::int AS alias_count,
                COALESCE(SUM(da.mention_count), 0)::int AS alias_mention_count,
                COALESCE(SUM(da.review_count), 0)::int AS alias_review_count,
                COALESCE(SUM(da.business_count), 0)::int AS alias_business_count,
                ROUND(AVG(da.avg_confidence)::numeric, 5)::float AS avg_alias_confidence
            FROM {qname(schema, 'dish')} d
            LEFT JOIN {qname(schema, 'dish_alias')} da ON da.dish_id = d.dish_id
            GROUP BY d.dish_id, d.dish_code, d.canonical_name, d.review_status
            ORDER BY alias_mention_count DESC, alias_count DESC, d.canonical_name
            LIMIT :top_n;
            """,
            {"top_n": top_n},
        )
        report["top_dishes_by_alias_mentions"] = top_dishes
        print_table(top_dishes)

        print_section(f"9. Top {top_n} aliases by mention count")
        top_aliases = mappings(
            conn,
            f"""
            SELECT
                d.canonical_name,
                da.alias_text,
                da.alias_type,
                da.mention_count,
                da.review_count,
                da.business_count,
                da.avg_confidence::float AS avg_confidence
            FROM {qname(schema, 'dish_alias')} da
            JOIN {qname(schema, 'dish')} d ON d.dish_id = da.dish_id
            ORDER BY COALESCE(da.mention_count, 0) DESC, da.alias_text
            LIMIT :top_n;
            """,
            {"top_n": top_n},
        )
        report["top_aliases_by_mentions"] = top_aliases
        print_table(top_aliases)

    report["status"] = {
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
    }

    return report, errors, warnings


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check the AI dish catalog and alias import in PostgreSQL."
    )

    parser.add_argument(
        "--schema",
        default=settings.pgschema,
        help=f"Target PostgreSQL schema. Default: {settings.pgschema}.",
    )
    parser.add_argument(
        "--run-code",
        default=DEFAULT_RUN_CODE,
        help=f"ai_pipeline_run.run_code to check. Default: {DEFAULT_RUN_CODE}.",
    )
    parser.add_argument(
        "--catalog-path",
        type=Path,
        default=None,
        help="Optional path to dish_catalog_seed_v2.csv to compare expected cleaned row count.",
    )
    parser.add_argument(
        "--aliases-path",
        type=Path,
        default=None,
        help="Optional path to dish_aliases_seed_v2.csv to compare expected cleaned row count.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=25,
        help="Number of top rows to show in diagnostic tables. Default: 25.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Optional path to write a JSON check report.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 when warnings are found. Errors always return code 1.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report, errors, warnings = run_checks(
            schema=args.schema,
            run_code=args.run_code,
            catalog_path=args.catalog_path,
            aliases_path=args.aliases_path,
            top_n=args.top_n,
        )

        if args.report_path is not None:
            args.report_path.parent.mkdir(parents=True, exist_ok=True)
            with args.report_path.open("w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=json_safe)
            print(f"\nJSON report written to: {args.report_path}")

        print_section("Final check result")

        if errors:
            print("ERRORS:")
            for item in errors:
                print(f"  - {item}")
        else:
            print("No blocking errors found.")

        if warnings:
            print("\nWARNINGS:")
            for item in warnings:
                print(f"  - {item}")
        else:
            print("No warnings found.")

        if errors:
            print("\nCatalog check FAILED.")
            return 1

        if warnings and args.strict:
            print("\nCatalog check finished with warnings and --strict is enabled.")
            return 1

        print("\nCatalog check completed successfully.")
        return 0

    except Exception as exc:
        print(f"\nUnexpected error while checking AI dish catalog: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
