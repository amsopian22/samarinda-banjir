import geopandas as gpd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta

app = FastAPI(title="Samarinda Flood Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_GRID   = os.path.join(PROJECT_ROOT, "data", "processed", "grid_features.gpkg")
PATH_SUNGAI = os.path.join(PROJECT_ROOT, "data", "processed", "sungai_samarinda.gpkg")

# —— Cache di RAM ——
grid_geojson   = None
sungai_geojson = None


def load_geodata():
    global grid_geojson, sungai_geojson
    print("[API] Membaca GeoPackage...")
    gdf_grid   = gpd.read_file(PATH_GRID).to_crs("EPSG:4326")
    gdf_sungai = gpd.read_file(PATH_SUNGAI).to_crs("EPSG:4326")

    # Sertakan semua kolom untuk tooltip interaktif di frontend
    TOOLTIP_COLS = [
        "geometry", "p_flood_pred", "impact_category",
        "elevation", "slope_deg", "dist_sungai_m", "cn_score",
        "pop_density_km2", "impact_score",
        "rain_today", "rain_h_minus_1", "rain_h_minus_2", "rain_h_minus_3"
    ]
    cols_grid   = [c for c in gdf_grid.columns if c in TOOLTIP_COLS]
    cols_sungai = [c for c in gdf_sungai.columns if c in ["geometry","name","level_m"]]

    grid_geojson   = json.loads(gdf_grid[cols_grid].to_json())
    sungai_geojson = json.loads(gdf_sungai[cols_sungai].to_json())
    print("[API] Cache GeoJSON siap!")


@app.on_event("startup")
async def startup_event():
    load_geodata()


# ——————————————————————————————
# ENDPOINT GEOSPASIAL
# ——————————————————————————————
@app.get("/")
def read_root():
    return {"status": "ok", "message": "API Samarinda WebGIS siap digunakan"}

@app.get("/api/grid")
def get_grid():
    """Grid prediksi banjir 7965 titik"""
    return grid_geojson

@app.get("/api/sungai")
def get_sungai():
    """Garis vektor sungai Mahakam & Karang Mumus"""
    return sungai_geojson


# ——————————————————————————————
# ENDPOINT CUACA OPEN-METEO
# ——————————————————————————————
@app.get("/api/weather")
def get_weather():
    """Ambil data curah hujan 7 hari dari Open-Meteo (Samarinda: -0.5022, 117.1536)"""
    try:
        today = date.today()
        start = (today - timedelta(days=6)).isoformat()
        end   = today.isoformat()

        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude=-0.5022&longitude=117.1536"
            f"&daily=precipitation_sum,weathercode"
            f"&timezone=Asia/Makassar"
            f"&start_date={start}&end_date={end}"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})
        dates  = daily.get("time", [])
        precip = daily.get("precipitation_sum", [])
        codes  = daily.get("weathercode", [])

        # Buat seri historis 7 hari
        history = [
            {
                "date":       d,
                "rain_mm":    round(p, 1) if p is not None else 0.0,
                "wmo_code":   c,
                "label":      _wmo_to_label(c)
            }
            for d, p, c in zip(dates, precip, codes)
        ]

        today_entry  = history[-1]  if history else {}
        h_minus_1    = history[-2]["rain_mm"] if len(history) >= 2 else 0
        h_minus_2    = history[-3]["rain_mm"] if len(history) >= 3 else 0
        h_minus_3    = history[-4]["rain_mm"] if len(history) >= 4 else 0
        avg_7d       = round(sum(d["rain_mm"] for d in history) / max(len(history),1), 1)

        return {
            "today":     today_entry,
            "h_minus_1": h_minus_1,
            "h_minus_2": h_minus_2,
            "h_minus_3": h_minus_3,
            "avg_7d":    avg_7d,
            "history":   history
        }
    except Exception as e:
        return {"error": str(e)}


# ——————————————————————————————
# ENDPOINT TMA REAL-TIME (Web Scrape SIHKA)
# ——————————————————————————————
@app.get("/api/tma")
def get_tma():
    """Scrape TMA live dari hidrologi.id/duga-air"""
    try:
        hdrs = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get("https://hidrologi.id/duga-air", headers=hdrs, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        tma_mahakam    = None
        tma_karang     = None
        status_mahakam = "Normal"
        status_karang  = "Normal"

        rows = soup.select("table tr")
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.select("td")]
            if len(cells) < 3:
                continue
            name  = cells[0].upper()
            value = _extract_float(cells)
            if value is None:
                continue
            if "MAHAKAM" in name or "TENGGARONG" in name:
                if tma_mahakam is None:
                    tma_mahakam = value
            if "KARANG MUMUS" in name or "MUANG" in name or "LINGAI" in name:
                if tma_karang is None:
                    tma_karang = value

        # Fallback dummy jika scrape gagal
        tma_mahakam = tma_mahakam or 2.30
        tma_karang  = tma_karang  or 1.80

        # Klasifikasi status awalan
        status_mahakam = _tma_status(tma_mahakam, siaga=5.0, waspada=4.0, normal=3.0)
        status_karang  = _tma_status(tma_karang,  siaga=3.0, waspada=2.5, normal=1.5)

        return {
            "mahakam": {
                "level_m": round(tma_mahakam, 2),
                "status":  status_mahakam,
                "siaga_m": 5.0
            },
            "karang_mumus": {
                "level_m": round(tma_karang, 2),
                "status":  status_karang,
                "siaga_m": 3.0
            },
            "timestamp": date.today().isoformat()
        }
    except Exception as e:
        return {"error": str(e), "mahakam": {"level_m": 2.30, "status": "Normal", "siaga_m": 5.0},
                "karang_mumus": {"level_m": 1.80, "status": "Normal", "siaga_m": 3.0}}


# ——————————————————————————————
# ENDPOINT SUMMARY AREA TERDAMPAK
# ——————————————————————————————
@app.get("/api/summary")
def get_summary():
    """Hitung statistik ringkasan area dampak dari grid prediksi"""
    if not grid_geojson:
        return {"error": "Data belum dimuat"}
    features = grid_geojson.get("features", [])
    counts   = {"Aman": 0, "Waspada": 0, "Rawan": 0, "Parah": 0}
    high_risk = 0
    prob_sum  = 0.0
    for f in features:
        prop = f.get("properties", {})
        cat  = prop.get("impact_category", "Aman")
        if cat in counts:
            counts[cat] += 1
        p = prop.get("p_flood_pred", 0)
        prob_sum += p
        if p >= 0.7:
            high_risk += 1
    total = max(len(features), 1)
    return {
        "total_grid":    total,
        "distribution":  counts,
        "pct_high_risk": round(high_risk / total * 100, 1),
        "avg_prob":      round(prob_sum / total, 3)
    }


# ——————————————————————————————
# UTILITIES
# ——————————————————————————————
def _wmo_to_label(code):
    if code is None:      return "Tidak Diketahui"
    if code == 0:         return "Cerah"
    if code < 10:         return "Berawan Sebagian"
    if code < 30:         return "Berawan"
    if code < 50:         return "Berkabut"
    if code < 60:         return "Gerimis"
    if code < 70:         return "Hujan"
    if code < 80:         return "Hujan Salju"
    if code < 90:         return "Hujan Lebat"
    return "Badai Petir"

def _extract_float(cells):
    for cell in cells:
        try:
            return float(cell.replace(",", "."))
        except:
            continue
    return None

def _tma_status(level, siaga, waspada, normal):
    if level >= siaga:   return "Siaga"
    if level >= waspada: return "Waspada"
    if level >= normal:  return "Normal"
    return "Rendah"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_api:app", host="0.0.0.0", port=8000, reload=True)
