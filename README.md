# VibePune 🌆

**"Where should I rent in Pune?" — answered with ML, street imagery, and open data.**

Built for students and young professionals moving to Pune for its IT industry:
enter your office or college, and VibePune scores every candidate neighborhood
on what actually matters when picking a flat — commute by public transport,
street-level vibe (greenery, liveliness, calmness, upkeep), daily essentials
nearby, air quality, and model-estimated perceived safety.

Under the hood: computer vision on Mapillary street imagery (segmentation +
zero-shot CLIP + detection), OpenStreetMap features, the community PMPML GTFS
feed for bus routing, and station-interpolated AQI — fused into per-hex scores
on an interactive map. Inspired by MIT's Place Pulse urban-perception research.

> 🚧 Status: Phase 1-2 (data layer). Roadmap below.

## How it works

```
Mapillary imagery ─┐
                   ├─► per-image features ─► H3 hex aggregation ─► vibe scores ─► interactive map
OpenStreetMap ─────┘
```

Per-image features come from three model families (all pretrained, zero cost):

1. **Semantic segmentation** (SegFormer, Cityscapes) → % vegetation, sky, road, building pixels
2. **Zero-shot CLIP scoring** → images scored against natural-language vibe prompts
   (see `config.yaml → vibe_dimensions`)
3. **Object detection** (YOLOv8) → people / vehicle / shopfront counts

Heavy ML runs offline in Google Colab; the deployed app only serves
precomputed scores, so the whole system runs on free tiers end to end.

## Project structure

```
vibepune/
├── config.yaml              # study areas, vibe dimensions, sampling params
├── src/vibepune/
│   ├── config.py            # config loader
│   ├── mapillary_client.py  # Mapillary Graph API v4 client
│   ├── check_coverage.py    # Phase 1: imagery coverage report per area
│   └── sample_points.py     # Phase 2: sample points along OSM road network
├── notebooks/               # Colab notebooks for the ML pipeline (Phase 3)
├── app/                     # Streamlit app (Phase 5)
└── data/                    # raw images + processed features (gitignored)
```

## Quickstart (Phase 1)

```bash
git clone https://github.com/<you>/vibepune && cd vibepune
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Get a free Mapillary client token:
#    https://www.mapillary.com/dashboard/developers  → create app → copy Client Token
cp .env.example .env   # paste your token inside

# 2. Run the coverage check
cd src && python -m vibepune.check_coverage
```

This prints an imagery count per study area and writes
`data/processed/coverage_report.csv`. Areas flagged **THIN** need a wider
radius, a substitute area, or self-captured imagery via the Mapillary app.


## Feature tiers

**MVP (v1.0):** vibe hex-map (5 dimensions) · commute time to a user-entered
destination (PMPML GTFS + OpenTripPlanner) · essentials score (OSM POIs) ·
AQI per area (WAQI stations, IDW-interpolated) · personalized weight sliders

**v1.1:** commute isochrones ("show every area within 45 min of my office") ·
side-by-side area comparison + shareable report card

**v1.2:** monsoon flood-risk layer (elevation + river proximity) · perceived
safety (Place Pulse transfer learning, clearly labeled as model-estimated,
NOT crime data) · quiet-vs-happening lifestyle toggle · noise proxy ·
indicative rent ranges (manually curated, no scraping)

## Roadmap

- [x] **Phase 1 — Scoping**: define vibe dimensions, pick 8 contrasting areas, verify Mapillary coverage
- [ ] **Phase 2 — Data layer**: sample road network (50 m spacing), match & download nearest images, pull OSM POI features, PMPML GTFS transit metrics (`vibepune.transit`), AQI stations (`vibepune.aqi`)
- [ ] **Phase 3 — ML pipeline**: segmentation + CLIP + detection over all images (Colab)
- [ ] **Phase 4 — Aggregation**: H3 hex binning, normalization, composite VibeScore, validation
- [ ] **Phase 5 — App (MVP)**: Streamlit hex map, destination input + commute times, weight sliders, image drill-down
- [ ] **Phase 6 — Deploy**: Streamlit Community Cloud / HF Spaces, demo GIF, write-up
- [ ] **v1.1+**: isochrones, comparison report cards, flood risk, perceived safety, temporal change analysis

## Data & licensing

- Imagery: [Mapillary](https://www.mapillary.com) (CC-BY-SA). Image files are
  processed locally and **not** redistributed in this repo.
- Map data: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL), via OSMnx.
- Scores are model-derived perceptions, not objective measures of any
  neighborhood's quality or safety.

## License

MIT
