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
    - Fungsi: Menjalankan Apache Airflow untuk orkestrasi pipeline data, pelatihan model ML, dan pemrosesan GIS.
2.  **GitHub (Data Bridge):** Menjadi jembatan sinkronisasi antara hasil proses di server dan dashboard.
3.  **Vercel (Frontend):** Hosting dashboard berbasis React + MapLibre yang ringan dan cepat.

---

## 🤖 Machine Learning Implementation

Proyek ini menggunakan pendekatan **Supervised Learning** dengan mekanisme *fallback* otomatis untuk menjamin ketersediaan prediksi meskipun terdapat kendala pada *library* tertentu di server.

### 1. Model Utama & Hierarki Fallback
- **XGBoost (Primary):** Menggunakan metode `tree_method='hist'` untuk pemrosesan data grid besar secara cepat. Dioptimalkan dengan 8 cor CPU (parallel processing) untuk menjaga stabilitas server.
- **Random Forest (Secondary):** Digunakan sebagai cadangan jika XGBoost gagal diinisialisasi. Memberikan hasil yang stabil melalui teknik *bagging*.
- **Logistic Regression (Tertiary):** Model dasar (*baseline*) jika model ensemble tidak tersedia.

### 2. Fitur Prediksi (Input Features)
Setiap titik grid dianalisis berdasarkan 8 parameter kunci:
- **Hidrologi Statis:** Elevasi (DEM), Kemiringan lereng (*Slope*), dan Jarak ke badan sungai (*Distance to River*).
- **Karakteristik Tanah:** *Curve Number (CN)* yang diekstrak dari penggunaan lahan (*land cover*) OpenStreetMap.
- **Dinamika Cuaca:** Curah hujan hari ini (*T*), serta akumulasi hujan 1 hari sebelumnya (*T-1*), 2 hari (*T-2*), dan 3 hari (*T-3*) untuk menghitung tingkat kejenuhan tanah.

### 3. Training & Labeling
Karena ketiadaan label banjir historis real-time per titik, sistem menggunakan **Sigmoid Calibration Formula** yang diselaraskan dengan koefisien hidrologi lokal Samarinda untuk menghasilkan label target awal, yang kemudian dipelajari oleh model ML untuk generalisasi pola spasial.

---

## 🔄 Tahapan Pipeline (Technical Stages)

Pipeline orkestrasi di Apache Airflow menjalankan urutan tugas berikut secara otomatis setiap malam:

1.  **📍 Batas Wilayah (Boundary Retrieval):** Mengambil data administratif terbaru dari API atau file lokal GeoJSON.
2.  **🏔️ Topografi & GIS (Spatial Analysis):**
    - Mendownload data elevasi dari OpenTopoData.
    - Menghitung kemiringan lereng (*Slope*) per titik grid.
    - Menghitung jarak Euclid setiap titik ke vektor sungai (OSM).
3.  **🌦️ Cuaca & Hidrometri (Live Data):**
    - Mengambil data curah hujan 4 hari terakhir dari Open-Meteo API.
    - Melakukan *scrapping* tinggi muka air (TMA) Sungai Mahakam dan Karang Mumus dari portal SIHKA.
4.  **🏙️ Karakteristik Lahan (Land Cover Analysis):** 
    - Mengunduh data tutupan lahan OSMnx.
    - Memetakan jenis lahan (hutan, pemukiman, aspal) ke nilai *SCS Curve Number*.
5.  **🤖 Intelligence Layer (ML Execution):**
    - Sinkronisasi data menjadi satu matriks fitur.
    - Melatih model dan memprediksi probabilitas banjir di ~18.000 titik.
6.  **📦 Data Serialization:** Mengonversi hasil prediksi GeoPandas ke file JSON statis untuk konsumsi frontend.
7.  **📤 Deployment Sync:** Push otomatis ke GitHub dan pemicuan webhook Vercel untuk pembaruan dashboard.

---

## ✨ Novelty & Keunggulan
- **Hibrid Live Sensor & Weather API.**
- **High-Resolution Smart Grid (200m).**
- **Automated Daily Re-training.**
- **Integration of SCS-CN with ML.**

## 📊 Dashboard Access
**[prediksi-banjir-samarinda.vercel.app](https://prediksi-banjir-samarinda.vercel.app/)**

---
**Developed by:** Ahmad Sopian - Data Scientist / Data Engineering - Diskominfo Kota Samarinda
