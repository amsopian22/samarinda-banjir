"""
main.py
============================================================
Samarinda Hydro-Intelligence & Predictive Heatmap
Orkestrasi Pipeline Utama
============================================================
Cara menjalankan:
    conda activate agentic_ai
    python main.py

Pipeline akan berjalan secara berurutan:
    1. Fetch batas wilayah Samarinda
    2. Verifikasi sumber DEM (OpenTopoData API)
    3. Fetch curah hujan hari ini (Open-Meteo)
    4. Buat data sungai (OSM / manual)
    5. Bangun grid sampling + ambil elevasi
    6. Hitung slope dari elevasi
    7. Hitung jarak ke sungai
    8. Latih model Random Forest
    9. Generate heatmap HTML interaktif
"""

import os
import time
import psutil

# --- Memory Guard ---
def check_memory(label=""):
    mem = psutil.virtual_memory()
    used_gb = mem.used / (1024 ** 3)
    avail_gb = mem.available / (1024 ** 3)
    print(f"[RAM] {label}: Terpakai={used_gb:.2f}GB | Tersedia={avail_gb:.2f}GB")
    return used_gb

RAM_LIMIT_GB = 2.0

def memory_safe_continue(step_name):
    used = check_memory(step_name)
    if used > RAM_LIMIT_GB:
        print(f"[RAM] ⚠️  Penggunaan RAM ({used:.2f}GB) melewati {RAM_LIMIT_GB}GB.")
        print("[RAM]     Memanggil garbage collector...")
        import gc
        gc.collect()
        check_memory("Setelah GC")
    return True


# =============================================================
# PIPELINE EXECUTION
# =============================================================

def main():
    start_time = time.time()
    print("=" * 60)
    print("  🌊 SAMARINDA HYDRO-INTELLIGENCE PIPELINE")
    print("=" * 60)

    # --- Step 1: Batas Wilayah ---
    print("\n📍 STEP 1/9: Mengambil batas administratif Samarinda...")
    from pipeline.p01_fetch_boundary import fetch_boundary
    fetch_boundary()
    memory_safe_continue("Setelah Step 1")

    # --- Step 2: Verifikasi DEM ---
    print("\n🏔️  STEP 2/9: Memverifikasi sumber DEM...")
    from pipeline import p02_fetch_dem as fetch_dem_02
    fetch_dem_02.run()
    memory_safe_continue("Setelah Step 2")

    # --- Step 3: Curah Hujan ---
    print("\n🌧️  STEP 3/9: Mengambil curah hujan hari ini...")
    from pipeline import p03_fetch_rainfall as fetch_rainfall_03
    rainfall_mm = fetch_rainfall_03.fetch_rainfall()
    memory_safe_continue("Setelah Step 3")

    # --- Step 4: Data Sungai ---
    print("\n🏞️  STEP 4/10: Memuat vektor & live TMA sungai (Web Scrape)...")
    from pipeline import p04_fetch_river as fetch_river_04
    fetch_river_04.run()
    memory_safe_continue("Setelah Step 4")

    # --- Step 5: Build Grid + Elevasi ---
    print("\n🗺️  STEP 5/9: Membangun grid sampling dan mengambil elevasi...")
    from pipeline import p07_build_grid as build_grid_07
    grid_gdf = build_grid_07.build_grid()
    memory_safe_continue("Setelah Step 5")

    # --- Step 6: Compute Slope ---
    print("\n📐 STEP 6/9: Menghitung Slope dari data elevasi grid...")
    from pipeline import p05_compute_slope as compute_slope_05
    grid_gdf = compute_slope_05.compute_slope_from_elevation(grid_gdf)
    memory_safe_continue("Setelah Step 6")

    # --- Step 7: Compute Distance to River ---
    print("\n📏 STEP 7/9: Menghitung jarak titik grid ke sungai...")
    import geopandas as gpd
    from config import PATH_RIVER, PATH_GRID_FEAT
    river_gdf = gpd.read_file(PATH_RIVER)
    from pipeline import p06_compute_distance as compute_distance_06
    grid_gdf = compute_distance_06.compute_distance_to_river(grid_gdf, river_gdf)
    # Simpan grid dengan semua fitur
    grid_gdf.to_file(PATH_GRID_FEAT, driver="GPKG")
    memory_safe_continue("Setelah Step 7")

    # --- Step 8: Fetch Land Cover (OSM) ---
    print("\n🌳 STEP 8/11: Mengunduh data tutupan lahan (OSM) & memetakan Curve Number...")
    from pipeline import p09_fetch_landcover as fetch_landcover_09
    fetch_landcover_09.run()
    memory_safe_continue("Setelah Step 8")

    # --- Step 9: Compute Curve Number (CN) ---
    print("\n🏙️ STEP 9/11: Menghitung skor SCS Curve Number pada tiap titik grid...")
    from pipeline import p10_compute_cn as compute_cn_10
    grid_path = compute_cn_10.run()
    if grid_path:
        grid_gdf = gpd.read_file(grid_path)
    memory_safe_continue("Setelah Step 9")

    # --- Step 10: Train Model ---
    print("\n🤖 STEP 10/11: Melatih model Machine Learning (dengan fitur CN)...")
    from model.train_model import train_model
    grid_gdf, model = train_model(grid_gdf)
    # Simpan grid dengan prediksi
    grid_gdf.to_file(PATH_GRID_FEAT, driver="GPKG")
    memory_safe_continue("Setelah Step 10")

    # --- Step 11: Compute Population Density & Impact ---
    print("\n👥 STEP 11/11: Menghitung kepadatan penduduk & skor dampak banjir...")
    from pipeline import p08_compute_impact as compute_impact_08
    compute_impact_08.compute_density_and_impact()
    memory_safe_continue("Setelah Step 11")

    # --- Step 12: Generate Peta Heatmap ---
    print("\n🗺️  SELESAI: Menghasilkan peta heatmap interaktif Samarinda...")
    from output import generate_heatmap
    output_path = generate_heatmap.generate_heatmap()

    # --- Selesai ---
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("  ✅ PIPELINE SELESAI!")
    print(f"  ⏱️  Total waktu: {elapsed:.1f} detik")
    print(f"  📄 Output: {os.path.abspath(output_path)}")
    print("=" * 60)
    print("\n💡 Buka file heatmap di browser:")
    print(f"   open {os.path.abspath(output_path)}")


if __name__ == "__main__":
    main()
