"""Tool registry: OpenAI function definitions and dispatch for all agent tools."""

import json
import logging

from src.tools.query_data import query_drilling_data
from src.tools.search_reports import search_daily_reports
from src.tools.well_overview import get_well_overview
from src.tools.phase_detection import get_drilling_phases
from src.tools.efficiency_metrics import compute_efficiency_metrics
from src.tools.compare_wells import compare_wells
from src.tools.bha_analysis import get_bha_configurations
from src.tools.issue_detection import identify_operational_issues
from src.tools.formation_context import get_formation_context
from src.tools.visualize import generate_depth_time_plot
from src.tools.ddr_narrative import get_ddr_narrative
from src.tools.field_benchmarks import get_field_benchmarks

logger = logging.getLogger(__name__)

# OpenAI function tool definitions
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_drilling_data",
            "description": (
                "Execute a SQL query against the Volve drilling database. "
                "DDR tables: ddr_status (well, date, report_no, md_m, tvd_m, hole_diameter_in, "
                "dist_drill_m, summary_24hr, forecast_24hr, rop_current_m_per_hr), "
                "ddr_activities (well, date, start_time, end_time, depth_m, activity_code, "
                "state, state_detail, comments), "
                "ddr_fluids (well, date, mud_type, mud_class, density_gcc, pv_mPas, yp_Pa), "
                "ddr_surveys (well, date, md_m, tvd_m, inclination_deg, azimuth_deg), "
                "wellbore_info (well, date, name_well, name_wellbore, spud_date, drill_complete_date). "
                "WITSML tables: witsml_bha_runs (well, wellbore, run_name, start_time, end_time, "
                "num_bit_run, num_string_run, md_start_m, md_stop_m), "
                "witsml_mudlog (well, wellbore, md_top_m, md_bottom_m, lith_type, lith_pct, "
                "rop_avg_m_per_hr, rop_min_m_per_hr, rop_max_m_per_hr, wob_avg_kN, torque_avg_kNm, "
                "rpm_avg, mud_weight_sg, ecd_sg, dxc, methane_avg_ppm, ethane_avg_ppm), "
                "witsml_trajectory (well, wellbore, md_m, tvd_m, inclination_deg, azimuth_deg, "
                "dls_deg_per_30m, ns_m, ew_m), "
                "witsml_messages (well, wellbore, timestamp, md_m, message_type, message_text). "
                "Other: formation_tops, perforations, production. "
                "Well names use underscores: '15_9_F_11_T2', '15_9_F_1_C'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "SQL query to execute (DuckDB SQL dialect)"
                    },
                },
                "required": ["sql_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_daily_reports",
            "description": (
                "Search daily drilling report text using semantic similarity. "
                "Searches over DDR activity comments, 24-hour summaries, and forecasts. "
                "Use this to find specific operational events, descriptions, or context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query"
                    },
                    "well": {
                        "type": "string",
                        "description": "Filter by well (underscore format, e.g. '15_9_F_11_T2')"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date filter (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date filter (YYYY-MM-DD)"
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of results (default 10)"
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_well_overview",
            "description": (
                "Get comprehensive overview for a well: date range, depth range, "
                "hole sizes, activity distribution, wellbore info, formation tops."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "well": {
                        "type": "string",
                        "description": "Well name (underscore format, e.g. '15_9_F_11_T2')"
                    },
                },
                "required": ["well"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_drilling_phases",
            "description": (
                "Identify and label major drilling phases for a well. "
                "Analyzes activity codes, depth progression, and hole sizes to detect "
                "phase transitions (drilling, tripping, casing, cementing, completion, NPT, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "well": {
                        "type": "string",
                        "description": "Well name (underscore format)"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)"
                    },
                },
                "required": ["well"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_efficiency_metrics",
            "description": (
                "Compute drilling efficiency: productive vs non-productive time, "
                "NPT breakdown, ROP by section, daily depth progress statistics."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "well": {
                        "type": "string",
                        "description": "Well name (underscore format)"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)"
                    },
                },
                "required": ["well"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_wells",
            "description": (
                "Compare drilling metrics between two wells side-by-side: "
                "date ranges, depths, activity distributions, NPT, hole sections, ROP."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "well1": {
                        "type": "string",
                        "description": "First well name (underscore format)"
                    },
                    "well2": {
                        "type": "string",
                        "description": "Second well name (underscore format)"
                    },
                },
                "required": ["well1", "well2"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bha_configurations",
            "description": (
                "Analyze BHA configurations and drilling performance for a well. "
                "Uses WITSML structured data: official BHA runs (161 total) with depth ranges, "
                "mudlog drilling parameters (ROP m/hr, WOB kN, torque kNm, RPM) per depth interval, "
                "performance ranking by hole section, lithology correlation, and DDR report evidence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "well": {
                        "type": "string",
                        "description": "Well name (underscore format)"
                    },
                },
                "required": ["well"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "identify_operational_issues",
            "description": (
                "Identify operational issues during drilling: equipment failures, "
                "well control events, mud losses, weather delays. "
                "Categorizes issues and proposes contributing factors."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "well": {
                        "type": "string",
                        "description": "Well name (underscore format)"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)"
                    },
                },
                "required": ["well"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_formation_context",
            "description": (
                "Get geological formation context for a well at a specific depth. "
                "Returns which formation a depth falls in, formation column, "
                "and surrounding formations. Uses formation_tops table (409 records)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "well": {
                        "type": "string",
                        "description": "Well name (underscore format)"
                    },
                    "depth_m": {
                        "type": "number",
                        "description": "Measured depth in meters (optional — omit for full formation column)"
                    },
                },
                "required": ["well"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_field_benchmarks",
            "description": (
                "Return cleaned field-wide rankings and summaries for cross-well questions. "
                "Prefer this over ad hoc SQL when the user asks 'across all wells', "
                "'field-wide', 'highest/lowest', 'rank', 'benchmark', gas-response ranking, "
                "risk ranking, or production summary. Modes: daily_progress, "
                "section_performance, gas_response, risk, production_summary."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": (
                            "Benchmark mode: daily_progress, section_performance, "
                            "gas_response, risk, or production_summary"
                        )
                    },
                    "wells": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional list of underscore-format wells to restrict the benchmark"
                        )
                    },
                    "hole_size_in": {
                        "type": "number",
                        "description": (
                            "Optional hole size filter in inches for section-based modes"
                        )
                    },
                    "formation": {
                        "type": "string",
                        "description": (
                            "Optional formation name for gas_response mode; defaults to Hugin"
                        )
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "How many top and bottom rows to show (default 5)"
                    },
                },
                "required": ["mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_depth_time_plot",
            "description": (
                "Generate a depth-vs-time plot for a well's drilling campaign. "
                "Shows depth progression, hole section boundaries as colored regions, "
                "and problem activities as red dots. Saves a PNG chart file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "well": {
                        "type": "string",
                        "description": "Well name (underscore format)"
                    },
                },
                "required": ["well"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ddr_narrative",
            "description": (
                "Retrieve DDR daily summaries, forecasts, and activity comments for a "
                "specific date or depth range. Unlike semantic search, this ALWAYS returns "
                "text if the well has DDR data in that range. Use this to get direct quotes "
                "for the 'Evidence from Daily Reports' section. Also returns WITSML operational "
                "messages if available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "well": {
                        "type": "string",
                        "description": "Well name (underscore format)"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)"
                    },
                    "depth_from": {
                        "type": "number",
                        "description": "Minimum depth in meters"
                    },
                    "depth_to": {
                        "type": "number",
                        "description": "Maximum depth in meters"
                    },
                },
                "required": ["well"],
            },
        },
    },
]

# Dispatch map: function name -> callable
TOOL_FUNCTIONS = {
    "query_drilling_data": lambda args: query_drilling_data(args["sql_query"]),
    "search_daily_reports": lambda args: search_daily_reports(
        query=args["query"],
        well=args.get("well"),
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        n_results=args.get("n_results", 10),
    ),
    "get_well_overview": lambda args: get_well_overview(args["well"]),
    "get_drilling_phases": lambda args: get_drilling_phases(
        well=args["well"],
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
    ),
    "compute_efficiency_metrics": lambda args: compute_efficiency_metrics(
        well=args["well"],
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
    ),
    "compare_wells": lambda args: compare_wells(args["well1"], args["well2"]),
    "get_bha_configurations": lambda args: get_bha_configurations(args["well"]),
    "identify_operational_issues": lambda args: identify_operational_issues(
        well=args["well"],
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
    ),
    "get_formation_context": lambda args: get_formation_context(
        well=args["well"],
        depth_m=args.get("depth_m"),
    ),
    "get_field_benchmarks": lambda args: get_field_benchmarks(
        mode=args["mode"],
        wells=args.get("wells"),
        hole_size_in=args.get("hole_size_in"),
        formation=args.get("formation"),
        top_n=args.get("top_n", 5),
    ),
    "generate_depth_time_plot": lambda args: generate_depth_time_plot(args["well"]),
    "get_ddr_narrative": lambda args: get_ddr_narrative(
        well=args["well"],
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        depth_from=args.get("depth_from"),
        depth_to=args.get("depth_to"),
    ),
}


def execute_tool(name: str, arguments: str) -> str:
    """Execute a tool by name with JSON arguments string.

    Args:
        name: Tool function name
        arguments: JSON string of arguments

    Returns:
        Tool result as string
    """
    if name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool '{name}'"

    try:
        args = json.loads(arguments)
    except json.JSONDecodeError as e:
        return f"Error parsing arguments: {e}"

    try:
        result = TOOL_FUNCTIONS[name](args)
        # Truncate very long results
        if len(result) > 15000:
            result = result[:15000] + "\n\n... [truncated, showing first 15000 chars]"
        return result
    except Exception as e:
        logger.exception("Tool execution error for %s", name)
        return f"Error executing {name}: {e}"
