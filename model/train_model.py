"""
model/train_model.py
Melatih model XGBoost untuk prediksi probabilitas banjir di Samarinda.
Input fitur: elevation, slope_deg, dist_sungai_m, cn_score, rain_today, rain_h_minus_1/2/3
Target: P(Flood) via formula Sigmoid dengan koefisien kalibrasi.
Output: model/flood_model.pkl
"""

import os
import sys
import traceback
import numpy as np
import joblib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import (
    BETA_0, BETA_1, BETA_2, BETA_3,
    PATH_GRID_FEAT, PATH_MODEL
)

# Bobot tambahan
BETA_5    = 0.5    # CN (Curve Number) — beton/kota = risiko naik
BETA_LAG_1 = 0.3  # Hujan kemarin
BETA_LAG_2 = 0.15 # Hujan 2 hari lalu
BETA_LAG_3 = 0.05 # Hujan 3 hari lalu


def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -500, 500)))


def safe_float_array(gdf, col, default=0.0):
    """Mengambil kolom dari GDF secara aman ke numpy float array."""
    if col not in gdf.columns:
        print(f"[MODEL] ⚠️  Kolom '{col}' tidak ditemukan, menggunakan default {default}")
        return np.full(len(gdf), default, dtype=np.float64)
    try:
        arr = gdf[col].fillna(default).astype(np.float64).values
        # Ganti Inf / -Inf jika ada
        arr = np.where(np.isinf(arr), default, arr)
        return arr
    except Exception as e:
        print(f"[MODEL] ⚠️  Gagal konversi kolom '{col}' ke float: {e}. Menggunakan default.")
        return np.full(len(gdf), default, dtype=np.float64)


def generate_target_labels(gdf):
    """
    Menghitung P(Flood) menggunakan formula sigmoid kalibrasi Samarinda.
    Semua fitur dinormalisasi z-score agar distribusi logit seimbang.
    """
    rain_0  = safe_float_array(gdf, "rain_today",     0.0)
    rain_1  = safe_float_array(gdf, "rain_h_minus_1", 0.0)
    rain_2  = safe_float_array(gdf, "rain_h_minus_2", 0.0)
    rain_3  = safe_float_array(gdf, "rain_h_minus_3", 0.0)
    # Fallback ke rainfall_mm jika rain_today tidak ada
    if "rain_today" not in gdf.columns and "rainfall_mm" in gdf.columns:
        rain_0 = safe_float_array(gdf, "rainfall_mm", 0.0)

    elev      = safe_float_array(gdf, "elevation",     10.0)
    dist      = safe_float_array(gdf, "dist_sungai_m", 5000.0)
    slop      = safe_float_array(gdf, "slope_deg",     0.0)
    cn_score  = safe_float_array(gdf, "cn_score",      75.0)

    def zscore(arr):
        std = arr.std()
        return (arr - arr.mean()) / (std if std > 1e-6 else 1.0)

    logit = (BETA_0
             + BETA_1    * zscore(rain_0)
             + BETA_LAG_1 * zscore(rain_1)
             + BETA_LAG_2 * zscore(rain_2)
             + BETA_LAG_3 * zscore(rain_3)
             - BETA_2    * zscore(elev)
             - BETA_3    * zscore(dist)
             + 0.3       * (-zscore(slop))
             + BETA_5    * zscore(cn_score))

    return sigmoid(logit)


def train_model(gdf):
    """
    Melatih model dengan fallback: XGBoost → RandomForest → LogisticRegression.
    Dilengkapi try-except menyeluruh dengan traceback untuk debugging GitHub Actions.
    """
    try:
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report
        from sklearn.pipeline import Pipeline
        import pandas as pd

        print("[MODEL] Menyiapkan feature matrix...")

        # Kolom fitur yang akan digunakan — urutkan dari yang paling penting
        DESIRED_FEATURES = [
            "elevation", "slope_deg", "dist_sungai_m", "cn_score",
            "rain_today", "rain_h_minus_1", "rain_h_minus_2", "rain_h_minus_3"
        ]
        # Gunakan kolom yang memang ada di dataset
        feature_cols = [c for c in DESIRED_FEATURES if c in gdf.columns]

        if len(feature_cols) == 0:
            raise ValueError(f"Tidak ada kolom fitur yang cocok! Kolom tersedia: {list(gdf.columns)}")

        print(f"[MODEL] Fitur yang digunakan ({len(feature_cols)}): {feature_cols}")

        # Bangun X: isi NaN dengan 0, konversi ke float64
        X = gdf[feature_cols].fillna(0).astype(np.float64).values
        print(f"[MODEL] Shape X: {X.shape} | dtype: {X.dtype}")
        print(f"[MODEL] NaN dalam X: {np.isnan(X).sum()} | Inf dalam X: {np.isinf(X).sum()}")

        # Ganti Inf jika ada (keamanan ekstra)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        # Generate label target probabilistik
        p_flood = generate_target_labels(gdf)
        gdf = gdf.copy()
        gdf["p_flood"] = p_flood

        # Gunakan threshold absolut agar persentase banjir dinamis sesuai cuaca,
        # dan bukan median yang selalu memaksa 50% wilayah banjir setiap hari.
        threshold = 0.55
        y = (p_flood >= threshold).astype(int)

        # Pastikan minimal ada 5% sampel di kedua kelas agar model bisa dilatih
        if sum(y==1) < len(y) * 0.05:
            # Jika terlalu sedikit banjir (kering), ambil top 5%
            threshold = np.percentile(p_flood, 95)
            y = (p_flood >= threshold).astype(int)
        elif sum(y==0) < len(y) * 0.05:
            # Jika terlalu banyak banjir (badai parah), sisakan bottom 5%
            threshold = np.percentile(p_flood, 5)
            y = (p_flood >= threshold).astype(int)

        print(f"[MODEL] Dataset: {len(X)} sampel")
        print(f"[MODEL] Threshold Final: {threshold:.4f}")
        print(f"[MODEL] Label distribusi: Aman={int(sum(y==0))}, Risiko={int(sum(y==1))}")

        unique_classes = np.unique(y)
        stratify_arg = y if len(unique_classes) > 1 else None
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=stratify_arg
        )

        # ── Pilih model: XGBoost > RandomForest > LogisticRegression ──
        model_name = None
        clf = None

        try:
            import xgboost as xgb
            xgb_version = tuple(int(x) for x in xgb.__version__.split('.')[:2])
            print(f"[MODEL] XGBoost versi {xgb.__version__} terdeteksi")

            # Parameter 'device' hanya tersedia di XGBoost >= 2.0
            xgb_params = dict(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                tree_method='hist',
                random_state=42,
                scale_pos_weight=(sum(y==0) / max(sum(y==1), 1)),
                n_jobs=-1,
                verbosity=0
            )
            if xgb_version >= (2, 0):
                xgb_params['device'] = 'cpu'  # Hanya di XGBoost >= 2.0

            clf = xgb.XGBClassifier(**xgb_params)
            model_name = "XGBoost"
        except Exception as ex_xgb:
            print(f"[MODEL] ⚠️  XGBoost gagal: {ex_xgb}. Fallback ke RandomForest.")

        if clf is None:
            try:
                from sklearn.ensemble import RandomForestClassifier
                clf = RandomForestClassifier(
                    n_estimators=50, max_depth=6,
                    random_state=42, class_weight='balanced', n_jobs=-1
                )
                model_name = "RandomForest"
            except Exception as ex_rf:
                print(f"[MODEL] ⚠️  RandomForest gagal: {ex_rf}. Fallback ke LogisticRegression.")

        if clf is None:
            from sklearn.linear_model import LogisticRegression
            clf = LogisticRegression(random_state=42, max_iter=1000, class_weight='balanced')
            model_name = "LogisticRegression"

        print(f"[MODEL] Melatih {model_name}...")

        model_pipeline = Pipeline([
            ("scaler",     StandardScaler()),
            ("classifier", clf)
        ])
        model_pipeline.fit(X_train, y_train)

        # Evaluasi
        y_pred = model_pipeline.predict(X_test)
        present  = sorted(np.unique(np.concatenate([y_test, y_pred])))
        names    = {0: "Aman", 1: "Risiko"}
        print(classification_report(
            y_test, y_pred,
            labels=present,
            target_names=[names[c] for c in present]
        ))

        # Simpan model
        os.makedirs(os.path.dirname(PATH_MODEL), exist_ok=True)
        joblib.dump({
            "pipeline":     model_pipeline,
            "feature_cols": feature_cols,
            "model_name":   model_name
        }, PATH_MODEL)
        print(f"[MODEL] ✅ Model disimpan → {PATH_MODEL}")

        # Prediksi probabilitas untuk seluruh dataset
        X_full = np.nan_to_num(
            gdf[feature_cols].fillna(0).astype(np.float64).values,
            nan=0.0, posinf=0.0, neginf=0.0
        )
        gdf["p_flood_pred"] = model_pipeline.predict_proba(X_full)[:, 1]
        print(f"[MODEL] ✅ Prediksi selesai. "
              f"p_flood_pred range: [{gdf['p_flood_pred'].min():.4f}, {gdf['p_flood_pred'].max():.4f}]")

        return gdf, model_pipeline

    except Exception as e:
        print("\n" + "="*60)
        print("[MODEL] ❌ FATAL ERROR saat melatih model:")
        print(f"  {type(e).__name__}: {e}")
        print("="*60)
        traceback.print_exc()
        print("="*60 + "\n")
        raise  # Re-raise agar GitHub Actions mendeteksi kegagalan


def run():
    """Entry point jika script dipanggil langsung."""
    import geopandas as gpd
    if not os.path.exists(PATH_GRID_FEAT):
        raise FileNotFoundError(f"Grid features tidak ditemukan: {PATH_GRID_FEAT}")

    gdf = gpd.read_file(PATH_GRID_FEAT)
    print(f"[MODEL] Grid dimuat: {len(gdf)} baris | Kolom: {list(gdf.columns)}")
    gdf, model = train_model(gdf)
    gdf.to_file(PATH_GRID_FEAT, driver="GPKG")
    print("[MODEL] ✅ Prediksi tersimpan ke grid features.")
    return gdf, model


if __name__ == "__main__":
    run()
