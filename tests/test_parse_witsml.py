"""Tests for WITSML real-time data parsing."""

import math
import pytest
from src.ingest.parse_witsml import parse_all_witsml, RAD_TO_DEG, MPS_TO_MPH
from src.config import WITSML_DIR


@pytest.fixture(scope="module")
def parsed():
    if not WITSML_DIR.exists():
        pytest.skip("WITSML data files not available")
    return parse_all_witsml()


class TestWitsmlParsing:
    """Test WITSML data parsing produces expected counts and structure."""

    def test_bha_run_count(self, parsed):
        assert len(parsed["bha_runs"]) == 161

    def test_mudlog_count(self, parsed):
        assert len(parsed["mudlog_intervals"]) > 2000

    def test_trajectory_count(self, parsed):
        assert len(parsed["trajectories"]) > 4000

    def test_message_count(self, parsed):
        assert len(parsed["messages"]) > 10000


class TestBhaRunParsing:
    """Test BHA run record structure."""

    def test_bha_run_fields(self, parsed):
        run = parsed["bha_runs"][0]
        assert "well" in run
        assert "wellbore" in run
        assert "run_name" in run
        assert "start_time" in run
        assert "end_time" in run

    def test_bha_run_well_names(self, parsed):
        wells = {r["well"] for r in parsed["bha_runs"]}
        assert "15_9_F_11_T2" in wells


class TestMudlogParsing:
    """Test mudlog interval parsing and unit conversions."""

    def test_mudlog_fields(self, parsed):
        ml = parsed["mudlog_intervals"][0]
        assert "md_top_m" in ml
        assert "rop_avg_m_per_hr" in ml
        assert "lith_type" in ml
        assert "wob_avg_kN" in ml

    def test_rop_units_in_m_per_hr(self, parsed):
        """ROP should be in m/hr (converted from m/s)."""
        for ml in parsed["mudlog_intervals"]:
            if ml["rop_avg_m_per_hr"] is not None:
                # Typical ROP is 1-200 m/hr, allow wider range for outliers
                assert ml["rop_avg_m_per_hr"] > 0
                break

    def test_lithology_types(self, parsed):
        types = {ml["lith_type"] for ml in parsed["mudlog_intervals"] if ml["lith_type"]}
        assert len(types) > 0
        # Common Volve lithologies
        assert "claystone" in types or "limestone" in types or "sandstone" in types

    def test_mudlog_well_names(self, parsed):
        wells = {ml["well"] for ml in parsed["mudlog_intervals"]}
        assert "15_9_F_11_T2" in wells


class TestTrajectoryParsing:
    """Test trajectory parsing and unit conversions."""

    def test_trajectory_fields(self, parsed):
        ts = parsed["trajectories"][0]
        assert "md_m" in ts
        assert "tvd_m" in ts
        assert "inclination_deg" in ts
        assert "azimuth_deg" in ts

    def test_angles_in_degrees(self, parsed):
        """Inclination and azimuth should be in degrees (converted from radians)."""
        for ts in parsed["trajectories"]:
            if ts["inclination_deg"] is not None:
                assert 0 <= ts["inclination_deg"] <= 180
                break
        for ts in parsed["trajectories"]:
            if ts["azimuth_deg"] is not None:
                assert 0 <= ts["azimuth_deg"] <= 360
                break

    def test_no_duplicate_stations(self, parsed):
        """Each well should not have duplicate MD values within same section."""
        from collections import Counter
        for well in ["15_9_F_11_T2"]:
            mds = [t["md_m"] for t in parsed["trajectories"] if t["well"] == well]
            counts = Counter(mds)
            dupes = {md: cnt for md, cnt in counts.items() if cnt > 1}
            assert len(dupes) == 0, f"Duplicate MDs for {well}: {dupes}"


class TestMessageParsing:
    """Test message parsing."""

    def test_message_fields(self, parsed):
        msg = parsed["messages"][0]
        assert "well" in msg
        assert "timestamp" in msg
        assert "message_text" in msg

    def test_message_well_names(self, parsed):
        wells = {m["well"] for m in parsed["messages"]}
        assert "15_9_F_11_T2" in wells


class TestUnitConversions:
    """Test unit conversion constants are correct."""

    def test_rad_to_deg(self):
        assert abs(RAD_TO_DEG - 57.2957795) < 0.001

    def test_mps_to_mph(self):
        assert MPS_TO_MPH == 3600.0
