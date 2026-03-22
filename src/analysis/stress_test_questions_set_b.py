"""Second, highly advanced stress-test question set for the SPE GCS 2026 Volve agent."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class StressQuestion:
    number: int
    category: str
    prompt: str

QUESTIONS: list[StressQuestion] = [
    # Category 1 — Phase Identification & Validation
    StressQuestion(1, "Phase Identification", "Evaluate the transition from the 17.5 in section to the 12.25 in section in well 15/9-F-11 A. Did the activity codes accurately reflect the casing running and cementing operations, or were there periods flagged as NPT that should be considered part of the phase transition?"),
    StressQuestion(2, "Phase Identification", "In well 15/9-F-5, during the 8.5 in reservoir section drilling, at what depth do the DDR comments first indicate shifting focus towards wellbore cleanup and preparation for completion rather than making new hole?"),
    StressQuestion(3, "Phase Identification", "Analyze the phase progression of well 15/9-19 ST2. How does the proportion of time spent in the 'formation evaluation' phase compare to that of the modern development well 15/9-F-1 C?"),
    StressQuestion(4, "Phase Identification", "For well 15/9-F-4, pinpoint the date when the 12.25 in hole section was officially declared at TD. What evidence in the DDR status info and activities confirms this milestone?"),
    StressQuestion(5, "Phase Identification", "During the drilling of well 15/9-F-12, identify any instances where the reported hole diameter in `ddr_status` contradicts the activity narrative. How should the phase boundary be interpreted in such cases?"),
    StressQuestion(6, "Phase Identification", "In well 15/9-F-15 A, map the surface casing cementing phase. Does the duration of this phase align with standard North Sea practices, or do the DDRs indicate unexpected delays?"),
    StressQuestion(7, "Phase Identification", "Trace the completion phase of well 15/9-F-1 B. Based on the daily reports, how much time elapsed between the last drilling activity and the final well handover?"),
    StressQuestion(8, "Phase Identification", "For well 15/9-F-14, contrast the time spent in the 8.5 in drilling phase against the time spent tripping. Did tripping operations consume an unusually high fraction of this phase?"),

    # Category 2 — Time & Efficiency Analysis
    StressQuestion(9, "Time & Efficiency", "Based on the WITSML mudlog for the 12.25 in section of 15/9-F-1 C, identify specific depth intervals with exceptionally high WOB and torque but poor ROP. What does this suggest about the drilling efficiency in those intervals?"),
    StressQuestion(10, "Time & Efficiency", "Analyze the flat-time events during the drilling of the Shetland Group in well 15/9-F-11 T2. Were these delays primarily caused by weather, equipment failure, or subsurface issues?"),
    StressQuestion(11, "Time & Efficiency", "Compare the overall productive time ratio of the exploration well 15/9-19 A with the development well 15/9-F-15 D. How much has the ratio improved over the decades?"),
    StressQuestion(12, "Time & Efficiency", "In well 15/9-F-4, identify the most severe single NPT event by duration. What was the root cause, and how did the rig crew resolve it according to the DDR?"),
    StressQuestion(13, "Time & Efficiency", "Evaluate the tripping speeds during the 12.25 in section of well 15/9-F-12 based on the DDR timeline. Do the speeds suggest tight hole conditions or smooth tripping?"),
    StressQuestion(14, "Time & Efficiency", "Assess the impact of waiting on cement (WOC) time across all sections of well 15/9-F-5. Did WOC constitute a significant portion of the total non-productive time?"),
    StressQuestion(15, "Time & Efficiency", "For well 15/9-F-1 C, correlate periods of low ROP with the reported mud properties (PV, YP). Did poor hole cleaning efficiency contribute to the reduced drilling speed?"),
    StressQuestion(16, "Time & Efficiency", "In well 15/9-F-14, analyze the efficiency of connection times in the 8.5 in section. Are there indications in the DDR of excessive connection gas or hole conditioning that extended connection times?"),

    # Category 3 — Section & ROP Performance
    StressQuestion(17, "Section & ROP", "Compare the average ROP in the Draupne formation across wells 15/9-F-1 C, 15/9-F-11 B, and 15/9-F-15 D. Which well drilled this formation fastest, and what was the corresponding mud weight?"),
    StressQuestion(18, "Section & ROP", "In the 17.5 in section of well 15/9-F-11 T2, identify the depth interval with the highest sustained ROP. What was the lithology reported in the WITSML mudlog for this interval?"),
    StressQuestion(19, "Section & ROP", "Analyze the drilling performance in the Hordaland Group for well 15/9-F-4. Did the ROP show significant variation, and how does this correlate with the DDR narratives of that phase?"),
    StressQuestion(20, "Section & ROP", "For well 15/9-F-12, evaluate the ROP response when entering the Ty formation. Was there a noticeable drill break or a decrease in ROP, and what do the DDRs state about the formation characteristics?"),
    StressQuestion(21, "Section & ROP", "In well 15/9-F-1 A, examine the relationship between ROP and ECD in the 8.5 in section based on mudlog data. Did higher ROP consistently result in elevated ECD, suggesting hole cleaning challenges?"),
    StressQuestion(22, "Section & ROP", "Compare the deepest 500 meters of drilling in wells 15/9-19 A and 15/9-F-1 C. How do the ROP values reflect the different drilling technologies used in these eras?"),
    StressQuestion(23, "Section & ROP", "For well 15/9-F-5, identify any depth intervals in the 12.25 in section where the ROP dropped significantly. Was this due to hard stringers or drilling dysfunction according to DDRs?"),
    StressQuestion(24, "Section & ROP", "Analyze the gas response (methane and ethane) versus ROP in the Hugin formation of well 15/9-F-15 D. Did the fastest drilling intervals produce the highest gas peaks?"),

    # Category 4 — BHA & Configuration Effectiveness
    StressQuestion(25, "BHA & Config", "Evaluate the performance of the BHA runs in the 8.5 in section of well 15/9-F-1 C. Which run achieved the highest average ROP, and what were the key components of that BHA?"),
    StressQuestion(26, "BHA & Config", "In well 15/9-F-11 T2, analyze the reasons for pulling the BHA in the 12.25 in section. Were most trips scheduled for bit changes or forced by tool failures?"),
    StressQuestion(27, "BHA & Config", "Compare the torque and drag indications between the BHA runs in the highly deviated sections of 15/9-F-1 A and 15/9-F-1 B. Which configuration encountered more friction?"),
    StressQuestion(28, "BHA & Config", "For well 15/9-F-15 D, assess the effectiveness of the BHA used in the 17.5 in section. Did it successfully maintain steady ROP and stable torque?"),
    StressQuestion(29, "BHA & Config", "In well 15/9-F-4, identify any BHA runs that experienced severe vibrations or stick-slip. How did the drillers mitigate these issues based on the DDR comments?"),
    StressQuestion(30, "BHA & Config", "Evaluate the correlation between RPM and ROP across all BHA runs in the 12.25 in section of well 15/9-F-1 C. Was higher RPM always beneficial for ROP?"),
    StressQuestion(31, "BHA & Config", "For well 15/9-F-14, analyze the performance of the directional tools in the 8.5 in section based on DDR descriptions. Did the directional control meet expectations without sacrificing ROP?"),
    StressQuestion(32, "BHA & Config", "Compare the number of BHA runs required to complete the 17.5 in section in the early development wells (e.g., F-12, F-14) versus the later wells (e.g., F-1 C, F-11 T2). Has BHA durability improved?"),

    # Category 5 — Operational Issues & Root Causes
    StressQuestion(33, "Issues & Root Causes", "In well 15/9-F-1 C, detail the events surrounding the loss of circulation in the 12.25 in section. At what depth did it occur, and what was the composition of the LCM pill used to cure it?"),
    StressQuestion(34, "Issues & Root Causes", "Analyze the well control incident in well 15/9-F-11 T2 during the 8.5 in section. What were the initial warning signs (e.g., flow increase, pit gain), and how long did it take to circulate out the influx?"),
    StressQuestion(35, "Issues & Root Causes", "For well 15/9-F-5, investigate the instances of stuck pipe. Were these incidents associated with high overbalance pressures or poor hole cleaning during connections?"),
    StressQuestion(36, "Issues & Root Causes", "In the exploration well 15/9-19 A, what was the primary cause of the severe wellbore instability in the Hordaland Group? How did the mud weight strategy evolve in response?"),
    StressQuestion(37, "Issues & Root Causes", "Evaluate the equipment failures reported in well 15/9-F-15 D. Did top drive issues or mud pump failures cause more cumulative NPT?"),
    StressQuestion(38, "Issues & Root Causes", "For well 15/9-F-4, analyze the impact of weather on rig operations. During which month did waiting on weather (WOW) have the most significant effect on the drilling schedule?"),
    StressQuestion(39, "Issues & Root Causes", "In well 15/9-F-12, investigate the cementing problems during the setting of the 13.3/8 in casing. Was there a failure to obtain returns, and what remedial actions were taken?"),
    StressQuestion(40, "Issues & Root Causes", "Analyze the relationship between mud properties (density, PV, YP) and tight hole occurrences in well 15/9-F-14. Did high viscosity contribute to the tight hole issues?"),
    StressQuestion(41, "Issues & Root Causes", "In well 15/9-F-1 B, were there any indications of shallow gas during the top hole drilling? How did the rig crew manage the risk?"),
    StressQuestion(42, "Issues & Root Causes", "Compare the frequency and severity of pack-off events between wells 15/9-F-11 A and 15/9-F-1 C. Which well experienced more severe pack-offs, and what were the contributing factors?"),

    # Category 6 — Synthesis, Comparison & Recommendations
    StressQuestion(43, "Synthesis & Recs", "Synthesize the drilling performance and subsequent production data for well 15/9-F-1 C. Did the relatively fast drilling of the reservoir section translate into higher early production rates compared to 15/9-F-15 D?"),
    StressQuestion(44, "Synthesis & Recs", "Based on the historical drilling issues in the Volve field, what specific mud weight and rheology profile would you recommend for drilling the challenging Draupne formation in a future infill well?"),
    StressQuestion(45, "Synthesis & Recs", "Compare the overall well delivery times (spud to completion) for the F-1 series (F-1, F-1 A, F-1 B, F-1 C). What were the primary drivers for the differences in delivery times?"),
    StressQuestion(46, "Synthesis & Recs", "Evaluate the effectiveness of the casing designs across the field. Did the standard casing program adequately isolate the problem formations, or were there frequent instances of casing points being altered due to wellbore conditions?"),
    StressQuestion(47, "Synthesis & Recs", "Based on the analysis of BHA runs and operational issues, what is the optimal BHA configuration for drilling the 8.5 in horizontal section in the Hugin formation to maximize ROP and minimize stick-slip?"),
    StressQuestion(48, "Synthesis & Recs", "Synthesize the impact of non-productive time on the overall economics of well 15/9-F-11 T2. If the weather and equipment delays were eliminated, how much faster could the well have been delivered?"),
    StressQuestion(49, "Synthesis & Recs", "Contrast the drilling strategies used in the exploration phase (15/9-19 series) with those in the late development phase (15/9-F-1 C, 15/9-F-11 T2). How did the approach to risk management and well control evolve?"),
    StressQuestion(50, "Synthesis & Recs", "Based on the entire Volve dataset, what are the top three 'lessons learned' that should be applied to any future drilling campaigns in analogous North Sea reservoirs?")
]