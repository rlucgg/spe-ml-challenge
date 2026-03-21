"""Central configuration for the SPE ML Challenge project."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / ".googledrive" / "Volve Data"
DDR_DIR = DATA_DIR / "Well_technical_data" / "Daily Drilling Report - XML Version"
WITSML_DIR = DATA_DIR / "WITSML Realtime drilling data"
PRODUCTION_FILE = DATA_DIR / "Production_data" / "Volve production data.xlsx"
WELL_PICKS_FILE = DATA_DIR / "Geophysical_Interpretations" / "Wells" / "Well_picks_Volve_v1.dat"
PERFORATIONS_FILE = DATA_DIR / "Geophysical_Interpretations" / "Wells" / "Well_perforations_Volve.dat"

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROCESSED_DIR / "volve.duckdb"
VECTORSTORE_DIR = PROCESSED_DIR / "vectorstore"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
EMBEDDING_MODEL = "text-embedding-3-small"

WITSML_NS = {"witsml": "http://www.witsml.org/schemas/1series"}
SENTINEL_VALUE = -999.99


def normalize_well_name(name: str) -> str:
    """Convert any well name format to canonical underscore format.

    Examples:
        'NO 15/9-F-11 T2' -> '15_9_F_11_T2'
        '15/9-F-11' -> '15_9_F_11'
        '15_9_F_11_T2' -> '15_9_F_11_T2' (already normalized)
    """
    import re
    name = re.sub(r"^NO\s+", "", name.strip())
    name = name.replace("/", "_").replace("-", "_").replace(" ", "_")
    name = re.sub(r"_+", "_", name)
    return name


def display_well_name(underscore_name: str) -> str:
    """Convert underscore format to human-readable display format.

    Examples:
        '15_9_F_11_T2' -> '15/9-F-11 T2'
        '15_9_19_A' -> '15/9-19 A'
        '15_9_F_1_C' -> '15/9-F-1 C'
    """
    parts = underscore_name.split("_")
    if len(parts) < 3:
        return underscore_name

    block_quad = f"{parts[0]}/{parts[1]}"

    if len(parts) > 2 and parts[2] == "F":
        well_num = parts[3] if len(parts) > 3 else ""
        sidetrack = " ".join(parts[4:]) if len(parts) > 4 else ""
        result = f"{block_quad}-F-{well_num}"
        if sidetrack:
            result += f" {sidetrack}"
        return result
    else:
        well_num = parts[2] if len(parts) > 2 else ""
        sidetrack = " ".join(parts[3:]) if len(parts) > 3 else ""
        result = f"{block_quad}-{well_num}"
        if sidetrack:
            result += f" {sidetrack}"
        return result
