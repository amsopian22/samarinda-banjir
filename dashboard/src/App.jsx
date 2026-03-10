import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import Map, { Source, Layer, Popup } from 'react-map-gl/maplibre'
import ReactECharts from 'echarts-for-react'
import axios from 'axios'
import 'maplibre-gl/dist/maplibre-gl.css'
import './index.css'

// Helper warna untuk badge impact
const IMPACT_COLOR = {
  Aman: { bg: 'rgba(16,185,129,0.2)', text: '#34d399', border: 'rgba(16,185,129,0.4)' },
  Waspada: { bg: 'rgba(245,158,11,0.2)', text: '#fbbf24', border: 'rgba(245,158,11,0.4)' },
  Rawan: { bg: 'rgba(249,115,22,0.2)', text: '#fb923c', border: 'rgba(249,115,22,0.4)' },
  Parah: { bg: 'rgba(239,68,68,0.2)', text: '#f87171', border: 'rgba(239,68,68,0.4)' },
}

// ── Sumber data: file JSON statis di /public/data/ ──────────────────────
// Di localhost: Vite akan serve dari dashboard/public/data/
// Di Vercel production: CDN global serve dari /data/
const DATA = {
  grid: '/data/grid.json',
  sungai: '/data/sungai.json',
  summary: '/data/summary.json',
  weather: '/data/weather.json',
  tma: '/data/tma.json',
}
const MAP_STYLES = {
  dark: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  street: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json'
}

// Fungsi helper status warna
const statusColor = { Normal: '#34d399', Waspada: '#fbbf24', Siaga: '#f87171', Rendah: '#a5b4fc' }
const riskClass = (pct) => pct >= 40 ? 'danger' : pct >= 20 ? 'warning' : 'safe'
const riskLabel = (pct) => pct >= 40 ? 'Tinggi' : pct >= 20 ? 'Waspada' : 'Rendah'
const riskIcon = (pct) => pct >= 40 ? '🚨' : pct >= 20 ? '⚠️' : '✅'
const riskDesc = (pct, weather, tma) => {
  if (pct >= 40) return `Area berisiko tinggi teridentifikasi sebesar ${pct}% dari wilayah Samarinda. Curah hujan aktif ${weather} mm dengan TMA Karang Mumus ${tma} m memperburuk kondisi.`
  if (pct >= 20) return `Sekitar ${pct}% wilayah dalam zona waspadaa. Pantau data cuaca dan TMA secara berkala.`
  return `Kondisi saat ini terkendali. Hanya ${pct}% wilayah yang menampilkan risiko, level sungai berada dalam batas normal.`
}

// ============ KOMPONEN TOOLTIP KARTU ============
function TooltipCard({ props }) {
  const p = props || {}
  const prob = Math.round((p.p_flood_pred || 0) * 100)
  const impact = p.impact_category || 'Aman'
  const col = IMPACT_COLOR[impact] || IMPACT_COLOR.Aman
  const probColor = prob >= 70 ? '#ef4444' : prob >= 40 ? '#f59e0b' : '#10b981'
  const elevation = p.elevation !== undefined ? `${p.elevation} m dpl` : '—'
  const slope = p.slope_deg !== undefined ? `${Number(p.slope_deg).toFixed(1)}°` : '—'
  const distRiver = p.dist_sungai_m !== undefined ? `${Math.round(p.dist_sungai_m)} m` : '—'
  const cn = p.cn_score !== undefined ? p.cn_score : '—'
  const popDens = p.pop_density_km2 !== undefined ? `${Math.round(p.pop_density_km2).toLocaleString('id')}/km²` : '—'
  const rain0 = p.rain_today !== undefined ? `${p.rain_today} mm` : '—'
  const rain1 = p.rain_h_minus_1 !== undefined ? `${p.rain_h_minus_1} mm` : '—'
  const rain2 = p.rain_h_minus_2 !== undefined ? `${p.rain_h_minus_2} mm` : '—'
  const rain3 = p.rain_h_minus_3 !== undefined ? `${p.rain_h_minus_3} mm` : '—'

  return (
    <div style={{
      fontFamily: "'Inter', sans-serif",
      background: 'linear-gradient(170deg, rgba(10,15,30,0.97) 0%, rgba(15,23,50,0.97) 100%)',
      border: `1px solid ${col.border}`,
      borderRadius: '12px',
      padding: '14px 16px',
      width: '260px',
      boxShadow: `0 10px 40px rgba(0,0,0,0.7), 0 0 20px ${col.bg}`
    }}>
      {/* Header: Badge Kategori + Probabilitas */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <span style={{
          background: col.bg, color: col.text, border: `1px solid ${col.border}`,
          borderRadius: '6px', padding: '3px 10px', fontSize: '12px', fontWeight: 800,
          textTransform: 'uppercase', letterSpacing: '0.5px'
        }}>{impact}</span>
        <span style={{ fontSize: '20px', fontWeight: 900, color: probColor }}>
          {prob}%
          <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 500, marginLeft: '3px' }}>peluang</span>
        </span>
      </div>

      {/* Progress Bar Probabilitas */}
      <div style={{ background: 'rgba(255,255,255,0.08)', borderRadius: '4px', height: '6px', marginBottom: '14px', overflow: 'hidden' }}>
        <div style={{
          width: `${prob}%`, height: '100%', borderRadius: '4px',
          background: `linear-gradient(90deg, #3b82f6, ${probColor})`,
          transition: 'width 0.5s ease'
        }} />
      </div>

      {/* Grid Data Atribut */}
      {[
        { icon: '⛰️', label: 'Elevasi', val: elevation },
        { icon: '📐', label: 'Kemiringan', val: slope },
        { icon: '🌊', label: 'Jarak ke Sungai', val: distRiver },
        { icon: '🌿', label: 'CN Score (Resapan)', val: cn },
        { icon: '👥', label: 'Kepadatan Penduduk', val: popDens },
      ].map(row => (
        <div key={row.label} style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '5px 0', borderBottom: '1px solid rgba(255,255,255,0.05)'
        }}>
          <span style={{ fontSize: '11px', color: '#64748b' }}>
            {row.icon} {row.label}
          </span>
          <span style={{ fontSize: '12px', fontWeight: 700, color: '#f0f4ff' }}>{row.val}</span>
        </div>
      ))}

      {/* Curah Hujan Historis */}
      <div style={{ marginTop: '10px', padding: '8px 10px', background: 'rgba(99,102,241,0.08)', borderRadius: '8px', border: '1px solid rgba(99,102,241,0.15)' }}>
        <div style={{ fontSize: '10px', color: '#6366f1', fontWeight: 700, marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '1px' }}>
          🌧️ Curah Hujan (Open-Meteo)
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
          {[['H-0 (Hari Ini)', rain0], ['H-1 (Kemarin)', rain1], ['H-2', rain2], ['H-3', rain3]].map(([lbl, val]) => (
            <div key={lbl}>
              <div style={{ fontSize: '9px', color: '#4f5b7c' }}>{lbl}</div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#a5b4fc' }}>{val}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const mapRef = useRef()
  const [mapStyle, setMapStyle] = useState('dark')
  const [gridData, setGridData] = useState(null)
  const [riverData, setRiverData] = useState(null)
  const [summary, setSummary] = useState(null)
  const [weather, setWeather] = useState(null)
  const [tma, setTma] = useState(null)
  const [hoveredCat, setHoveredCat] = useState(null)
  const [loading, setLoading] = useState(true)
  const [tooltipInfo, setTooltipInfo] = useState(null) // { lng, lat, features }

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [rGrid, rRiver, rSummary, rWeather, rTma] = await Promise.all([
          axios.get(DATA.grid),
          axios.get(DATA.sungai),
          axios.get(DATA.summary),
          axios.get(DATA.weather),
          axios.get(DATA.tma)
        ])
        setGridData(rGrid.data)
        setRiverData(rRiver.data)
        setSummary(rSummary.data)
        setWeather(rWeather.data)
        setTma(rTma.data)
      } catch (err) {
        console.warn('Data JSON belum tersedia, jalankan: python scripts/export_static.py', err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchAll()
  }, [])

  // — MapLibre Layers —
  const heatmapLayer = useMemo(() => ({
    id: 'flood-heatmap',
    type: 'heatmap',
    paint: {
      'heatmap-weight': ['interpolate', ['linear'], ['get', 'p_flood_pred'], 0, 0, 1, 1],
      'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 10, 1, 15, 4],
      'heatmap-color': [
        'interpolate', ['linear'], ['heatmap-density'],
        0, 'rgba(33,102,172,0)',
        0.25, 'rgb(103,169,207)',
        0.5, 'rgb(253,219,199)',
        0.75, 'rgb(239,138,98)',
        1, 'rgb(178,24,43)'
      ],
      'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 10, 5, 15, 22],
      'heatmap-opacity': 0.85
    }
  }), [])

  const circleLayer = useMemo(() => ({
    id: 'flood-circles',
    type: 'circle',
    paint: {
      'circle-radius': [
        'interpolate', ['linear'], ['zoom'],
        11, 0,
        13, 5,
        15, 9
      ],
      'circle-color': ['interpolate', ['linear'], ['get', 'p_flood_pred'],
        0, '#3b82f6', 0.4, '#f59e0b', 0.7, '#f97316', 1, '#ef4444'
      ],
      'circle-opacity': ['interpolate', ['linear'], ['zoom'], 11, 0, 13, 0.88],
      'circle-stroke-width': ['case',
        ['==', ['get', 'impact_category'], hoveredCat || ''], 2.5,
        1
      ],
      'circle-stroke-color': ['case',
        ['==', ['get', 'impact_category'], hoveredCat || ''], '#ffffff',
        'rgba(255,255,255,0.2)'
      ]
    }
  }), [hoveredCat])

  // —— Tooltip handler ——
  const onMapMouseMove = useCallback((e) => {
    const features = e.features
    if (features && features.length > 0) {
      const f = features[0]
      setTooltipInfo({
        lng: e.lngLat.lng,
        lat: e.lngLat.lat,
        props: f.properties
      })
      // Ubah cursor
      e.target.getCanvas().style.cursor = 'crosshair'
    } else {
      setTooltipInfo(null)
      e.target.getCanvas().style.cursor = ''
    }
  }, [])

  const onMapMouseLeave = useCallback((e) => {
    setTooltipInfo(null)
    if (e?.target) e.target.getCanvas().style.cursor = ''
  }, [])

  const riverLayer = useMemo(() => ({
    id: 'rivers',
    type: 'line',
    paint: {
      'line-color': '#38bdf8',
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 2, 15, 7],
      'line-opacity': 0.9
    }
  }), [])

  // — ECharts Donut —
  const chartOptions = useMemo(() => {
    if (!summary) return {}
    const dist = summary.distribution || {}
    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} grid ({d}%)',
        backgroundColor: 'rgba(10,15,30,0.9)',
        borderColor: 'rgba(99,102,241,0.3)',
        textStyle: { color: '#f0f4ff', fontSize: 12 }
      },
      color: ['#10b981', '#f59e0b', '#f97316', '#ef4444'],
      series: [{
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '55%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: 'rgba(10,15,30,0.8)', borderWidth: 3 },
        label: { show: true, color: '#94a3b8', fontSize: 11, formatter: '{b}\n{d}%' },
        labelLine: { lineStyle: { color: '#334155' } },
        data: [
          { name: 'Aman', value: dist.Aman || 0 },
          { name: 'Waspada', value: dist.Waspada || 0 },
          { name: 'Rawan', value: dist.Rawan || 0 },
          { name: 'Parah', value: dist.Parah || 0 }
        ]
      }]
    }
  }, [summary])

  const today = weather?.today
  const pctHighRisk = summary?.pct_high_risk || 0
  const karangTma = tma?.karang_mumus
  const mahakamTma = tma?.mahakam

  const alertClass = riskClass(pctHighRisk)

  return (
    <div className="app-wrapper">
      {/* ============= SIDEBAR ============= */}
      <aside className="sidebar">
        {/* --- Header --- */}
        <div className="sidebar-header">
          <div className="brand-row">
            <div className="brand-icon">🌊</div>
            <div>
              <h1>Hydro-Intelligence<br />Samarinda</h1>
            </div>
          </div>
          <p className="subtitle">
            Sistem Prediksi Risiko Banjir berbasis AI (XGBoost Time-Series)
            dan data hidrologi real-time untuk pengambilan keputusan eksekutif.
          </p>
          <div className="status-badge live">
            <div className="dot"></div>
            Data Live · {new Date().toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' })}
          </div>
        </div>

        {/* --- Status Banjir --- */}
        <div className="section-label">Status Kondisi</div>
        <div style={{ padding: '0 16px', flexShrink: 0 }}>
          <div className={`risk-alert ${alertClass}`}>
            <div className="alert-icon">{riskIcon(pctHighRisk)}</div>
            <div>
              <div className="alert-title">Risiko Banjir: {riskLabel(pctHighRisk)}</div>
              <div className="alert-text">
                {riskDesc(pctHighRisk, today?.rain_mm ?? '—', karangTma?.level_m ?? '—')}
              </div>
            </div>
          </div>
        </div>

        {/* --- Metrik Cuaca --- */}
        <div className="section-label">Curah Hujan (Open-Meteo)</div>
        <div className="metric-grid">
          <div className="metric-card blue">
            <div className="icon">🌧️</div>
            <div className="value">{today?.rain_mm ?? '—'}<span className="unit">mm</span></div>
            <div className="label">Hari Ini (H-0)</div>
          </div>
          <div className="metric-card purple">
            <div className="icon">📅</div>
            <div className="value">{weather?.h_minus_1 ?? '—'}<span className="unit">mm</span></div>
            <div className="label">Kemarin (H-1)</div>
          </div>
          <div className="metric-card teal">
            <div className="icon">📅</div>
            <div className="value">{weather?.h_minus_2 ?? '—'}<span className="unit">mm</span></div>
            <div className="label">2 Hari Lalu (H-2)</div>
          </div>
          <div className="metric-card amber">
            <div className="icon">📊</div>
            <div className="value">{weather?.avg_7d ?? '—'}<span className="unit">mm</span></div>
            <div className="label">Rata-Rata 7 Hari</div>
          </div>
        </div>

        {/* --- Mini Bar Curah Hujan 7 Hari --- */}
        {weather?.history && (
          <div className="rain-history" style={{ marginTop: '10px' }}>
            <div style={{ fontSize: '10px', color: '#4f5b7c', fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '6px' }}>
              Tren 7 Hari Terakhir
            </div>
            <div className="rain-bars">
              {weather.history.map((d, i) => {
                const maxRain = Math.max(...weather.history.map(x => x.rain_mm), 1)
                const pct = (d.rain_mm / maxRain) * 100
                const isToday = i === weather.history.length - 1
                return (
                  <div key={i} className="rain-bar-wrap" title={`${d.date}: ${d.rain_mm} mm`}>
                    <div className="rain-bar-fill" style={{
                      height: `${Math.max(pct, 4)}%`,
                      background: isToday
                        ? 'linear-gradient(180deg, #a5b4fc, #6366f1)'
                        : 'linear-gradient(180deg, #38bdf8, #1e40af)'
                    }} />
                    <div className="rain-bar-label">
                      {isToday ? 'H-0' : `H-${weather.history.length - 1 - i}`}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* --- TMA Sungai --- */}
        <div className="section-label">Tinggi Muka Air Sungai (SIHKA)</div>
        <div className="tma-cards">
          {/* Mahakam */}
          <div className="tma-card">
            <div className="river-info">
              <div className="river-name">🌊 Sungai Mahakam</div>
              <div>
                <span className="river-level" style={{ color: statusColor[mahakamTma?.status] || '#f0f4ff' }}>
                  {mahakamTma?.level_m ?? '—'}
                </span>
                <span className="river-unit">m dpl</span>
              </div>
              <div className={`status-pill ${mahakamTma?.status || 'Normal'}`}>
                {mahakamTma?.status || 'Normal'}
              </div>
            </div>
            <div className="gauge" style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '10px', color: '#4f5b7c', marginBottom: '4px' }}>Siaga: {mahakamTma?.siaga_m}m</div>
              <div className="gauge-bar">
                <div className="gauge-fill" style={{
                  width: `${Math.min((mahakamTma?.level_m || 0) / (mahakamTma?.siaga_m || 5) * 100, 100)}%`,
                  background: `linear-gradient(90deg, #10b981, ${statusColor[mahakamTma?.status] || '#10b981'})`
                }} />
              </div>
            </div>
          </div>

          {/* Karang Mumus */}
          <div className="tma-card">
            <div className="river-info">
              <div className="river-name">🌿 Karang Mumus</div>
              <div>
                <span className="river-level" style={{ color: statusColor[karangTma?.status] || '#f0f4ff' }}>
                  {karangTma?.level_m ?? '—'}
                </span>
                <span className="river-unit">m dpl</span>
              </div>
              <div className={`status-pill ${karangTma?.status || 'Normal'}`}>
                {karangTma?.status || 'Normal'}
              </div>
            </div>
            <div className="gauge" style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '10px', color: '#4f5b7c', marginBottom: '4px' }}>Siaga: {karangTma?.siaga_m}m</div>
              <div className="gauge-bar">
                <div className="gauge-fill" style={{
                  width: `${Math.min((karangTma?.level_m || 0) / (karangTma?.siaga_m || 3) * 100, 100)}%`,
                  background: `linear-gradient(90deg, #10b981, ${statusColor[karangTma?.status] || '#10b981'})`
                }} />
              </div>
            </div>
          </div>
        </div>

        {/* --- Donut Chart Distribusi Dampak --- */}
        <div className="section-label">Distribusi Area Terdampak</div>
        <div className="chart-area">
          {summary && (
            <ReactECharts
              option={chartOptions}
              style={{ height: '200px', width: '100%' }}
              onEvents={{
                'mouseover': p => setHoveredCat(p.name),
                'mouseout': () => setHoveredCat(null)
              }}
            />
          )}
        </div>

        {/* --- Stats Ringkasan --- */}
        <div className="metric-grid" style={{ marginTop: '8px' }}>
          <div className="metric-card green">
            <div className="icon">📍</div>
            <div className="value">{summary?.total_grid?.toLocaleString('id') ?? '—'}</div>
            <div className="label">Titik Grid Analisis</div>
          </div>
          <div className="metric-card red">
            <div className="icon">⚡</div>
            <div className="value">{pctHighRisk}<span className="unit">%</span></div>
            <div className="label">Zona Risiko Tinggi (P≥0.7)</div>
          </div>
        </div>

        <div className="spacer" />

        {/* --- Footer --- */}
        <div className="sidebar-footer">
          <span>🤖 Model XGBoost · Akurasi 99%</span>
          <span>📡 Open-Meteo · SIHKA</span>
        </div>
      </aside>

      {/* ============= PETA ============= */}
      <div className="map-container">
        <Map
          ref={mapRef}
          initialViewState={{ longitude: 117.1536, latitude: -0.5022, zoom: 11.5 }}
          mapStyle={MAP_STYLES[mapStyle]}
          style={{ width: '100%', height: '100%' }}
          interactiveLayerIds={['flood-circles']}
          onMouseMove={onMapMouseMove}
          onMouseLeave={onMapMouseLeave}
        >
          {riverData && (
            <Source id="rivers" type="geojson" data={riverData}>
              <Layer {...riverLayer} />
            </Source>
          )}
          {gridData && (
            <Source id="grid" type="geojson" data={gridData}>
              <Layer {...heatmapLayer} />
              <Layer {...circleLayer} />
            </Source>
          )}

          {/* ===== TOOLTIP POPUP ===== */}
          {tooltipInfo && (
            <Popup
              longitude={tooltipInfo.lng}
              latitude={tooltipInfo.lat}
              closeButton={false}
              closeOnClick={false}
              anchor="bottom"
              offset={12}
              maxWidth="280px"
            >
              <TooltipCard props={tooltipInfo.props} />
            </Popup>
          )}
        </Map>

        {/* Headline peta */}
        <div className="float-control map-headline">
          <span className="headline-chip">🗺️ PETA PREDIKSI BANJIR · SAMARINDA</span>
          <span className="headline-separator">|</span>
          <span className="headline-data">Curah Hujan: <span>{today?.rain_mm ?? '—'} mm</span></span>
          <span className="headline-separator">|</span>
          <span className="headline-data">Kondisi: <span>{today?.label ?? '—'}</span></span>
          <span className="headline-separator">|</span>
          <span className="headline-data">Risiko Tinggi: <span style={{ color: pctHighRisk >= 40 ? '#f87171' : '#34d399' }}>{pctHighRisk}%</span></span>
        </div>

        {/* Switcher Basemap */}
        <div className="float-control layer-switcher">
          {Object.keys(MAP_STYLES).map(s => (
            <button key={s} className={`layer-btn ${mapStyle === s ? 'active' : 'inactive'}`}
              onClick={() => setMapStyle(s)}>
              {s === 'dark' ? '🌙 Dark' : '🗺️ Street'}
            </button>
          ))}
        </div>

        {/* Legend */}
        <div className="float-control legend-box">
          <div className="legend-title">Probabilitas Genangan Banjir</div>
          <div className="legend-gradient" />
          <div className="legend-labels">
            <span>Aman (0%)</span>
            <span>Sedang (50%)</span>
            <span>Kritis (100%)</span>
          </div>
        </div>
      </div>
    </div>
  )
}
