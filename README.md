# SPE GCS 2026 ML Challenge — Agentic AI for Drilling Operational Intelligence

An AI agent that reads drilling data and daily reports from the Equinor Volve Field dataset, reasons about them, and answers operational questions with clear evidence-based reasoning.

## Quick Start

### 1. Prerequisites
- Python 3.10+
- OpenAI API key

### 2. Setup

```bash
# Clone the repository
git clone <repo-url>
cd spe-ml-challenge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Data Setup

Place the Volve dataset in `.googledrive/Volve Data/` at the project root. The directory should contain:
- `Well_technical_data/Daily Drilling Report - XML Version/` (1,759 DDR XML files)
- `WITSML Realtime drilling data/` (real-time drilling data for key wells)
- `Production_data/Volve production data.xlsx`
- `Geophysical_Interpretations/Wells/` (well picks and perforations)

### 4. Ingest Data

```bash
python -m src.main ingest
```

This parses all data sources into:
- **DuckDB** database (`data/processed/volve.duckdb`) — 12 tables for structured queries
- **ChromaDB** vector store (`data/processed/vectorstore/`) — 26,965 documents for semantic search

### 5. Ask Questions

```bash
# Standard question
python -m src.main ask "Identify the major drilling phases for well 15/9-F-11 T2"

# With full evidence trace (shows every tool call, data source, and retrieval time)
python -m src.main ask "Identify the major drilling phases for well 15/9-F-11 T2" --trace
```

### 6. Run Demo

```bash
# Run all 6 demo questions (print to stdout)
python -m src.main demo

# Run all 6 demo questions and save to demo_results.md with summary table
python -m src.main demo --save
```

## Architecture

```
User Question
     |
     v
GPT-5.4 mini Agent (tool calling, max 10 rounds, retry with backoff)
     |
     |-- query_drilling_data       SQL on 12 DuckDB tables
     |-- search_daily_reports      Semantic search on 26,965 ChromaDB docs
     |-- get_well_overview         Well metadata, sections, formations
     |-- get_drilling_phases       Hole-size + activity-code phase detection
     |-- compute_efficiency        NPT breakdown, ROP by section
     |-- compare_wells             Side-by-side well comparison
     |-- get_bha_configurations    WITSML BHA runs + mudlog drilling params
     |-- identify_issues           Problem detection + root cause correlation
     |-- get_formation_context     Geological context for any depth
     |-- get_field_benchmarks      Cross-well rankings and field-wide analysis
     |-- get_ddr_narrative         Guaranteed DDR text retrieval by date/depth
     |-- generate_depth_time_plot  Depth-vs-time chart with hole sections
     |
     v
Structured Answer with Evidence (+ optional Evidence Trace)
```

**Every answer includes:**
- Specific data evidence (depths, timestamps, measurements from WITSML mudlog)
- Direct quotes from daily drilling reports with well name and date
- Step-by-step reasoning chain
- Explicit assumptions and confidence level (HIGH/MEDIUM/LOW)

**Evidence Trace mode** (`--trace`): Shows the complete reasoning chain — every tool call, arguments, retrieval time, and data sources used. Maximum transparency for judges.

## Data Sources

| Source | Records | Description |
|--------|---------|-------------|
| DDR XML | 1,759 files | Daily drilling reports: 23,447 activities, fluids, surveys |
| WITSML Real-Time | 14 wells | 2,882 mudlog intervals (ROP/WOB/RPM/lithology), 161 BHA runs, 4,217 trajectory stations, 11,134 operational messages |
| Production | 15,634 rows | Daily well production data (2013-2016) |
| Formation Tops | 409 records | Geological formation boundaries |
| Perforations | 48 records | Perforation interval data |

## Testing

```bash
python -m pytest tests/ -v
```

95 tests covering: well name normalization, DDR parsing, WITSML parsing (unit conversions, deduplication), all 12 agent tools, field benchmarks, tool registry dispatch, output format validation.

## Presentation

10-slide presentation in `presentation/slides.pptx` covering architecture, data integration, tool design, example Q&A, and design decisions. Regenerate with:

```bash
python presentation/create_slides.py
```

## Technology

- **LLM**: OpenAI GPT-5.4 mini with extended reasoning (configurable via `OPENAI_MODEL` env var, falls back to GPT-4o if set)
- **Reasoning**: `reasoning_effort=high` for deep drilling domain analysis (configurable via `REASONING_EFFORT` env var)
- **Vector Store**: ChromaDB with OpenAI text-embedding-3-small (26,965 documents)
- **Database**: DuckDB (12 tables, in-process analytical SQL)
- **XML Parsing**: lxml (WITSML 1.4.0 DDR + WITSML 1.4.1 real-time)
- **No heavy frameworks** — pure OpenAI SDK + DuckDB + ChromaDB
