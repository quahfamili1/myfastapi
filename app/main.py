# app/main.py
import sys
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, SessionLocal, create_default_user, create_default_settings
from app import models
from contextlib import asynccontextmanager

# Configure logging for the entire application
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all log messages
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Configure uvicorn’s logger explicitly
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.setLevel(logging.DEBUG)
uvicorn_error_logger = logging.getLogger("uvicorn.error")
uvicorn_error_logger.setLevel(logging.DEBUG)

# Add the project root path to sys.path explicitly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Drop all existing tables (use caution in production)
logger.warning("Dropping all existing tables - use caution in production.")
models.Base.metadata.drop_all(bind=engine)

# Create tables in the database
logger.info("Creating database tables.")
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI()

# Allow CORS from any origin for development (configure carefully in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update for production-specific domains
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Import and include routers with a versioned prefix
from app.routers import team_assets, users, assets, metadata, unowned_assets, temporary_assets
app.include_router(users.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")
app.include_router(metadata.router, prefix="/api/v1")
app.include_router(team_assets.router, prefix="/api/v1")
app.include_router(unowned_assets.router, prefix="/api/v1")
app.include_router(temporary_assets.router, prefix="/api/v1")

# Define a lifespan event handler to manage app startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run at startup
    logger.info("Application startup - initializing default user and settings.")
    db = SessionLocal()
    try:
        create_default_user(db)
        logger.info("Default user created successfully.")
        
        create_default_settings(db)
        logger.info("Default settings initialized successfully.")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
    finally:
        db.close()

    yield  # Control passes here during the app's lifecycle

    # Code to run at shutdown
    logger.info("Application shutdown.")

# Set lifespan context for the application
app.router.lifespan_context = lifespan

# Run the application with uvicorn if this file is the entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8005,
        log_level="debug",
        reload=True
    )
