"""Tests for agent tools against the database."""

import pytest
from pathlib import Path
from src.config import DB_PATH


def _db_exists():
    return DB_PATH.exists()


@pytest.fixture(autouse=True)
def require_db():
    if not _db_exists():
        pytest.skip("Database not built — run 'python -m src.main ingest' first")


class TestQueryData:
    """Test the SQL query tool."""

    def test_basic_query(self):
        from src.tools.query_data import query_drilling_data
        result = query_drilling_data("SELECT COUNT(*) as cnt FROM ddr_status")
        assert "1759" in result

    def test_well_list(self):
        from src.tools.query_data import get_available_wells
        wells = get_available_wells()
        assert len(wells) == 26
        assert "15_9_F_11_T2" in wells

    def test_invalid_sql(self):
        from src.tools.query_data import query_drilling_data
        result = query_drilling_data("SELECT * FROM nonexistent_table")
        assert "Error" in result or "error" in result

    def test_limit_applied(self):
        from src.tools.query_data import query_drilling_data
        result = query_drilling_data(
            "SELECT * FROM ddr_activities WHERE well = '15_9_F_11_T2'", limit=5
        )
        lines = [l for l in result.split("\n") if l.strip() and not l.startswith("-")]
        assert len(lines) <= 8

    def test_witsml_tables_queryable(self):
        from src.tools.query_data import query_drilling_data
        result = query_drilling_data("SELECT COUNT(*) as cnt FROM witsml_bha_runs")
        assert "161" in result
        result = query_drilling_data("SELECT COUNT(*) as cnt FROM witsml_mudlog")
        assert "2882" in result


class TestWellOverview:
    """Test the well overview tool."""

    def test_returns_data(self):
        from src.tools.well_overview import get_well_overview
        result = get_well_overview("15_9_F_11_T2")
        assert "15/9-F-11 T2" in result
        assert "Date Range" in result
        assert "2013-03-24" in result

    def test_no_data_well(self):
        from src.tools.well_overview import get_well_overview
        result = get_well_overview("NONEXISTENT_WELL")
        assert "No data found" in result


class TestPhaseDetection:
    """Test the drilling phase detection tool."""

    def test_returns_phases(self):
        from src.tools.phase_detection import get_drilling_phases
        result = get_drilling_phases("15_9_F_11_T2")
        assert "Drilling Phases" in result
        assert "Drilling" in result
        assert "2013" in result

    def test_hole_sections_detected(self):
        from src.tools.phase_detection import get_drilling_phases
        result = get_drilling_phases("15_9_F_11_T2")
        assert '26' in result
        assert '17.5' in result or '17 1/2' in result

    def test_major_phases_present(self):
        from src.tools.phase_detection import get_drilling_phases
        result = get_drilling_phases("15_9_F_11_T2")
        assert "MAJOR PHASES" in result
        assert "Surface" in result or "26\"" in result

    def test_depth_validation_present(self):
        from src.tools.phase_detection import get_drilling_phases
        result = get_drilling_phases("15_9_F_11_T2")
        assert "DEPTH PROGRESSION" in result

    def test_confidence_assessment_present(self):
        from src.tools.phase_detection import get_drilling_phases
        result = get_drilling_phases("15_9_F_11_T2")
        assert "CONFIDENCE" in result
        assert "HIGH" in result or "MEDIUM" in result or "LOW" in result


class TestEfficiencyMetrics:
    """Test the efficiency metrics tool."""

    def test_returns_metrics(self):
        from src.tools.efficiency_metrics import compute_efficiency_metrics
        result = compute_efficiency_metrics("15_9_F_11_T2")
        assert "Efficiency Metrics" in result
        assert "Productive Time" in result
        assert "NPT" in result


class TestCompareWells:
    """Test the well comparison tool."""

    def test_returns_comparison(self):
        from src.tools.compare_wells import compare_wells
        result = compare_wells("15_9_F_11", "15_9_F_1_C")
        assert "Comparison" in result
        assert "15/9-F-11" in result
        assert "15/9-F-1 C" in result


class TestIssueDetection:
    """Test the issue detection tool."""

    def test_returns_issues(self):
        from src.tools.issue_detection import identify_operational_issues
        result = identify_operational_issues("15_9_F_11_T2")
        assert "Operational Issues" in result
        assert "Problem/NPT Activities" in result


class TestBhaAnalysis:
    """Test the BHA analysis tool (rewritten with WITSML data)."""

    def test_returns_analysis(self):
        from src.tools.bha_analysis import get_bha_configurations
        result = get_bha_configurations("15_9_F_11_T2")
        assert "BHA Configuration" in result

    def test_has_official_runs(self):
        from src.tools.bha_analysis import get_bha_configurations
        result = get_bha_configurations("15_9_F_11_T2")
        assert "Official BHA Runs" in result
        assert "WITSML" in result

    def test_has_mudlog_params(self):
        from src.tools.bha_analysis import get_bha_configurations
        result = get_bha_configurations("15_9_F_11_T2")
        assert "Drilling Parameters" in result or "MudLog" in result
        assert "ROP" in result or "m/h" in result

    def test_has_performance_ranking(self):
        from src.tools.bha_analysis import get_bha_configurations
        result = get_bha_configurations("15_9_F_11_T2")
        assert "Performance Ranking" in result or "Ranking" in result

    def test_has_ddr_evidence(self):
        from src.tools.bha_analysis import get_bha_configurations
        result = get_bha_configurations("15_9_F_11_T2")
        assert "DDR Report Evidence" in result or "DDR" in result

    def test_well_without_witsml(self):
        """Wells without WITSML data should fallback gracefully."""
        from src.tools.bha_analysis import get_bha_configurations
        result = get_bha_configurations("15_9_19_A")
        assert "BHA Configuration" in result
        assert "No WITSML" in result or "No activity" in result


class TestDdrNarrative:
    """Test the DDR narrative retrieval tool."""

    def test_returns_narrative(self):
        from src.tools.ddr_narrative import get_ddr_narrative
        result = get_ddr_narrative("15_9_F_11_T2")
        assert "DDR Narrative" in result
        assert "DAILY SUMMARIES" in result

    def test_date_filtered(self):
        from src.tools.ddr_narrative import get_ddr_narrative
        result = get_ddr_narrative(
            "15_9_F_11_T2", date_from="2013-04-14", date_to="2013-04-16"
        )
        assert "2013-04-1" in result
        assert "DDR" in result

    def test_depth_filtered(self):
        from src.tools.ddr_narrative import get_ddr_narrative
        result = get_ddr_narrative(
            "15_9_F_11_T2", depth_from=1000, depth_to=2000
        )
        assert "DDR Narrative" in result

    def test_always_returns_text(self):
        """Core requirement: this tool must always return DDR text for valid wells."""
        from src.tools.ddr_narrative import get_ddr_narrative
        result = get_ddr_narrative("15_9_F_11_T2")
        assert "Summary:" in result or "summary" in result.lower()
        # Must contain actual quoted text
        assert '"' in result

    def test_empty_well(self):
        from src.tools.ddr_narrative import get_ddr_narrative
        result = get_ddr_narrative("NONEXISTENT")
        assert "No DDR narrative" in result


class TestFormationContext:
    """Test the formation context tool."""

    def test_returns_formations(self):
        from src.tools.formation_context import get_formation_context
        result = get_formation_context("15_9_F_11")
        assert "formation" in result.lower() or "Formation" in result

    def test_depth_lookup(self):
        from src.tools.formation_context import get_formation_context
        result = get_formation_context("15_9_F_11", depth_m=3000.0)
        assert "Current formation" in result or "formation" in result.lower()

    def test_full_column(self):
        from src.tools.formation_context import get_formation_context
        result = get_formation_context("15_9_F_11")
        assert "Complete formation column" in result or "Hugin" in result

    def test_unknown_well_fallback(self):
        from src.tools.formation_context import get_formation_context
        result = get_formation_context("NONEXISTENT_WELL")
        assert "No formation" in result or "Available wells" in result


class TestSearchReports:
    """Test the report search tool (SQL fallback)."""

    def test_keyword_search(self):
        from src.tools.search_reports import search_daily_reports
        result = search_daily_reports(
            "stuck pipe overpull", well="15_9_F_11_T2"
        )
        assert "Result" in result or "No matching" in result

    def test_filtered_by_well(self):
        from src.tools.search_reports import search_daily_reports
        result = search_daily_reports("drilling", well="15_9_F_11_T2")
        if "Result" in result:
            assert "15_9_F_11_T2" in result


class TestToolRegistry:
    """Test tool registry dispatch."""

    def test_all_tools_registered(self):
        from src.tools.tool_registry import TOOL_FUNCTIONS, TOOL_DEFINITIONS
        assert len(TOOL_FUNCTIONS) == len(TOOL_DEFINITIONS)
        for defn in TOOL_DEFINITIONS:
            name = defn["function"]["name"]
            assert name in TOOL_FUNCTIONS, f"Tool {name} not in dispatch map"

    def test_tool_count(self):
        from src.tools.tool_registry import TOOL_DEFINITIONS
        assert len(TOOL_DEFINITIONS) == 11  # 9 + visualize + ddr_narrative

    def test_execute_tool(self):
        from src.tools.tool_registry import execute_tool
        import json
        result = execute_tool(
            "get_well_overview",
            json.dumps({"well": "15_9_F_11_T2"})
        )
        assert "15/9-F-11 T2" in result

    def test_execute_formation_tool(self):
        from src.tools.tool_registry import execute_tool
        import json
        result = execute_tool(
            "get_formation_context",
            json.dumps({"well": "15_9_F_11", "depth_m": 3000.0})
        )
        assert "formation" in result.lower()

    def test_unknown_tool(self):
        from src.tools.tool_registry import execute_tool
        result = execute_tool("nonexistent_tool", "{}")
        assert "Error" in result


class TestOutputFormatter:
    """Test the output formatter validation."""

    def test_validate_good_answer(self):
        from src.agent.output_formatter import validate_answer
        answer = """## Answer
        The well drilled 3 sections in 53 days.
        ## Evidence from Drilling Data
        At 2574m MD, ROP averaged 29.2 m/hr.
        ## Evidence from Daily Reports
        DDR 15/9-F-11 T2, 2013-04-15: "Set 13-3/8 casing at 2145m."
        ## Reasoning
        Step 1: Analyzed hole sizes.
        ## Assumptions
        Activity codes are correct.
        ## Confidence & Uncertainty
        HIGH — multiple data sources confirm."""
        result = validate_answer(answer)
        assert result["valid"]
        assert result["has_measurement"]
        assert len(result["warnings"]) == 0 or len(result["warnings"]) <= 1

    def test_validate_missing_sections(self):
        from src.agent.output_formatter import validate_answer
        answer = "## Answer\nThe well was drilled successfully."
        result = validate_answer(answer)
        assert not result["valid"]
        assert len(result["missing_sections"]) > 0

    def test_format_answer_shows_warnings(self):
        from src.agent.output_formatter import format_answer
        formatted = format_answer("Just a plain answer.", "Test question?")
        assert "QUESTION:" in formatted
        assert "Missing sections" in formatted
