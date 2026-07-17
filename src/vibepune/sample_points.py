"""Phase 2 (bonus head start): sample points along the road network.

For each study area, downloads the OSM drive network with OSMnx and drops a
sample point every `point_spacing_m` meters along every street. These points
are later matched to their nearest Mapillary image.

Usage:
    python -m vibepune.sample_points

Output:
    data/processed/sample_points.parquet  (area, lat, lon, road_name, highway)

Note: OSMnx downloads from the Overpass API — free, but be polite (it caches
responses locally by default). Run this in Colab if your machine struggles.
"""
from __future__ import annotations

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.geometry import LineString

from .config import DATA_PROCESSED, get_study_areas, load_config

METRIC_CRS = "EPSG:32643"  # UTM zone 43N — meters, correct for Pune


def sample_along_line(line: LineString, spacing_m: float) -> list:
    """Return shapely Points every `spacing_m` along a (projected) line."""
    n = max(1, int(line.length // spacing_m))
    return [line.interpolate(i * spacing_m) for i in range(n + 1)]


def sample_area(area, spacing_m: float, network_type: str) -> gpd.GeoDataFrame:
    graph = ox.graph_from_point(
        (area.lat, area.lon), dist=area.radius_m, network_type=network_type
    )
    edges = ox.graph_to_gdfs(graph, nodes=False).to_crs(METRIC_CRS)

    records = []
    for _, edge in edges.iterrows():
        geom = edge.geometry
        if not isinstance(geom, LineString):
            continue
        highway = edge.get("highway")
        name = edge.get("name")
        for pt in sample_along_line(geom, spacing_m):
            records.append({
                "area": area.name,
                "geometry": pt,
                "road_name": name if isinstance(name, str) else None,
                "highway": highway if isinstance(highway, str) else str(highway),
            })

    gdf = gpd.GeoDataFrame(records, crs=METRIC_CRS).to_crs("EPSG:4326")
    gdf["lon"] = gdf.geometry.x
    gdf["lat"] = gdf.geometry.y
    # de-duplicate points that landed on shared intersections
    gdf = gdf.drop_duplicates(subset=["lon", "lat"]).reset_index(drop=True)
    return gdf


def main() -> None:
    cfg = load_config()
    spacing = float(cfg["sampling"]["point_spacing_m"])
    network_type = cfg["sampling"]["network_type"]

    frames = []
    for area in get_study_areas(cfg):
        print(f"Sampling {area.label}...")
        gdf = sample_area(area, spacing, network_type)
        print(f"  {len(gdf)} points")
        frames.append(gdf)

    out = pd.concat(frames, ignore_index=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = DATA_PROCESSED / "sample_points.parquet"
    out.drop(columns="geometry").to_parquet(out_path, index=False)
    print(f"\n{len(out)} total sample points -> {out_path}")


if __name__ == "__main__":
    main()
