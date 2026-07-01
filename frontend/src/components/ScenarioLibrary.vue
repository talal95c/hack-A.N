<template>
  <div class="scenario-library">
    <!-- Header -->
    <div class="library-header">
      <div class="header-left">
        <h2>{{ $t('scenarios.title') }}</h2>
        <p class="subtitle">{{ $t('scenarios.subtitle') }}</p>
      </div>
      <div class="header-right">
        <button class="create-btn" @click="$router.push('/process/new')">
          + {{ $t('scenarios.createNew') }}
        </button>
      </div>
    </div>

    <!-- Filters Bar -->
    <div class="filters-bar">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input 
          v-model="searchQuery" 
          type="text" 
          :placeholder="$t('scenarios.searchPlaceholder')" 
        />
      </div>

      <div class="status-tabs">
        <button 
          v-for="tab in ['all', 'draft', 'reviewed', 'published']" 
          :key="tab"
          class="tab-btn"
          :class="{ active: currentTab === tab }"
          @click="currentTab = tab"
        >
          {{ { all: $t('scenarios.filterAll'), draft: $t('scenarios.filterDraft'), reviewed: $t('scenarios.filterReviewed'), published: $t('scenarios.filterPublished') }[tab] }}
        </button>
      </div>
    </div>

    <!-- Scenarios Grid -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span>Chargement de la bibliothèque législative...</span>
    </div>

    <div v-else-if="filteredScenarios.length === 0" class="empty-state">
      <p>Aucun scénario ne correspond aux critères sélectionnés.</p>
    </div>

    <div v-else class="scenarios-grid">
      <div 
        v-for="scenario in filteredScenarios" 
        :key="scenario.id"
        class="scenario-card"
        :class="`status-${scenario.status}`"
      >
        <div class="card-top">
          <span class="bill-num">{{ scenario.bill_number }}</span>
          <span class="status-badge" :class="scenario.status">
            {{ getStatusLabel(scenario.status) }}
          </span>
        </div>

        <h3 class="scenario-title" @click="openScenario(scenario)">{{ scenario.title }}</h3>
        <p class="scenario-author">Par {{ scenario.author }} — {{ scenario.date }}</p>
        <p class="scenario-summary">{{ scenario.summary }}</p>

        <div class="tags-row">
          <span v-for="tag in scenario.tags" :key="tag" class="tag">{{ tag }}</span>
        </div>

        <div class="card-metrics">
          <div class="metric">
            <span class="m-label">Impact Net Démographique</span>
            <span class="m-val">{{ scenario.archetype_impact_net }}</span>
          </div>
          <div class="metric">
            <span class="m-label">Couverture Cartographique</span>
            <span class="m-val">{{ scenario.region_count }} régions</span>
          </div>
        </div>

        <div class="card-actions">
          <button class="btn-primary" @click="openScenario(scenario)">
            {{ $t('scenarios.openBtn') }}
          </button>
          <button 
            class="btn-secondary" 
            :class="{ 'in-compare': isInComparison(scenario.id) }"
            @click="toggleCompare(scenario.id)"
          >
            {{ isInComparison(scenario.id) ? '✓ En comparaison' : $t('scenarios.compareBtn') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { listScenarios } from '../api/scenarios'
import { useSimulationStore } from '../store/simulation'

const router = useRouter()
const { t } = useI18n()
const simulationStore = useSimulationStore()

const scenarios = ref([])
const loading = ref(true)
const searchQuery = ref('')
const currentTab = ref('all')

const fetchScenarios = async () => {
  loading.value = true
  const res = await listScenarios()
  scenarios.value = res?.data || []
  loading.value = false
}

const filteredScenarios = computed(() => {
  return scenarios.value.filter(s => {
    const matchesTab = currentTab.value === 'all' || s.status === currentTab.value
    const matchesQuery = !searchQuery.value || 
      s.title.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      s.author.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      s.tags.some(tag => tag.toLowerCase().includes(searchQuery.value.toLowerCase()))
    return matchesTab && matchesQuery
  })
})

const getStatusLabel = (status) => {
  switch (status) {
    case 'draft': return t('scenarios.statusDraft')
    case 'reviewed': return t('scenarios.statusReviewed')
    case 'published': return t('scenarios.statusPublished')
    default: return status
  }
}

const openScenario = (scenario) => {
  simulationStore.setCurrentScenario(scenario.id)
  router.push(`/scenario-detail/${scenario.id}`)
}

const toggleCompare = (id) => {
  simulationStore.toggleComparison(id)
}

const isInComparison = (id) => {
  return simulationStore.comparisonList.includes(id)
}

onMounted(fetchScenarios)
</script>

<style scoped>
.scenario-library {
  padding: 32px 40px;
  background: #FFF;
  min-height: 100vh;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.library-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 32px;
}

.library-header h2 {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px 0;
}

.subtitle {
  color: #666;
  margin: 0;
  font-size: 15px;
}

.create-btn {
  background: #FF4500;
  color: #FFF;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.create-btn:hover {
  background: #E03E00;
}

.filters-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
  background: #FAFAFA;
  padding: 16px 20px;
  border: 1px solid #EAEAEA;
  border-radius: 8px;
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  background: #FFF;
  border: 1px solid #DDD;
  border-radius: 6px;
  padding: 8px 12px;
}

.search-box input {
  border: none;
  outline: none;
  width: 100%;
  margin-left: 8px;
  font-family: inherit;
  font-size: 14px;
}

.status-tabs {
  display: flex;
  gap: 6px;
}

.tab-btn {
  background: transparent;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #666;
  cursor: pointer;
}

.tab-btn.active {
  background: #000;
  color: #FFF;
}

.scenarios-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 24px;
}

.scenario-card {
  background: #FFF;
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.scenario-card:hover {
  border-color: #BBB;
  box-shadow: 0 8px 24px rgba(0,0,0,0.05);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.bill-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 700;
  color: #888;
}

.status-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 12px;
  text-transform: uppercase;
}

.status-badge.draft { background: #F5F5F5; color: #666; }
.status-badge.reviewed { background: #E3F2FD; color: #1565C0; }
.status-badge.published { background: #E8F5E9; color: #2E7D32; }

.scenario-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 8px 0;
  cursor: pointer;
}

.scenario-title:hover {
  color: #FF4500;
}

.scenario-author {
  font-size: 12px;
  color: #888;
  margin: 0 0 12px 0;
}

.scenario-summary {
  font-size: 13px;
  color: #555;
  line-height: 1.5;
  margin: 0 0 16px 0;
  flex: 1;
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}

.tag {
  background: #F5F5F5;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: #444;
}

.card-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  background: #FAFAFA;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
  border: 1px solid #F0F0F0;
}

.m-label {
  font-size: 10px;
  color: #888;
  display: block;
}

.m-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 700;
  color: #000;
}

.card-actions {
  display: flex;
  gap: 10px;
}

.btn-primary {
  flex: 1;
  background: #000;
  color: #FFF;
  border: none;
  padding: 10px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.btn-secondary {
  flex: 1;
  background: #FFF;
  color: #000;
  border: 1px solid #000;
  padding: 10px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.btn-secondary.in-compare {
  background: #E8F5E9;
  border-color: #2E7D32;
  color: #2E7D32;
}
</style>
