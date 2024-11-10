# app/asset_handlers/dashboard_asset_handler.py

from app.asset_handlers.base_asset_handler import BaseAssetHandler
from app.utils import (
    get_headers,
    generate_valid_name,
    get_team_details
)
import logging
import requests

logger = logging.getLogger(__name__)

class DashboardAssetHandler(BaseAssetHandler):
    def __init__(self, db, asset_data, current_user):
        super().__init__(db, asset_data, current_user)
        self.asset_type = "dashboards"  # Define the asset type here

    # Implement or override methods as needed


    DEFAULT_DASHBOARD_SERVICE_NAME = "default_dashboard_service"

    def validate_asset_data(self):
        # Validate and process asset data
        self.asset_name = self.asset_data.get('name') or self.asset_data.get('title')
        if not self.asset_name:
            raise ValueError("Asset must have a 'name' or 'title' field.")
        self.asset_name = generate_valid_name(self.asset_name)
        if not self.asset_name:
            raise ValueError("Generated 'name' field is empty after sanitization.")

        self.description = self.asset_data.get('description', '')
        # Process other dashboard-specific data

    def prepare_payload(self):
        # Prepare the payload for the API request
        self.payload = {
            "name": self.asset_name,
            "displayName": self.asset_data.get('displayName', self.asset_name),
            "description": self.description,
            "service": self.DEFAULT_DASHBOARD_SERVICE_NAME
            # Add other necessary fields
        }

    def ingest_asset(self):
        # Make the API request to ingest the asset
        url = f"{self.OPENMETADATA_API_URL}/dashboards"
        response = requests.post(url, json=self.payload, headers=self.headers)
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create dashboard. Status Code: {response.status_code}, Response: {response.text}")
        logger.info(f"Dashboard '{self.asset_name}' created successfully.")
