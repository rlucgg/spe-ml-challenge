"""Stress-test question set for the SPE GCS 2026 Volve agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StressQuestion:
    """A single stress-test question with category metadata."""

    number: int
    category: str
    prompt: str


QUESTIONS: list[StressQuestion] = [
    StressQuestion(
        1,
        "Drilling Phase Identification",
        "Identify the major drilling phases for well 15/9-F-11 T2, and validate each phase boundary with hole-size changes, measured depth progression, and DDR narrative evidence.",
    ),
    StressQuestion(
        2,
        "Drilling Phase Identification",
        "On what date and at what depth did 15/9-F-11 T2 transition from the 26 in surface section into the 17 1/2 in section, and what DDR evidence confirms the casing or FIT transition?",
    ),
    StressQuestion(
        3,
        "Drilling Phase Identification",
        "For 15/9-F-1 C, separate drilling from post-TD liner or completion activity and explain when the well stopped making new hole versus when it continued with completion operations.",
    ),
    StressQuestion(
        4,
        "Drilling Phase Identification",
        "Compare drilling phase distributions and durations across 15/9-F-11, 15/9-F-11 T2, 15/9-F-11 A, and 15/9-F-11 B. Which section spent the highest fraction of time in actual drilling versus interruption or completion work?",
    ),
    StressQuestion(
        5,
        "Drilling Phase Identification",
        "For 15/9-F-15 D, identify the transition from 17 1/2 in to 12 1/4 in to 8 1/2 in hole and state where phase classification becomes ambiguous because the well moves into completion or tieback operations.",
    ),
    StressQuestion(
        6,
        "Drilling Phase Identification",
        "Validate whether 15/9-F-12 should be treated as a drilling-only well or a drilling-plus-completion lifecycle in this dataset, using both hole-size data and long-tail DDR narratives through 2016.",
    ),
    StressQuestion(
        7,
        "Drilling Phase Identification",
        "Across the F-1 family of 15/9-F-1, 15/9-F-1 A, 15/9-F-1 B, and 15/9-F-1 C, how did each sidetrack or branch inherit or diverge from the prior section's phase sequence?",
    ),
    StressQuestion(
        8,
        "Drilling Phase Identification",
        "For 15/9-19 A, distinguish genuine drilling phases from remediation phases associated with tight hole and lost circulation, and explain how confident you are in the phase labels given the older reports.",
    ),
    StressQuestion(
        9,
        "Time and Efficiency Analysis",
        "Break down non-productive time for 15/9-F-11 T2 by repair, weather, other interruptions, and any well-control-related activities. Which cause dominated and on which dates?",
    ),
    StressQuestion(
        10,
        "Time and Efficiency Analysis",
        "For 15/9-F-1 C, quantify how much time was lost to weather-driven cuttings-disposal constraints during the early 17 1/2 in section around 2014-02-23 to 2014-02-24, and what drilling work continued in parallel?",
    ),
    StressQuestion(
        11,
        "Time and Efficiency Analysis",
        "Compare non-productive time patterns between 15/9-F-14 and 15/9-F-12 during their initial 2007 campaigns. Which well was more constrained by weather, and which by equipment issues?",
    ),
    StressQuestion(
        12,
        "Time and Efficiency Analysis",
        "Identify flat-time periods for 15/9-F-15 D during November 2013 where measured depth changed little or not at all. What explains those flat segments in the DDRs?",
    ),
    StressQuestion(
        13,
        "Time and Efficiency Analysis",
        "Did drilling efficiency improve across the F-11 sequence from main bore to T2 to A to B, as measured by average daily progress, interruption share, and DDR-reported operational friction?",
    ),
    StressQuestion(
        14,
        "Time and Efficiency Analysis",
        "Across all wells with DDR drilling campaigns, which wellbore sections show the highest and lowest average daily drilled distance while actually making hole, and what operational narratives explain the extremes?",
    ),
    StressQuestion(
        15,
        "Time and Efficiency Analysis",
        "For 15/9-F-4, how much of the campaign appears to have been consumed by rig or equipment maintenance rather than drilling progress, and which equipment systems were repeat offenders?",
    ),
    StressQuestion(
        16,
        "Time and Efficiency Analysis",
        "Detect any evidence of invisible lost time on 15/9-F-1 C or 15/9-F-11 T2, where the well kept moving but comments suggest repeated conditioning, surveys, or extra circulation that reduced effective drilling efficiency.",
    ),
    StressQuestion(
        17,
        "Section and ROP Performance",
        "How did ROP change across formations in 15/9-F-1 C as the well moved from Draupne and Heather into Hugin, and do gas and lithology changes support that interpretation?",
    ),
    StressQuestion(
        18,
        "Section and ROP Performance",
        "Rank the hole sections for drilling difficulty across wells with mudlog coverage, including 15/9-F-11 T2, 15/9-F-11 A, 15/9-F-11 B, 15/9-F-1, 15/9-F-1 A, 15/9-F-1 B, 15/9-F-1 C, and 15/9-F-15 D, using ROP, WOB, torque, RPM, and DDR context.",
    ),
    StressQuestion(
        19,
        "Section and ROP Performance",
        "In 15/9-F-11 T2, were the slower intervals in the 8 1/2 in section more consistent with formation effects or drilling dysfunction, based on ROP, WOB, torque, RPM, and DDR comments?",
    ),
    StressQuestion(
        20,
        "Section and ROP Performance",
        "Which well shows the clearest gas response while drilling the Hugin reservoir: 15/9-F-1 C, 15/9-F-1 B, 15/9-F-15 D, or 15/9-F-11 A? Use methane and ethane peaks, lithology, and DDR narrative.",
    ),
    StressQuestion(
        21,
        "Section and ROP Performance",
        "For 15/9-F-15 D, identify intervals where ROP was high but ECD or gas response also increased. Was the drilling speed likely appropriate, or did it elevate operational risk?",
    ),
    StressQuestion(
        22,
        "Section and ROP Performance",
        "Using mudlog data, where are the best candidate intervals for connection-gas or hydrocarbon-show analysis in 15/9-F-1 C and 15/9-F-11 A, and how should those intervals be interpreted operationally?",
    ),
    StressQuestion(
        23,
        "Section and ROP Performance",
        "Compare the 17 1/2 in sections of 15/9-F-11 T2 and 15/9-F-15 D. Which one drilled faster after adjusting qualitatively for weather and interruptions, and what does the DDR evidence say about hole cleaning or logistics constraints?",
    ),
    StressQuestion(
        24,
        "Section and ROP Performance",
        "Across all wells with WITSML mudlog coverage, where do you see the biggest ROP optimization opportunity that did not clearly compromise well control or hole condition?",
    ),
    StressQuestion(
        25,
        "BHA and Configuration Effectiveness",
        "For 15/9-F-11 T2, which official BHA run appears most effective when combining run depth interval, average ROP, WOB, torque, RPM, and DDR narrative?",
    ),
    StressQuestion(
        26,
        "BHA and Configuration Effectiveness",
        "Compare BHA effectiveness between 15/9-F-1 C and 15/9-F-15 D in the 8 1/2 in reservoir sections. Which configuration delivered the better drilling performance in Hugin-like conditions?",
    ),
    StressQuestion(
        27,
        "BHA and Configuration Effectiveness",
        "Identify any BHA runs in 15/9-F-11 T2 or 15/9-F-1 C that appear to have ended prematurely or underperformed relative to surrounding runs. What evidence supports that conclusion?",
    ),
    StressQuestion(
        28,
        "BHA and Configuration Effectiveness",
        "For 15/9-F-1 B versus 15/9-F-1 C, did the later branch show a better drilling response in the gas-bearing sandstone interval, suggesting a learning effect or configuration improvement?",
    ),
    StressQuestion(
        29,
        "BHA and Configuration Effectiveness",
        "In 15/9-F-11 T2, do DDR comments around bit or BHA trips line up cleanly with the official WITSML BHA run boundaries, or are there inconsistencies that would matter for judge scrutiny?",
    ),
    StressQuestion(
        30,
        "BHA and Configuration Effectiveness",
        "Which well with BHA and mudlog coverage shows the highest average RPM, and is that likely real drilling practice or a data-quality artifact? Explain how you would treat it.",
    ),
    StressQuestion(
        31,
        "BHA and Configuration Effectiveness",
        "For 15/9-F-15 D, recommend the most suitable BHA approach for a future offset based on what actually worked in the 17 1/2 in, 12 1/4 in, and 8 1/2 in sections.",
    ),
    StressQuestion(
        32,
        "BHA and Configuration Effectiveness",
        "Across all wells with official BHA runs, which hole section appears most sensitive to configuration choice rather than purely to geology?",
    ),
    StressQuestion(
        33,
        "Operational Issues and Root Causes",
        "Analyze the weather-related downtime on 15/9-F-14 during November 2007. How severe was it, how long did it persist, and what work was still accomplished while waiting on weather?",
    ),
    StressQuestion(
        34,
        "Operational Issues and Root Causes",
        "For 15/9-F-15 D in mid-November 2013, what were the main root causes of delay: weather, cuttings logistics, trip-tank loss monitoring, or equipment leaks?",
    ),
    StressQuestion(
        35,
        "Operational Issues and Root Causes",
        "Did 15/9-F-12 have a recurring TDS or flowline-isolation-valve reliability problem in June 2007, and how much operational disruption did it cause?",
    ),
    StressQuestion(
        36,
        "Operational Issues and Root Causes",
        "For 15/9-F-4, what equipment system created the most recurring trouble: PRS, TDS, casing tong, crane logistics, or valves? Support the diagnosis with dated DDR evidence.",
    ),
    StressQuestion(
        37,
        "Operational Issues and Root Causes",
        "Examine the stable-loss or lost-circulation behavior on 15/9-F-12 around 2007-06-26 to 2007-06-27. Was it operationally significant or just background loss that was managed successfully?",
    ),
    StressQuestion(
        38,
        "Operational Issues and Root Causes",
        "In 15/9-F-11 T2, do the rupture-disc events on MP #1 and MP #2 on 2013-04-14 look like a transient equipment nuisance or a broader reliability issue that materially affected progress?",
    ),
    StressQuestion(
        39,
        "Operational Issues and Root Causes",
        "For the legacy well 15/9-19 A, what do the DDRs suggest was the dominant cause of repeated trouble: pack-off or tight hole, lost circulation, cavings, or mechanical sticking?",
    ),
    StressQuestion(
        40,
        "Operational Issues and Root Causes",
        "Did 15/9-F-1 C encounter any meaningful well-control warning signs in the 8 1/2 in section, or do the data mostly show hydrocarbon indication without control loss?",
    ),
    StressQuestion(
        41,
        "Operational Issues and Root Causes",
        "Compare operational issue patterns between 15/9-F-11 T2 and 15/9-F-1 C. Which well was more constrained by logistics and weather versus subsurface or drilling response?",
    ),
    StressQuestion(
        42,
        "Operational Issues and Root Causes",
        "Across all wells, which campaign appears riskiest from a combined view of interruptions, loss or stuck indications, and problematic narratives, and why?",
    ),
    StressQuestion(
        43,
        "Synthesis Comparison and Recommendations",
        "Based on 15/9-F-11 T2, 15/9-F-1 C, and 15/9-F-15 D, what are the clearest cross-well best practices for drilling the Volve reservoir section into Hugin?",
    ),
    StressQuestion(
        44,
        "Synthesis Comparison and Recommendations",
        "What lessons learned from the problematic early wells 15/9-19 A, 15/9-19 B, and 15/9-19 ST2 seem to have been incorporated into the later Volve development wells?",
    ),
    StressQuestion(
        45,
        "Synthesis Comparison and Recommendations",
        "If you were planning the next Volve development well, what drilling-program changes would you recommend for weather exposure, cuttings logistics, and section-transition discipline?",
    ),
    StressQuestion(
        46,
        "Synthesis Comparison and Recommendations",
        "Create a shift-handover summary for 15/9-F-1 C at the point the well reached TD around 2014-03-15, including operational state, immediate risks, and next planned operations.",
    ),
    StressQuestion(
        47,
        "Synthesis Comparison and Recommendations",
        "Quantify well-on-well improvement across the F-1 sequence from 15/9-F-1 B to 15/9-F-1 C in the reservoir section. Did the later branch drill faster, cleaner, or just under different geology?",
    ),
    StressQuestion(
        48,
        "Synthesis Comparison and Recommendations",
        "Integrate drilling and production data for the producing wells. Do wells with smoother drilling or completion histories, such as 15/9-F-1 C or 15/9-F-15 D, show any obvious production advantage versus 15/9-F-11, 15/9-F-12, 15/9-F-14, 15/9-F-4, or 15/9-F-5?",
    ),
    StressQuestion(
        49,
        "Synthesis Comparison and Recommendations",
        "Across the Volve field, which wells should be considered highest risk for future intervention or sidetrack work based on their original drilling issues, formation context, and completion or perforation geometry?",
    ),
    StressQuestion(
        50,
        "Synthesis Comparison and Recommendations",
        "If you had to optimize the drilling sequence for future Volve infill wells, which reference well would you use as the main benchmark for each major section, and which would you avoid copying?",
    ),
]
