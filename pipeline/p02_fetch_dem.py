"""
pipeline/02_fetch_dem.py
Mengunduh Digital Elevation Model (DEM) SRTM untuk wilayah Samarinda.
Menggunakan SRTM Tile Grabber dari cgiar.org (Format GeoTIFF).
Output: data/dem/samarinda_dem.tif

CATATAN: File DEM ~60-100MB. Hanya perlu diunduh sekali.
"""

import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import BBOX_SAMARINDA, PATH_DEM

# Koordinat tile SRTM yang mencakup Samarinda (CGIAR grid tile 49_09 dan 49_10)
# SRTM CGIAR-CSI tile yang mencakup area Kalimantan Timur:
SRTM_TILE_URLS = [
    "https://srtm.csi.cgiar.org/wp-content/uploads/files/srtm_5x5/TIFF/srtm_49_09.zip",
    "https://srtm.csi.cgiar.org/wp-content/uploads/files/srtm_5x5/TIFF/srtm_49_08.zip",
]

# Alternatif: OpenTopography (butuh API Key gratis - daftar di opentopodata.org)
OPENTOPO_URL = "https://api.opentopodata.org/v1/srtm30m"


def fetch_dem_opentopodata_check():
    """
    Cek apakah OpenTopoData tersedia sebagai alternatif ringan.
    Endpoint ini mengembalikan nilai titik, bukan raster, namun bisa digunakan 
    untuk grid sampling langsung (menghindari unduhan file besar).
    """
    test_url = f"{OPENTOPO_URL}?locations=-0.5022,117.1536"
    try:
        r = requests.get(test_url, timeout=10)
        r.raise_for_status()
        data = r.json()
        elev = data["results"][0]["elevation"]
        print(f"[02] ✅ OpenTopoData tersedia. Elevasi pusat Samarinda: {elev}m")
        return True
    except Exception as e:
        print(f"[02] ⚠️  OpenTopoData tidak tersedia: {e}")
        return False


def fetch_elevation_for_points(lats, lons, batch_size=99):
    """
    Mengambil nilai elevasi dari OpenTopoData untuk list titik koordinat.
    Gratis, tanpa unduhan file besar, ideal untuk Apple M3 8GB.
    API limit: 100 titik per request.
    """
    import math
    elevations = []
    total_batches = math.ceil(len(lats) / batch_size)

    print(f"[02] Mengambil elevasi untuk {len(lats)} titik dalam {total_batches} batch...")

    for i in range(0, len(lats), batch_size):
        batch_lats = lats[i:i+batch_size]
        batch_lons = lons[i:i+batch_size]
        locations = "|".join([f"{la},{lo}" for la, lo in zip(batch_lats, batch_lons)])

        try:
            r = requests.get(
                OPENTOPO_URL,
                params={"locations": locations, "interpolation": "bilinear"},
                timeout=30
            )
            r.raise_for_status()
            data = r.json()
            batch_elev = [res["elevation"] if res["elevation"] is not None else 0
                          for res in data["results"]]
            elevations.extend(batch_elev)
            batch_num = (i // batch_size) + 1
            if batch_num % 5 == 0 or batch_num == total_batches:
                print(f"[02]   Progress: batch {batch_num}/{total_batches} selesai")
        except Exception as e:
            print(f"[02] ⚠️  Batch {i//batch_size + 1} gagal: {e}. Menggunakan elevasi 0.")
            elevations.extend([0.0] * len(batch_lats))

    return elevations


def run():
    """
    Strategi utama fetch DEM menggunakan OpenTopoData point API.
    File grid titik akan dibuat oleh 07_build_grid.py dan digunakan oleh script ini.
    """
    print("[02] ✅ Modul DEM aktif. Elevasi akan diambil per-titik via OpenTopoData")
    print("[02]    saat pipeline grid (07_build_grid.py) berjalan untuk efisiensi RAM.")
    available = fetch_dem_opentopodata_check()
    if available:
        os.makedirs(os.path.dirname(PATH_DEM), exist_ok=True)
        # Tandai bahwa DEM tersedia via API (tidak perlu download file TIF besar)
        with open("data/dem/dem_source.txt", "w") as f:
            f.write("source: opentopodata_api\nurl: https://api.opentopodata.org/v1/srtm30m\n")
        print("[02] ✅ Sumber DEM dicatat. Tidak perlu unduh file ~100MB.")
    return available


if __name__ == "__main__":
    run()
