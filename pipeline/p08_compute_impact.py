import os
import sys
import numpy as np
import geopandas as gpd
from shapely.geometry import Point

sys.path.insert(0, os.getcwd())
from config import PATH_GRID_FEAT, CRS_GEO, CRS_UTM

def compute_density_and_impact():
    if not os.path.exists(PATH_GRID_FEAT):
        print("Grid tidak ditemukan!")
        return
        
    gdf = gpd.read_file(PATH_GRID_FEAT)
    
    # Titik pusat kepadatan (ekonomi/pemukiman Samarinda)
    centers = [
        (-0.5022, 117.1536), # Samarinda Kota (Paling padat, ~12000 jiwa/km2)
        (-0.4735, 117.1650), # Sungai Pinang (~8000 jiwa/km2)
        (-0.5356, 117.1261)  # Samarinda Seberang (~6000 jiwa/km2)
    ]
    
    # Ubah centers ke UTM untuk perhitungan jarak meter
    centers_geom = gpd.GeoSeries([Point(lon, lat) for lat, lon in centers], crs=CRS_GEO).to_crs(CRS_UTM)
    
    density_list = []
    
    gdf_utm = gdf.to_crs(CRS_UTM)
    for idx, row in gdf_utm.iterrows():
        point = row.geometry
        # Hitung jarak ke tiap pusat
        dists = [point.distance(center) for center in centers_geom]
        
        # Model peluruhan eksponensial (Exponential decay)
        # Kepadatan = base + C1*exp(-d1/R1) + C2*exp(-d2/R2) + C3*exp(-d3/R3)
        base_density = 500  # Minimal pinggiran kota
        d1 = 15000 * np.exp(-dists[0] / 3000.0) # Radius pengaruh 3km
        d2 = 8000  * np.exp(-dists[1] / 2500.0)
        d3 = 8000  * np.exp(-dists[2] / 2000.0)
        
        total_density = int(base_density + d1 + d2 + d3)
        density_list.append(total_density)
        
    gdf["pop_density_km2"] = density_list
    
    # Hitung Dampak Kependudukan (Impact Score) jika sudah ada model flood pred
    if "p_flood_pred" in gdf.columns:
        p_col = "p_flood_pred"
    elif "p_flood" in gdf.columns:
        p_col = "p_flood"
    else:
        p_col = None
        
    if p_col:
        # Dampak = Probabilitas Banjir * Kepadatan Penduduk
        # Normalisasi ke skala 0-100
        max_density = max(density_list)
        gdf["impact_score"] = (gdf[p_col] * (gdf["pop_density_km2"] / max_density)) * 100
        
        # Kategori Dampak
        conditions = [
            (gdf["impact_score"] >= 40),
            (gdf["impact_score"] >= 20),
            (gdf["impact_score"] >= 5),
            (gdf["impact_score"] < 5)
        ]
        choices = ["Parah", "Sedang", "Rendah", "Aman"]
        gdf["impact_category"] = np.select(conditions, choices, default="Aman")
        
    gdf.to_file(PATH_GRID_FEAT, driver="GPKG")
    print("✅ Kepadatan penduduk (synthetic) dan skor dampak berhasil dihitung.")
    print(gdf[["pop_density_km2", "impact_category"]].head())

if __name__ == "__main__":
    compute_density_and_impact()
