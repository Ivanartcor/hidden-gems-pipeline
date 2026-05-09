-- =========================================================
-- 08_ai_views.sql
-- Capa de consulta IA para Hidden Gems
--
-- Objetivo:
--   Crear vistas legibles sobre la capa IA ya cargada en PostgreSQL:
--   - señales por local + plato
--   - candidatos Hidden Gems
--   - rankings prototipo Yelp
--   - resúmenes por local, plato y ciudad
--   - menciones con sentimiento para auditoría
--
-- Nota:
--   Las vistas no crean nuevos datos. Solo exponen de forma cómoda
--   las tablas persistidas en 07_ai_module.sql.
-- =========================================================

SET search_path TO hidden_gems, public;

-- =========================================================
-- 0) Limpieza idempotente de vistas propias
-- =========================================================
-- Se eliminan en orden inverso de dependencia.

DROP VIEW IF EXISTS hidden_gems.vw_ai_hidden_gems_yelp_top;
DROP VIEW IF EXISTS hidden_gems.vw_ai_hidden_gems_city_summary;
DROP VIEW IF EXISTS hidden_gems.vw_ai_hidden_gems_place_summary;
DROP VIEW IF EXISTS hidden_gems.vw_ai_hidden_gems_dish_summary;
DROP VIEW IF EXISTS hidden_gems.vw_ai_dish_mentions_with_sentiment;
DROP VIEW IF EXISTS hidden_gems.vw_ai_dish_place_signals;
DROP VIEW IF EXISTS hidden_gems.vw_ai_hidden_gem_candidate_detail;
DROP VIEW IF EXISTS hidden_gems.vw_ai_pipeline_run_summary;

-- =========================================================
-- 1) vw_ai_pipeline_run_summary
-- =========================================================
-- Vista de gobierno para revisar versiones, ejecuciones y métricas IA.

CREATE VIEW hidden_gems.vw_ai_pipeline_run_summary AS
SELECT
    apr.ai_pipeline_run_id,
    apr.run_code,
    apr.run_type,
    apr.status::text AS status,
    apr.started_at,
    apr.finished_at,
    apr.duration_seconds,
    apr.source_run_id,
    apr.parent_ai_run_id,
    apr.input_artifacts_json,
    apr.output_artifacts_json,
    apr.metrics_json,
    apr.config_json,
    apr.notes,
    apr.created_at,
    apr.updated_at,
    COUNT(DISTINCT d.dish_id) AS dishes_generated,
    COUNT(DISTINCT da.dish_alias_id) AS aliases_generated,
    COUNT(DISTINCT dm.dish_mention_id) AS mentions_generated,
    COUNT(DISTINCT dms.dish_mention_sentiment_id) AS sentiments_generated,
    COUNT(DISTINCT dps.dish_place_signal_id) AS place_signals_generated,
    COUNT(DISTINCT hgc.hidden_gem_candidate_id) AS ranking_candidates_generated
FROM hidden_gems.ai_pipeline_run apr
LEFT JOIN hidden_gems.dish d
    ON d.source_ai_run_id = apr.ai_pipeline_run_id
LEFT JOIN hidden_gems.dish_alias da
    ON da.source_ai_run_id = apr.ai_pipeline_run_id
LEFT JOIN hidden_gems.dish_mention dm
    ON dm.ai_pipeline_run_id = apr.ai_pipeline_run_id
LEFT JOIN hidden_gems.dish_mention_sentiment dms
    ON dms.ai_pipeline_run_id = apr.ai_pipeline_run_id
LEFT JOIN hidden_gems.dish_place_signal dps
    ON dps.ai_pipeline_run_id = apr.ai_pipeline_run_id
LEFT JOIN hidden_gems.hidden_gem_candidate hgc
    ON hgc.ai_pipeline_run_id = apr.ai_pipeline_run_id
GROUP BY
    apr.ai_pipeline_run_id,
    apr.run_code,
    apr.run_type,
    apr.status,
    apr.started_at,
    apr.finished_at,
    apr.duration_seconds,
    apr.source_run_id,
    apr.parent_ai_run_id,
    apr.input_artifacts_json,
    apr.output_artifacts_json,
    apr.metrics_json,
    apr.config_json,
    apr.notes,
    apr.created_at,
    apr.updated_at;

COMMENT ON VIEW hidden_gems.vw_ai_pipeline_run_summary IS
'Vista de gobierno de ejecuciones IA con conteos de entidades derivadas generadas por cada run.';

-- =========================================================
-- 2) vw_ai_dish_place_signals
-- =========================================================
-- Vista base de señales agregadas por place + dish.
-- Es útil para analizar qué platos tienen señal suficiente en cada local.

CREATE VIEW hidden_gems.vw_ai_dish_place_signals AS
SELECT
    dps.dish_place_signal_id,
    dps.ai_pipeline_run_id,
    apr.run_code AS ai_run_code,
    dps.signal_version,

    p.place_id,
    COALESCE(p.display_name, p.canonical_name) AS place_name,
    p.canonical_name AS place_canonical_name,
    p.normalized_name AS place_normalized_name,
    p.address_text,
    p.latitude,
    p.longitude,

    ds.dish_id,
    ds.canonical_name AS dish_name,
    ds.normalized_name AS dish_normalized_name,
    ds.display_name AS dish_display_name,
    ds.language_code AS dish_language_code,

    pna.neighborhood_id AS current_neighborhood_id,
    n.official_name AS current_neighborhood_name,
    pna.district_id AS current_district_id,
    dist.official_name AS current_district_name,

    dps.mention_count,
    dps.review_count,
    dps.positive_mentions,
    dps.neutral_mentions,
    dps.negative_mentions,
    dps.positive_ratio,
    dps.negative_ratio,
    dps.avg_ner_confidence,
    dps.avg_sentiment_confidence,
    dps.avg_signal_weight,
    dps.total_signal_weight,
    dps.avg_rating,
    dps.avg_sentiment_score_raw,
    dps.confidence_weighted_sentiment,
    dps.bayesian_sentiment_score,
    dps.reliability_high_ratio,
    dps.high_reliability_mentions,
    dps.medium_reliability_mentions,
    dps.low_reliability_mentions,
    dps.aggregate_quality_tier,
    dps.evidence_tier,
    dps.is_rankable_candidate,
    dps.quality_flags,

    CASE
        WHEN dps.evidence_tier = 'strong' THEN 4
        WHEN dps.evidence_tier = 'solid' THEN 3
        WHEN dps.evidence_tier = 'emerging' THEN 2
        WHEN dps.evidence_tier = 'weak' THEN 1
        ELSE 0
    END AS evidence_tier_order,

    CASE
        WHEN dps.aggregate_quality_tier = 'high' THEN 3
        WHEN dps.aggregate_quality_tier = 'medium' THEN 2
        WHEN dps.aggregate_quality_tier = 'low' THEN 1
        ELSE 0
    END AS aggregate_quality_tier_order,

    dps.created_at,
    dps.updated_at
FROM hidden_gems.dish_place_signal dps
JOIN hidden_gems.place p
    ON p.place_id = dps.place_id
JOIN hidden_gems.dish ds
    ON ds.dish_id = dps.dish_id
JOIN hidden_gems.ai_pipeline_run apr
    ON apr.ai_pipeline_run_id = dps.ai_pipeline_run_id
LEFT JOIN hidden_gems.place_neighborhood_assignment pna
    ON pna.place_id = p.place_id
   AND pna.is_current = TRUE
LEFT JOIN hidden_gems.neighborhood n
    ON n.neighborhood_id = pna.neighborhood_id
LEFT JOIN hidden_gems.district dist
    ON dist.district_id = pna.district_id;

COMMENT ON VIEW hidden_gems.vw_ai_dish_place_signals IS
'Señales IA agregadas por local canónico y plato canónico, enriquecidas con datos de place, dish y barrio actual si existe.';

-- =========================================================
-- 3) vw_ai_hidden_gem_candidate_detail
-- =========================================================
-- Vista principal de detalle del ranking Hidden Gems.
-- Incluye todos los candidatos, no solo seleccionados.

CREATE VIEW hidden_gems.vw_ai_hidden_gem_candidate_detail AS
SELECT
    hgc.hidden_gem_candidate_id,
    hgc.ai_pipeline_run_id,
    apr.run_code AS ai_run_code,
    hgc.ranking_version,
    hgc.ranking_scope,

    hgc.hidden_gem_rank,
    hgc.hidden_gem_selected_rank,
    hgc.hidden_gem_tier,
    hgc.is_selected,
    hgc.is_production_ready,
    hgc.human_review_status,

    hgc.hidden_gem_score,
    hgc.hidden_gem_score_base,

    p.place_id,
    COALESCE(p.display_name, p.canonical_name) AS place_name,
    p.canonical_name AS place_canonical_name,
    p.normalized_name AS place_normalized_name,
    p.address_text,
    p.latitude,
    p.longitude,
    p.is_active AS place_is_active,
    p.place_confidence,

    ds.dish_id,
    ds.canonical_name AS dish_name,
    ds.normalized_name AS dish_normalized_name,
    ds.display_name AS dish_display_name,
    ds.language_code AS dish_language_code,
    ds.is_reviewed AS dish_is_reviewed,
    ds.review_status AS dish_review_status,

    hgc.neighborhood_id,
    COALESCE(n_hgc.official_name, n_current.official_name) AS neighborhood_name,
    COALESCE(n_hgc.normalized_name, n_current.normalized_name) AS neighborhood_normalized_name,
    hgc.district_id,
    COALESCE(dist_hgc.official_name, dist_current.official_name) AS district_name,
    COALESCE(dist_hgc.normalized_name, dist_current.normalized_name) AS district_normalized_name,

    dps.dish_place_signal_id,
    dps.signal_version,
    dps.mention_count,
    dps.review_count,
    dps.positive_mentions,
    dps.neutral_mentions,
    dps.negative_mentions,
    dps.positive_ratio,
    dps.negative_ratio,
    dps.avg_ner_confidence,
    dps.avg_sentiment_confidence,
    dps.avg_signal_weight,
    dps.total_signal_weight,
    dps.avg_rating,
    dps.confidence_weighted_sentiment,
    dps.bayesian_sentiment_score,
    dps.reliability_high_ratio,
    dps.high_reliability_mentions,
    dps.medium_reliability_mentions,
    dps.low_reliability_mentions,
    dps.aggregate_quality_tier,
    dps.evidence_tier,
    dps.is_rankable_candidate,

    hgc.local_sentiment_component,
    hgc.evidence_component,
    hgc.confidence_component,
    hgc.positive_balance_component,
    hgc.rarity_component,
    hgc.local_outperformance_component,
    hgc.hiddenness_component,
    hgc.preliminary_component,
    hgc.negative_penalty_factor,
    hgc.beverage_penalty_factor,
    hgc.noise_penalty_factor,
    hgc.low_evidence_penalty_factor,

    hgc.ranking_explanation,
    hgc.ranking_config_json,
    hgc.quality_flags,

    CASE
        WHEN hgc.hidden_gem_tier = 'top_hidden_gem' THEN 4
        WHEN hgc.hidden_gem_tier = 'strong_hidden_gem' THEN 3
        WHEN hgc.hidden_gem_tier = 'promising_hidden_gem' THEN 2
        WHEN hgc.hidden_gem_tier = 'exploratory_hidden_gem' THEN 1
        ELSE 0
    END AS hidden_gem_tier_order,

    CASE
        WHEN dps.evidence_tier = 'strong' THEN 4
        WHEN dps.evidence_tier = 'solid' THEN 3
        WHEN dps.evidence_tier = 'emerging' THEN 2
        WHEN dps.evidence_tier = 'weak' THEN 1
        ELSE 0
    END AS evidence_tier_order,

    hgc.created_at,
    hgc.updated_at
FROM hidden_gems.hidden_gem_candidate hgc
JOIN hidden_gems.place p
    ON p.place_id = hgc.place_id
JOIN hidden_gems.dish ds
    ON ds.dish_id = hgc.dish_id
JOIN hidden_gems.ai_pipeline_run apr
    ON apr.ai_pipeline_run_id = hgc.ai_pipeline_run_id
LEFT JOIN hidden_gems.dish_place_signal dps
    ON dps.dish_place_signal_id = hgc.dish_place_signal_id
LEFT JOIN hidden_gems.place_neighborhood_assignment pna
    ON pna.place_id = hgc.place_id
   AND pna.is_current = TRUE
LEFT JOIN hidden_gems.neighborhood n_hgc
    ON n_hgc.neighborhood_id = hgc.neighborhood_id
LEFT JOIN hidden_gems.neighborhood n_current
    ON n_current.neighborhood_id = pna.neighborhood_id
LEFT JOIN hidden_gems.district dist_hgc
    ON dist_hgc.district_id = hgc.district_id
LEFT JOIN hidden_gems.district dist_current
    ON dist_current.district_id = pna.district_id;

COMMENT ON VIEW hidden_gems.vw_ai_hidden_gem_candidate_detail IS
'Detalle completo de candidatos Hidden Gems con place, dish, señal agregada, componentes del score y contexto geográfico cuando exista.';

-- =========================================================
-- 4) vw_ai_hidden_gems_yelp_top
-- =========================================================
-- Vista lista para demo del ranking prototipo Yelp.

CREATE VIEW hidden_gems.vw_ai_hidden_gems_yelp_top AS
SELECT
    hidden_gem_selected_rank,
    hidden_gem_rank,
    hidden_gem_tier,
    hidden_gem_score,
    hidden_gem_score_base,
    place_id,
    place_name,
    address_text,
    latitude,
    longitude,
    dish_id,
    dish_name,
    mention_count,
    review_count,
    positive_mentions,
    neutral_mentions,
    negative_mentions,
    positive_ratio,
    negative_ratio,
    bayesian_sentiment_score,
    confidence_weighted_sentiment,
    total_signal_weight,
    reliability_high_ratio,
    aggregate_quality_tier,
    evidence_tier,
    local_sentiment_component,
    evidence_component,
    confidence_component,
    positive_balance_component,
    rarity_component,
    local_outperformance_component,
    hiddenness_component,
    ranking_explanation,
    ranking_version,
    ranking_scope,
    is_production_ready,
    human_review_status,
    created_at,
    updated_at
FROM hidden_gems.vw_ai_hidden_gem_candidate_detail
WHERE ranking_scope = 'yelp_prototype'
  AND is_selected = TRUE
ORDER BY hidden_gem_selected_rank NULLS LAST, hidden_gem_score DESC;

COMMENT ON VIEW hidden_gems.vw_ai_hidden_gems_yelp_top IS
'Ranking prototipo Yelp de candidatos Hidden Gems seleccionados. No es producción Sevilla.';

-- =========================================================
-- 5) vw_ai_hidden_gems_place_summary
-- =========================================================
-- Resumen por local: cuántos candidatos tiene y cuál es su mejor plato.

CREATE VIEW hidden_gems.vw_ai_hidden_gems_place_summary AS
WITH selected_candidates AS (
    SELECT *
    FROM hidden_gems.vw_ai_hidden_gem_candidate_detail
    WHERE is_selected = TRUE
)
SELECT
    place_id,
    place_name,
    address_text,
    latitude,
    longitude,
    ranking_scope,
    COUNT(*) AS selected_candidate_count,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'top_hidden_gem') AS top_hidden_gem_count,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'strong_hidden_gem') AS strong_hidden_gem_count,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'promising_hidden_gem') AS promising_hidden_gem_count,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'exploratory_hidden_gem') AS exploratory_hidden_gem_count,
    ROUND(AVG(hidden_gem_score), 5) AS avg_hidden_gem_score,
    MAX(hidden_gem_score) AS max_hidden_gem_score,
    SUM(mention_count) AS total_candidate_mentions,
    SUM(review_count) AS total_candidate_reviews,
    ROUND(AVG(positive_ratio), 6) AS avg_positive_ratio,
    ROUND(AVG(negative_ratio), 6) AS avg_negative_ratio,
    (ARRAY_AGG(dish_name ORDER BY hidden_gem_score DESC, hidden_gem_selected_rank NULLS LAST))[1] AS top_dish_name,
    (ARRAY_AGG(hidden_gem_tier ORDER BY hidden_gem_score DESC, hidden_gem_selected_rank NULLS LAST))[1] AS top_hidden_gem_tier,
    (ARRAY_AGG(ranking_explanation ORDER BY hidden_gem_score DESC, hidden_gem_selected_rank NULLS LAST))[1] AS top_ranking_explanation
FROM selected_candidates
GROUP BY
    place_id,
    place_name,
    address_text,
    latitude,
    longitude,
    ranking_scope
ORDER BY max_hidden_gem_score DESC, selected_candidate_count DESC, place_name;

COMMENT ON VIEW hidden_gems.vw_ai_hidden_gems_place_summary IS
'Resumen por local de candidatos Hidden Gems seleccionados, incluyendo mejor plato y conteos por tier.';

-- =========================================================
-- 6) vw_ai_hidden_gems_dish_summary
-- =========================================================
-- Resumen por plato seleccionado en el ranking.

CREATE VIEW hidden_gems.vw_ai_hidden_gems_dish_summary AS
WITH selected_candidates AS (
    SELECT *
    FROM hidden_gems.vw_ai_hidden_gem_candidate_detail
    WHERE is_selected = TRUE
)
SELECT
    dish_id,
    dish_name,
    dish_normalized_name,
    dish_language_code,
    ranking_scope,
    COUNT(*) AS selected_place_count,
    COUNT(DISTINCT place_id) AS distinct_places,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'top_hidden_gem') AS top_hidden_gem_count,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'strong_hidden_gem') AS strong_hidden_gem_count,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'promising_hidden_gem') AS promising_hidden_gem_count,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'exploratory_hidden_gem') AS exploratory_hidden_gem_count,
    ROUND(AVG(hidden_gem_score), 5) AS avg_hidden_gem_score,
    MAX(hidden_gem_score) AS max_hidden_gem_score,
    SUM(mention_count) AS total_mentions,
    SUM(review_count) AS total_reviews,
    ROUND(AVG(positive_ratio), 6) AS avg_positive_ratio,
    ROUND(AVG(negative_ratio), 6) AS avg_negative_ratio,
    (ARRAY_AGG(place_name ORDER BY hidden_gem_score DESC, hidden_gem_selected_rank NULLS LAST))[1] AS top_place_name,
    (ARRAY_AGG(address_text ORDER BY hidden_gem_score DESC, hidden_gem_selected_rank NULLS LAST))[1] AS top_place_address,
    (ARRAY_AGG(ranking_explanation ORDER BY hidden_gem_score DESC, hidden_gem_selected_rank NULLS LAST))[1] AS top_ranking_explanation
FROM selected_candidates
GROUP BY
    dish_id,
    dish_name,
    dish_normalized_name,
    dish_language_code,
    ranking_scope
ORDER BY max_hidden_gem_score DESC, selected_place_count DESC, dish_name;

COMMENT ON VIEW hidden_gems.vw_ai_hidden_gems_dish_summary IS
'Resumen por plato de candidatos Hidden Gems seleccionados.';

-- =========================================================
-- 7) vw_ai_hidden_gems_city_summary
-- =========================================================
-- Resumen geográfico simple a partir de direcciones, útil para el prototipo Yelp.
-- Nota: el core place no tiene columnas city/state; se derivan desde address_text
-- solo como ayuda exploratoria para Yelp. Para Sevilla real se usará neighborhood.

CREATE VIEW hidden_gems.vw_ai_hidden_gems_city_summary AS
WITH selected_candidates AS (
    SELECT *
    FROM hidden_gems.vw_ai_hidden_gem_candidate_detail
    WHERE is_selected = TRUE
), address_parts AS (
    SELECT
        *,
        NULLIF(BTRIM(SPLIT_PART(address_text, ',', 2)), '') AS inferred_city,
        NULLIF(BTRIM(SPLIT_PART(address_text, ',', 3)), '') AS inferred_state_zip
    FROM selected_candidates
)
SELECT
    ranking_scope,
    inferred_city,
    inferred_state_zip,
    COUNT(*) AS selected_candidate_count,
    COUNT(DISTINCT place_id) AS distinct_places,
    COUNT(DISTINCT dish_id) AS distinct_dishes,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'top_hidden_gem') AS top_hidden_gem_count,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'strong_hidden_gem') AS strong_hidden_gem_count,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'promising_hidden_gem') AS promising_hidden_gem_count,
    COUNT(*) FILTER (WHERE hidden_gem_tier = 'exploratory_hidden_gem') AS exploratory_hidden_gem_count,
    ROUND(AVG(hidden_gem_score), 5) AS avg_hidden_gem_score,
    MAX(hidden_gem_score) AS max_hidden_gem_score,
    (ARRAY_AGG(place_name ORDER BY hidden_gem_score DESC, hidden_gem_selected_rank NULLS LAST))[1] AS top_place_name,
    (ARRAY_AGG(dish_name ORDER BY hidden_gem_score DESC, hidden_gem_selected_rank NULLS LAST))[1] AS top_dish_name,
    (ARRAY_AGG(ranking_explanation ORDER BY hidden_gem_score DESC, hidden_gem_selected_rank NULLS LAST))[1] AS top_ranking_explanation
FROM address_parts
GROUP BY
    ranking_scope,
    inferred_city,
    inferred_state_zip
ORDER BY max_hidden_gem_score DESC, selected_candidate_count DESC;

COMMENT ON VIEW hidden_gems.vw_ai_hidden_gems_city_summary IS
'Resumen exploratorio por ciudad/estado inferidos desde address_text. En producción Sevilla se priorizarán neighborhood y district.';

-- =========================================================
-- 8) vw_ai_dish_mentions_with_sentiment
-- =========================================================
-- Vista de auditoría: menciones individuales con sentimiento, review,
-- local y plato. Es la vista más útil para explicar por qué un plato
-- obtuvo buena o mala señal.

CREATE VIEW hidden_gems.vw_ai_dish_mentions_with_sentiment AS
SELECT
    dm.dish_mention_id,
    dms.dish_mention_sentiment_id,
    dm.ai_pipeline_run_id AS mention_ai_pipeline_run_id,
    dms.ai_pipeline_run_id AS sentiment_ai_pipeline_run_id,
    apr_m.run_code AS mention_ai_run_code,
    apr_s.run_code AS sentiment_ai_run_code,

    p.place_id,
    COALESCE(p.display_name, p.canonical_name) AS place_name,
    p.address_text,
    p.latitude,
    p.longitude,

    ds.dish_id,
    ds.canonical_name AS dish_name,
    ds.normalized_name AS dish_normalized_name,

    r.review_id,
    r.source_review_id,
    r.source_place_record_id,
    r.rating_value,
    r.review_language,
    r.review_created_at,
    r.review_text_raw,
    r.review_text_normalized,
    r.is_training_eligible,
    r.is_operational_review,

    dm.mention_text,
    dm.mention_normalized,
    dm.start_char,
    dm.end_char,
    dm.start_token,
    dm.end_token,
    dm.token_count,
    dm.ner_confidence_mean,
    dm.ner_confidence_min,
    dm.ner_confidence_max,
    dm.normalization_status,
    dm.normalization_method,
    dm.normalization_confidence,
    dm.human_review_status AS mention_human_review_status,

    dms.sentiment_label,
    dms.sentiment_score,
    dms.sentiment_confidence,
    dms.sentiment_reliability_tier,
    dms.sentiment_reason,
    dms.sentiment_method,
    dms.context_sentence,
    dms.context_window,
    dms.target_clause_context,
    dms.near_mention_context,
    dms.positive_terms,
    dms.negative_terms,
    dms.flags AS sentiment_flags,
    dms.is_training_candidate,
    dms.human_review_status AS sentiment_human_review_status,

    CASE
        WHEN dms.sentiment_label = 'positive' THEN 1
        WHEN dms.sentiment_label = 'neutral' THEN 0
        WHEN dms.sentiment_label = 'negative' THEN -1
        ELSE NULL
    END AS sentiment_label_numeric,

    dm.created_at AS mention_created_at,
    dms.created_at AS sentiment_created_at
FROM hidden_gems.dish_mention dm
JOIN hidden_gems.dish_mention_sentiment dms
    ON dms.dish_mention_id = dm.dish_mention_id
JOIN hidden_gems.review r
    ON r.review_id = dm.review_id
JOIN hidden_gems.place p
    ON p.place_id = dm.place_id
LEFT JOIN hidden_gems.dish ds
    ON ds.dish_id = dm.dish_id
LEFT JOIN hidden_gems.ai_pipeline_run apr_m
    ON apr_m.ai_pipeline_run_id = dm.ai_pipeline_run_id
LEFT JOIN hidden_gems.ai_pipeline_run apr_s
    ON apr_s.ai_pipeline_run_id = dms.ai_pipeline_run_id;

COMMENT ON VIEW hidden_gems.vw_ai_dish_mentions_with_sentiment IS
'Auditoría de menciones de platos con sentimiento aspect-based, enlazadas con review, place y dish.';

-- =========================================================
-- 9) Consultas de referencia rápida en comentarios
-- =========================================================

COMMENT ON SCHEMA hidden_gems IS
'Hidden Gems: esquema principal con datos fuente, core canónico, geografía, calidad y capa IA.';

-- Ejemplos de uso:
--
-- Top 20 prototipo Yelp:
-- SELECT *
-- FROM hidden_gems.vw_ai_hidden_gems_yelp_top
-- LIMIT 20;
--
-- Mejores platos por local:
-- SELECT *
-- FROM hidden_gems.vw_ai_hidden_gems_place_summary
-- LIMIT 20;
--
-- Platos más seleccionados:
-- SELECT *
-- FROM hidden_gems.vw_ai_hidden_gems_dish_summary
-- ORDER BY selected_place_count DESC, max_hidden_gem_score DESC
-- LIMIT 20;
--
-- Evidencia textual de un candidato concreto:
-- SELECT *
-- FROM hidden_gems.vw_ai_dish_mentions_with_sentiment
-- WHERE place_name = 'Sushi Ushi'
--   AND dish_name = 'sushi'
-- ORDER BY sentiment_confidence DESC
-- LIMIT 25;

