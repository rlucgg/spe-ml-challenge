"""Tool: Compute drilling efficiency metrics (NPT, ROP, productive time)."""

import logging
from typing import Optional

import duckdb

from src.config import DB_PATH, display_well_name

logger = logging.getLogger(__name__)

# Activity codes classified as Non-Productive Time
NPT_CODES = {
    "interruption -- repair": "Equipment Repair",
    "interruption -- waiting on weather": "Weather",
    "interruption -- waiting": "Waiting",
    "interruption -- other": "Other NPT",
    "interruption -- wait": "Waiting",
    "interruption -- maintain": "Maintenance",
    "well_control -- kick": "Well Control",
    "well_control -- kill": "Well Control",
    "well_control -- shut-in": "Well Control",
}

# Sub-classify "interruption -- other" using comment keywords
_NPT_COMMENT_RULES = [
    (["cement", "waiting on cement", "woc"], "Waiting on Cement"),
    (["mwd", "lwd", "tool", "sensor", "probe", "signal"], "MWD/Tool Issue"),
    (["survey", "gyro"], "Survey Operations"),
    (["rig up", "rig down", "rigged", "r/u", "r/d", "nipple"], "Rig Up/Down"),
    (["circul", "displace", "sweep", "condition"], "Circulating/Conditioning"),
    (["crew", "safety", "meeting", "drill", "hse"], "Crew/Safety/Meeting"),
    (["slip", "cut", "drill line"], "Slip & Cut Drill Line"),
    (["test", "pressure test", "fit", "lot", "leak"], "Pressure Testing"),
]


def _sub_classify_npt(comments: str) -> str:
    """Sub-classify 'Other NPT' using keywords in the activity comments."""
    cl = comments.lower()
    for keywords, label in _NPT_COMMENT_RULES:
        if any(kw in cl for kw in keywords):
            return label
    return "Other NPT (unclassified)"

PRODUCTIVE_CODES = {
    "drilling -- drill": "Drilling",
    "drilling -- ream": "Reaming",
    "drilling -- coring": "Coring",
    "cementing -- cement": "Cementing",
    "cementing -- casing": "Casing",
    "completion -- completion": "Completion",
    "logging -- log": "Logging",
}


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def compute_efficiency_metrics(
    well: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> str:
    """Compute drilling efficiency metrics for a well.

    Calculates: productive vs non-productive time, NPT breakdown by cause,
    ROP by hole section, drilling efficiency ratio, and daily depth progress.

    Args:
        well: Well name (underscore format)
        date_from: Optional start date (YYYY-MM-DD)
        date_to: Optional end date (YYYY-MM-DD)

    Returns:
        Formatted efficiency analysis text
    """
    con = _get_con()
    like_pattern = well.replace("*", "%")

    # Get activities with duration
    query = """
        SELECT date, start_time, end_time, depth_m, activity_code,
               state, state_detail, comments
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

    # Get depth progression by date
    depth_query = """
        SELECT date, md_m, hole_diameter_in, dist_drill_m
        FROM ddr_status
        WHERE well LIKE ?
    """
    d_params = [like_pattern]
    if date_from:
        depth_query += " AND date >= ?"
        d_params.append(date_from)
    if date_to:
        depth_query += " AND date <= ?"
        d_params.append(date_to)
    depth_query += " ORDER BY date"

    depths = con.execute(depth_query, d_params).fetchall()
    con.close()

    if not activities:
        return f"No activity data found for well '{well}'"

    lines = [f"=== Efficiency Metrics for {display_well_name(well)} ===\n"]

    # Classify activities and compute time
    productive_hrs = 0.0
    npt_hrs = 0.0
    trip_hrs = 0.0
    other_hrs = 0.0
    npt_breakdown = {}
    productive_breakdown = {}
    problem_count = 0
    longest_npt_event = {"cause": "", "hrs": 0.0, "date": "", "comment": ""}

    for act in activities:
        code = (act[4] or "").lower().strip()
        state = act[5] or ""

        # Estimate duration from timestamps
        try:
            from datetime import datetime
            start = datetime.fromisoformat(act[1]) if act[1] else None
            end = datetime.fromisoformat(act[2]) if act[2] else None
            if start and end:
                duration_hrs = (end - start).total_seconds() / 3600
            else:
                duration_hrs = 0
        except (ValueError, TypeError):
            duration_hrs = 0

        if state == "problem":
            problem_count += 1

        if code in NPT_CODES:
            npt_hrs += duration_hrs
            cause = NPT_CODES[code]
            # Sub-classify generic "Other NPT" using comment text
            if cause == "Other NPT":
                comments = act[7] or ""
                cause = _sub_classify_npt(comments)
            npt_breakdown[cause] = npt_breakdown.get(cause, 0) + duration_hrs
            if duration_hrs > longest_npt_event["hrs"]:
                longest_npt_event = {
                    "cause": cause, "hrs": duration_hrs,
                    "date": act[0], "comment": (act[7] or "")[:120],
                }
        elif code in PRODUCTIVE_CODES:
            productive_hrs += duration_hrs
            kind = PRODUCTIVE_CODES[code]
            productive_breakdown[kind] = productive_breakdown.get(kind, 0) + duration_hrs
        elif "trip" in code:
            trip_hrs += duration_hrs
        else:
            other_hrs += duration_hrs

    total_hrs = productive_hrs + npt_hrs + trip_hrs + other_hrs

    # Time breakdown
    lines.append("Time Breakdown:")
    if total_hrs > 0:
        lines.append(f"  Total Time: {total_hrs:.1f} hrs ({total_hrs / 24:.1f} days)")
        lines.append(
            f"  Productive Time: {productive_hrs:.1f} hrs "
            f"({productive_hrs / total_hrs * 100:.1f}%)"
        )
        lines.append(
            f"  Non-Productive Time (NPT): {npt_hrs:.1f} hrs "
            f"({npt_hrs / total_hrs * 100:.1f}%)"
        )
        lines.append(
            f"  Tripping Time: {trip_hrs:.1f} hrs "
            f"({trip_hrs / total_hrs * 100:.1f}%)"
        )
        lines.append(
            f"  Other: {other_hrs:.1f} hrs "
            f"({other_hrs / total_hrs * 100:.1f}%)"
        )
    lines.append(f"  Activities with problems: {problem_count}")

    # NPT breakdown
    if npt_breakdown:
        lines.append("\nNPT Breakdown:")
        for cause, hrs in sorted(npt_breakdown.items(), key=lambda x: -x[1]):
            lines.append(f"  {cause}: {hrs:.1f} hrs")
        if longest_npt_event["hrs"] > 0:
            lines.append(f"\n  Longest single NPT event: {longest_npt_event['hrs']:.1f} hrs"
                         f" ({longest_npt_event['cause']}) on {longest_npt_event['date']}")
            if longest_npt_event["comment"]:
                lines.append(f"    \"{longest_npt_event['comment']}\"")

    # Productive time breakdown
    if productive_breakdown:
        lines.append("\nProductive Time Breakdown:")
        for kind, hrs in sorted(productive_breakdown.items(), key=lambda x: -x[1]):
            lines.append(f"  {kind}: {hrs:.1f} hrs")

    # ROP by hole section
    if depths:
        lines.append("\nDepth Progress by Section:")
        by_hole = {}
        prev_depth = None
        prev_date = None
        for d in depths:
            hole = d[2]
            md = d[1]
            dist = d[3]
            if hole and md:
                if hole not in by_hole:
                    by_hole[hole] = {"depths": [], "dates": [], "dist_drilled": 0}
                by_hole[hole]["depths"].append(md)
                by_hole[hole]["dates"].append(d[0])
                if dist:
                    by_hole[hole]["dist_drilled"] += dist

        for hole, info in sorted(by_hole.items(),
                                  key=lambda x: min(x[1]["depths"])):
            min_d = min(info["depths"])
            max_d = max(info["depths"])
            n_days = len(info["dates"])
            drilled = info["dist_drilled"] or (max_d - min_d)
            avg_rop = drilled / n_days if n_days > 0 else 0
            lines.append(
                f"  {hole}\" hole: {min_d:.0f}m → {max_d:.0f}m "
                f"({drilled:.0f}m in {n_days} days, avg {avg_rop:.1f} m/day)"
            )

    # Daily ROP
    if len(depths) > 1:
        daily_progress = []
        for i in range(1, len(depths)):
            if depths[i][1] and depths[i - 1][1]:
                progress = depths[i][1] - depths[i - 1][1]
                if progress > 0:
                    daily_progress.append(progress)

        if daily_progress:
            lines.append("\nDaily Depth Progress Statistics (m/day):")
            daily_progress.sort()
            lines.append(f"  Min: {min(daily_progress):.1f}")
            lines.append(f"  Max: {max(daily_progress):.1f}")
            avg = sum(daily_progress) / len(daily_progress)
            lines.append(f"  Mean: {avg:.1f}")
            mid = len(daily_progress) // 2
            median = daily_progress[mid]
            lines.append(f"  Median: {median:.1f}")

    return "\n".join(lines)
