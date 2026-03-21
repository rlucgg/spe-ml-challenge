"""Tool: Identify operational issues and problems from DDR data."""

import logging
from typing import Optional

import duckdb

from src.config import DB_PATH, display_well_name

logger = logging.getLogger(__name__)


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def identify_operational_issues(
    well: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> str:
    """Identify key operational issues encountered during drilling.

    Analyzes DDR activities with state='problem' or NPT-related codes,
    extracts issue patterns, and proposes contributing factors.

    Args:
        well: Well name (underscore format)
        date_from: Optional start date (YYYY-MM-DD)
        date_to: Optional end date (YYYY-MM-DD)

    Returns:
        Issue analysis with timeline, categories, and contributing factors
    """
    con = _get_con()
    like_pattern = well.replace("*", "%")

    # Get all problem activities
    query = """
        SELECT date, start_time, end_time, depth_m, activity_code,
               state, state_detail, comments
        FROM ddr_activities
        WHERE well LIKE ?
          AND (state = 'problem'
               OR activity_code LIKE 'interruption%'
               OR activity_code LIKE 'well_control%'
               OR state_detail IN ('equipment failure', 'mud loss', 'operation failed'))
    """
    params = [like_pattern]
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)
    query += " ORDER BY date, start_time"

    issues = con.execute(query, params).fetchall()

    # Get total activity count for context
    total_query = """
        SELECT COUNT(*) FROM ddr_activities WHERE well LIKE ?
    """
    t_params = [like_pattern]
    if date_from:
        total_query += " AND date >= ?"
        t_params.append(date_from)
    if date_to:
        total_query += " AND date <= ?"
        t_params.append(date_to)
    total_count = con.execute(total_query, t_params).fetchone()[0]

    # Get 24hr summaries mentioning problems
    summary_query = """
        SELECT date, md_m, summary_24hr FROM ddr_status
        WHERE well LIKE ?
          AND (summary_24hr LIKE '%problem%' OR summary_24hr LIKE '%issue%'
               OR summary_24hr LIKE '%failure%' OR summary_24hr LIKE '%stuck%'
               OR summary_24hr LIKE '%loss%' OR summary_24hr LIKE '%kick%'
               OR summary_24hr LIKE '%repair%' OR summary_24hr LIKE '%wait%')
    """
    s_params = [like_pattern]
    if date_from:
        summary_query += " AND date >= ?"
        s_params.append(date_from)
    if date_to:
        summary_query += " AND date <= ?"
        s_params.append(date_to)
    summary_query += " ORDER BY date"

    problem_summaries = con.execute(summary_query, s_params).fetchall()
    con.close()

    lines = [f"=== Operational Issues for {display_well_name(well)} ===\n"]
    lines.append(
        f"Total Activities: {total_count} | "
        f"Problem/NPT Activities: {len(issues)} "
        f"({len(issues) / total_count * 100:.1f}% of total)\n"
        if total_count else ""
    )

    if not issues and not problem_summaries:
        lines.append("No significant operational issues detected.")
        return "\n".join(lines)

    # Categorize issues
    categories = {}
    issue_timeline = []
    for iss in issues:
        code = iss[4] or "unknown"
        detail = iss[6] or ""
        comments = iss[7] or ""

        # Determine issue category
        if "well_control" in code:
            cat = "Well Control"
        elif "repair" in code:
            cat = "Equipment Repair"
        elif "waiting" in code:
            if "weather" in code:
                cat = "Weather Delay"
            else:
                cat = "Waiting/Delay"
        elif "equipment failure" in detail:
            cat = "Equipment Failure"
        elif "mud loss" in detail:
            cat = "Mud Losses"
        elif "operation failed" in detail:
            cat = "Operational Difficulty"
        else:
            cat = "Other Issue"

        if cat not in categories:
            categories[cat] = {"count": 0, "events": []}
        categories[cat]["count"] += 1
        categories[cat]["events"].append({
            "date": iss[0],
            "depth_m": iss[3],
            "code": code,
            "detail": detail,
            "comments": comments[:200],
        })

        # Estimate duration
        try:
            from datetime import datetime
            start = datetime.fromisoformat(iss[1]) if iss[1] else None
            end = datetime.fromisoformat(iss[2]) if iss[2] else None
            dur_hrs = (end - start).total_seconds() / 3600 if start and end else 0
        except (ValueError, TypeError):
            dur_hrs = 0

        issue_timeline.append({
            "date": iss[0],
            "depth_m": iss[3],
            "category": cat,
            "duration_hrs": dur_hrs,
            "comments": comments[:150],
        })

    # Issue Summary by Category
    lines.append("Issue Summary by Category:")
    for cat, info in sorted(categories.items(), key=lambda x: -x[1]["count"]):
        lines.append(f"\n  {cat}: {info['count']} occurrences")
        # Show first few examples
        for ev in info["events"][:3]:
            depth = f"{ev['depth_m']:.0f}m" if ev["depth_m"] else "N/A"
            lines.append(f"    - {ev['date']} @ {depth}: {ev['comments']}")

    # Timeline of major issues
    lines.append("\n\nIssue Timeline (chronological):")
    for it in issue_timeline[:30]:
        depth = f"{it['depth_m']:.0f}m" if it["depth_m"] else "N/A"
        dur = f" ({it['duration_hrs']:.1f}h)" if it["duration_hrs"] > 0 else ""
        lines.append(f"  {it['date']} @ {depth} [{it['category']}]{dur}: {it['comments']}")

    # Contributing factors analysis
    lines.append("\n\nPotential Contributing Factors:")
    if "Equipment Repair" in categories or "Equipment Failure" in categories:
        lines.append("  - Equipment reliability: Multiple equipment-related issues detected")
    if "Mud Losses" in categories:
        lines.append("  - Wellbore stability: Mud loss events suggest formation issues")
    if "Well Control" in categories:
        lines.append("  - Pressure management: Well control events indicate pore pressure challenges")
    if "Weather Delay" in categories:
        lines.append("  - Environmental: Weather-related delays impacting operations")
    if "Operational Difficulty" in categories:
        lines.append("  - Operational complexity: Multiple operation failures noted")

    # Problem summaries from DDR
    if problem_summaries:
        lines.append("\n\nRelevant 24hr Summary Excerpts:")
        for ps in problem_summaries[:5]:
            depth = f"{ps[1]:.0f}m" if ps[1] else "N/A"
            summary = (ps[2] or "")[:200]
            lines.append(f"  {ps[0]} ({depth}): \"{summary}\"")

    return "\n".join(lines)
