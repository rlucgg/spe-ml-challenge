"""Parse DDR (Daily Drilling Report) XML files into structured data.

Handles WITSML 1.4.0.0 XML with namespace 'http://www.witsml.org/schemas/1series'.
Parses 1,759 DDR files across 26 wellbore sections.
"""

import logging
from pathlib import Path
from typing import Optional

from lxml import etree

from src.config import DDR_DIR, SENTINEL_VALUE, WITSML_NS

logger = logging.getLogger(__name__)
NS = WITSML_NS


def _text(element, tag: str, default: str = "") -> str:
    """Extract text from a child element."""
    el = element.find(f"witsml:{tag}", NS)
    if el is not None and el.text:
        return el.text.strip()
    return default


def _float(element, tag: str) -> Optional[float]:
    """Extract float, returning None for sentinel -999.99 or missing."""
    val = _text(element, tag)
    if not val:
        return None
    try:
        f = float(val)
        return None if f < -990.0 else f
    except ValueError:
        return None


def _int(element, tag: str) -> Optional[int]:
    """Extract integer from child element."""
    val = _text(element, tag)
    if not val:
        return None
    try:
        return int(val)
    except ValueError:
        try:
            return int(float(val))
        except ValueError:
            return None


def parse_well_from_filename(filename: str) -> tuple[str, str]:
    """Extract well name and date from DDR filename.

    Args:
        filename: e.g. '15_9_F_11_T2_2013_03_24.xml'

    Returns:
        (well_name, date_str): e.g. ('15_9_F_11_T2', '2013-03-24')
    """
    stem = Path(filename).stem
    parts = stem.split("_")
    date_str = f"{parts[-3]}-{parts[-2]}-{parts[-1]}"
    well_name = "_".join(parts[:-3])
    return well_name, date_str


def _parse_wellbore_info(report, well: str, date: str) -> Optional[dict]:
    """Parse wellboreInfo element."""
    wb = report.find("witsml:wellboreInfo", NS)
    if wb is None:
        return None

    rig_name = ""
    rig_el = wb.find("witsml:rigAlias", NS)
    if rig_el is not None:
        rig_name = _text(rig_el, "name")

    return {
        "well": well,
        "date": date,
        "name_well": _text(report, "nameWell"),
        "name_wellbore": _text(report, "nameWellbore"),
        "spud_date": _text(wb, "dTimSpud"),
        "drill_complete_date": _text(wb, "dateDrillComplete"),
        "operator": _text(wb, "operator"),
        "drill_contractor": _text(wb, "drillContractor"),
        "rig_name": rig_name,
    }


def _parse_status(report, well: str, date: str) -> Optional[dict]:
    """Parse statusInfo element."""
    si = report.find("witsml:statusInfo", NS)
    if si is None:
        return None
    return {
        "well": well,
        "date": date,
        "report_no": _int(si, "reportNo"),
        "md_m": _float(si, "md"),
        "tvd_m": _float(si, "tvd"),
        "hole_diameter_in": _float(si, "diaHole"),
        "md_csg_last_m": _float(si, "mdCsgLast"),
        "tvd_csg_last_m": _float(si, "tvdCsgLast"),
        "dist_drill_m": _float(si, "distDrill"),
        "water_depth_m": _float(si, "waterDepth"),
        "elev_kelly_m": _float(si, "elevKelly"),
        "rop_current_m_per_hr": _float(si, "ropCurrent"),
        "summary_24hr": _text(si, "sum24Hr"),
        "forecast_24hr": _text(si, "forecast24Hr"),
    }


def _parse_activities(report, well: str, date: str) -> list[dict]:
    """Parse all activity elements."""
    results = []
    for act in report.findall("witsml:activity", NS):
        results.append({
            "well": well,
            "date": date,
            "start_time": _text(act, "dTimStart"),
            "end_time": _text(act, "dTimEnd"),
            "depth_m": _float(act, "md"),
            "phase": _text(act, "phase"),
            "activity_code": _text(act, "proprietaryCode"),
            "state": _text(act, "state"),
            "state_detail": _text(act, "stateDetailActivity"),
            "comments": _text(act, "comments"),
        })
    return results


def _parse_fluids(report, well: str, date: str) -> list[dict]:
    """Parse all fluid elements."""
    results = []
    for fl in report.findall("witsml:fluid", NS):
        results.append({
            "well": well,
            "date": date,
            "mud_type": _text(fl, "type"),
            "mud_class": _text(fl, "mudClass"),
            "location_sample": _text(fl, "locationSample"),
            "density_gcc": _float(fl, "density"),
            "pv_mPas": _float(fl, "pv"),
            "yp_Pa": _float(fl, "yp"),
            "vis_funnel_s": _float(fl, "visFunnel"),
        })
    return results


def _parse_surveys(report, well: str, date: str) -> list[dict]:
    """Parse all surveyStation elements."""
    results = []
    for sv in report.findall("witsml:surveyStation", NS):
        results.append({
            "well": well,
            "date": date,
            "md_m": _float(sv, "md"),
            "tvd_m": _float(sv, "tvd"),
            "inclination_deg": _float(sv, "incl"),
            "azimuth_deg": _float(sv, "azi"),
        })
    return results


def _parse_pore_pressure(report, well: str, date: str) -> list[dict]:
    """Parse porePressure elements if present."""
    results = []
    for pp in report.findall("witsml:porePressure", NS):
        results.append({
            "well": well,
            "date": date,
            "md_m": _float(pp, "md"),
            "tvd_m": _float(pp, "tvd"),
            "emw_gcc": _float(pp, "ecd"),
        })
    return results


def _build_text_corpus(
    status: Optional[dict], activities: list[dict], well: str, date: str
) -> list[dict]:
    """Build text documents for vector store indexing.

    Creates one document per activity comment and one for the 24hr summary.
    """
    docs = []

    if status and status.get("summary_24hr"):
        docs.append({
            "well": well,
            "date": date,
            "depth_m": status.get("md_m"),
            "doc_type": "summary_24hr",
            "text": status["summary_24hr"],
        })

    if status and status.get("forecast_24hr"):
        docs.append({
            "well": well,
            "date": date,
            "depth_m": status.get("md_m"),
            "doc_type": "forecast_24hr",
            "text": status["forecast_24hr"],
        })

    for act in activities:
        if act.get("comments"):
            docs.append({
                "well": well,
                "date": date,
                "depth_m": act.get("depth_m"),
                "doc_type": "activity",
                "activity_code": act.get("activity_code", ""),
                "text": act["comments"],
            })

    return docs


def parse_ddr_file(filepath: Path) -> dict:
    """Parse a single DDR XML file into structured data.

    Returns dict with keys: well, date, status, activities, fluids, surveys,
    wellbore_info, text_docs. Returns error key on failure.
    """
    well_name, date_str = parse_well_from_filename(filepath.name)

    try:
        tree = etree.parse(str(filepath))
    except etree.XMLSyntaxError as e:
        logger.warning("XML parse error in %s: %s", filepath.name, e)
        return {"well": well_name, "date": date_str, "error": str(e)}

    root = tree.getroot()
    report = root.find("witsml:drillReport", NS)
    if report is None:
        return {"well": well_name, "date": date_str, "error": "No drillReport element"}

    status = _parse_status(report, well_name, date_str)
    activities = _parse_activities(report, well_name, date_str)
    fluids = _parse_fluids(report, well_name, date_str)
    surveys = _parse_surveys(report, well_name, date_str)
    wellbore_info = _parse_wellbore_info(report, well_name, date_str)
    text_docs = _build_text_corpus(status, activities, well_name, date_str)

    return {
        "well": well_name,
        "date": date_str,
        "status": status,
        "activities": activities,
        "fluids": fluids,
        "surveys": surveys,
        "wellbore_info": wellbore_info,
        "text_docs": text_docs,
    }


def parse_all_ddrs(ddr_dir: Optional[Path] = None) -> dict:
    """Parse all DDR XML files in the directory.

    Returns dict with keys:
        statuses, activities, fluids, surveys, wellbore_infos, text_docs, errors
    Each is a list of dicts ready for DuckDB insertion.
    """
    ddr_dir = ddr_dir or DDR_DIR
    xml_files = sorted(ddr_dir.glob("*.xml"))
    logger.info("Found %d DDR XML files to parse", len(xml_files))

    all_statuses = []
    all_activities = []
    all_fluids = []
    all_surveys = []
    all_wellbore_infos = []
    all_text_docs = []
    errors = []

    for i, filepath in enumerate(xml_files):
        if (i + 1) % 200 == 0:
            logger.info("Parsed %d / %d DDR files...", i + 1, len(xml_files))

        result = parse_ddr_file(filepath)

        if "error" in result:
            errors.append({"file": filepath.name, "error": result["error"]})
            continue

        if result["status"]:
            all_statuses.append(result["status"])
        all_activities.extend(result["activities"])
        all_fluids.extend(result["fluids"])
        all_surveys.extend(result["surveys"])
        if result["wellbore_info"]:
            all_wellbore_infos.append(result["wellbore_info"])
        all_text_docs.extend(result["text_docs"])

    logger.info(
        "DDR parsing complete: %d statuses, %d activities, %d fluids, "
        "%d surveys, %d wellbore records, %d text docs, %d errors",
        len(all_statuses), len(all_activities), len(all_fluids),
        len(all_surveys), len(all_wellbore_infos), len(all_text_docs),
        len(errors),
    )

    return {
        "statuses": all_statuses,
        "activities": all_activities,
        "fluids": all_fluids,
        "surveys": all_surveys,
        "wellbore_infos": all_wellbore_infos,
        "text_docs": all_text_docs,
        "errors": errors,
    }
