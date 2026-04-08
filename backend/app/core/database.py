"""Database connections - PostgreSQL and InfluxDB."""
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from .config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# ── lazy singletons ──────────────────────────────────────
_engine = None
_SessionLocal = None


def _get_engine():
    """Create engine on first use, not at import time."""
    global _engine
    if _engine is None:
        url = settings.SQLALCHEMY_DATABASE_URL

        # Log masked URL so you can verify in Vercel logs
        import re
        masked = re.sub(r':([^@]+)@', ':***@', url)
        logger.info("Initializing DB engine with URL: %s", masked)

        engine_kwargs = {"pool_pre_ping": True}

        if settings.DB_USE_NULL_POOL:
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs.update({
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_recycle": settings.DB_POOL_RECYCLE,
            })

        _engine = create_engine(url, **engine_kwargs)

    return _engine


def _get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_get_engine()
        )
    return _SessionLocal


def get_db():
    """Get database session."""
    SessionLocal = _get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── InfluxDB (keep as-is, it's fine) ─────────────────────
influxdb_client = None
influxdb_write_api = None
influxdb_query_api = None

if settings.INFLUXDB_ENABLED:
    try:
        influxdb_client = InfluxDBClient(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN,
            org=settings.INFLUXDB_ORG,
        )
        influxdb_write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
        influxdb_query_api = influxdb_client.query_api()
    except Exception as exc:
        logger.warning("InfluxDB client initialization failed: %s", exc)


def get_influxdb_write_api():
    if influxdb_write_api is None:
        raise RuntimeError("InfluxDB write API is not initialized.")
    return influxdb_write_api


def get_influxdb_query_api():
    if influxdb_query_api is None:
        raise RuntimeError("InfluxDB query API is not initialized.")
    return influxdb_query_api