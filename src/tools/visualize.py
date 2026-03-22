"""Tool: Generate depth-vs-time plots for drilling operations."""

import logging
import tempfile
from pathlib import Path
from typing import Optional

import duckdb

from src.config import DB_PATH, display_well_name

logger = logging.getLogger(__name__)


def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def generate_depth_time_plot(well: str) -> str:
    """Generate a depth-vs-time plot for a well's drilling campaign.

    Creates a matplotlib chart showing depth progression over time with:
    - Hole section boundaries as colored regions
    - Problem activities marked as red dots
    - Casing points annotated

    Args:
        well: Well name (underscore format, e.g. '15_9_F_11_T2')

    Returns:
        Path to the saved PNG file, or error message
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime
    except ImportError:
        return "Error: matplotlib not available"

    con = _get_con()
    like = well.replace("*", "%")

    # Get depth progression
    rows = con.execute("""
        SELECT date, md_m, hole_diameter_in
        FROM ddr_status
        WHERE well LIKE ? AND md_m IS NOT NULL
        ORDER BY date
    """, [like]).fetchall()

    # Get problem activities
    problems = con.execute("""
        SELECT date, depth_m
        FROM ddr_activities
        WHERE well LIKE ? AND state = 'problem' AND depth_m IS NOT NULL
    """, [like]).fetchall()

    con.close()

    if not rows:
        return f"No depth data found for well '{well}'"

    dates = [datetime.strptime(r[0], "%Y-%m-%d") for r in rows]
    depths = [r[1] for r in rows]
    holes = [r[2] for r in rows]

    fig, ax = plt.subplots(figsize=(12, 7))

    # Color regions by hole section
    hole_colors = {
        36.0: "#E8F5E9", 30.0: "#E8F5E9",
        26.0: "#C8E6C9", 17.5: "#FFF9C4",
        12.25: "#FFE0B2", 8.5: "#FFCCBC",
    }
    prev_hole = None
    region_start = 0
    for i, h in enumerate(holes):
        if h != prev_hole and prev_hole is not None and i > 0:
            color = hole_colors.get(prev_hole, "#F5F5F5")
            ax.axhspan(
                min(depths[region_start:i]), max(depths[region_start:i]),
                alpha=0.3, color=color, label=f'{prev_hole}"' if prev_hole not in [h2 for h2 in holes[:region_start]] else ""
            )
            region_start = i
        prev_hole = h
    if prev_hole:
        color = hole_colors.get(prev_hole, "#F5F5F5")
        ax.axhspan(
            min(depths[region_start:]), max(depths[region_start:]),
            alpha=0.3, color=color
        )

    # Main depth line
    ax.plot(dates, depths, "b-", linewidth=1.5, label="Measured Depth")

    # Problem markers
    if problems:
        p_dates = [datetime.strptime(p[0], "%Y-%m-%d") for p in problems]
        p_depths = [p[1] for p in problems]
        ax.scatter(p_dates, p_depths, c="red", s=20, zorder=5, label="Problems", alpha=0.7)

    # Annotate hole section changes
    prev_h = None
    for i, (d, depth, h) in enumerate(zip(dates, depths, holes)):
        if h != prev_h and prev_h is not None:
            ax.axhline(y=depth, color="gray", linestyle="--", linewidth=0.5, alpha=0.5)
            ax.annotate(f'{h}"', xy=(d, depth), fontsize=8, color="gray")
        prev_h = h

    ax.invert_yaxis()
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Measured Depth (m)", fontsize=12)
    ax.set_title(f"Depth vs Time — {display_well_name(well)}", fontsize=14)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    out_dir = Path(tempfile.gettempdir())
    out_path = out_dir / f"depth_time_{well}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

    return f"Chart saved to: {out_path}\nWell: {display_well_name(well)}\nDate range: {dates[0].date()} to {dates[-1].date()}\nDepth range: {min(depths):.0f}m to {max(depths):.0f}m\nProblem events plotted: {len(problems)}"
