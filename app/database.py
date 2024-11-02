# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv
from app.models import User, Settings  # Import models directly from app.models
from app.models.base import Base       # Import Base from models/base.py

# Load environment variables
load_dotenv()

# Database connection parameters
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3307")

# Construct the database URL
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# Set up the engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Provide a session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_default_user(db: Session):
    """Create a default user if it doesn't exist."""
    default_user = db.query(User).filter(User.username == 'admin').first()
    if not default_user:
        default_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=User.get_password_hash('123'),
            role='user',
            team='best1',
            team_id='83f9c0ed-14b5-4c42-a22b-f60f83eef400'
        )
        db.add(default_user)
        db.commit()

def create_default_settings(db: Session):
    """Create default settings if they don't exist."""
    settings = db.query(Settings).first()
    if not settings:
        default_token = (
            "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImNhdGFsb2ciLCJyb2xlcyI6W10sImVtYWlsIjoiY2F0YWxvZ0BvcGVuLW1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3Mjg4MTg3MzIsImV4cCI6bnVsbH0.zUtNXPA9FHIDFZ68hn_SXcYlcDF_No9EjsjkV8kRHXeEKw1CEKgAy9Tmcrb8Rc0kvbBYXHvwhVO7x0ST29fg0A7PY_OI7RJkuTjqlZ_oZkMxsnanKBrmkh9cJi07x5wyYqGFptdF4AxjRzvH4GuE_xaMsmsxESnpq7C-eFauOwJ7mXy0KAYxIFC8nc4ps5MGzi5JgCytkaVS8OWnlVLvMx-PfeW-qwtJ_CgZcoDXb8g93O2FPiAUrfZv196b7vaygEPRZt0DBrvzlju9RB62llwjrvefD6BkQF_L9KhTU9rX5gE3Y3VFMFNdheKc6ecq1H4OsaZ7uyO7SH2GBiVE5Q"  # Replace this with the actual token or use an environment variable
        )
        settings = Settings(id="default", openmetadata_token=default_token)
        db.add(settings)
        db.commit()
