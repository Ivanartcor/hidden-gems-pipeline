"""
Dashboard Streamlit - Hidden Gems Sevilla IA v2

Uso recomendado desde la raíz del repositorio:

    streamlit run dashboard/streamlit_sevilla_v2_app.py

Datos esperados por defecto:

    data/artifacts/ai/sevilla/dashboard_v2/

Este dashboard consume el export generado por:

    scripts/export_sevilla_dashboard_data_v2.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# Configuración visual
# ============================================================

APP_TITLE = "Hidden Gems Sevilla IA v2"
DEFAULT_DATA_DIR = Path("data/artifacts/ai/sevilla/dashboard_v2")

TIER_ORDER = [
    "top_hidden_gem",
    "strong_hidden_gem",
    "promising_hidden_gem",
    "exploratory_hidden_gem",
]

EVIDENCE_ORDER = ["strong", "solid", "emerging", "weak", "unknown"]
QUALITY_ORDER = ["high", "medium", "low", "unknown"]
SENTIMENT_ORDER = ["positive", "neutral", "negative"]

TIER_LABELS = {
    "top_hidden_gem": "Top Hidden Gem",
    "strong_hidden_gem": "Strong",
    "promising_hidden_gem": "Promising",
    "exploratory_hidden_gem": "Exploratory",
    "not_selected": "No seleccionado",
}

EVIDENCE_LABELS = {
    "strong": "Fuerte",
    "solid": "Sólida",
    "emerging": "Emergente",
    "weak": "Débil",
    "unknown": "Sin clasificar",
}

QUALITY_LABELS = {
    "high": "Alta",
    "medium": "Media",
    "low": "Baja",
    "unknown": "Sin clasificar",
}


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)


CUSTOM_CSS = """
<style>
:root {
    --hg-bg: #0b1020;
    --hg-panel: rgba(255, 255, 255, 0.055);
    --hg-panel-border: rgba(255, 255, 255, 0.12);
    --hg-text-muted: rgba(255, 255, 255, 0.66);
    --hg-accent: #70e1f5;
    --hg-accent-2: #ffd194;
    --hg-green: #2ee59d;
    --hg-red: #ff6b6b;
    --hg-purple: #b892ff;
}

.block-container {
    padding-top: 1.4rem;
    padding-bottom: 3rem;
}

.hg-hero {
    padding: 1.35rem 1.45rem;
    border: 1px solid var(--hg-panel-border);
    border-radius: 24px;
    background: radial-gradient(circle at 10% 10%, rgba(112, 225, 245, 0.22), transparent 32%),
                radial-gradient(circle at 90% 20%, rgba(255, 209, 148, 0.18), transparent 30%),
                linear-gradient(135deg, rgba(16, 23, 43, 0.98), rgba(8, 11, 24, 0.98));
    box-shadow: 0 18px 50px rgba(0,0,0,0.28);
    margin-bottom: 1.1rem;
}

.hg-hero h1 {
    margin: 0;
    font-size: 2.2rem;
    letter-spacing: -0.04em;
}

.hg-hero p {
    margin-top: 0.55rem;
    margin-bottom: 0;
    color: var(--hg-text-muted);
    font-size: 1rem;
    max-width: 1100px;
}

.hg-chip-row {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-top: 0.85rem;
}

.hg-chip {
    border: 1px solid rgba(255,255,255,0.14);
    background: rgba(255,255,255,0.06);
    color: rgba(255,255,255,0.9);
    border-radius: 999px;
    padding: 0.28rem 0.62rem;
    font-size: 0.82rem;
}

.hg-card {
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 20px;
    padding: 1rem 1.05rem;
    background: linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.025));
    box-shadow: 0 10px 30px rgba(0,0,0,0.16);
    margin-bottom: 0.75rem;
}

.hg-card h3 {
    margin-top: 0;
    margin-bottom: 0.35rem;
    font-size: 1.05rem;
}

.hg-card p {
    color: var(--hg-text-muted);
    margin: 0.25rem 0;
}

.hg-kpi {
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 18px;
    padding: 1rem;
    min-height: 118px;
    background: linear-gradient(180deg, rgba(255,255,255,0.075), rgba(255,255,255,0.035));
}

.hg-kpi .label {
    color: var(--hg-text-muted);
    font-size: 0.82rem;
    line-height: 1.2;
}

.hg-kpi .value {
    margin-top: 0.4rem;
    font-size: 1.72rem;
    font-weight: 800;
    letter-spacing: -0.03em;
}

.hg-kpi .sub {
    margin-top: 0.25rem;
    color: rgba(255,255,255,0.58);
    font-size: 0.76rem;
}

.hg-pill {
    display: inline-block;
    padding: 0.18rem 0.52rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(255,255,255,0.06);
}

.hg-pill-top { background: rgba(255, 209, 148, 0.16); color: #ffd194; }
.hg-pill-strong { background: rgba(46, 229, 157, 0.14); color: #2ee59d; }
.hg-pill-promising { background: rgba(112, 225, 245, 0.14); color: #70e1f5; }
.hg-pill-exploratory { background: rgba(184, 146, 255, 0.14); color: #b892ff; }
.hg-pill-low { background: rgba(255, 107, 107, 0.14); color: #ff8b8b; }

.hg-muted { color: var(--hg-text-muted); }
.hg-small { font-size: 0.83rem; }
.hg-divider { height: 1px; background: rgba(255,255,255,0.10); margin: 0.8rem 0; }

[data-testid="stMetricValue"] {
    font-size: 1.65rem;
}

.stDataFrame {
    border-radius: 16px;
    overflow: hidden;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================
# Utilidades generales
# ============================================================

def as_path(value: str | Path) -> Path:
    return Path(str(value)).expanduser().resolve() if str(value).strip() else DEFAULT_DATA_DIR.resolve()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def read_csv(path: Path, default: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    if default is None:
        default = pd.DataFrame()
    if not path.exists():
        return default
    try:
        return pd.read_csv(path)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def fmt_int(value: Any) -> str:
    return f"{safe_int(value):,}".replace(",", ".")


def fmt_float(value: Any, digits: int = 2) -> str:
    return f"{safe_float(value):.{digits}f}"


def fmt_pct(value: Any, digits: int = 1) -> str:
    return f"{safe_float(value) * 100:.{digits}f}%"


def non_empty_values(series: pd.Series) -> List[str]:
    if series is None or len(series) == 0:
        return []
    values = [str(v) for v in series.dropna().unique().tolist() if str(v).strip() and str(v).lower() != "nan"]
    return sorted(values)


def ordered_values(values: Iterable[str], preferred_order: List[str]) -> List[str]:
    values = list(values)
    preferred = [v for v in preferred_order if v in values]
    rest = sorted([v for v in values if v not in preferred])
    return preferred + rest


def has_cols(df: pd.DataFrame, cols: Iterable[str]) -> bool:
    return all(c in df.columns for c in cols)


def first_col(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def tier_label(value: Any) -> str:
    return TIER_LABELS.get(str(value), str(value))


def evidence_label(value: Any) -> str:
    return EVIDENCE_LABELS.get(str(value), str(value))


def quality_label(value: Any) -> str:
    return QUALITY_LABELS.get(str(value), str(value))


def pill_html(value: Any, kind: str = "tier") -> str:
    raw = str(value)
    if kind == "tier":
        label = tier_label(raw)
        css = {
            "top_hidden_gem": "hg-pill-top",
            "strong_hidden_gem": "hg-pill-strong",
            "promising_hidden_gem": "hg-pill-promising",
            "exploratory_hidden_gem": "hg-pill-exploratory",
        }.get(raw, "")
    elif kind == "quality":
        label = quality_label(raw)
        css = "hg-pill-strong" if raw == "high" else "hg-pill-exploratory" if raw == "medium" else "hg-pill-low"
    elif kind == "evidence":
        label = evidence_label(raw)
        css = "hg-pill-strong" if raw == "strong" else "hg-pill-promising" if raw == "solid" else "hg-pill-exploratory"
    else:
        label = raw
        css = ""
    return f'<span class="hg-pill {css}">{label}</span>'


def render_kpi(label: str, value: Any, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="hg-kpi">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            <div class="sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == "float64":
            out[col] = out[col].round(4)
    return out


def pick_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    return df[[c for c in columns if c in df.columns]].copy()


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


# ============================================================
# Coordenadas y mapas
# ============================================================

PATCH_ID = "streamlit_sevilla_v2_real_coordinates_map_and_reviews_2026_05_15"

COORD_LAT_CANDIDATES = [
    "latitude_std", "latitude", "lat", "place_latitude", "place_latitude_std", "y", "Y",
]
COORD_LON_CANDIDATES = [
    "longitude_std", "longitude", "lon", "lng", "place_longitude", "place_longitude_std", "x", "X",
]

# Centroides aproximados solo como fallback visual cuando no existan coordenadas reales.
DISTRICT_CENTROIDS = {
    "Casco Antiguo": (37.3891, -5.9941),
    "Triana": (37.3826, -6.0061),
    "Los Remedios": (37.3745, -6.0034),
    "Nervión": (37.3831, -5.9735),
    "Sur": (37.3617, -5.9798),
    "Bellavista - La Palmera": (37.3427, -5.9821),
    "Cerro - Amate": (37.3766, -5.9469),
    "San Pablo - Santa Justa": (37.3944, -5.9633),
    "Macarena": (37.4071, -5.9867),
    "Norte": (37.4289, -5.9812),
    "Este - Alcosa - Torreblanca": (37.4045, -5.9055),
}


def detect_coord_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """Return the most likely latitude/longitude columns present in a dataframe."""
    lat_col = first_col(df, COORD_LAT_CANDIDATES)
    lon_col = first_col(df, COORD_LON_CANDIDATES)
    return lat_col, lon_col


def normalize_coordinate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure latitude_std/longitude_std exist when any coordinate-like columns are present."""
    if df is None or df.empty:
        return df
    out = df.copy()
    lat_col, lon_col = detect_coord_columns(out)
    if lat_col and lon_col:
        out["latitude_std"] = pd.to_numeric(out[lat_col], errors="coerce")
        out["longitude_std"] = pd.to_numeric(out[lon_col], errors="coerce")
        if "coordinate_source_std" not in out.columns:
            out["coordinate_source_std"] = "source_columns"
    return out


def merge_coordinates_from_reference(df: pd.DataFrame, coords: pd.DataFrame) -> pd.DataFrame:
    """Propagate coordinates from place_coordinates.csv when the main dataframe lacks them."""
    if df is None or df.empty:
        return df
    out = normalize_coordinate_columns(df)
    if "latitude_std" in out.columns and "longitude_std" in out.columns and out["latitude_std"].notna().any():
        return out
    if coords is None or coords.empty:
        return out

    coords_norm = normalize_coordinate_columns(coords)
    if "latitude_std" not in coords_norm.columns or "longitude_std" not in coords_norm.columns:
        return out

    join_keys = []
    if "place_id_std" in out.columns and "place_id_std" in coords_norm.columns:
        join_keys = ["place_id_std"]
    elif "place_id" in out.columns and "place_id_std" in coords_norm.columns:
        out["place_id_std"] = out["place_id"].astype(str)
        join_keys = ["place_id_std"]
    elif "place_name_std" in out.columns and "place_name_std" in coords_norm.columns:
        join_keys = ["place_name_std"]

    if not join_keys:
        return out

    keep_cols = join_keys + ["latitude_std", "longitude_std"]
    if "coordinate_source_std" in coords_norm.columns:
        keep_cols.append("coordinate_source_std")

    coords_small = coords_norm[keep_cols].drop_duplicates(subset=join_keys)
    suffix_cols = {"latitude_std": "latitude_std_ref", "longitude_std": "longitude_std_ref", "coordinate_source_std": "coordinate_source_std_ref"}
    coords_small = coords_small.rename(columns={c: suffix_cols[c] for c in coords_small.columns if c in suffix_cols})

    merged = out.merge(coords_small, on=join_keys, how="left")
    if "latitude_std" not in merged.columns:
        merged["latitude_std"] = np.nan
    if "longitude_std" not in merged.columns:
        merged["longitude_std"] = np.nan

    merged["latitude_std"] = pd.to_numeric(merged["latitude_std"], errors="coerce").combine_first(
        pd.to_numeric(merged.get("latitude_std_ref"), errors="coerce")
    )
    merged["longitude_std"] = pd.to_numeric(merged["longitude_std"], errors="coerce").combine_first(
        pd.to_numeric(merged.get("longitude_std_ref"), errors="coerce")
    )

    if "coordinate_source_std" not in merged.columns:
        merged["coordinate_source_std"] = ""
    if "coordinate_source_std_ref" in merged.columns:
        merged["coordinate_source_std"] = merged["coordinate_source_std"].where(
            merged["coordinate_source_std"].astype(str).str.strip() != "",
            merged["coordinate_source_std_ref"],
        )

    return merged.drop(columns=[c for c in ["latitude_std_ref", "longitude_std_ref", "coordinate_source_std_ref"] if c in merged.columns])


def add_fallback_centroids(df: pd.DataFrame) -> pd.DataFrame:
    """Add fallback coordinates when real coordinates are absent. These are marked as approximate."""
    if df is None or df.empty:
        return df
    out = df.copy()
    if "latitude_std" not in out.columns:
        out["latitude_std"] = np.nan
    if "longitude_std" not in out.columns:
        out["longitude_std"] = np.nan
    if "coordinate_source_std" not in out.columns:
        out["coordinate_source_std"] = ""

    for district, (lat, lon) in DISTRICT_CENTROIDS.items():
        mask = (
            out["latitude_std"].isna()
            & out["longitude_std"].isna()
            & out.get("district_name_std", pd.Series(index=out.index, dtype=str)).astype(str).eq(district)
        )
        # Pequeño jitter determinista por barrio/local para que los puntos no se pisen totalmente.
        jitter_seed = out.loc[mask, "place_name_std"].astype(str) if "place_name_std" in out.columns else pd.Series("", index=out.loc[mask].index)
        jitter = jitter_seed.map(lambda x: (abs(hash(x)) % 1000) / 1000.0 - 0.5)
        out.loc[mask, "latitude_std"] = lat + jitter * 0.012
        out.loc[mask, "longitude_std"] = lon + jitter * 0.012
        out.loc[mask, "coordinate_source_std"] = "approx_district_centroid"

    return out


def build_place_map_dataframe(df: pd.DataFrame, use_fallback: bool = True) -> pd.DataFrame:
    """Aggregate selected/ranking rows to one marker per place for the territorial map."""
    if df is None or df.empty:
        return pd.DataFrame()
    work = normalize_coordinate_columns(df)
    if use_fallback:
        work = add_fallback_centroids(work)

    required = ["latitude_std", "longitude_std"]
    if not has_cols(work, required):
        return pd.DataFrame()

    work["latitude_std"] = pd.to_numeric(work["latitude_std"], errors="coerce")
    work["longitude_std"] = pd.to_numeric(work["longitude_std"], errors="coerce")
    work = work.dropna(subset=["latitude_std", "longitude_std"])
    if work.empty:
        return work

    group_cols = [
        c for c in [
            "place_id_std", "place_name_std", "district_name_std", "neighborhood_name_std",
            "latitude_std", "longitude_std", "coordinate_source_std",
        ] if c in work.columns
    ]
    agg = (
        work.groupby(group_cols, dropna=False)
        .agg(
            candidate_count=("dashboard_candidate_key", "count"),
            dishes=("dish_name_std", lambda s: ", ".join(sorted(set([str(x) for x in s.dropna().head(8)])))),
            best_score=("score_std", "max"),
            avg_score=("score_std", "mean"),
            total_mentions=("mention_count_std", "sum"),
            total_reviews=("review_count_std", "sum"),
            top_tier=("tier_std", lambda s: next((x for x in TIER_ORDER if x in set(s.astype(str))), str(s.iloc[0]) if len(s) else "")),
            best_evidence=("evidence_tier_std", lambda s: next((x for x in EVIDENCE_ORDER if x in set(s.astype(str))), str(s.iloc[0]) if len(s) else "")),
            best_quality=("quality_tier_std", lambda s: next((x for x in QUALITY_ORDER if x in set(s.astype(str))), str(s.iloc[0]) if len(s) else "")),
        )
        .reset_index()
    )
    agg["marker_size"] = np.clip(pd.to_numeric(agg["candidate_count"], errors="coerce").fillna(1) * 6 + 8, 10, 42)
    return agg



# ============================================================
# Carga de datos
# ============================================================

@st.cache_data(show_spinner=False)
def load_dashboard_data(data_dir_str: str) -> Dict[str, Any]:
    data_dir = Path(data_dir_str)

    data = {
        "data_dir": data_dir,
        "summary": read_json(data_dir / "dashboard_export_summary.json", {}),
        "metadata": read_json(data_dir / "dashboard_metadata.json", {}),
        "contract": read_json(data_dir / "data_contract.json", {}),
        "kpis": read_json(data_dir / "kpi_summary.json", {}),
        "filters": read_json(data_dir / "filter_options.json", {}),
        "ranking": read_csv(data_dir / "ranking_detail.csv"),
        "selected": read_csv(data_dir / "selected_candidates.csv"),
        "top_global": read_csv(data_dir / "top_global.csv"),
        "top_by_district": read_csv(data_dir / "top_by_district.csv"),
        "top_by_neighborhood": read_csv(data_dir / "top_by_neighborhood.csv"),
        "top_by_dish": read_csv(data_dir / "top_by_dish.csv"),
        "district_summary": read_csv(data_dir / "district_summary.csv"),
        "neighborhood_summary": read_csv(data_dir / "neighborhood_summary.csv"),
        "dish_summary": read_csv(data_dir / "dish_summary.csv"),
        "place_summary": read_csv(data_dir / "place_summary.csv"),
        "tier_summary": read_csv(data_dir / "tier_summary.csv"),
        "evidence_summary": read_csv(data_dir / "evidence_summary.csv"),
        "quality_summary": read_csv(data_dir / "quality_summary.csv"),
        "mentions": read_csv(data_dir / "mention_examples.csv"),
        "place_coordinates": read_csv(data_dir / "place_coordinates.csv"),
        "comparison_summary": read_json(data_dir / "comparison" / "sevilla_ranking_v1_vs_v2_summary.json", {}),
        "ranking_overlap": read_csv(data_dir / "comparison" / "ranking_overlap.csv"),
        "v2_only": read_csv(data_dir / "comparison" / "v2_only_candidates.csv"),
        "v1_only": read_csv(data_dir / "comparison" / "v1_only_candidates.csv"),
        "score_shift": read_csv(data_dir / "comparison" / "score_shift_comparison.csv"),
        "tier_shift": read_csv(data_dir / "comparison" / "tier_shift_summary.csv"),
        "top_district_shift": read_csv(data_dir / "comparison" / "top_district_shift.csv"),
        "top_neighborhood_shift": read_csv(data_dir / "comparison" / "top_neighborhood_shift.csv"),
        "top_dish_shift": read_csv(data_dir / "comparison" / "top_dish_shift.csv"),
    }

    # Normalizar score y coordenadas. Si el export trae place_coordinates.csv, las propagamos
    # a ranking/selected/top_global/mentions para que el mapa use coordenadas reales.
    coords = data.get("place_coordinates", pd.DataFrame())
    for key in ["ranking", "selected", "top_global", "top_by_district", "top_by_neighborhood", "top_by_dish", "mentions"]:
        if isinstance(data.get(key), pd.DataFrame):
            if "score_std" in data[key].columns:
                data[key]["score_std"] = pd.to_numeric(data[key]["score_std"], errors="coerce")
            data[key] = merge_coordinates_from_reference(data[key], coords)

    return data


# ============================================================
# Filtros
# ============================================================

def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()

    def apply_multiselect(col: str, values: List[str]) -> None:
        nonlocal out
        if values and col in out.columns:
            out = out[out[col].astype(str).isin(values)]

    apply_multiselect("district_name_std", filters.get("districts", []))
    apply_multiselect("neighborhood_name_std", filters.get("neighborhoods", []))
    apply_multiselect("dish_name_std", filters.get("dishes", []))
    apply_multiselect("place_name_std", filters.get("places", []))
    apply_multiselect("tier_std", filters.get("tiers", []))
    apply_multiselect("evidence_tier_std", filters.get("evidence_tiers", []))
    apply_multiselect("quality_tier_std", filters.get("quality_tiers", []))

    if "score_std" in out.columns:
        min_score, max_score = filters.get("score_range", (None, None))
        if min_score is not None:
            out = out[out["score_std"].fillna(-999) >= float(min_score)]
        if max_score is not None:
            out = out[out["score_std"].fillna(999) <= float(max_score)]

    if "mention_count_std" in out.columns:
        out = out[pd.to_numeric(out["mention_count_std"], errors="coerce").fillna(0) >= filters.get("min_mentions", 0)]

    if "review_count_std" in out.columns:
        out = out[pd.to_numeric(out["review_count_std"], errors="coerce").fillna(0) >= filters.get("min_reviews", 0)]

    search = str(filters.get("search", "") or "").strip().lower()
    if search:
        search_cols = [
            "place_name_std",
            "dish_name_std",
            "district_name_std",
            "neighborhood_name_std",
            "explanation_std",
        ]
        mask = pd.Series(False, index=out.index)
        for col in search_cols:
            if col in out.columns:
                mask = mask | out[col].astype(str).str.lower().str.contains(search, na=False)
        out = out[mask]

    return out


def build_sidebar_filters(base_df: pd.DataFrame, summary: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, Path]:
    st.sidebar.title("💎 Hidden Gems IA v2")
    st.sidebar.caption("Ranking experimental asistido por modelos")

    data_dir_input = st.sidebar.text_input(
        "Carpeta de datos del dashboard",
        value=str(DEFAULT_DATA_DIR),
        help="Debe contener dashboard_export_summary.json, selected_candidates.csv, ranking_detail.csv, etc.",
    )
    data_dir = Path(data_dir_input)

    st.sidebar.markdown("---")
    selected_only = st.sidebar.toggle("Mostrar solo candidatos seleccionados", value=True)

    search = st.sidebar.text_input("Buscar local, plato, barrio o explicación", value="")

    districts = non_empty_values(base_df.get("district_name_std", pd.Series(dtype=str)))
    selected_districts = st.sidebar.multiselect("Distrito", districts, default=[])

    neighborhood_df = base_df.copy()
    if selected_districts and "district_name_std" in neighborhood_df.columns:
        neighborhood_df = neighborhood_df[neighborhood_df["district_name_std"].astype(str).isin(selected_districts)]
    neighborhoods = non_empty_values(neighborhood_df.get("neighborhood_name_std", pd.Series(dtype=str)))
    selected_neighborhoods = st.sidebar.multiselect("Barrio", neighborhoods, default=[])

    dishes = non_empty_values(base_df.get("dish_name_std", pd.Series(dtype=str)))
    selected_dishes = st.sidebar.multiselect("Plato", dishes, default=[])

    places = non_empty_values(base_df.get("place_name_std", pd.Series(dtype=str)))
    selected_places = st.sidebar.multiselect("Local", places, default=[])

    tiers = ordered_values(non_empty_values(base_df.get("tier_std", pd.Series(dtype=str))), TIER_ORDER)
    selected_tiers = st.sidebar.multiselect(
        "Tier Hidden Gem",
        tiers,
        default=tiers,
        format_func=tier_label,
    )

    evidence_tiers = ordered_values(non_empty_values(base_df.get("evidence_tier_std", pd.Series(dtype=str))), EVIDENCE_ORDER)
    selected_evidence = st.sidebar.multiselect(
        "Evidencia",
        evidence_tiers,
        default=evidence_tiers,
        format_func=evidence_label,
    )

    quality_tiers = ordered_values(non_empty_values(base_df.get("quality_tier_std", pd.Series(dtype=str))), QUALITY_ORDER)
    selected_quality = st.sidebar.multiselect(
        "Calidad agregada",
        quality_tiers,
        default=quality_tiers,
        format_func=quality_label,
    )

    if "score_std" in base_df.columns and not base_df["score_std"].dropna().empty:
        score_min = float(np.floor(base_df["score_std"].min()))
        score_max = float(np.ceil(base_df["score_std"].max()))
    else:
        score_min, score_max = 0.0, 100.0

    score_range = st.sidebar.slider(
        "Rango de score v2",
        min_value=float(score_min),
        max_value=float(score_max),
        value=(float(score_min), float(score_max)),
        step=0.5,
    )

    min_mentions = st.sidebar.slider("Mínimo menciones", 0, 20, 0, 1)
    min_reviews = st.sidebar.slider("Mínimo reviews", 0, 20, 0, 1)

    st.sidebar.markdown("---")
    warnings = summary.get("warnings", []) if isinstance(summary, dict) else []
    if warnings:
        with st.sidebar.expander("Avisos del export", expanded=False):
            for warning in warnings:
                st.warning(warning)

    return {
        "search": search,
        "districts": selected_districts,
        "neighborhoods": selected_neighborhoods,
        "dishes": selected_dishes,
        "places": selected_places,
        "tiers": selected_tiers,
        "evidence_tiers": selected_evidence,
        "quality_tiers": selected_quality,
        "score_range": score_range,
        "min_mentions": min_mentions,
        "min_reviews": min_reviews,
    }, selected_only, data_dir


# ============================================================
# Componentes gráficos
# ============================================================

def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    orientation: str = "v",
    color: Optional[str] = None,
    text: Optional[str] = None,
    key: str = "bar_chart",
    height: int = 420,
) -> None:
    if df.empty or x not in df.columns or y not in df.columns:
        st.info("No hay datos suficientes para este gráfico.")
        return

    fig = px.bar(
        df,
        x=x if orientation == "v" else y,
        y=y if orientation == "v" else x,
        color=color if color in df.columns else None,
        text=text if text in df.columns else None,
        orientation=orientation,
        title=title,
        height=height,
    )
    fig.update_layout(
        margin=dict(l=8, r=8, t=55, b=8),
        legend_title_text="",
        xaxis_title="",
        yaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def pie_chart(df: pd.DataFrame, names: str, values: str, title: str, key: str) -> None:
    if df.empty or names not in df.columns or values not in df.columns:
        st.info("No hay datos suficientes para este gráfico.")
        return
    fig = px.pie(df, names=names, values=values, hole=0.48, title=title)
    fig.update_layout(margin=dict(l=8, r=8, t=55, b=8), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True, key=key)


def histogram(df: pd.DataFrame, col: str, title: str, key: str, bins: int = 30) -> None:
    if df.empty or col not in df.columns:
        st.info("No hay datos suficientes para este gráfico.")
        return
    fig = px.histogram(df, x=col, nbins=bins, title=title, height=390)
    fig.update_layout(margin=dict(l=8, r=8, t=55, b=8), xaxis_title="", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True, key=key)


def scatter_chart(df: pd.DataFrame, x: str, y: str, title: str, color: Optional[str], hover_cols: List[str], key: str) -> None:
    if df.empty or x not in df.columns or y not in df.columns:
        st.info("No hay datos suficientes para este gráfico.")
        return
    fig = px.scatter(
        df,
        x=x,
        y=y,
        color=color if color in df.columns else None,
        hover_data=[c for c in hover_cols if c in df.columns],
        title=title,
        height=440,
    )
    fig.update_layout(margin=dict(l=8, r=8, t=55, b=8), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True, key=key)


def treemap_chart(df: pd.DataFrame, path_cols: List[str], values: str, color: str, title: str, key: str) -> None:
    cols = [c for c in path_cols if c in df.columns]
    if df.empty or not cols or values not in df.columns:
        st.info("No hay datos suficientes para este gráfico.")
        return
    fig = px.treemap(
        df,
        path=cols,
        values=values,
        color=color if color in df.columns else None,
        title=title,
        height=520,
    )
    fig.update_layout(margin=dict(l=8, r=8, t=55, b=8))
    st.plotly_chart(fig, use_container_width=True, key=key)


# ============================================================
# Secciones del dashboard
# ============================================================

def render_header(summary: Dict[str, Any]) -> None:
    generated_at = summary.get("generated_at", "") if isinstance(summary, dict) else ""
    st.markdown(
        f"""
        <div class="hg-hero">
            <h1>💎 Hidden Gems Sevilla IA v2</h1>
            <p>
                Dashboard experimental para descubrir platos destacados por barrio usando NER entrenado,
                normalización/entity linking con reranker y sentimiento ABSA por mención.
            </p>
            <div class="hg-chip-row">
                <span class="hg-chip">Ranking IA v2</span>
                <span class="hg-chip">Modelo asistido</span>
                <span class="hg-chip">No production-ready</span>
                <span class="hg-chip">Generado: {generated_at[:19] if generated_at else "sin fecha"}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_grid(df: pd.DataFrame, kpis: Dict[str, Any]) -> None:
    selected_candidates = len(df)
    selected_places = df["place_id_std"].nunique() if "place_id_std" in df.columns else 0
    selected_dishes = df["dish_id_std"].nunique() if "dish_id_std" in df.columns else 0
    selected_neighborhoods = df["neighborhood_name_std"].nunique() if "neighborhood_name_std" in df.columns else 0
    selected_districts = df["district_name_std"].nunique() if "district_name_std" in df.columns else 0
    avg_score = df["score_std"].mean() if "score_std" in df.columns and len(df) else 0
    mentions = df["mention_count_std"].sum() if "mention_count_std" in df.columns else 0
    reviews = df["review_count_std"].sum() if "review_count_std" in df.columns else 0

    cols = st.columns(4)
    with cols[0]:
        render_kpi("Candidatos filtrados", fmt_int(selected_candidates), "place + dish seleccionados")
    with cols[1]:
        render_kpi("Locales", fmt_int(selected_places), f"{fmt_int(selected_neighborhoods)} barrios")
    with cols[2]:
        render_kpi("Platos", fmt_int(selected_dishes), f"{fmt_int(selected_districts)} distritos")
    with cols[3]:
        render_kpi("Score medio", fmt_float(avg_score, 2), f"{fmt_int(mentions)} menciones · {fmt_int(reviews)} reviews")

    comp = kpis.get("comparison", {}) if isinstance(kpis, dict) else {}
    if comp:
        cols = st.columns(4)
        with cols[0]:
            render_kpi("Cobertura v1 en v2", fmt_pct(comp.get("v1_coverage_in_v2", 0)), "candidatos v1 recuperados")
        with cols[1]:
            render_kpi("Solapamiento Jaccard", fmt_pct(comp.get("jaccard_overlap", 0)), "v1 vs v2")
        with cols[2]:
            render_kpi("Nuevos locales", f"+{fmt_int(comp.get('selected_places_delta_v2_minus_v1', 0))}", "delta v2 - v1")
        with cols[3]:
            render_kpi("Nuevos barrios", f"+{fmt_int(comp.get('selected_neighborhoods_delta_v2_minus_v1', 0))}", "delta v2 - v1")


def render_candidate_card(row: pd.Series, mentions_df: pd.DataFrame) -> None:
    place = row.get("place_name_std", "")
    dish = row.get("dish_name_std", "")
    score = fmt_float(row.get("score_std", 0), 1)
    tier = row.get("tier_std", "")
    evidence = row.get("evidence_tier_std", "")
    quality = row.get("quality_tier_std", "")
    district = row.get("district_name_std", "")
    neighborhood = row.get("neighborhood_name_std", "")
    mentions = fmt_int(row.get("mention_count_std", 0))
    reviews = fmt_int(row.get("review_count_std", 0))
    pos = fmt_pct(row.get("positive_ratio_std", 0))
    neg = fmt_pct(row.get("negative_ratio_std", 0))
    explanation = row.get("explanation_std", "")

    st.markdown(
        f"""
        <div class="hg-card">
            <h3>{dish} · {place}</h3>
            <p><b>Score:</b> {score}/100 · {pill_html(tier, "tier")} · {pill_html(evidence, "evidence")} · {pill_html(quality, "quality")}</p>
            <p><b>Zona:</b> {neighborhood} · {district}</p>
            <p><b>Evidencia:</b> {mentions} menciones · {reviews} reviews · {pos} positivas · {neg} negativas</p>
            <div class="hg-divider"></div>
            <p>{explanation if str(explanation).strip() else "Sin explicación generada."}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    candidate_key = row.get("dashboard_candidate_key", "")
    if not mentions_df.empty and "dashboard_candidate_key" in mentions_df.columns:
        examples = mentions_df[mentions_df["dashboard_candidate_key"].astype(str) == str(candidate_key)].copy()
        if not examples.empty:
            with st.expander("Ver ejemplos de reseñas/menciones", expanded=False):
                for _, ex in examples.head(5).iterrows():
                    sentiment = ex.get("sentiment_label_std", "")
                    conf = fmt_pct(ex.get("sentiment_confidence_std", 0))
                    context = ex.get("context_std", "")
                    full_review = ex.get("review_text_std", "")
                    rating = ex.get("rating_value_std", "")
                    mention = ex.get("mention_text_std", "")
                    st.markdown(
                        f"""
                        <div class="hg-card">
                            <p><b>Mención:</b> {mention} · <b>Sentimiento:</b> {sentiment} ({conf}) · <b>Rating:</b> {rating}</p>
                            <p><b>Contexto:</b> {context}</p>
                            <p class="hg-muted"><b>Review completa:</b> {full_review if str(full_review).strip() else "No disponible"}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


def render_overview(data: Dict[str, Any], filtered_df: pd.DataFrame) -> None:
    st.subheader("Resumen ejecutivo")
    render_kpi_grid(filtered_df, data.get("kpis", {}))

    st.markdown("### Distribución de selección")
    c1, c2, c3 = st.columns(3)
    with c1:
        tier_counts = filtered_df["tier_std"].value_counts().reindex(TIER_ORDER).dropna().reset_index()
        tier_counts.columns = ["tier_std", "selected_count"]
        tier_counts["tier_label"] = tier_counts["tier_std"].map(tier_label)
        pie_chart(tier_counts, "tier_label", "selected_count", "Tiers Hidden Gem", key="overview_tier_pie")
    with c2:
        evidence_counts = filtered_df["evidence_tier_std"].value_counts().reset_index() if "evidence_tier_std" in filtered_df.columns else pd.DataFrame()
        if not evidence_counts.empty:
            evidence_counts.columns = ["evidence_tier_std", "selected_count"]
            evidence_counts["evidence_label"] = evidence_counts["evidence_tier_std"].map(evidence_label)
        pie_chart(evidence_counts, "evidence_label", "selected_count", "Nivel de evidencia", key="overview_evidence_pie")
    with c3:
        quality_counts = filtered_df["quality_tier_std"].value_counts().reset_index() if "quality_tier_std" in filtered_df.columns else pd.DataFrame()
        if not quality_counts.empty:
            quality_counts.columns = ["quality_tier_std", "selected_count"]
            quality_counts["quality_label"] = quality_counts["quality_tier_std"].map(quality_label)
        pie_chart(quality_counts, "quality_label", "selected_count", "Calidad agregada", key="overview_quality_pie")

    c1, c2 = st.columns([1.1, 1])
    with c1:
        histogram(filtered_df, "score_std", "Distribución de score IA v2", key="overview_score_hist")
    with c2:
        scatter_chart(
            filtered_df,
            x="review_count_std",
            y="score_std",
            color="tier_std",
            title="Score vs reviews",
            hover_cols=["place_name_std", "dish_name_std", "district_name_std", "evidence_tier_std", "quality_tier_std"],
            key="overview_score_reviews_scatter",
        )

    st.markdown("### Top global filtrado")
    top_cols = [
        "selected_rank_std",
        "place_name_std",
        "dish_name_std",
        "district_name_std",
        "neighborhood_name_std",
        "score_std",
        "tier_std",
        "evidence_tier_std",
        "quality_tier_std",
        "mention_count_std",
        "review_count_std",
        "positive_ratio_std",
        "negative_ratio_std",
    ]
    st.dataframe(clean_dataframe_for_display(pick_columns(filtered_df.sort_values("score_std", ascending=False), top_cols).head(30)), use_container_width=True)


def render_ranking_explorer(data: Dict[str, Any], filtered_df: pd.DataFrame) -> None:
    st.subheader("Explorador de ranking")

    if filtered_df.empty:
        st.info("No hay candidatos con los filtros actuales.")
        return

    sort_options = {
        "Score descendente": ("score_std", False),
        "Rank seleccionado": ("selected_rank_std", True),
        "Más menciones": ("mention_count_std", False),
        "Más reviews": ("review_count_std", False),
        "Mayor ratio positivo": ("positive_ratio_std", False),
        "Menor ratio negativo": ("negative_ratio_std", True),
    }
    c1, c2, c3 = st.columns([1.1, 1, 1])
    with c1:
        sort_label = st.selectbox("Ordenar por", list(sort_options.keys()))
    with c2:
        page_size = st.selectbox("Filas por página", [20, 50, 100, 200], index=1)
    with c3:
        show_cards = st.toggle("Mostrar tarjetas", value=True)

    sort_col, ascending = sort_options[sort_label]
    df_sorted = filtered_df.sort_values(sort_col if sort_col in filtered_df.columns else "score_std", ascending=ascending)
    page_count = max(1, int(np.ceil(len(df_sorted) / page_size)))
    page = st.number_input("Página", min_value=1, max_value=page_count, value=1, step=1)
    page_df = df_sorted.iloc[(page - 1) * page_size : page * page_size].copy()

    display_cols = [
        "selected_rank_std",
        "place_name_std",
        "dish_name_std",
        "district_name_std",
        "neighborhood_name_std",
        "score_std",
        "tier_std",
        "evidence_tier_std",
        "quality_tier_std",
        "mention_count_std",
        "review_count_std",
        "positive_ratio_std",
        "neutral_ratio_std",
        "negative_ratio_std",
        "weighted_sentiment_std",
        "avg_absa_confidence_v2",
        "avg_normalization_confidence_v2",
    ]

    st.download_button(
        "Descargar candidatos filtrados CSV",
        data=df_to_csv_bytes(df_sorted),
        file_name="hidden_gems_sevilla_v2_filtrado.csv",
        mime="text/csv",
    )

    st.dataframe(clean_dataframe_for_display(pick_columns(page_df, display_cols)), use_container_width=True, height=520)

    if show_cards:
        st.markdown("### Detalle de candidatos")
        options = [
            f"#{safe_int(r.get('selected_rank_std', r.get('global_rank_std', 0)))} · {r.get('dish_name_std', '')} · {r.get('place_name_std', '')}"
            for _, r in page_df.iterrows()
        ]
        if options:
            selected_label = st.selectbox("Selecciona un candidato", options)
            idx = options.index(selected_label)
            render_candidate_card(page_df.iloc[idx], data.get("mentions", pd.DataFrame()))


def render_geography(data: Dict[str, Any], filtered_df: pd.DataFrame) -> None:
    st.subheader("Análisis territorial")

    if filtered_df.empty:
        st.info("No hay datos geográficos con los filtros actuales.")
        return

    district = (
        filtered_df.groupby("district_name_std", dropna=False)
        .agg(
            selected_count=("dashboard_candidate_key", "count"),
            selected_places=("place_id_std", "nunique"),
            selected_dishes=("dish_id_std", "nunique"),
            selected_neighborhoods=("neighborhood_name_std", "nunique"),
            total_mentions=("mention_count_std", "sum"),
            total_reviews=("review_count_std", "sum"),
            avg_score=("score_std", "mean"),
            max_score=("score_std", "max"),
            avg_positive_ratio=("positive_ratio_std", "mean"),
            avg_negative_ratio=("negative_ratio_std", "mean"),
        )
        .reset_index()
        .sort_values("selected_count", ascending=False)
    )

    neighborhood = (
        filtered_df.groupby(["district_name_std", "neighborhood_name_std"], dropna=False)
        .agg(
            selected_count=("dashboard_candidate_key", "count"),
            selected_places=("place_id_std", "nunique"),
            selected_dishes=("dish_id_std", "nunique"),
            total_mentions=("mention_count_std", "sum"),
            total_reviews=("review_count_std", "sum"),
            avg_score=("score_std", "mean"),
            max_score=("score_std", "max"),
        )
        .reset_index()
        .sort_values("selected_count", ascending=False)
    )

    st.markdown("### Mapa de locales candidatos")
    map_mode = st.radio(
        "Coordenadas del mapa",
        ["Usar coordenadas reales si existen", "Forzar fallback aproximado por distrito"],
        horizontal=True,
        key="geo_map_mode",
    )
    use_fallback = map_mode == "Forzar fallback aproximado por distrito"
    map_df = build_place_map_dataframe(filtered_df, use_fallback=use_fallback)

    real_coord_count = 0
    if "coordinate_source_std" in map_df.columns:
        real_coord_count = int((map_df["coordinate_source_std"].astype(str) != "approx_district_centroid").sum())
    coord_total = len(map_df)

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        render_kpi("Locales en mapa", fmt_int(coord_total), "marcadores únicos")
    with mc2:
        render_kpi("Con coordenada real", fmt_int(real_coord_count), "según export")
    with mc3:
        render_kpi("Distritos visibles", fmt_int(filtered_df["district_name_std"].nunique()), "con filtros")
    with mc4:
        render_kpi("Barrios visibles", fmt_int(filtered_df["neighborhood_name_std"].nunique()), "con filtros")

    if not map_df.empty:
        fig = px.scatter_mapbox(
            map_df,
            lat="latitude_std",
            lon="longitude_std",
            color="best_score",
            size="marker_size",
            hover_name="place_name_std" if "place_name_std" in map_df.columns else None,
            hover_data={
                "district_name_std": True,
                "neighborhood_name_std": True,
                "candidate_count": True,
                "dishes": True,
                "best_score": ":.2f",
                "total_mentions": True,
                "total_reviews": True,
                "top_tier": True,
                "best_evidence": True,
                "best_quality": True,
                "latitude_std": False,
                "longitude_std": False,
                "marker_size": False,
                "coordinate_source_std": True if "coordinate_source_std" in map_df.columns else False,
            },
            zoom=11,
            height=620,
            title="Mapa de locales con candidatos Hidden Gems IA v2",
            color_continuous_scale="Viridis",
        )
        fig.update_layout(
            mapbox_style="open-street-map",
            margin=dict(l=8, r=8, t=55, b=8),
            coloraxis_colorbar_title="Score máximo",
        )
        st.plotly_chart(fig, use_container_width=True, key="geo_real_map")
        if real_coord_count < coord_total:
            st.caption(
                "Algunos puntos usan centroides aproximados porque no tienen coordenada real en el export. "
                "Con el export parcheado deberían aparecer `latitude_std`, `longitude_std` y `place_coordinates.csv`."
            )
    else:
        st.warning("No se han encontrado coordenadas para pintar el mapa. Revisa que el export incluya latitude_std/longitude_std o place_coordinates.csv.")

    c1, c2 = st.columns([1.1, 1])
    with c1:
        bar_chart(
            district.head(15),
            x="district_name_std",
            y="selected_count",
            title="Candidatos seleccionados por distrito",
            color="avg_score",
            text="selected_count",
            key="geo_district_bar",
        )
    with c2:
        treemap_chart(
            neighborhood,
            path_cols=["district_name_std", "neighborhood_name_std"],
            values="selected_count",
            color="avg_score",
            title="Distribución por distrito y barrio",
            key="geo_treemap",
        )

    st.markdown("### Top barrios")
    top_neighborhoods = neighborhood.head(30)
    bar_chart(
        top_neighborhoods.sort_values("selected_count", ascending=True),
        x="neighborhood_name_std",
        y="selected_count",
        title="Top barrios por número de candidatos",
        orientation="h",
        color="district_name_std",
        text="selected_count",
        key="geo_neighborhood_bar",
        height=650,
    )

    st.markdown("### Resumen territorial")
    st.dataframe(clean_dataframe_for_display(district), use_container_width=True)

    st.markdown("### Top por distrito")
    top_by_district = (
        filtered_df.sort_values("score_std", ascending=False)
        .groupby("district_name_std")
        .head(10)
        .sort_values(["district_name_std", "score_std"], ascending=[True, False])
    )
    cols = ["district_name_std", "selected_rank_std", "place_name_std", "dish_name_std", "score_std", "tier_std", "evidence_tier_std", "quality_tier_std", "latitude_std", "longitude_std"]
    st.dataframe(clean_dataframe_for_display(pick_columns(top_by_district, cols)), use_container_width=True)



def render_dishes_places(data: Dict[str, Any], filtered_df: pd.DataFrame) -> None:
    st.subheader("Platos y locales")

    if filtered_df.empty:
        st.info("No hay datos con los filtros actuales.")
        return

    dish = (
        filtered_df.groupby("dish_name_std", dropna=False)
        .agg(
            selected_count=("dashboard_candidate_key", "count"),
            selected_places=("place_id_std", "nunique"),
            selected_neighborhoods=("neighborhood_name_std", "nunique"),
            total_mentions=("mention_count_std", "sum"),
            total_reviews=("review_count_std", "sum"),
            avg_score=("score_std", "mean"),
            max_score=("score_std", "max"),
            avg_positive_ratio=("positive_ratio_std", "mean"),
            avg_negative_ratio=("negative_ratio_std", "mean"),
        )
        .reset_index()
        .sort_values("selected_count", ascending=False)
    )

    place = (
        filtered_df.groupby(["place_name_std", "district_name_std", "neighborhood_name_std"], dropna=False)
        .agg(
            selected_count=("dashboard_candidate_key", "count"),
            selected_dishes=("dish_id_std", "nunique"),
            total_mentions=("mention_count_std", "sum"),
            total_reviews=("review_count_std", "sum"),
            avg_score=("score_std", "mean"),
            max_score=("score_std", "max"),
        )
        .reset_index()
        .sort_values(["selected_count", "max_score"], ascending=[False, False])
    )

    c1, c2 = st.columns(2)
    with c1:
        bar_chart(
            dish.head(20).sort_values("selected_count", ascending=True),
            x="dish_name_std",
            y="selected_count",
            title="Platos con más candidatos",
            orientation="h",
            color="avg_score",
            text="selected_count",
            key="dish_count_bar",
            height=580,
        )
    with c2:
        bar_chart(
            dish.sort_values("max_score", ascending=False).head(20).sort_values("max_score", ascending=True),
            x="dish_name_std",
            y="max_score",
            title="Platos con mayor score máximo",
            orientation="h",
            color="selected_count",
            text="max_score",
            key="dish_score_bar",
            height=580,
        )

    st.markdown("### Locales con más platos destacados")
    bar_chart(
        place.head(25).sort_values("selected_count", ascending=True),
        x="place_name_std",
        y="selected_count",
        title="Locales con mayor número de señales seleccionadas",
        orientation="h",
        color="avg_score",
        text="selected_count",
        key="place_count_bar",
        height=720,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Resumen por plato")
        st.dataframe(clean_dataframe_for_display(dish), use_container_width=True, height=520)
    with c2:
        st.markdown("#### Resumen por local")
        st.dataframe(clean_dataframe_for_display(place), use_container_width=True, height=520)


def render_evidence_quality(data: Dict[str, Any], filtered_df: pd.DataFrame) -> None:
    st.subheader("Evidencia, calidad y confianza")

    if filtered_df.empty:
        st.info("No hay datos con los filtros actuales.")
        return

    c1, c2 = st.columns(2)
    with c1:
        scatter_chart(
            filtered_df,
            x="avg_absa_confidence_v2" if "avg_absa_confidence_v2" in filtered_df.columns else "score_std",
            y="score_std",
            color="quality_tier_std",
            title="Score vs confianza ABSA media",
            hover_cols=["place_name_std", "dish_name_std", "evidence_tier_std", "quality_tier_std"],
            key="evidence_absa_scatter",
        )
    with c2:
        scatter_chart(
            filtered_df,
            x="avg_normalization_confidence_v2" if "avg_normalization_confidence_v2" in filtered_df.columns else "score_std",
            y="score_std",
            color="evidence_tier_std",
            title="Score vs confianza de normalización",
            hover_cols=["place_name_std", "dish_name_std", "evidence_tier_std", "quality_tier_std"],
            key="evidence_norm_scatter",
        )

    c1, c2, c3 = st.columns(3)
    with c1:
        if "avg_absa_confidence_v2" in filtered_df.columns:
            histogram(filtered_df, "avg_absa_confidence_v2", "Confianza ABSA", key="evidence_absa_hist")
    with c2:
        if "avg_normalization_confidence_v2" in filtered_df.columns:
            histogram(filtered_df, "avg_normalization_confidence_v2", "Confianza normalización", key="evidence_norm_hist")
    with c3:
        if "needs_review_ratio_v2" in filtered_df.columns:
            histogram(filtered_df, "needs_review_ratio_v2", "Ratio de señales revisables", key="evidence_review_hist")

    st.markdown("### Matriz evidencia × calidad")
    if has_cols(filtered_df, ["evidence_tier_std", "quality_tier_std", "dashboard_candidate_key"]):
        matrix = filtered_df.pivot_table(
            index="evidence_tier_std",
            columns="quality_tier_std",
            values="dashboard_candidate_key",
            aggfunc="count",
            fill_value=0,
        )
        fig = px.imshow(matrix, text_auto=True, title="Número de candidatos por evidencia y calidad", height=420)
        fig.update_layout(margin=dict(l=8, r=8, t=55, b=8))
        st.plotly_chart(fig, use_container_width=True, key="evidence_quality_heatmap")
        st.dataframe(matrix, use_container_width=True)

    st.markdown("### Componentes del ranking")
    component_cols = [
        "ranking_sentiment_component_v2",
        "ranking_evidence_component_v2",
        "ranking_quality_component_v2",
        "ranking_consensus_component_v2",
        "ranking_uniqueness_component_v2",
        "ranking_rating_component_v2",
        "negative_sentiment_penalty_v2",
        "quality_risk_penalty_v2",
        "low_evidence_penalty_v2",
    ]
    available = [c for c in component_cols if c in filtered_df.columns]
    if available:
        comp_df = filtered_df[available].mean().reset_index()
        comp_df.columns = ["component", "avg_value"]
        bar_chart(
            comp_df.sort_values("avg_value", ascending=True),
            x="component",
            y="avg_value",
            title="Media de componentes del score en el conjunto filtrado",
            orientation="h",
            text="avg_value",
            key="ranking_components_bar",
            height=500,
        )


def render_comparison(data: Dict[str, Any]) -> None:
    st.subheader("Comparación ranking v1 vs IA v2")

    summary = data.get("comparison_summary", {}) or {}
    quality = summary.get("quality", {}) if isinstance(summary, dict) else {}
    counts = summary.get("counts", {}) if isinstance(summary, dict) else {}
    diversity = summary.get("diversity_delta", {}) if isinstance(summary, dict) else {}

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("V1 seleccionados", fmt_int(counts.get("v1_selected_unique", 0)), "baseline")
    with c2:
        render_kpi("V2 seleccionados", fmt_int(counts.get("v2_selected_unique", 0)), "IA v2")
    with c3:
        render_kpi("Coincidencias", fmt_int(counts.get("matched_candidates", 0)), "mismo local + plato")
    with c4:
        render_kpi("Cobertura v1→v2", fmt_pct(quality.get("v1_coverage_in_v2", 0)), "v1 recuperado en v2")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        places_delta = diversity.get("selected_places", {}).get("delta_v2_minus_v1", 0) if isinstance(diversity, dict) else 0
        render_kpi("Delta locales", f"+{fmt_int(places_delta)}", "v2 - v1")
    with c2:
        neigh_delta = diversity.get("selected_neighborhoods", {}).get("delta_v2_minus_v1", 0) if isinstance(diversity, dict) else 0
        render_kpi("Delta barrios", f"+{fmt_int(neigh_delta)}", "v2 - v1")
    with c3:
        dishes_delta = diversity.get("selected_dishes", {}).get("delta_v2_minus_v1", 0) if isinstance(diversity, dict) else 0
        render_kpi("Delta platos", f"+{fmt_int(dishes_delta)}", "v2 - v1")
    with c4:
        render_kpi("Jaccard", fmt_pct(quality.get("jaccard_overlap", 0)), "solapamiento global")

    tier_shift = data.get("tier_shift", pd.DataFrame())
    score_shift = data.get("score_shift", pd.DataFrame())
    v2_only = data.get("v2_only", pd.DataFrame())
    v1_only = data.get("v1_only", pd.DataFrame())
    overlap = data.get("ranking_overlap", pd.DataFrame())

    c1, c2 = st.columns(2)
    with c1:
        if not tier_shift.empty:
            st.markdown("### Cambios por tier")
            st.dataframe(clean_dataframe_for_display(tier_shift), use_container_width=True, height=360)
        else:
            st.info("No se encontró tier_shift_summary.csv.")
    with c2:
        if not score_shift.empty and "score_delta_v2_minus_v1" in score_shift.columns:
            histogram(score_shift, "score_delta_v2_minus_v1", "Distribución de delta score v2 - v1", key="comparison_score_delta_hist")

    st.markdown("### Candidatos nuevos en v2")
    if not v2_only.empty:
        cols = [
            "v2_rank",
            "v2_place_name",
            "v2_dish_name",
            "v2_district_name",
            "v2_neighborhood_name",
            "v2_score",
            "v2_tier",
            "v2_mention_count",
            "v2_review_count",
            "v2_evidence_tier",
            "v2_quality_tier",
            "v2_explanation",
        ]
        st.dataframe(clean_dataframe_for_display(pick_columns(v2_only, cols).head(80)), use_container_width=True, height=520)
    else:
        st.info("No se encontró v2_only_candidates.csv.")

    st.markdown("### Candidatos que estaban en v1 y no en v2")
    if not v1_only.empty:
        cols = [
            "v1_rank",
            "v1_place_name",
            "v1_dish_name",
            "v1_district_name",
            "v1_neighborhood_name",
            "v1_score",
            "v1_tier",
            "v1_mention_count",
            "v1_review_count",
            "v1_evidence_tier",
        ]
        st.dataframe(clean_dataframe_for_display(pick_columns(v1_only, cols).head(80)), use_container_width=True, height=420)

    st.markdown("### Coincidencias v1/v2")
    if not overlap.empty:
        cols = [
            "v1_rank",
            "v2_rank",
            "rank_delta_v2_minus_v1",
            "v1_place_name",
            "v1_dish_name",
            "v1_score",
            "v2_score",
            "score_delta_v2_minus_v1",
            "v1_tier",
            "v2_tier",
            "tier_changed",
        ]
        st.dataframe(clean_dataframe_for_display(pick_columns(overlap, cols).head(120)), use_container_width=True, height=520)


def render_mentions(data: Dict[str, Any], filtered_df: pd.DataFrame) -> None:
    st.subheader("Detalle de menciones y reseñas")

    mentions = data.get("mentions", pd.DataFrame())
    if mentions.empty:
        st.info("No se encontró mention_examples.csv o no contiene filas.")
        return

    allowed_keys = set(filtered_df["dashboard_candidate_key"].astype(str).tolist()) if "dashboard_candidate_key" in filtered_df.columns else set()
    ex = mentions.copy()
    if allowed_keys and "dashboard_candidate_key" in ex.columns:
        ex = ex[ex["dashboard_candidate_key"].astype(str).isin(allowed_keys)]

    st.markdown("### Selección por local y plato")
    local_options = ["Todos"] + non_empty_values(ex.get("place_name_std", pd.Series(dtype=str)))
    selected_local = st.selectbox("Seleccionar local", local_options, index=0, key="mentions_place_selector")
    if selected_local != "Todos" and "place_name_std" in ex.columns:
        ex = ex[ex["place_name_std"].astype(str) == selected_local]

    dish_options = ["Todos"] + non_empty_values(ex.get("dish_name_std", pd.Series(dtype=str)))
    selected_dish = st.selectbox("Seleccionar plato dentro del local", dish_options, index=0, key="mentions_dish_selector")
    if selected_dish != "Todos" and "dish_name_std" in ex.columns:
        ex = ex[ex["dish_name_std"].astype(str) == selected_dish]

    # Mostrar ficha del candidato seleccionado si existe en el ranking filtrado.
    if selected_local != "Todos":
        candidate_scope = filtered_df.copy()
        if "place_name_std" in candidate_scope.columns:
            candidate_scope = candidate_scope[candidate_scope["place_name_std"].astype(str) == selected_local]
        if selected_dish != "Todos" and "dish_name_std" in candidate_scope.columns:
            candidate_scope = candidate_scope[candidate_scope["dish_name_std"].astype(str) == selected_dish]
        if not candidate_scope.empty:
            best = candidate_scope.sort_values("score_std", ascending=False).iloc[0]
            st.markdown(
                f"""
                <div class="hg-card">
                    <h3>{best.get('place_name_std', '')} · {best.get('dish_name_std', '')}</h3>
                    <p>
                        <b>Score v2:</b> {fmt_float(best.get('score_std', 0), 2)} ·
                        <b>Tier:</b> {tier_label(best.get('tier_std', ''))} ·
                        <b>Evidencia:</b> {evidence_label(best.get('evidence_tier_std', ''))} ·
                        <b>Calidad:</b> {quality_label(best.get('quality_tier_std', ''))}
                    </p>
                    <p>
                        <b>Menciones:</b> {fmt_int(best.get('mention_count_std', 0))} ·
                        <b>Reviews:</b> {fmt_int(best.get('review_count_std', 0))} ·
                        <b>Positivas:</b> {fmt_pct(best.get('positive_ratio_std', 0))} ·
                        <b>Negativas:</b> {fmt_pct(best.get('negative_ratio_std', 0))}
                    </p>
                    <p class="hg-muted">{best.get('explanation_std', '')}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sentiments = ordered_values(non_empty_values(ex.get("sentiment_label_std", pd.Series(dtype=str))), SENTIMENT_ORDER)
        selected_sentiments = st.multiselect("Sentimiento", sentiments, default=sentiments, key="mentions_sentiment_filter")
    with c2:
        min_conf = st.slider("Confianza mínima sentimiento", 0.0, 1.0, 0.0, 0.05, key="mentions_conf_filter")
    with c3:
        if "rating_value_std" in ex.columns and pd.to_numeric(ex["rating_value_std"], errors="coerce").notna().any():
            min_rating = st.slider("Rating mínimo", 0.0, 5.0, 0.0, 0.5, key="mentions_rating_filter")
        else:
            min_rating = 0.0
            st.caption("Sin rating disponible")
    with c4:
        show_full = st.toggle("Mostrar review completa", value=True, key="mentions_show_full")

    if selected_sentiments and "sentiment_label_std" in ex.columns:
        ex = ex[ex["sentiment_label_std"].astype(str).isin(selected_sentiments)]
    if "sentiment_confidence_std" in ex.columns:
        ex = ex[pd.to_numeric(ex["sentiment_confidence_std"], errors="coerce").fillna(0) >= min_conf]
    if "rating_value_std" in ex.columns:
        ex = ex[pd.to_numeric(ex["rating_value_std"], errors="coerce").fillna(0) >= min_rating]

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_kpi("Filas visibles", fmt_int(len(ex)), "menciones/reseñas")
    with k2:
        review_col = first_col(ex, ["review_id_std", "review_id"])
        render_kpi("Reviews únicas", fmt_int(ex[review_col].nunique() if review_col else len(ex)), "tras filtros")
    with k3:
        render_kpi("Platos", fmt_int(ex["dish_name_std"].nunique() if "dish_name_std" in ex.columns else 0), "en la selección")
    with k4:
        conf = pd.to_numeric(ex.get("sentiment_confidence_std", pd.Series(dtype=float)), errors="coerce")
        render_kpi("Confianza media", fmt_pct(conf.mean() if not conf.empty else 0), "ABSA")
    with k5:
        rating = pd.to_numeric(ex.get("rating_value_std", pd.Series(dtype=float)), errors="coerce")
        render_kpi("Rating medio", fmt_float(rating.mean() if not rating.empty else 0, 2), "reseñas")

    sentiment_counts = ex["sentiment_label_std"].value_counts().reset_index() if "sentiment_label_std" in ex.columns else pd.DataFrame()
    if not sentiment_counts.empty:
        sentiment_counts.columns = ["sentiment", "count"]
        pie_chart(sentiment_counts, "sentiment", "count", "Distribución de sentimiento en reseñas filtradas", key="mentions_sentiment_pie")

    st.markdown("### Tabla de reseñas/menciones")
    cols = [
        "selected_rank_std",
        "place_name_std",
        "dish_name_std",
        "score_std",
        "tier_std",
        "evidence_tier_std",
        "quality_tier_std",
        "mention_text_std",
        "sentiment_label_std",
        "sentiment_confidence_std",
        "rating_value_std",
        "context_std",
        "review_text_std",
    ]
    if not show_full:
        cols = [c for c in cols if c != "review_text_std"]
    st.dataframe(clean_dataframe_for_display(pick_columns(ex, cols)), use_container_width=True, height=540)

    st.download_button(
        "Descargar reseñas filtradas CSV",
        data=df_to_csv_bytes(pick_columns(ex, cols)),
        file_name="sevilla_v2_reseñas_filtradas.csv",
        mime="text/csv",
        key="mentions_download_csv",
    )

    st.markdown("### Vista tipo ficha")
    max_cards = st.slider("Número de fichas a mostrar", 5, 50, 15, 5, key="mentions_cards_count")
    for _, row in ex.head(max_cards).iterrows():
        review = row.get("review_text_std", "") if show_full else ""
        st.markdown(
            f"""
            <div class="hg-card">
                <h3>{row.get('dish_name_std', '')} · {row.get('place_name_std', '')}</h3>
                <p>
                    <b>Score candidato:</b> {fmt_float(row.get('score_std', 0), 2)} ·
                    <b>Tier:</b> {tier_label(row.get('tier_std', ''))} ·
                    <b>Evidencia:</b> {evidence_label(row.get('evidence_tier_std', ''))} ·
                    <b>Calidad:</b> {quality_label(row.get('quality_tier_std', ''))}
                </p>
                <p>
                    <b>Mención:</b> {row.get('mention_text_std', '')} ·
                    <b>Sentimiento:</b> {row.get('sentiment_label_std', '')} ({fmt_pct(row.get('sentiment_confidence_std', 0))}) ·
                    <b>Rating:</b> {row.get('rating_value_std', '')}
                </p>
                <p><b>Contexto:</b> {row.get('context_std', '')}</p>
                {f'<p class="hg-muted"><b>Review completa:</b> {review}</p>' if str(review).strip() else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )



def render_score_explanation(data: Dict[str, Any], filtered_df: pd.DataFrame) -> None:
    st.subheader("Cómo se calcula la puntuación Hidden Gem IA v2")

    st.markdown(
        """
        El `hidden_gem_score_v2` es una puntuación normalizada de **0 a 100** para ordenar candidatos
        de tipo **local + plato**. No representa una verdad absoluta ni una nota gastronómica oficial:
        es una señal experimental construida a partir de evidencias textuales, modelos entrenados y
        reglas de calidad.
        """
    )

    st.markdown("### Fórmula conceptual")
    st.code(
        """
hidden_gem_score_v2 =
    sentimiento_ABSA_ponderado
  + evidencia_de_menciones_y_reviews
  + calidad_de_normalización_y_confianza
  + consenso_híbrido/NER
  + especificidad/rareza_del_plato
  + rating_como_señal_secundaria
  - penalización_por_negativos
  - penalización_por_baja_evidencia
  - penalización_por_revisión_manual
        """.strip(),
        language="text",
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(
            """
            **Componentes positivos**

            - **Sentimiento ABSA**: sentimiento hacia la mención concreta del plato, no hacia la reseña completa.
            - **Evidencia**: número de menciones y reviews diferentes que respaldan el candidato.
            - **Calidad**: confianza de la normalización, confianza del sentimiento y limpieza de la señal.
            - **Consenso**: mayor peso cuando la mención aparece respaldada por el sistema híbrido y por el NER.
            - **Especificidad**: se favorecen platos más informativos o menos genéricos cuando la evidencia acompaña.
            """
        )
    with c2:
        st.markdown(
            """
            **Penalizaciones**

            - **Ratio negativo**: presencia de menciones negativas hacia el plato.
            - **Baja evidencia**: pocos reviews o menciones.
            - **Baja confianza**: normalización o sentimiento dudosos.
            - **Revisión manual**: señales marcadas como experimentales, fragmentos o casos de calidad baja.
            """
        )

    st.info(
        "Los scores v2 son comparables entre candidatos dentro del ranking v2, pero no son equivalentes directamente a los scores v1, porque la fórmula cambió."
    )

    st.markdown("### Relación entre score, evidencia y calidad")
    if filtered_df.empty:
        st.info("No hay candidatos con los filtros actuales.")
        return

    chart_cols = [
        "score_std", "mention_count_std", "review_count_std", "positive_ratio_std", "negative_ratio_std",
        "tier_std", "evidence_tier_std", "quality_tier_std", "place_name_std", "dish_name_std",
    ]
    df = pick_columns(filtered_df, chart_cols).copy()
    for col in ["score_std", "mention_count_std", "review_count_std", "positive_ratio_std", "negative_ratio_std"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    c3, c4 = st.columns(2)
    with c3:
        scatter_chart(
            df,
            x="review_count_std",
            y="score_std",
            title="Score vs número de reviews",
            color="quality_tier_std",
            hover_cols=["place_name_std", "dish_name_std", "tier_std", "evidence_tier_std"],
            key="score_explain_reviews_scatter",
        )
    with c4:
        scatter_chart(
            df,
            x="positive_ratio_std",
            y="score_std",
            title="Score vs ratio positivo ABSA",
            color="evidence_tier_std",
            hover_cols=["place_name_std", "dish_name_std", "tier_std", "quality_tier_std"],
            key="score_explain_positive_scatter",
        )

    st.markdown("### Tabla de componentes visibles")
    component_cols = [
        "selected_rank_std", "place_name_std", "dish_name_std", "score_std", "tier_std",
        "mention_count_std", "review_count_std", "positive_ratio_std", "negative_ratio_std",
        "evidence_tier_std", "quality_tier_std", "explanation_std",
    ]
    st.dataframe(
        clean_dataframe_for_display(pick_columns(filtered_df.sort_values("score_std", ascending=False), component_cols)),
        use_container_width=True,
        height=560,
    )


def render_data_contract(data: Dict[str, Any]) -> None:
    st.subheader("Contrato de datos y artefactos")

    contract = data.get("contract", {})
    metadata = data.get("metadata", {})
    summary = data.get("summary", {})

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Contrato")
        st.json(contract, expanded=False)
    with c2:
        st.markdown("### Metadatos")
        st.json(metadata, expanded=False)

    st.markdown("### Summary del export")
    st.json(summary, expanded=False)

    st.markdown("### Archivos cargados")
    files = summary.get("files", []) if isinstance(summary, dict) else []
    if files:
        st.dataframe(pd.DataFrame({"file": files}), use_container_width=True)

    st.markdown("### Previews raw")
    previews = {
        "selected_candidates": data.get("selected", pd.DataFrame()),
        "ranking_detail": data.get("ranking", pd.DataFrame()),
        "mention_examples": data.get("mentions", pd.DataFrame()),
    }
    for name, df in previews.items():
        with st.expander(name, expanded=False):
            st.dataframe(clean_dataframe_for_display(df.head(50)), use_container_width=True)


# ============================================================
# Main
# ============================================================

def main() -> None:
    # Carga inicial para construir sidebar con datos por defecto.
    initial_data_dir = DEFAULT_DATA_DIR
    initial_data = load_dashboard_data(str(initial_data_dir))
    initial_base = initial_data.get("selected", pd.DataFrame())
    if initial_base.empty:
        initial_base = initial_data.get("ranking", pd.DataFrame())

    filters, selected_only, data_dir = build_sidebar_filters(initial_base, initial_data.get("summary", {}))

    data = load_dashboard_data(str(data_dir))

    if not Path(data_dir).exists():
        st.error(f"No existe la carpeta de datos: {data_dir}")
        st.stop()

    selected_df = data.get("selected", pd.DataFrame())
    ranking_df = data.get("ranking", pd.DataFrame())

    base_df = selected_df if selected_only and not selected_df.empty else ranking_df
    if base_df.empty:
        st.error("No se han encontrado datos de ranking. Revisa la carpeta dashboard_v2.")
        st.stop()

    # Asegurar columnas críticas.
    for col in ["score_std", "mention_count_std", "review_count_std", "positive_ratio_std", "negative_ratio_std"]:
        if col in base_df.columns:
            base_df[col] = pd.to_numeric(base_df[col], errors="coerce")

    filtered_df = apply_filters(base_df, filters)

    render_header(data.get("summary", {}))

    st.caption(
        "El ranking IA v2 es experimental: combina modelos entrenados, evidencia textual, calidad de normalización y sentimiento por mención. "
        "Los scores son comparables dentro de v2, pero no equivalen directamente a los scores del baseline v1."
    )

    tabs = st.tabs([
        "📌 Resumen",
        "🏆 Ranking",
        "🗺️ Territorio",
        "🍽️ Platos y locales",
        "🧪 Evidencia y calidad",
        "🔁 Comparativa v1/v2",
        "💬 Reseñas",
        "🧮 Puntuación",
        "📄 Datos",
    ])

    with tabs[0]:
        render_overview(data, filtered_df)
    with tabs[1]:
        render_ranking_explorer(data, filtered_df)
    with tabs[2]:
        render_geography(data, filtered_df)
    with tabs[3]:
        render_dishes_places(data, filtered_df)
    with tabs[4]:
        render_evidence_quality(data, filtered_df)
    with tabs[5]:
        render_comparison(data)
    with tabs[6]:
        render_mentions(data, filtered_df)
    with tabs[7]:
        render_score_explanation(data, filtered_df)
    with tabs[8]:
        render_data_contract(data)


if __name__ == "__main__":
    main()
