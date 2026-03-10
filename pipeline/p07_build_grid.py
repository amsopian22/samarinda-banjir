"""
pipeline/07_build_grid.py
Membangun titik-titik grid sampling di seluruh area Samarinda.
Setiap titik akan mendapatkan nilai elevasi, slope, dan jarak ke sungai.
Output: data/processed/grid_features.gpkg (CRS: EPSG:32750)
"""

import os
import sys
import numpy as np
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import (
    BBOX_SAMARINDA, CRS_GEO, CRS_UTM, GRID_SPACING_M,
    PATH_GRID_FEAT, PATH_BOUNDARY, PATH_RAINFALL
)
from pipeline.fetch_elevation import fetch_elevation_for_points_safe


def build_grid():
    import geopandas as gpd
    from shapely.geometry import Point
    import pandas as pd

    print("[07] Membangun grid sampling titik untuk Samarinda...")

    # --- Muat batas wilayah Samarinda ---
    try:
        boundary = gpd.read_file(PATH_BOUNDARY).to_crs(CRS_UTM)
        boundary_union = boundary.geometry.unary_union
        print(f"[07]   Batas wilayah dimuat dari {PATH_BOUNDARY}")
    except Exception as e:
        print(f"[07] ⚠️  Batas tidak ditemukan ({e}). Menggunakan bounding box.")
        from shapely.geometry import box
        min_lon, min_lat, max_lon, max_lat = BBOX_SAMARINDA
        # Buat dummy boundary dari bounding box
        dummy_gdf = gpd.GeoDataFrame(
            {"geometry": [box(min_lon, min_lat, max_lon, max_lat)]},
            crs=CRS_GEO
        ).to_crs(CRS_UTM)
        boundary_union = dummy_gdf.geometry.iloc[0]

    # --- Buat grid titik dalam UTM ---
    bounds = boundary_union.bounds  # (minx, miny, maxx, maxy) dalam meter
    xs = np.arange(bounds[0], bounds[2], GRID_SPACING_M)
    ys = np.arange(bounds[1], bounds[3], GRID_SPACING_M)

    total_potential = len(xs) * len(ys)
    print(f"[07]   Grid potensial: {len(xs)} x {len(ys)} = {total_potential} titik")

    # --- Filter titik yang ada di dalam batas wilayah ---
    points = []
    print("[07]   Memfilter titik di dalam batas wilayah...")
    for x in xs:
        for y in ys:
            pt = Point(x, y)
            if boundary_union.contains(pt):
                points.append(pt)

    print(f"[07]   Titik valid dalam batas wilayah: {len(points)}")
    if len(points) == 0:
        raise ValueError("Tidak ada titik yang masuk dalam batas wilayah!")

    # --- Buat GeoDataFrame grid ---
    grid_gdf = gpd.GeoDataFrame({"geometry": points}, crs=CRS_UTM)
    grid_gdf_wgs84 = grid_gdf.to_crs(CRS_GEO)
    grid_gdf["lon"] = grid_gdf_wgs84.geometry.x
    grid_gdf["lat"] = grid_gdf_wgs84.geometry.y

    # --- Ambil nilai elevasi dari OpenTopoData API ---
    lats = grid_gdf["lat"].tolist()
    lons = grid_gdf["lon"].tolist()

    print(f"[07]   Mengambil elevasi untuk {len(lats)} titik dari API...")
    elevations = fetch_elevation_for_points_safe(lats, lons)
    grid_gdf["elevation"] = elevations

    # --- Tambahkan curah hujan time-series ---
    try:
        with open(PATH_RAINFALL, "r") as f:
            rain_data = json.load(f)
        grid_gdf["rain_today"] = rain_data.get("rain_today", 25.0)
        grid_gdf["rain_h_minus_1"] = rain_data.get("rain_h_minus_1", 20.0)
        grid_gdf["rain_h_minus_2"] = rain_data.get("rain_h_minus_2", 15.0)
        grid_gdf["rain_h_minus_3"] = rain_data.get("rain_h_minus_3", 10.0)
        
        # Backward compatibility jika visualisasi lama masih butuh rainfall_mm
        grid_gdf["rainfall_mm"] = rain_data.get("rain_today", 25.0)
    except Exception:
        grid_gdf["rain_today"] = 25.0
        grid_gdf["rain_h_minus_1"] = 20.0
        grid_gdf["rain_h_minus_2"] = 15.0
        grid_gdf["rain_h_minus_3"] = 10.0
        grid_gdf["rainfall_mm"] = 25.0

    # --- Simpan ke GeoPackage ---
    os.makedirs(os.path.dirname(PATH_GRID_FEAT), exist_ok=True)
    grid_gdf.to_file(PATH_GRID_FEAT, driver="GPKG")
    print(f"[07] ✅ Grid {len(grid_gdf)} titik disimpan ke {PATH_GRID_FEAT}")
    print(f"[07]    Elevasi: min={min(elevations):.1f}m, max={max(elevations):.1f}m")
    return grid_gdf


if __name__ == "__main__":
    build_grid()
