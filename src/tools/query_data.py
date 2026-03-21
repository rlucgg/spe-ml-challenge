"""Tool: Query structured drilling data via SQL on DuckDB."""

import logging
from typing import Optional

import duckdb

from src.config import DB_PATH

logger = logging.getLogger(__name__)


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def query_drilling_data(sql_query: str, limit: int = 200) -> str:
    """Execute a SQL query against the Volve drilling database.

    Available tables and columns:
    - ddr_status: well, date, report_no, md_m, tvd_m, hole_diameter_in,
      md_csg_last_m, tvd_csg_last_m, dist_drill_m, water_depth_m,
      elev_kelly_m, rop_current_m_per_hr, summary_24hr, forecast_24hr
    - ddr_activities: well, date, start_time, end_time, depth_m, phase,
      activity_code, state, state_detail, comments
    - ddr_fluids: well, date, mud_type, mud_class, location_sample,
      density_gcc, pv_mPas, yp_Pa, vis_funnel_s
    - ddr_surveys: well, date, md_m, tvd_m, inclination_deg, azimuth_deg
    - wellbore_info: well, date, name_well, name_wellbore, spud_date,
      drill_complete_date, operator, drill_contractor, rig_name
    - formation_tops: well, surface_name, md_m, tvd_m, tvdss_m, twt_ms
    - perforations: well, md_top_m, md_base_m, tvd_top_m, tvd_base_m
    - production: well, date, on_stream_hrs, avg_downhole_pressure,
      avg_downhole_temperature, bore_oil_vol, bore_gas_vol, bore_wat_vol,
      flow_kind, avg_choke_size, avg_whp_p, avg_wht_p
    - witsml_bha_runs: well, wellbore, run_name, start_time, end_time,
      num_bit_run, num_string_run, md_start_m, md_stop_m
    - witsml_mudlog: well, wellbore, md_top_m, md_bottom_m, lith_type,
      lith_pct, rop_avg_m_per_hr, rop_min_m_per_hr, rop_max_m_per_hr,
      wob_avg_kN, torque_avg_kNm, rpm_avg, mud_weight_sg, ecd_sg, dxc,
      methane_avg_ppm, ethane_avg_ppm
    - witsml_trajectory: well, wellbore, timestamp, md_m, tvd_m,
      inclination_deg, azimuth_deg, dls_deg_per_30m, ns_m, ew_m
    - witsml_messages: well, wellbore, timestamp, md_m, message_type,
      message_text

    Well names use underscore format: e.g. '15_9_F_11_T2', '15_9_F_1_C'

    Args:
        sql_query: SQL query to execute
        limit: Maximum rows to return (default 200)

    Returns:
        Query results as formatted text table
    """
    if not sql_query.strip():
        return "Error: Empty query"

    # Safety: add LIMIT if not present
    query_upper = sql_query.upper().strip()
    if "LIMIT" not in query_upper and query_upper.startswith("SELECT"):
        sql_query = f"{sql_query.rstrip().rstrip(';')} LIMIT {limit}"

    try:
        con = _get_con()
        result = con.execute(sql_query)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        con.close()

        if not rows:
            return f"Query returned 0 rows.\nQuery: {sql_query}"

        # Format as text table
        lines = [" | ".join(columns)]
        lines.append("-" * len(lines[0]))
        for row in rows:
            lines.append(" | ".join(str(v) if v is not None else "NULL" for v in row))

        summary = f"\n({len(rows)} rows returned)"
        return "\n".join(lines) + summary

    except Exception as e:
        return f"SQL Error: {e}\nQuery: {sql_query}"


def get_available_wells() -> list[str]:
    """Get list of all wells in the database."""
    try:
        con = _get_con()
        rows = con.execute(
            "SELECT DISTINCT well FROM ddr_status ORDER BY well"
        ).fetchall()
        con.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def get_table_schema(table_name: str) -> str:
    """Get schema for a specific table."""
    try:
        con = _get_con()
        result = con.execute(f"DESCRIBE {table_name}")
        rows = result.fetchall()
        con.close()
        return "\n".join(f"  {r[0]}: {r[1]}" for r in rows)
    except Exception as e:
        return f"Error: {e}"
