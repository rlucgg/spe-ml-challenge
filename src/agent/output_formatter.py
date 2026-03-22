"""Format and validate agent output for display."""

import re
from typing import Optional


REQUIRED_SECTIONS = [
    "Answer",
    "Evidence from Drilling Data",
    "Evidence from Daily Reports",
    "Reasoning",
    "Assumptions",
    "Confidence",
]


def validate_answer(answer: str) -> dict:
    """Validate that the answer contains all required sections and evidence.

    Returns dict with: valid (bool), missing_sections (list), has_measurement (bool),
    has_ddr_quote (bool), warnings (list).
    """
    warnings = []
    missing = []

    for section in REQUIRED_SECTIONS:
        if not re.search(rf"##?\s*{section}", answer, re.IGNORECASE):
            missing.append(section)

    # Check for at least one specific measurement (number + unit)
    has_measurement = bool(re.search(
        r"\d+(?:\.\d+)?\s*(?:m|m/hr|m/h|kN|kNm|sg|g/cm3|mPa|Pa|ppm|hrs?|days?|%)",
        answer
    ))

    # Check for a DDR quote with date attribution (handles bold markdown format)
    has_ddr_quote = bool(re.search(
        r"DDR.*?(?:15[/_]9|F-\d).*?\d{4}", answer, re.IGNORECASE
    )) or bool(re.search(
        r"(?:DDR|report|daily)\s.*?\d{4}[-/]\d{2}[-/]\d{2}", answer, re.IGNORECASE
    )) or bool(re.search(r'"\*?\*?[A-Z].*?\*?\*?"', answer))

    if missing:
        warnings.append(f"Missing sections: {', '.join(missing)}")
    if not has_measurement:
        warnings.append("No specific measurement with units found")
    if not has_ddr_quote:
        warnings.append("No DDR report quote with date attribution found")

    return {
        "valid": len(missing) == 0,
        "missing_sections": missing,
        "has_measurement": has_measurement,
        "has_ddr_quote": has_ddr_quote,
        "warnings": warnings,
    }


def format_answer(answer: str, question: str) -> str:
    """Format the agent's answer for terminal display.

    Validates structure and adds warnings for missing sections.
    """
    lines = []
    lines.append("=" * 70)
    lines.append(f"QUESTION: {question}")
    lines.append("=" * 70)
    lines.append("")

    # Check structure
    has_structure = any(
        re.search(rf"##?\s*{section}", answer, re.IGNORECASE)
        for section in REQUIRED_SECTIONS[:3]
    )

    if has_structure:
        lines.append(answer)
    else:
        lines.append("## Answer")
        lines.append(answer)

    # Validate and show warnings
    validation = validate_answer(answer)
    if validation["warnings"]:
        lines.append("")
        lines.append("-" * 70)
        lines.append("FORMAT WARNINGS:")
        for w in validation["warnings"]:
            lines.append(f"  - {w}")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)
