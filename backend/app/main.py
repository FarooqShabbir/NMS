"""FastAPI application main entry point."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from .core.config import settings
from .core.database import engine, Base
from .api.router_devices import router as devices_router
from .api.router_routing import router as routing_router
from .api.router_vpn import router as vpn_router
from .api.router_backup import router as backup_router
from .api.router_alerts import router as alerts_router
from .api.router_auth import router as auth_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting NMS Application...")

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(routing_router)
app.include_router(vpn_router)
app.include_router(backup_router)
app.include_router(alerts_router)


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
