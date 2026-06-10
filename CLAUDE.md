# CyanoSafe Phone Demo

Mobile-optimized version of the CyanoSafe CA HAB Safety Map.

## Project overview
- Static site hosted on GitHub Pages (`docs/` folder)
- Main app: `docs/index.html` — all-in-one Leaflet.js map + sidebar
- Data: `docs/blooms.json` (3,476 FHAB records), `docs/wid_map.json` (SFEI satellite lookup)
- Backend (local dev only): `main.py` FastAPI server

## Key libraries
- Leaflet.js 1.9.4 (CDN)
- QRCode.js 1.0.0 (CDN)

## Data fields in blooms.json
`id, cid, name, county, rwb, lat, lon, obs, status, adv, detail, size, texture, location, landmark, wtype, wuse, resp, toxin, toxin_types, illness`

## Color palette (WCAG AA / colorblind-safe)
- Danger: `#B91C1C` | Warning: `#C2410C` | Caution: `#A16207`
- Watch: `#1D4ED8` | Mat: `#7E22CE` | Other: `#374151`
- CA Blue: `#003368` | CA Gold: `#FDB913`

## Development
Serve locally: `python3 -m http.server 8001 --directory docs`
Deploy: push to `main` branch — GitHub Pages serves `docs/`
