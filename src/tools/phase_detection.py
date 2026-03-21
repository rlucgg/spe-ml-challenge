"""Tool: Detect and label drilling phases from DDR activity codes."""

import logging
from datetime import datetime, timedelta
from typing import Optional

import duckdb

from src.config import DB_PATH, display_well_name

logger = logging.getLogger(__name__)

# Phase classification rules based on DDR proprietaryCode values
PHASE_MAP = {
    "drilling -- drill": "Drilling",
    "drilling -- trip": "Tripping",
    "drilling -- ream": "Reaming",
    "drilling -- coring": "Coring",
    "cementing -- cement": "Cementing",
    "cementing -- casing": "Casing",
    "cementing -- liner": "Casing",
    "completion -- completion": "Completion",
    "completion -- gravel pack": "Completion",
    "completion -- perforate": "Completion",
    "completion -- stimulate": "Completion",
    "logging -- log": "Logging",
    "logging -- wireline": "Logging",
    "well_control -- kick": "Well Control",
    "well_control -- kill": "Well Control",
    "well_control -- shut-in": "Well Control",
    "equipment -- rig": "Equipment",
    "equipment -- bha": "Equipment",
    "equipment -- mud": "Mud Work",
    "interruption -- repair": "NPT - Repair",
    "interruption -- waiting on weather": "NPT - Weather",
    "interruption -- other": "Other",
    "interruption -- waiting": "NPT - Waiting",
    "testing -- test": "Testing",
    "testing -- dst": "Testing",
    "conditioning -- circulate": "Circulating",
    "conditioning -- displace": "Circulating",
}


def _classify_activity(code: str) -> str:
    """Classify an activity code into a drilling phase."""
    code_lower = code.lower().strip()
    if code_lower in PHASE_MAP:
        return PHASE_MAP[code_lower]
    # Fuzzy match on prefix
    for key, phase in PHASE_MAP.items():
        if code_lower.startswith(key.split(" -- ")[0]):
            return phase
    return "Other"


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def get_drilling_phases(
    well: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> str:
    """Identify and label major drilling phases for a well.

    Analyzes DDR activity codes, depth progression, and hole size changes
    to identify drilling phases. Returns chronological phase breakdown
    with evidence.

    Args:
        well: Well name (underscore format, e.g. '15_9_F_11_T2')
        date_from: Optional start date filter (YYYY-MM-DD)
        date_to: Optional end date filter (YYYY-MM-DD)

    Returns:
        Detailed phase breakdown with dates, depths, and evidence
    """
    con = _get_con()
    like_pattern = well.replace("*", "%")

    # Get activities with timestamps
    query = """
        SELECT date, start_time, end_time, depth_m, activity_code, state,
               state_detail, comments
        FROM ddr_activities
        WHERE well LIKE ?
    """
    params = [like_pattern]
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)
    query += " ORDER BY date, start_time"

    activities = con.execute(query, params).fetchall()

    # Get depth progression from status
    status_query = """
        SELECT date, md_m, tvd_m, hole_diameter_in, summary_24hr
        FROM ddr_status
        WHERE well LIKE ?
    """
    s_params = [like_pattern]
    if date_from:
        status_query += " AND date >= ?"
        s_params.append(date_from)
    if date_to:
        status_query += " AND date <= ?"
        s_params.append(date_to)
    status_query += " ORDER BY date"

    statuses = con.execute(status_query, s_params).fetchall()
    con.close()

    if not activities and not statuses:
        return f"No data found for well '{well}'"

    # Classify each activity
    classified = []
    for act in activities:
        phase = _classify_activity(act[4]) if act[4] else "Unknown"
        classified.append({
            "date": act[0],
            "start": act[1],
            "end": act[2],
            "depth_m": act[3],
            "code": act[4],
            "state": act[5],
            "detail": act[6],
            "comments": act[7],
            "phase": phase,
        })

    # Detect major phase transitions (group consecutive same-phase activities)
    phases = []
    current_phase = None
    phase_start_date = None
    phase_start_depth = None
    phase_activities = []

    for act in classified:
        if act["phase"] != current_phase:
            if current_phase and phase_activities:
                phases.append({
                    "phase": current_phase,
                    "start_date": phase_start_date,
                    "end_date": phase_activities[-1]["date"],
                    "start_depth": phase_start_depth,
                    "end_depth": phase_activities[-1].get("depth_m"),
                    "activity_count": len(phase_activities),
                    "problems": sum(1 for a in phase_activities if a["state"] == "problem"),
                    "sample_comments": [
                        a["comments"] for a in phase_activities[:2] if a["comments"]
                    ],
                })
            current_phase = act["phase"]
            phase_start_date = act["date"]
            phase_start_depth = act.get("depth_m")
            phase_activities = [act]
        else:
            phase_activities.append(act)

    # Don't forget the last phase
    if current_phase and phase_activities:
        phases.append({
            "phase": current_phase,
            "start_date": phase_start_date,
            "end_date": phase_activities[-1]["date"],
            "start_depth": phase_start_depth,
            "end_depth": phase_activities[-1].get("depth_m"),
            "activity_count": len(phase_activities),
            "problems": sum(1 for a in phase_activities if a["state"] == "problem"),
            "sample_comments": [
                a["comments"] for a in phase_activities[:2] if a["comments"]
            ],
        })

    # Merge short phases into major phase blocks by hole section
    hole_sections = []
    for s in statuses:
        if s[3]:  # hole_diameter_in
            hole_sections.append({
                "date": s[0], "md_m": s[1], "tvd_m": s[2],
                "hole_in": s[3], "summary": s[4],
            })

    # Build output
    lines = [f"=== Drilling Phases for {display_well_name(well)} ===\n"]

    if statuses:
        lines.append(f"Date Range: {statuses[0][0]} to {statuses[-1][0]}")
        depths = [s[1] for s in statuses if s[1]]
        if depths:
            lines.append(f"Depth Range: {min(depths):.1f}m to {max(depths):.1f}m MD")

    # Hole section summary
    if hole_sections:
        seen_holes = {}
        for hs in hole_sections:
            h = hs["hole_in"]
            if h not in seen_holes:
                seen_holes[h] = {"first_date": hs["date"], "last_date": hs["date"],
                                 "min_md": hs["md_m"], "max_md": hs["md_m"]}
            else:
                seen_holes[h]["last_date"] = hs["date"]
                if hs["md_m"] and hs["md_m"] > seen_holes[h]["max_md"]:
                    seen_holes[h]["max_md"] = hs["md_m"]

        lines.append("\nHole Sections Drilled:")
        for h, info in sorted(seen_holes.items(), key=lambda x: x[1].get("min_md", 0)):
            lines.append(
                f"  {h}\" hole: {info['first_date']} to {info['last_date']}, "
                f"{info['min_md']:.0f}m - {info['max_md']:.0f}m MD"
            )

    # Phase summary
    phase_counts = {}
    for p in phases:
        name = p["phase"]
        if name not in phase_counts:
            phase_counts[name] = {"count": 0, "problems": 0}
        phase_counts[name]["count"] += p["activity_count"]
        phase_counts[name]["problems"] += p["problems"]

    lines.append("\nPhase Distribution (by activity count):")
    total = sum(v["count"] for v in phase_counts.values())
    for name, v in sorted(phase_counts.items(), key=lambda x: -x[1]["count"]):
        pct = v["count"] / total * 100 if total else 0
        prob = f" [{v['problems']} problems]" if v["problems"] else ""
        lines.append(f"  {name}: {v['count']} activities ({pct:.1f}%){prob}")

    # Chronological phase timeline
    lines.append("\nChronological Phase Timeline:")
    for i, p in enumerate(phases):
        depth_str = ""
        if p["start_depth"] and p["end_depth"]:
            depth_str = f" | Depth: {p['start_depth']:.0f}m → {p['end_depth']:.0f}m"
        elif p["start_depth"]:
            depth_str = f" | Depth: {p['start_depth']:.0f}m"

        prob_str = f" [!{p['problems']} problems]" if p["problems"] else ""
        lines.append(
            f"  {i + 1}. {p['phase']}: {p['start_date']} to {p['end_date']}"
            f"{depth_str} ({p['activity_count']} activities){prob_str}"
        )
        for comment in p["sample_comments"][:1]:
            short = comment[:150] + "..." if len(comment) > 150 else comment
            lines.append(f"     Evidence: \"{short}\"")

    return "\n".join(lines)
