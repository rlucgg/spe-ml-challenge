"""Tests for config module: well name normalization and display."""

import pytest
from src.config import normalize_well_name, display_well_name


class TestNormalizeWellName:
    """Test well name normalization across all input formats."""

    def test_ddr_filename_format(self):
        assert normalize_well_name("15_9_F_11_T2") == "15_9_F_11_T2"

    def test_witsml_format_with_no_prefix(self):
        assert normalize_well_name("NO 15/9-F-11 T2") == "15_9_F_11_T2"

    def test_production_format(self):
        assert normalize_well_name("15/9-F-11") == "15_9_F_11"

    def test_slash_format(self):
        assert normalize_well_name("15/9-F-1 C") == "15_9_F_1_C"

    def test_already_normalized(self):
        assert normalize_well_name("15_9_F_11_T2") == "15_9_F_11_T2"

    def test_exploration_well(self):
        assert normalize_well_name("NO 15/9-19 A") == "15_9_19_A"

    def test_collapses_multiple_underscores(self):
        assert normalize_well_name("15/9--F-11") == "15_9_F_11"

    def test_strips_whitespace(self):
        assert normalize_well_name("  NO 15/9-F-11  ") == "15_9_F_11"


class TestDisplayWellName:
    """Test conversion from underscore to display format."""

    def test_f_well_with_sidetrack(self):
        assert display_well_name("15_9_F_11_T2") == "15/9-F-11 T2"

    def test_f_well_no_sidetrack(self):
        assert display_well_name("15_9_F_11") == "15/9-F-11"

    def test_f_well_letter_sidetrack(self):
        assert display_well_name("15_9_F_1_C") == "15/9-F-1 C"

    def test_exploration_well(self):
        assert display_well_name("15_9_19_A") == "15/9-19 A"

    def test_exploration_well_bt2(self):
        assert display_well_name("15_9_19_BT2") == "15/9-19 BT2"

    def test_short_name_passthrough(self):
        assert display_well_name("AB") == "AB"


class TestNormalizeDisplayRoundtrip:
    """Verify that normalize -> display produces expected results."""

    WELL_NAMES = [
        ("NO 15/9-F-11 T2", "15/9-F-11 T2"),
        ("NO 15/9-F-1 C", "15/9-F-1 C"),
        ("15/9-F-11", "15/9-F-11"),
        ("NO 15/9-19 A", "15/9-19 A"),
    ]

    @pytest.mark.parametrize("input_name,expected_display", WELL_NAMES)
    def test_roundtrip(self, input_name, expected_display):
        normalized = normalize_well_name(input_name)
        displayed = display_well_name(normalized)
        assert displayed == expected_display
