"""Tool: Compare drilling metrics between two wells."""

import logging
from typing import Optional

import duckdb

from src.config import DB_PATH, display_well_name

logger = logging.getLogger(__name__)


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def compare_wells(well1: str, well2: str) -> str:
    """Compare drilling operations between two wells.

    Compares: date ranges, total depth, drilling duration, activity distributions,
    NPT, hole sections, and depth progress rates.

    Args:
        well1: First well name (underscore format)
        well2: Second well name (underscore format)

    Returns:
        Side-by-side comparison text
    """
    con = _get_con()

    def well_stats(well: str) -> dict:
        like = well.replace("*", "%")
        stats = {}

        # Basic stats
        row = con.execute("""
            SELECT MIN(date), MAX(date), COUNT(DISTINCT date),
                   MIN(md_m), MAX(md_m)
            FROM ddr_status WHERE well LIKE ?
        """, [like]).fetchone()
        stats["first_date"] = row[0]
        stats["last_date"] = row[1]
        stats["num_reports"] = row[2]
        stats["min_depth"] = row[3]
        stats["max_depth"] = row[4]

        # Activity distribution
        acts = con.execute("""
            SELECT activity_code, COUNT(*) as cnt
            FROM ddr_activities
            WHERE well LIKE ? AND activity_code != ''
            GROUP BY activity_code ORDER BY cnt DESC
        """, [like]).fetchall()
        stats["activities"] = {a[0]: a[1] for a in acts}
        stats["total_activities"] = sum(a[1] for a in acts) if acts else 0

        # Problem count
        probs = con.execute("""
            SELECT COUNT(*) FROM ddr_activities
            WHERE well LIKE ? AND state = 'problem'
        """, [like]).fetchone()
        stats["problem_count"] = probs[0] if probs else 0

        # Hole sections
        holes = con.execute("""
            SELECT DISTINCT hole_diameter_in, MIN(md_m), MAX(md_m),
                   COUNT(DISTINCT date)
            FROM ddr_status
            WHERE well LIKE ? AND hole_diameter_in IS NOT NULL
            GROUP BY hole_diameter_in ORDER BY MIN(md_m)
        """, [like]).fetchall()
        stats["hole_sections"] = holes

        # Daily drilling distances
        dists = con.execute("""
            SELECT dist_drill_m FROM ddr_status
            WHERE well LIKE ? AND dist_drill_m IS NOT NULL AND dist_drill_m > 0
        """, [like]).fetchall()
        if dists:
            vals = [d[0] for d in dists]
            stats["avg_daily_drill"] = sum(vals) / len(vals)
            stats["max_daily_drill"] = max(vals)
        else:
            stats["avg_daily_drill"] = 0
            stats["max_daily_drill"] = 0

        # Production data
        prod = con.execute("""
            SELECT SUM(bore_oil_vol), SUM(bore_gas_vol), SUM(bore_wat_vol), AVG(avg_downhole_pressure)
            FROM production
            WHERE well LIKE ?
        """, [like]).fetchone()
        stats["production"] = prod if prod and prod[0] is not None else None

        return stats

    s1 = well_stats(well1)
    s2 = well_stats(well2)
    con.close()

    if not s1["first_date"]:
        return f"No data found for well '{well1}'"
    if not s2["first_date"]:
        return f"No data found for well '{well2}'"

    n1 = display_well_name(well1)
    n2 = display_well_name(well2)

    lines = [f"=== Comparison: {n1} vs {n2} ===\n"]

    # Side-by-side summary
    lines.append(f"{'Metric':<30} {n1:<25} {n2:<25}")
    lines.append("-" * 80)
    lines.append(f"{'Date Range':<30} {s1['first_date']} - {s1['last_date']:<10} "
                 f"{s2['first_date']} - {s2['last_date']}")
    lines.append(f"{'DDR Reports':<30} {s1['num_reports']:<25} {s2['num_reports']}")
    d1 = f"{s1['min_depth']:.0f} - {s1['max_depth']:.0f}m" if s1['max_depth'] else "N/A"
    d2 = f"{s2['min_depth']:.0f} - {s2['max_depth']:.0f}m" if s2['max_depth'] else "N/A"
    lines.append(f"{'Depth Range (MD)':<30} {d1:<25} {d2}")
    lines.append(f"{'Total Activities':<30} {s1['total_activities']:<25} "
                 f"{s2['total_activities']}")
    lines.append(f"{'Problem Activities':<30} {s1['problem_count']:<25} "
                 f"{s2['problem_count']}")
    lines.append(f"{'Avg Daily Drill (m)':<30} {s1['avg_daily_drill']:<25.1f} "
                 f"{s2['avg_daily_drill']:.1f}")
    lines.append(f"{'Max Daily Drill (m)':<30} {s1['max_daily_drill']:<25.1f} "
                 f"{s2['max_daily_drill']:.1f}")

    # Activity comparison
    all_codes = sorted(
        set(list(s1["activities"].keys()) + list(s2["activities"].keys()))
    )
    if all_codes:
        lines.append(f"\n{'Activity Code':<35} {n1:<20} {n2:<20}")
        lines.append("-" * 75)
        for code in all_codes:
            c1 = s1["activities"].get(code, 0)
            c2 = s2["activities"].get(code, 0)
            p1 = f"{c1} ({c1 / s1['total_activities'] * 100:.0f}%)" if s1['total_activities'] else "0"
            p2 = f"{c2} ({c2 / s2['total_activities'] * 100:.0f}%)" if s2['total_activities'] else "0"
            lines.append(f"  {code:<33} {p1:<20} {p2}")

    # Hole section comparison
    lines.append(f"\nHole Sections:")
    lines.append(f"  {n1}:")
    for h in s1.get("hole_sections", []):
        lines.append(f"    {h[0]}\" hole: {h[1]:.0f}m - {h[2]:.0f}m ({h[3]} days)")
    lines.append(f"  {n2}:")
    for h in s2.get("hole_sections", []):
        lines.append(f"    {h[0]}\" hole: {h[1]:.0f}m - {h[2]:.0f}m ({h[3]} days)")

    # Production comparison
    has_prod = s1.get("production") or s2.get("production")
    if has_prod:
        lines.append(f"\nProduction Summary:")
        lines.append(f"{'Metric':<30} {n1:<25} {n2:<25}")
        lines.append("-" * 80)
        p1 = s1.get("production") or (0, 0, 0, 0)
        p2 = s2.get("production") or (0, 0, 0, 0)
        
        lines.append(f"{'Cum Oil (Sm3)':<30} {p1[0] or 0:<25.1f} {p2[0] or 0:.1f}")
        lines.append(f"{'Cum Gas (Sm3)':<30} {p1[1] or 0:<25.1f} {p2[1] or 0:.1f}")
        lines.append(f"{'Cum Water (Sm3)':<30} {p1[2] or 0:<25.1f} {p2[2] or 0:.1f}")
        lines.append(f"{'Avg Downhole Press (bar)':<30} {p1[3] or 0:<25.1f} {p2[3] or 0:.1f}")

    return "\n".join(lines)
