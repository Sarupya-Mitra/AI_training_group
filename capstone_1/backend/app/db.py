from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from app import config


def get_connection():
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        cursor_factory=RealDictCursor,  # rows come back as dicts
    )


@contextmanager
def get_cursor():
    """Give a cursor inside one transaction.
    Commits if everything succeeds, rolls back on any error,
    and ALWAYS closes the connection."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
