# OpenTripPlanner setup (commute routing + isochrones)

OTP gives door-to-door bus routing and isochrones ("everywhere reachable in
45 min") for free, running locally or in Colab. Recipe:

1. Get inputs into one folder, e.g. `otp/`:
   - `pmpml_gtfs.zip` — the GTFS feed (see `python -m vibepune.transit`)
   - `pune.osm.pbf` — OSM extract for Pune. Download a Maharashtra extract
     from Geofabrik (free) and clip it with `osmium extract -b 73.72,18.44,73.98,18.64`
2. Download the OTP shaded jar (otp-x.y.z-shaded.jar) from the
   OpenTripPlanner GitHub releases (free, Apache-2.0). Needs Java 17+.
3. Build + serve:
   `java -Xmx4G -jar otp-shaded.jar --build --serve otp/`
4. Query the REST API at http://localhost:8080 :
   - plan a trip: `/otp/routers/default/plan?fromPlace=18.51,73.85&toPlace=18.59,73.74&mode=TRANSIT,WALK`
   - isochrone:   `/otp/routers/default/isochrone?fromPlace=...&cutoffSec=2700`
5. For the deployed app: precompute commute times from each H3 hex centroid
   to a grid of common destinations (IT parks, universities), store as a
   lookup table -> the app stays static/free, no Java server in production.

Common destinations to precompute (add more in config later):
- Hinjewadi Phases 1-3, Magarpatta City, EON IT Park Kharadi, SP Infocity,
  Baner-Balewadi High Street, COEP, SPPU, Symbiosis Viman Nagar, FLAME, MIT-WPU
