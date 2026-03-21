"""Build DuckDB database from parsed data sources."""

import logging
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

from src.config import DB_PATH, PROCESSED_DIR

logger = logging.getLogger(__name__)


def get_connection(db_path: Optional[Path] = None) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection, creating the database file if needed."""
    db_path = db_path or DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def create_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Create all tables in DuckDB."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS ddr_status (
            well VARCHAR,
            date VARCHAR,
            report_no INTEGER,
            md_m DOUBLE,
            tvd_m DOUBLE,
            hole_diameter_in DOUBLE,
            md_csg_last_m DOUBLE,
            tvd_csg_last_m DOUBLE,
            dist_drill_m DOUBLE,
            water_depth_m DOUBLE,
            elev_kelly_m DOUBLE,
            rop_current_m_per_hr DOUBLE,
            summary_24hr VARCHAR,
            forecast_24hr VARCHAR
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS ddr_activities (
            well VARCHAR,
            date VARCHAR,
            start_time VARCHAR,
            end_time VARCHAR,
            depth_m DOUBLE,
            phase VARCHAR,
            activity_code VARCHAR,
            state VARCHAR,
            state_detail VARCHAR,
            comments VARCHAR
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS ddr_fluids (
            well VARCHAR,
            date VARCHAR,
            mud_type VARCHAR,
            mud_class VARCHAR,
            location_sample VARCHAR,
            density_gcc DOUBLE,
            pv_mPas DOUBLE,
            yp_Pa DOUBLE,
            vis_funnel_s DOUBLE
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS ddr_surveys (
            well VARCHAR,
            date VARCHAR,
            md_m DOUBLE,
            tvd_m DOUBLE,
            inclination_deg DOUBLE,
            azimuth_deg DOUBLE
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS wellbore_info (
            well VARCHAR,
            date VARCHAR,
            name_well VARCHAR,
            name_wellbore VARCHAR,
            spud_date VARCHAR,
            drill_complete_date VARCHAR,
            operator VARCHAR,
            drill_contractor VARCHAR,
            rig_name VARCHAR
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS formation_tops (
            well VARCHAR,
            surface_name VARCHAR,
            md_m DOUBLE,
            tvd_m DOUBLE,
            tvdss_m DOUBLE,
            twt_ms DOUBLE
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS perforations (
            well VARCHAR,
            md_top_m DOUBLE,
            md_base_m DOUBLE,
            tvd_top_m DOUBLE,
            tvd_base_m DOUBLE
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS production (
            well VARCHAR,
            date VARCHAR,
            on_stream_hrs DOUBLE,
            avg_downhole_pressure DOUBLE,
            avg_downhole_temperature DOUBLE,
            bore_oil_vol DOUBLE,
            bore_gas_vol DOUBLE,
            bore_wat_vol DOUBLE,
            flow_kind VARCHAR,
            avg_choke_size DOUBLE,
            avg_whp_p DOUBLE,
            avg_wht_p DOUBLE
        )
    """)
    logger.info("All database tables created")


def load_ddr_data(con: duckdb.DuckDBPyConnection, parsed: dict) -> None:
    """Load parsed DDR data into DuckDB tables."""
    if parsed["statuses"]:
        df = pd.DataFrame(parsed["statuses"])
        con.execute("INSERT INTO ddr_status SELECT * FROM df")
        logger.info("Loaded %d DDR status records", len(df))

    if parsed["activities"]:
        df = pd.DataFrame(parsed["activities"])
        con.execute("INSERT INTO ddr_activities SELECT * FROM df")
        logger.info("Loaded %d DDR activity records", len(df))

    if parsed["fluids"]:
        df = pd.DataFrame(parsed["fluids"])
        con.execute("INSERT INTO ddr_fluids SELECT * FROM df")
        logger.info("Loaded %d DDR fluid records", len(df))

    if parsed["surveys"]:
        df = pd.DataFrame(parsed["surveys"])
        con.execute("INSERT INTO ddr_surveys SELECT * FROM df")
        logger.info("Loaded %d DDR survey records", len(df))

    if parsed["wellbore_infos"]:
        df = pd.DataFrame(parsed["wellbore_infos"])
        con.execute("INSERT INTO wellbore_info SELECT * FROM df")
        logger.info("Loaded %d wellbore info records", len(df))


def load_well_tech_data(
    con: duckdb.DuckDBPyConnection,
    formation_tops: list[dict],
    perforations: list[dict],
) -> None:
    """Load well technical data into DuckDB."""
    if formation_tops:
        df = pd.DataFrame(formation_tops)
        con.execute("INSERT INTO formation_tops SELECT * FROM df")
        logger.info("Loaded %d formation top records", len(df))

    if perforations:
        df = pd.DataFrame(perforations)
        con.execute("INSERT INTO perforations SELECT * FROM df")
        logger.info("Loaded %d perforation records", len(df))


def load_production_data(
    con: duckdb.DuckDBPyConnection, prod_df: pd.DataFrame
) -> None:
    """Load production data into DuckDB."""
    if prod_df.empty:
        logger.warning("No production data to load")
        return

    col_map = {
        "well": "well",
        "date": "date",
        "on_stream_hrs": "on_stream_hrs",
        "avg_downhole_pressure": "avg_downhole_pressure",
        "avg_downhole_temperature": "avg_downhole_temperature",
        "bore_oil_vol": "bore_oil_vol",
        "bore_gas_vol": "bore_gas_vol",
        "bore_wat_vol": "bore_wat_vol",
        "flow_kind": "flow_kind",
        "avg_choke_size_p": "avg_choke_size",
        "avg_whp_p": "avg_whp_p",
        "avg_wht_p": "avg_wht_p",
    }

    available_cols = {}
    for src, dst in col_map.items():
        if src in prod_df.columns:
            available_cols[src] = dst

    if not available_cols:
        logger.warning("No matching production columns found")
        return

    df = prod_df[list(available_cols.keys())].rename(columns=available_cols)

    for col in ["well", "date", "on_stream_hrs", "avg_downhole_pressure",
                 "avg_downhole_temperature", "bore_oil_vol", "bore_gas_vol",
                 "bore_wat_vol", "flow_kind", "avg_choke_size", "avg_whp_p",
                 "avg_wht_p"]:
        if col not in df.columns:
            df[col] = None

    con.execute("INSERT INTO production SELECT * FROM df")
    logger.info("Loaded %d production records", len(df))


def build_database(
    parsed_ddrs: dict,
    formation_tops: list[dict],
    perforations: list[dict],
    prod_df: pd.DataFrame,
    db_path: Optional[Path] = None,
) -> Path:
    """Build the complete DuckDB database from all parsed data.

    Returns the path to the database file.
    """
    db_path = db_path or DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database to rebuild fresh
    if db_path.exists():
        db_path.unlink()

    con = get_connection(db_path)
    create_tables(con)
    load_ddr_data(con, parsed_ddrs)
    load_well_tech_data(con, formation_tops, perforations)
    load_production_data(con, prod_df)

    # Log summary stats
    for table in ["ddr_status", "ddr_activities", "ddr_fluids", "ddr_surveys",
                   "wellbore_info", "formation_tops", "perforations", "production"]:
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        logger.info("Table %s: %d rows", table, count)

    con.close()
    logger.info("Database built at %s", db_path)
    return db_path
