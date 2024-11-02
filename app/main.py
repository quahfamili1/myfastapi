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

# Drop all existing tables (use with caution in a production environment)
logger.warning("Dropping all existing tables - use caution in production.")
models.Base.metadata.drop_all(bind=engine)

# Create tables in the database
logger.info("Creating database tables.")
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Allow CORS from any origin for development (be careful in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Change this in production to specific domains that should be allowed
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include routers with a versioned prefix
from app.routers import users, assets, metadata
app.include_router(users.router, prefix="/api/v1")           # Use /api/v1 prefix
app.include_router(assets.router, prefix="/api/v1")
app.include_router(metadata.router, prefix="/api/v1")

# Define a lifespan event handler to replace the deprecated startup event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run at startup
    logger.info("Application startup - creating default user and settings.")
    db = SessionLocal()
    try:
        # Create the default user if it doesn't exist
        create_default_user(db)
        logger.info("Default user created successfully.")
        
        # Ensure default OpenMetadata token is set
        create_default_settings(db)
        logger.info("Default settings initialized successfully.")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
    finally:
        db.close()

    yield  # Control passes here during the app's lifecycle

    # Code to run at shutdown
    logger.info("Application shutdown.")

app.router.lifespan_context = lifespan

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8005,
        log_level="debug",
        reload=True
    )
