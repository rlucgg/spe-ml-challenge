"""CLI entry point for the SPE GCS 2026 ML Challenge drilling agent.

Usage:
    python -m src.main ingest              # Ingest all data into DuckDB + ChromaDB
    python -m src.main ask "question"      # Ask a drilling operations question
    python -m src.main ask "question" --trace  # Ask with full evidence trace
    python -m src.main demo               # Run all 6 demo questions
    python -m src.main demo --save        # Run demo and save to demo_results.md
"""

import logging
import sys
import time
from datetime import datetime

import typer

app = typer.Typer(
    name="volve-agent",
    help="AI Agent for Volve Field Drilling Operational Intelligence",
)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def ingest(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Ingest all Volve data into DuckDB and ChromaDB."""
    setup_logging(verbose)
    logger = logging.getLogger("ingest")

    start = time.time()
    logger.info("Starting data ingestion pipeline...")

    # Step 1: Parse DDR XML files
    logger.info("Step 1/6: Parsing DDR XML files...")
    from src.ingest.parse_ddr import parse_all_ddrs
    parsed_ddrs = parse_all_ddrs()
    logger.info(
        "  Parsed: %d statuses, %d activities, %d text docs",
        len(parsed_ddrs["statuses"]),
        len(parsed_ddrs["activities"]),
        len(parsed_ddrs["text_docs"]),
    )

    # Step 2: Parse well technical data
    logger.info("Step 2/6: Parsing well technical data...")
    from src.ingest.parse_well_tech import parse_well_picks, parse_perforations
    formation_tops = parse_well_picks()
    perforations = parse_perforations()

    # Step 3: Parse production data
    logger.info("Step 3/6: Parsing production data...")
    from src.ingest.parse_production import parse_production_data
    import pandas as pd
    try:
        prod_df = parse_production_data()
    except Exception as e:
        logger.warning("Could not parse production data: %s", e)
        prod_df = pd.DataFrame()

    # Step 4: Parse WITSML real-time data
    logger.info("Step 4/6: Parsing WITSML real-time data...")
    from src.ingest.parse_witsml import parse_all_witsml
    try:
        parsed_witsml = parse_all_witsml()
        logger.info(
            "  Parsed: %d bha_runs, %d mudlog_intervals, %d trajectories, %d messages",
            len(parsed_witsml["bha_runs"]),
            len(parsed_witsml["mudlog_intervals"]),
            len(parsed_witsml["trajectories"]),
            len(parsed_witsml["messages"]),
        )
    except Exception as e:
        logger.warning("Could not parse WITSML data: %s", e)
        parsed_witsml = None

    # Step 5: Build DuckDB database
    logger.info("Step 5/6: Building DuckDB database...")
    from src.ingest.build_database import build_database
    db_path = build_database(
        parsed_ddrs, formation_tops, perforations, prod_df, parsed_witsml
    )
    logger.info("Database built at %s", db_path)

    # Step 6: Build ChromaDB vector store
    logger.info("Step 6/6: Building ChromaDB vector store...")
    import os
    if os.getenv("OPENAI_API_KEY"):
        from src.ingest.build_vectorstore import build_vectorstore
        doc_count = build_vectorstore(parsed_ddrs["text_docs"])
        logger.info("Vector store built with %d documents", doc_count)
    else:
        logger.warning(
            "OPENAI_API_KEY not set — skipping vector store build. "
            "Set it in .env or environment and re-run 'python -m src.main ingest'."
        )

    elapsed = time.time() - start
    logger.info("Ingestion complete in %.1f seconds", elapsed)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Drilling operations question"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    trace: bool = typer.Option(False, "--trace", "-t",
                                help="Show full evidence trace with tool calls"),
) -> None:
    """Ask a drilling operations question about the Volve dataset."""
    setup_logging(verbose)

    from src.agent.orchestrator import ask_question
    from src.agent.output_formatter import format_answer

    answer = ask_question(question, verbose=verbose, trace=trace)
    formatted = format_answer(answer, question)
    print(formatted)


@app.command()
def demo(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    save: bool = typer.Option(False, "--save", "-s",
                               help="Save results to demo_results.md"),
) -> None:
    """Run all 6 demo questions to showcase the agent."""
    setup_logging(verbose)

    from src.agent.orchestrator import ask_question
    from src.agent.output_formatter import format_answer, validate_answer
    from src.agent.prompts import DEMO_QUESTIONS

    header = (
        "# SPE GCS 2026 ML Challenge — Demo Results\n\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )

    print("\n" + "=" * 70)
    print("SPE GCS 2026 ML Challenge — Demo Run")
    print(f"Running {len(DEMO_QUESTIONS)} demonstration questions"
          f"{' (saving to demo_results.md)' if save else ''}...")
    print("=" * 70 + "\n")

    results = []

    for i, question in enumerate(DEMO_QUESTIONS):
        print(f"\n{'#' * 70}")
        print(f"# Demo Question {i + 1} of {len(DEMO_QUESTIONS)}")
        print(f"{'#' * 70}")

        start = time.time()
        answer = ask_question(question, verbose=verbose, trace=save)
        elapsed = time.time() - start

        formatted = format_answer(answer, question)
        print(formatted)
        print(f"\n[Answered in {elapsed:.1f}s]\n")

        validation = validate_answer(answer)
        results.append({
            "num": i + 1,
            "question": question,
            "answer": answer,
            "formatted": formatted,
            "elapsed": elapsed,
            "confidence": _extract_confidence(answer),
            "valid": validation["valid"],
            "warnings": validation["warnings"],
        })

    if save:
        _save_demo_results(header, results)


def _extract_confidence(answer: str) -> str:
    """Extract confidence level from answer text."""
    import re
    match = re.search(r"\b(HIGH|MEDIUM|LOW)\b", answer, re.IGNORECASE)
    return match.group(0).upper() if match else "N/A"


def _save_demo_results(header: str, results: list[dict]) -> None:
    """Save demo results to demo_results.md."""
    lines = [header]

    # Summary table
    lines.append("## Summary\n")
    lines.append("| # | Question | Confidence | Time | Format OK |")
    lines.append("|---|----------|-----------|------|-----------|")
    for r in results:
        q_short = r["question"][:60] + "..." if len(r["question"]) > 60 else r["question"]
        ok = "Yes" if r["valid"] else f"No ({len(r['warnings'])} warnings)"
        lines.append(f"| {r['num']} | {q_short} | {r['confidence']} | {r['elapsed']:.1f}s | {ok} |")
    lines.append("\n---\n")

    # Full answers
    for r in results:
        lines.append(f"## Question {r['num']}\n")
        lines.append(f"**Q:** {r['question']}\n")
        lines.append(r["answer"])
        lines.append(f"\n*Answered in {r['elapsed']:.1f}s*\n")
        lines.append("\n---\n")

    with open("demo_results.md", "w") as f:
        f.write("\n".join(lines))

    print(f"\nDemo results saved to demo_results.md")


if __name__ == "__main__":
    app()
