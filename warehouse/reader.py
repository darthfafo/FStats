"""
Lectura del warehouse desde Streamlit.

Solo hace SELECT sobre las vistas deduplicadas (definidas en db.py), así la
app siempre ve el último valor por fecha sin preocuparse por el append-only.
Los resultados se cachean 1h para no golpear MotherDuck en cada rerun.

Todas las funciones devuelven DataFrames de pandas y reciben el nombre
legible del portal (config.PORTALES["nombre"]); internamente lo traducen al
portal_id estable del warehouse.
"""
import pandas as pd

from warehouse.db import get_connection, portal_id

# Caché de Streamlit si está disponible; si no (CI / script), no-op.
try:
    import streamlit as st
    _cache = st.cache_data(ttl=3600, show_spinner=False)
except Exception:  # pragma: no cover - fuera de Streamlit
    def _cache(fn):
        return fn


def _query(sql, params=None):
    con = get_connection(read_only=True)
    try:
        return con.execute(sql, params or []).fetchdf()
    finally:
        con.close()


@_cache
def daily_metric(nombre, plataforma, metric_name):
    """
    Serie diaria de una métrica de insights para un portal.

    plataforma: 'fb' o 'ig'.
    metric_name: nombre crudo guardado (p.ej. 'page_impressions_unique',
                 'reach', 'follower_count', ...).
    Devuelve columnas: metric_date (date), metric_value (int).
    """
    view = "fb_page_insights" if plataforma == "fb" else "ig_account_insights"
    return _query(
        f"""SELECT metric_date, metric_value
            FROM {view}
            WHERE portal_id = ? AND metric_name = ?
            ORDER BY metric_date""",
        [portal_id(nombre), metric_name],
    )


@_cache
def followers_history(nombre, plataforma):
    """
    Histórico de seguidores (un punto por día) para graficar tendencia.

    Devuelve columnas: snapshot_date (date), followers_count (int).
    """
    view = "fb_page_info_daily" if plataforma == "fb" else "ig_account_info_daily"
    return _query(
        f"""SELECT snapshot_date, followers_count
            FROM {view}
            WHERE portal_id = ?
            ORDER BY snapshot_date""",
        [portal_id(nombre)],
    )


@_cache
def reach_by_follow_type(nombre):
    """
    Histórico de alcance diario por tipo de seguidor (Instagram).

    Devuelve columnas: metric_date (date), follow_type (text), reach_value (int).
    follow_type ∈ {'follower', 'non_follower', 'unknown'}.
    """
    return _query(
        """SELECT metric_date, follow_type, reach_value
           FROM ig_reach_by_follow_type
           WHERE portal_id = ?
           ORDER BY metric_date""",
        [portal_id(nombre)],
    )


@_cache
def demographics(nombre, audience_type, breakdown):
    """
    Última foto de demografía de un portal (Instagram).

    audience_type: 'follower' (seguidores) | 'engaged' (audiencia que interactúa).
    breakdown: 'age' | 'city' | 'country' | 'gender'.
    Devuelve columnas: dimension (text), value (int), ordenadas por value desc.
    """
    pid = portal_id(nombre)
    return _query(
        """SELECT dimension, value
           FROM ig_demographics
           WHERE portal_id = ? AND audience_type = ? AND breakdown = ?
             AND snapshot_date = (
                 SELECT max(snapshot_date) FROM ig_demographics
                 WHERE portal_id = ? AND audience_type = ? AND breakdown = ?
             )
           ORDER BY value DESC""",
        [pid, audience_type, breakdown, pid, audience_type, breakdown],
    )


@_cache
def posts(nombre, plataforma):
    """Posts deduplicados de un portal (último estado conocido de cada uno)."""
    view = "fb_posts" if plataforma == "fb" else "ig_posts"
    return _query(
        f"SELECT * FROM {view} WHERE portal_id = ?",
        [portal_id(nombre)],
    )


@_cache
def available_dates(nombre, plataforma):
    """Rango de fechas con datos de insights cargados (para notas/leyendas)."""
    view = "fb_page_insights" if plataforma == "fb" else "ig_account_insights"
    df = _query(
        f"""SELECT min(metric_date) AS desde, max(metric_date) AS hasta
            FROM {view} WHERE portal_id = ?""",
        [portal_id(nombre)],
    )
    if df.empty or pd.isna(df.iloc[0]["desde"]):
        return None, None
    return df.iloc[0]["desde"], df.iloc[0]["hasta"]
