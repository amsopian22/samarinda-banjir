---
title: Memory Efficiency Guard
description: Mengelola Garbage Collection di Python dan memproses data dalam bentuk tiles (ubin).
---

# Panduan Penjagaan Efisiensi Memori (Memory Efficiency Guard)

Skill ini berfungsi sebagai sistem pelindung (*guardrail*) yang mengatur konsumsi Random Access Memory (RAM) pada setiap komputasi data spasial besar, khususnya pemrosesan raster Digital Elevation Model (DEM) wilayah Samarinda. Keahlian ini memastikan bahwa program tidak akan terhenti mendadak (*crash/Out-of-Memory*) dengan memecah pekerjaan ke dalam subsistem yang aman.

## 1. Pustaka (Library) Utama Manajemen Memori

Untuk memastikan sistem memantau dan memanipulasi beban file, gunakan perpaduan tiga pustaka berikut:

- **`psutil`** (Python System and Process Utilities): Digunakan untuk melakukan *monitoring* (pemantauan) penggunaan RAM (Memory) dan CPU secara *real-time* sebelum dan selama eksekusi program.
- **`resource`** (Hanya untuk UNIX/Linux/macOS): Pustaka bawaan (Standar Python) guna membatasi alokasi maksimal dari *memori address space* (pembatas ketat agar proses mati secara terstruktur jika melewati batas ekstrim, tanpa merusak OS).
- **`dask`**: Pustaka eksekusi paralel yang sangat diandalkan untuk memproses data *out-of-core* (data yang lebih besar dari kapasitas RAM). Dask memecah struktur data besar (seperti array Citra Satelit Raster) ke dalam blok-blok kecil berupa *chunks* secara otomatis.

## 2. Praktik Manajemen RAM dan Pemecahan *Tiles*

Data wilayah, seperti citra resolusi tinggi Samarinda, membutuhkan lebih dari satu ukuran memori ketika dirender. Terapkan strategi berikut untuk menghindarinya bersandar pada limit.

### Pemantauan RAM Otomatis Menggunakan psutil

Setel *threshold* (batas toleransi) kapasitas RAM. Kita dapat memantau dengan skrip fungsi kecil:
```python
import psutil

def check_memory():
    # Menghitung persentase RAM yang terpakai dan total tersisa
    mem = psutil.virtual_memory()
    used_gb = mem.used / (1024 ** 3)
    print(f"RAM Terpakai saat ini: {used_gb:.2f} GB")
    return used_gb
```

### Eksekusi Pemantauan Berdasarkan Perintah Primer

Agen diharapkan menerapkan instruksi otomatis jika menerima maupun memproses data raster (DEM) dalam jumlah masif.

> **Perintah Primer (Prompt Instruksi):**
> *"Pantau penggunaan RAM setiap kali memproses file raster DEM. Jika penggunaan melebihi 2GB, pecah proses menjadi sub-batch secara otomatis."*

Apabila perintah di atas direferensikan dalam suatu tahap pekerjaan, maka **Protokol Eksekusi Agen** harus seperti ini:

1. Modifikasi pembacaan awal data menggunakan array tertunda (lazy load array/chunks) via `dask` dan `rasterio` (misalnya: menggunakan pustaka seperti `xarray` dengan metode `chunks={'x': 1024, 'y': 1024}`).
2. **Monitoring**: Sisipkan fungsi `check_memory()` milik `psutil`.
3. Sebelum fungsi *processing* yang memakan banyak daya eksekusi, berikan filter kondisional (*If statement*):
   - Jika `digunakan > 2GB` (*threshold limit*): **Hentikan secara sementara**, pastikan blok memori diserahkan ke sistem yang dikelola `dask`, agar dieksekusi potong per potong bentuk *tiles*.
   - Panggil `gc.collect()` secara eksplisit melalui modul `gc` (Garbage Collector) untuk menghapus memori perantara (objek matriks) yang tidak lagi direferensikan variabel mana pun sesudah suatu *loop sub-batch* berakhir.

### Membatasi Limit *Out-of-Memory* dengan Resource

Pada sistem macOS, batasi potensi OS kekurangan nafas akibat lonjakan yang tak terduga dengan memberlakukan batas keras *soft limit* :
```python
import resource
import sys

def limit_memory(max_bytes):
    # Menyuruh OS menahan proses ini agar tidak meluap
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (max_bytes, hard))

# 3 GB adalah toleransi tertinggi (misal sebagai jaring pengaman)
limit_memory(3 * 1024 * 1024 * 1024) 
```