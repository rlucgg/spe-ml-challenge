# CLAUDE.md — SPE GCS 2026 ML Challenge

## Project Overview

This is the SPE GCS 2026 ML Challenge: "Building an Agentic AI System for Operational Intelligence." The task is to build an AI agent that reads drilling data and daily drilling reports from the Equinor Volve Field dataset, reasons about them, and answers operational questions with clear evidence-based reasoning.

**DEADLINE: March 22, 2026, 11:59 PM**

The full specification is in `spec.md`. Read it thoroughly before starting.

## Repository Layout

```
spe-ml-challenge/
├── CLAUDE.md               ← You are here
├── spec.md                 ← Detailed architecture and implementation plan
├── .googledrive/           ← Raw Volve dataset (gitignored, DO NOT MODIFY)
│   ├── Problem Statement_ML Challenge_2026.pdf
│   ├── Kickoff_Recording_ML Challenge_2026.mp4
│   └── Volve Data/
│       ├── Well_technical_data/Daily Drilling Report - XML Version/  ← 1,759 DDR XMLs
│       ├── WITSML Realtime drilling data/                            ← Real-time drilling
│       ├── Production_data/Volve production data.xlsx
│       ├── Well_logs/ and Well_logs_pr_WELL/
│       ├── Reports/
│       └── Geophysical_Interpretations/
├── src/                    ← All source code goes here
├── data/processed/         ← DuckDB + ChromaDB (gitignored)
├── presentation/           ← 5-min slide deck
└── tests/
```

## Critical Context

### What the Judges Want
- Quality of REASONING (not just correct answers)
- Evidence from BOTH drilling data AND daily reports for every answer
- Consistency across answers
- Clear assumptions and uncertainty handling
- Transparency and reproducibility
- "Complexity alone will not be rewarded"

### What Judges Will Do
- Clone the repo
- Set their own `OPENAI_API_KEY` env variable
- Run `pip install -r requirements.txt`
- Run ingestion: `python -m src.main ingest`
- Ask questions: `python -m src.main ask "your question here"`
- Evaluate answer quality, evidence, reasoning

## Key Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Then add OPENAI_API_KEY

# Ingest data (run once, ~3 min)
python -m src.main ingest

# Ask a question
python -m src.main ask "Identify the major drilling phases for well 15/9-F-11 T2"

# Run all demo questions
python -m src.main demo

# Run tests (always run before committing)
python -m pytest tests/ -v
```

## Data Details You Must Know

### DDR XML Structure (MOST IMPORTANT DATA SOURCE)
Location: `.googledrive/Volve Data/Well_technical_data/Daily Drilling Report - XML Version/`
Files: 1,759 XML files, named `{WELL}_{YYYY}_{MM}_{DD}.xml`
Namespace: `http://www.witsml.org/schemas/1series` with prefix `witsml:`
Schema version: WITSML 1.4.0.0

Key XML paths within `<witsml:drillReport>`:
- `witsml:statusInfo/witsml:md` — current measured depth (meters)
- `witsml:statusInfo/witsml:tvd` — true vertical depth (meters)
- `witsml:statusInfo/witsml:diaHole` — hole diameter (inches)
- `witsml:statusInfo/witsml:sum24Hr` — 24-hour narrative summary (FREE TEXT)
- `witsml:statusInfo/witsml:forecast24Hr` — next-day forecast (FREE TEXT)
- `witsml:activity/witsml:dTimStart` + `dTimEnd` — activity time window
- `witsml:activity/witsml:md` — depth at activity
- `witsml:activity/witsml:proprietaryCode` — activity classification
  - Values: "drilling -- drill", "drilling -- trip", "cementing -- cement",
    "interruption -- repair", "interruption -- waiting on weather",
    "well_control -- kick", "equipment -- rig", etc.
- `witsml:activity/witsml:state` — "ok" or "problem"
- `witsml:activity/witsml:stateDetailActivity` — "success", "equipment failure", "mud loss"
- `witsml:activity/witsml:comments` — FREE TEXT detailed operational description
- `witsml:fluid/witsml:type` — mud type
- `witsml:fluid/witsml:density` — mud weight (g/cm3)
- `witsml:fluid/witsml:pv` — plastic viscosity (mPa.s)
- `witsml:fluid/witsml:yp` — yield point (Pa)

Wells with DDR data (26 wellbore sections across 15 main wells):
15_9_19_A, 15_9_19_B, 15_9_19_BT2, 15_9_19_S, 15_9_19_ST2,
15_9_F_1, 15_9_F_1_A, 15_9_F_1_B, 15_9_F_1_C,
15_9_F_4, 15_9_F_5, 15_9_F_7, 15_9_F_9, 15_9_F_9_A,
15_9_F_10, 15_9_F_11, 15_9_F_11_A, 15_9_F_11_B, 15_9_F_11_T2,
15_9_F_12, 15_9_F_14,
15_9_F_15, 15_9_F_15_A, 15_9_F_15_B, 15_9_F_15_C, 15_9_F_15_D

### WITSML Real-Time Drilling Data
Location: `.googledrive/Volve Data/WITSML Realtime drilling data/`
Format: WITSML 1.4.1.1 XML
Best wells: Norway-Statoil-NO 15/9-F-1 C (6,985 files), F-11 (4,516), F-15 (4,029)

Data types per well:
- `log/` — depth/time indexed curves (ROP, WOB, RPM, torque, pressure, flow)
- `mudLog/` — drilling params + gas detection + lithology (MOST USEFUL)
- `message/` — operational event logs
- `bhaRun/` — BHA run info with operating parameters
- `trajectory/` — well path surveys
- `tubular/` — pipe configurations
- `wbGeometry/` — wellbore geometry

NOTE: WITSML log files can be VERY LARGE (hundreds of MB). Parse selectively.
Focus on mudLog and bhaRun first — they're smaller and more information-dense.

### Production Data
Location: `.googledrive/Volve Data/Production_data/Volve production data.xlsx`
Sheet: "Daily Production Data" — 15,635 rows, 24 columns
Wells: F-1C, F-11, F-12, F-14, F-15D, F-4, F-5
Date range: July 2013 to April 2016

### Well Technical Data
Location: `.googledrive/Volve Data/Well_technical_data/`
- `WellWellbore/` — survey data (MD, TVD, inclination, azimuth)
- `EDM.XML/` — casing specs, materials, stress calculations

### Geophysical Interpretations
Location: `.googledrive/Volve Data/Geophysical_Interpretations/`
- `Wells/Well_picks_Volve_v1.dat` — formation tops (557 lines)
- `Wells/Well_perforations_Volve.dat` — perforation intervals (49 lines)

## Implementation Status

All core phases are implemented and tested:

1. **DDR XML parsing** — All 1,759 files parsed → 23,447 activities, 26,965 text docs, zero errors
2. **WITSML real-time data** — 161 BHA runs, 2,882 mudlog intervals (ROP/WOB/RPM/lithology), 4,217 trajectory stations, 11,134 messages
3. **Vector store** — 26,965 DDR text documents embedded in ChromaDB (text-embedding-3-small)
4. **Agent tools** — 9 tools: query_data, search_reports, well_overview, phase_detection, efficiency_metrics, compare_wells, bha_analysis, issue_detection, formation_context
5. **Orchestrator** — GPT-5.4 mini agent with tool calling via OpenAI SDK (max 10 rounds)
6. **CLI** — `python -m src.main ingest|ask|demo`
7. **Tests** — 86 tests across 4 test files, all passing
8. **Presentation** — 8 slides in `presentation/slides.pptx`

### DuckDB Tables (12 total)
DDR: `ddr_status`, `ddr_activities`, `ddr_fluids`, `ddr_surveys`, `wellbore_info`
WITSML: `witsml_bha_runs`, `witsml_mudlog`, `witsml_trajectory`, `witsml_messages`
Other: `formation_tops`, `perforations`, `production`

## Technology Stack

- Python 3.10+
- openai (SDK for GPT-5.4 mini tool calling)
- duckdb (in-process analytical SQL)
- chromadb (vector store for text search)
- lxml (XML parsing)
- pandas, numpy (data processing)
- openpyxl (Excel reading)
- matplotlib, plotly (visualization)
- typer (CLI framework)
- python-dotenv (env variable loading)

DO NOT use LangChain, LlamaIndex, or other heavy frameworks. Keep it simple.

## Style & Quality Standards

- Type hints on all functions
- Docstrings on all public functions
- Logging via `logging` module (not print statements)
- All config via environment variables or CLI args
- No hardcoded file paths — use pathlib with configurable base directory
- Error handling: graceful failures with informative messages
- Each tool function should be independently testable

## Agent Output Format

For EVERY question, the agent MUST produce this structure:

```
## Answer
[Clear, concise answer to the question]

## Evidence from Drilling Data
[Specific values, timestamps, measurements with sources]

## Evidence from Daily Reports
[Direct quotes from DDRs with well name and date]

## Reasoning
[Step-by-step explanation connecting evidence to conclusion]

## Assumptions
[What was assumed and why]

## Confidence & Uncertainty
[High/Medium/Low with justification; what could change the conclusion]
```

## Well Naming Convention Mapping

DDR files use underscores: `15_9_F_11_T2`
WITSML uses slash notation: `NO 15/9-F-11`
Production data uses: `15/9-F-11`

Build a mapping utility that normalizes well names across data sources.

## Demo Questions for Testing

Use these to validate the system works end-to-end:

1. "Identify and label the major drilling phases for well 15/9-F-11 T2, including the evidence used for each phase."
2. "Distinguish between productive and non-productive drilling time for well 15/9-F-11, and justify the criteria used."
3. "Determine which hole section appears easiest to drill and which appears most challenging for well 15/9-F-11, with supporting evidence."
4. "Identify the most effective drilling configuration or BHA run for well 15/9-F-11 and explain the context."
5. "Identify key operational issues encountered while drilling 15/9-F-11 and propose likely contributing factors."
6. "Compare the drilling phase distribution of 15/9-F-11 with 15/9-F-1 C and explain key differences."

## Gotchas & Warnings

- DDR XML uses namespace `witsml:` — you MUST handle this in lxml parsing
- Some DDR fields use sentinel value `-999.99` for missing data — filter these out
- WITSML log files can be hundreds of MB — do NOT try to load them all into memory
- Well F-11 has sections: main (17 DDRs), T2 (53), A (14), B (90) — these are DIFFERENT wellbores
- Date gaps in DDRs are normal (weekends, completion phases)
- The `proprietaryCode` field in DDR activities is the KEY for phase classification
- ChromaDB embeddings need the OpenAI API key too (for text-embedding-3-small)
- DuckDB file goes in `data/processed/volve.duckdb` — gitignore it
- The `.googledrive/` folder is gitignored and must exist locally with the Volve dataset

## Submission Checklist

- [x] README.md with clear setup instructions
- [x] requirements.txt with pinned versions
- [x] .env.example with OPENAI_API_KEY placeholder
- [x] .gitignore excludes .googledrive/, data/processed/, .env, __pycache__/
- [x] `python -m src.main ingest` works end-to-end
- [x] `python -m src.main ask "question"` produces structured, evidence-backed answers
- [x] `python -m src.main demo` runs all 6 demo questions
- [x] All 6 question categories produce quality answers
- [x] 86 unit tests passing (`python -m pytest tests/ -v`)
- [x] No API keys in the code
- [x] Presentation slides (8 slides in `presentation/slides.pptx`)
- [ ] svpoludasu@gmail.com added as GitHub collaborator
