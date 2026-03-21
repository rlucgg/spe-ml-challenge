"""Parse Volve production data from Excel."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from src.config import PRODUCTION_FILE

logger = logging.getLogger(__name__)


def parse_production_data(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Parse production data Excel file into a DataFrame.

    Returns DataFrame with columns: well, date, on_stream_hrs, avg_downhole_pressure,
    avg_downhole_temperature, bore_oil_vol, bore_gas_vol, bore_water_vol, etc.
    """
    filepath = filepath or PRODUCTION_FILE
    if not filepath.exists():
        logger.warning("Production file not found: %s", filepath)
        return pd.DataFrame()

    logger.info("Reading production data from %s", filepath)
    df = pd.read_excel(filepath, sheet_name="Daily Production Data")

    rename_map = {}
    for col in df.columns:
        clean = (
            col.strip()
            .lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("/", "_per_")
        )
        rename_map[col] = clean
    df = df.rename(columns=rename_map)

    if "dateprd" in df.columns:
        df = df.rename(columns={"dateprd": "date"})
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    if "npd_well_bore_code" in df.columns:
        df = df.rename(columns={"npd_well_bore_code": "npd_code"})
    if "npd_well_bore_name" in df.columns:
        df = df.rename(columns={"npd_well_bore_name": "well"})

    logger.info("Parsed %d production records", len(df))
    return df
