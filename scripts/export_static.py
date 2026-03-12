"""
export_static.py
================
Script untuk mengkonversi semua data pipeline (GeoPackage, prediksi model,
curah hujan Open-Meteo, TMA) menjadi file JSON statis yang siap di-serve
oleh Vercel tanpa perlu backend API sama sekali.

Jalankan sekali secara manual untuk validasi:
  conda activate agentic_ai
  python scripts/export_static.py

Atau biarkan GitHub Actions yang menjalankannya secara otomatis setiap hari.
"""

import os
import json
import math
import requests
from datetime import date, timedelta

# ───────────────────────────────────────────────
# Paths
# ───────────────────────────────────────────────
ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "dashboard", "public", "data")
os.makedirs(OUT_DIR, exist_ok=True)

print("=" * 60)
print("  Samarinda Flood · Static JSON Export")
print("=" * 60)

# ───────────────────────────────────────────────
# 1. GRID PREDIKSI BANJIR (GeoPackage → GeoJSON)
# ───────────────────────────────────────────────
try:
    import geopandas as gpd

    PATH_GRID   = os.path.join(ROOT, "data", "processed", "grid_features.gpkg")
    PATH_SUNGAI = os.path.join(ROOT, "data", "processed", "sungai_samarinda.gpkg")
    TOOLTIP_COLS = [
        "geometry", "p_flood_pred", "impact_category",
        "elevation", "slope_deg", "dist_sungai_m", "cn_score",
        "pop_density_km2", "impact_score",
        "rain_today", "rain_h_minus_1", "rain_h_minus_2", "rain_h_minus_3"
    ]

    print("\n[1/4] Membaca grid prediksi banjir...")
    gdf_grid = gpd.read_file(PATH_GRID).to_crs("EPSG:4326")
    cols = [c for c in gdf_grid.columns if c in TOOLTIP_COLS]
    grid_json = json.loads(gdf_grid[cols].to_json())

    # Serialisasi aman (handle NaN/Inf dari sklearn)
    def sanitize(obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(v) for v in obj]
        return obj

    grid_json = sanitize(grid_json)
    out_path = os.path.join(OUT_DIR, "grid.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(grid_json, f, ensure_ascii=False, separators=(",", ":"))
    size_kb = os.path.getsize(out_path) / 1024
    print(f"   ✅ grid.json — {len(grid_json['features'])} fitur, {size_kb:.0f} KB")

    print("\n[2/4] Membaca data sungai...")
    gdf_sungai = gpd.read_file(PATH_SUNGAI).to_crs("EPSG:4326")
    sungai_cols = [c for c in gdf_sungai.columns if c in ["geometry","name","level_m"]]
    sungai_json = sanitize(json.loads(gdf_sungai[sungai_cols].to_json()))
    sungai_path = os.path.join(OUT_DIR, "sungai.json")
    with open(sungai_path, "w", encoding="utf-8") as f:
        json.dump(sungai_json, f, ensure_ascii=False, separators=(",", ":"))
    print(f"   ✅ sungai.json — {len(sungai_json['features'])} fitur")

    # Hitung juga summary statistik
    features = grid_json.get("features", [])
    counts   = {"Aman": 0, "Waspada": 0, "Rawan": 0, "Parah": 0}
    high_risk = 0
    prob_sum  = 0.0
    for feat in features:
        p = feat.get("properties", {}) or {}
        cat = p.get("impact_category", "Aman")
        if cat in counts:
            counts[cat] += 1
        prob = p.get("p_flood_pred") or 0
        prob_sum += prob
        if prob >= 0.7:
            high_risk += 1
    total = max(len(features), 1)
    summary = {
        "total_grid":    total,
        "distribution":  counts,
        "pct_high_risk": round(high_risk / total * 100, 1),
        "avg_prob":      round(prob_sum / total, 3),
        "generated_at":  date.today().isoformat()
    }
    with open(os.path.join(OUT_DIR, "summary.json"), "w") as f:
        json.dump(summary, f)
    print(f"   ✅ summary.json — Risiko Tinggi: {summary['pct_high_risk']}%")

except Exception as e:
    print(f"   ❌ Gagal ekspor GeoPackage: {e}")

# ───────────────────────────────────────────────
# 3. DATA CUACA OPEN-METEO (7 hari)
# ───────────────────────────────────────────────
def wmo_to_label(code):
    if code is None:    return "Tidak Diketahui"
    if code == 0:       return "Cerah"
    if code < 10:       return "Berawan Sebagian"
    if code < 30:       return "Berawan"
    if code < 50:       return "Berkabut"
    if code < 60:       return "Gerimis"
    if code < 70:       return "Hujan"
    if code < 80:       return "Hujan Salju"
    if code < 90:       return "Hujan Lebat"
    return "Badai Petir"

print("\n[3/4] Mengambil data cuaca Open-Meteo...")
try:
    today_d = date.today()
    start   = (today_d - timedelta(days=6)).isoformat()
    end     = today_d.isoformat()
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude=-0.5022&longitude=117.1536"
        f"&daily=precipitation_sum,weathercode"
        f"&timezone=Asia/Makassar"
        f"&start_date={start}&end_date={end}"
    )
    resp = requests.get(url, timeout=15)
    data = resp.json()
    daily   = data.get("daily", {})
    dates   = daily.get("time", [])
    precips = daily.get("precipitation_sum", [])
    codes   = daily.get("weathercode", [])

    history = [
        {
            "date":     d,
            "rain_mm":  round(p, 1) if p is not None else 0.0,
            "wmo_code": c,
            "label":    wmo_to_label(c)
        }
        for d, p, c in zip(dates, precips, codes)
    ]

    weather_payload = {
        "today":     history[-1]   if history else {},
        "h_minus_1": history[-2]["rain_mm"] if len(history) >= 2 else 0,
        "h_minus_2": history[-3]["rain_mm"] if len(history) >= 3 else 0,
        "h_minus_3": history[-4]["rain_mm"] if len(history) >= 4 else 0,
        "avg_7d":    round(sum(d["rain_mm"] for d in history) / max(len(history), 1), 1),
        "history":   history
    }
    with open(os.path.join(OUT_DIR, "weather.json"), "w") as f:
        json.dump(weather_payload, f)
    print(f"   ✅ weather.json — Hari ini: {weather_payload['today'].get('rain_mm', 0)} mm")
except Exception as e:
    print(f"   ❌ Gagal ambil cuaca: {e}")

# ───────────────────────────────────────────────
# 4. DATA TMA SUNGAI (Dari GeoPackage Sebelumnya)
# ───────────────────────────────────────────────
print("\n[4/4] Menyusun data TMA sungai...")
try:
    tma_mahakam = 2.30
    tma_karang  = 1.80
    
    if 'gdf_sungai' in locals():
        # Ambil langsung dari data spasial yang sudah diolah p04_fetch_river.py
        mhk = gdf_sungai[gdf_sungai["name"].str.contains("Mahakam", case=False, na=False)]
        krg = gdf_sungai[gdf_sungai["name"].str.contains("Karang", case=False, na=False)]
        if not mhk.empty:
            tma_mahakam = float(mhk["level_m"].mean())
        if not krg.empty:
            tma_karang = float(krg["level_m"].mean())

    def tma_status(level, siaga, waspada, normal):
        if level >= siaga:   return "Siaga"
        if level >= waspada: return "Waspada"
        if level >= normal:  return "Normal"
        return "Rendah"

    tma_payload = {
        "mahakam": {
            "level_m": round(tma_mahakam, 2),
            "status":  tma_status(tma_mahakam, 5.0, 4.0, 3.0),
            "siaga_m": 5.0
        },
        "karang_mumus": {
            "level_m": round(tma_karang, 2),
            "status":  tma_status(tma_karang, 3.0, 2.5, 1.5),
            "siaga_m": 3.0
        },
        "timestamp": date.today().isoformat()
    }
except Exception as e:
    print(f"   ❌ Gagal menyusun data TMA: {e}")
    tma_payload = {
        "mahakam":      {"level_m": 2.30, "status": "Normal", "siaga_m": 5.0},
        "karang_mumus": {"level_m": 1.80, "status": "Normal", "siaga_m": 3.0},
        "timestamp":    date.today().isoformat()
    }

with open(os.path.join(OUT_DIR, "tma.json"), "w") as f:
    json.dump(tma_payload, f)
print(f"   ✅ tma.json — Mahakam: {tma_payload['mahakam']['level_m']} m")

# ───────────────────────────────────────────────
# SELESAI
# ───────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"  ✅ Export selesai · {date.today()} · Output: {OUT_DIR}")
print("=" * 60)
