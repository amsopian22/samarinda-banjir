"""
pipeline/05_compute_slope.py
Menghitung nilai Slope (kemiringan lahan) dari nilai elevasi per titik.
Digunakan sebagai salah satu fitur input model prediksi banjir.
Strategy: Slope dihitung menggunakan finite-differences pada array numpy 
elevasi dari grid sampling (tanpa perlu file raster besar).
Output: kolom 'slope_deg' ditambahkan ke grid_features.gpkg
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import PATH_GRID_FEAT, CRS_UTM, GRID_SPACING_M


def compute_slope_from_elevation(gdf):
    """
    Menghitung slope dalam derajat dari nilai elevasi per-titik pada GeoDataFrame.
    Menggunakan pendekatan gradient dari koordinat UTM (satuan meter).
    """
    import geopandas as gpd

    print("[05] Menghitung Slope dari distribusi elevasi grid...")

    if "elevation" not in gdf.columns:
        raise ValueError("Kolom 'elevation' tidak ditemukan dalam GeoDataFrame.")

    # Ambil koordinat x, y dalam meter (UTM)
    x = gdf.geometry.x.values
    y = gdf.geometry.y.values
    z = gdf["elevation"].values.astype(float)

    # Estimasi gradien menggunakan perbedaan ke tetangga terdekat
    # Hitung gradien menggunakan scipy untuk data titik tak teratur
    try:
        from scipy.spatial import cKDTree
        from scipy.interpolate import griddata

        print("[05]   Menginterpolasi elevasi ke grid reguler untuk perhitungan gradien...")

        # Buat grid reguler
        xi = np.linspace(x.min(), x.max(), 100)
        yi = np.linspace(y.min(), y.max(), 100)
        xi_grid, yi_grid = np.meshgrid(xi, yi)

        # Interpolasi elevasi ke grid reguler
        zi = griddata((x, y), z, (xi_grid, yi_grid), method='linear', fill_value=0)

        # Hitung gradien pada grid reguler
        dx = xi[1] - xi[0]
        dy = yi[1] - yi[0]
        grad_y, grad_x = np.gradient(zi, dy, dx)

        # Interpolasi nilai slope kembali ke titik asli
        slope_rad = np.sqrt(grad_x**2 + grad_y**2)
        slope_deg_grid = np.degrees(np.arctan(slope_rad))

        # Ambil nilai slope untuk tiap titik asli
        slope_values = griddata(
            (xi_grid.ravel(), yi_grid.ravel()),
            slope_deg_grid.ravel(),
            (x, y),
            method='linear',
            fill_value=0.0
        )

    except Exception as e:
        print(f"[05] ⚠️  Interpolasi gradien gagal ({e}). Menggunakan slope konstan estimasi.")
        # Fallback: estimasi slope dari std elevasi dalam jendela terdekat
        from scipy.spatial import cKDTree
        tree = cKDTree(np.column_stack([x, y]))
        dist, idx = tree.query(np.column_stack([x, y]), k=min(8, len(x)))
        slope_values = np.zeros(len(x))
        for i in range(len(x)):
            neighbors_z = z[idx[i]]
            elev_diff    = np.abs(neighbors_z - z[i])
            slope_values[i] = np.degrees(np.arctan(elev_diff.mean() / (GRID_SPACING_M + 1e-6)))

    # Batasi nilai slope maksimum yang masuk akal
    slope_values = np.clip(slope_values, 0, 70)
    gdf["slope_deg"] = slope_values

    print(f"[05] ✅ Slope dihitung. Range: {slope_values.min():.2f}° - {slope_values.max():.2f}°")
    return gdf


def run():
    import geopandas as gpd
    if not os.path.exists(PATH_GRID_FEAT):
        print("[05] ⚠️  Grid features belum dibuat. Jalankan 07_build_grid.py terlebih dahulu.")
        return None
    gdf = gpd.read_file(PATH_GRID_FEAT)
    gdf = compute_slope_from_elevation(gdf)
    gdf.to_file(PATH_GRID_FEAT, driver="GPKG")
    print(f"[05] ✅ Slope disimpan ke {PATH_GRID_FEAT}")
    return gdf


if __name__ == "__main__":
    run()
