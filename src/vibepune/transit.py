"""v2: Public-transport access metrics from the PMPML GTFS feed.

Data source: community-maintained GTFS for PMPML buses (Pune + PCMC),
built from the official Apli-PMPML API — https://github.com/croyla/pmpml-gtfs

This module handles the *static* transit layer (stop access, route density).
Full door-to-door routing + isochrones ("show me everywhere within 45 min of
my office") is done with OpenTripPlanner using this same GTFS file + an OSM
extract — see notebooks/otp_setup.md for the recipe.

Usage:
    python -m vibepune.transit            # download GTFS + compute metrics

Outputs:
    data/raw/gtfs/                        # extracted GTFS feed
    data/processed/transit_access.csv    # per-area stop access metrics
"""
from __future__ import annotations

import io
import math
import zipfile
from pathlib import Path

import pandas as pd
import requests

from .config import DATA_PROCESSED, PROJECT_ROOT, get_study_areas, load_config

GTFS_DIR = PROJECT_ROOT / "data" / "raw" / "gtfs"


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in meters."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def download_gtfs(cfg: dict) -> Path:
    """Download and extract the PMPML GTFS zip (skips if already present)."""
    GTFS_DIR.mkdir(parents=True, exist_ok=True)
    stops_file = GTFS_DIR / "stops.txt"
    if stops_file.exists():
        print(f"GTFS already present at {GTFS_DIR}")
        return GTFS_DIR

    url = cfg["transit"]["gtfs_url"]
    print(f"Downloading GTFS from {url} ...")
    resp = requests.get(url, timeout=120, allow_redirects=True)
    if resp.status_code != 200:
        raise RuntimeError(
            f"GTFS download failed (HTTP {resp.status_code}). "
            f"{cfg['transit']['gtfs_fallback_note']}"
        )
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(GTFS_DIR)
    print(f"Extracted GTFS to {GTFS_DIR}")
    return GTFS_DIR


def load_stops() -> pd.DataFrame:
    stops = pd.read_csv(GTFS_DIR / "stops.txt")
    return stops.dropna(subset=["stop_lat", "stop_lon"])


def routes_per_stop() -> pd.Series:
    """Count distinct routes serving each stop (a simple service-level proxy)."""
    trips = pd.read_csv(GTFS_DIR / "trips.txt", usecols=["route_id", "trip_id"])
    stop_times = pd.read_csv(GTFS_DIR / "stop_times.txt", usecols=["trip_id", "stop_id"])
    merged = stop_times.merge(trips, on="trip_id")
    return merged.groupby("stop_id")["route_id"].nunique()


def area_transit_metrics(cfg: dict) -> pd.DataFrame:
    """Per-study-area transit access summary."""
    stops = load_stops()
    try:
        service = routes_per_stop()
        stops = stops.merge(
            service.rename("n_routes"), left_on="stop_id", right_index=True, how="left"
        )
    except FileNotFoundError:
        stops["n_routes"] = None

    good_access_m = cfg["transit"]["good_stop_access_m"]
    rows = []
    for area in get_study_areas(cfg):
        d = stops.apply(
            lambda s: haversine_m(area.lat, area.lon, s.stop_lat, s.stop_lon), axis=1
        )
        in_area = stops[d <= area.radius_m]
        nearest = d.min() if len(d) else None
        rows.append({
            "area": area.name,
            "label": area.label,
            "stops_in_area": len(in_area),
            "stops_per_km2": round(
                len(in_area) / (math.pi * (area.radius_m / 1000) ** 2), 2
            ),
            "nearest_stop_m": round(nearest) if nearest is not None else None,
            "nearest_stop_within_walk": bool(nearest is not None and nearest <= good_access_m),
            "median_routes_per_stop": (
                float(in_area["n_routes"].median()) if len(in_area) else None
            ),
        })
    return pd.DataFrame(rows)


def main() -> None:
    cfg = load_config()
    download_gtfs(cfg)
    df = area_transit_metrics(cfg)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out = DATA_PROCESSED / "transit_access.csv"
    df.to_csv(out, index=False)
    print(df.to_string(index=False))
    print(f"\nWritten to {out}")


if __name__ == "__main__":
    main()
