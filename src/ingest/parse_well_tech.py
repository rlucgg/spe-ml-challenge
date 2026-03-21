"""Parse well technical data: formation tops (well picks) and perforations."""

import logging
import re
from pathlib import Path
from typing import Optional

from src.config import WELL_PICKS_FILE, PERFORATIONS_FILE, normalize_well_name

logger = logging.getLogger(__name__)


def parse_well_picks(filepath: Optional[Path] = None) -> list[dict]:
    """Parse Well_picks_Volve_v1.dat into formation tops list.

    Returns list of dicts with: well, surface_name, md_m, tvd_m, tvdss_m, twt_ms
    """
    filepath = filepath or WELL_PICKS_FILE
    if not filepath.exists():
        logger.warning("Well picks file not found: %s", filepath)
        return []

    logger.info("Parsing well picks from %s", filepath)
    results = []
    current_well = None

    with open(filepath, "r", encoding="latin-1") as f:
        for line in f:
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue

            well_match = re.match(r"^Well\s+(.+)$", line)
            if well_match:
                current_well = well_match.group(1).strip()
                continue

            if line.strip().startswith("Well name") or line.strip().startswith("---"):
                continue

            if current_well and line.strip():
                # Fixed-width format based on separator line positions:
                # Well name: cols 2-25, Surface: cols 27-66,
                # Obs#: 68-72, Qlf: 74-76, MD: 78-85, TVD: 87-94,
                # TVDSS: 96-103, TWT: 105-112
                if len(line) < 78:
                    continue
                try:
                    well_name = line[2:26].strip()
                    surface_name = line[27:67].strip()
                    if not well_name or not surface_name:
                        continue

                    def _safe_float(s):
                        s = s.strip()
                        if not s:
                            return None
                        try:
                            return float(s)
                        except ValueError:
                            return None

                    md = _safe_float(line[78:87]) if len(line) > 78 else None
                    tvd = _safe_float(line[87:96]) if len(line) > 87 else None
                    tvdss = _safe_float(line[96:105]) if len(line) > 96 else None
                    twt = _safe_float(line[105:114]) if len(line) > 105 else None

                    if md is not None:
                        results.append({
                            "well": normalize_well_name(well_name),
                            "surface_name": surface_name,
                            "md_m": md,
                            "tvd_m": tvd,
                            "tvdss_m": tvdss,
                            "twt_ms": twt,
                        })
                except (ValueError, IndexError):
                    continue

    logger.info("Parsed %d formation top records", len(results))
    return results


def parse_perforations(filepath: Optional[Path] = None) -> list[dict]:
    """Parse Well_perforations_Volve.dat into perforation intervals.

    Returns list of dicts with: well, md_top_m, md_base_m, tvd_top_m, tvd_base_m
    """
    filepath = filepath or PERFORATIONS_FILE
    if not filepath.exists():
        logger.warning("Perforations file not found: %s", filepath)
        return []

    logger.info("Parsing perforations from %s", filepath)
    results = []

    with open(filepath, "r", encoding="latin-1") as f:
        header_found = False
        for line in f:
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            if "Well name" in line or "---" in line:
                header_found = True
                continue
            if not header_found:
                if line.startswith("Well "):
                    continue
                continue

            if len(line) > 40:
                well_name = line[:24].strip()
                nums_str = line[24:].split()
                num_vals = []
                for n in nums_str:
                    try:
                        num_vals.append(float(n))
                    except ValueError:
                        pass

                if well_name and len(num_vals) >= 2:
                    results.append({
                        "well": normalize_well_name(well_name),
                        "md_top_m": num_vals[0] if len(num_vals) > 0 else None,
                        "md_base_m": num_vals[1] if len(num_vals) > 1 else None,
                        "tvd_top_m": num_vals[2] if len(num_vals) > 2 else None,
                        "tvd_base_m": num_vals[3] if len(num_vals) > 3 else None,
                    })

    logger.info("Parsed %d perforation records", len(results))
    return results
