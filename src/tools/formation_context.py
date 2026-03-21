"""Tool: Get geological formation context for a well and depth."""

import logging
from typing import Optional

import duckdb

from src.config import DB_PATH, normalize_well_name

logger = logging.getLogger(__name__)


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def get_formation_context(well: str, depth_m: Optional[float] = None) -> str:
    """Get geological formation context for a well at a specific depth.

    Queries formation_tops table to identify what formation a depth falls in.
    If no formation data for this well, uses nearest wells' data as reference.

    Args:
        well: Well name (underscore format, e.g. '15_9_F_11_T2')
        depth_m: Measured depth in meters. If None, returns all formations for the well.

    Returns:
        Formation context including name, depth range, and surrounding formations
    """
    con = _get_con()
    like = well.replace("*", "%")

    # Get formation tops for this well
    tops = con.execute("""
        SELECT well, surface_name, md_m, tvd_m, tvdss_m
        FROM formation_tops
        WHERE well LIKE ?
        ORDER BY md_m
    """, [like]).fetchall()

    # If no data for this well, try parent well or nearby wells
    if not tops:
        # Try parent well (e.g., 15_9_F_11_T2 → 15_9_F_11)
        parts = well.split("_")
        if len(parts) > 4:
            parent = "_".join(parts[:4])
            tops = con.execute("""
                SELECT well, surface_name, md_m, tvd_m, tvdss_m
                FROM formation_tops
                WHERE well LIKE ?
                ORDER BY md_m
            """, [parent.replace("*", "%")]).fetchall()

    # If still no data, get all available wells with formation data
    if not tops:
        available = con.execute("""
            SELECT DISTINCT well FROM formation_tops ORDER BY well
        """).fetchall()
        con.close()
        well_list = ", ".join(w[0] for w in available[:10])
        return f"No formation top data for well '{well}'. Available wells with formation data: {well_list}"

    con.close()

    lines = [f"Formation tops for {tops[0][0]}:"]

    if depth_m is not None:
        # Find which formation the depth falls in
        current_fm = None
        above_fm = None
        below_fm = None

        for i, top in enumerate(tops):
            if top[2] is not None and top[2] <= depth_m:
                current_fm = top
            elif top[2] is not None and top[2] > depth_m and below_fm is None:
                below_fm = top

        if current_fm:
            above_idx = tops.index(current_fm)
            if above_idx > 0:
                above_fm = tops[above_idx - 1]

        lines.append(f"\nAt {depth_m:.0f}m MD:")
        if current_fm:
            tvd_str = f", TVD: {current_fm[3]:.0f}m" if current_fm[3] else ""
            lines.append(f"  Current formation: {current_fm[1]} (top at {current_fm[2]:.0f}m MD{tvd_str})")
        else:
            lines.append("  Current formation: Above shallowest formation top")
        if above_fm:
            lines.append(f"  Formation above: {above_fm[1]} (top at {above_fm[2]:.0f}m MD)")
        if below_fm:
            lines.append(f"  Formation below: {below_fm[1]} (top at {below_fm[2]:.0f}m MD)")
        lines.append("")

    # Full formation column
    lines.append("Complete formation column:")
    for top in tops:
        md_str = f"{top[2]:.0f}m MD" if top[2] else "?"
        tvd_str = f", {top[3]:.0f}m TVD" if top[3] else ""
        lines.append(f"  {top[1]}: {md_str}{tvd_str}")

    return "\n".join(lines)
