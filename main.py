import math
import pandas as pd
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="CyanoSafe API")

DATA_DIR = "data"


def _clean(val):
    """Convert NaN/NaT to None for JSON serialization."""
    if val is None:
        return None
    try:
        if math.isnan(float(val)):
            return None
    except (TypeError, ValueError):
        pass
    v = str(val).strip()
    return None if v in ("nan", "NaT", "") else v


def load_blooms() -> list[dict]:
    reports = pd.read_csv(f"{DATA_DIR}/FHAB_reports_06092026.csv", low_memory=False)

    # Normalize column names (strip BOM, spaces)
    reports.columns = [c.strip().lstrip("﻿") for c in reports.columns]

    # Use Bloom_Longitude (prefer the non-duplicate column)
    lon_col = "Bloom_Longitude" if "Bloom_Longitude" in reports.columns else "Bloom Longitude"

    blooms = []
    for _, row in reports.iterrows():
        try:
            lat = float(row.get("Bloom_Latitude", ""))
            lon = float(row.get(lon_col, ""))
        except (TypeError, ValueError):
            continue
        if math.isnan(lat) or math.isnan(lon):
            continue

        blooms.append({
            "id":       _clean(row.get("Bloom_Report_ID")),
            "cid":      _clean(row.get("Case_ID")),
            "name":     _clean(row.get("Water_Body_Name")) or _clean(row.get("Official_Water_Body_Name")),
            "county":   _clean(row.get("County")),
            "rwb":      _clean(row.get("Regional_Water_Board")),
            "lat":      lat,
            "lon":      lon,
            "obs":      _clean(row.get("Observation_Date")),
            "status":   _clean(row.get("Case_Status")),
            "adv":      _clean(row.get("Reported_Advisory_Types")),
            "detail":   _clean(row.get("Advisory_Detail_Description")) or _clean(row.get("Advisory_Detail")),
            "size":     _clean(row.get("Bloom_Size")),
            "texture":  _clean(row.get("Bloom_Texture")),
            "location": _clean(row.get("Bloom_Location")),
            "landmark": _clean(row.get("Landmark")),
            "wtype":    _clean(row.get("Water_Body_Type")),
            "wuse":     _clean(row.get("Water_Body_Use")),
            "resp":     _clean(row.get("Response_Type")),
            "toxin":    "detected cyanotoxin" in (
                (row.get("Advisory_Detail_Description") or "") + " " + (row.get("AdvisoryDetail") or "")
            ).lower(),
        })

    return blooms


@app.get("/api/blooms")
def get_blooms():
    return load_blooms()


@app.get("/api/health")
def health():
    return {"status": "ok", "records": len(load_blooms())}


app.mount("/", StaticFiles(directory="docs", html=True), name="static")
