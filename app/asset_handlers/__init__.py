# app/asset_handlers/__init__.py

from app.asset_handlers.table_asset_handler import TableAssetHandler
from app.asset_handlers.search_index_asset_handler import SearchIndexAssetHandler
from app.asset_handlers.dashboard_asset_handler import DashboardAssetHandler

asset_handler_registry = {
    "tables": TableAssetHandler,
    "searchIndexes": SearchIndexAssetHandler,
    "dashboards": DashboardAssetHandler,
    # Add other asset handlers here
}
