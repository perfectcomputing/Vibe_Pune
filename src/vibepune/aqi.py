"""v2: Air-quality layer — fetch station AQI and interpolate per area.

Free data: WAQI (aqicn.org). Get a free token at
https://aqicn.org/data-platform/token/ and put WAQI_TOKEN=... in your .env.
(OpenAQ is a drop-in alternative if you prefer fully-open data.)

Stations in Pune are sparse, so each study area gets an inverse-distance-
weighted (IDW) estimate from nearby stations — a defensible, explainable
interpolation you can discuss in interviews.

Usage:
    python -m vibepune.aqi

Output:
    data/processed/aqi_by_area.csv
"""
from __future__ import annotations

import math
import os

import pandas as pd
import requests

from .config import DATA_PROCESSED, PROJECT_ROOT, get_study_areas, load_config
from .transit import haversine_m


def get_waqi_token() -> str:
    token = os.environ.get("WAQI_TOKEN")
    if token:
        return token
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip().startswith("WAQI_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError(
        "WAQI token not found. Get one free at https://aqicn.org/data-platform/token/ "
        "and add WAQI_TOKEN=... to your .env"
    )


def fetch_stations(cfg: dict) -> pd.DataFrame:
    """All AQI stations inside the city bbox, with current AQI values."""
    min_lon, min_lat, max_lon, max_lat = cfg["city_bbox"]
    resp = requests.get(
        cfg["aqi"]["waqi_bounds_endpoint"],
        params={
            "token": get_waqi_token(),
            # WAQI expects lat1,lng1,lat2,lng2
            "latlng": f"{min_lat},{min_lon},{max_lat},{max_lon}",
        },
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != "ok":
        raise RuntimeError(f"WAQI error: {payload}")

    rows = []
    for st in payload.get("data", []):
        try:
            aqi = float(st["aqi"])  # can be "-" for offline stations
        except (ValueError, TypeError):
            continue
        rows.append({
            "station": st.get("station", {}).get("name"),
            "lat": st["lat"],
            "lon": st["lon"],
            "aqi": aqi,
        })
    df = pd.DataFrame(rows)
    print(f"{len(df)} live stations in bbox")
    return df


def idw_estimate(lat: float, lon: float, stations: pd.DataFrame, cfg: dict) -> dict:
    """Inverse-distance-weighted AQI at a point from nearby stations."""
    power = cfg["aqi"]["idw_power"]
    max_km = cfg["aqi"]["max_station_distance_km"]

    st = stations.copy()
    st["dist_m"] = st.apply(lambda s: haversine_m(lat, lon, s.lat, s.lon), axis=1)
    st = st[st.dist_m <= max_km * 1000]
    if st.empty:
        return {"aqi_idw": None, "n_stations_used": 0, "nearest_station_km": None}

    # a station essentially at the point wins outright
    if st.dist_m.min() < 100:
        s = st.loc[st.dist_m.idxmin()]
        return {
            "aqi_idw": round(s.aqi, 1),
            "n_stations_used": 1,
            "nearest_station_km": round(s.dist_m / 1000, 2),
        }

    w = 1.0 / (st.dist_m**power)
    return {
        "aqi_idw": round(float((st.aqi * w).sum() / w.sum()), 1),
        "n_stations_used": int(len(st)),
        "nearest_station_km": round(float(st.dist_m.min()) / 1000, 2),
    }


def main() -> None:
    cfg = load_config()
    stations = fetch_stations(cfg)
    rows = []
    for area in get_study_areas(cfg):
        est = idw_estimate(area.lat, area.lon, stations, cfg)
        rows.append({"area": area.name, "label": area.label, **est})
    df = pd.DataFrame(rows)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out = DATA_PROCESSED / "aqi_by_area.csv"
    df.to_csv(out, index=False)
    print(df.to_string(index=False))
    print(f"\nWritten to {out}")
    print("Note: AQI is a snapshot — for the app, fetch live or cache daily.")


if __name__ == "__main__":
    main()
