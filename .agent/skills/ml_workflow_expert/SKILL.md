---
title: Machine Learning Workflow Expert
description: Panduan standar untuk membangun, melatih, dan mengelola alur kerja Machine Learning yang kuat dan terotomatisasi.
---

# 🤖 Machine Learning Workflow Expert

Skill ini mendefinisikan standar terbaik dalam mengelola pipeline Machine Learning (ML), mulai dari eksperimen lokal hingga otomatisasi di server produksi (MLOps).

## 🌍 Environment & Setup

Gunakan lingkungan Conda berikut untuk menjaga konsistensi:

| Environment | Kegunaan | Perintah Aktivasi |
| :--- | :--- | :--- |
| **agentic_ai** | Pengembangan model AI, riset, dan eksperimentasi lokal. | `conda activate agentic_ai` |
| **diskominfo** | Pekerjaan umum dan integrasi sistem. | `conda activate diskominfo` |
| **flood_pipeline** | Environment khusus produksi di Airflow Server. | `conda activate flood_pipeline` |

## 🚀 Best Practices dalam Alur Kerja ML

Agar pipeline ML berjalan stabil dan akurat, ikuti prinsip-prinsip berikut:

### 1. Modularitas Pipeline
Bagi kode menjadi modul-modul terpisah (fetch data, transform, train, export).
- **Keuntungan:** Mudah didebug dan memungkinkan pemrosesan ulang pada tahap tertentu tanpa mengulang seluruh pipeline.

### 2. Mekanisme Fallback (Robustness)
Jangan mengandalkan satu algoritme saja. Berikan opsi cadangan jika library utama gagal.
- **Contoh:** `XGBoost` (Utama) → `RandomForest` (Fallback) → `LogisticRegression` (Baseline).

### 3. Manajemen Resource Server
Optimalkan penggunaan perangkat keras berdasarkan spesifikasi server:
- **Parallel Processing:** Gunakan `n_jobs` yang sesuai (misal: 8 core dari 20 core) agar tidak membekukan sistem lain.
- **Memory Guard:** Implementasikan pembatasan RAM (`RAM_LIMIT_GB`) jika bekerja dengan dataset besar di lingkungan berbagi.

### 4. Validasi Data & Fitur
- Selalu periksa nilai `NaN` atau `Inf` sebelum melatih model.
- Simpan daftar fitur (`feature_cols`) dalam metadata model untuk memastikan konsistensi saat fase prediksi.

### 5. Logging & Traceability
Gunakan `traceback` secara detail, terutama saat menjalankan proses di lingkungan remote seperti Docker atau SSH Airflow, agar error mudah diidentifikasi dari log.

### 6. Otomatisasi (CI/CD for ML)
Integrasikan hasil model dengan dashboard secara otomatis melalui Git-Sync dan Webhook (seperti Vercel) untuk memastikan data yang dilihat pengguna selalu *up-to-date*.

## 📈 Monitoring Kualitas
- Pantau **Akurasi, Presisi, dan Recall** secara berkala.
- Skalibasi model menggunakan metode seperti *Sigmoid Calibration* jika label target nyata terbatas.