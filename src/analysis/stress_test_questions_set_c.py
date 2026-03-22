"""Independent stress-test question set C — 30 questions designed by a
petroleum engineering domain expert to probe edge cases, cross-well
synthesis, and data integration depth."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StressQuestion:
    number: int
    category: str
    prompt: str


QUESTIONS: list[StressQuestion] = [
    # ── Category 1: Phase Identification (4) ──────────────────────────
    StressQuestion(
        1, "Phase Identification",
        "Reconstruct the drilling sequence for well 15/9-F-4. "
        "How many hole sections were drilled, what were the casing shoe depths, "
        "and how long did each section take?",
    ),
    StressQuestion(
        2, "Phase Identification",
        "Well 15/9-F-15 C has 84 DDR records spanning 2009 to 2013. "
        "Identify whether this represents a single continuous drilling campaign "
        "or multiple campaigns separated by long idle periods, and provide "
        "evidence for your conclusion.",
    ),
    StressQuestion(
        3, "Phase Identification",
        "For the exploration well 15/9-19 A (drilled in the 1990s), identify "
        "the drilling phases and compare the activity code distribution with "
        "a modern development well such as 15/9-F-11 T2. "
        "What differences reflect changes in drilling practices over 15 years?",
    ),
    StressQuestion(
        4, "Phase Identification",
        "Well 15/9-F-11 has only 17 DDR records. Is this sufficient data to "
        "identify drilling phases? What can you determine, and what is "
        "ambiguous due to the sparse record count?",
    ),

    # ── Category 2: Efficiency & NPT (5) ──────────────────────────────
    StressQuestion(
        5, "Efficiency & NPT",
        "Rank the top 5 wells by percentage of time spent on non-productive "
        "activities. For the worst performer, decompose the NPT into "
        "sub-categories and identify the single longest NPT event.",
    ),
    StressQuestion(
        6, "Efficiency & NPT",
        "For well 15/9-F-5, calculate the productive time ratio and compare "
        "it with the field average. What drove the difference?",
    ),
    StressQuestion(
        7, "Efficiency & NPT",
        "How much rig time was lost to weather delays across all Volve wells? "
        "Was there a seasonal pattern — were certain months worse than others?",
    ),
    StressQuestion(
        8, "Efficiency & NPT",
        "Compare tripping time as a fraction of total time between 15/9-F-11 T2 "
        "and 15/9-F-11 B. The B well is a high-angle lateral — did the "
        "higher inclination lead to more trip time?",
    ),
    StressQuestion(
        9, "Efficiency & NPT",
        "Estimate the connection time overhead for well 15/9-F-11 T2 by "
        "examining how many trips were made per hole section, and how the "
        "trip-to-drilling time ratio changed with depth.",
    ),

    # ── Category 3: ROP & Section Performance (5) ─────────────────────
    StressQuestion(
        10, "ROP & Section Performance",
        "Using WITSML mudlog data, compare the average ROP in the Hugin "
        "Formation sandstone across all wells that penetrated it. Which well "
        "achieved the fastest ROP in the reservoir, and what drilling "
        "parameters (WOB, RPM, mud weight) were used?",
    ),
    StressQuestion(
        11, "ROP & Section Performance",
        "For well 15/9-F-15 D, was there a measurable ROP difference between "
        "the claystone and limestone intervals in the 8.5-inch section? "
        "Use the WITSML mudlog lithology and ROP data.",
    ),
    StressQuestion(
        12, "ROP & Section Performance",
        "Identify any depth intervals in 15/9-F-11 T2 where the d-exponent "
        "(DxC) showed a significant change. Correlate these with formation "
        "tops and drilling parameter changes.",
    ),
    StressQuestion(
        13, "ROP & Section Performance",
        "Across the field, which 17.5-inch section drilled the fastest "
        "(highest average daily progress)? What factors — geological, "
        "operational, or equipment — might explain its performance?",
    ),
    StressQuestion(
        14, "ROP & Section Performance",
        "For well 15/9-F-1 C, compare the DDR-reported daily drilling "
        "progress with the WITSML mudlog ROP data. Are they consistent, "
        "or does the mudlog suggest higher instantaneous ROP masked by "
        "non-drilling time within each day?",
    ),

    # ── Category 4: BHA & Configuration (4) ───────────────────────────
    StressQuestion(
        15, "BHA & Configuration",
        "For 15/9-F-11 B, which BHA string number drilled the longest "
        "interval? What were the drilling parameters for that run, and "
        "was it a steerable motor or rotary steerable system?",
    ),
    StressQuestion(
        16, "BHA & Configuration",
        "Across all wells with WITSML BHA run data, which well had the "
        "most BHA runs? Does a higher number of runs correlate with "
        "more equipment problems or with more complex well geometry?",
    ),
    StressQuestion(
        17, "BHA & Configuration",
        "For well 15/9-F-14, identify from DDR comments what bit types "
        "were used (PDC vs tri-cone) and how the bit condition was "
        "described when pulled out of hole.",
    ),
    StressQuestion(
        18, "BHA & Configuration",
        "Compare the BHA performance (ROP, WOB, torque) between the "
        "8.5-inch sections of 15/9-F-11 T2 and 15/9-F-11 A. Both are "
        "sidetracks from the same parent well — did the second well "
        "benefit from lessons learned in the first?",
    ),

    # ── Category 5: Operational Issues (6) ────────────────────────────
    StressQuestion(
        19, "Operational Issues",
        "Were there any stuck pipe events recorded across the Volve wells? "
        "Identify the well, depth, duration, and how the pipe was freed.",
    ),
    StressQuestion(
        20, "Operational Issues",
        "For well 15/9-F-12, which had 165 DDR records over nearly 10 years, "
        "identify the dominant operational challenges. Were the issues "
        "primarily drilling-related or workover/intervention-related?",
    ),
    StressQuestion(
        21, "Operational Issues",
        "Across all wells, were there any events where the ECD exceeded "
        "the formation fracture gradient, leading to mud losses? "
        "Use WITSML mudlog ECD data and DDR comments to investigate.",
    ),
    StressQuestion(
        22, "Operational Issues",
        "For well 15/9-F-10, what were the main operational issues "
        "encountered? This well has 71 DDR records — summarize the key "
        "problems and how they were addressed.",
    ),
    StressQuestion(
        23, "Operational Issues",
        "Identify any fishing operations recorded in the Volve dataset. "
        "What equipment was lost, in which well, and was the fish "
        "successfully recovered?",
    ),
    StressQuestion(
        24, "Operational Issues",
        "Was there any correlation between high gas readings in the mudlog "
        "and well control events or flow checks? Use WITSML methane data "
        "alongside DDR activity records.",
    ),

    # ── Category 6: Synthesis & Recommendations (6) ───────────────────
    StressQuestion(
        25, "Synthesis & Recommendations",
        "If you were planning a new 8.5-inch horizontal section targeting "
        "the Hugin Formation from the F-11 slot, what mud weight range, "
        "BHA configuration, and operational precautions would you recommend "
        "based on offset well data?",
    ),
    StressQuestion(
        26, "Synthesis & Recommendations",
        "Produce a shift handover summary for well 15/9-F-11 T2 covering "
        "the 24-hour period of 2013-04-22. Include: current depth, "
        "operations summary, problems encountered, and plan for next shift.",
    ),
    StressQuestion(
        27, "Synthesis & Recommendations",
        "Did the wells with the highest drilling NPT also have the "
        "lowest cumulative oil production? Investigate whether drilling "
        "difficulty predicted production outcome for Volve wells.",
    ),
    StressQuestion(
        28, "Synthesis & Recommendations",
        "Rank the Volve development wells from best to worst overall "
        "drilling performance, considering ROP, NPT, total days to TD, "
        "and number of operational incidents. Justify your ranking criteria.",
    ),
    StressQuestion(
        29, "Synthesis & Recommendations",
        "What is the estimated total cost impact of weather-related NPT "
        "across all Volve wells, assuming a spread rate of $500,000 per "
        "day? Which well was most affected?",
    ),
    StressQuestion(
        30, "Synthesis & Recommendations",
        "Based on all available data, write a 5-point executive summary "
        "of drilling performance across the Volve field that a VP of "
        "Drilling Operations could present to the board. Each point must "
        "be supported by specific data from at least two wells.",
    ),
]
