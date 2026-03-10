---
title: Realtime API Connector
description: Melakukan scraping data cuaca atau menghubungkan ke API cuaca terbuka (seperti Open-Meteo) untuk mendapatkan data curah hujan harian di Samarinda.
---

# Panduan Koneksi API Cuaca Realtime (Realtime API Connector)

Keahlian ini bertugas untuk menyambungkan agen dengan sumber data cuaca aktual secara *realtime*. Data curah hujan (presipitasi) ini sangat penting untuk digunakan sebagai input variabel (nilai `P` atau Curah Hujan Harian) dalam model hidrologi Limpasan Permukaan (seperti formula *Curve Number*).

## 1. Sumber API yang Digunakan: Open-Meteo

Karena BMKG belum menyediakan API publik terbuka gratis tanpa batasan akses otentikasi (API Key), agen direkomendasikan untuk menggunakan **Open-Meteo API**.
Open-Meteo adalah layanan gratis (tanpa perlu API key) yang menggabungkan berbagai model cuaca global (termasuk GFS dan ICON) yang sangat andal untuk menentukan curah hujan harian di suatu titik koordinat.

**Koordinat referensi Pusat Samarinda:**
- Latitude: `-0.5022`
- Longitude: `117.1536`

## 2. Pustaka (Library) Utama

Pastikan lingkungan kerja (seperti *conda environment `agentic_ai`*) memiliki pustaka standar untuk melakukan *HTTP Request*.
- **`requests`**: Digunakan untuk memanggil titik akhir (endpoint) REST API.
- **`json`**: Memecah respons data ke dalam *dictionary* Python.
- **`datetime`**: Menentukan sinkronisasi zona waktu (hari ini).

## 3. Implementasi Skrip Ekstraksi Curah Hujan

Berikut adalah standar kode (*boilerplate*) agen untuk mengambil total curah hujan (`precipitation_sum`) harian dalam hitungan milimeter (mm):

```python
import requests
from datetime import datetime

def dapatkan_curah_hujan_samarinda():
    """
    Mengambil prediksi curah hujan total hari ini di Samarinda 
    menggunakan Open-Meteo API.
    """
    # Titik tengah Samarinda
    lat = -0.5022
    lon = 117.1536
    
    # Endpoint Open-Meteo untuk total curah hujan harian
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=precipitation_sum&timezone=Asia%2FJakarta"
    )
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Memastikan tidak ada error HTTP
        data = response.json()
        
        # Mengekstrak tanggal hari ini dan nilai curah hujan harian bersangkutan
        tanggal_hari_ini = data['daily']['time'][0]
        curah_hujan_mm = data['daily']['precipitation_sum'][0]
        
        print(f"Data Cuaca Samarinda ({tanggal_hari_ini}):")
        print(f"Curah Hujan: {curah_hujan_mm} mm")
        
        return curah_hujan_mm
        
    except Exception as e:
        print(f"Gagal mengambil data cuaca: {e}")
        # Kembalikan nilai default historis 0.0 jika gagal
        return 0.0
```

## 4. Integrasi dengan Pemodelan Hidrologi

Data cuaca presipitasi yang berhasil diambil akan langsung dihubungkan (di-referensikan) ke dalam formula *Curve Number* yang terdapat di dalam pedoman **Hydrological Modelling Expert**.

Apabila Anda (Agen) mendapatkan instruksi: 
> *"Ambil data curah hujan hari ini dan masukkan sebagai variabel perhitungan limpasan di Samarinda"*

Maka langkah agen adalah:
1. Panggil dan eksekusi fungsi `dapatkan_curah_hujan_samarinda()`.
2. Simpan hasilnya ke dalam variabel `P` (Curah Hujan Harian, dalam satuan mm).
3. Jalankan persaman hidrologi Curve Number berdasarkan jenis tutupan lahan (seperti yang telah didefinisikan dalam skill Hidrologi):
   \\[ Q = \frac{(P - I_a)^2}{(P - I_a) + S} \\]
   *(Perhatikan jika `P < I_a` maka tidak ada limpasan atau `Q = 0` karena curah hujan di bawah daya serap awal).*