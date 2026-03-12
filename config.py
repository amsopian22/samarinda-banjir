# config.py
# ============================================================
# Konfigurasi Sentral: Samarinda Hydro-Intelligence System
# ============================================================

# --- Koordinat Referensi Samarinda ---
LAT_CENTER  = -0.5022
LON_CENTER  = 117.1536

# Bounding Box untuk unduhan DEM (min_lon, min_lat, max_lon, max_lat)
BBOX_SAMARINDA = (116.75, -1.10, 117.70, 0.05)

# --- Sistem Referensi Koordinat ---
CRS_GEO     = "EPSG:4326"    # WGS84 - untuk data geografis & web map
CRS_UTM     = "EPSG:32750"   # WGS84 / UTM Zone 50S - untuk analisis spasial Samarinda

# --- Parameter Model Prediksi ---
# Koefisien sigmoids: P(Flood) = sigmoid(b0 + b1*Rain - b2*Elev - b3*Dist)
BETA_0 = 0.5    # Bias / intercept
BETA_1 = 0.08   # Pengaruh curah hujan (mm)
BETA_2 = 0.03   # Pengaruh elevasi (meter)
BETA_3 = 0.0002 # Pengaruh jarak ke sungai (meter)

# Threshold probabilitas banjir
FLOOD_THRESHOLD = 0.50  # >= 50% dianggap zona risiko tinggi

# --- Grid Sampling ---
GRID_SPACING_M = 200  # Jarak antar titik sampling ditingkatkan untuk resolusi tinggi (Server 20 CPU/64GB)

# --- Threshold Memory Guard ---
RAM_LIMIT_GB = 12.0  # Batas maksimum RAM ditingkatkan (Server 64GB)

# --- Path Data ---
PATH_BOUNDARY    = "data/boundary/samarinda.geojson"
PATH_DEM         = "data/dem/samarinda_dem.tif"
PATH_SLOPE       = "data/processed/slope.tif"
PATH_RAINFALL    = "data/processed/rainfall_today.json"
PATH_RIVER       = "data/processed/sungai_samarinda.gpkg"
PATH_GRID_FEAT   = "data/processed/grid_features.gpkg"
PATH_MODEL       = "model/flood_model.pkl"
PATH_HEATMAP     = "output/heatmap_samarinda.html"
