# app/utils.py

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

logger = logging.getLogger(__name__)

# Secret key and algorithm for JWT
SECRET_KEY = "your_secret_key"  # Replace with your actual secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Adjust as needed

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
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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
    settings = db.query(Settings).first()
    if settings and settings.openmetadata_token:
        return settings.openmetadata_token
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
# app/utils.py
# app/utils.py

# app/utils.py

def get_or_create_database_service(name: str, headers: dict, OPENMETADATA_API_URL: str) -> dict:
    """Retrieve or create the database service by name."""
    try:
        response = requests.get(f"{OPENMETADATA_API_URL}/services/databaseServices/name/{name}", headers=headers)
        if response.status_code == 200:
            logger.info(f"Database service '{name}' found.")
            return response.json()
        else:
            logger.info(f"Database service '{name}' not found. Creating new database service.")
            payload = {
                "serviceType": "CustomDatabase",
                "name": name
            }
            response = requests.post(f"{OPENMETADATA_API_URL}/services/databaseServices", json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"Database service '{name}' created successfully.")
            return response.json()
    except Exception as e:
        logger.error(f"Exception while creating database service '{name}': {str(e)}")
        return {"error": str(e)}

# app/utils.py

def get_or_create_database(name, service_name, headers, OPENMETADATA_API_URL):
    """Retrieve or create a database under the given service."""
    try:
        # Construct the fully qualified name for the database
        database_fqn = f"{service_name}.{name}"
        
        # Try to get the database by fully qualified name
        response = requests.get(f"{OPENMETADATA_API_URL}/databases/name/{database_fqn}", headers=headers)
        
        # Check if the response contains valid JSON data
        if response.status_code == 200:
            logger.info(f"Database '{name}' found under service '{service_name}'.")
            return response.json()
        
        # If the database does not exist, create it
        logger.info(f"Database '{name}' not found. Creating new database.")
        
        # Create the database with the correct payload
        payload = {
            "name": name,
            "service": service_name
        }
        response = requests.post(f"{OPENMETADATA_API_URL}/databases", json=payload, headers=headers)
        
        # Handle unexpected response formats
        try:
            response_data = response.json()
        except ValueError:
            error_msg = f"Unexpected response format when creating database '{name}'. Status Code: {response.status_code}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Check for successful creation or log errors
        if response.status_code in [200, 201]:
            logger.info(f"Database '{name}' created successfully.")
            return response_data
        else:
            error_msg = f"Failed to create database '{name}'. Status Code: {response.status_code}, Response: {response_data}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    except Exception as e:
        error_msg = f"Exception while creating database '{name}': {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

# app/utils.py

def get_or_create_schema(name, service_name, database_name, headers, OPENMETADATA_API_URL):
    """Retrieve or create a database schema under the given database."""
    try:
        # Construct the fully qualified name for the database schema
        schema_fqn = f"{service_name}.{database_name}.{name}"
        
        # Try to get the schema by fully qualified name
        response = requests.get(f"{OPENMETADATA_API_URL}/databaseSchemas/name/{schema_fqn}", headers=headers)
        
        if response.status_code == 200:
            logger.info(f"Database schema '{name}' found under database '{database_name}'.")
            return response.json()
        
        # If schema not found, proceed to create it
        logger.info(f"Database schema '{name}' not found. Creating new schema.")
        
        # Create the schema with the required payload
        payload = {
            "name": name,
            "database": f"{service_name}.{database_name}"
        }
        
        response = requests.post(f"{OPENMETADATA_API_URL}/databaseSchemas", json=payload, headers=headers)
        
        # Check if the response is valid JSON
        try:
            response_data = response.json()
        except ValueError:
            error_msg = f"Unexpected response format when creating schema '{name}'. Status Code: {response.status_code}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Check if the schema creation succeeded
        if response.status_code in [200, 201]:
            logger.info(f"Database schema '{name}' created successfully.")
            return response_data
        else:
            error_msg = f"Failed to create schema '{name}'. Status Code: {response.status_code}, Response: {response_data}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    except Exception as e:
        error_msg = f"Exception while creating schema '{name}': {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def get_team_details(team_id, headers, OPENMETADATA_API_URL):
    """Retrieve team details by team ID."""
    try:
        response = requests.get(f"{OPENMETADATA_API_URL}/teams/{team_id}", headers=headers)
        response.raise_for_status()
        team = response.json()
        return team
    except Exception as e:
        logger.error(f"Error retrieving team details for team_id '{team_id}': {str(e)}")
        return None

def get_or_create_search_service(name, service_type, headers, OPENMETADATA_API_URL):
    """Retrieve or create the search service by name."""
    try:
        response = requests.get(f"{OPENMETADATA_API_URL}/services/searchServices/name/{name}", headers=headers)
        if response.status_code == 200:
            logger.info(f"Search service '{name}' found.")
            return response.json()
        else:
            logger.info(f"Search service '{name}' not found. Creating new search service.")
            payload = {
                "name": name,
                "serviceType": service_type,
                "connection": {
                    "config": {
                        "type": service_type
                    }
                }
            }
            response = requests.post(f"{OPENMETADATA_API_URL}/services/searchServices", json=payload, headers=headers)
            if response.status_code not in [200, 201]:
                error_msg = f"Failed to create search service '{name}'. Status Code: {response.status_code}, Response: {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
            logger.info(f"Search service '{name}' created successfully.")
            return response.json()
    except Exception as e:
        logger.error(f"Exception while creating search service '{name}': {str(e)}")
        return {"error": str(e)}
# app/utils.py

def get_team_details(team_id, headers, OPENMETADATA_API_URL):
    """Retrieve team details by team ID."""
    try:
        response = requests.get(f"{OPENMETADATA_API_URL}/teams/{team_id}", headers=headers)
        response.raise_for_status()
        team = response.json()
        return team
    except Exception as e:
        logger.error(f"Error retrieving team details for team_id '{team_id}': {str(e)}")
        return None

def generate_valid_name(title):
    # Convert to lowercase
    name = title.lower()
    # Replace spaces and special characters with underscores
    name = re.sub(r'[^a-z0-9_]', '_', name)
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    # Trim leading and trailing underscores
    name = name.strip('_')
    # Ensure the name is not empty and within size limits
    if not name or len(name) > 256:
        name = f"table_{uuid.uuid4().hex}"
    return name
