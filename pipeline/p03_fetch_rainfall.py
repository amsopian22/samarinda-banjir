"""
pipeline/03_fetch_rainfall.py
Mengambil data curah hujan harian Samarinda via Open-Meteo API.
Output: data/processed/rainfall_today.json
"""

import requests
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import LAT_CENTER, LON_CENTER, PATH_RAINFALL


def fetch_rainfall(days_back=7):
    """
    Mengambil curah hujan harian Samarinda selama N hari terakhir.
    Mengembalikan dict: {'date': str, 'precipitation_mm': float, 'series': list}
    """
    print(f"[03] Mengambil data curah hujan {days_back} hari terakhir dari Open-Meteo...")

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LAT_CENTER}&longitude={LON_CENTER}"
        f"&daily=precipitation_sum&timezone=Asia%2FJakarta"
        f"&past_days={days_back}"
    )

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        dates  = data["daily"]["time"]
        precip = data["daily"]["precipitation_sum"]

        # Nilai curah hujan hari ini (indeks terakhir)
        today_date   = dates[-1]
        today_precip = precip[-1] if precip[-1] is not None else 0.0

        # Rata-rata 7 hari terakhir
        valid_precip = [p for p in precip if p is not None]
        avg_7day     = sum(valid_precip) / len(valid_precip) if valid_precip else 0.0

        # Histori hujan:
        h_0 = precip[-1] if len(precip) >= 1 and precip[-1] is not None else 0.0
        h_1 = precip[-2] if len(precip) >= 2 and precip[-2] is not None else 0.0
        h_2 = precip[-3] if len(precip) >= 3 and precip[-3] is not None else 0.0
        h_3 = precip[-4] if len(precip) >= 4 and precip[-4] is not None else 0.0

        result = {
            "tanggal_hari_ini": today_date,
            "curah_hujan_mm": h_0,
            "rain_today": h_0,
            "rain_h_minus_1": h_1,
            "rain_h_minus_2": h_2,
            "rain_h_minus_3": h_3,
            "rata_rata_7hari_mm": round(avg_7day, 2),
            "series": [{"date": d, "precipitation_mm": p or 0.0}
                       for d, p in zip(dates, precip)],
            "sumber": "Open-Meteo API",
            "diambil_pada": datetime.now().isoformat()
        }

        # Simpan ke file JSON
        os.makedirs(os.path.dirname(PATH_RAINFALL), exist_ok=True)
        with open(PATH_RAINFALL, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"[03] ✅ Curah Hujan Hari Ini ({today_date}): {h_0} mm")
        print(f"[03]    H-1: {h_1} mm | H-2: {h_2} mm | H-3: {h_3} mm")
        print(f"[03]    Rata-rata 7 hari: {avg_7day:.2f} mm")
        return h_0

    except Exception as e:
        print(f"[03] ⚠️  Gagal mengambil data cuaca: {e}")
        print("[03]    Menggunakan nilai curah hujan default historis: 25.0 mm")
        fallback = {
            "tanggal_hari_ini": datetime.now().strftime("%Y-%m-%d"),
            "curah_hujan_mm": 25.0,
            "rata_rata_7hari_mm": 22.0,
            "sumber": "fallback_historis",
            "series": []
        }
        os.makedirs(os.path.dirname(PATH_RAINFALL), exist_ok=True)
        with open(PATH_RAINFALL, "w", encoding="utf-8") as f:
            json.dump(fallback, f, indent=2)
        return 25.0


if __name__ == "__main__":
    fetch_rainfall()
