<template>
  <div class="scenario-panel">
    <div class="scenario-header">
      <h3>Projection dans le temps & Perspectives</h3>
      <span class="scenario-id">ID: {{ scenarioId || 'non généré' }}</span>
    </div>

    <p class="disclaimer">
      Estimation qualitative générée par IA, ne reflète pas la position officielle des groupes
      parlementaires ni une prédiction fiable de vote réel.
    </p>

    <div v-if="status === 'idle'" class="scenario-empty">
      <p>Aucune projection temporelle générée pour cette simulation.</p>
      <button class="btn-generate" :disabled="!simulationId" @click="launchGeneration">
        Générer la projection temporelle
      </button>
    </div>

    <div v-else-if="status === 'generating'" class="scenario-loading">
      <span class="dot pulsing"></span>
      Génération en cours{{ progress ? ` (${progress}%)` : '' }}...
    </div>

    <div v-else-if="status === 'failed'" class="scenario-error">
      <p>Échec de la génération : {{ errorMessage || 'erreur inconnue' }}</p>
      <button class="btn-generate" @click="launchGeneration">Réessayer</button>
    </div>

    <div v-else-if="status === 'completed'" class="scenario-sections">
      <div v-if="voteOutcome" class="vote-outcome">
        <h4>Résultat du vote simulé (pondéré par sièges réels)</h4>
        <p>
          <strong>{{ voteOutcomeLabel }}</strong>
          — {{ voteOutcome.support_seats }} pour / {{ voteOutcome.oppose_seats }} contre
          / {{ voteOutcome.abstain_seats }} abstention(s)
          / {{ voteOutcome.undecided_seats }} indécis, sur {{ voteOutcome.total_seats }} sièges.
        </p>
        <ul class="vote-by-group">
          <li v-for="g in voteOutcome.by_group" :key="g.group_name">
            {{ g.group_name }} ({{ g.seats }} sièges) — {{ g.position }}
          </li>
        </ul>
      </div>
      <section v-for="(section, idx) in sections" :key="idx" class="scenario-section">
        <h4>{{ section.title }}</h4>
        <p>{{ section.content }}</p>
      </section>
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
.scenario-panel { padding: 16px; }
.scenario-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.scenario-id { font-size: 12px; color: #999; }
.disclaimer { font-size: 12px; color: #888; margin-bottom: 16px; }
.btn-generate { padding: 8px 16px; cursor: pointer; }
.scenario-section { margin-bottom: 16px; }
.vote-outcome { margin-bottom: 20px; padding: 12px; border: 1px solid #E0E0E0; border-radius: 6px; }
.vote-by-group { font-size: 13px; color: #555; margin-top: 8px; padding-left: 18px; }
.dot.pulsing { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #FF9800; animation: pulse 1s infinite; margin-right: 6px; }
@keyframes pulse { 50% { opacity: 0.4; } }
</style>
