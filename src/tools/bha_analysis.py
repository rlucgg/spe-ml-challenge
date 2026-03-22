"""Tool: Analyze BHA configurations using WITSML structured data + DDR context."""

import logging
from typing import Optional

import duckdb

from src.config import DB_PATH, display_well_name

logger = logging.getLogger(__name__)


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def get_bha_configurations(well: str) -> str:
    """Analyze BHA configurations and their drilling performance for a well.

    Uses WITSML structured data (bha_runs + mudlog) for actual drilling
    parameters, cross-referenced with DDR activity comments for context.

    Args:
        well: Well name (underscore format, e.g. '15_9_F_11_T2')

    Returns:
        BHA run analysis with performance metrics, rankings, and DDR evidence
    """
    con = _get_con()
    like = well.replace("*", "%")

    # 1. Get official BHA runs from WITSML
    bha_runs = con.execute("""
        SELECT run_name, start_time, end_time, num_bit_run, num_string_run,
               md_start_m, md_stop_m
        FROM witsml_bha_runs
        WHERE well LIKE ?
        ORDER BY start_time
    """, [like]).fetchall()

    # 2. Get mudlog drilling parameters (with quality filters for realistic values)
    mudlog_raw_count = con.execute("""
        SELECT COUNT(*) FROM witsml_mudlog WHERE well LIKE ?
          AND rop_avg_m_per_hr IS NOT NULL
    """, [like]).fetchone()[0]

    mudlog = con.execute("""
        SELECT md_top_m, md_bottom_m, lith_type, lith_pct,
               rop_avg_m_per_hr, wob_avg_kN, torque_avg_kNm, rpm_avg,
               mud_weight_sg, ecd_sg, dxc
        FROM witsml_mudlog
        WHERE well LIKE ?
          AND rop_avg_m_per_hr IS NOT NULL
          AND (rop_avg_m_per_hr > 0 AND rop_avg_m_per_hr <= 200)
          AND (rpm_avg IS NULL OR (rpm_avg > 0 AND rpm_avg <= 300))
          AND (wob_avg_kN IS NULL OR (wob_avg_kN > 0 AND wob_avg_kN <= 500))
          AND (torque_avg_kNm IS NULL OR (torque_avg_kNm > 0 AND torque_avg_kNm <= 100))
        ORDER BY md_top_m
    """, [like]).fetchall()

    mudlog_filtered = mudlog_raw_count - len(mudlog)

    # 3. Get DDR depth progression and hole sizes
    ddr_status = con.execute("""
        SELECT date, md_m, hole_diameter_in, dist_drill_m
        FROM ddr_status
        WHERE well LIKE ?
        ORDER BY date
    """, [like]).fetchall()

    # 4. Get DDR comments mentioning BHA/bit for narrative evidence
    bha_comments = con.execute("""
        SELECT date, depth_m, activity_code, comments
        FROM ddr_activities
        WHERE well LIKE ?
          AND comments IS NOT NULL
          AND (LOWER(comments) LIKE '%bha%' OR LOWER(comments) LIKE '%bit%'
               OR LOWER(comments) LIKE '%pick up%' OR LOWER(comments) LIKE '%p/u%'
               OR LOWER(comments) LIKE '%tripped out%' OR LOWER(comments) LIKE '%pooh%'
               OR LOWER(comments) LIKE '%new assembly%')
        ORDER BY date, start_time
    """, [like]).fetchall()

    con.close()

    lines = [f"=== BHA Configuration Analysis for {display_well_name(well)} ===\n"]

    # --- Section A: Official BHA Runs ---
    if bha_runs:
        lines.append(f"Official BHA Runs (from WITSML): {len(bha_runs)}\n")
        for i, run in enumerate(bha_runs):
            name = run[0] or f"Run {i+1}"
            start = run[1][:10] if run[1] else "?"
            end = run[2][:10] if run[2] else "?"
            md_s = f"{run[5]:.0f}m" if run[5] is not None else "?"
            md_e = f"{run[6]:.0f}m" if run[6] is not None else "?"
            bit_num = run[3] or ""
            str_num = run[4] or ""
            ids = []
            if bit_num:
                ids.append(f"bit#{bit_num}")
            if str_num:
                ids.append(f"string#{str_num}")
            id_str = f" ({', '.join(ids)})" if ids else ""
            lines.append(
                f"  {name}{id_str}: {start} to {end} | MD: {md_s} → {md_e}"
            )
    else:
        lines.append("No WITSML BHA run data available for this well.")

    # --- Section B: Drilling Parameters from MudLog ---
    if mudlog:
        quality_note = ""
        if mudlog_filtered > 0:
            quality_note = f" ({mudlog_filtered} outlier readings filtered)"
        lines.append(f"\nDrilling Parameters (from WITSML MudLog): {len(mudlog)} depth intervals{quality_note}\n")

        # Group by hole section using DDR hole sizes
        hole_map = {}
        for d in ddr_status:
            if d[1] and d[2]:
                hole_map[d[1]] = d[2]

        def _get_hole_size(depth: float) -> Optional[float]:
            best_hole = None
            best_dist = float("inf")
            for md, hole in hole_map.items():
                dist = abs(md - depth)
                if dist < best_dist:
                    best_dist = dist
                    best_hole = hole
            return best_hole

        # Compute stats per hole section
        section_stats = {}
        for ml in mudlog:
            md_mid = ((ml[0] or 0) + (ml[1] or 0)) / 2
            hole = _get_hole_size(md_mid)
            key = f"{hole}\"" if hole else "Unknown"
            if key not in section_stats:
                section_stats[key] = {
                    "rop": [], "wob": [], "torque": [], "rpm": [],
                    "mw": [], "ecd": [], "intervals": 0,
                    "md_min": ml[0], "md_max": ml[1], "liths": {},
                }
            s = section_stats[key]
            s["intervals"] += 1
            if ml[1] and (s["md_max"] is None or ml[1] > s["md_max"]):
                s["md_max"] = ml[1]
            if ml[0] and (s["md_min"] is None or ml[0] < s["md_min"]):
                s["md_min"] = ml[0]
            if ml[4] is not None:
                s["rop"].append(ml[4])
            if ml[5] is not None:
                s["wob"].append(ml[5])
            if ml[6] is not None:
                s["torque"].append(ml[6])
            if ml[7] is not None:
                s["rpm"].append(ml[7])
            if ml[8] is not None:
                s["mw"].append(ml[8])
            if ml[9] is not None:
                s["ecd"].append(ml[9])
            lith = ml[2] or "unknown"
            s["liths"][lith] = s["liths"].get(lith, 0) + 1

        def _avg(vals):
            return sum(vals) / len(vals) if vals else 0

        lines.append(f"{'Section':<12} {'Depth Range':<22} {'Avg ROP':>10} {'Avg WOB':>10} "
                      f"{'Avg Torque':>12} {'Avg RPM':>10} {'MW (sg)':>10} {'Intervals':>10}")
        lines.append("-" * 100)

        ranked_sections = []
        for sec, s in sorted(section_stats.items(),
                              key=lambda x: x[1].get("md_min") or 0):
            avg_rop = _avg(s["rop"])
            avg_wob = _avg(s["wob"])
            avg_tq = _avg(s["torque"])
            avg_rpm = _avg(s["rpm"])
            avg_mw = _avg(s["mw"])
            md_range = f"{s['md_min']:.0f}-{s['md_max']:.0f}m" if s["md_min"] and s["md_max"] else "?"
            lines.append(
                f"  {sec:<10} {md_range:<22} {avg_rop:>8.1f}m/h {avg_wob:>8.1f}kN "
                f"{avg_tq:>10.1f}kNm {avg_rpm:>8.0f} {avg_mw:>8.3f} {s['intervals']:>10}"
            )
            ranked_sections.append((sec, avg_rop, s))

        # Top lithologies per section
        lines.append("\nLithology by Section:")
        for sec, s in sorted(section_stats.items(),
                              key=lambda x: x[1].get("md_min") or 0):
            top_liths = sorted(s["liths"].items(), key=lambda x: -x[1])[:3]
            lith_str = ", ".join(f"{l} ({c})" for l, c in top_liths)
            lines.append(f"  {sec}: {lith_str}")

        # --- Section C: Performance Ranking ---
        if ranked_sections:
            lines.append("\nPerformance Ranking (by average ROP):")
            for rank, (sec, avg_rop, s) in enumerate(
                sorted(ranked_sections, key=lambda x: -x[1]), 1
            ):
                md_range = f"{s['md_min']:.0f}-{s['md_max']:.0f}m" if s["md_min"] and s["md_max"] else "?"
                rop_range = ""
                if s["rop"]:
                    rop_range = f" (min={min(s['rop']):.1f}, max={max(s['rop']):.1f})"
                lines.append(
                    f"  {rank}. {sec} @ {md_range}: avg ROP {avg_rop:.1f} m/hr{rop_range}"
                )
    else:
        lines.append("\nNo WITSML mudlog data available. Using DDR-based analysis.")

    # Fallback/Additional context: DDR-based hole section performance with estimated ROP
    if ddr_status:
        by_hole = {}
        for d in ddr_status:
            h = d[2]
            if h and d[3] and d[3] > 0:
                if h not in by_hole:
                    by_hole[h] = {"dists": [], "dates": [], "md_min": d[1], "md_max": d[1]}
                by_hole[h]["dists"].append(d[3])
                by_hole[h]["dates"].append(d[0])
                if d[1] and d[1] < by_hole[h]["md_min"]:
                    by_hole[h]["md_min"] = d[1]
                if d[1] and d[1] > by_hole[h]["md_max"]:
                    by_hole[h]["md_max"] = d[1]
        if by_hole:
            lines.append("\nPerformance by Hole Section (DDR daily progress — estimated):")
            ranked = []
            for hole, info in sorted(by_hole.items(), key=lambda x: x[1].get("md_min", 0)):
                n_days = len(info["dates"])
                total = sum(info["dists"])
                avg = total / n_days if n_days else 0
                md_range = f"{info['md_min']:.0f}-{info['md_max']:.0f}m"
                lines.append(
                    f"  {hole}\" hole: {md_range} | {n_days} days, "
                    f"{total:.0f}m drilled, avg {avg:.1f} m/day"
                )
                ranked.append((hole, avg, md_range))

            if len(ranked) > 1:
                best = max(ranked, key=lambda x: x[1])
                worst = min(ranked, key=lambda x: x[1])
                lines.append(f"\n  Best section: {best[0]}\" ({best[2]}) at {best[1]:.1f} m/day")
                lines.append(f"  Slowest section: {worst[0]}\" ({worst[2]}) at {worst[1]:.1f} m/day")

    # Extract BHA mentions from DDR comments
    if bha_comments:
        lines.append(f"\nBHA References from DDR Comments ({len(bha_comments)} mentions):")
        for bc in bha_comments[:10]:
            depth = f"{bc[1]:.0f}m" if bc[1] else "?"
            comment = (bc[3] or "")[:180]
            lines.append(f"  {bc[0]} @ {depth}: \"{comment}\"")

    # --- Section D: DDR Evidence ---
    if bha_comments:
        lines.append(f"\nDDR Report Evidence ({len(bha_comments)} BHA-related entries):")
        for bc in bha_comments[:8]:
            depth = f"{bc[1]:.0f}m" if bc[1] else "?"
            comment = (bc[3] or "")[:180]
            lines.append(f"  {bc[0]} @ {depth}: \"{comment}\"")

    # --- Data Source Quality ---
    lines.append("\nData Source Quality:")
    if bha_runs and mudlog:
        lines.append(f"  WITSML data: {len(bha_runs)} BHA runs, {len(mudlog)} mudlog intervals — HIGH confidence")
    elif bha_runs:
        lines.append(f"  WITSML BHA runs: {len(bha_runs)} — MEDIUM confidence (no mudlog data)")
    else:
        lines.append("  DDR-derived estimates only — LOWER confidence (no WITSML real-time data)")

    return "\n".join(lines)
