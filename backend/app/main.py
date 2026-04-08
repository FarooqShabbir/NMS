"""FastAPI application main entry point."""
from importlib import import_module
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from .core.config import settings
from .core.database import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _load_router(module_name: str, router_name: str):
    """Load a router module safely so one import failure does not crash app startup."""
    try:
        module = import_module(module_name)
        return getattr(module, "router")
    except Exception as exc:
        logger.error("Skipping router '%s' due import error: %s", router_name, exc, exc_info=True)
        return None


loaded_routers = [
    _load_router("app.api.router_auth", "auth"),
    _load_router("app.api.router_devices", "devices"),
    _load_router("app.api.router_routing", "routing"),
    _load_router("app.api.router_vpn", "vpn"),
    _load_router("app.api.router_backup", "backup"),
    _load_router("app.api.router_alerts", "alerts"),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting NMS Application...")

    try:
        if settings.AUTO_CREATE_TABLES:
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=engine)
        else:
            logger.info("Skipping automatic table creation (AUTO_CREATE_TABLES=false)")

        if settings.SEED_DEFAULT_ADMIN:
            from sqlalchemy.orm import Session
            from .models.user import User, UserRole
            from .core.security import get_password_hash

            db = Session(bind=engine)
            try:
                admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
                if not admin:
                    admin = User(
                        username=settings.ADMIN_USERNAME,
                        email=settings.ADMIN_EMAIL,
                        full_name=settings.ADMIN_FULL_NAME,
                        hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                        role=UserRole.ADMIN,
                        is_superuser=True,
                    )
                    db.add(admin)
                    db.commit()
                    logger.info("Created default admin user (%s)", settings.ADMIN_USERNAME)
            finally:
                db.close()
        else:
            logger.info("Skipping default admin seeding (SEED_DEFAULT_ADMIN=false)")
    except Exception as exc:
        if settings.IS_VERCEL:
            logger.error("Startup initialization failed on Vercel: %s", exc, exc_info=True)
            logger.info("Continuing without startup initialization.")
        else:
            raise

    logger.info("NMS Application started successfully!")

    yield

    # Shutdown
    logger.info("Shutting down NMS Application...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Network Monitoring System with SNMP backend",
    lifespan=lifespan,
)

# CORS middleware
# On Vercel, vercel.json headers handle origin restriction at the edge,
# so we use ["*"] to avoid double-filtering. Locally, use parsed origins.
cors_origins = ["*"] if settings.IS_VERCEL else settings.parsed_cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Explicit OPTIONS handler for preflight requests (safety net for Vercel)
@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    """Handle CORS preflight requests explicitly."""
    return JSONResponse(
        content=None,
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "https://netmonitoring.vercel.app",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Requested-With",
            "Access-Control-Allow-Credentials": "true",
        },
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# Include routers
for router in loaded_routers:
    if router is not None:
        app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
