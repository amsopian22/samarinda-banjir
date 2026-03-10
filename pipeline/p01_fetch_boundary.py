"""
pipeline/01_fetch_boundary.py
Mengunduh batas administratif Kota Samarinda dari Nominatim OSM.
Output: data/boundary/samarinda.geojson (CRS: EPSG:4326 & EPSG:32750)
"""

import requests
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import PATH_BOUNDARY, CRS_GEO, CRS_UTM

def fetch_boundary():
    print("[01] Mengunduh batas administratif Samarinda dari Nominatim OSM...")

    # Nominatim API: cari batas kota Samarinda
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "city": "Samarinda",
        "state": "Kalimantan Timur",
        "country": "Indonesia",
        "format": "geojson",
        "polygon_geojson": 1,
        "limit": 1
    }
    headers = {"User-Agent": "SamarindaHydroIntelligence/1.0"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get("features"):
            raise ValueError("Tidak ada hasil dari Nominatim. Gunakan fallback batas manual.")

        geojson_data = data
        os.makedirs(os.path.dirname(PATH_BOUNDARY), exist_ok=True)

        with open(PATH_BOUNDARY, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, ensure_ascii=False, indent=2)

        print(f"[01] ✅ Batas wilayah disimpan ke: {PATH_BOUNDARY}")
        return True

    except Exception as e:
        print(f"[01] ⚠️  Gagal dari Nominatim: {e}")
        print("[01] Menggunakan batas manual Samarinda sebagai fallback...")
        _create_fallback_boundary()
        return True


def _create_fallback_boundary():
    """Batas bounding-box manual Samarinda jika Nominatim gagal."""
    # Koordinat sederhana batas kota Samarinda (approx polygon)
    fallback_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Kota Samarinda", "source": "manual_fallback"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [116.75, -1.10], [117.70, -1.10],
                        [117.70,  0.05], [116.75,  0.05],
                        [116.75, -1.10]
                    ]]
                }
            }
        ]
    }
    os.makedirs(os.path.dirname(PATH_BOUNDARY), exist_ok=True)
    with open(PATH_BOUNDARY, "w", encoding="utf-8") as f:
        json.dump(fallback_geojson, f, indent=2)
    print(f"[01] ✅ Batas fallback manual disimpan ke: {PATH_BOUNDARY}")


if __name__ == "__main__":
    fetch_boundary()
