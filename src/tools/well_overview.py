"""Tool: Get well overview and metadata."""

import logging
from typing import Optional

import duckdb

from src.config import DB_PATH, display_well_name

logger = logging.getLogger(__name__)


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def get_well_overview(well: str) -> str:
    """Get comprehensive overview for a well/wellbore section.

    Includes: date range, depth range, hole sizes, number of DDR reports,
    activity code distribution, wellbore info, and formation tops.

    Args:
        well: Well name in underscore format (e.g. '15_9_F_11_T2').
              Use '%' for wildcard matching.

    Returns:
        Formatted well overview text
    """
    con = _get_con()
    like_pattern = well.replace("*", "%")

    lines = [f"=== Well Overview: {display_well_name(well)} ===\n"]

    # Basic info
    try:
        row = con.execute("""
            SELECT
                MIN(date) as first_date,
                MAX(date) as last_date,
                COUNT(DISTINCT date) as num_reports,
                MIN(md_m) as min_depth,
                MAX(md_m) as max_depth,
                MIN(tvd_m) as min_tvd,
                MAX(tvd_m) as max_tvd
            FROM ddr_status
            WHERE well LIKE ?
        """, [like_pattern]).fetchone()

        if row and row[0]:
            lines.append(f"Date Range: {row[0]} to {row[1]}")
            lines.append(f"Number of DDR Reports: {row[2]}")
            lines.append(f"MD Range: {row[3]:.1f}m to {row[4]:.1f}m")
            if row[5] and row[6]:
                lines.append(f"TVD Range: {row[5]:.1f}m to {row[6]:.1f}m")
        else:
            con.close()
            return f"No data found for well matching '{well}'"
    except Exception as e:
        con.close()
        return f"Error querying well overview: {e}"

    # Hole sizes
    try:
        holes = con.execute("""
            SELECT DISTINCT hole_diameter_in, MIN(date) as from_date,
                   MAX(date) as to_date, MIN(md_m) as min_md, MAX(md_m) as max_md
            FROM ddr_status
            WHERE well LIKE ? AND hole_diameter_in IS NOT NULL
            GROUP BY hole_diameter_in
            ORDER BY min_md
        """, [like_pattern]).fetchall()
        if holes:
            lines.append("\nHole Sections:")
            for h in holes:
                lines.append(
                    f"  {h[0]}\" hole: {h[1]} to {h[2]}, "
                    f"depth {h[3]:.0f}m - {h[4]:.0f}m"
                )
    except Exception:
        pass

    # Wellbore info
    try:
        wb = con.execute("""
            SELECT DISTINCT name_well, name_wellbore, spud_date,
                   drill_complete_date, operator, drill_contractor, rig_name
            FROM wellbore_info
            WHERE well LIKE ?
            LIMIT 1
        """, [like_pattern]).fetchone()
        if wb:
            lines.append(f"\nWell: {wb[0]}")
            lines.append(f"Wellbore: {wb[1]}")
            if wb[2]:
                lines.append(f"Spud Date: {wb[2]}")
            if wb[3]:
                lines.append(f"Drill Complete: {wb[3]}")
            lines.append(f"Operator: {wb[4]}")
            lines.append(f"Contractor: {wb[5]}")
            if wb[6]:
                lines.append(f"Rig: {wb[6]}")
    except Exception:
        pass

    # Activity code distribution
    try:
        acts = con.execute("""
            SELECT activity_code, COUNT(*) as cnt,
                   SUM(CASE WHEN state = 'problem' THEN 1 ELSE 0 END) as problems
            FROM ddr_activities
            WHERE well LIKE ? AND activity_code != ''
            GROUP BY activity_code
            ORDER BY cnt DESC
        """, [like_pattern]).fetchall()
        if acts:
            lines.append("\nActivity Distribution:")
            total_acts = sum(a[1] for a in acts)
            for a in acts:
                pct = a[1] / total_acts * 100
                prob_str = f" ({a[2]} problems)" if a[2] > 0 else ""
                lines.append(f"  {a[0]}: {a[1]} ({pct:.1f}%){prob_str}")
    except Exception:
        pass

    # Formation tops if available
    try:
        tops = con.execute("""
            SELECT surface_name, md_m, tvd_m
            FROM formation_tops
            WHERE well LIKE ?
            ORDER BY md_m
        """, [like_pattern]).fetchall()
        if tops:
            lines.append("\nFormation Tops:")
            for t in tops:
                tvd_str = f", TVD: {t[2]:.1f}m" if t[2] else ""
                lines.append(f"  {t[0]}: MD {t[1]:.1f}m{tvd_str}")
    except Exception:
        pass

    con.close()
    return "\n".join(lines)
