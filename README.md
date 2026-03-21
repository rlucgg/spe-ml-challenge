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
- `Production_data/Volve production data.xlsx`
- `Geophysical_Interpretations/Wells/` (well picks and perforations)

### 4. Ingest Data

```bash
python -m src.main ingest
```

This parses all DDR XML files, production data, and geological data into:
- **DuckDB** database (`data/processed/volve.duckdb`) — structured queries
- **ChromaDB** vector store (`data/processed/vectorstore/`) — semantic search over report text

### 5. Ask Questions

```bash
python -m src.main ask "Identify the major drilling phases for well 15/9-F-11 T2"
```

### 6. Run Demo

```bash
python -m src.main demo
```

Runs all 6 demonstration questions covering: drilling phases, efficiency, hole section difficulty, BHA effectiveness, operational issues, and cross-well comparison.

## Architecture

```
User Question
     │
     ▼
GPT-4o Agent (tool calling)
     │
     ├─→ query_drilling_data (SQL on DuckDB)
     ├─→ search_daily_reports (semantic search on ChromaDB)
     ├─→ get_well_overview (well metadata)
     ├─→ get_drilling_phases (phase detection algorithm)
     ├─→ compute_efficiency_metrics (NPT, ROP analysis)
     ├─→ compare_wells (cross-well comparison)
     ├─→ get_bha_configurations (BHA/bit analysis)
     └─→ identify_operational_issues (problem detection)
     │
     ▼
Structured Answer with Evidence
```

**Every answer includes:**
- Specific data evidence (depths, timestamps, measurements)
- Direct quotes from daily drilling reports
- Step-by-step reasoning
- Stated assumptions and confidence level

## Data Sources

| Source | Records | Description |
|--------|---------|-------------|
| DDR XML | 1,759 files | Daily drilling reports with activities, fluids, surveys |
| Production | 15,635 rows | Daily well production data (2013-2016) |
| Well Picks | 557 lines | Formation tops across Volve wells |
| Perforations | 49 lines | Perforation interval data |

## Technology

- **LLM**: OpenAI GPT-4o with function calling
- **Vector Store**: ChromaDB with OpenAI embeddings
- **Database**: DuckDB (in-process analytical SQL)
- **XML Parsing**: lxml
- **No heavy frameworks** — pure OpenAI SDK + DuckDB + ChromaDB
