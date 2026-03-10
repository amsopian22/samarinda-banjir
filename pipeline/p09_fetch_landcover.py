"""
pipeline/p09_fetch_landcover.py
Mengambil data tata guna lahan (Land Cover) dari OpenStreetMap menggunakan osmnx.
Memetakan tipe penggunaan lahan (landuse/natural) ke nilai SCS Curve Number (CN).
Output: data/processed/landcover_cn.gpkg
"""

import os
import sys
import geopandas as gpd
import pandas as pd
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import PATH_BOUNDARY, CRS_GEO, CRS_UTM

PATH_LANDCOVER = "data/processed/landcover_cn.gpkg"

# Pemetaan Sederhana Landuse ke Nilai CN (Tipe Tanah Umum - Kelompok C/D di daerah basah)
# CN Tinggi (85-100) -> Banyak perkerasan, aspal, bangunan (Air langsung mengalir)
# CN Sedang (70-85)  -> Tanah terbuka, taman, rumput
# CN Rendah (50-70)  -> Hutan, semak belukar (Resapan air tinggi)
# CN Khusus (100)    -> Badan Air (Sungai, Danau)
CN_MAPPING = {
    # Perkotaan / Terbangun (Impervious) - CN Tinggi
    "commercial": 95,
    "retail": 95,
    "industrial": 95,
    "residential": 85,
    "brownfield": 85,
    "cemetery": 75,
    "construction": 90,
    "garages": 95,
    
    # Hijau / Terbuka - CN Sedang ke Rendah
    "forest": 60,
    "wood": 60,
    "grass": 70,
    "meadow": 70,
    "orchard": 70,
    "park": 75,
    "recreation_ground": 75,
    "allotments": 75,
    "farmland": 78,
    "farmyard": 82,
    
    # Air - CN 100 (Total limpasan)
    "water": 100,
    "wetland": 100,
    "basin": 100,
    "reservoir": 100
}

def assign_cn(row):
    """Fungsi helper untuk mendapatkan nilai CN berdasarkan tag OSM."""
    # Prioritaskan tag 'natural' jika ada (seperti water, wood)
    if pd.notna(row.get('natural')):
        nat = str(row['natural']).lower()
        if nat in CN_MAPPING:
            return CN_MAPPING[nat]
            
    # Baru cek tag 'landuse'
    if pd.notna(row.get('landuse')):
        lu = str(row['landuse']).lower()
        if lu in CN_MAPPING:
            return CN_MAPPING[lu]
            
    # Default CN jika tipe tidak dienumerasi (Anggap pemukiman pinggiran/tanah campur)
    return 80

def run():
    print("[09] Memulai ekstraksi Land Cover Samarinda dari OSM...")
    try:
        import osmnx as ox
    except ImportError:
        print("[09] ❌ Package 'osmnx' belum terinstall. Lewati ekstraksi land cover.")
        return None
        
    if not os.path.exists(PATH_BOUNDARY):
        print(f"[09] ❌ Batas Samarinda tidak ditemukan: {PATH_BOUNDARY}")
        return None
        
    # Load boundary polygon
    boundary_gdf = gpd.read_file(PATH_BOUNDARY)
    boundary_polygon = boundary_gdf.geometry.iloc[0]
    
    print("[09] Mengunduh data landuse & natural polygon via Overpass API (bisa memakan waktu beberapa menit)...")
    tags = {
        'landuse': True,
        'natural': True
    }
    
    try:
        # Fetch data dari OSM di dalam batas poligon Samarinda
        landcover_gdf = ox.features_from_polygon(boundary_polygon, tags)
        
        # Filter hanya tipe polygon (kita abaikan node/point untuk landcover)
        landcover_gdf = landcover_gdf[landcover_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
        
        if landcover_gdf.empty:
            print("[09] ⚠️  Tidak ada data landcover polygon yang ditemukan.")
            return None
            
        print(f"[09] Berhasil mengunduh {len(landcover_gdf)} poligon tata guna lahan.")
        
        # Hitung Nilai CN
        landcover_gdf['cn_score'] = landcover_gdf.apply(assign_cn, axis=1)
        
        # Pilih kolom yang relevan saja agar ukuran file tidak bengkak
        cols_to_keep = ['geometry', 'cn_score']
        if 'landuse' in landcover_gdf.columns: cols_to_keep.append('landuse')
        if 'natural' in landcover_gdf.columns: cols_to_keep.append('natural')
        
        # Ekstrak kolom yang ada saja
        final_gdf = landcover_gdf[[c for c in cols_to_keep if c in landcover_gdf.columns]]
        
        # Simpan ke file dalam proyeks WGS84
        os.makedirs(os.path.dirname(PATH_LANDCOVER), exist_ok=True)
        final_gdf.to_file(PATH_LANDCOVER, driver="GPKG")
        
        print(f"[09] ✅ Data Land Cover tersimpan di {PATH_LANDCOVER}")
        
        # Tampilkan ringkasan distribusi CN
        print("\n--- Distribusi Curve Number (CN) ---")
        print(final_gdf['cn_score'].value_counts())
        print("------------------------------------\n")
        
        return PATH_LANDCOVER
        
    except Exception as e:
        print(f"[09] ❌ Gagal mengekstrak land cover: {e}")
        return None

if __name__ == "__main__":
    run()
