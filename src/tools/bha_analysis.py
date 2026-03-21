"""Tool: Analyze BHA (Bottom Hole Assembly) configurations from DDR data."""

import logging
import re
from typing import Optional

import duckdb

from src.config import DB_PATH, display_well_name

logger = logging.getLogger(__name__)


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def get_bha_configurations(well: str) -> str:
    """Analyze BHA configurations and their performance for a well.

    Extracts BHA-related information from DDR activity comments,
    identifies runs, and correlates with drilling performance.

    Args:
        well: Well name (underscore format)

    Returns:
        BHA configuration analysis with performance metrics
    """
    con = _get_con()
    like_pattern = well.replace("*", "%")

    # Get drilling activities with comments mentioning BHA, bit, or tool changes
    activities = con.execute("""
        SELECT date, start_time, end_time, depth_m, activity_code,
               state, comments
        FROM ddr_activities
        WHERE well LIKE ?
          AND activity_code != ''
        ORDER BY date, start_time
    """, [like_pattern]).fetchall()

    # Get depth progression for ROP calculation
    depths = con.execute("""
        SELECT date, md_m, hole_diameter_in, dist_drill_m
        FROM ddr_status
        WHERE well LIKE ?
        ORDER BY date
    """, [like_pattern]).fetchall()

    con.close()

    if not activities:
        return f"No activity data found for well '{well}'"

    lines = [f"=== BHA Configuration Analysis for {display_well_name(well)} ===\n"]

    # Extract BHA-related events from comments
    bha_events = []
    drilling_runs = []
    current_run_start = None
    current_run_start_depth = None
    current_hole = None

    for act in activities:
        code = (act[4] or "").lower()
        comments = act[6] or ""
        comments_lower = comments.lower()

        # Detect BHA/bit changes
        is_bha_event = any(kw in comments_lower for kw in [
            "pick up", "p/u", "ran in hole", "r.i.h", "rih",
            "bha", "bit", "new assembly", "changed bit",
            "tripped out", "t.o.o.h", "pooh", "pulled out",
            "new bha", "make up bha", "m/u bha",
        ])

        if is_bha_event and ("trip" in code or "equipment" in code or "drill" in code):
            bha_events.append({
                "date": act[0],
                "depth_m": act[3],
                "code": act[4],
                "comments": comments[:200],
            })

        # Track drilling runs (continuous drilling sequences)
        if "drill" in code and "drill" in code:
            if current_run_start is None:
                current_run_start = act[0]
                current_run_start_depth = act[3]
        else:
            if current_run_start is not None and current_run_start_depth:
                drilling_runs.append({
                    "start_date": current_run_start,
                    "end_date": act[0],
                    "start_depth": current_run_start_depth,
                    "end_depth": act[3] or current_run_start_depth,
                })
                current_run_start = None
                current_run_start_depth = None

    if current_run_start and current_run_start_depth:
        last_act = activities[-1]
        drilling_runs.append({
            "start_date": current_run_start,
            "end_date": last_act[0],
            "start_depth": current_run_start_depth,
            "end_depth": last_act[3] or current_run_start_depth,
        })

    # BHA Events Timeline
    if bha_events:
        lines.append("BHA/Bit Change Events:")
        for ev in bha_events:
            depth = f"{ev['depth_m']:.0f}m" if ev['depth_m'] else "N/A"
            lines.append(f"  {ev['date']} @ {depth}: {ev['comments']}")
        lines.append("")

    # Drilling Runs Analysis
    if drilling_runs:
        lines.append(f"Drilling Runs Identified: {len(drilling_runs)}")
        lines.append("")
        for i, run in enumerate(drilling_runs):
            drilled = (run["end_depth"] or 0) - (run["start_depth"] or 0)
            lines.append(
                f"  Run {i + 1}: {run['start_date']} to {run['end_date']}"
                f" | {run['start_depth']:.0f}m → {run['end_depth']:.0f}m"
                f" | Drilled: {drilled:.0f}m"
            )

    # Drilling parameters extracted from comments
    rop_values = []
    wob_values = []
    rpm_values = []

    for act in activities:
        comments = act[6] or ""
        code = (act[4] or "").lower()
        if "drill" not in code:
            continue

        # Extract ROP from comments
        rop_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:m/hr|m/h|meter/hour|metres/hour)", comments, re.I)
        if rop_match:
            rop_values.append(float(rop_match.group(1)))

        # Extract WOB
        wob_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:tons?\s*WOB|MT\s*WOB|WOB)", comments, re.I)
        if not wob_match:
            wob_match = re.search(r"WOB\s*(\d+(?:\.\d+)?)", comments, re.I)
        if wob_match:
            wob_values.append(float(wob_match.group(1)))

        # Extract RPM
        rpm_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:rpm|RPM)", comments, re.I)
        if rpm_match:
            rpm_values.append(float(rpm_match.group(1)))

    if rop_values or wob_values or rpm_values:
        lines.append("\nDrilling Parameters (from DDR comments):")
        if rop_values:
            lines.append(
                f"  ROP: min={min(rop_values):.1f}, max={max(rop_values):.1f}, "
                f"avg={sum(rop_values)/len(rop_values):.1f} m/hr "
                f"({len(rop_values)} readings)"
            )
        if wob_values:
            lines.append(
                f"  WOB: min={min(wob_values):.1f}, max={max(wob_values):.1f}, "
                f"avg={sum(wob_values)/len(wob_values):.1f} tons "
                f"({len(wob_values)} readings)"
            )
        if rpm_values:
            lines.append(
                f"  RPM: min={min(rpm_values):.1f}, max={max(rpm_values):.1f}, "
                f"avg={sum(rpm_values)/len(rpm_values):.1f} "
                f"({len(rpm_values)} readings)"
            )

    # Per-hole-section performance
    if depths:
        lines.append("\nPerformance by Hole Section:")
        by_hole = {}
        for d in depths:
            h = d[2]
            if h:
                if h not in by_hole:
                    by_hole[h] = {"dists": [], "dates": []}
                if d[3] and d[3] > 0:
                    by_hole[h]["dists"].append(d[3])
                by_hole[h]["dates"].append(d[0])

        for hole, info in sorted(by_hole.items(), key=lambda x: x[0], reverse=True):
            n_days = len(info["dates"])
            total_drilled = sum(info["dists"])
            avg = total_drilled / n_days if n_days else 0
            lines.append(
                f"  {hole}\" hole: {n_days} days, "
                f"{total_drilled:.0f}m drilled, avg {avg:.1f} m/day"
            )

    return "\n".join(lines)
