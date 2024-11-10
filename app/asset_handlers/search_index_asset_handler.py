# app/asset_handlers/search_index_asset_handler.py

import logging
import requests
from app.asset_handlers.base_asset_handler import BaseAssetHandler
from app.utils import generate_valid_name

logger = logging.getLogger(__name__)

class SearchIndexAssetHandler(BaseAssetHandler):
    OPENMETADATA_API_URL = "http://localhost:8585/api/v1"  # Adjust as necessary

    DEFAULT_SEARCH_SERVICE_NAME = "default_search_service"

    def validate_asset_data(self):
        # Validate and process asset data
        self.asset_name = self.asset_data.get('name') or self.asset_data.get('title')
        if not self.asset_name:
            raise ValueError("Asset must have a 'name' or 'title' field.")
        self.asset_name = generate_valid_name(self.asset_name)
        if not self.asset_name:
            raise ValueError("Generated 'name' field is empty after sanitization.")

        self.description = self.asset_data.get('description', '')
        self.fields = self.asset_data.get('fields', [])
        if not self.fields:
            raise ValueError("SearchIndex must have at least one field.")

        # Process fields
        self.processed_fields = []
        for idx, field in enumerate(self.fields, start=1):
            field_name = generate_valid_name(field.get('name'))
            if not field_name:
                raise ValueError(f"Field name is invalid: {field.get('name')}")
            self.processed_fields.append({
                "name": field_name,
                "displayName": field.get('name'),
                "dataType": field.get('dataType', 'VARCHAR'),
                "description": field.get('description', ''),
                "ordinalPosition": idx
            })

    def prepare_payload(self):
        # Prepare the payload for the API request
        self.payload = {
            "name": self.asset_name,
            "displayName": self.asset_data.get('displayName', self.asset_name),
            "description": self.description,
            "fields": self.processed_fields,
            "service": self.DEFAULT_SEARCH_SERVICE_NAME
            # Add other necessary fields
        }

    def ingest_asset(self):
        # Make the API request to ingest the asset
        url = f"{self.OPENMETADATA_API_URL}/searchIndexes"
        response = requests.post(url, json=self.payload, headers=self.headers)
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create search index. Status Code: {response.status_code}, Response: {response.text}")
        logger.info(f"SearchIndex '{self.asset_name}' created successfully.")
