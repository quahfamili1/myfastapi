import logging
import re
import uuid
import requests
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Settings, User
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from app.config import settings  # Import settings for configuration

logger = logging.getLogger(__name__)

# Secret key and algorithm for JWT from configuration
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.TOKEN_EXPIRE_MINUTES

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_password_hash(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plaintext password matches a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Retrieve the current user based on the token."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception
        return user
    except JWTError as e:
        logger.error(f"JWT Error: {str(e)}")
        raise credentials_exception

def get_openmetadata_token(db: Session):
    """Retrieve OpenMetadata token from the database settings."""
    settings_record = db.query(Settings).first()
    if settings_record and settings_record.openmetadata_token:
        return settings_record.openmetadata_token
    logger.error("OpenMetadata API token not found in the database.")
    raise HTTPException(status_code=500, detail="OpenMetadata API token is not configured in the database")

def get_headers(db: Session) -> dict:
    """Generate headers for OpenMetadata API requests."""
    token = get_openmetadata_token(db)
    if not token:
        raise HTTPException(status_code=500, detail="OpenMetadata API token is not configured.")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def get_or_create_database_service(name: str, headers: dict) -> dict:
    """Retrieve or create the database service by name."""
    try:
        response = requests.get(f"{settings.OPENMETADATA_API_URL}/services/databaseServices/name/{name}", headers=headers)
        if response.status_code == 200:
            logger.info(f"Database service '{name}' found.")
            return response.json()
        else:
            logger.info(f"Database service '{name}' not found. Creating new database service.")
            payload = {
                "serviceType": "CustomDatabase",
                "name": name
            }
            response = requests.post(f"{settings.OPENMETADATA_API_URL}/services/databaseServices", json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"Database service '{name}' created successfully.")
            return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Exception while creating database service '{name}': {str(e)}")
        return {"error": str(e)}

def get_or_create_database(name: str, service_name: str, headers: dict) -> dict:
    """Retrieve or create a database under the given service."""
    try:
        database_fqn = f"{service_name}.{name}"
        response = requests.get(f"{settings.OPENMETADATA_API_URL}/databases/name/{database_fqn}", headers=headers)

        if response.status_code == 200:
            logger.info(f"Database '{name}' found under service '{service_name}'.")
            return response.json()

        logger.info(f"Database '{name}' not found. Creating new database.")
        payload = {
            "name": name,
            "service": {
                "id": service_name
            }
        }
        response = requests.post(f"{settings.OPENMETADATA_API_URL}/databases", json=payload, headers=headers)

        response_data = response.json() if response.status_code in [200, 201] else {"error": response.text}
        if response.status_code in [200, 201]:
            logger.info(f"Database '{name}' created successfully.")
        else:
            logger.error(f"Failed to create database '{name}'. Status Code: {response.status_code}, Response: {response_data['error']}")
        
        return response_data
    except requests.exceptions.RequestException as e:
        error_msg = f"Exception while creating database '{name}': {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

def get_or_create_schema(name: str, service_name: str, database_name: str, headers: dict) -> dict:
    """Retrieve or create a database schema under the given database."""
    try:
        schema_fqn = f"{service_name}.{database_name}.{name}"
        response = requests.get(f"{settings.OPENMETADATA_API_URL}/databaseSchemas/name/{schema_fqn}", headers=headers)

        if response.status_code == 200:
            logger.info(f"Database schema '{name}' found under database '{database_name}'.")
            return response.json()

        logger.info(f"Database schema '{name}' not found. Creating new schema.")
        payload = {
            "name": name,
            "database": {
                "id": f"{service_name}.{database_name}"
            }
        }
        response = requests.post(f"{settings.OPENMETADATA_API_URL}/databaseSchemas", json=payload, headers=headers)

        response_data = response.json() if response.status_code in [200, 201] else {"error": response.text}
        if response.status_code in [200, 201]:
            logger.info(f"Database schema '{name}' created successfully.")
        else:
            logger.error(f"Failed to create schema '{name}'. Status Code: {response.status_code}, Response: {response_data['error']}")
        
        return response_data
    except requests.exceptions.RequestException as e:
        error_msg = f"Exception while creating schema '{name}': {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

def get_team_details(team_id: str, headers: dict) -> dict:
    """Retrieve team details by team ID."""
    try:
        response = requests.get(f"{settings.OPENMETADATA_API_URL}/teams/{team_id}", headers=headers)
        response.raise_for_status()
        team = response.json()
        return team
    except requests.exceptions.RequestException as e:
        logger.error(f"Error retrieving team details for team_id '{team_id}': {str(e)}")
        return None

def generate_valid_name(title: str) -> str:
    """Generate a valid name from a given title."""
    name = title.lower()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    if not name or len(name) > 256:
        name = f"table_{uuid.uuid4().hex}"
    return name
