<template>
  <div class="scenario-detail-view">
    <MiroNavbar />

    <div class="workbench-header">
      <div class="header-main">
        <div class="breadcrumb">
          <router-link to="/scenarios" class="back-link">← Bibliothèque des Scénarios</router-link>
          <span class="sep">/</span>
          <span class="current-id">{{ scenarioId }}</span>
        </div>
        <div class="title-row">
          <h1>{{ scenario?.title || 'Analyse Prospective : Réforme APL 2026' }}</h1>
          <span class="status-badge" :class="scenarioStatus">{{ scenarioStatus }}</span>
        </div>
        <p class="author-meta">Créé par {{ scenario?.author || 'Dr. Hélène Moreau' }} — Modèle de microsimulation OpenFisca couplé Oasis</p>
      </div>

      <div class="header-actions">
        <button class="btn-wizard" @click="launchWizard">
          ⚙️ Constructeur Multi-Agents (Oasis)
        </button>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="workbench-tabs">
      <button 
        class="w-tab" 
        :class="{ active: activeTab === 'map' }"
        @click="activeTab = 'map'"
      >
        🗺️ Carte Territoriale (13 Régions)
      </button>
      <button 
        class="w-tab" 
        :class="{ active: activeTab === 'timeline' }"
        @click="activeTab = 'timeline'"
      >
        📈 Trajectoire & Adhésion Temporelle
      </button>
      <button 
        class="w-tab" 
        :class="{ active: activeTab === 'review' }"
        @click="activeTab = 'review'"
      >
        📋 Revue Méthodologique & Publication
      </button>
    </div>

    <!-- Tab Content -->
    <main class="workbench-body">
      <div v-show="activeTab === 'map'" class="tab-pane">
        <FranceMap :simulationId="scenarioId" />
      </div>

      <div v-show="activeTab === 'timeline'" class="tab-pane">
        <ProspectiveTimeline :scenarioId="scenarioId" />
      </div>

      <div v-show="activeTab === 'review'" class="tab-pane">
        <PublishReviewPanel 
          :scenarioId="scenarioId" 
          :initialStatus="scenarioStatus"
          @status-changed="handleStatusChange"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getScenario } from '../api/scenarios'
import MiroNavbar from '../components/MiroNavbar.vue'
import FranceMap from '../components/FranceMap.vue'
import ProspectiveTimeline from '../components/ProspectiveTimeline.vue'
import PublishReviewPanel from '../components/PublishReviewPanel.vue'

const props = defineProps({
  scenarioId: {
    type: String,
    required: true
  }
})

const router = useRouter()
const scenario = ref(null)
const scenarioStatus = ref('draft')
const activeTab = ref('map')

const loadScenarioInfo = async () => {
  const res = await getScenario(props.scenarioId)
  if (res?.success && res.data) {
    scenario.value = res.data
    scenarioStatus.value = res.data.status || 'draft'
  }
}

const handleStatusChange = (newStatus) => {
  scenarioStatus.value = newStatus
  if (scenario.value) {
    scenario.value.status = newStatus
  }
}

const launchWizard = () => {
  router.push(`/simulation/${props.scenarioId}`)
}

onMounted(loadScenarioInfo)
</script>

<style scoped>
.scenario-detail-view {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #F9F9F9;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.workbench-header {
  background: #FFF;
  border-bottom: 1px solid #EAEAEA;
  padding: 24px 40px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.breadcrumb {
  font-size: 13px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.back-link {
  color: #666;
  text-decoration: none;
  font-weight: 600;
}

.back-link:hover {
  color: #000;
}

.sep {
  color: #CCC;
}

.current-id {
  font-family: 'JetBrains Mono', monospace;
  color: #888;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 6px;
}

.title-row h1 {
  font-size: 26px;
  font-weight: 700;
  margin: 0;
}

.status-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 4px;
}

.status-badge.draft { background: #EEE; color: #555; }
.status-badge.reviewed { background: #E3F2FD; color: #1565C0; }
.status-badge.published { background: #E8F5E9; color: #2E7D32; }

.author-meta {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.btn-wizard {
  background: #000;
  color: #FFF;
  border: none;
  padding: 12px 20px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}

.btn-wizard:hover {
  background: #222;
}

.workbench-tabs {
  display: flex;
  gap: 8px;
  background: #FAFAFA;
  padding: 0 40px;
  border-bottom: 1px solid #EAEAEA;
}

.w-tab {
  background: none;
  border: none;
  padding: 16px 20px;
  font-size: 14px;
  font-weight: 600;
  color: #666;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.w-tab:hover {
  color: #000;
}

.w-tab.active {
  color: #FF4500;
  border-bottom-color: #FF4500;
}

.workbench-body {
  flex: 1;
  padding: 32px 40px;
}

.tab-pane {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
