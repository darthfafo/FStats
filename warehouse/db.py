import duckdb
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "fstats.duckdb")

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
"""


def get_connection(read_only=False):
    con = duckdb.connect(DB_PATH, read_only=read_only)
    if not read_only:
        initialize(con)
    return con


def initialize(con):
    for statement in _SCHEMA_SQL.split(";"):
        stmt = statement.strip()
        if stmt:
            try:
                con.execute(stmt)
            except Exception as e:
                print(f"[DB] Schema init warning: {e}")
    con.commit()
