"""Format agent output for display."""

import re


def format_answer(answer: str, question: str) -> str:
    """Format the agent's answer for terminal display.

    Ensures the answer has the required structure and is well-formatted.
    """
    lines = []
    lines.append("=" * 70)
    lines.append(f"QUESTION: {question}")
    lines.append("=" * 70)
    lines.append("")

    # Check if answer already has our expected sections
    expected_sections = [
        "Answer", "Evidence from Drilling Data", "Evidence from Daily Reports",
        "Reasoning", "Assumptions", "Confidence",
    ]

    has_structure = any(
        re.search(rf"##?\s*{section}", answer, re.IGNORECASE)
        for section in expected_sections[:3]
    )

    if has_structure:
        lines.append(answer)
    else:
        # Wrap unstructured answer
        lines.append("## Answer")
        lines.append(answer)

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)
