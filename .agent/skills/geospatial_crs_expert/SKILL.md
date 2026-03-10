---
name: geospatial_crs_expert
description: Memastikan semua data spasial (vektor sungai, titik elevasi, dll) di wilayah Samarinda memiliki sistem referensi koordinat (CRS) yang sinkron dan selaras di atas peta.
---

# Panduan Sinkronisasi CRS Geospasial untuk Samarinda

Skill ini memberikan panduan dan pustaka instruksi bagi agent/environment untuk memastikan data spasial (seperti vektor sungai, titik elevasi/topografi, dan batas wilayah) selaras (overlap) sempurna tanpa ada pergeseran (shifting) ketika dipetakan di atas basemap Samarinda.

## 1. Pemahaman Sistem Referensi Koordinat (CRS) Samarinda

Wilayah Samarinda, Kalimantan Timur, berada di selatan khatulistiwa dan dalam zona spesifik yang menyebabkan kita harus memperhatikan CRS yang tepat:
- **`EPSG:4326` (WGS 84)**: Sistem koordinat geografis umum (Latitude/Longitude). Sering digunakan untuk pertukaran data, format GeoJSON, dan layer web map.
- **`EPSG:32750` (WGS 84 / UTM zone 50S)**: Sistem koordinat terproyeksi (dalam satuan meter) yang paling ideal dan akurat untuk Samarinda. **Wajib digunakan saat melakukan operasi analisis spasial** seperti `buffer()`, `distance()`, `area`, atau interpolasi elevasi agar hasilnya presisi.
- **`EPSG:3857` (Pseudo-Mercator)**: CRS umum untuk *basemap* di peta web (Google Maps, OpenStreetMap).

## 2. Pustaka (Library) Utama yang Digunakan

Dalam melakukan pengolahan dan sinkronisasi data geospasial, kita sangat bergantung pada integrasi tiga pustaka utama Python berikut:
- **`geopandas`**: Digunakan sebagai struktur data utama (GeoDataFrame) untuk membaca, memanipulasi, dan menulis data spasial. GeoPandas sangat mempermudah operasi reproyeksi berskala besar (`to_crs()`) maupun input/output file.
- **`pyproj`**: Pustaka fundamental (backend) untuk menangani definisi dan transformasi sistem referensi koordinat (CRS). Anda bisa menggunakannya secara langsung jika perlu mendefinisikan CRS yang sangat spesifik atau melakukan perhitungan titik ke titik (seperti menghitung *azimuth* atau jarak geodesi langsung).
- **`shapely`**: Digunakan untuk membuat, memanipulasi, dan menganalisis secara matematika objek geometri planar (titik, garis, poligon). `shapely` sangat diperlukan untuk operasi analisis seperti `buffer`, pengecekan titik potong/bersebelahan (`intersection`, `touches`), atau `distance` terhadap objek setelah data diproyeksikan ke dalam satuan meter.

## 3. Standar Alur Kerja Sinkronisasi

Untuk memproses data spasial, selalu gunakan lingkungan conda Anda. Misalnya, pastikan lingkungan `agentic_ai` yang memiliki komponen geospasial telah aktif.

### a. Pengecekan CRS Awal
Seluruh dataset yang dibaca wajib dicek nilai CRS-nya.

```python
import geopandas as gpd

# Muat data vektor
sungai_gdf = gpd.read_file('path/vektor_sungai.gpkg')
elevasi_gdf = gpd.read_file('path/titik_elevasi.shp')

# Pastikan mengetahui CRS asli sebelum proses apapun
print("CRS Sungai:", sungai_gdf.crs)
print("CRS Elevasi:", elevasi_gdf.crs)
```

*Jika data tidak memiliki CRS (`gdf.crs is None`), tapi dikonfirmasi koordinatnya format lat/lon (-1.xx, 117.xx), maka set CRS-nya ke WGS 84:*
```python
if sungai_gdf.crs is None:
    sungai_gdf = sungai_gdf.set_crs(epsg=4326)
```

### b. Menyamakan CRS (Reproyeksi)
Semua vektor yang akan digabungkan atau di-plot bersamaan pada satu bidang harus memiliki CRS yang identik.

```python
# Untuk Keperluan Analisis dan Perhitungan Geometri (Proyeksi ke Samarinda UTM 50S)
target_crs = 32750 

if sungai_gdf.crs != f"EPSG:{target_crs}":
    sungai_gdf_utm = sungai_gdf.to_crs(epsg=target_crs)
else:
    sungai_gdf_utm = sungai_gdf

if elevasi_gdf.crs != f"EPSG:{target_crs}":
    elevasi_gdf_utm = elevasi_gdf.to_crs(epsg=target_crs)
else:
    elevasi_gdf_utm = elevasi_gdf
```

### c. Persiapan Ekspor ke Web Map (Contoh: Folium, Streamlit Folium)
Peta web interaktif umumnya mengharuskan data input berformat `EPSG:4326`. Ubah kembali data hasil analisis ke WGS 84 saat akan dikirim ke *frontend* atau disimpan sebagai basis data web.

```python
sungai_final_wgs84 = sungai_gdf_utm.to_crs(epsg=4326)
elevasi_final_wgs84 = elevasi_gdf_utm.to_crs(epsg=4326)
```

## 4. Menangani Ketidaksinkronan (Troubleshooting)

- **Masalah:** Data tidak muncul di Samarinda, muncul di koordinat (0, 0) dekat benua Afrika.
  - **Identifikasi:** Data yang memiliki koordinat format proyeksi *meter* (nilainya jutaan misal: x=510000, y=9800000) dianggap secara sistem sebagai latitude/longitude.
  - **Solusi:** `gdf.set_crs(epsg=32750)` lalu reproyeksikan dengan `gdf.to_crs(epsg=4326)`.
- **Masalah:** Garis sungai tidak menyatu mulus dengan titik elevasi kontur.
  - **Penyebab:** Satuan unit dari sistem terproyeksi yang dipakai mungkin sedikit berbeda, atau ada perbedaan "Datum" sebelumnya.
  - **Solusi:** Validasi menggunakan plot Matplotlib lokal secara bertumpuk dengan `alpha=0.5` untuk memverifikasi kedekatan (proximity) objek sebelum masuk web aplikasi.

## Aturan Tambahan
- Usahakan menyimpan data primer hasil proses backend dalam format GeoPackage (`.gpkg`) karena kemampuannya mendokumentasikan CRS lebih baik daripada Shapefile.
- Beri konfirmasi ke sistem bahwa vektor sudah divisualisasikan tumpang-tindih melalui validasi unit bounding-box (`total_bounds`). Jika `total_bounds` dari dataset yang berbeda ada di rentang yang sama (contoh rentang Lat: -0.6 hingga -0.4, Lon: 117.0 hingga 117.3), maka dipastikan tersinkronisasi.