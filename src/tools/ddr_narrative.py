"""Tool: Retrieve DDR narrative text for specific date/depth ranges.

Unlike semantic search, this tool uses SQL queries to ALWAYS return DDR text
for a given well and date range — guaranteed citation source.
"""

import logging
from typing import Optional

import duckdb

from src.config import DB_PATH, display_well_name

logger = logging.getLogger(__name__)


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def get_ddr_narrative(
    well: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    depth_from: Optional[float] = None,
    depth_to: Optional[float] = None,
) -> str:
    """Retrieve DDR daily summaries and key activity comments for a date/depth range.

    This tool returns ACTUAL TEXT from daily drilling reports — use it to get
    direct quotes for evidence. Unlike semantic search, this always returns
    results if the well has DDR data in the specified range.

    Args:
        well: Well name (underscore format, e.g. '15_9_F_11_T2')
        date_from: Start date (YYYY-MM-DD). If omitted, returns earliest data.
        date_to: End date (YYYY-MM-DD). If omitted, returns latest data.
        depth_from: Minimum depth in meters (filters activities by depth)
        depth_to: Maximum depth in meters (filters activities by depth)

    Returns:
        DDR narrative text with 24hr summaries, forecasts, and activity details
    """
    con = _get_con()
    like = well.replace("*", "%")

    lines = [f"=== DDR Narrative for {display_well_name(well)} ===\n"]

    # Build date filter
    def _df(q, p):
        if date_from:
            q += " AND date >= ?"
            p.append(date_from)
        if date_to:
            q += " AND date <= ?"
            p.append(date_to)
        return q, p

    # 1. Get 24hr summaries and forecasts
    sq = """SELECT date, md_m, hole_diameter_in, summary_24hr, forecast_24hr
            FROM ddr_status WHERE well LIKE ? AND summary_24hr IS NOT NULL"""
    sp = [like]
    sq, sp = _df(sq, sp)
    if depth_from is not None:
        sq += " AND md_m >= ?"
        sp.append(depth_from)
    if depth_to is not None:
        sq += " AND md_m <= ?"
        sp.append(depth_to)
    sq += " ORDER BY date"
    summaries = con.execute(sq, sp).fetchall()

    # 2. Get key activity comments (with state_detail for richer context)
    aq = """SELECT date, depth_m, activity_code, state, state_detail, comments
            FROM ddr_activities
            WHERE well LIKE ? AND comments IS NOT NULL AND comments != ''"""
    ap = [like]
    aq, ap = _df(aq, ap)
    if depth_from is not None:
        aq += " AND depth_m >= ?"
        ap.append(depth_from)
    if depth_to is not None:
        aq += " AND depth_m <= ?"
        ap.append(depth_to)
    aq += " ORDER BY date, start_time"
    activities = con.execute(aq, ap).fetchall()

    # 3. Get WITSML operational messages if available
    mq = """SELECT timestamp, md_m, message_text
            FROM witsml_messages WHERE well LIKE ?"""
    mp = [like]
    if date_from:
        mq += " AND timestamp >= ?"
        mp.append(date_from)
    if date_to:
        mq += " AND timestamp <= ?"
        mp.append(date_to + "T99")
    if depth_from is not None:
        mq += " AND md_m >= ?"
        mp.append(depth_from)
    if depth_to is not None:
        mq += " AND md_m <= ?"
        mp.append(depth_to)
    mq += " ORDER BY timestamp LIMIT 20"
    messages = con.execute(mq, mp).fetchall()

    con.close()

    if not summaries and not activities:
        return f"No DDR narrative found for well '{well}' in the specified range."

    # Format output
    date_range = ""
    if date_from or date_to:
        date_range = f" ({date_from or '?'} to {date_to or '?'})"
    depth_range = ""
    if depth_from is not None or depth_to is not None:
        depth_range = f" | Depth: {depth_from or '?'}m - {depth_to or '?'}m"
    lines.append(f"Range: {date_range}{depth_range}")
    lines.append(f"DDR Reports: {len(summaries)} | Activities: {len(activities)}\n")

    # Daily summaries — the richest narrative source
    lines.append("DAILY SUMMARIES:")
    for s in summaries[:15]:
        date, md, hole, summary, forecast = s
        depth_str = f"{md:.0f}m" if md else "?"
        hole_str = f" ({hole}\" hole)" if hole else ""
        lines.append(f"\n  DDR {display_well_name(well)}, {date} @ {depth_str}{hole_str}:")
        lines.append(f"    Summary: \"{summary}\"")
        if forecast:
            lines.append(f"    Forecast: \"{forecast}\"")

    # Key activities with state classification
    if activities:
        lines.append("\n\nKEY ACTIVITIES:")
        # Prioritize activities with problems, unique events, drilling
        shown = 0
        for a in activities:
            if shown >= 15:
                break
            date, depth, code, state, detail, comment = a
            if len(comment) < 20:
                continue
            depth_str = f"{depth:.0f}m" if depth else "?"
            state_str = f" [{state}]" if state == "problem" else ""
            detail_str = f" ({detail})" if detail and detail not in ("success", "") else ""
            lines.append(
                f"  {date} @ {depth_str} [{code}]{state_str}{detail_str}: "
                f"\"{comment[:200]}\""
            )
            shown += 1

    # WITSML messages
    if messages:
        lines.append("\n\nOPERATIONAL MESSAGES (WITSML):")
        for m in messages[:10]:
            ts = m[0][:10] if m[0] else "?"
            depth_str = f"{m[1]:.0f}m" if m[1] else "?"
            lines.append(f"  {ts} @ {depth_str}: \"{m[2]}\"")

    return "\n".join(lines)
