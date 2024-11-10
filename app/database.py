# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models import User, Settings, TemporaryAsset  # Import models directly
from app.models.base import Base  # Import Base from models/base.py
from app.config import settings  # Import the settings from config.py

# Set up the engine and session using settings from config.py
DATABASE_URL = (
    f"mysql+pymysql://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}@"
    f"{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"
)
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
            password_hash=User.get_password_hash('123'),  # Replace with a more secure password
            role='admin',
            team='best1',
            team_id='83f9c0ed-14b5-4c42-a22b-f60f83eef400'
        )
        db.add(default_user)
        db.commit()

def create_default_settings(db: Session):
    """Create default settings if they don't exist."""
    settings_entry = db.query(Settings).first()
    if not settings_entry:
        settings_entry = Settings(
            id="default",
            openmetadata_token=settings.OPENMETADATA_TOKEN  # Use token from environment variable
        )
        db.add(settings_entry)
        db.commit()

# Create tables if they do not exist
def init_db():
    Base.metadata.create_all(bind=engine)
