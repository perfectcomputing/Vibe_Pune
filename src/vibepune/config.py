"""Load and validate VibePune project configuration."""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"


@dataclass
class StudyArea:
    name: str
    label: str
    lat: float
    lon: float
    radius_m: float
    expected_vibe: str = ""

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """(min_lon, min_lat, max_lon, max_lat) box around the center.

        Uses a simple equirectangular approximation, fine at city scale.
        """
        dlat = self.radius_m / 111_320.0
        dlon = self.radius_m / (111_320.0 * math.cos(math.radians(self.lat)))
        return (self.lon - dlon, self.lat - dlat, self.lon + dlon, self.lat + dlat)


def load_config(path: Path | str = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_study_areas(cfg: dict | None = None, include_disabled: bool = False) -> list[StudyArea]:
    """Return study areas. By default only those with enabled: true (pilot mode)."""
    cfg = cfg or load_config()
    areas = []
    for a in cfg["study_areas"]:
        if not include_disabled and not a.get("enabled", True):
            continue
        lat, lon = a["center"]
        areas.append(
            StudyArea(
                name=a["name"],
                label=a["label"],
                lat=lat,
                lon=lon,
                radius_m=a["radius_m"],
                expected_vibe=a.get("expected_vibe", ""),
            )
        )
    return areas


def get_mapillary_token() -> str:
    """Read the Mapillary client token from env or a local .env file."""
    token = os.environ.get("MAPILLARY_TOKEN")
    if token:
        return token
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("MAPILLARY_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError(
        "Mapillary token not found. Get a free client token at "
        "https://www.mapillary.com/dashboard/developers, then either "
        "`export MAPILLARY_TOKEN=MLY|...` or copy .env.example to .env and fill it in."
    )
