# 🌊 Samarinda Hydro-Intelligence & Predictive Heatmap

[![Status: Live](https://img.shields.io/badge/Status-Live-green)](https://prediksi-banjir-samarinda.vercel.app/)
[![Deployment: Vercel](https://img.shields.io/badge/Deployment-Vercel-black)](https://prediksi-banjir-samarinda.vercel.app/)
[![Orchestrator: Airflow](https://img.shields.io/badge/Orchestrator-Airflow-blue)](https://airflow.apache.org/)

Platform visualisasi data eksekutif untuk prediksi risiko banjir di wilayah Samarinda secara *real-time*. Proyek ini mengintegrasikan pemodelan hidrologi, Machine Learning, dan data spasial beresolusi tinggi untuk memberikan panduan pengambilan keputusan bagi *stakeholder* terkait.

## 🚀 Overview Proyek

Sistem ini memprediksi probabilitas genangan banjir di tiap titik sampling (grid) wilayah Samarinda setiap hari. Berbeda dengan peta banjir statis konvensional, sistem ini bersifat dinamis sesuai dengan kondisi cuaca terkini dan tinggi muka air sungai.

### 🏗️ Arsitektur Sistem
Sistem berjalan dalam ekosistem hibrid:
1.  **Server Utama (Backend & Processing):** 
    - Spesifikasi: 20 Core CPU, 64GB RAM.
    - Fungsi: Menjalankan Apache Airflow untuk orkestrasi pipeline data, pelatihan model ML (XGBoost), dan pemrosesan GIS beresolusi tinggi.
2.  **GitHub (Data Bridge):** Menjadi jembatan sinkronisasi antara hasil proses di server dan dashboard.
3.  **Vercel (Frontend):** Hosting dashboard berbasis React + MapLibre yang ringan dan cepat untuk akses publik/eksekutif.

## ✨ Novelty & Keunggulan (Apa yang Baru?)

Proyek ini memiliki beberapa aspek **Novelty** dibandingkan sistem pemantauan banjir standar:

1.  **Hibrid Live Sensor & Weather API:** Menggabungkan data *live* Tinggi Muka Air (TMA) dari portal **SIHKA** (Sungai Mahakam & Karang Mumus) dengan data prediksi cuaca presisi dari **Open-Meteo**.
2.  **High-Resolution Smart Grid:** Menggunakan analisis grid dengan kerapatan **200 meter** (mencakup >17.000 titik pantau). Ini memungkinkan deteksi risiko hingga ke level kelurahan dan blok bangunan.
3.  **SCS Curve Number Integration:** Mengintegrasikan model hidrologi klasik (SCS-CN) dengan Machine Learning modern. Sistem secara otomatis mengambil data tutupan lahan (*land cover*) terbaru dari OpenStreetMap untuk menghitung koefisien resapan air tanah secara dinamis.
4.  **Automated Daily Learning:** Pipeline Airflow tidak hanya memperbarui data, tapi juga melatih ulang (*re-train*) model XGBoost setiap ada perubahan parameter cuaca yang signifikan, memastikan prediksi tetap tajam.
5.  **Executive-Ready Dashboard:** Desain premium dengan pendekatan *Data Journalism*, memberikan ringkasan naratif otomatis tentang jumlah populasi terdampak dan zonasi risiko.

## 🛠️ Tech Stack

- **Languange:** Python 3.12+ (Backend), JavaScript/React (Frontend)
- **Data Engineering:** Apache Airflow, GeoPandas, Shapely
- **Machine Learning:** XGBoost (Optimized Parallel Processing), Scikit-learn
- **Spatial Data:** OSMnx, OpenTopoData (DEM), SIHKA (Web Scraping)
- **Visualisasi:** MapLibre GL, ECharts, Axios (with Cache-Busting)

## 🔄 Alur Pipeline (Daily Workflow)

1.  **Data Extraction:** Mengambil batas wilayah, elevasi, land cover, tinggi sungai, dan curah hujan.
2.  **Hydrological Modelling:** Menghitung *Slope*, *Distance to River*, dan *Curve Number (CN)*.
3.  **Intelligence Layer:** Melatih model XGBoost menggunakan 8 core CPU server untuk memprediksi probabilitas banjir di 17.000+ titik.
4.  **Static Export:** Mengonversi hasil spasial (GeoPackage) ke JSON statis yang ringan.
5.  **Git-Sync & Deploy:** Melakukan *push* data ke GitHub secara otomatis dan memicu *Deployment Hook* di Vercel.

## 📊 Dashboard Access
Kunjungi dashboard interaktif di: **[prediksi-banjir-samarinda.vercel.app](https://prediksi-banjir-samarinda.vercel.app/)**

---
**Developed by:** Bidang 4 - Diskominfo Kota Samarinda
