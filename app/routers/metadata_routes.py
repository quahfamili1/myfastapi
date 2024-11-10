# app/routers/metadata_routes.py
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List
import requests
from app.config import settings  # Load settings for API URL and token

# Initialize Router
router = APIRouter()

# Define Pydantic Models
class Attribute(BaseModel):
    name: str
    description: str

class Metadata(BaseModel):
    displayName: str
    description: str
    attributes: List[Attribute]
    tag: str

class RegenerateRequest(BaseModel):
    assetId: str
    displayName: str
    attributes: List[str]

# OpenMetadata configuration from environment variables or config
OPENMETADATA_API_URL = settings.OPENMETADATA_API_URL
API_TOKEN = settings.OPENMETADATA_TOKEN

@router.get("/metadata/suggestions/{assetId}", response_model=Metadata)
async def get_metadata_suggestions(assetId: str):
    """Fetch metadata suggestions from OpenMetadata based on asset ID"""
    asset_type = "tables"
    url = f"{OPENMETADATA_API_URL}/{asset_type}/{assetId}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Asset with ID {assetId} not found in OpenMetadata.")
        response.raise_for_status()
        data = response.json()
        metadata = Metadata(
            displayName=data.get("displayName", ""),
            description=data.get("description", ""),
            attributes=[
                Attribute(name=column.get("name", ""), description=column.get("description", ""))
                for column in data.get("columns", [])
            ],
            tag=data.get("tags", [{}])[0].get("tagFQN", "") if data.get("tags") else "",
        )
        return metadata

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail="Failed to fetch metadata from OpenMetadata") from e

@router.post("/metadata/regenerate", response_model=Metadata)
async def regenerate_metadata(request: RegenerateRequest):
    """Regenerate metadata suggestions using an external Python script (simulated with mock data)"""
    # Simulate the external script output using mock data
    # In a real scenario, you would call the external script here
    external_script_output = {
        "displayName": request.displayName,
        "description": f"Regenerated description for {request.displayName}",
        "attributes": [
            {"name": attr_name, "description": f"Regenerated description for {attr_name}"}
            for attr_name in request.attributes
        ],
        "tag": "RegeneratedTag"
    }

    metadata = Metadata(**external_script_output)
    return metadata

@router.patch("/metadata/update/{assetId}", response_model=dict)
async def update_metadata(assetId: str, metadata: Metadata = Body(...)):
    """Update metadata in OpenMetadata using PATCH"""
    asset_type = "tables"
    url = f"{OPENMETADATA_API_URL}/{asset_type}/{assetId}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json-patch+json",
    }

    # Fetch the current version of the asset to include in If-Match header
    try:
        get_response = requests.get(url, headers={"Authorization": f"Bearer {API_TOKEN}"})
        get_response.raise_for_status()
        current_asset = get_response.json()
        current_version = current_asset.get("version")
        if not current_version:
            raise HTTPException(status_code=500, detail="Unable to retrieve current asset version.")
    except requests.RequestException as e:
        print("Error during GET request:", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve current asset from OpenMetadata") from e

    headers["If-Match"] = str(current_version)

    # Construct the JSON Patch payload
    patch_operations = []

    # Update displayName if it differs from the current value
    if metadata.displayName != current_asset.get("displayName", ""):
        patch_operations.append({
            "op": "replace",
            "path": "/displayName",
            "value": metadata.displayName
        })

    # Update description if it differs from the current value
    if metadata.description != current_asset.get("description", ""):
        patch_operations.append({
            "op": "replace",
            "path": "/description",
            "value": metadata.description
        })

    # Process attributes (columns)
    current_columns = current_asset.get("columns", [])
    column_name_to_index = {col.get("name"): idx for idx, col in enumerate(current_columns)}
    processed_columns = set()

    for index, attr in enumerate(metadata.attributes):
        if attr.name in column_name_to_index:
            column_index = column_name_to_index[attr.name]
            current_column = current_columns[column_index]
            if attr.name != current_column.get("name", ""):
                patch_operations.append({
                    "op": "replace",
                    "path": f"/columns/{column_index}/name",
                    "value": attr.name
                })
            if attr.description != current_column.get("description", ""):
                patch_operations.append({
                    "op": "replace",
                    "path": f"/columns/{column_index}/description",
                    "value": attr.description
                })
            processed_columns.add(attr.name)
        else:
            new_column = {
                "name": attr.name,
                "dataType": "VARCHAR",  # Default type, adjust as needed
                "description": attr.description,
            }
            patch_operations.append({
                "op": "add",
                "path": "/columns/-",
                "value": new_column
            })

    indices_to_remove = [idx for col_name, idx in column_name_to_index.items() if col_name not in processed_columns]
    for index in sorted(indices_to_remove, reverse=True):
        patch_operations.append({
            "op": "remove",
            "path": f"/columns/{index}"
        })

    current_tags = current_asset.get("tags", [])
    new_tag = {"tagFQN": metadata.tag} if metadata.tag else None
    if new_tag:
        if not current_tags or current_tags[0].get("tagFQN", "") != metadata.tag:
            patch_operations.append({
                "op": "replace" if current_tags else "add",
                "path": "/tags",
                "value": [new_tag]
            })
    elif current_tags:
        patch_operations.append({
            "op": "remove",
            "path": "/tags"
        })

    if not patch_operations:
        return {"message": "No changes detected."}

    # Debugging output
    print("Headers for PATCH:", headers)
    print("Patch Operations:", patch_operations)

    # Send the PATCH request to update the asset
    try:
        response = requests.patch(url, headers=headers, json=patch_operations)
        print("PATCH Response Status Code:", response.status_code)
        print("PATCH Response Content:", response.text)
        response.raise_for_status()
        return {"message": "Metadata updated successfully"}
    except requests.RequestException as e:
        print("Error during PATCH request:", e)
        raise HTTPException(status_code=500, detail=f"Failed to update metadata in OpenMetadata: {e}") from e
