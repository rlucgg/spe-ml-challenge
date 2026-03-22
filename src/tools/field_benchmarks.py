"""Tool: Clean field-wide benchmarking across wells and sections."""

from __future__ import annotations

import logging
from statistics import mean, pstdev
from typing import Optional

import duckdb

from src.config import DB_PATH, display_well_name

logger = logging.getLogger(__name__)


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def _sql_array(values: Optional[list[str]]) -> str:
    """Render a SQL array literal for optional well filters."""
    if not values:
        return "NULL"
    quoted = ", ".join("'" + v.replace("'", "''") + "'" for v in values)
    return f"[{quoted}]"


def _zscore(value: float, values: list[float]) -> float:
    """Compute a stable population z-score."""
    if len(values) < 2:
        return 0.0
    sigma = pstdev(values)
    if sigma == 0:
        return 0.0
    return (value - mean(values)) / sigma


def _format_top_bottom(
    title: str,
    rows: list[dict],
    top_n: int,
    line_builder,
) -> list[str]:
    """Format ranked rows with top and bottom slices."""
    lines = [title]
    if not rows:
        lines.append("  No rows found.")
        return lines

    top_rows = rows[:top_n]
    bottom_rows = list(reversed(rows[-top_n:])) if len(rows) > top_n else []

    lines.append("  Top:")
    for idx, row in enumerate(top_rows, 1):
        lines.append(f"    {idx}. {line_builder(row)}")

    if bottom_rows:
        lines.append("  Bottom:")
        for idx, row in enumerate(bottom_rows, 1):
            lines.append(f"    {idx}. {line_builder(row)}")

    return lines


def _formation_window(
    con: duckdb.DuckDBPyConnection,
    well: str,
    formation: str,
) -> Optional[tuple[float, float]]:
    """Resolve a usable MD window for a formation in one well."""
    rows = con.execute(
        """
        SELECT surface_name, md_m
        FROM formation_tops
        WHERE well = ? AND LOWER(surface_name) LIKE ?
        ORDER BY md_m
        """,
        [well, f"%{formation.lower()}%"],
    ).fetchall()
    if not rows:
        return None

    top_candidates = [md for name, md in rows if md is not None and "top" in name.lower()]
    base_candidates = [md for name, md in rows if md is not None and "base" in name.lower()]

    top_md = min(top_candidates) if top_candidates else rows[0][1]
    if top_md is None:
        return None

    if base_candidates:
        base_md = max(base_candidates)
    else:
        next_row = con.execute(
            """
            SELECT MIN(md_m)
            FROM formation_tops
            WHERE well = ? AND md_m > ?
            """,
            [well, top_md],
        ).fetchone()
        base_md = next_row[0] if next_row and next_row[0] is not None else top_md + 400.0

    if base_md <= top_md:
        base_md = top_md + 400.0

    return top_md, base_md


def _daily_progress_benchmark(
    con: duckdb.DuckDBPyConnection,
    wells: Optional[list[str]],
    hole_size_in: Optional[float],
    top_n: int,
) -> str:
    """Return cleaned cross-well daily drilling progress benchmarks."""
    well_filter = ""
    hole_filter = ""
    params: list = []

    if wells:
        placeholders = ",".join("?" for _ in wells)
        well_filter = f" AND well IN ({placeholders})"
        params.extend(wells)
    if hole_size_in is not None:
        hole_filter = " AND hole_diameter_in = ?"
        params.append(hole_size_in)

    rows = con.execute(
        f"""
        WITH daily AS (
            SELECT
                well,
                hole_diameter_in,
                date,
                SUM(COALESCE(dist_drill_m, 0)) AS dist_m
            FROM ddr_status
            WHERE hole_diameter_in IS NOT NULL
              AND COALESCE(dist_drill_m, 0) > 0
              {well_filter}
              {hole_filter}
            GROUP BY well, hole_diameter_in, date
        ),
        sec AS (
            SELECT
                well,
                hole_diameter_in,
                AVG(dist_m) AS avg_daily_m,
                COUNT(*) AS drilling_days,
                SUM(dist_m) AS total_m
            FROM daily
            GROUP BY well, hole_diameter_in
        )
        SELECT well, hole_diameter_in, avg_daily_m, drilling_days, total_m
        FROM sec
        WHERE drilling_days >= 2
        ORDER BY avg_daily_m DESC
        """,
        params,
    ).fetchall()

    data = [
        {
            "well": row[0],
            "hole_in": row[1],
            "avg_daily_m": row[2],
            "drilling_days": row[3],
            "total_m": row[4],
        }
        for row in rows
    ]

    lines = [
        "=== Field Benchmarks: Daily Progress ===",
        "Rules: excludes NULL hole sizes, requires dist_drill_m > 0, requires at least 2 drilling days per section.",
    ]
    lines.extend(
        _format_top_bottom(
            "Ranked hole sections by average drilled distance per active drilling day:",
            data,
            top_n,
            lambda r: (
                f"{display_well_name(r['well'])} | {r['hole_in']:.2f}\" "
                f"| avg {r['avg_daily_m']:.1f} m/day | {r['drilling_days']} drilling days "
                f"| total {r['total_m']:.1f} m"
            ),
        )
    )
    return "\n".join(lines)


def _section_performance_benchmark(
    con: duckdb.DuckDBPyConnection,
    wells: Optional[list[str]],
    hole_size_in: Optional[float],
    top_n: int,
) -> str:
    """Return cleaned section performance / difficulty benchmarks."""
    well_filter = ""
    params: list = []
    if wells:
        placeholders = ",".join("?" for _ in wells)
        well_filter = f"WHERE well IN ({placeholders})"
        params.extend(wells)

    bounds = con.execute(
        f"""
        SELECT
            well,
            hole_diameter_in,
            MIN(md_m) AS md_min,
            MAX(md_m) AS md_max
        FROM ddr_status
        {well_filter}
        GROUP BY well, hole_diameter_in
        HAVING hole_diameter_in IS NOT NULL
        """,
        params,
    ).fetchall()

    mudlog_filter = ""
    mudlog_params: list = []
    if wells:
        placeholders = ",".join("?" for _ in wells)
        mudlog_filter = f" AND well IN ({placeholders})"
        mudlog_params.extend(wells)

    mudlog_rows = con.execute(
        f"""
        SELECT
            well,
            (COALESCE(md_top_m, 0) + COALESCE(md_bottom_m, 0)) / 2.0 AS md_mid,
            rop_avg_m_per_hr,
            wob_avg_kN,
            torque_avg_kNm,
            rpm_avg,
            mud_weight_sg,
            ecd_sg,
            methane_avg_ppm
        FROM witsml_mudlog
        WHERE rop_avg_m_per_hr IS NOT NULL
          AND rop_avg_m_per_hr > 0
          AND rop_avg_m_per_hr <= 200
          AND (rpm_avg IS NULL OR (rpm_avg > 0 AND rpm_avg <= 300))
          AND (wob_avg_kN IS NULL OR (wob_avg_kN > 0 AND wob_avg_kN <= 500))
          AND (torque_avg_kNm IS NULL OR (torque_avg_kNm > 0 AND torque_avg_kNm <= 100))
          {mudlog_filter}
        """,
        mudlog_params,
    ).fetchall()

    grouped: dict[tuple[str, float], dict] = {}
    for well, hole_in, md_min, md_max in bounds:
        if hole_size_in is not None and hole_in != hole_size_in:
            continue
        grouped[(well, hole_in)] = {
            "well": well,
            "hole_in": hole_in,
            "md_min": md_min,
            "md_max": md_max,
            "rop": [],
            "wob": [],
            "torque": [],
            "rpm": [],
            "mw": [],
            "ecd": [],
            "methane": [],
        }

    for row in mudlog_rows:
        well, md_mid, rop, wob, torque, rpm, mw, ecd, methane = row
        for (sec_well, sec_hole), bucket in grouped.items():
            if sec_well != well:
                continue
            if bucket["md_min"] is None or bucket["md_max"] is None:
                continue
            if bucket["md_min"] <= md_mid <= bucket["md_max"]:
                bucket["rop"].append(rop)
                if wob is not None:
                    bucket["wob"].append(wob)
                if torque is not None:
                    bucket["torque"].append(torque)
                if rpm is not None:
                    bucket["rpm"].append(rpm)
                if mw is not None:
                    bucket["mw"].append(mw)
                if ecd is not None:
                    bucket["ecd"].append(ecd)
                if methane is not None:
                    bucket["methane"].append(methane)
                break

    rows: list[dict] = []
    for row in grouped.values():
        if len(row["rop"]) < 10:
            continue
        rows.append(
            {
                "well": row["well"],
                "hole_in": row["hole_in"],
                "md_min": row["md_min"],
                "md_max": row["md_max"],
                "intervals": len(row["rop"]),
                "avg_rop": mean(row["rop"]),
                "avg_wob": mean(row["wob"]) if row["wob"] else 0.0,
                "avg_torque": mean(row["torque"]) if row["torque"] else 0.0,
                "avg_rpm": mean(row["rpm"]) if row["rpm"] else 0.0,
                "avg_mw": mean(row["mw"]) if row["mw"] else 0.0,
                "avg_ecd": mean(row["ecd"]) if row["ecd"] else 0.0,
                "avg_ch4": mean(row["methane"]) if row["methane"] else 0.0,
            }
        )

    if rows:
        rops = [r["avg_rop"] for r in rows]
        wobs = [r["avg_wob"] for r in rows]
        torques = [r["avg_torque"] for r in rows]
        for row in rows:
            row["difficulty_index"] = (
                _zscore(row["avg_wob"], wobs)
                + _zscore(row["avg_torque"], torques)
                - _zscore(row["avg_rop"], rops)
            )

    hardest = sorted(rows, key=lambda r: r["difficulty_index"], reverse=True)
    fastest = sorted(rows, key=lambda r: r["avg_rop"], reverse=True)

    lines = [
        "=== Field Benchmarks: Section Performance ===",
        "Rules: assigns mudlog intervals to DDR section depth windows, filters ROP/RPM/WOB/torque outliers, requires at least 10 mudlog intervals per section.",
    ]
    lines.extend(
        _format_top_bottom(
            "Hardest sections by composite difficulty index (higher WOB/torque and lower ROP score as harder):",
            hardest,
            top_n,
            lambda r: (
                f"{display_well_name(r['well'])} | {r['hole_in']:.2f}\" "
                f"| difficulty {r['difficulty_index']:.2f} | avg ROP {r['avg_rop']:.1f} m/hr "
                f"| WOB {r['avg_wob']:.1f} kN | torque {r['avg_torque']:.1f} kNm "
                f"| intervals {r['intervals']}"
            ),
        )
    )
    lines.append("")
    lines.extend(
        _format_top_bottom(
            "Fastest sections by average ROP:",
            fastest,
            top_n,
            lambda r: (
                f"{display_well_name(r['well'])} | {r['hole_in']:.2f}\" "
                f"| avg ROP {r['avg_rop']:.1f} m/hr | WOB {r['avg_wob']:.1f} kN "
                f"| torque {r['avg_torque']:.1f} kNm | RPM {r['avg_rpm']:.0f}"
            ),
        )
    )
    return "\n".join(lines)


def _gas_response_benchmark(
    con: duckdb.DuckDBPyConnection,
    wells: Optional[list[str]],
    formation: str,
    top_n: int,
) -> str:
    """Return formation-window gas-response benchmarks."""
    well_rows = con.execute(
        """
        SELECT DISTINCT well
        FROM witsml_mudlog
        ORDER BY well
        """
    ).fetchall()
    candidates = [row[0] for row in well_rows]
    if wells:
        candidates = [well for well in candidates if well in wells]

    rows: list[dict] = []
    for well in candidates:
        window = _formation_window(con, well, formation)
        if not window:
            continue
        top_md, base_md = window
        stats = con.execute(
            """
            SELECT
                COUNT(*) AS n_intervals,
                MAX(methane_avg_ppm) AS max_ch4,
                MAX(ethane_avg_ppm) AS max_c2,
                AVG(methane_avg_ppm) AS avg_ch4,
                AVG(ethane_avg_ppm) AS avg_c2
            FROM witsml_mudlog
            WHERE well = ?
              AND md_top_m >= ?
              AND md_bottom_m <= ?
              AND methane_avg_ppm IS NOT NULL
            """,
            [well, top_md, base_md],
        ).fetchone()
        if not stats or not stats[0]:
            continue

        dominant = con.execute(
            """
            SELECT lith_type, COUNT(*) AS n
            FROM witsml_mudlog
            WHERE well = ?
              AND md_top_m >= ?
              AND md_bottom_m <= ?
              AND lith_type IS NOT NULL
            GROUP BY lith_type
            ORDER BY n DESC
            LIMIT 1
            """,
            [well, top_md, base_md],
        ).fetchone()

        rows.append(
            {
                "well": well,
                "top_md": top_md,
                "base_md": base_md,
                "intervals": stats[0],
                "max_ch4": stats[1] or 0.0,
                "max_c2": stats[2] or 0.0,
                "avg_ch4": stats[3] or 0.0,
                "avg_c2": stats[4] or 0.0,
                "dominant_lith": dominant[0] if dominant else "unknown",
            }
        )

    rows = sorted(rows, key=lambda r: (r["max_ch4"], r["max_c2"]), reverse=True)

    lines = [
        f"=== Field Benchmarks: Gas Response in {formation} ===",
        "Rules: filters mudlog intervals to the resolved formation MD window for each well and ranks by peak methane, then peak ethane.",
    ]
    lines.extend(
        _format_top_bottom(
            "Ranked wells by in-formation gas response:",
            rows,
            top_n,
            lambda r: (
                f"{display_well_name(r['well'])} | {r['top_md']:.1f}-{r['base_md']:.1f} m MD "
                f"| max CH4 {r['max_ch4']:.0f} ppm | max C2 {r['max_c2']:.0f} ppm "
                f"| avg CH4 {r['avg_ch4']:.0f} ppm | dominant lith {r['dominant_lith']}"
            ),
        )
    )
    return "\n".join(lines)


def _risk_benchmark(
    con: duckdb.DuckDBPyConnection,
    wells: Optional[list[str]],
    top_n: int,
) -> str:
    """Return field-wide risk benchmarks from issue proxies and geometry."""
    well_filter = ""
    params: list = []
    if wells:
        placeholders = ",".join("?" for _ in wells)
        well_filter = f"WHERE well IN ({placeholders})"
        params.extend(wells)

    rows = con.execute(
        f"""
        WITH acts AS (
            SELECT
                well,
                COUNT(*) FILTER (WHERE activity_code LIKE 'interruption%') AS interruptions,
                COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(comments, '')) LIKE '%stuck%'
                       OR LOWER(COALESCE(comments, '')) LIKE '%tight hole%'
                       OR LOWER(COALESCE(comments, '')) LIKE '%pack off%'
                       OR LOWER(COALESCE(comments, '')) LIKE '%packing-off%'
                       OR LOWER(COALESCE(comments, '')) LIKE '%lost circulation%'
                       OR LOWER(COALESCE(comments, '')) LIKE '%mud loss%'
                       OR LOWER(COALESCE(comments, '')) LIKE '%losses%'
                       OR LOWER(COALESCE(comments, '')) LIKE '%kick%'
                       OR LOWER(COALESCE(comments, '')) LIKE '%influx%'
                       OR LOWER(COALESCE(comments, '')) LIKE '%cavings%'
                       OR LOWER(COALESCE(comments, '')) LIKE '%slough%'
                ) AS severe_mentions,
                COUNT(*) FILTER (WHERE activity_code LIKE 'well_control%') AS well_control,
                COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(comments, '')) LIKE '%fish%'
                       OR LOWER(COALESCE(comments, '')) LIKE '%fishing%'
                ) AS fishing_mentions,
                COUNT(*) AS total_activities
            FROM ddr_activities
            {well_filter}
            GROUP BY well
        ),
        perf AS (
            SELECT
                well,
                COUNT(*) AS perf_count,
                MAX(md_base_m) AS deepest_perf_md
            FROM perforations
            GROUP BY well
        )
        SELECT
            acts.well,
            interruptions,
            severe_mentions,
            well_control,
            fishing_mentions,
            total_activities,
            COALESCE(perf.perf_count, 0) AS perf_count,
            COALESCE(perf.deepest_perf_md, 0) AS deepest_perf_md
        FROM acts
        LEFT JOIN perf ON perf.well = acts.well
        ORDER BY acts.well
        """,
        params,
    ).fetchall()

    data: list[dict] = []
    for row in rows:
        score = (
            row[2] * 3.0
            + row[3] * 5.0
            + row[4] * 2.0
            + row[1] * 0.05
            + (1.0 if row[6] > 0 else 0.0)
        )
        data.append(
            {
                "well": row[0],
                "interruptions": row[1],
                "severe_mentions": row[2],
                "well_control": row[3],
                "fishing_mentions": row[4],
                "total_activities": row[5],
                "perf_count": row[6],
                "deepest_perf_md": row[7],
                "risk_score": score,
            }
        )

    data = sorted(data, key=lambda r: r["risk_score"], reverse=True)

    lines = [
        "=== Field Benchmarks: Well Risk ===",
        "Rules: risk score emphasizes severe stuck/loss/kick/cavings narratives, well-control tags, fishing language, and only lightly weights generic interruptions; perforation presence is treated as added intervention complexity, not drilling risk.",
    ]
    lines.extend(
        _format_top_bottom(
            "Ranked wells by composite drilling/intervention risk proxy:",
            data,
            top_n,
            lambda r: (
                f"{display_well_name(r['well'])} | risk {r['risk_score']:.1f} "
                f"| severe mentions {r['severe_mentions']} | well control {r['well_control']} "
                f"| fishing {r['fishing_mentions']} | interruptions {r['interruptions']} "
                f"| perforation sets {r['perf_count']}"
            ),
        )
    )
    return "\n".join(lines)


def _production_summary(
    con: duckdb.DuckDBPyConnection,
    wells: Optional[list[str]],
    top_n: int,
) -> str:
    """Return normalized production summary by well."""
    rows = con.execute(
        """
        SELECT
            well,
            COUNT(*) AS prod_days,
            SUM(bore_oil_vol) AS cum_oil,
            SUM(bore_gas_vol) AS cum_gas,
            SUM(bore_wat_vol) AS cum_water,
            AVG(avg_downhole_pressure) AS avg_pressure
        FROM production
        GROUP BY well
        ORDER BY cum_oil DESC NULLS LAST
        """
    ).fetchall()

    data = []
    for row in rows:
        if wells and row[0] not in wells:
            continue
        data.append(
            {
                "well": row[0],
                "prod_days": row[1],
                "cum_oil": row[2],
                "cum_gas": row[3],
                "cum_water": row[4],
                "avg_pressure": row[5],
            }
        )

    lines = [
        "=== Field Benchmarks: Production Summary ===",
        "Rules: production wells are stored in normalized underscore format for direct comparison with DDR and WITSML wells.",
    ]
    lines.extend(
        _format_top_bottom(
            "Ranked wells by cumulative oil volume:",
            data,
            top_n,
            lambda r: (
                f"{display_well_name(r['well'])} | prod days {r['prod_days']} "
                f"| cum oil {0.0 if r['cum_oil'] is None else r['cum_oil']:.1f} "
                f"| cum gas {0.0 if r['cum_gas'] is None else r['cum_gas']:.1f} "
                f"| avg pressure {0.0 if r['avg_pressure'] is None else r['avg_pressure']:.1f}"
            ),
        )
    )
    return "\n".join(lines)


def get_field_benchmarks(
    mode: str,
    wells: Optional[list[str]] = None,
    hole_size_in: Optional[float] = None,
    formation: Optional[str] = None,
    top_n: int = 5,
) -> str:
    """Return cleaned field-wide benchmarks for cross-well questions.

    Args:
        mode: One of daily_progress, section_performance, gas_response,
            risk, production_summary.
        wells: Optional list of underscore-format wells to restrict the scan.
        hole_size_in: Optional hole size filter for section-based modes.
        formation: Optional formation name for gas_response.
        top_n: Number of top/bottom rows to show.
    """
    con = _get_con()
    try:
        if mode == "daily_progress":
            return _daily_progress_benchmark(con, wells, hole_size_in, top_n)
        if mode == "section_performance":
            return _section_performance_benchmark(con, wells, hole_size_in, top_n)
        if mode == "gas_response":
            return _gas_response_benchmark(con, wells, formation or "Hugin", top_n)
        if mode == "risk":
            return _risk_benchmark(con, wells, top_n)
        if mode == "production_summary":
            return _production_summary(con, wells, top_n)
        return f"Unknown benchmark mode '{mode}'. Valid modes: daily_progress, section_performance, gas_response, risk, production_summary."
    finally:
        con.close()
