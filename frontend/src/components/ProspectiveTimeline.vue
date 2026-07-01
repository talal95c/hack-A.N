<template>
  <div class="prospective-timeline">
    <div class="time-header">
      <div class="titles">
        <h2>{{ $t('timeline.title') }}</h2>
        <p class="subtitle">{{ $t('timeline.subtitle') }}</p>
      </div>
      <div class="mode-switch">
        <button 
          class="mode-btn" 
          :class="{ active: mode === 'trend' }"
          @click="mode = 'trend'"
        >
          📈 {{ $t('timeline.modeTrend') }}
        </button>
        <button 
          class="mode-btn" 
          :class="{ active: mode === 'retrospective' }"
          @click="mode = 'retrospective'"
        >
          🔄 {{ $t('timeline.modeRetrospective') }}
        </button>
      </div>
    </div>

    <!-- Timeline Slider -->
    <div class="slider-section" v-if="rounds.length > 0">
      <div class="slider-labels">
        <span class="l-num">Tour actuel : <strong>{{ currentRound?.month }}</strong></span>
        <span class="l-total">Total : {{ totalRounds }} Mois</span>
      </div>
      <input 
        type="range" 
        :min="0" 
        :max="rounds.length - 1" 
        v-model.number="selectedRoundIdx"
        class="time-slider"
      />
      <div class="ticks-row">
        <span 
          v-for="(r, idx) in rounds" 
          :key="r.round"
          class="tick"
          :class="{ active: idx === selectedRoundIdx }"
          @click="selectedRoundIdx = idx"
        >
          M+{{ r.round }}
        </span>
      </div>
    </div>

    <!-- Metrics Cards for Current Round -->
    <div class="round-metrics" v-if="currentRound">
      <div class="m-card">
        <span class="m-title">{{ $t('timeline.approvalRate') }}</span>
        <div class="m-val-row">
          <span class="num">{{ getApprovalValue(currentRound) }}%</span>
          <span class="trend pos">↗ Projections positives</span>
        </div>
        <div class="progress-bg">
          <div class="progress-fill" :style="{ width: getApprovalValue(currentRound) + '%' }"></div>
        </div>
      </div>

      <div class="m-card">
        <span class="m-title">{{ $t('timeline.socialTension') }}</span>
        <div class="m-val-row">
          <span class="num">{{ currentRound.social_tension }} / 100</span>
          <span class="trend" :class="currentRound.social_tension < 25 ? 'pos' : 'neg'">
            {{ currentRound.social_tension < 25 ? 'Apaisement' : 'Vigilance' }}
          </span>
        </div>
        <div class="progress-bg">
          <div class="progress-fill tension" :style="{ width: currentRound.social_tension + '%' }"></div>
        </div>
      </div>

      <div class="m-card">
        <span class="m-title">{{ $t('timeline.fiscalDeficit') }}</span>
        <div class="m-val-row">
          <span class="num">{{ currentRound.fiscal_deficit }} M€</span>
          <span class="trend neu">Cumul budgétaire</span>
        </div>
        <p class="m-note">Impact net sur les finances publiques en année pleine.</p>
      </div>
    </div>

    <!-- Comparative Trajectory Chart (SVG) -->
    <div class="trajectory-section" v-if="rounds.length > 0">
      <h3>📈 Trajectoires simulées d'opinion (Adhésion populaire en %)</h3>
      <div class="chart-box">
        <svg viewBox="0 0 800 240" class="traj-svg">
          <!-- Grid lines -->
          <line x1="60" y1="30" x2="760" y2="30" stroke="#EEE" />
          <line x1="60" y1="90" x2="760" y2="90" stroke="#EEE" />
          <line x1="60" y1="150" x2="760" y2="150" stroke="#EEE" />
          <line x1="60" y1="210" x2="760" y2="210" stroke="#EEE" />
          
          <text x="20" y="35" class="axis-l">80%</text>
          <text x="20" y="95" class="axis-l">70%</text>
          <text x="20" y="155" class="axis-l">60%</text>
          <text x="20" y="215" class="axis-l">50%</text>

          <!-- Polyline for Trend -->
          <polyline 
            :points="getPolylinePoints('trend_approval')" 
            fill="none" 
            stroke="#1E88E5" 
            stroke-width="3" 
          />
          <!-- Polyline for Retrospective candidate -->
          <polyline 
            v-if="mode === 'retrospective'"
            :points="getPolylinePoints('retrospective_approval')" 
            fill="none" 
            stroke="#FF5722" 
            stroke-width="3" 
            stroke-dasharray="6,4"
          />

          <!-- Dots for Current Round -->
          <circle 
            v-for="(r, idx) in rounds" 
            :key="idx"
            :cx="60 + idx * (700 / (rounds.length - 1))"
            :cy="210 - ((getApprovalValue(r) - 50) / 35) * 180"
            r="5"
            :fill="idx === selectedRoundIdx ? '#000' : '#1E88E5'"
            class="point-dot"
            @click="selectedRoundIdx = idx"
          />
        </svg>
        <div class="chart-legend">
          <span><span class="dot blue"></span> Trajectoire de référence</span>
          <span v-if="mode === 'retrospective'"><span class="dot orange"></span> Trajectoire rétrospective alternative</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getTemporalRounds } from '../api/temporal'

const props = defineProps({
  scenarioId: {
    type: String,
    default: 'sim_logement_apl_2026'
  }
})

const rounds = ref([])
const totalRounds = ref(12)
const selectedRoundIdx = ref(0)
const mode = ref('trend') // trend | retrospective

const currentRound = computed(() => {
  return rounds.value[selectedRoundIdx.value] || null
})

const loadRounds = async () => {
  const res = await getTemporalRounds(props.scenarioId)
  if (res?.data?.rounds) {
    rounds.value = res.data.rounds
    totalRounds.value = res.data.total_rounds || rounds.value.length
  }
}

const getApprovalValue = (r) => {
  if (mode.value === 'retrospective' && r.retrospective_approval) {
    return r.retrospective_approval
  }
  return r.trend_approval || r.approval_rate || 50
}

const getPolylinePoints = (field) => {
  if (rounds.value.length < 2) return ''
  const w = 700 / (rounds.value.length - 1)
  return rounds.value.map((r, idx) => {
    const x = 60 + idx * w
    const val = r[field] || r.approval_rate || 50
    const y = 210 - ((val - 50) / 35) * 180
    return `${x},${Math.max(20, Math.min(220, y))}`
  }).join(' ')
}

onMounted(loadRounds)
</script>

<style scoped>
.prospective-timeline {
  padding: 32px 40px;
  background: #FFF;
  min-height: 100vh;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.time-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 32px;
}

.titles h2 {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px 0;
}

.subtitle {
  color: #666;
  margin: 0;
  font-size: 15px;
}

.mode-switch {
  display: flex;
  background: #FAFAFA;
  border: 1px solid #EAEAEA;
  padding: 4px;
  border-radius: 6px;
  gap: 4px;
}

.mode-btn {
  background: transparent;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  color: #666;
  cursor: pointer;
}

.mode-btn.active {
  background: #000;
  color: #FFF;
}

.slider-section {
  background: #FAFAFA;
  border: 1px solid #EAEAEA;
  padding: 24px;
  border-radius: 8px;
  margin-bottom: 32px;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  margin-bottom: 12px;
}

.time-slider {
  width: 100%;
  accent-color: #FF4500;
  cursor: pointer;
}

.ticks-row {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
}

.tick {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #888;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.tick.active {
  background: #000;
  color: #FFF;
  font-weight: 700;
}

.round-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 40px;
}

.m-card {
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  padding: 24px;
}

.m-title {
  font-size: 12px;
  font-weight: 700;
  color: #888;
  display: block;
  margin-bottom: 12px;
}

.m-val-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 16px;
}

.num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 28px;
  font-weight: 700;
}

.trend {
  font-size: 11px;
  font-weight: 600;
}

.trend.pos { color: #2E7D32; }
.trend.neg { color: #D32F2F; }

.progress-bg {
  height: 8px;
  background: #EEE;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #1E88E5;
}

.progress-fill.tension { background: #FF5722; }

.trajectory-section {
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  padding: 24px;
}

.trajectory-section h3 {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 20px 0;
}

.traj-svg {
  width: 100%;
  max-height: 260px;
}

.axis-l {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  fill: #888;
}

.point-dot {
  cursor: pointer;
  transition: r 0.2s;
}

.point-dot:hover {
  r: 8;
}

.chart-legend {
  display: flex;
  gap: 24px;
  font-size: 12px;
  margin-top: 16px;
}

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 6px;
}

.dot.blue { background: #1E88E5; }
.dot.orange { background: #FF5722; }
</style>
