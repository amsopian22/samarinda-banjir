"""
pipeline/fetch_elevation.py
Helper modul untuk mengambil nilai elevasi dari OpenTopoData API.
Digunakan oleh 07_build_grid.py.
"""

import requests
import math


OPENTOPO_URL = "https://api.opentopodata.org/v1/srtm30m"


def fetch_elevation_for_points_safe(lats, lons, batch_size=99):
    """
    Mengambil nilai elevasi untuk list titik koordinat via OpenTopoData API.
    Memproses dalam batch, aman untuk M3 8GB.
    Jika API gagal untuk suatu batch, nilai 0.0 digunakan sebagai fallback.
    """
    elevations = []
    total_batches = math.ceil(len(lats) / batch_size)

    print(f"[DEM]  Mengambil elevasi untuk {len(lats)} titik dalam {total_batches} batch...")

    for i in range(0, len(lats), batch_size):
        batch_lats = lats[i:i+batch_size]
        batch_lons = lons[i:i+batch_size]
        locations  = "|".join([f"{la},{lo}" for la, lo in zip(batch_lats, batch_lons)])

        try:
            r = requests.get(
                OPENTOPO_URL,
                params={"locations": locations, "interpolation": "bilinear"},
                timeout=30
            )
            r.raise_for_status()
            data = r.json()
            batch_elev = [
                res["elevation"] if res.get("elevation") is not None else 0.0
                for res in data["results"]
            ]
            elevations.extend(batch_elev)

        except requests.exceptions.HTTPError as e:
            if "429" in str(e):
                # Rate limit - tunggu lalu coba lagi
                import time
                print(f"[DEM]  Rate limit! Menunggu 10 detik...")
                time.sleep(10)
                try:
                    r = requests.get(
                        OPENTOPO_URL,
                        params={"locations": locations, "interpolation": "bilinear"},
                        timeout=30
                    )
                    data = r.json()
                    batch_elev = [res.get("elevation") or 0.0 for res in data["results"]]
                    elevations.extend(batch_elev)
                except Exception:
                    elevations.extend([0.0] * len(batch_lats))
            else:
                print(f"[DEM] ⚠️  HTTP error pada batch {i//batch_size + 1}: {e}")
                elevations.extend([0.0] * len(batch_lats))

        except Exception as e:
            print(f"[DEM] ⚠️  Batch {i//batch_size + 1} gagal: {e}. Pakai elevasi 0.")
            elevations.extend([0.0] * len(batch_lats))

        batch_num = (i // batch_size) + 1
        if batch_num % 10 == 0 or batch_num == total_batches:
            print(f"[DEM]  Progress: batch {batch_num}/{total_batches} selesai")

    return elevations
