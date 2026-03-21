"""Tests for DDR XML parsing."""

import pytest
from pathlib import Path
from src.ingest.parse_ddr import parse_well_from_filename, parse_ddr_file, parse_all_ddrs
from src.config import DDR_DIR


class TestParseWellFromFilename:
    """Test extraction of well name and date from DDR filenames."""

    def test_f11_t2(self):
        well, date = parse_well_from_filename("15_9_F_11_T2_2013_03_24.xml")
        assert well == "15_9_F_11_T2"
        assert date == "2013-03-24"

    def test_exploration_well(self):
        well, date = parse_well_from_filename("15_9_19_A_1997_07_25.xml")
        assert well == "15_9_19_A"
        assert date == "1997-07-25"

    def test_f1_c(self):
        well, date = parse_well_from_filename("15_9_F_1_C_2014_02_22.xml")
        assert well == "15_9_F_1_C"
        assert date == "2014-02-22"

    def test_simple_well(self):
        well, date = parse_well_from_filename("15_9_F_4_2007_06_01.xml")
        assert well == "15_9_F_4"
        assert date == "2007-06-01"


class TestParseDdrFile:
    """Test parsing of individual DDR XML files."""

    @pytest.fixture
    def sample_file(self):
        f = DDR_DIR / "15_9_F_11_T2_2013_03_24.xml"
        if not f.exists():
            pytest.skip("DDR data files not available")
        return f

    def test_parse_returns_dict(self, sample_file):
        result = parse_ddr_file(sample_file)
        assert isinstance(result, dict)
        assert "error" not in result

    def test_parse_well_name(self, sample_file):
        result = parse_ddr_file(sample_file)
        assert result["well"] == "15_9_F_11_T2"
        assert result["date"] == "2013-03-24"

    def test_parse_status(self, sample_file):
        result = parse_ddr_file(sample_file)
        status = result["status"]
        assert status is not None
        assert status["md_m"] == 306.0
        assert status["hole_diameter_in"] == 26.0
        assert "Transferred over" in status["summary_24hr"]

    def test_parse_activities(self, sample_file):
        result = parse_ddr_file(sample_file)
        acts = result["activities"]
        assert len(acts) > 0
        assert all("activity_code" in a for a in acts)
        assert all("comments" in a for a in acts)

    def test_parse_fluids(self, sample_file):
        result = parse_ddr_file(sample_file)
        fluids = result["fluids"]
        assert len(fluids) > 0
        assert fluids[0]["density_gcc"] == 1.35

    def test_parse_surveys(self, sample_file):
        result = parse_ddr_file(sample_file)
        surveys = result["surveys"]
        assert len(surveys) > 0
        assert all(s["md_m"] is not None for s in surveys)

    def test_text_docs_generated(self, sample_file):
        result = parse_ddr_file(sample_file)
        docs = result["text_docs"]
        assert len(docs) > 0
        doc_types = {d["doc_type"] for d in docs}
        assert "summary_24hr" in doc_types
        assert "activity" in doc_types

    def test_sentinel_values_filtered(self, sample_file):
        """Verify -999.99 sentinel values are converted to None."""
        result = parse_ddr_file(sample_file)
        status = result["status"]
        # rop_current is -999.99 in this file, should be None
        assert status["rop_current_m_per_hr"] is None


class TestParseAllDdrs:
    """Test the full DDR parsing pipeline."""

    @pytest.fixture(scope="class")
    def parsed(self):
        if not DDR_DIR.exists():
            pytest.skip("DDR data files not available")
        return parse_all_ddrs()

    def test_all_files_parsed(self, parsed):
        assert len(parsed["statuses"]) == 1759
        assert len(parsed["errors"]) == 0

    def test_activity_count(self, parsed):
        assert len(parsed["activities"]) > 20000

    def test_text_docs_count(self, parsed):
        assert len(parsed["text_docs"]) > 25000

    def test_all_wells_present(self, parsed):
        wells = {s["well"] for s in parsed["statuses"]}
        assert "15_9_F_11_T2" in wells
        assert "15_9_F_1_C" in wells
        assert "15_9_F_11_B" in wells
        assert len(wells) == 26
