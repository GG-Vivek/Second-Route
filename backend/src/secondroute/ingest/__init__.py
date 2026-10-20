"""
Partner data ingestion (Phase 3).

Adapters that bring external data in: partner sales imports, FRED component
prices and Wikimedia demand signals.
"""

from secondroute.ingest.models import (
    ComponentPrice,
    DecayParam,
    DemandSignal,
    ImportFile,
    LaunchEvent,
    TeardownYield,
)
from secondroute.ingest.sales import (
    auto_detect_mapping,
    file_hash,
    import_sales,
    parse_sales_csv,
    preview_sales_file,
)
from secondroute.ingest.schemas import (
    ColumnMapping,
    ImportPreview,
    ImportRecordRead,
    ImportResult,
    RejectedRow,
)

__all__ = [
    "ColumnMapping",
    "ComponentPrice",
    "DecayParam",
    "DemandSignal",
    "ImportFile",
    "ImportPreview",
    "ImportRecordRead",
    "ImportResult",
    "LaunchEvent",
    "RejectedRow",
    "TeardownYield",
    "auto_detect_mapping",
    "file_hash",
    "import_sales",
    "parse_sales_csv",
    "preview_sales_file",
]
