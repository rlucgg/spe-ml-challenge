"""Batch runner for the Volve stress-test question set."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from src.agent.orchestrator import ask_question
from src.agent.output_formatter import validate_answer
from src.analysis.stress_test_questions_set_b import QUESTIONS


def _build_markdown(results: list[dict], label: str) -> str:
    """Render batch results to markdown."""
    created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# Stress Test Results ({label})",
        "",
        f"Generated: {created}",
        "",
        f"Questions run: {len(results)}",
        "",
    ]

    for item in results:
        lines.extend(
            [
                f"## Question {item['number']}",
                "",
                f"Category: {item['category']}",
                "",
                f"Q: {item['prompt']}",
                "",
                f"Elapsed: {item['elapsed_s']:.1f}s",
                "",
                item["answer"],
                "",
                "---",
                "",
            ]
        )

    return "\n".join(lines)


def _build_summary(results: list[dict]) -> dict:
    """Compute lightweight batch summary stats."""
    validation_counter = Counter()
    section_warnings = Counter()

    for item in results:
        validation = item["validation"]
        if validation["valid"]:
            validation_counter["valid"] += 1
        else:
            validation_counter["invalid"] += 1
        if validation["has_measurement"]:
            validation_counter["with_measurement"] += 1
        if validation["has_ddr_quote"]:
            validation_counter["with_ddr_quote"] += 1
        for warning in validation["warnings"]:
            section_warnings[warning] += 1

    return {
        "num_questions": len(results),
        "validation_counts": dict(validation_counter),
        "warning_counts": dict(section_warnings),
    }


def run_batch(
    output_json: Path,
    output_md: Path,
    start: int,
    end: int,
    label: str,
) -> None:
    """Run the stress-test questions and write artifacts."""
    selected = [q for q in QUESTIONS if start <= q.number <= end]
    results: list[dict] = []

    for q in selected:
        print(f"[Q{q.number:02d}] {q.category}")
        t0 = time.time()
        answer = ask_question(q.prompt, verbose=False, trace=True)
        elapsed = time.time() - t0
        validation = validate_answer(answer)

        result = {
            "number": q.number,
            "category": q.category,
            "prompt": q.prompt,
            "elapsed_s": elapsed,
            "answer": answer,
            "validation": validation,
        }
        results.append(result)

        status = "valid" if validation["valid"] else "needs_review"
        print(f"  -> {status} in {elapsed:.1f}s")

        payload = {
            "label": label,
            "generated_at": datetime.now().isoformat(),
            "summary": _build_summary(results),
            "results": results,
        }
        output_json.write_text(json.dumps(payload, indent=2))
        output_md.write_text(_build_markdown(results, label))


def main() -> None:
    """Parse args and execute the batch run."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", default="stress_test_results.json")
    parser.add_argument("--output-md", default="stress_test_results.md")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=50)
    parser.add_argument("--label", default="baseline")
    args = parser.parse_args()

    run_batch(
        output_json=Path(args.output_json),
        output_md=Path(args.output_md),
        start=args.start,
        end=args.end,
        label=args.label,
    )


if __name__ == "__main__":
    main()
