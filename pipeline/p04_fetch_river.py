"""
pipeline/p04_fetch_river.py
Mengambil data geometri sungai dan memadukan Tinggi Muka Air (TMA) secara real-time
melalui web scraping dari dashboard BWS Kalimantan IV (hidrologi.id).
Output: data/processed/sungai_samarinda.gpkg
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
import geopandas as gpd
from shapely.geometry import LineString
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import PATH_RIVER, CRS_GEO

# URL Dashboard BWS
SIHKA_URL = "https://hidrologi.id/duga-air"

def fetch_live_tma():
    """
    Scrape data TMA (Tinggi Muka Air) dari tabel portal SIHKA
    Mengembalikan dictionary format: {'mahakam': level_m, 'karang_mumus': level_m}
    """
    print(f"[04] Mengambil TMA Real-time dari {SIHKA_URL} ...")
    
    tma_data = {
        "mahakam": None,
        "karang_mumus": None
    }
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(SIHKA_URL, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        
        table = soup.find('table')
        if not table:
            raise ValueError("Tabel data tidak ditemukan di halaman web.")
            
        rows = table.find_all('tr')
        
        # Ekstrak rata-rata pos
        mahakam_levels = []
        karang_mumus_levels = []
        
        for row in rows[3:]: # Skip header rows
            cols = row.find_all(['th', 'td'])
            cols = [ele.text.strip().replace('\n', '') for ele in cols]
            
            if len(cols) > 4:
                item_name = cols[1].lower()
                
                # Coba ambil rata-rata dari 2 hari terakhir
                try:
                    # Angka TMA berada di antara index 5 sampai 8 (jam pemantauan s/d rata-rata)
                    val = None
                    for i in [8, 7, 6, 5]:  # Prioritaskan Rata-rata (idx 8), jika kosong ambil jam terakhir
                        if i < len(cols) and cols[i] and cols[i] != '-':
                            try:
                                val = float(cols[i])
                                break
                            except ValueError:
                                continue
                                
                    if val is not None:
                        if 'mahakam' in item_name and 'tenggarong' in item_name:
                            mahakam_levels.append(val)
                        elif 'karang mumus' in item_name and ('muang' in item_name or 'gunung lingai' in item_name):
                            karang_mumus_levels.append(val)
                except Exception:
                    continue
                    
        # Gabungkan hasil rata-rata
        if mahakam_levels:
            tma_data["mahakam"] = np.mean(mahakam_levels)
        if karang_mumus_levels:
            tma_data["karang_mumus"] = np.mean(karang_mumus_levels)
            
    except Exception as e:
        print(f"[04] ⚠️  Gagal scraping data TMA: {e}")
        
    # Fallback if scraping fails or specific data is missing
    if tma_data["mahakam"] is None:
        print("[04] ⚠️  TMA Mahakam tidak ditemukan. Menggunakan fallback historis (2.5m).")
        tma_data["mahakam"] = 2.5
    if tma_data["karang_mumus"] is None:
        print("[04] ⚠️  TMA Karang Mumus tidak ditemukan. Menggunakan fallback historis (1.8m).")
        tma_data["karang_mumus"] = 1.8
        
    print(f"[04] ✅ Live TMA Mahakam: {tma_data['mahakam']:.2f}m | Karang Mumus: {tma_data['karang_mumus']:.2f}m")
    return tma_data

def create_river_data(tma_data):
    """
    Membuat geometri sungai dan menyematkan atribut level air (TMA).
    """
    print("[04] Membangun vektor sungai dengan atribut TMA...")
    
    # Koordinat manual Sungai Mahakam (melewati Samarinda)
    mahakam_coords = [
        (117.060, -0.560),
        (117.100, -0.530),
        (117.150, -0.520),
        (117.200, -0.550),
        (117.250, -0.580)
    ]
    
    # Koordinat manual Sungai Karang Mumus (membelah kota)
    karang_mumus_coords = [
        (117.170, -0.420),
        (117.180, -0.450),
        (117.165, -0.480),
        (117.155, -0.500),
        (117.153, -0.538) # Muara bertemu Mahakam
    ]
    
    mahakam_line = LineString(mahakam_coords)
    karang_mumus_line = LineString(karang_mumus_coords)
    
    # Split sungai panjang menjadi segmen lebih pendek untuk resolusi lebih baik (sederhana)
    features = []
    
    # Segmen Mahakam
    for i in range(len(mahakam_coords) - 1):
        segment = LineString([mahakam_coords[i], mahakam_coords[i+1]])
        features.append({
            "name": f"Mahakam Segmen {i+1}",
            "type": "river",
            "level_m": tma_data["mahakam"],
            "geometry": segment
        })
        
    # Segmen Karang Mumus
    for i in range(len(karang_mumus_coords) - 1):
        segment = LineString([karang_mumus_coords[i], karang_mumus_coords[i+1]])
        features.append({
            "name": f"Karang Mumus Segmen {i+1}",
            "type": "river",
            "level_m": tma_data["karang_mumus"],
            "geometry": segment
        })
        
    gdf = gpd.GeoDataFrame(features, crs=CRS_GEO)
    return gdf

def run():
    tma_data = fetch_live_tma()
    gdf = create_river_data(tma_data)
    
    os.makedirs(os.path.dirname(PATH_RIVER), exist_ok=True)
    gdf.to_file(PATH_RIVER, driver="GPKG")
    print(f"[04] ✅ Data sungai real-time disimpan: {len(gdf)} segmen")
    return PATH_RIVER

if __name__ == "__main__":
    run()
