<template>
  <div class="france-map-container" aria-label="Carte territoriale d'impact de la réforme">
    <!-- Header Controls -->
    <div class="map-controls">
      <div class="controls-left">
        <h3 class="map-title">{{ $t('map.title') }}</h3>
        <div class="granularity-badge">
          <span class="dot active"></span>
          {{ mapData?.granularity === 'circonscription' ? $t('map.granularityCirco') : $t('map.granularityRegion') }}
        </div>
      </div>
      <div class="controls-right">
        <button 
          class="rgaa-toggle-btn"
          @click="showTable = !showTable"
          :aria-expanded="showTable"
          aria-controls="rgaa-table-view"
        >
          <span class="icon">📊</span>
          {{ showTable ? 'Voir la Carte graphique' : 'Tableau Accessible (RGAA)' }}
        </button>
      </div>
    </div>

    <!-- Empty State / Build Trigger -->
    <div v-if="!loading && (!mapData?.areas || mapData.areas.length === 0)" class="empty-map-state">
      <div class="empty-content">
        <span class="empty-icon">🗺️</span>
        <h4>{{ $t('map.buildMapPrompt') }}</h4>
        <p class="empty-desc">Les simulations démographiques régionales doivent être consolidées pour générer le calque cartographique.</p>
        <button 
          class="build-map-btn" 
          @click="triggerBuildMap" 
          :disabled="building"
        >
          <span v-if="building" class="spinner-sm"></span>
          {{ building ? $t('map.buildingMap') : $t('map.buildMapBtn') }}
        </button>
      </div>
    </div>

    <!-- Main Content Area -->
    <div v-else class="map-content-wrapper">
      <!-- RGAA Accessible Table Alternative -->
      <div v-if="showTable" id="rgaa-table-view" class="rgaa-table-container">
        <table class="accessible-table" role="grid">
          <caption>Impact territorial par région métropolitaine (Échelle -2 à +2 et calculs OpenFisca)</caption>
          <thead>
            <tr>
              <th scope="col">Code INSEE</th>
              <th scope="col">Région</th>
              <th scope="col">Score IA (Qualitatif)</th>
              <th scope="col">Calcul OpenFisca</th>
              <th scope="col">Archétypes Dominants</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="area in mapData.areas" :key="area.code">
              <td><code>{{ area.code }}</code></td>
              <td class="region-name">{{ area.name }}</td>
              <td>
                <span class="score-pill" :style="getScoreStyle(area.qualitative_score)">
                  {{ formatScore(area.qualitative_score) }}
                </span>
              </td>
              <td>
                <span v-if="area.openfisca_indicator?.available" class="fisca-badge success">
                  {{ area.openfisca_indicator.value > 0 ? '+' : '' }}{{ area.openfisca_indicator.value }} {{ area.openfisca_indicator.unit }}
                </span>
                <span v-else class="fisca-badge not-avail">
                  {{ $t('map.openfiscaNotAvailable') }}
                </span>
              </td>
              <td>
                <div class="archetypes-list">
                  <span v-for="arch in (area.top_archetypes || [])" :key="arch" class="arch-tag">{{ arch }}</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Graphical D3 Map & Detail Panel -->
      <div v-else class="map-interactive-view">
        <div class="d3-map-area" ref="mapSvgContainer">
          <svg viewBox="0 0 700 650" class="svg-map" role="img" aria-label="Carte des 13 régions de France métropolitaine">
            <!-- Render 13 Stylized Region Polygons -->
            <g class="regions-group">
              <g 
                v-for="region in regionCoordinates" 
                :key="region.code"
                class="region-node"
                :class="{ 'selected': selectedArea?.code === region.code }"
                :aria-label="`Région ${region.name}. Score IA : ${getAreaScore(region.code)}. Appuyez pour voir les détails.`"
                role="button"
                tabindex="0"
                @click="selectRegion(region.code)"
                @keydown.enter="selectRegion(region.code)"
                @keydown.space.prevent="selectRegion(region.code)"
              >
                <path 
                  :d="region.path" 
                  :fill="getRegionFill(region.code)"
                  :stroke="selectedArea?.code === region.code ? '#000000' : (isOpenFiscaAvailable(region.code) ? '#1565C0' : '#FFFFFF')"
                  :stroke-width="selectedArea?.code === region.code ? 3.5 : (isOpenFiscaAvailable(region.code) ? 2.5 : 1.5)"
                  :stroke-dasharray="isOpenFiscaAvailable(region.code) ? 'none' : 'none'"
                  class="region-path"
                />
                <!-- Region Name Label -->
                <text 
                  :x="region.labelX" 
                  :y="region.labelY" 
                  class="region-label"
                  text-anchor="middle"
                >
                  {{ region.shortName || region.name }}
                </text>
                <!-- OpenFisca Verified Indicator Dot -->
                <circle 
                  v-if="isOpenFiscaAvailable(region.code)"
                  :cx="region.labelX + 28" 
                  :cy="region.labelY - 12" 
                  r="6" 
                  fill="#1E88E5" 
                  stroke="#FFF" 
                  stroke-width="1.5"
                >
                  <title>Calcul OpenFisca vérifié</title>
                </circle>
              </g>
            </g>
          </svg>

          <!-- Permanent Qualitative Legend -->
          <div class="map-legend">
            <div class="legend-header">
              <span class="legend-title">{{ $t('map.legendScore') }}</span>
            </div>
            <div class="legend-scale">
              <div v-for="score in [-2, -1, 0, 1, 2]" :key="score" class="scale-item">
                <span class="color-box" :style="getScoreStyle(score)"></span>
                <span class="scale-num">{{ score > 0 ? `+${score}` : score }}</span>
              </div>
            </div>
            <div class="legend-badges-info">
              <div class="badge-row">
                <span class="dot-sample fisca"></span>
                <span>{{ $t('map.openfiscaAvailable') }} (Microsimulation)</span>
              </div>
              <div class="badge-row">
                <span class="dot-sample ai"></span>
                <span>Estimation exploratoire par agents IA</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Detail Panel -->
        <div class="region-detail-panel" v-if="selectedArea">
          <div class="detail-header">
            <div>
              <span class="insee-code">INSEE #{{ selectedArea.code }}</span>
              <h4 class="detail-title">{{ selectedArea.name }}</h4>
            </div>
            <button class="close-detail" @click="selectedArea = null" aria-label="Fermer le panneau">×</button>
          </div>

          <div class="detail-body">
            <!-- Qualitative IA Score -->
            <div class="score-card">
              <span class="card-label">IMPACT IA PROSPECTIF</span>
              <div class="score-display">
                <span class="big-score" :style="getScoreStyle(selectedArea.qualitative_score)">
                  {{ formatScore(selectedArea.qualitative_score) }}
                </span>
                <span class="score-text">{{ getScoreDescription(selectedArea.qualitative_score) }}</span>
              </div>
            </div>

            <!-- OpenFisca Indicator -->
            <div class="openfisca-card" :class="{ 'active': selectedArea.openfisca_indicator?.available }">
              <div class="card-header-row">
                <span class="fisca-logo">⚛️ OpenFisca</span>
                <span class="fisca-status">
                  {{ selectedArea.openfisca_indicator?.available ? 'CALCULÉ' : 'NON DISPONIBLE' }}
                </span>
              </div>
              
              <div v-if="selectedArea.openfisca_indicator?.available" class="fisca-value-box">
                <div class="val-num">
                  {{ selectedArea.openfisca_indicator.value > 0 ? '+' : '' }}{{ selectedArea.openfisca_indicator.value }}
                  <span class="val-unit">{{ selectedArea.openfisca_indicator.unit }}</span>
                </div>
                <p class="val-label">{{ selectedArea.openfisca_indicator.label }}</p>
              </div>
              <div v-else class="fisca-empty">
                <p>{{ $t('map.openfiscaInfo') }}</p>
              </div>
            </div>

            <!-- Dominant Archetypes -->
            <div class="archetypes-card" v-if="selectedArea.top_archetypes?.length">
              <span class="card-label">{{ $t('map.archetypesTop') }} ({{ selectedArea.archetype_count || 'N/A' }} profils)</span>
              <div class="arch-pills">
                <span v-for="arch in selectedArea.top_archetypes" :key="arch" class="arch-pill">
                  👤 {{ arch }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer Disclaimer -->
    <div class="map-footer">
      <span class="disclaimer-text">ℹ️ {{ $t('map.disclaimer') }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMapData, buildMapData } from '../api/map'

const props = defineProps({
  simulationId: {
    type: String,
    default: 'sim_logement_apl_2026'
  },
  granularity: {
    type: String,
    default: 'region'
  }
})

const { t } = useI18n()

const loading = ref(true)
const building = ref(false)
const mapData = ref(null)
const selectedArea = ref(null)
const showTable = ref(false)

// 13 Metropolitan Regions stylized vector coordinates (self-contained SVG paths)
const regionCoordinates = [
  { code: '32', name: 'Hauts-de-France', shortName: 'Hauts-de-France', path: 'M 320,30 L 400,20 L 440,70 L 410,130 L 330,120 Z', labelX: 375, labelY: 80 },
  { code: '28', name: 'Normandie', shortName: 'Normandie', path: 'M 180,100 L 320,100 L 330,120 L 290,170 L 190,160 Z', labelX: 255, labelY: 135 },
  { code: '11', name: 'Île-de-France', shortName: 'Île-de-France', path: 'M 330,120 L 410,130 L 400,190 L 320,180 Z', labelX: 365, labelY: 155 },
  { code: '44', name: 'Grand Est', shortName: 'Grand Est', path: 'M 410,70 L 560,80 L 580,180 L 470,220 L 400,190 L 410,130 Z', labelX: 485, labelY: 150 },
  { code: '53', name: 'Bretagne', shortName: 'Bretagne', path: 'M 50,140 L 180,130 L 190,210 L 80,220 Z', labelX: 120, labelY: 180 },
  { code: '52', name: 'Pays de la Loire', shortName: 'Pays de la Loire', path: 'M 180,160 L 280,160 L 270,250 L 160,240 Z', labelX: 220, labelY: 205 },
  { code: '24', name: 'Centre-Val de Loire', shortName: 'Centre-Val de Loire', path: 'M 280,160 L 390,170 L 380,260 L 270,250 Z', labelX: 330, labelY: 215 },
  { code: '27', name: 'Bourgogne-Franche-Comté', shortName: 'Bourgogne-Franche-Comté', path: 'M 390,170 L 490,190 L 510,290 L 390,280 Z', labelX: 445, labelY: 235 },
  { code: '75', name: 'Nouvelle-Aquitaine', shortName: 'Nouv. Aquitaine', path: 'M 160,240 L 280,240 L 310,380 L 240,480 L 140,430 Z', labelX: 225, labelY: 350 },
  { code: '84', name: 'Auvergne-Rhône-Alpes', shortName: 'Auvergne-Rhône-Alpes', path: 'M 360,270 L 510,280 L 530,410 L 370,410 Z', labelX: 445, labelY: 345 },
  { code: '76', name: 'Occitanie', shortName: 'Occitanie', path: 'M 240,430 L 370,410 L 410,530 L 270,550 Z', labelX: 330, labelY: 480 },
  { code: '93', name: "Provence-Alpes-Côte d'Azur", shortName: 'PACA', path: 'M 430,410 L 550,400 L 570,510 L 430,510 Z', labelX: 495, labelY: 460 },
  { code: '94', name: 'Corse', shortName: 'Corse', path: 'M 590,500 L 630,490 L 640,580 L 600,590 Z', labelX: 615, labelY: 545 }
]

const loadData = async () => {
  loading.value = true
  const res = await getMapData(props.simulationId, props.granularity)
  mapData.value = res?.data || res || { areas: [] }
  if (mapData.value.areas && mapData.value.areas.length > 0 && !selectedArea.value) {
    selectedArea.value = mapData.value.areas[0]
  }
  loading.value = false
}

const triggerBuildMap = async () => {
  building.value = true
  await buildMapData(props.simulationId)
  building.value = false
  await loadData()
}

const selectRegion = (code) => {
  const found = mapData.value?.areas?.find(a => a.code === code)
  if (found) {
    selectedArea.value = found
  }
}

const getAreaScore = (code) => {
  const found = mapData.value?.areas?.find(a => a.code === code)
  return found ? found.qualitative_score : 0
}

const isOpenFiscaAvailable = (code) => {
  const found = mapData.value?.areas?.find(a => a.code === code)
  return !!found?.openfisca_indicator?.available
}

const getRegionFill = (code) => {
  const score = getAreaScore(code)
  switch (score) {
    case -2: return '#D32F2F'
    case -1: return '#EF5350'
    case 1: return '#66BB6A'
    case 2: return '#2E7D32'
    default: return '#E0E0E0'
  }
}

const getScoreStyle = (score) => {
  switch (score) {
    case -2: return { backgroundColor: '#D32F2F', color: '#FFF' }
    case -1: return { backgroundColor: '#EF5350', color: '#FFF' }
    case 1: return { backgroundColor: '#66BB6A', color: '#FFF' }
    case 2: return { backgroundColor: '#2E7D32', color: '#FFF' }
    default: return { backgroundColor: '#9E9E9E', color: '#FFF' }
  }
}

const formatScore = (score) => {
  if (score > 0) return `+${score}`
  return `${score}`
}

const getScoreDescription = (score) => {
  switch (score) {
    case -2: return 'Impact très défavorable'
    case -1: return 'Défavorable modéré'
    case 1: return 'Favorable modéré'
    case 2: return 'Impact très favorable'
    default: return 'Neutre ou équilibré'
  }
}

watch(() => props.simulationId, loadData)
watch(() => props.granularity, loadData)

onMounted(loadData)
</script>

<style scoped>
.france-map-container {
  display: flex;
  flex-direction: column;
  background: #FFF;
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  overflow: hidden;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.map-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #EAEAEA;
  background: #FAFAFA;
}

.controls-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.map-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0;
  color: #000;
}

.granularity-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #000;
  color: #FFF;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 4px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #4CAF50;
}

.rgaa-toggle-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #FFF;
  border: 1px solid #000;
  color: #000;
  font-weight: 600;
  font-size: 12px;
  padding: 6px 14px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.rgaa-toggle-btn:hover {
  background: #000;
  color: #FFF;
}

.map-content-wrapper {
  min-height: 580px;
  display: flex;
  position: relative;
}

.map-interactive-view {
  display: flex;
  width: 100%;
}

.d3-map-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  padding: 20px;
  background: #FCFCFC;
}

.svg-map {
  width: 100%;
  max-height: 520px;
}

.region-node {
  cursor: pointer;
  outline: none;
  transition: transform 0.2s;
}

.region-node:hover .region-path,
.region-node:focus .region-path {
  filter: brightness(0.92);
  stroke: #000;
  stroke-width: 2.5;
}

.region-path {
  transition: fill 0.3s, stroke 0.2s, stroke-width 0.2s;
}

.region-label {
  font-size: 11px;
  font-weight: 700;
  fill: #111;
  pointer-events: none;
  text-shadow: 0 0 4px #FFF, 0 0 4px #FFF;
}

/* Legend */
.map-legend {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: #FFF;
  border: 1px solid #DDD;
  padding: 12px 16px;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}

.legend-title {
  font-size: 11px;
  font-weight: 700;
  display: block;
  margin-bottom: 8px;
  color: #444;
}

.legend-scale {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}

.scale-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.color-box {
  width: 28px;
  height: 14px;
  border-radius: 2px;
}

.scale-num {
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
}

.legend-badges-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 10px;
  color: #666;
  border-top: 1px dashed #EEE;
  padding-top: 8px;
}

.badge-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot-sample {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-sample.fisca { background: #1E88E5; }
.dot-sample.ai { background: #9E9E9E; }

/* Detail Panel */
.region-detail-panel {
  width: 320px;
  background: #FFF;
  border-left: 1px solid #EAEAEA;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: -4px 0 16px rgba(0,0,0,0.03);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid #EAEAEA;
  padding-bottom: 12px;
}

.insee-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #888;
  font-weight: 600;
}

.detail-title {
  font-size: 18px;
  font-weight: 700;
  margin: 4px 0 0 0;
}

.close-detail {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #888;
}

.score-card, .openfisca-card, .archetypes-card {
  border: 1px solid #EAEAEA;
  padding: 12px;
  border-radius: 6px;
  background: #FAFAFA;
}

.card-label {
  font-size: 10px;
  font-weight: 700;
  color: #888;
  display: block;
  margin-bottom: 8px;
}

.score-display {
  display: flex;
  align-items: center;
  gap: 12px;
}

.big-score {
  font-family: 'JetBrains Mono', monospace;
  font-size: 18px;
  font-weight: 700;
  padding: 6px 14px;
  border-radius: 4px;
}

.score-text {
  font-size: 13px;
  font-weight: 600;
}

.openfisca-card.active {
  border-color: #1E88E5;
  background: #E3F2FD;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.fisca-logo {
  font-weight: 700;
  font-size: 12px;
  color: #0D47A1;
}

.fisca-status {
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 2px;
  background: #FFF;
  color: #0D47A1;
}

.val-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 24px;
  font-weight: 700;
  color: #0D47A1;
}

.val-unit {
  font-size: 12px;
}

.val-label {
  font-size: 11px;
  color: #1565C0;
  margin: 4px 0 0 0;
}

.fisca-empty {
  font-size: 11px;
  color: #666;
  line-height: 1.4;
}

.arch-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.arch-pill {
  font-size: 11px;
  background: #FFF;
  border: 1px solid #DDD;
  padding: 4px 8px;
  border-radius: 12px;
}

/* Empty State */
.empty-map-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 500px;
  background: #FAFAFA;
}

.empty-content {
  text-align: center;
  max-width: 400px;
}

.empty-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.empty-desc {
  color: #666;
  font-size: 14px;
  margin-bottom: 24px;
  line-height: 1.5;
}

.build-map-btn {
  background: #000;
  color: #FFF;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

/* RGAA Accessible Table */
.rgaa-table-container {
  width: 100%;
  padding: 24px;
  overflow-x: auto;
}

.accessible-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.accessible-table th,
.accessible-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #EAEAEA;
  font-size: 13px;
}

.accessible-table th {
  background: #F5F5F5;
  font-weight: 700;
}

.score-pill {
  padding: 4px 10px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
}

.fisca-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
}

.fisca-badge.success { background: #E3F2FD; color: #1565C0; }
.fisca-badge.not-avail { color: #888; }

.archetypes-list {
  display: flex;
  gap: 6px;
}

.arch-tag {
  background: #EEE;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

/* Footer */
.map-footer {
  padding: 12px 24px;
  background: #F9F9F9;
  border-top: 1px solid #EAEAEA;
  font-size: 12px;
  color: #666;
}
</style>
