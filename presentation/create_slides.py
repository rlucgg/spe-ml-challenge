"""Generate presentation slides for SPE GCS 2026 ML Challenge."""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR


def _add_title_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    # Title
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(1.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Agentic AI for Drilling\nOperational Intelligence"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0x1A, 0x47, 0x7A)
    p.alignment = PP_ALIGN.CENTER
    # Subtitle
    txBox2 = slide.shapes.add_textbox(Inches(0.8), Inches(3.2), Inches(8.4), Inches(1.5))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.text = "SPE GCS 2026 ML Challenge\nAnalyzing the Equinor Volve Field Dataset"
    p2.font.size = Pt(20)
    p2.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    p2.alignment = PP_ALIGN.CENTER
    # Author
    txBox3 = slide.shapes.add_textbox(Inches(0.8), Inches(5.0), Inches(8.4), Inches(0.8))
    tf3 = txBox3.text_frame
    p3 = tf3.paragraphs[0]
    p3.text = "Rong Lu | March 2026"
    p3.font.size = Pt(16)
    p3.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
    p3.alignment = PP_ALIGN.CENTER


def _add_content_slide(prs, title, bullets, subtitle=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    # Title bar
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9.0), Inches(0.8))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0x1A, 0x47, 0x7A)
    # Subtitle
    if subtitle:
        txBox_s = slide.shapes.add_textbox(Inches(0.5), Inches(1.0), Inches(9.0), Inches(0.5))
        tf_s = txBox_s.text_frame
        p_s = tf_s.paragraphs[0]
        p_s.text = subtitle
        p_s.font.size = Pt(14)
        p_s.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
        p_s.font.italic = True
    # Content
    y_start = 1.6 if subtitle else 1.3
    txBox2 = slide.shapes.add_textbox(Inches(0.7), Inches(y_start), Inches(8.6), Inches(5.5 - y_start))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf2.paragraphs[0]
        else:
            p = tf2.add_paragraph()
        if bullet.startswith("  "):
            p.text = bullet.strip()
            p.font.size = Pt(14)
            p.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            p.level = 1
        else:
            p.text = bullet
            p.font.size = Pt(16)
            p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            p.level = 0
        p.space_after = Pt(6)


def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(5.625)

    # Slide 1: Title
    _add_title_slide(prs)

    # Slide 2: Challenge Overview
    _add_content_slide(prs, "The Challenge", [
        "Build an AI agent that analyzes the Equinor Volve Field drilling dataset",
        "Answer operational questions with evidence-based reasoning",
        "6 question categories the system must handle:",
        "  1. Drilling Phase Identification & Validation",
        "  2. Time & Efficiency Analysis (NPT, productive time)",
        "  3. Section & ROP Performance",
        "  4. BHA Configuration Effectiveness",
        "  5. Operational Issues & Root Causes",
        "  6. Synthesis, Comparison & Recommendations",
        "Judges evaluate: quality of REASONING, not just correct answers",
    ], subtitle="Goal: Explain what happened, why, and what to do next")

    # Slide 3: Architecture
    _add_content_slide(prs, "System Architecture", [
        "User Question  -->  GPT-4o Agent (tool calling, max 10 rounds)",
        "",
        "9 Agent Tools:",
        "  query_drilling_data    SQL on 12 DuckDB tables",
        "  search_daily_reports   Semantic search on 26,965 ChromaDB docs",
        "  get_well_overview      Well metadata, sections, formations",
        "  get_drilling_phases    Hole-size + activity-code phase detection",
        "  compute_efficiency     NPT breakdown, ROP by section",
        "  compare_wells          Side-by-side well comparison",
        "  get_bha_configs        WITSML BHA runs + mudlog drilling params",
        "  identify_issues        Problem detection + root cause analysis",
        "  get_formation_context  Geological context for any depth",
    ], subtitle="Pure OpenAI SDK + DuckDB + ChromaDB  |  No LangChain, no framework bloat")

    # Slide 4: Data Coverage
    _add_content_slide(prs, "Data Integration", [
        "DDR Daily Drilling Reports: 1,759 XML files parsed (zero errors)",
        "  23,447 activities | 2,271 fluid records | 1,726 survey stations",
        "",
        "WITSML Real-Time Data: 33 wellbore sections across 22 wells",
        "  2,882 mudlog intervals with actual ROP, WOB, torque, RPM, lithology",
        "  161 BHA runs | 4,217 trajectory stations | 11,134 messages",
        "",
        "Additional: 15,634 production records | 409 formation tops | 48 perforations",
        "",
        "Vector Store: 26,965 DDR text documents indexed in ChromaDB",
        "Database: 12 DuckDB tables | Total ingestion: ~3 minutes",
    ], subtitle="12 DuckDB tables from 4 data sources")

    # Slide 5: Tool Design
    _add_content_slide(prs, "Evidence-First Design", [
        "Every answer MUST include:",
        "  1. Specific measurements from structured data (depths, ROP, timestamps)",
        "  2. Direct quotes from DDR reports with well name and date",
        "  3. Step-by-step reasoning chain",
        "  4. Explicit assumptions and confidence level (HIGH/MEDIUM/LOW)",
        "",
        "Key differentiators vs typical approaches:",
        "  WITSML mudlog = actual measured ROP, not estimated from daily progress",
        "  Hole-size transitions define drilling phases, not just activity codes",
        "  Formation context links ROP variations to geology",
        "  Dual evidence (data + reports) for every conclusion",
    ], subtitle="Dual-source cross-referencing: structured data AND daily report narratives")

    # Slide 6: Example Q&A
    _add_content_slide(prs, "Example: Drilling Phase Identification", [
        'Q: "Identify the major drilling phases for well 15/9-F-11 T2"',
        "",
        "Agent calls: get_drilling_phases --> query_drilling_data --> search_daily_reports",
        "",
        "Answer identifies 3 major hole sections:",
        "  Phase 1: Surface 26\" (Mar 24 - Apr 13) | 306m - 1,365m MD",
        "  Phase 2: Intermediate 17.5\" (Apr 14 - Apr 28) | 1,400m - 2,577m MD",
        "  Phase 3: Reservoir 8.5\" (Apr 29 - May 9) | 2,907m - 4,562m MD",
        "",
        "Evidence: ROP data from witsml_mudlog + DDR quotes from each phase transition",
        "Confidence: HIGH -- hole size changes confirmed by activity codes and DDR summaries",
    ], subtitle="Category 1 question with full evidence chain")

    # Slide 7: Design Decisions
    _add_content_slide(prs, "Key Design Decisions", [
        "OpenAI SDK over LangChain: transparent, debuggable, minimal dependencies",
        "DuckDB over SQLite/Postgres: in-process, analytical SQL, zero config",
        "ChromaDB for retrieval: lightweight, embedded, cosine similarity search",
        "",
        "Rule-based + LLM hybrid for phase detection:",
        "  Rules: hole sizes + activity codes classify phases deterministically",
        "  LLM: validates against DDR narratives, handles ambiguity",
        "",
        "Domain-specific tooling over generic agents:",
        "  Each tool purpose-built for a drilling question category",
        "  Tools return structured evidence, not just raw data",
        "",
        "86 automated tests ensure reliability across all components",
    ], subtitle='"Complexity alone will not be rewarded" -- Judges')

    # Slide 8: Summary
    _add_content_slide(prs, "Summary", [
        "12 DuckDB tables from 4 data sources (DDR + WITSML + production + geology)",
        "9 purpose-built agent tools covering all 6 question categories",
        "26,965 searchable DDR documents in ChromaDB vector store",
        "Mandatory dual evidence: structured data + daily report quotes",
        "86 automated tests, all passing",
        "",
        "Reproducible: pip install, set API key, ingest (~3 min), ask questions",
        "",
        "What makes it win:",
        "  Evidence-first architecture with transparent reasoning",
        "  Deep data integration most competitors won't achieve",
        "  Domain-appropriate drilling engineering, not generic ML",
        "  Clean, minimal, readable code",
    ])

    output_path = "presentation/slides.pptx"
    prs.save(output_path)
    print(f"Presentation saved to {output_path}")
    return output_path


if __name__ == "__main__":
    create_presentation()
