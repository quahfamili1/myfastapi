# app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models import Settings
from app.schemas import UserLogin, UserCreate, User as UserSchema
from app.utils import verify_password, create_access_token, get_password_hash
from datetime import timedelta
import requests
import logging
import os

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# Configure logger
logger = logging.getLogger(__name__)

OPENMETADATA_API_URL = os.getenv("OPENMETADATA_API_URL", "http://localhost:8585/api/v1/teams")

def get_headers(db: Session):
    """Retrieve authorization headers for OpenMetadata API."""
    settings = db.query(Settings).first()
    if not settings or not settings.openmetadata_token:
        logger.error("OpenMetadata API token not configured.")
        raise HTTPException(status_code=500, detail="OpenMetadata API token is not configured in the database")
    return {"Authorization": f"Bearer {settings.openmetadata_token}", "Content-Type": "application/json"}

def check_team_in_catalog(team_name: str, db: Session) -> str:
    """Check if a team exists in OpenMetadata and return its ID if it does."""
    headers = get_headers(db)
    try:
        response = requests.get(f"{OPENMETADATA_API_URL}/name/{team_name}", headers=headers)
        if response.status_code == 200:
            return response.json().get("id")  # Return the team ID if it exists
    except requests.RequestException as e:
        logger.error(f"Error checking team in catalog: {e}")
    return None

def create_team_in_catalog(team_name: str, db: Session) -> str:
    """Create a team in OpenMetadata and return the team ID."""
    headers = get_headers(db)
    payload = {"name": team_name, "displayName": team_name}
    response = requests.post(OPENMETADATA_API_URL, json=payload, headers=headers)
    if response.status_code == 201:
        return response.json().get("id")  # Return the new team ID if creation is successful
    else:
        logger.error(f"Failed to create team '{team_name}': {response.text}")
        raise HTTPException(status_code=500, detail="Failed to create team in catalog")

@router.post("/login", summary="User login", description="Authenticate a user and return a JWT token.")
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT access token."""
    logger.info(f"Login attempt for user: {user_login.username}")
    user = db.query(User).filter(User.username == user_login.username).first()

    if not user or not verify_password(user_login.password, user.password_hash):
        logger.warning("Invalid login attempt.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.team:
        # Retrieve or create team in OpenMetadata and sync team_id if needed
        team_id = check_team_in_catalog(user.team, db)
        if not team_id:
            team_id = create_team_in_catalog(user.team, db)

        if user.team_id != team_id:
            user.team_id = team_id
            db.commit()

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    logger.info(f"User {user.username} successfully logged in.")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user.username,
            "team": user.team
        }
    }

@router.post("/", response_model=UserSchema, summary="Create a new user", description="Register a new user in the system.")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user, ensuring the team exists in OpenMetadata."""
    logger.info(f"Creating new user: {user.username}")

    if db.query(User).filter(User.username == user.username).first():
        logger.warning(f"Username '{user.username}' already registered.")
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user.password)

    team_id = None
    if user.team:
        # Retrieve or create team in OpenMetadata
        team_id = check_team_in_catalog(user.team, db)
        if not team_id:
            team_id = create_team_in_catalog(user.team, db)
        logger.info(f"Team '{user.team}' ID set to: {team_id}")

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        role=user.role,
        team=user.team,
        team_id=team_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"User {new_user.username} created successfully.")
    return new_user
