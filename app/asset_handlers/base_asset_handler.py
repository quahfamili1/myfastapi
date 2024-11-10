# app/asset_handlers/base_asset_handler.py

import logging
import requests
from app.utils import get_headers

logger = logging.getLogger(__name__)

class BaseAssetHandler:
# app/asset_handlers/base_asset_handler.py
    OPENMETADATA_API_URL = "http://localhost:8585/api/v1"  # Adjust this URL as necessary

    def __init__(self, db, asset_data, current_user):
        self.db = db
        self.asset_data = asset_data
        self.current_user = current_user
        self.headers = get_headers(self.db)


    def handle(self):
        raise NotImplementedError("Subclasses should implement this method")

    def update_asset(self, asset_id):
        raise NotImplementedError("Subclasses should implement this method")

    def delete_asset(self, asset_id):
        raise NotImplementedError("Subclasses should implement this method")

    def claim_asset(self, asset_id):
        """
        Claims ownership of an asset if it is unowned.
        This logic is shared across asset types.
        """
        asset_url = f"{self.OPENMETADATA_API_URL}/{self.asset_type}/{asset_id}"

        try:
            # Check current ownership of the asset
            response = requests.get(asset_url, headers=self.headers)
            response.raise_for_status()
            asset_data = response.json()
            asset_owners = asset_data.get("owners", [])

            # Check if the asset is unowned
            if asset_owners:
                logger.warning(f"Asset {asset_id} is already owned.")
                return {"success": False, "errors": ["Asset is already owned"]}

            # Update the asset ownership with the current user's team
            payload = {
                "op": "replace",
                "path": "/owners",
                "value": [
                    {
                        "type": "team",
                        "id": self.current_user.team_id,
                        "name": self.current_user.team
                    }
                ]
            }
            claim_headers = self.headers.copy()
            claim_headers["Content-Type"] = "application/json-patch+json"
            claim_response = requests.patch(asset_url, json=[payload], headers=claim_headers)
            claim_response.raise_for_status()

            logger.info(f"User {self.current_user.id} claimed asset {asset_id}")
            return {"success": True, "data": claim_response.json()}
        except requests.RequestException as e:
            logger.error(f"Error claiming asset: {str(e)}")
            return {"success": False, "errors": [f"Failed to communicate with OpenMetadata API: {str(e)}"]}
