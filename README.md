# CyanoSafe — Mobile HAB Safety Map

A mobile-optimized web app for reviewing harmful algal bloom (HAB) event monitoring data in California.

**Live app:** https://ggearheart.github.io/CyanoSafe_phone_demo/
**Desktop version:** https://ggearheart.github.io/CyanoSafe_demo/

## Overview

CyanoSafe helps users detect, track, and respond to cyanobacterial (blue-green algae) blooms that can pose risks to human health, wildlife, and water quality across California's lakes, reservoirs, and waterways. The primary data source is the Freshwater and Estuarine HAB (FHAB) program run by the CA State Water Resources Control Board. This dataset — https://data.ca.gov/dataset/surface-water-freshwater-harmful-algal-blooms — covers over 12 years of bloom investigations.

## Features

- Full-screen interactive map of CA bloom locations
- Color-coded advisory levels (Danger, Warning, Caution, Watch, Algal Mat)
- Filter by advisory level, status, county, regional water board, date range, cyanotoxins, and illness reports
- Bilingual interface (English / Spanish)
- Satellite cyano index from SFEI for water bodies with sensor coverage
- Print-ready advisory signs (English + Spanish)
- Report a Bloom section with QR code to FHAB reporting page
- Download filtered results as CSV
- Mobile-first layout: bottom sheet sidebar, full-screen map, touch-optimized tap targets

## Data Notes

Each event reflects a confirmed investigation of an alleged HAB. Most are triggered by public reports. Only a fraction involve full water sampling and laboratory analysis (microscopy, genetic testing, cyanotoxin chemistry) — so toxin-confirmed cases likely undercount true toxin presence across the dataset.

## Development

Serve locally:
```
python3 -m http.server 8001 --directory docs
```
Then open http://localhost:8001

Deploy: push to `main` — GitHub Pages serves from `docs/`.

## License

State of California — open data. See CA Water Boards for terms of use.
