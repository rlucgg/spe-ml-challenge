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
        # Header + up to 5 data rows + summary
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
        assert '26' in result  # 26" hole section
        assert '17.5' in result or '17 1/2' in result  # 17.5" hole section


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
    """Test the BHA analysis tool."""

    def test_returns_analysis(self):
        from src.tools.bha_analysis import get_bha_configurations
        result = get_bha_configurations("15_9_F_11_T2")
        assert "BHA Configuration" in result


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

    def test_execute_tool(self):
        from src.tools.tool_registry import execute_tool
        import json
        result = execute_tool(
            "get_well_overview",
            json.dumps({"well": "15_9_F_11_T2"})
        )
        assert "15/9-F-11 T2" in result

    def test_unknown_tool(self):
        from src.tools.tool_registry import execute_tool
        result = execute_tool("nonexistent_tool", "{}")
        assert "Error" in result
