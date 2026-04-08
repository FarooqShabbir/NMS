"""Database connections - PostgreSQL and InfluxDB."""
import logging
import re

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from .config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# Public names that main.py imports directly
engine = None
engine_init_error = None


def _init_engine():
    """Initialize engine lazily on first use."""
    global engine, engine_init_error

    if engine is not None:
        return engine

    try:
        url = settings.SQLALCHEMY_DATABASE_URL

        # Log masked URL to verify correct password is used
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

        engine = create_engine(url, **engine_kwargs)
        engine_init_error = None
        logger.info("DB engine initialized successfully.")

    except Exception as exc:
        engine_init_error = exc
        engine = None
        logger.error("Database engine initialization failed: %s", exc, exc_info=True)

    return engine


# Initialize on module load — but failures won't crash the app
_init_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session, retrying engine init if it previously failed."""
    global SessionLocal

    current_engine = _init_engine()  # retry if engine was None

    if current_engine is None:
        raise RuntimeError(f"Database engine is not initialized: {engine_init_error}")

    # Rebind session if engine was just initialized
    if SessionLocal.kw.get("bind") is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=current_engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── InfluxDB ─────────────────────────────────────────────
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