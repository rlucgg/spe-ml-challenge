# SPE GCS 2026 ML Challenge — Solution Specification

## Building an Agentic AI System for Operational Intelligence

**Author:** Rong Lu | **Date:** March 20, 2026 | **Deadline:** March 22, 2026, 11:59 PM

---

## 1. Challenge Summary

Build an intelligent AI agent that reads drilling data and daily reports from the Equinor Volve Field dataset, reasons about them, and answers operational questions in a clear, evidence-based way. The goal is NOT prediction — it is to explain what happened, why it happened, and what the potential next steps are.

### Evaluation Criteria (from problem statement + webinar + emails)
- **Quality of reasoning** (most important — emphasized repeatedly)
- Correct and relevant use of evidence
- Consistency across answers
- Clarity of assumptions
- Handling of uncertainty
- Practical relevance of insights
- Transparency, traceability, reproducibility
- **"Complexity alone will not be rewarded"**

### Submission Requirements
- Code on GitHub (add `svpoludasu@gmail.com` as collaborator)
- Judges use their own API keys — do NOT embed credentials
- 5-minute max presentation (voiceover walkthrough of slides is sufficient)
- Must be reproducible

---

## 2. Question Categories the System Must Answer

### Category 1: Drilling Phase Identification & Validation
- Identify and label major drilling phases for a given well over a selected interval
- Detect significant operational or phase transitions
- Assess alignment between inferred phases and daily drilling reports
- Identify periods of ambiguity and sources of uncertainty

### Category 2: Time & Efficiency Analysis
- Distinguish productive vs. non-productive drilling time (with justified criteria)
- Define and evaluate drilling efficiency over time
- Compare drilling efficiency between wells
- Evaluate whether higher drilling speed correlates with stability or risk

### Category 3: Section & ROP Performance
- Determine which hole sections are easiest/most challenging to drill
- Analyze ROP variation across sections with notable trends
- Identify periods of exceptional drilling performance

### Category 4: Configuration & BHA Effectiveness
- Identify the most effective drilling configuration or BHA run
- Assess whether configuration changes coincide with performance changes
- Evaluate configuration effectiveness by hole section
- Identify robust vs. underperforming configurations

### Category 5: Operational Issues & Root Causes
- Identify key operational issues during drilling
- Propose contributing factors or root causes
- Analyze issue persistence, resolution, or recurrence
- Highlight conflicting interpretations between data and reports

### Category 6: Synthesis & Recommendations
- Compare drilling phase distributions between wells
- Describe remaining uncertainties
- Determine which operational teams should be notified
- Produce a shift handover summary
- Extract lessons learned for future wells
- Recommend drilling configurations for similar conditions

---

## 3. Dataset Inventory

### 3.1 Daily Drilling Reports (DDR) — THE CORE NLP DATA
- **Location:** `.googledrive/Volve Data/Well_technical_data/Daily Drilling Report - XML Version/`
- **Format:** WITSML 1.4.0.0 XML (also available as HTML and PDF)
- **Count:** 1,759 XML files across 15 wells (26 wellbore sections)
- **Date Range:** 1980-01-01 to 2016-10-24

**Key XML elements per DDR:**
- `<statusInfo>`: MD, TVD, hole diameter, 24hr summary, 24hr forecast
- `<activity>`: timestamped activities with proprietaryCode (drilling, trip, cementing, well_control, equipment, interruption), state (ok/problem), stateDetailActivity (success/equipment failure/mud loss), free-text comments
- `<fluid>`: mud type, density, viscosity (PV, YP), mud class
- `<porePressure>`: EMW readings
- `<gasReadingInfo>`: gas composition (C1-C5)
- `<surveyStation>`: MD, TVD, inclination, azimuth
- `<lithShowInfo>`: rock type and depth intervals

**Wells with most DDR coverage:**
| Well Section | DDR Count | Date Range |
|---|---|---|
| 15_9_F_12 | 165 | 2007-06 to 2016-10 |
| 15_9_F_14 | 134 | 2007-11 to 2016-10 |
| 15_9_F_4 | 130 | 2007-06 to 2016-10 |
| 15_9_F_5 | 103 | 2007-11 to 2016-10 |
| 15_9_F_1_C | 98 | various |
| 15_9_F_15_D | 99 | various |
| 15_9_F_11_B | 90 | 2013-05 to 2016-10 |
| 15_9_F_11_T2 | 53 | 2013-03 to 2013-05 |

**File naming convention:** `{WELL}_{YYYY}_{MM}_{DD}.xml`

### 3.2 WITSML Real-Time Drilling Data
- **Location:** `.googledrive/Volve Data/WITSML Realtime drilling data/`
- **Format:** WITSML 1.4.1.1 XML
- **Wells:** 26 well directories
- **Data types per well:**
  - `log/` — Real-time drilling measurements (depth or datetime indexed): ROP, WOB, RPM, torque, pump pressure, flow rate, temperatures
  - `message/` — Operational event logs with timestamps
  - `mudLog/` — Drilling parameters + gas detection + lithology
  - `trajectory/` — Well path (MD, TVD, inclination, azimuth)
  - `tubular/` — Pipe and tool configurations
  - `bhaRun/` — BHA run information with operating parameters
  - `wbGeometry/` — Wellbore geometry and casing
  - `rig/` — Rig configuration metadata

**Best wells for real-time data (Tier 1):**
- Norway-Statoil-NO 15/9-F-1 C (6,985 files)
- Norway-Statoil-NO 15/9-F-11 (4,516 files)
- Norway-Statoil-NO 15/9-F-15 (4,029 files)

### 3.3 Production Data
- **Location:** `.googledrive/Volve Data/Production_data/Volve production data.xlsx`
- **Wells:** 7 (F-1C, F-11, F-12, F-14, F-15D, F-4, F-5)
- **Date Range:** July 2013 to April 2016
- **Measurements:** On-stream hours, downhole pressure/temp, bore oil/gas/water volumes, choke size, wellhead P/T
- **Sheets:** Daily (15,635 rows) + Monthly (528 rows)

### 3.4 Well Technical Data
- **Location:** `.googledrive/Volve Data/Well_technical_data/`
- **Content:** Well surveys, EDM database (casing specs, materials, stress), wellbore geometry
- **16 main wells + relief well locations**

### 3.5 Well Logs
- **Location:** `.googledrive/Volve Data/Well_logs/` and `Well_logs_pr_WELL/`
- **Formats:** LAS (301 files), DLIS (607 files), SEGY (121 files)
- **Log types:** Mud logging, LWD/EWL, pressure tests, composite, petrophysical interpretation, core data, biostratigraphy, geochemistry
- **Key curves:** GR, CALI, DEN, NEU, AC (sonic), RDEP/RMED (resistivity)

### 3.6 Reports
- **Discovery Report** (194 pages, 174 MB) — Comprehensive field discovery documentation
- **Volve PUD** (53 pages, 4.7 MB) — Plan for Development and Operation

### 3.7 Geophysical Interpretations
- Well picks with formation tops (557 lines)
- Well perforations (49 lines)
- Seismic horizons (TWT and depth domain)
- Fault sticks and polygons

---

## 4. Solution Architecture

### 4.1 Design Philosophy
- **Evidence-first**: Every answer cites specific data points and report excerpts
- **Transparent reasoning**: Show the chain from data → analysis → conclusion
- **Tool-calling agent**: LLM orchestrates specialized tools, not a monolithic pipeline
- **Reproducible**: Single `python main.py` entry point, judges provide their own API key via env var

### 4.2 System Overview

```
┌──────────────────────────────────────────────────────┐
│                   USER QUERY                          │
│  "Identify drilling phases for F-11 T2 section"      │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│              ORCHESTRATOR AGENT (GPT-4o)              │
│  - Understands the question category                  │
│  - Plans which tools to call and in what order        │
│  - Synthesizes evidence into structured answer        │
│  - Applies domain knowledge (drilling engineering)    │
└──────┬───────┬───────┬───────┬───────┬───────────────┘
       │       │       │       │       │
       ▼       ▼       ▼       ▼       ▼
   ┌───────┬───────┬───────┬───────┬───────┐
   │ Tool  │ Tool  │ Tool  │ Tool  │ Tool  │
   │  1    │  2    │  3    │  4    │  5    │
   └───────┴───────┴───────┴───────┴───────┘
       │       │       │       │       │
       ▼       ▼       ▼       ▼       ▼
┌──────────────────────────────────────────────────────┐
│              DATA LAYER                               │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │  DuckDB     │  │ ChromaDB    │  │ File System  │ │
│  │ (structured │  │ (DDR text   │  │ (raw XML,    │ │
│  │  queries)   │  │  search)    │  │  LAS, etc.)  │ │
│  └─────────────┘  └─────────────┘  └──────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 4.3 Component Details

#### A. Data Ingestion Pipeline (`src/ingest/`)

**Step 1: Parse DDR XML → Structured + Text**
```
Input:  1,759 DDR XML files
Output:
  - ddr_activities table (well, date, start_time, end_time, depth_m, activity_type, state, detail, comments)
  - ddr_status table (well, date, md_m, tvd_m, hole_diameter_in, summary_24hr, forecast_24hr)
  - ddr_fluids table (well, date, mud_type, density_gcc, pv_mPas, yp_Pa)
  - ddr_gas table (well, date, depth_m, methane_ppm, ethane_ppm, ...)
  - ddr_surveys table (well, date, md_m, tvd_m, inclination_deg, azimuth_deg)
  - Text corpus for vector indexing (activity comments + 24hr summaries)
```

**Step 2: Parse WITSML Real-Time Data → Time Series**
```
Input:  Key WITSML log/mudLog/message/bhaRun/trajectory XML files
Output:
  - drilling_params table (well, timestamp, depth_m, rop_m_per_hr, wob_kN, rpm, torque_kNm, pump_pressure_kPa, flow_rate_lpm, hookload_kN)
  - bha_runs table (well, run_number, start_depth_m, end_depth_m, start_time, end_time, bit_type, components)
  - trajectory table (well, md_m, tvd_m, inclination_deg, azimuth_deg)
  - messages table (well, timestamp, depth_m, message_type, text)
```

**Step 3: Parse Production Data**
```
Input:  Volve production data.xlsx
Output: production table (well, date, oil_vol, gas_vol, water_vol, pressure, temperature, choke_size)
```

**Step 4: Parse Well Technical Data**
```
Input:  Survey files, EDM database, well picks
Output:
  - well_metadata table (well, spud_date, completion_date, water_depth, operator, rig)
  - formation_tops table (well, formation_name, md_m, tvd_m)
  - casing_program table (well, section, casing_od_in, shoe_depth_m)
```

**Step 5: Build Vector Store**
```
Input:  DDR text corpus (activity comments + summaries + forecasts)
Output: ChromaDB collection with embeddings (OpenAI text-embedding-3-small)
  - Metadata: well, date, activity_type, depth_m
  - Chunk size: per-activity (natural document boundary)
```

#### B. Agent Tools (`src/tools/`)

| Tool Name | Description | Returns |
|---|---|---|
| `query_drilling_data` | SQL queries on drilling parameters, DDR activities, fluids, gas | Tabular data + summary stats |
| `search_daily_reports` | Semantic search over DDR text corpus | Ranked passages with well/date/depth context |
| `get_well_overview` | Well metadata, sections drilled, date ranges, total depth | Structured well profile |
| `get_drilling_phases` | Algorithm-based phase detection from activity codes + depth progression | Phase labels with time intervals and evidence |
| `compute_efficiency_metrics` | NPT classification, ROP statistics, productive time ratios | Metrics with breakdown |
| `compare_wells` | Side-by-side comparison of any metric between wells | Comparison table + delta analysis |
| `get_bha_configurations` | BHA run details, component lists, operating parameters | Configuration records |
| `identify_operational_issues` | Filter DDR activities with state=problem, extract patterns | Issue timeline with root cause hints |
| `get_formation_context` | Formation tops, lithology, and geological context for a depth | Geological context |
| `generate_visualization` | Create plots (depth vs time, ROP by section, NPT breakdown, etc.) | Matplotlib/Plotly chart saved as image |

#### C. Orchestrator Agent (`src/agent/`)

**LLM:** OpenAI GPT-4o (best balance of reasoning + speed + tool calling)
- Falls back to GPT-4o-mini for simple lookups
- System prompt includes drilling domain knowledge primer
- Tool-calling with structured outputs

**System Prompt Strategy:**
```
You are a senior drilling engineer AI assistant analyzing the Equinor Volve Field dataset.
You have access to tools for querying structured drilling data and searching daily drilling reports.

For EVERY question, you MUST:
1. State your interpretation of the question
2. Plan which data sources to consult
3. Call relevant tools to gather evidence
4. Cross-reference structured data with daily report narratives
5. Synthesize findings with clear reasoning
6. State assumptions and confidence level
7. Provide a structured answer with citations

Output format for each answer:
- ANSWER: Clear, concise answer
- EVIDENCE FROM DATA: Specific values, timestamps, measurements cited
- EVIDENCE FROM REPORTS: Direct quotes from DDRs with dates
- REASONING: Step-by-step explanation of how evidence leads to conclusion
- ASSUMPTIONS: What was assumed and why
- CONFIDENCE: High/Medium/Low with justification
- UNCERTAINTY: What could change the conclusion
```

#### D. Drilling Phase Detection Algorithm (`src/analysis/phase_detection.py`)

Automated phase classification using DDR activity codes:

| Phase | Activity Codes | Data Signals |
|---|---|---|
| Surface Drilling | drilling, large hole diameter (26"-36") | Low depth, high ROP |
| Intermediate Drilling | drilling, medium hole (17.5") | Moderate depth progression |
| Production Drilling | drilling, small hole (12.25"-8.5") | Target depth approach |
| Tripping | trip in/out | No depth change, hookload variations |
| Casing & Cementing | cementing, casing | Specific depth milestones |
| Completion | completion activities | Near TD |
| Well Control | well_control, kick | Pressure anomalies |
| Non-Productive Time | waiting (weather, equipment), repair | No depth progress |
| Logging | logging, wireline | Stationary depth, specific tools |

Algorithm:
1. Parse DDR activity codes → initial phase labels
2. Validate with depth vs. time curve (from drilling_params)
3. Cross-reference with DDR 24hr summaries for confirmation
4. Detect transitions by monitoring phase changes + depth discontinuities
5. Flag ambiguous periods where data and reports conflict

#### E. Efficiency Analysis Module (`src/analysis/efficiency.py`)

**NPT (Non-Productive Time) Classification:**
- From DDR activity codes: `interruption--*`, `waiting--*`, `repair--*`
- From data: periods with zero depth progress but active pumps/rotation
- Categories: Weather, Equipment Failure, Mud Issues, Well Control, Waiting on Orders

**ROP Analysis:**
- Compute ROP per section from depth progression / time
- Normalize by hole diameter and formation
- Statistical comparison across wells (mean, P10, P50, P90)

**Drilling Efficiency Metrics:**
- Productive Time Ratio = (drilling_time) / (total_time)
- Mechanical Specific Energy (MSE) proxy from WOB, RPM, torque, ROP
- Connection time analysis
- Trip speed analysis

---

## 5. Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| Language | Python 3.10+ | Universal, rich ecosystem |
| LLM | OpenAI GPT-4o via API | Best tool-calling, reasoning quality; judges have own keys |
| Embeddings | OpenAI text-embedding-3-small | Cost-effective, excellent retrieval |
| Vector Store | ChromaDB | Lightweight, no server needed, pip install |
| Structured DB | DuckDB | In-process analytical SQL, fast, no server |
| XML Parsing | lxml + custom WITSML parser | Fast, handles namespaces well |
| Data Processing | pandas, numpy | Standard data manipulation |
| Visualization | matplotlib, plotly | Publication-quality charts |
| CLI Interface | Typer or Click | Clean CLI for judges |
| Agent Framework | Custom (openai SDK function calling) | Minimal dependencies, full control, transparent |
| Excel | openpyxl | Read production data XLSX |
| LAS Parsing | lasio | Standard LAS file reader |

### Why NOT LangChain/LlamaIndex?
- Adds complexity without clear benefit for this use case
- Custom tool-calling with OpenAI SDK is simpler, more transparent, more debuggable
- Judges can read the code easily
- "Complexity alone will not be rewarded"

---

## 6. Project Structure

```
spe-ml-challenge/
├── CLAUDE.md                    # Claude Code instructions
├── spec.md                      # This document
├── README.md                    # Setup + usage instructions for judges
├── requirements.txt             # Python dependencies
├── .env.example                 # Template: OPENAI_API_KEY=your-key-here
├── .gitignore                   # .googledrive, .env, __pycache__, data/processed/
│
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entry point: CLI interface
│   │
│   ├── ingest/                  # Data ingestion pipeline
│   │   ├── __init__.py
│   │   ├── parse_ddr.py         # DDR XML → structured tables + text corpus
│   │   ├── parse_witsml.py      # WITSML logs/messages/bhaRun → time series
│   │   ├── parse_production.py  # XLSX → production table
│   │   ├── parse_well_tech.py   # Surveys, EDM, well picks
│   │   ├── build_vectorstore.py # Text → ChromaDB embeddings
│   │   └── build_database.py    # Orchestrate all ingestion → DuckDB + ChromaDB
│   │
│   ├── tools/                   # Agent tools
│   │   ├── __init__.py
│   │   ├── tool_registry.py     # OpenAI function definitions
│   │   ├── query_data.py        # SQL-based data queries
│   │   ├── search_reports.py    # Vector search over DDR text
│   │   ├── well_overview.py     # Well metadata retrieval
│   │   ├── phase_detection.py   # Drilling phase identification
│   │   ├── efficiency_metrics.py# NPT, ROP, efficiency computations
│   │   ├── compare_wells.py     # Cross-well comparisons
│   │   ├── bha_analysis.py      # BHA configuration analysis
│   │   ├── issue_detection.py   # Operational issue identification
│   │   ├── formation_context.py # Geological context
│   │   └── visualize.py         # Chart generation
│   │
│   ├── agent/                   # LLM agent
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # Main agent loop with tool calling
│   │   ├── prompts.py           # System prompts + few-shot examples
│   │   └── output_formatter.py  # Structured answer formatting
│   │
│   └── analysis/                # Standalone analysis modules
│       ├── __init__.py
│       ├── phase_detection.py   # Phase detection algorithm
│       ├── efficiency.py        # Efficiency computation logic
│       ├── rop_analysis.py      # ROP statistics and trends
│       └── npt_classification.py# NPT categorization logic
│
├── data/
│   ├── raw/                     # Symlink to .googledrive/Volve Data/
│   └── processed/               # DuckDB file, ChromaDB directory (gitignored)
│       ├── volve.duckdb
│       └── vectorstore/
│
├── notebooks/                   # Optional exploration notebooks
│   └── exploration.ipynb
│
├── presentation/                # 5-minute presentation
│   └── slides.pptx              # or slides.pdf
│
└── tests/
    ├── test_ingest.py
    ├── test_tools.py
    └── test_agent.py
```

---

## 7. Implementation Plan (Priority Order)

### Phase 1: Data Ingestion (CRITICAL PATH — Do First)
1. **parse_ddr.py** — Parse all 1,759 DDR XML files into structured tables
   - Activity log with timestamps, codes, states, comments
   - Status info (depth, hole size, summaries)
   - Fluid properties, gas readings, surveys
   - This is the HIGHEST VALUE data source
2. **parse_witsml.py** — Parse WITSML data for key wells (F-11, F-1C, F-15)
   - Focus on mudLog (most information-dense), bhaRun, trajectory, messages
   - Log data is huge; parse selectively for drilling-relevant curves
3. **parse_production.py** — Parse XLSX (straightforward)
4. **parse_well_tech.py** — Parse surveys, well picks, formation tops
5. **build_database.py** — Load everything into DuckDB
6. **build_vectorstore.py** — Embed DDR text into ChromaDB

### Phase 2: Agent Tools
7. **query_data.py** — SQL query interface over DuckDB
8. **search_reports.py** — Semantic search over ChromaDB
9. **well_overview.py** — Well metadata lookup
10. **phase_detection.py** — Automated phase classification
11. **efficiency_metrics.py** — NPT and ROP computations
12. **compare_wells.py** — Cross-well comparison
13. **bha_analysis.py** — BHA/configuration analysis
14. **issue_detection.py** — Problem detection from DDR state fields
15. **visualize.py** — Chart generation

### Phase 3: Agent Core
16. **prompts.py** — System prompt with drilling domain knowledge
17. **tool_registry.py** — OpenAI function definitions for all tools
18. **orchestrator.py** — Agent loop: receive question → plan → call tools → synthesize
19. **output_formatter.py** — Format structured answers per problem statement requirements

### Phase 4: CLI & Polish
20. **main.py** — CLI: `python src/main.py ingest` and `python src/main.py ask "question"`
21. **README.md** — Setup instructions for judges
22. **.env.example** — API key template
23. **requirements.txt** — Pin all dependencies

### Phase 5: Presentation
24. **slides.pptx** — 5-minute walkthrough of approach, architecture, sample Q&A

---

## 8. Key Design Decisions

### 8.1 DDR XML is the Primary Data Source
The DDR activity logs contain the richest information: timestamped activities with classification codes, free-text descriptions, mud properties, and depth progression. The agent's ability to search, parse, and reason over DDR text is the #1 differentiator.

### 8.2 Dual Evidence Requirement
Every answer MUST cite evidence from both structured data AND daily reports. The problem statement explicitly asks for this. The agent is prompted to always cross-reference.

### 8.3 Phase Detection is Algorithmic + LLM-Validated
First pass: rule-based phase detection from DDR activity codes and depth curves.
Second pass: LLM validates by reading DDR summaries and checking for consistency.
This hybrid approach is more transparent and reproducible than pure LLM classification.

### 8.4 Focus Wells for Demo
**Primary:** 15/9-F-11 (all sections: main, T2, A, B) — 174 DDRs, rich WITSML data, complete drilling campaign from spud to completion
**Secondary:** 15/9-F-1 C — 98 DDRs, good WITSML data, different drilling campaign for comparison
**Tertiary:** 15/9-F-15 (all sections) — Long operational history

### 8.5 Minimal Dependencies
No LangChain, no complex frameworks. Pure OpenAI SDK + DuckDB + ChromaDB. Judges can `pip install -r requirements.txt` and run immediately.

---

## 9. Sample Agent Interaction

**User Query:** "Identify and label the major drilling phases for well 15/9-F-11 T2, including the evidence used for each phase."

**Agent Plan:**
1. Call `get_well_overview("15_9_F_11_T2")` → Get date range, total depth, sections
2. Call `get_drilling_phases("15_9_F_11_T2")` → Automated phase detection from activity codes
3. Call `query_drilling_data("SELECT date, md_m, activity_type, state FROM ddr_activities WHERE well LIKE '%F_11_T2%' ORDER BY date, start_time")` → Full activity timeline
4. Call `search_daily_reports("drilling phase transition casing cementing", well="15_9_F_11_T2")` → Find report passages describing phase changes
5. Call `query_drilling_data("SELECT date, md_m, tvd_m, hole_diameter_in FROM ddr_status WHERE well LIKE '%F_11_T2%' ORDER BY date")` → Depth progression curve

**Agent Output:**
```
ANSWER: The F-11 T2 section drilling campaign (March 24 - May 15, 2013) comprised
5 major phases: [detailed phase breakdown with date ranges and depths]

EVIDENCE FROM DATA:
- Depth progression: 605m to 4,356m over 52 days
- Activity code distribution: 62% drilling, 15% tripping, 8% cementing, ...
- [specific ROP values per section]

EVIDENCE FROM REPORTS:
- DDR 2013-03-24: "Commenced drilling 17-1/2" hole from 605m..."
- DDR 2013-04-15: "Set 13-3/8" casing at 2,145m. Cemented..."
- [more report citations]

REASONING: [step-by-step explanation]

ASSUMPTIONS: [stated assumptions]

CONFIDENCE: High — phase boundaries clearly marked by casing points and activity code transitions, confirmed by daily report narratives.
```

---

## 10. Risk Mitigation

| Risk | Mitigation |
|---|---|
| WITSML XML parsing complexity | Focus on DDR (cleaner XML); WITSML as supplementary |
| Large data volume (30K+ files) | Parse selectively; focus on 3-4 key wells |
| LLM hallucination | Tool-calling ensures LLM reasons over REAL data; citations required |
| API rate limits | Cache tool results; batch similar queries |
| Judge reproducibility | Clear README, .env.example, pinned deps, `python main.py ingest && python main.py ask` |
| Time constraint (2 days) | Prioritize DDR parsing + core agent; skip nice-to-haves |

---

## 11. What Makes This Solution Win

1. **Evidence-first architecture**: Not just an LLM chatbot — every answer backed by specific data points and report citations
2. **Dual-source cross-referencing**: Structured data AND unstructured reports, as the problem statement demands
3. **Transparent reasoning chain**: The agent shows its work at every step
4. **Domain-appropriate**: Phase detection algorithm uses real drilling engineering concepts (not generic ML)
5. **Reproducible**: Single command setup, judges use their own API keys
6. **Clean, minimal code**: No unnecessary framework complexity — judges can read and understand it
7. **Handles all 6 question categories**: Purpose-built tools for each analysis type
8. **Quantified uncertainty**: Every answer includes confidence level and stated assumptions
