<template>
  <div class="comparison-dashboard">
    <div class="dash-header">
      <div class="header-titles">
        <h2>{{ $t('comparison.title') }}</h2>
        <p class="subtitle">{{ $t('comparison.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <button v-if="comparisonIds.length > 0" class="clear-btn" @click="clearAll">
          × {{ $t('comparison.clearBtn') }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span>Analyse comparative en cours...</span>
    </div>

    <div v-else-if="comparisonData.length === 0" class="empty-comparison">
      <div class="empty-box">
        <span class="empty-icon">⚖️</span>
        <h3>{{ $t('comparison.noSelection') }}</h3>
        <p>{{ $t('comparison.selectHint') }}</p>
        <button class="go-lib-btn" @click="$router.push('/scenarios')">
          Ouvrir la Bibliothèque des Scénarios
        </button>
      </div>
    </div>

    <div v-else class="comparison-content">
      <!-- Side by Side Summary Cards -->
      <div class="summary-grid" :style="{ gridTemplateColumns: `repeat(${comparisonData.length}, 1fr)` }">
        <div v-for="item in comparisonData" :key="item.id" class="comp-card">
          <div class="card-head">
            <span class="tag">SCÉNARIO COMPARÉ</span>
            <button class="remove-comp" @click="removeComparison(item.id)">×</button>
          </div>
          <h3 class="title">{{ item.title }}</h3>
          
          <div class="net-metric">
            <span class="l">IMPACT NET MOYEN</span>
            <span class="v">{{ item.net_impact_mean }} €/mois</span>
            <span class="ci" v-if="item.confidence_interval">
              IC 95% : [{{ item.confidence_interval[0] }}, {{ item.confidence_interval[1] }}]
            </span>
          </div>

          <div class="distribution-bar">
            <div class="win" :style="{ width: item.winners_pct + '%' }" :title="`Gagnants: ${item.winners_pct}%`"></div>
            <div class="neu" :style="{ width: item.neutral_pct + '%' }" :title="`Neutres: ${item.neutral_pct}%`"></div>
            <div class="lose" :style="{ width: item.losers_pct + '%' }" :title="`Perdants: ${item.losers_pct}%`"></div>
          </div>
          <div class="dist-labels">
            <span>🟢 Gagnants ({{ item.winners_pct }}%)</span>
            <span>⚪ Neutres ({{ item.neutral_pct }}%)</span>
            <span>🔴 Perdants ({{ item.losers_pct }}%)</span>
          </div>
        </div>
      </div>

      <!-- Archetype Divergence Section (With Confidence Bars) -->
      <div class="divergence-section">
        <h3>📊 {{ $t('comparison.divergenceChart') }}</h3>
        <p class="section-hint">Impact estimé par archétype socio-économique avec fourchettes d'incertitude.</p>
        
        <div class="archetypes-table">
          <table>
            <thead>
              <tr>
                <th>Archétype Démographique</th>
                <th v-for="item in comparisonData" :key="item.id">{{ item.title }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(arch, idx) in allArchetypeNames" :key="arch">
                <td class="arch-name-cell">👤 <strong>{{ arch }}</strong></td>
                <td v-for="item in comparisonData" :key="item.id">
                  <div class="arch-impact-cell">
                    <span class="delta-val" :class="getDeltaClass(getArchData(item, idx)?.delta)">
                      {{ getArchData(item, idx)?.delta || '0.00 €' }}
                    </span>
                    <div v-if="getArchData(item, idx)?.ci" class="ci-range">
                      IC: [{{ getArchData(item, idx).ci[0] }}€ .. {{ getArchData(item, idx).ci[1] }}€]
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Side by Side Maps -->
      <div class="maps-section">
        <h3>🗺️ {{ $t('comparison.sideBySide') }}</h3>
        <div class="maps-grid" :style="{ gridTemplateColumns: `repeat(${comparisonData.length}, 1fr)` }">
          <div v-for="item in comparisonData" :key="item.id" class="map-col">
            <h4 class="col-title">{{ item.title }}</h4>
            <FranceMap :simulationId="item.id" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useSimulationStore } from '../store/simulation'
import { compareScenarios } from '../api/comparison'
import FranceMap from './FranceMap.vue'

const simulationStore = useSimulationStore()
const loading = ref(false)
const comparisonData = ref([])

const comparisonIds = computed(() => simulationStore.comparisonList)

const loadComparisons = async () => {
  if (comparisonIds.value.length === 0) {
    comparisonData.value = []
    return
  }
  loading.value = true
  const res = await compareScenarios(comparisonIds.value)
  comparisonData.value = res?.data || []
  loading.value = false
}

const allArchetypeNames = computed(() => {
  if (comparisonData.value.length === 0) return []
  const names = new Set()
  comparisonData.value.forEach(item => {
    item.archetypes?.forEach(a => names.add(a.name))
  })
  return Array.from(names)
})

const getArchData = (item, idx) => {
  if (!item.archetypes) return null
  return item.archetypes[idx] || item.archetypes[0]
}

const getDeltaClass = (deltaStr) => {
  if (!deltaStr) return 'neu'
  if (deltaStr.startsWith('+')) return 'pos'
  if (deltaStr.startsWith('-')) return 'neg'
  return 'neu'
}

const removeComparison = (id) => {
  simulationStore.toggleComparison(id)
}

const clearAll = () => {
  simulationStore.clearComparison()
}

watch(comparisonIds, loadComparisons, { deep: true })

onMounted(() => {
  // If list is empty, default to comparing 2 items for demonstration if standalone
  if (simulationStore.comparisonList.length === 0) {
    simulationStore.toggleComparison('sim_logement_apl_2026')
    simulationStore.toggleComparison('sim_transition_energ_taxe')
  } else {
    loadComparisons()
  }
})
</script>

<style scoped>
.comparison-dashboard {
  padding: 32px 40px;
  background: #FFF;
  min-height: 100vh;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.dash-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 32px;
}

.header-titles h2 {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px 0;
}

.subtitle {
  color: #666;
  margin: 0;
  font-size: 15px;
}

.clear-btn {
  background: #F5F5F5;
  border: 1px solid #DDD;
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.empty-comparison {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 500px;
  background: #FAFAFA;
  border: 1px dashed #DDD;
  border-radius: 8px;
}

.empty-box {
  text-align: center;
  max-width: 440px;
}

.empty-icon {
  font-size: 56px;
  display: block;
  margin-bottom: 16px;
}

.go-lib-btn {
  background: #000;
  color: #FFF;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-weight: 600;
  margin-top: 20px;
  cursor: pointer;
}

.summary-grid {
  display: grid;
  gap: 24px;
  margin-bottom: 40px;
}

.comp-card {
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  padding: 24px;
  background: #FAFAFA;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.tag {
  font-size: 10px;
  font-weight: 700;
  background: #000;
  color: #FFF;
  padding: 2px 6px;
  border-radius: 2px;
}

.remove-comp {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #888;
}

.comp-card .title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 16px 0;
}

.net-metric {
  margin-bottom: 20px;
}

.l {
  font-size: 10px;
  color: #888;
  display: block;
}

.v {
  font-family: 'JetBrains Mono', monospace;
  font-size: 24px;
  font-weight: 700;
  color: #000;
}

.ci {
  display: block;
  font-size: 11px;
  color: #666;
  font-family: 'JetBrains Mono', monospace;
}

.distribution-bar {
  display: flex;
  height: 10px;
  border-radius: 5px;
  overflow: hidden;
  margin-bottom: 8px;
}

.win { background: #4CAF50; }
.neu { background: #E0E0E0; }
.lose { background: #F44336; }

.dist-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #666;
}

.divergence-section, .maps-section {
  margin-bottom: 48px;
}

.divergence-section h3, .maps-section h3 {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 8px 0;
}

.section-hint {
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
}

.archetypes-table {
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  overflow: hidden;
}

.archetypes-table table {
  width: 100%;
  border-collapse: collapse;
}

.archetypes-table th, .archetypes-table td {
  padding: 16px;
  border-bottom: 1px solid #EAEAEA;
  text-align: left;
}

.archetypes-table th {
  background: #F5F5F5;
  font-weight: 700;
  font-size: 13px;
}

.arch-name-cell {
  font-size: 14px;
}

.delta-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 16px;
  font-weight: 700;
}

.delta-val.pos { color: #2E7D32; }
.delta-val.neg { color: #D32F2F; }

.ci-range {
  font-size: 11px;
  color: #888;
  font-family: 'JetBrains Mono', monospace;
}

.maps-grid {
  display: grid;
  gap: 24px;
}

.map-col {
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  padding: 16px;
}

.col-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 16px 0;
}
</style>
