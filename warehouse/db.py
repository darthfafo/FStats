"""
Conexión al warehouse de FStats.

Por defecto se conecta a MotherDuck (DuckDB en la nube), que es donde viven
los datos en producción. El token se lee del entorno o de los secrets de
Streamlit — nunca se hardcodea ni se mete en la cadena de conexión.

Para desarrollo local sin nube, exportá FSTATS_DB_LOCAL=1 y usa un archivo
DuckDB local (warehouse/fstats_local.duckdb, ignorado por git).

Esquema: 6 tablas "raw" append-only + vistas deduplicadas para lectura.
"""
import os
import duckdb

# Nombre de la base en MotherDuck (md:fstats) o archivo local.
DB_NAME = os.getenv("FSTATS_DB_NAME", "fstats")
_LOCAL_PATH = os.path.join(os.path.dirname(__file__), "fstats_local.duckdb")


# Nombre de portal (config.PORTALES["nombre"]) -> id estable en el warehouse.
PORTAL_ID_MAP = {
    "Chubut Noticias": "chubut_noticias",
    "Atento Chubut":   "atento_chubut",
    "La Calle Online": "la_calle_online",
    "El Americano":    "el_americano",
    "VISTE ESTO?":     "viste_esto",
    "Boca en Linea":   "boca_en_linea",
}


def portal_id(nombre):
    """Id estable de portal a partir del nombre legible de config.PORTALES."""
    return PORTAL_ID_MAP.get(nombre, nombre.lower().replace(" ", "_"))


# ---------------------------------------------------------------------------
# Esquema
# ---------------------------------------------------------------------------
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_fb_page_insights (
    portal_id     TEXT,
    page_id       TEXT,
    metric_name   TEXT,
    metric_date   DATE,
    metric_value  BIGINT,
    ingested_at   TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_fb_posts (
    portal_id       TEXT,
    post_id         TEXT,
    created_date    DATE,
    message         TEXT,
    reactions_count INTEGER DEFAULT 0,
    comments_count  INTEGER DEFAULT 0,
    shares_count    INTEGER DEFAULT 0,
    ingested_at     TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_fb_page_info (
    portal_id       TEXT,
    page_id         TEXT,
    followers_count INTEGER,
    fan_count       INTEGER,
    ingested_at     TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_ig_account_insights (
    portal_id    TEXT,
    ig_id        TEXT,
    metric_name  TEXT,
    metric_date  DATE,
    metric_value BIGINT,
    ingested_at  TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_ig_posts (
    portal_id      TEXT,
    post_id        TEXT,
    caption        TEXT,
    media_type     TEXT,
    product_type   TEXT,
    published_date DATE,
    like_count     INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    permalink      TEXT,
    content_type   TEXT,
    is_reel        BOOLEAN,
    plays          INTEGER DEFAULT 0,
    reach          INTEGER DEFAULT 0,
    ingested_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_ig_account_info (
    portal_id       TEXT,
    ig_id           TEXT,
    followers_count INTEGER,
    follows_count   INTEGER,
    media_count     INTEGER,
    ingested_at     TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_fb_fan_growth (
    portal_id    TEXT,
    metric_date  DATE,
    new_follows  INTEGER DEFAULT 0,
    ingested_at  TIMESTAMP DEFAULT now()
);
"""

# Migraciones idempotentes para bases ya creadas (CREATE TABLE IF NOT EXISTS no
# agrega columnas nuevas a una tabla existente).
_MIGRATIONS_SQL = """
ALTER TABLE raw_ig_posts ADD COLUMN IF NOT EXISTS plays INTEGER DEFAULT 0;
ALTER TABLE raw_ig_posts ADD COLUMN IF NOT EXISTS reach INTEGER DEFAULT 0;
"""

# ---------------------------------------------------------------------------
# Vistas deduplicadas (resuelven el append-only en la LECTURA)
#
# Las tablas raw acumulan una fila por corrida. Estas vistas se quedan, para
# cada clave natural, con la última versión ingestada (mayor ingested_at).
# Así la ingesta sigue siendo un INSERT simple y la lectura siempre devuelve
# el valor más fresco, sin duplicados.
# ---------------------------------------------------------------------------
_VIEWS_SQL = """
CREATE OR REPLACE VIEW fb_page_insights AS
SELECT portal_id, page_id, metric_name, metric_date, metric_value
FROM (
    SELECT *, row_number() OVER (
        PARTITION BY portal_id, metric_name, metric_date
        ORDER BY ingested_at DESC
    ) AS rn
    FROM raw_fb_page_insights
) WHERE rn = 1;

CREATE OR REPLACE VIEW ig_account_insights AS
SELECT portal_id, ig_id, metric_name, metric_date, metric_value
FROM (
    SELECT *, row_number() OVER (
        PARTITION BY portal_id, metric_name, metric_date
        ORDER BY ingested_at DESC
    ) AS rn
    FROM raw_ig_account_insights
) WHERE rn = 1;

CREATE OR REPLACE VIEW fb_posts AS
SELECT portal_id, post_id, created_date, message,
       reactions_count, comments_count, shares_count
FROM (
    SELECT *, row_number() OVER (
        PARTITION BY portal_id, post_id
        ORDER BY ingested_at DESC
    ) AS rn
    FROM raw_fb_posts
) WHERE rn = 1;

CREATE OR REPLACE VIEW ig_posts AS
SELECT portal_id, post_id, caption, media_type, product_type,
       published_date, like_count, comments_count, permalink,
       content_type, is_reel, plays, reach
FROM (
    SELECT *, row_number() OVER (
        PARTITION BY portal_id, post_id
        ORDER BY ingested_at DESC
    ) AS rn
    FROM raw_ig_posts
) WHERE rn = 1;

CREATE OR REPLACE VIEW fb_fan_growth AS
SELECT portal_id, metric_date, new_follows
FROM (
    SELECT *, row_number() OVER (
        PARTITION BY portal_id, metric_date
        ORDER BY ingested_at DESC
    ) AS rn
    FROM raw_fb_fan_growth
) WHERE rn = 1;

-- Snapshot diario de seguidores: una fila por portal y día (el último del día).
CREATE OR REPLACE VIEW fb_page_info_daily AS
SELECT portal_id, page_id, followers_count, fan_count, snapshot_date
FROM (
    SELECT *, CAST(ingested_at AS DATE) AS snapshot_date,
           row_number() OVER (
               PARTITION BY portal_id, CAST(ingested_at AS DATE)
               ORDER BY ingested_at DESC
           ) AS rn
    FROM raw_fb_page_info
) WHERE rn = 1;

CREATE OR REPLACE VIEW ig_account_info_daily AS
SELECT portal_id, ig_id, followers_count, follows_count, media_count, snapshot_date
FROM (
    SELECT *, CAST(ingested_at AS DATE) AS snapshot_date,
           row_number() OVER (
               PARTITION BY portal_id, CAST(ingested_at AS DATE)
               ORDER BY ingested_at DESC
           ) AS rn
    FROM raw_ig_account_info
) WHERE rn = 1;
"""


# ---------------------------------------------------------------------------
# Conexión
# ---------------------------------------------------------------------------
def _use_local():
    return os.getenv("FSTATS_DB_LOCAL", "").strip() in ("1", "true", "True")


def _motherduck_token():
    """Token de MotherDuck: primero entorno (CI / local), luego secrets de Streamlit."""
    token = os.getenv("MOTHERDUCK_TOKEN") or os.getenv("motherduck_token")
    if token:
        return token
    try:
        import streamlit as st
        return st.secrets["MOTHERDUCK_TOKEN"]
    except Exception:
        return None


def _connect():
    if _use_local():
        return duckdb.connect(_LOCAL_PATH)

    token = _motherduck_token()
    if not token:
        raise RuntimeError(
            "Falta MOTHERDUCK_TOKEN. Cargalo como variable de entorno "
            "(GitHub Actions / local) o en los secrets de Streamlit. "
            "Para probar contra un archivo local exportá FSTATS_DB_LOCAL=1."
        )
    # El token viaja por entorno, no en la cadena de conexión (evita que se
    # filtre en logs). DuckDB lo lee automáticamente al conectar a 'md:'.
    os.environ["motherduck_token"] = token
    # Conectamos a la cuenta y nos aseguramos de que la base exista (la primera
    # corrida la crea). 'md:fstats' directo falla si la base aún no está.
    con = duckdb.connect("md:")
    con.execute(f'CREATE DATABASE IF NOT EXISTS "{DB_NAME}"')
    con.execute(f'USE "{DB_NAME}"')
    return con


def get_connection(read_only=False):
    """
    Devuelve una conexión al warehouse.

    read_only=False (default): para ingesta. Inicializa esquema + vistas.
    read_only=True: para lectura desde Streamlit. No toca el esquema.
    """
    con = _connect()
    if not read_only:
        initialize(con)
    return con


def initialize(con):
    """Crea las tablas raw, aplica migraciones y refresca las vistas de lectura."""
    for block in (_SCHEMA_SQL, _MIGRATIONS_SQL, _VIEWS_SQL):
        for statement in block.split(";"):
            stmt = statement.strip()
            if stmt:
                try:
                    con.execute(stmt)
                except Exception as e:
                    print(f"[DB] Schema/view init warning: {e}")
    con.commit()
