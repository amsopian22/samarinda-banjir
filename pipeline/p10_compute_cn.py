"""
pipeline/p10_compute_cn.py
Melakukan Spatial Join antara titik grid (grid_features.gpkg) dengan 
poligon landcover (landcover_cn.gpkg) untuk menempelkan nilai CN ke setiap titik.
Output: di-overwrite ke grid_features.gpkg
"""

import os
import sys
import geopandas as gpd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import PATH_GRID_FEAT, CRS_UTM, CRS_GEO

PATH_LANDCOVER = "data/processed/landcover_cn.gpkg"

def run():
    print("[10] Memulai Spatial Join Curve Number (CN) ke grid sampling...")
    
    if not os.path.exists(PATH_GRID_FEAT):
        print(f"[10] ❌ File grid belum ada: {PATH_GRID_FEAT}")
        return
        
    if not os.path.exists(PATH_LANDCOVER):
        print(f"[10] ⚠️  File landcover belum ada ({PATH_LANDCOVER}). Memasukkan rata-rata default CN=75 ke semua grid.")
        grid_gdf = gpd.read_file(PATH_GRID_FEAT)
        grid_gdf["cn_score"] = 75
        grid_gdf.to_file(PATH_GRID_FEAT, driver="GPKG")
        return PATH_GRID_FEAT
        
    try:
        # Load grid features (biasanya dalam UTM dari langkah sebelumnya, tapi kita akan standardisasi)
        grid_gdf = gpd.read_file(PATH_GRID_FEAT)
        
        # Load landcover (dalam format WGS84 dari p09)
        lc_gdf = gpd.read_file(PATH_LANDCOVER)
        
        # Pastikan CRS disamakan sebelum spatial join. Menggunakan UTM untuk akurasi jarak
        print(f"[10] Menyelaraskan CRS... (merujuk skill geospatial_crs_expert)")
        grid_gdf = grid_gdf.to_crs(CRS_UTM)
        lc_gdf = lc_gdf.to_crs(CRS_UTM)
        
        # Jika grid_gdf sudah punya kolom cn_score sebelumnya, drop dulu agar tidak duplikat
        if "cn_score" in grid_gdf.columns:
            grid_gdf = grid_gdf.drop(columns=["cn_score"])
            
        # Lakukan klasifikasi spatial join (titik mana jatuh di poligon mana)
        # sjoin merangkap grid_gdf (titik) dengan (poligon) lc_gdf
        print(f"[10] Melakukan spatial join pada {len(grid_gdf)} titik...")
        
        # Menyambungkan kolom cn_score dari lc_gdf ke grid_gdf. 
        # how="left" agar titik yang tidak kena poligon (misal area tak terdaftar di OSM) tidak hilang
        joined_gdf = gpd.sjoin(grid_gdf, lc_gdf[['cn_score', 'geometry']], how="left", predicate="within")
        
        # Banyak poligon OSM yang tumpang tindih. Titik bisa tergabung dua kali. Kita bersihkan duplikat
        joined_gdf = joined_gdf[~joined_gdf.index.duplicated(keep='first')]
        
        # Untuk area yang tak ter-cover OSM, kita beri fallback (misal pinggiran kota: CN 75)
        joined_gdf["cn_score"] = joined_gdf["cn_score"].fillna(75).astype(int)
        
        # Bersihkan kolom sjoin leftovers (index_right)
        if "index_right" in joined_gdf.columns:
             joined_gdf = joined_gdf.drop(columns=["index_right"])
             
        # Selamatkan kembali ke disk
        joined_gdf.to_file(PATH_GRID_FEAT, driver="GPKG")
        print(f"[10] ✅ Kolom cn_score berhasil disematkan. Data disimpan.")
        
        # Ambil list kolom untuk sample print agar tidak error
        sample_cols = [c for c in ['elevation', 'slope_deg', 'dist_sungai_m', 'cn_score'] if c in joined_gdf.columns]
        print(f"[10] Sempel hasil:\n{joined_gdf[sample_cols].head()}")
        
        return PATH_GRID_FEAT
        
    except Exception as e:
        print(f"[10] ❌ Gagal menghitung CN: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
