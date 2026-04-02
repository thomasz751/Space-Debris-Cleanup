from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import re


@dataclass
class OrdemAzimuthRow:
    az_start_deg: int
    az_end_deg: int
    flux_by_threshold: Dict[str, float]


@dataclass
class OrdemSummary:
    year: Optional[int] = None
    perigee_alt_km: Optional[float] = None
    apogee_alt_km: Optional[float] = None
    inclination_deg: Optional[float] = None
    min_flux_by_threshold: Dict[str, float] = field(default_factory=dict)
    max_flux_by_threshold: Dict[str, float] = field(default_factory=dict)
    rows: List[OrdemAzimuthRow] = field(default_factory=list)

    def total_flux(self, threshold: str) -> float:
        """
        Returns total flux integrated over azimuth.
        ORDEM table values are in #/m^2/yr/deg and each row is a 1-degree bin,
        so summing rows gives total #/m^2/yr over all azimuth bins.
        """
        return sum(row.flux_by_threshold[threshold] for row in self.rows)

    def average_flux_per_degree(self, threshold: str) -> float:
        if not self.rows:
            return 0.0
        total_width = sum(row.az_end_deg - row.az_start_deg for row in self.rows)
        if total_width == 0:
            return 0.0
        return self.total_flux(threshold) / total_width

    def available_thresholds(self) -> List[str]:
        if not self.rows:
            return []
        return list(self.rows[0].flux_by_threshold.keys())

    def band_flux(self, lower_threshold: str, upper_threshold: str) -> float:
        """
        Converts cumulative thresholds into a differential band:
        band(lower, upper) = F(>lower) - F(>upper)

        Example:
            band_flux(">1cm", ">10cm") -> flux for 1cm to 10cm
        """
        return self.total_flux(lower_threshold) - self.total_flux(upper_threshold)


class OrdemParseError(Exception):
    pass


class OrdemParser:
    HEADER_RE = re.compile(
        r"Year:\s*(?P<year>\d+)\s+Perigee Altitude\s*=\s*(?P<perigee>[0-9.]+)\s+"
        r"Apogee Altitude\s*=\s*(?P<apogee>[0-9.]+)\s+inc\s*=\s*(?P<inc>[0-9.]+)"
    )

    NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:E[-+]?\d+)?", re.IGNORECASE)

    def parse_file(self, path: str | Path) -> OrdemSummary:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        return self.parse_text(text)

    def parse_text(self, text: str) -> OrdemSummary:
        lines = text.splitlines()
        summary = OrdemSummary()

        self._parse_metadata(lines, summary)
        thresholds, table_start_idx = self._find_table_header(lines)
        self._parse_table(lines, table_start_idx, thresholds, summary)

        if not summary.rows:
            raise OrdemParseError("No azimuth data rows were parsed from the ORDEM output.")

        return summary

    def _parse_metadata(self, lines: List[str], summary: OrdemSummary) -> None:
        for line in lines:
            match = self.HEADER_RE.search(line)
            if match:
                summary.year = int(match.group("year"))
                summary.perigee_alt_km = float(match.group("perigee"))
                summary.apogee_alt_km = float(match.group("apogee"))
                summary.inclination_deg = float(match.group("inc"))
                return

    def _find_table_header(self, lines):
        for i, line in enumerate(lines):
            parts = line.split()
            lowered = [p.lower() for p in parts]

            # Old azimuth-style format
            if len(parts) >= 3 and lowered[0] == "az" and lowered[1] == "1":
                thresholds = parts[2:]
                return {
                    "mode": "azimuth",
                    "thresholds": thresholds,
                    "table_start_idx": i,
                }

            # Spacecraft-mode format
            expected_prefix = [
                "x_ne", "y_ne", "x_se", "y_se", "x_sw",
                "y_sw", "x_nw", "y_nw", "x-mid", "y-mid"
            ]
            if len(parts) >= 16 and [p.lower() for p in parts[:10]] == expected_prefix:
                thresholds = parts[10:]
                return {
                    "mode": "spacecraft",
                    "thresholds": thresholds,
                    "table_start_idx": i,
                }

        raise OrdemParseError("Could not find supported ORDEM table header.")
    def _parse_table(
        self,
        lines: List[str],
        start_idx: int,
        thresholds: List[str],
        summary: OrdemSummary,
    ) -> None:
        """
        Parses:
        - Min. row
        - Max. row
        - Data rows
        """
        for line in lines[start_idx:]:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("------"):
                continue

            if stripped.startswith("Min.:"):
                values = self._extract_numeric_values(line)
                if len(values) < len(thresholds):
                    raise OrdemParseError("Min row does not contain enough threshold values.")
                summary.min_flux_by_threshold = {
                    th: val for th, val in zip(thresholds, values[-len(thresholds):])
                }
                continue

            if stripped.startswith("Max.:"):
                values = self._extract_numeric_values(line)
                if len(values) < len(thresholds):
                    raise OrdemParseError("Max row does not contain enough threshold values.")
                summary.max_flux_by_threshold = {
                    th: val for th, val in zip(thresholds, values[-len(thresholds):])
                }
                continue

            row = self._parse_data_row(line, thresholds)
            if row is not None:
                summary.rows.append(row)

    def _extract_numeric_values(self, line: str) -> List[float]:
        nums = self.NUMBER_RE.findall(line)
        return [float(x) for x in nums]

    def _parse_data_row(
        self,
        line: str,
        thresholds: List[str],
    ) -> Optional[OrdemAzimuthRow]:
        nums = self.NUMBER_RE.findall(line)
        if len(nums) < 2 + len(thresholds):
            return None

        try:
            az_start = int(float(nums[0]))
            az_end = int(float(nums[1]))
            flux_values = [float(x) for x in nums[2:2 + len(thresholds)]]
        except ValueError:
            return None

        flux_by_threshold = {
            threshold: value for threshold, value in zip(thresholds, flux_values)
        }

        return OrdemAzimuthRow(
            az_start_deg=az_start,
            az_end_deg=az_end,
            flux_by_threshold=flux_by_threshold,
        )