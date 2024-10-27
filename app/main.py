# app/main.py
import sys
import os

# Add the project root path to sys.path explicitly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, SessionLocal, create_default_user
from app import models

# Drop all existing tables (use with caution in a production environment)
models.Base.metadata.drop_all(bind=engine)

# Create tables in the database
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Allow CORS from any origin for development (be careful in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in production to the specific domains that should be allowed
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include routers (assuming they exist)
from app.routers import users, assets, claim_requests, metadata
app.include_router(users.router)
app.include_router(assets.router)
app.include_router(claim_requests.router)
app.include_router(metadata.router)

# Create default user on startup
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        create_default_user(db)
    finally:
        db.close()
