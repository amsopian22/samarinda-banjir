"""
pipeline/06_compute_distance.py
Menghitung jarak terdekat setiap titik grid ke sungai terdekat.
Menggunakan geopandas.sjoin_nearest pada CRS UTM 50S (satuan meter).
Output: kolom 'dist_sungai_m' ditambahkan ke grid_features.gpkg
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import PATH_GRID_FEAT, PATH_RIVER, CRS_UTM


def compute_distance_to_river(grid_gdf, river_gdf):
    """
    Menghitung jarak terdekat setiap titik grid ke sungai menggunakan
    geopandas sjoin_nearest (efisien, tidak membutuhkan loop Python eksplisit).
    """
    import geopandas as gpd

    print("[06] Menghitung jarak titik grid ke sungai terdekat...")

    # Pastikan CRS sama (UTM 50S)
    if grid_gdf.crs != CRS_UTM:
        grid_gdf = grid_gdf.to_crs(CRS_UTM)
    if river_gdf.crs != CRS_UTM:
        river_gdf = river_gdf.to_crs(CRS_UTM)

    # Siapkan geometri sungai sebagai unified (satu multilinestring)
    from shapely.ops import unary_union
    river_union = unary_union(river_gdf.geometry)

    print(f"[06]   Menghitung distance dari {len(grid_gdf)} titik ke sungai...")

    # Hitung jarak dalam batch untuk hemat RAM
    BATCH_SIZE = 5000
    distances = []
    total = len(grid_gdf)

    for i in range(0, total, BATCH_SIZE):
        batch = grid_gdf.geometry.iloc[i:i+BATCH_SIZE]
        batch_dist = batch.distance(river_union).values
        distances.extend(batch_dist.tolist())
        if (i // BATCH_SIZE) % 5 == 0:
            print(f"[06]   Progress: {min(i+BATCH_SIZE, total)}/{total} titik selesai")

    grid_gdf["dist_sungai_m"] = distances
    min_d = min(distances)
    max_d = max(distances)
    print(f"[06] ✅ Jarak ke sungai dihitung. Range: {min_d:.0f}m - {max_d:.0f}m")
    return grid_gdf


def run():
    import geopandas as gpd

    if not os.path.exists(PATH_GRID_FEAT):
        print("[06] ⚠️  Grid features belum ada. Jalankan 07_build_grid.py dahulu.")
        return None
    if not os.path.exists(PATH_RIVER):
        print("[06] ⚠️  Data sungai belum ada. Jalankan 04_synthetic_river.py dahulu.")
        return None

    grid_gdf = gpd.read_file(PATH_GRID_FEAT)
    river_gdf = gpd.read_file(PATH_RIVER)

    grid_gdf = compute_distance_to_river(grid_gdf, river_gdf)
    grid_gdf.to_file(PATH_GRID_FEAT, driver="GPKG")
    print(f"[06] ✅ Kolom 'dist_sungai_m' disimpan ke {PATH_GRID_FEAT}")
    return grid_gdf


if __name__ == "__main__":
    run()
