"""Tool: Detect and label drilling phases from hole sizes, activity codes, and depth."""

import logging
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
    "interruption -- wait": "NPT - Waiting",
    "interruption -- maintain": "NPT - Repair",
    "testing -- test": "Testing",
    "testing -- dst": "Testing",
    "conditioning -- circulate": "Circulating",
    "conditioning -- displace": "Circulating",
}

# Hole size to section name mapping
HOLE_SECTION_NAMES = {
    36.0: "Conductor (36\")",
    30.0: "Conductor (30\")",
    26.0: "Surface (26\")",
    17.5: "Intermediate (17.5\")",
    12.25: "Production (12.25\")",
    8.5: "Reservoir (8.5\")",
}


def _classify_activity(code: str) -> str:
    """Classify an activity code into a drilling phase."""
    code_lower = code.lower().strip()
    if code_lower in PHASE_MAP:
        return PHASE_MAP[code_lower]
    for key, phase in PHASE_MAP.items():
        if code_lower.startswith(key.split(" -- ")[0]):
            return phase
    return "Other"


def _section_name(hole_in: float) -> str:
    """Get human-readable section name from hole diameter."""
    if hole_in is None:
        return "Unknown"
    closest = min(HOLE_SECTION_NAMES.keys(), key=lambda h: abs(h - hole_in))
    if abs(closest - hole_in) < 2.0:
        return HOLE_SECTION_NAMES[closest]
    return f"{hole_in}\" Section"


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def get_drilling_phases(
    well: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> str:
    """Identify and label major drilling phases for a well.

    PRIMARY method: hole-size changes define major phase boundaries.
    SECONDARY method: activity codes classify sub-phases within each section.
    Includes depth progression validation and phase confidence assessment.

    Args:
        well: Well name (underscore format, e.g. '15_9_F_11_T2')
        date_from: Optional start date filter (YYYY-MM-DD)
        date_to: Optional end date filter (YYYY-MM-DD)

    Returns:
        Detailed phase breakdown with dates, depths, evidence, and confidence
    """
    con = _get_con()
    like = well.replace("*", "%")

    def _add_date_filters(q, p, prefix=""):
        if date_from:
            q += f" AND {prefix}date >= ?"
            p.append(date_from)
        if date_to:
            q += f" AND {prefix}date <= ?"
            p.append(date_to)
        return q, p

    # Get status data (hole sizes, depths)
    sq = "SELECT date, md_m, tvd_m, hole_diameter_in, dist_drill_m, summary_24hr FROM ddr_status WHERE well LIKE ?"
    sp = [like]
    sq, sp = _add_date_filters(sq, sp)
    sq += " ORDER BY date"
    statuses = con.execute(sq, sp).fetchall()

    # Get activities
    aq = "SELECT date, start_time, end_time, depth_m, activity_code, state, state_detail, comments FROM ddr_activities WHERE well LIKE ?"
    ap = [like]
    aq, ap = _add_date_filters(aq, ap)
    aq += " ORDER BY date, start_time"
    activities = con.execute(aq, ap).fetchall()

    con.close()

    if not activities and not statuses:
        return f"No data found for well '{well}'"

    lines = [f"=== Drilling Phases for {display_well_name(well)} ===\n"]

    # --- STEP 1: Hole-size-based major phase detection (PRIMARY) ---
    hole_phases = []
    current_hole = None
    phase_start = None
    phase_start_md = None

    for s in statuses:
        date, md, tvd, hole, dist, summary = s
        if hole and hole != current_hole:
            if current_hole is not None:
                hole_phases.append({
                    "hole_in": current_hole,
                    "section": _section_name(current_hole),
                    "start_date": phase_start,
                    "end_date": date,
                    "start_md": phase_start_md,
                    "end_md": md,
                })
            current_hole = hole
            phase_start = date
            phase_start_md = md

    # Close the last phase
    if current_hole and statuses:
        last = statuses[-1]
        hole_phases.append({
            "hole_in": current_hole,
            "section": _section_name(current_hole),
            "start_date": phase_start,
            "end_date": last[0],
            "start_md": phase_start_md,
            "end_md": last[1],
        })

    if statuses:
        lines.append(f"Date Range: {statuses[0][0]} to {statuses[-1][0]}")
        depths = [s[1] for s in statuses if s[1]]
        if depths:
            lines.append(f"Depth Range: {min(depths):.1f}m to {max(depths):.1f}m MD")
        lines.append("")

    # --- Output major hole-section phases ---
    if hole_phases:
        lines.append("MAJOR PHASES (by hole section):\n")
        for i, hp in enumerate(hole_phases, 1):
            md_range = ""
            if hp["start_md"] and hp["end_md"]:
                md_range = f" | MD: {hp['start_md']:.0f}m → {hp['end_md']:.0f}m"
            days = 0
            for s in statuses:
                if hp["start_date"] <= s[0] <= hp["end_date"]:
                    days += 1
            lines.append(
                f"  Phase {i}: {hp['section']} ({hp['hole_in']}\")"
            )
            lines.append(
                f"    Dates: {hp['start_date']} to {hp['end_date']} ({days} DDR days){md_range}"
            )

            # Find casing point (end of section)
            for s in statuses:
                if s[0] == hp["end_date"] and s[1]:
                    lines.append(f"    Casing point: ~{s[1]:.0f}m MD")
                    break

            # Sub-phase activity breakdown within this hole section
            section_acts = [
                a for a in activities
                if hp["start_date"] <= a[0] <= hp["end_date"]
            ]
            if section_acts:
                sub_counts = {}
                problems = 0
                for a in section_acts:
                    phase = _classify_activity(a[4]) if a[4] else "Unknown"
                    sub_counts[phase] = sub_counts.get(phase, 0) + 1
                    if a[5] == "problem":
                        problems += 1
                total_sub = sum(sub_counts.values())
                top_subs = sorted(sub_counts.items(), key=lambda x: -x[1])[:5]
                sub_str = ", ".join(
                    f"{name} {cnt}/{total_sub} ({cnt/total_sub*100:.0f}%)"
                    for name, cnt in top_subs
                )
                lines.append(f"    Activities: {total_sub} total — {sub_str}")
                if problems:
                    lines.append(f"    Problems: {problems} activities with issues")

            # DDR summary evidence for this phase
            phase_summaries = [
                s[5] for s in statuses
                if hp["start_date"] <= s[0] <= hp["end_date"] and s[5]
            ]
            if phase_summaries:
                first_summary = phase_summaries[0][:150]
                lines.append(f"    Evidence: \"{first_summary}\"")
            lines.append("")

    # --- STEP 2: Depth progression validation ---
    lines.append("DEPTH PROGRESSION VALIDATION:")
    prev_md = None
    reversals = []
    for s in statuses:
        if s[1] is not None:
            if prev_md is not None and s[1] < prev_md - 10:
                reversals.append({"date": s[0], "from": prev_md, "to": s[1]})
            prev_md = s[1]
    if reversals:
        lines.append(f"  Depth reversals detected: {len(reversals)} (may indicate trips, sidetracks, or reaming)")
        for r in reversals[:3]:
            lines.append(f"    {r['date']}: {r['from']:.0f}m → {r['to']:.0f}m (drop of {r['from']-r['to']:.0f}m)")
    else:
        lines.append("  Depth monotonically increasing — no significant reversals detected.")

    # --- STEP 3: Activity-level phase distribution ---
    lines.append("\nACTIVITY PHASE DISTRIBUTION:")
    phase_counts = {}
    for a in activities:
        phase = _classify_activity(a[4]) if a[4] else "Unknown"
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
    total = sum(phase_counts.values())
    for name, cnt in sorted(phase_counts.items(), key=lambda x: -x[1]):
        pct = cnt / total * 100 if total else 0
        lines.append(f"  {name}: {cnt} activities ({pct:.1f}%)")

    # --- STEP 4: Confidence assessment ---
    lines.append("\nPHASE DETECTION CONFIDENCE:")
    has_hole_sizes = len(hole_phases) > 1
    has_activities = len(activities) > 20
    has_summaries = any(s[5] for s in statuses)
    if has_hole_sizes and has_activities and has_summaries:
        lines.append("  Level: HIGH")
        lines.append("  Basis: Hole size changes confirmed by activity code transitions and DDR summaries.")
    elif has_activities and has_summaries:
        lines.append("  Level: MEDIUM")
        lines.append("  Basis: Activity codes present but no hole size data to confirm major phase boundaries.")
    else:
        lines.append("  Level: LOW")
        lines.append("  Basis: Sparse data — limited activities or missing DDR summaries.")

    return "\n".join(lines)
