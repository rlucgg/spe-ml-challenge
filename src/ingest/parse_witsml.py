"""Parse WITSML real-time drilling data (bhaRun, mudLog, trajectory, message).

WITSML 1.4.1.1 XML with namespace 'http://www.witsml.org/schemas/1series'.
Directory structure: {well_dir}/{section_num}/{data_type}/*.xml
"""

import logging
import math
from pathlib import Path
from typing import Optional

from lxml import etree

from src.config import WITSML_DIR, normalize_well_name

logger = logging.getLogger(__name__)

NS = {"w": "http://www.witsml.org/schemas/1series"}

# Unit conversion constants
RAD_TO_DEG = 180.0 / math.pi
MPS_TO_MPH = 3600.0  # m/s → m/hr
N_TO_KN = 0.001
NM_TO_KNM = 0.001
KGM3_TO_SG = 0.001  # kg/m³ → g/cm³ (= sg)
DLS_RAD_M_TO_DEG_30M = RAD_TO_DEG * 30.0  # rad/m → deg/30m


def _text(el, tag: str, default: str = "") -> str:
    """Extract text from child element using WITSML namespace."""
    child = el.find(f"w:{tag}", NS)
    if child is not None and child.text:
        return child.text.strip()
    return default


def _float(el, tag: str) -> Optional[float]:
    """Extract float from child element, returning None for missing/sentinel."""
    val = _text(el, tag)
    if not val:
        return None
    try:
        f = float(val)
        return None if f == -999.25 or f == -9999 else f
    except ValueError:
        return None


def _safe_xml_parse(filepath: Path):
    """Parse an XML file, returning None on failure."""
    try:
        return etree.parse(str(filepath))
    except (etree.XMLSyntaxError, OSError) as e:
        logger.debug("Skipping %s: %s", filepath.name, e)
        return None


def _discover_sections(witsml_dir: Path) -> list[dict]:
    """Discover all wellbore sections across all WITSML well directories.

    Returns list of dicts with: well_dir, section_dir, well, wellbore
    """
    sections = []
    for well_dir in sorted(witsml_dir.iterdir()):
        if not well_dir.is_dir() or well_dir.name.startswith("."):
            continue

        for section_dir in sorted(well_dir.iterdir()):
            if not section_dir.is_dir() or section_dir.name.startswith("_"):
                continue
            # Skip non-numeric directories
            if not section_dir.name.replace(" ", "").isalnum():
                continue

            # Read wellbore info from _wellboreInfo XML
            well_name = ""
            wellbore_name = ""
            wb_dir = section_dir / "_wellboreInfo"
            if wb_dir.exists():
                for f in wb_dir.glob("*.xml"):
                    tree = _safe_xml_parse(f)
                    if tree is None:
                        continue
                    wb_el = tree.find(".//w:wellbore", NS)
                    if wb_el is not None:
                        well_name = _text(wb_el, "nameWell")
                        wellbore_name = _text(wb_el, "name")
                    break

            if well_name:
                # Use wellbore name for the 'well' key to match DDR conventions.
                # E.g. wellbore "NO 15/9-F-11 T2" → "15_9_F_11_T2" (matches DDR files)
                # Falls back to well name if wellbore name matches it (main wellbore).
                norm_wb = normalize_well_name(wellbore_name) if wellbore_name else ""
                norm_well = normalize_well_name(well_name)
                well_key = norm_wb if norm_wb else norm_well
                sections.append({
                    "section_dir": section_dir,
                    "well": well_key,
                    "wellbore": wellbore_name,
                })

    logger.info("Discovered %d WITSML wellbore sections", len(sections))
    return sections


def _parse_bha_runs(section_dir: Path, well: str, wellbore: str) -> list[dict]:
    """Parse all bhaRun XML files in a section directory."""
    bha_dir = section_dir / "bhaRun"
    if not bha_dir.exists():
        return []

    results = []
    for filepath in sorted(bha_dir.glob("*.xml")):
        tree = _safe_xml_parse(filepath)
        if tree is None:
            continue

        for run in tree.findall(".//w:bhaRun", NS):
            dp = run.find("w:drillingParams", NS)
            md_start = _float(dp, "mdHoleStart") if dp is not None else None
            md_stop = _float(dp, "mdHoleStop") if dp is not None else None

            results.append({
                "well": well,
                "wellbore": wellbore,
                "run_name": _text(run, "name"),
                "start_time": _text(run, "dTimStart"),
                "end_time": _text(run, "dTimStop"),
                "num_bit_run": _text(run, "numBitRun"),
                "num_string_run": _text(run, "numStringRun"),
                "md_start_m": md_start,
                "md_stop_m": md_stop,
            })

    return results


def _parse_mudlog(section_dir: Path, well: str, wellbore: str) -> list[dict]:
    """Parse mudLog geology intervals with drilling parameters.

    Converts from WITSML SI units to field units:
    - ROP: m/s → m/hr
    - WOB: N → kN
    - Torque: N.m → kN.m
    - RPM: c/s → RPM
    - Mud weight, ECD: kg/m³ → sg (g/cm³)
    """
    ml_dir = section_dir / "mudLog"
    if not ml_dir.exists():
        return []

    results = []
    for filepath in sorted(ml_dir.glob("*.xml")):
        tree = _safe_xml_parse(filepath)
        if tree is None:
            continue

        for interval in tree.findall(".//w:geologyInterval", NS):
            # Get primary lithology
            lith_el = interval.find("w:lithology", NS)
            lith_type = _text(lith_el, "type") if lith_el is not None else ""
            lith_pct_raw = _float(lith_el, "lithPc") if lith_el is not None else None

            # ROP conversion: m/s → m/hr
            rop_avg_raw = _float(interval, "ropAv")
            rop_min_raw = _float(interval, "ropMn")
            rop_max_raw = _float(interval, "ropMx")
            rop_avg = rop_avg_raw * MPS_TO_MPH if rop_avg_raw is not None else None
            rop_min = rop_min_raw * MPS_TO_MPH if rop_min_raw is not None else None
            rop_max = rop_max_raw * MPS_TO_MPH if rop_max_raw is not None else None

            # WOB: N → kN
            wob_raw = _float(interval, "wobAv")
            wob_kN = wob_raw * N_TO_KN if wob_raw is not None else None

            # Torque: N.m → kN.m
            tq_raw = _float(interval, "tqAv")
            torque_kNm = tq_raw * NM_TO_KNM if tq_raw is not None else None

            # RPM: c/s → RPM
            rpm_raw = _float(interval, "rpmAv")
            rpm = rpm_raw * 60.0 if rpm_raw is not None else None

            # Mud weight and ECD: kg/m³ → sg
            mw_raw = _float(interval, "wtMudAv")
            mw_sg = mw_raw * KGM3_TO_SG if mw_raw is not None else None
            ecd_raw = _float(interval, "ecdTdAv")
            ecd_sg = ecd_raw * KGM3_TO_SG if ecd_raw is not None else None

            # Gas data from chromatograph
            chrom = interval.find("w:chromatograph", NS)
            methane = _float(chrom, "methAv") if chrom is not None else None
            ethane = _float(chrom, "ethAv") if chrom is not None else None

            results.append({
                "well": well,
                "wellbore": wellbore,
                "md_top_m": _float(interval, "mdTop"),
                "md_bottom_m": _float(interval, "mdBottom"),
                "lith_type": lith_type,
                "lith_pct": lith_pct_raw,
                "rop_avg_m_per_hr": rop_avg,
                "rop_min_m_per_hr": rop_min,
                "rop_max_m_per_hr": rop_max,
                "wob_avg_kN": wob_kN,
                "torque_avg_kNm": torque_kNm,
                "rpm_avg": rpm,
                "mud_weight_sg": mw_sg,
                "ecd_sg": ecd_sg,
                "dxc": _float(interval, "dxcAv"),
                "methane_avg_ppm": methane,
                "ethane_avg_ppm": ethane,
            })

    return results


def _parse_trajectory(section_dir: Path, well: str, wellbore: str) -> list[dict]:
    """Parse trajectory survey stations.

    Converts inclination and azimuth from radians to degrees.
    """
    traj_dir = section_dir / "trajectory"
    if not traj_dir.exists():
        return []

    results = []
    seen_mds = set()  # deduplicate stations across files

    for filepath in sorted(traj_dir.glob("*.xml")):
        tree = _safe_xml_parse(filepath)
        if tree is None:
            continue

        for station in tree.findall(".//w:trajectoryStation", NS):
            md = _float(station, "md")
            if md is None or md in seen_mds:
                continue
            seen_mds.add(md)

            incl_rad = _float(station, "incl")
            azi_rad = _float(station, "azi")
            dls_raw = _float(station, "dls")

            results.append({
                "well": well,
                "wellbore": wellbore,
                "timestamp": _text(station, "dTimStn"),
                "md_m": md,
                "tvd_m": _float(station, "tvd"),
                "inclination_deg": incl_rad * RAD_TO_DEG if incl_rad is not None else None,
                "azimuth_deg": azi_rad * RAD_TO_DEG if azi_rad is not None else None,
                "dls_deg_per_30m": dls_raw * DLS_RAD_M_TO_DEG_30M if dls_raw is not None else None,
                "ns_m": _float(station, "dispNs"),
                "ew_m": _float(station, "dispEw"),
            })

    return results


def _parse_messages(section_dir: Path, well: str, wellbore: str) -> list[dict]:
    """Parse operational messages."""
    msg_dir = section_dir / "message"
    if not msg_dir.exists():
        return []

    results = []
    for filepath in sorted(msg_dir.glob("*.xml")):
        tree = _safe_xml_parse(filepath)
        if tree is None:
            continue

        for msg in tree.findall(".//w:message", NS):
            results.append({
                "well": well,
                "wellbore": wellbore,
                "timestamp": _text(msg, "dTim"),
                "md_m": _float(msg, "md"),
                "message_type": _text(msg, "typeMessage"),
                "message_text": _text(msg, "messageText"),
            })

    return results


def parse_all_witsml(witsml_dir: Optional[Path] = None) -> dict:
    """Parse all WITSML real-time data from directory structure.

    Returns dict with keys: bha_runs, mudlog_intervals, trajectories,
    messages, each a list of dicts ready for DuckDB insertion.
    """
    witsml_dir = witsml_dir or WITSML_DIR
    if not witsml_dir.exists():
        logger.warning("WITSML directory not found: %s", witsml_dir)
        return {"bha_runs": [], "mudlog_intervals": [], "trajectories": [], "messages": []}

    sections = _discover_sections(witsml_dir)

    all_bha = []
    all_mudlog = []
    all_traj = []
    all_msg = []

    for sec in sections:
        sd = sec["section_dir"]
        w = sec["well"]
        wb = sec["wellbore"]

        bha = _parse_bha_runs(sd, w, wb)
        all_bha.extend(bha)

        mudlog = _parse_mudlog(sd, w, wb)
        all_mudlog.extend(mudlog)

        traj = _parse_trajectory(sd, w, wb)
        all_traj.extend(traj)

        msg = _parse_messages(sd, w, wb)
        all_msg.extend(msg)

        if bha or mudlog or traj or msg:
            logger.debug(
                "  %s (%s): bha=%d mudlog=%d traj=%d msg=%d",
                wb, w, len(bha), len(mudlog), len(traj), len(msg),
            )

    logger.info(
        "WITSML parsing complete: %d bha_runs, %d mudlog_intervals, "
        "%d trajectory_stations, %d messages",
        len(all_bha), len(all_mudlog), len(all_traj), len(all_msg),
    )

    return {
        "bha_runs": all_bha,
        "mudlog_intervals": all_mudlog,
        "trajectories": all_traj,
        "messages": all_msg,
    }
