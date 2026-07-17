"""Phase 1: check Mapillary imagery coverage for each Pune study area.

Usage:
    python -m vibepune.check_coverage

Outputs:
    data/processed/coverage_report.csv   — per-area image counts & stats
    data/processed/coverage_images.csv   — one row per discovered image
Prints a go/no-go verdict per area so you can swap weak areas early.
"""
from __future__ import annotations

import csv
from collections import Counter

from .config import DATA_PROCESSED, get_study_areas, load_config
from .mapillary_client import MapillaryClient

# Minimum images for an area to be considered viable for the pipeline.
MIN_VIABLE_IMAGES = 150


def main() -> None:
    cfg = load_config()
    min_year = cfg["sampling"]["min_capture_year"]
    client = MapillaryClient(cfg=cfg)
    areas = get_study_areas(cfg)

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    report_rows: list[dict] = []
    all_images: list[dict] = []

    print(f"Checking Mapillary coverage for {len(areas)} study areas "
          f"(imagery from {min_year}+)...\n")

    for area in areas:
        rows = [
            MapillaryClient.parse_image(img)
            for img in client.images_in_bbox(area.bbox, min_year=min_year)
        ]
        for r in rows:
            r["area"] = area.name
        all_images.extend(rows)

        n = len(rows)
        years = Counter(r["year"] for r in rows if r["year"])
        n_pano = sum(1 for r in rows if r["is_pano"])
        n_flat = n - n_pano
        newest = max(years) if years else None
        verdict = "OK" if n_flat >= MIN_VIABLE_IMAGES else (
            "THIN — consider capturing imagery yourself or widening radius"
        )

        report_rows.append({
            "area": area.name,
            "label": area.label,
            "total_images": n,
            "flat_images": n_flat,
            "pano_images": n_pano,
            "newest_year": newest,
            "years_breakdown": dict(sorted(years.items())),
            "verdict": verdict,
        })
        print(f"  {area.label:38s} {n:6d} images "
              f"({n_flat} flat / {n_pano} pano), newest {newest}  -> {verdict}")

    # write per-area report
    report_path = DATA_PROCESSED / "coverage_report.csv"
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(report_rows[0].keys()))
        writer.writeheader()
        writer.writerows(report_rows)

    # write full image index (becomes the Phase 2 download manifest)
    images_path = DATA_PROCESSED / "coverage_images.csv"
    if all_images:
        with open(images_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_images[0].keys()))
            writer.writeheader()
            writer.writerows(all_images)

    total = sum(r["total_images"] for r in report_rows)
    thin = [r["label"] for r in report_rows if r["verdict"] != "OK"]
    print(f"\nTotal images discovered: {total}")
    print(f"Report written to {report_path}")
    print(f"Image index written to {images_path}")
    if thin:
        print(f"\nAreas needing attention: {', '.join(thin)}")
        print("Options: widen radius_m in config.yaml, pick a nearby area, "
              "or capture imagery with the Mapillary mobile app (great resume story).")


if __name__ == "__main__":
    main()
