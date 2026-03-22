"""Tool: Identify operational issues with root cause correlation."""

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
    """Identify key operational issues with root cause correlation.

    Analyzes DDR activities with state='problem' or NPT-related codes,
    then cross-references with mud properties, formation context, hole section,
    and WITSML drilling parameters to identify contributing factors.

    Args:
        well: Well name (underscore format)
        date_from: Optional start date (YYYY-MM-DD)
        date_to: Optional end date (YYYY-MM-DD)

    Returns:
        Issue analysis with timeline, categories, root cause correlation
    """
    con = _get_con()
    like = well.replace("*", "%")

    def _df(q, p):
        if date_from:
            q += " AND date >= ?"
            p.append(date_from)
        if date_to:
            q += " AND date <= ?"
            p.append(date_to)
        return q, p

    # Get problem activities
    iq = """
        SELECT date, start_time, end_time, depth_m, activity_code,
               state, state_detail, comments
        FROM ddr_activities
        WHERE well LIKE ?
          AND (state = 'problem'
               OR activity_code LIKE 'interruption%'
               OR activity_code LIKE 'well_control%'
               OR state_detail IN ('equipment failure', 'mud loss', 'operation failed'))
    """
    ip = [like]
    iq, ip = _df(iq, ip)
    iq += " ORDER BY date, start_time"
    issues = con.execute(iq, ip).fetchall()

    # Total activity count
    tq = "SELECT COUNT(*) FROM ddr_activities WHERE well LIKE ?"
    tp = [like]
    tq, tp = _df(tq, tp)
    total_count = con.execute(tq, tp).fetchone()[0]

    # Fluid data for correlation
    fq = "SELECT date, mud_type, mud_class, density_gcc, pv_mPas, yp_Pa FROM ddr_fluids WHERE well LIKE ?"
    fp = [like]
    fq, fp = _df(fq, fp)
    fq += " ORDER BY date"
    fluids = con.execute(fq, fp).fetchall()

    # Hole size data
    hq = "SELECT date, md_m, hole_diameter_in FROM ddr_status WHERE well LIKE ?"
    hp = [like]
    hq, hp = _df(hq, hp)
    hq += " ORDER BY date"
    hole_data = con.execute(hq, hp).fetchall()

    # Formation tops for geological context
    formation_tops = con.execute("""
        SELECT surface_name, md_m FROM formation_tops
        WHERE well LIKE ? ORDER BY md_m
    """, [like]).fetchall()

    # WITSML mudlog for drilling parameter context
    mudlog_stats = con.execute("""
        SELECT md_top_m, md_bottom_m, rop_avg_m_per_hr, wob_avg_kN, lith_type
        FROM witsml_mudlog
        WHERE well LIKE ? AND rop_avg_m_per_hr IS NOT NULL
          AND rop_avg_m_per_hr > 0 AND rop_avg_m_per_hr < 500
        ORDER BY md_top_m
    """, [like]).fetchall()

    # Problem summaries
    sq = """
        SELECT date, md_m, summary_24hr FROM ddr_status
        WHERE well LIKE ?
          AND (summary_24hr LIKE '%problem%' OR summary_24hr LIKE '%issue%'
               OR summary_24hr LIKE '%failure%' OR summary_24hr LIKE '%stuck%'
               OR summary_24hr LIKE '%loss%' OR summary_24hr LIKE '%kick%'
               OR summary_24hr LIKE '%repair%' OR summary_24hr LIKE '%wait%')
    """
    sp = [like]
    sq, sp = _df(sq, sp)
    sq += " ORDER BY date"
    problem_summaries = con.execute(sq, sp).fetchall()

    con.close()

    lines = [f"=== Operational Issues for {display_well_name(well)} ===\n"]
    if total_count:
        lines.append(
            f"Total Activities: {total_count} | "
            f"Problem/NPT Activities: {len(issues)} "
            f"({len(issues) / total_count * 100:.1f}% of total)\n"
        )

    if not issues and not problem_summaries:
        lines.append("No significant operational issues detected.")
        return "\n".join(lines)

    # Build lookup helpers
    fluid_by_date = {}
    for f in fluids:
        fluid_by_date[f[0]] = {"type": f[1], "class": f[2], "density": f[3], "pv": f[4], "yp": f[5]}

    hole_by_date = {}
    for h in hole_data:
        hole_by_date[h[0]] = {"md_m": h[1], "hole_in": h[2]}

    def _get_formation(depth_m):
        if not depth_m or not formation_tops:
            return None
        current = None
        for name, md in formation_tops:
            if md is not None and md <= depth_m:
                current = name
        return current

    def _get_rop_context(depth_m):
        if not depth_m or not mudlog_stats:
            return None
        rops = [m[2] for m in mudlog_stats if m[0] and m[1] and m[0] <= depth_m <= m[1]]
        if rops:
            return sum(rops) / len(rops)
        # Find nearest
        nearest = min(mudlog_stats, key=lambda m: abs(((m[0] or 0) + (m[1] or 0)) / 2 - depth_m))
        return nearest[2]

    # --- Categorize issues ---
    categories = {}
    issue_timeline = []

    for iss in issues:
        code = iss[4] or "unknown"
        detail = iss[6] or ""
        comments = iss[7] or ""

        if "well_control" in code:
            cat = "Well Control"
        elif "repair" in code or "maintain" in code.lower():
            cat = "Equipment Repair"
        elif "waiting" in code:
            cat = "Weather Delay" if "weather" in code else "Waiting/Delay"
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
            "date": iss[0], "depth_m": iss[3], "code": code,
            "detail": detail, "comments": comments[:200],
        })

        try:
            from datetime import datetime
            st = datetime.fromisoformat(iss[1]) if iss[1] else None
            en = datetime.fromisoformat(iss[2]) if iss[2] else None
            dur_hrs = (en - st).total_seconds() / 3600 if st and en else 0
        except (ValueError, TypeError):
            dur_hrs = 0

        issue_timeline.append({
            "date": iss[0], "depth_m": iss[3], "category": cat,
            "duration_hrs": dur_hrs, "comments": comments[:150],
        })

    # --- Issue Summary ---
    lines.append("Issue Summary by Category:")
    for cat, info in sorted(categories.items(), key=lambda x: -x[1]["count"]):
        lines.append(f"\n  {cat}: {info['count']} occurrences")
        for ev in info["events"][:3]:
            depth = f"{ev['depth_m']:.0f}m" if ev["depth_m"] else "N/A"
            lines.append(f"    - {ev['date']} @ {depth}: {ev['comments']}")

    # --- Contributing Factors Analysis (the killer section) ---
    lines.append("\n\nCONTRIBUTING FACTORS ANALYSIS:\n")

    for cat, info in sorted(categories.items(), key=lambda x: -x[1]["count"]):
        if info["count"] < 2:
            continue
        lines.append(f"  {cat} ({info['count']} events):")

        # Depth distribution
        depths = [e["depth_m"] for e in info["events"] if e["depth_m"]]
        if depths:
            lines.append(f"    Depth range: {min(depths):.0f}m - {max(depths):.0f}m MD")

        # Hole section correlation
        event_holes = set()
        for e in info["events"]:
            hole_info = hole_by_date.get(e["date"])
            if hole_info and hole_info["hole_in"]:
                event_holes.add(hole_info["hole_in"])
        if event_holes:
            lines.append(f"    Hole sections affected: {', '.join(f'{h}\"' for h in sorted(event_holes))}")

        # Formation correlation
        formations = set()
        for e in info["events"]:
            fm = _get_formation(e["depth_m"])
            if fm:
                formations.add(fm)
        if formations:
            lines.append(f"    Formations: {', '.join(sorted(formations))}")

        # Mud properties during issues
        issue_dates = {e["date"] for e in info["events"]}
        issue_muds = [fluid_by_date[d] for d in issue_dates if d in fluid_by_date]
        if issue_muds:
            densities = [m["density"] for m in issue_muds if m["density"]]
            if densities:
                lines.append(f"    Mud weight during issues: {min(densities):.2f} - {max(densities):.2f} g/cm3")

        # ROP context
        if depths and mudlog_stats:
            rop_at_issues = [_get_rop_context(d) for d in depths]
            rop_at_issues = [r for r in rop_at_issues if r]
            if rop_at_issues:
                all_rops = [m[2] for m in mudlog_stats]
                avg_all = sum(all_rops) / len(all_rops)
                avg_issue = sum(rop_at_issues) / len(rop_at_issues)
                comparison = "above" if avg_issue > avg_all * 1.1 else "below" if avg_issue < avg_all * 0.9 else "near"
                lines.append(
                    f"    ROP at issue depths: avg {avg_issue:.1f} m/hr "
                    f"({comparison} well average of {avg_all:.1f} m/hr)"
                )

        lines.append("")

    # --- Temporal Trend ---
    if len(issue_timeline) > 5:
        lines.append("TEMPORAL TREND:")
        mid = len(issue_timeline) // 2
        first_half = issue_timeline[:mid]
        second_half = issue_timeline[mid:]
        lines.append(
            f"  First half: {len(first_half)} issues "
            f"({first_half[0]['date']} to {first_half[-1]['date']})"
        )
        lines.append(
            f"  Second half: {len(second_half)} issues "
            f"({second_half[0]['date']} to {second_half[-1]['date']})"
        )
        if len(second_half) > len(first_half) * 1.3:
            lines.append("  Trend: Issues INCREASING over time")
        elif len(second_half) < len(first_half) * 0.7:
            lines.append("  Trend: Issues DECREASING over time")
        else:
            lines.append("  Trend: Issues roughly STABLE over time")

    # --- Issue Timeline ---
    lines.append("\nIssue Timeline (chronological):")
    for it in issue_timeline[:25]:
        depth = f"{it['depth_m']:.0f}m" if it["depth_m"] else "N/A"
        dur = f" ({it['duration_hrs']:.1f}h)" if it["duration_hrs"] > 0 else ""
        lines.append(f"  {it['date']} @ {depth} [{it['category']}]{dur}: {it['comments']}")

    # --- DDR Summary Evidence ---
    if problem_summaries:
        lines.append("\n\nRelevant 24hr Summary Excerpts:")
        for ps in problem_summaries[:5]:
            depth = f"{ps[1]:.0f}m" if ps[1] else "N/A"
            summary = (ps[2] or "")[:200]
            lines.append(f"  {ps[0]} ({depth}): \"{summary}\"")

    return "\n".join(lines)
