<template>
  <div class="scenario-panel-container">
    <div class="scenario-content-max">
      <!-- Architectural Top Header -->
      <header class="scenario-header">
        <div class="header-main">
          <div class="cad-badge">
            <span>|← PROJECTION TEMPORELLE & SIMULATION DE VOTE →|</span>
          </div>
          <h2 class="scenario-title">Projection dans le temps & Perspectives</h2>
        </div>
        <div class="header-meta">
          <span class="meta-label">IDENTIFIANT SCÉNARIO</span>
          <span class="meta-id" :class="{ 'id-active': scenarioId }">
            {{ scenarioId ? scenarioId : 'NON GÉNÉRÉ' }}
          </span>
        </div>
      </header>

      <!-- Mandatory Scientific Disclaimer Callout -->
      <div class="scientific-disclaimer" role="note">
        <div class="disclaimer-indicator"></div>
        <div class="disclaimer-text">
          <strong>Avertissement méthodologique :</strong> Estimation qualitative générée par IA, ne reflète pas la position officielle des groupes parlementaires ni une prédiction fiable de vote réel.
        </div>
      </div>

      <!-- STATE 1: IDLE / EMPTY STATE -->
      <div v-if="status === 'idle'" class="scenario-state-card empty-card">
        <div class="card-corner corner-tl">+</div>
        <div class="card-corner corner-tr">+</div>
        <div class="card-corner corner-bl">+</div>
        <div class="card-corner corner-br">+</div>

        <div class="empty-graphic">
          <div class="wireframe-circle">
            <div class="inner-pulse"></div>
          </div>
        </div>

        <h3 class="empty-title">Aucune projection temporelle active</h3>
        <p class="empty-desc">
          Lancez le moteur de projection exploratoire pour analyser l'évolution tendancielle de la proposition de loi dans le temps, repérer les points de bascule chronologiques et simuler le décompte pondéré sur les 577 sièges de l'hémicycle.
        </p>

        <button 
          class="btn-architectural-launch" 
          :disabled="!simulationId" 
          @click="launchGeneration"
        >
          <span>Générer la projection temporelle</span>
          <span class="arrow-icon">→</span>
        </button>
      </div>

      <!-- STATE 2: GENERATING STATE -->
      <div v-else-if="status === 'generating'" class="scenario-state-card loading-card">
        <div class="loading-spinner-box">
          <span class="spinner-ring"></span>
        </div>
        <h3 class="loading-title">Modélisation tendancielle en cours...</h3>
        <p class="loading-subtitle">
          Analyse des interactions parlementaires et agrégation pondérée des sièges
        </p>

        <div class="progress-bar-container">
          <div class="progress-bar-fill" :style="{ width: `${progress || 15}%` }"></div>
        </div>
        <span class="progress-label">{{ progress ? `${progress}%` : 'Calcul en cours...' }}</span>
      </div>

      <!-- STATE 3: FAILED STATE -->
      <div v-else-if="status === 'failed'" class="scenario-state-card error-card">
        <div class="error-badge">ERREUR DE CALCUL</div>
        <h3 class="error-title">Échec de la génération exploratoire</h3>
        <p class="error-desc">{{ errorMessage || 'Une erreur inattendue est survenue lors de la simulation.' }}</p>
        <button class="btn-architectural-retry" @click="launchGeneration">
          <span>Relancer la simulation</span>
        </button>
      </div>

      <!-- STATE 4: COMPLETED STATE -->
      <div v-else-if="status === 'completed'" class="scenario-results">
        <!-- Simulated Vote Section (Weighted by 577 real seats) -->
        <div v-if="voteOutcome" class="vote-outcome-card">
          <div class="vote-card-header">
            <div class="vote-title-group">
              <span class="section-tag">DÉCOMPTE PONDÉRÉ (577 SIÈGES)</span>
              <h3 class="vote-title">Résultat du vote simulé</h3>
            </div>
            <div class="outcome-badge" :class="getOutcomeClass(voteOutcome.outcome)">
              {{ voteOutcomeLabel }}
            </div>
          </div>

          <!-- Proportional Visual Bar -->
          <div class="vote-proportional-bar">
            <div 
              class="bar-segment segment-support" 
              :style="{ width: `${(voteOutcome.support_seats / (voteOutcome.total_seats || 577)) * 100}%` }"
              :title="`Pour: ${voteOutcome.support_seats} sièges`"
            ></div>
            <div 
              class="bar-segment segment-oppose" 
              :style="{ width: `${(voteOutcome.oppose_seats / (voteOutcome.total_seats || 577)) * 100}%` }"
              :title="`Contre: ${voteOutcome.oppose_seats} sièges`"
            ></div>
            <div 
              class="bar-segment segment-abstain" 
              :style="{ width: `${(voteOutcome.abstain_seats / (voteOutcome.total_seats || 577)) * 100}%` }"
              :title="`Abstention: ${voteOutcome.abstain_seats} sièges`"
            ></div>
            <div 
              class="bar-segment segment-undecided" 
              :style="{ width: `${(voteOutcome.undecided_seats / (voteOutcome.total_seats || 577)) * 100}%` }"
              :title="`Indécis: ${voteOutcome.undecided_seats} sièges`"
            ></div>
          </div>

          <!-- Vote Legend Metrics -->
          <div class="vote-metrics-grid">
            <div class="metric-box box-support">
              <span class="metric-val">{{ voteOutcome.support_seats }}</span>
              <span class="metric-lbl">Pour</span>
            </div>
            <div class="metric-box box-oppose">
              <span class="metric-val">{{ voteOutcome.oppose_seats }}</span>
              <span class="metric-lbl">Contre</span>
            </div>
            <div class="metric-box box-abstain">
              <span class="metric-val">{{ voteOutcome.abstain_seats }}</span>
              <span class="metric-lbl">Abstention</span>
            </div>
            <div class="metric-box box-undecided">
              <span class="metric-val">{{ voteOutcome.undecided_seats }}</span>
              <span class="metric-lbl">Indécis</span>
            </div>
          </div>

          <!-- Parliamentary Groups Breakdown -->
          <div class="groups-breakdown">
            <h4 class="breakdown-title">Positionnement par groupe parlementaire</h4>
            <div class="groups-grid">
              <div 
                v-for="g in voteOutcome.by_group" 
                :key="g.group_name" 
                class="group-item-card"
              >
                <div class="group-info">
                  <span class="group-name">{{ g.group_name }}</span>
                  <span class="group-seats">{{ g.seats }} sièges</span>
                </div>
                <span class="group-pos-tag" :class="getPositionClass(g.position)">
                  {{ formatPosition(g.position) }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Analytical Sections (Observed state, trend trajectory, tipping points) -->
        <div class="scenario-sections-grid">
          <section 
            v-for="(section, idx) in sections" 
            :key="idx" 
            class="section-card"
          >
            <div class="section-card-header">
              <span class="section-index">PARTIE 0{{ idx + 1 }}</span>
              <h4 class="section-card-title">{{ section.title }}</h4>
            </div>
            <div class="section-card-body">
              <p class="section-text">{{ section.content }}</p>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { generateScenario, getScenarioStatus, getScenario, getScenarioBySimulation } from '../api/scenario'

const props = defineProps({
  simulationId: String
})
const emit = defineEmits(['add-log', 'update-status'])

const scenarioId = ref(null)
const status = ref('idle') // idle | generating | completed | failed
const progress = ref(0)
const errorMessage = ref('')
const sections = ref([])
const voteOutcome = ref(null)
let pollTimer = null

const voteOutcomeLabel = computed(() => {
  if (!voteOutcome.value) return ''
  const map = { adopted: 'Adopté (simulé)', rejected: 'Rejeté (simulé)', uncertain: 'Résultat incertain' }
  return map[voteOutcome.value.outcome] || voteOutcome.value.outcome
})

const getOutcomeClass = (outcome) => {
  if (outcome === 'adopted') return 'badge-adopted'
  if (outcome === 'rejected') return 'badge-rejected'
  return 'badge-uncertain'
}

const formatPosition = (pos) => {
  const map = { support: 'Pour', oppose: 'Contre', abstain: 'Abstention', undecided: 'Indécis' }
  return map[pos] || pos
}

const getPositionClass = (pos) => {
  if (pos === 'support') return 'tag-support'
  if (pos === 'oppose') return 'tag-oppose'
  if (pos === 'abstain') return 'tag-abstain'
  return 'tag-undecided'
}

const log = (msg) => emit('add-log', msg)

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const loadScenarioContent = async (id) => {
  const res = await getScenario(id)
  if (res.success && res.data) {
    sections.value = res.data.sections || []
    voteOutcome.value = res.data.vote_outcome || null
    status.value = res.data.status === 'completed' ? 'completed' : status.value
    emit('update-status', status.value)
  }
}

const pollStatus = (taskId) => {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const res = await getScenarioStatus({ task_id: taskId, simulation_id: props.simulationId })
      if (!res.success) return
      const data = res.data
      progress.value = data.progress || 0
      if (data.status === 'completed' || data.already_completed) {
        stopPolling()
        status.value = 'completed'
        scenarioId.value = data.scenario_id || scenarioId.value
        if (scenarioId.value) await loadScenarioContent(scenarioId.value)
        log('Scénario tendanciel généré')
        emit('update-status', 'completed')
      } else if (data.status === 'failed') {
        stopPolling()
        status.value = 'failed'
        errorMessage.value = data.error || ''
        emit('update-status', 'failed')
      }
    } catch (err) {
      log(`Erreur de polling du scénario: ${err.message}`)
    }
  }, 2000)
}

const launchGeneration = async () => {
  if (!props.simulationId) return
  status.value = 'generating'
  log('Lancement de la génération du scénario tendanciel')
  try {
    const res = await generateScenario({ simulation_id: props.simulationId })
    if (res.success && res.data) {
      scenarioId.value = res.data.scenario_id
      if (res.data.already_generated) {
        status.value = 'completed'
        await loadScenarioContent(scenarioId.value)
      } else {
        pollStatus(res.data.task_id)
      }
    } else {
      status.value = 'failed'
      errorMessage.value = res.error || ''
    }
  } catch (err) {
    status.value = 'failed'
    errorMessage.value = err.message
  }
}

const checkExisting = async () => {
  if (!props.simulationId) return
  try {
    const res = await getScenarioBySimulation(props.simulationId)
    if (res.success && res.has_scenario && res.data) {
      scenarioId.value = res.data.scenario_id
      status.value = res.data.status === 'completed' ? 'completed' : 'idle'
      if (status.value === 'completed') {
        sections.value = res.data.sections || []
        voteOutcome.value = res.data.vote_outcome || null
      }
    }
  } catch (err) {
    // 404/has_scenario:false -> pas encore de scénario, état "idle" par défaut
  }
}

watch(() => props.simulationId, (newId) => {
  if (newId) checkExisting()
}, { immediate: true })

onMounted(() => {
  if (props.simulationId) checkExisting()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
/* Container & Layout */
.scenario-panel-container {
  height: 100%;
  overflow-y: auto;
  padding: 32px 36px 64px;
  background-color: #FFFFFF;
  color: #0F172A;
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
}

.scenario-content-max {
  max-width: 1080px;
  margin: 0 auto;
}

/* Header Section */
.scenario-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  border-bottom: 1px solid #E2E8F0;
  padding-bottom: 20px;
  margin-bottom: 24px;
}

.cad-badge {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  color: #64748B;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  padding: 4px 12px;
  border-radius: 9999px;
  margin-bottom: 12px;
}

.scenario-title {
  font-size: 26px;
  font-weight: 700;
  color: #0F172A;
  letter-spacing: -0.5px;
  margin: 0;
}

.header-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.meta-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #94A3B8;
  letter-spacing: 0.5px;
}

.meta-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #94A3B8;
  background: #F1F5F9;
  padding: 4px 10px;
  border-radius: 6px;
}

.meta-id.id-active {
  color: #0F172A;
  background: #E2E8F0;
}

/* Mandatory Disclaimer */
.scientific-disclaimer {
  display: flex;
  align-items: stretch;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-left: 4px solid #0F172A;
  border-radius: 8px;
  padding: 14px 18px;
  margin-bottom: 36px;
}

.disclaimer-text {
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
}

/* State Cards (Idle, Loading, Error) */
.scenario-state-card {
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  padding: 56px 40px;
  text-align: center;
  background: #FFFFFF;
  position: relative;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.03);
  margin: 32px auto;
  max-width: 680px;
}

.card-corner {
  position: absolute;
  font-family: 'JetBrains Mono', monospace;
  color: #CBD5E1;
  font-size: 14px;
  line-height: 1;
}

.corner-tl { top: 12px; left: 14px; }
.corner-tr { top: 12px; right: 14px; }
.corner-bl { bottom: 12px; left: 14px; }
.corner-br { bottom: 12px; right: 14px; }

.empty-graphic {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.wireframe-circle {
  width: 64px;
  height: 64px;
  border: 1px dashed #94A3B8;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.inner-pulse {
  width: 24px;
  height: 24px;
  background: #0F172A;
  border-radius: 50%;
  animation: pulseIdle 2.5s infinite ease-in-out;
}

@keyframes pulseIdle {
  0%, 100% { transform: scale(0.9); opacity: 0.8; }
  50% { transform: scale(1.15); opacity: 1; }
}

.empty-title, .loading-title, .error-title {
  font-size: 20px;
  font-weight: 700;
  color: #0F172A;
  margin: 0 0 12px;
}

.empty-desc, .loading-subtitle, .error-desc {
  font-size: 14.5px;
  line-height: 1.6;
  color: #64748B;
  max-width: 500px;
  margin: 0 auto 32px;
}

/* Action Buttons */
.btn-architectural-launch, .btn-architectural-retry {
  background: #000000;
  color: #FFFFFF;
  border: none;
  padding: 15px 34px;
  border-radius: 9999px;
  font-size: 14.5px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.btn-architectural-launch:hover:not(:disabled),
.btn-architectural-retry:hover {
  background: #1E293B;
  transform: translateY(-2px);
  box-shadow: 0 15px 32px rgba(0, 0, 0, 0.25);
}

.btn-architectural-launch:disabled {
  background: #94A3B8;
  cursor: not-allowed;
  box-shadow: none;
}

.arrow-icon {
  transition: transform 0.25s ease;
}

.btn-architectural-launch:hover:not(:disabled) .arrow-icon {
  transform: translateX(4px);
}

/* Loading Spinner & Progress */
.loading-spinner-box {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.spinner-ring {
  width: 48px;
  height: 48px;
  border: 3px solid #E2E8F0;
  border-top-color: #0F172A;
  border-radius: 50%;
  animation: spin 1s infinite linear;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-bar-container {
  width: 100%;
  max-width: 380px;
  height: 6px;
  background: #F1F5F9;
  border-radius: 3px;
  margin: 24px auto 12px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: #0F172A;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.progress-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #64748B;
}

/* Error State */
.error-badge {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  color: #DC2626;
  background: #FEF2F2;
  border: 1px solid #FCA5A5;
  padding: 4px 12px;
  border-radius: 9999px;
  margin-bottom: 16px;
}

/* Results Area */
.vote-outcome-card {
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  padding: 32px;
  background: #FFFFFF;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.03);
  margin-bottom: 36px;
}

.vote-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.section-tag {
  display: block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #64748B;
  margin-bottom: 4px;
}

.vote-title {
  font-size: 20px;
  font-weight: 700;
  color: #0F172A;
  margin: 0;
}

.outcome-badge {
  font-size: 13.5px;
  font-weight: 700;
  padding: 8px 18px;
  border-radius: 9999px;
}

.badge-adopted { background: #DCFCE7; color: #166534; border: 1px solid #86EFAC; }
.badge-rejected { background: #FEF2F2; color: #991B1B; border: 1px solid #FCA5A5; }
.badge-uncertain { background: #FEF9C3; color: #854D0E; border: 1px solid #FDE047; }

/* Proportional Visual Bar */
.vote-proportional-bar {
  display: flex;
  height: 16px;
  width: 100%;
  border-radius: 9999px;
  overflow: hidden;
  background: #F1F5F9;
  margin-bottom: 24px;
}

.bar-segment { transition: width 0.6s ease; }
.segment-support { background: #22C55E; }
.segment-oppose { background: #EF4444; }
.segment-abstain { background: #94A3B8; }
.segment-undecided { background: #E2E8F0; }

/* Metrics Grid */
.vote-metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.metric-box {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #E2E8F0;
  text-align: center;
}

.metric-val {
  display: block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 4px;
}

.metric-lbl {
  font-size: 12.5px;
  font-weight: 600;
}

.box-support { background: #F0FDF4; border-color: #BBF7D0; color: #15803D; }
.box-oppose { background: #FEF2F2; border-color: #FECACA; color: #B91C1C; }
.box-abstain { background: #F8FAFC; border-color: #E2E8F0; color: #475569; }
.box-undecided { background: #FFFFFF; border-color: #E2E8F0; color: #64748B; }

/* Groups Breakdown */
.groups-breakdown {
  border-top: 1px solid #F1F5F9;
  padding-top: 24px;
}

.breakdown-title {
  font-size: 14px;
  font-weight: 700;
  color: #334155;
  margin: 0 0 16px;
}

.groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.group-item-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  background: #FAFAFA;
}

.group-info {
  display: flex;
  flex-direction: column;
}

.group-name {
  font-weight: 700;
  font-size: 13.5px;
  color: #0F172A;
}

.group-seats {
  font-size: 11.5px;
  color: #64748B;
}

.group-pos-tag {
  font-size: 11.5px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
}

.tag-support { background: #DCFCE7; color: #166534; }
.tag-oppose { background: #FEF2F2; color: #991B1B; }
.tag-abstain { background: #F1F5F9; color: #475569; }
.tag-undecided { background: #E2E8F0; color: #64748B; }

/* Analytical Sections Grid */
.scenario-sections-grid {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-card {
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  padding: 32px;
  background: #FFFFFF;
  box-shadow: 0 4px 15px rgba(15, 23, 42, 0.02);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.section-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
}

.section-card-header {
  margin-bottom: 16px;
  border-bottom: 1px solid #F1F5F9;
  padding-bottom: 12px;
}

.section-index {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  color: #94A3B8;
}

.section-card-title {
  font-size: 18px;
  font-weight: 700;
  color: #0F172A;
  margin: 4px 0 0;
}

.section-text {
  font-size: 14.5px;
  line-height: 1.7;
  color: #334155;
  white-space: pre-wrap;
  margin: 0;
}

@media (max-width: 768px) {
  .scenario-panel-container { padding: 20px 16px 48px; }
  .vote-metrics-grid { grid-template-columns: repeat(2, 1fr); }
  .scenario-header { flex-direction: column; align-items: flex-start; gap: 12px; }
  .header-meta { align-items: flex-start; }
}
</style>
