# app/asset_handlers/table_asset_handler.py

from app.asset_handlers.base_asset_handler import BaseAssetHandler
from app.utils import (
    get_headers, 
    get_or_create_database_service, 
    get_or_create_database, 
    get_or_create_schema,
    generate_valid_name,
    get_team_details
)
import logging
import requests

logger = logging.getLogger(__name__)

class TableAssetHandler(BaseAssetHandler):
    def __init__(self, db, asset_data, current_user):
        super().__init__(db, asset_data, current_user)
        self.asset_type = "tables"
        # Log the asset data received to confirm attribute data
        logger.debug(f"Asset data received in TableAssetHandler: {self.asset_data}")

    def handle(self):
        """Handles the creation or update of a table asset in OpenMetadata."""
        headers = get_headers(self.db)
        created_assets = []
        errors = []

        # Define the required hierarchy names
        database_service_name = self.asset_data.get("service_name", "default_service")
        database_name = self.asset_data.get("database_name", "default_database")
        schema_name = self.asset_data.get("schema_name", "default_schema")

        # Ensure the parent hierarchy is created or retrieved
        database_service = get_or_create_database_service(database_service_name, headers, self.OPENMETADATA_API_URL)
        if not database_service or 'error' in database_service:
            error_msg = f"Failed to get or create database service '{database_service_name}'."
            errors.append(error_msg)
            logger.error(error_msg)
            return {"success": False, "errors": errors}

        database = get_or_create_database(database_name, database_service_name, headers, self.OPENMETADATA_API_URL)
        if not database or 'error' in database:
            error_msg = f"Failed to get or create database '{database_name}'."
            errors.append(error_msg)
            logger.error(error_msg)
            return {"success": False, "errors": errors}

        database_schema = get_or_create_schema(schema_name, database_service_name, database_name, headers, self.OPENMETADATA_API_URL)
        if not database_schema or 'error' in database_schema:
            error_msg = f"Failed to get or create schema '{schema_name}'."
            errors.append(error_msg)
            logger.error(error_msg)
            return {"success": False, "errors": errors}

        # Construct the full payload for creating or updating the table
        columns = self._construct_columns()
        if not columns:
            logger.warning("No valid columns were constructed for this asset.")

        table_payload = {
            "name": generate_valid_name(self.asset_data["title"]),
            "displayName": self.asset_data["title"],
            "description": self.asset_data.get("description", ""),
            "columns": columns,
            "databaseSchema": f"{database_service_name}.{database_name}.{schema_name}",
            "owners": self._get_owners(),
        }

        # Log the final payload before making the API request
        logger.info(f"Final payload for table creation/update: {table_payload}")

        # Check if the table already exists
        table_fqn = f"{database_service_name}.{database_name}.{schema_name}.{table_payload['name']}"
        existing_table = self._check_existing_table(table_fqn, headers)
        
        try:
            if existing_table:
                # If table exists, use PUT to update it
                logger.info(f"Table '{self.asset_data['title']}' already exists, updating it with PUT.")
                response = requests.put(f"{self.OPENMETADATA_API_URL}/tables", json=table_payload, headers=headers)
            else:
                # If table does not exist, use POST to create it
                logger.info(f"Table '{self.asset_data['title']}' does not exist, creating it with POST.")
                response = requests.post(f"{self.OPENMETADATA_API_URL}/tables", json=table_payload, headers=headers)
            
            response.raise_for_status()
            created_assets.append(response.json())
            logger.info(f"Table '{self.asset_data['title']}' processed successfully.")
            return {"success": True, "created_assets": created_assets}

        except requests.RequestException as e:
            error_msg = f"Failed to process table '{self.asset_data['title']}': {str(e)}"
            if e.response is not None:
                error_msg += f", Response content: {e.response.text}"
            errors.append(error_msg)
            logger.error(error_msg)
            return {"success": False, "errors": errors}

    def _construct_columns(self):
        """Constructs columns for the table from asset data attributes and descriptions."""
        columns = []
        attributes = self.asset_data.get("attributes", [])
        descriptions = self.asset_data.get("att_desc", [])

        # Log the received attributes and descriptions for debugging
        logger.debug(f"Attributes received: {attributes}")
        logger.debug(f"Descriptions received: {descriptions}")

        # Pad descriptions to match attributes length, if necessary
        if len(descriptions) < len(attributes):
            descriptions.extend([""] * (len(attributes) - len(descriptions)))

        for idx, (attr_name, attr_desc) in enumerate(zip(attributes, descriptions), start=1):
            column_name = generate_valid_name(attr_name)
            if not column_name:
                logger.warning(f"Generated column name for attribute '{attr_name}' is empty. Skipping.")
                continue

            column = {
                "name": column_name,
                "displayName": attr_name.strip(),
                "dataType": "VARCHAR",  # Adjust data type as needed
                "dataLength": 100,      # Default or adjust as necessary
                "dataTypeDisplay": "varchar",
                "description": attr_desc.strip() if attr_desc else "",  # Ensuring empty descriptions if absent
                "tags": [],
                "ordinalPosition": idx
            }

            # Log each column to confirm correct structure before adding
            logger.debug(f"Constructed column: {column}")
            columns.append(column)

        # Final logging of all columns
        if columns:
            logger.info(f"Total columns constructed: {len(columns)}")
        else:
            logger.warning("No valid columns constructed for this asset.")

        return columns

    def _get_owners(self):
        """Retrieve owner information for the asset."""
        if self.current_user and self.current_user.team_id:
            team_details = get_team_details(self.current_user.team_id, self.headers, self.OPENMETADATA_API_URL)
            if team_details:
                return [{
                    "id": team_details["id"],
                    "type": "team",
                    "name": team_details["name"]
                }]
            else:
                logger.warning(f"Could not retrieve team details for team ID '{self.current_user.team_id}'.")
        
        # Return an empty list if no owner information is available
        return []



    def _check_existing_table(self, table_fqn, headers):
        """Checks if a table with the specified fully qualified name already exists."""
        try:
            response = requests.get(f"{self.OPENMETADATA_API_URL}/tables/name/{table_fqn}", headers=headers)
            if response.status_code == 200:
                logger.info(f"Table '{table_fqn}' already exists in OpenMetadata.")
                return response.json()
            return None
        except requests.RequestException as e:
            logger.error(f"Error checking existing table '{table_fqn}': {str(e)}")
            return None

    def _get_owners(self):
        """Retrieve owner information for the asset."""
        if self.current_user and self.current_user.team_id:
            team_details = get_team_details(self.current_user.team_id, get_headers(self.db), self.OPENMETADATA_API_URL)
            if team_details:
                return [{
                    "id": team_details["id"],
                    "type": "team",
                    "name": team_details["name"]
                }]
            else:
                logger.warning(f"Could not retrieve team details for team ID '{self.current_user.team_id}'.")
        
        # Return an empty list if no owner information is available
        return []
