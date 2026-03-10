---
title: Hydrological Modelling Expert
description: Memahami konsep Slope (kemiringan), Flow Direction, dan Flow Accumulation.
---

# Panduan Pemodelan Hidrologi & Limpasan Air Samarinda

Skill ini memberikan panduan kepada agent/environment dalam menerapkan pemodelan hidrologi untuk menghitung potensi akumulasi, limpasan (*runoff*), dan rute aliran air hujan dari wilayah perbukitan menuju dataran rendah di Samarinda (khususnya wilayah DAS Sungai Karang Mumus).

## 1. Pemahaman Konsep Permukaan & Aliran Air

Dalam pemodelan topografi Samarinda, agen diwajibkan memahami tahapan pengolahan kontur menjadi sistem drainase virtual:

- **DEM (Digital Elevation Model)**: Dasar pembacaan tinggi muka bumi. Jika menggunakan data satelit, area perbukitan (seperti Sempaja) harus memiliki nilai meter yang lebih besar dari area muara Karang Mumus.
- **Slope (Kemiringan Lahan)**: Derajat curam lereng. Semakin tinggi kemiringan, aliran air *runoff* semakin cepat dan potensial membawa sedimen.
- **Flow Direction**: Menghitung arah aliran dari setiap sel (piksel) ke piksel tetangga terendah (metode D8).
- **Flow Accumulation**: Menjumlahkan berapa banyak sel hulu yang bermuara/mengalir masuk ke satu sel spesifik. Area dengan akumulasi sel sangat besar (misal: > 1000 sel) didefinisikan secara rasional sebagai titik genangan atau alur batas sungai alami.

## 2. Pengukuran Limpasan Permukaan (Runoff)

Untuk mengkalkulasi besaran limpasan dari hujan menjadi genangan di darat, digunakan dua instrumen formula utama berikut yang disesuaikan dengan **jenis tutupan lahan** di Samarinda.

### a. Metode Curve Number (SCS-CN)
Digunakan untuk menaksir seberapa banyak curah hujan yang tidak meresap ke tanah berdasarkan tutupan lahan (land cover) dan jenis hidrologi tanah (Hydrological Soil Group).

- **Analisis Lahan Samarinda**:
  - Lahan Tambang/Lahan Terbuka: Beri nilai CN sangat tinggi (contoh: 88-95). Sedikit sekali yang meresap.
  - Perkotaan/Pusat Kota (Beton/Aspal): Beri nilai CN tinggi (contoh: 90-98).
  - Hutan Semak/Vegetasi Rapat: Beri nilai CN rendah (contoh: 55-70). Banyak potensi infiltrasi air.

**Logika Perhitungan Volume Limpasan (Q):**
\\[ Q = \frac{(P - I_a)^2}{(P - I_a) + S} \\]
*(Dimana `P` = curah hujan, `I_a` = abstraksi awal, `S` = potensi penyimpanan maksimum).*

### b. Rumus Kecepatan Debit Manning
Formula ini dipakai untuk memodelkan kelancaran air saat menyusuri saluran drainase pinggiran kota atau alur Sungai Karang Mumus. Koefisien Kekasaran Manning (`n`) memengaruhi hasil:

- **Analisis Kekasaran (n)**:
  - Saluran Beton/Semen: `n = 0.013 – 0.015` (aliran lancar dan cepat masuk sungai utama)
  - Saluran alami/Sungai penuh semak belukar: `n = 0.035 – 0.050` (aliran terhambat, dapat meningkatkan *backwater* atau banjir rob lokal saat air pasang bertemu limpasan bukit)

## 3. Instruksi Eksekusi Logika Agen

Apabila agen menerima penugasan langsung terkait pemodelan ini, maka segera bertindak berdasarkan pedoman berikut:

> **Perintah Primer (Prompt Instruksi):**
> "Terapkan logika hidrologi untuk menghitung akumulasi aliran air dari daerah perbukitan menuju daerah rendah di sekitar Sungai Karang Mumus."

Saat diinstruksikan perintah tersebut, **Agen harus**:
1. Merujuk ke berkas batas tutupan lahan (*land cover*) Kota Samarinda.
2. Membaca/merender peta topografi (DEM) di CRS UTM 50S (`EPSG:32750`) khusus untuk area *catchment* Karang Mumus.
3. Menghitung profil **Slope** menjadi derajat kemiringan.
4. Menambahkan atribut limpasan (runoff) metode **Curve Number** menggunakan parameter curah hujan hari ini/data cuaca.
5. Memetakan vektor **Flow Accumulation** dengan mencari rute jatuhnya air limpasan dari *pixel* tebing ke titik terendah sempadan sungai (menghitung `Flow Direction`).
6. Merekomendasikan/menganalisa bagian persimpangan saluran mana yang mungkin tidak menampung debit kecepatan air yang diestimasi menggunakan **Hukum Manning**.