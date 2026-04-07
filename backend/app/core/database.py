"""Database connections - PostgreSQL and InfluxDB."""
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from .config import settings

logger = logging.getLogger(__name__)

# PostgreSQL
engine_kwargs = {
    "pool_pre_ping": True,
}

if settings.DB_USE_NULL_POOL:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs.update(
        {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_recycle": settings.DB_POOL_RECYCLE,
        }
    )

engine = None
engine_init_error = None
try:
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URL, **engine_kwargs)
except Exception as exc:
    engine_init_error = exc
    logger.error("Database engine initialization failed: %s", exc, exc_info=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Get database session."""
    if engine is None:
        raise RuntimeError(f"Database engine is not initialized: {engine_init_error}")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# InfluxDB
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
    """Get InfluxDB write API."""
    if influxdb_write_api is None:
        raise RuntimeError("InfluxDB write API is not initialized. Check INFLUXDB settings.")
    return influxdb_write_api


def get_influxdb_query_api():
    """Get InfluxDB query API."""
    if influxdb_query_api is None:
        raise RuntimeError("InfluxDB query API is not initialized. Check INFLUXDB settings.")
    return influxdb_query_api
