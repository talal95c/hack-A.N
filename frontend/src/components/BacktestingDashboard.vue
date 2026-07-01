<template>
  <div class="backtesting-dashboard">
    <div class="dash-header">
      <div class="titles">
        <h2>{{ $t('backtesting.title') }}</h2>
        <p class="subtitle">{{ $t('backtesting.subtitle') }}</p>
      </div>
      <div class="source-badge">
        <span>🏛️ Source vérifiée : data.gouv.fr/an-groupes</span>
      </div>
    </div>

    <!-- Top KPI Cards -->
    <div class="kpi-grid" v-if="metrics">
      <div class="kpi-card highlight">
        <span class="label">{{ $t('backtesting.overallAccuracy') }}</span>
        <span class="val">{{ metrics.overall_accuracy }}%</span>
        <span class="note">Concordance sur 48 lois historiques</span>
      </div>
      <div class="kpi-card">
        <span class="label">{{ $t('backtesting.seatsAnalyzed') }}</span>
        <span class="val">{{ metrics.total_seats_benchmarked }}</span>
        <span class="note">Sièges à l'Assemblée nationale</span>
      </div>
      <div class="kpi-card">
        <span class="label">Date de calibration</span>
        <span class="val">{{ metrics.last_calibration_date }}</span>
        <span class="note">Moteur Oasis v2.4</span>
      </div>
    </div>

    <!-- Parliamentary Groups Table -->
    <div class="table-section">
      <h3>🏛️ {{ $t('backtesting.groupBreakdown') }} (577 Sièges)</h3>
      <p class="table-hint">Précision de la modélisation du vote par groupe politique à l'Assemblée nationale.</p>

      <div class="table-box">
        <table>
          <thead>
            <tr>
              <th>Groupe Politique (AN)</th>
              <th>Sièges</th>
              <th>Taux d'Accord Simulé vs Réel</th>
              <th>Marge de Confidence</th>
              <th>Précision Visuelle</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="grp in groups" :key="grp.code">
              <td>
                <span class="grp-code">{{ grp.code }}</span>
                <span class="grp-name">{{ grp.name }}</span>
              </td>
              <td><span class="seats-pill">{{ grp.seats }}</span></td>
              <td class="acc-cell">{{ grp.simulated_agreement }}%</td>
              <td class="ci-cell">±{{ grp.confidence_margin }}%</td>
              <td class="bar-cell">
                <div class="acc-bar-bg">
                  <div class="acc-bar-fill" :style="{ width: grp.simulated_agreement + '%' }"></div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Bill Categories Breakdown -->
    <div class="categories-section" v-if="billTypes.length">
      <h3>📑 {{ $t('backtesting.billTypeBreakdown') }}</h3>
      <div class="cat-grid">
        <div v-for="cat in billTypes" :key="cat.category" class="cat-card">
          <span class="cat-title">{{ cat.category }}</span>
          <div class="cat-stat">
            <span class="num">{{ cat.accuracy }}%</span>
            <span class="sample">Évalué sur {{ cat.sample_size }} textes</span>
          </div>
          <div class="acc-bar-bg">
            <div class="acc-bar-fill cat" :style="{ width: cat.accuracy + '%' }"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getBacktestingRuns } from '../api/backtesting'

const metrics = ref(null)
const groups = ref([])
const billTypes = ref([])

const loadData = async () => {
  const res = await getBacktestingRuns()
  if (res?.success) {
    metrics.value = res.metrics
    groups.value = res.groups || []
    billTypes.value = res.bill_types || []
  }
}

onMounted(loadData)
</script>

<style scoped>
.backtesting-dashboard {
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

.source-badge {
  background: #F5F5F5;
  border: 1px solid #DDD;
  padding: 8px 14px;
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 40px;
}

.kpi-card {
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  padding: 24px;
  background: #FAFAFA;
}

.kpi-card.highlight {
  background: #000;
  color: #FFF;
  border-color: #000;
}

.kpi-card.highlight .label,
.kpi-card.highlight .note {
  color: #AAA;
}

.label {
  font-size: 12px;
  font-weight: 700;
  color: #888;
  display: block;
  margin-bottom: 8px;
}

.val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 32px;
  font-weight: 700;
  display: block;
  margin-bottom: 8px;
}

.note {
  font-size: 11px;
  color: #666;
}

.table-section, .categories-section {
  margin-bottom: 48px;
}

h3 {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 8px 0;
}

.table-hint {
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
}

.table-box {
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 14px 16px;
  border-bottom: 1px solid #EAEAEA;
  text-align: left;
}

th {
  background: #F5F5F5;
  font-weight: 700;
  font-size: 13px;
}

.grp-code {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  background: #EEE;
  padding: 2px 6px;
  border-radius: 4px;
  margin-right: 10px;
  font-size: 12px;
}

.grp-name {
  font-size: 14px;
}

.seats-pill {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 14px;
}

.acc-cell {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 15px;
  color: #2E7D32;
}

.ci-cell {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #888;
}

.acc-bar-bg {
  height: 8px;
  background: #EEE;
  border-radius: 4px;
  overflow: hidden;
  width: 140px;
}

.acc-bar-fill {
  height: 100%;
  background: #4CAF50;
}

.acc-bar-fill.cat {
  background: #FF4500;
}

.cat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  margin-top: 16px;
}

.cat-card {
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  padding: 20px;
}

.cat-title {
  font-size: 15px;
  font-weight: 700;
  display: block;
  margin-bottom: 12px;
}

.cat-stat {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}

.cat-stat .num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 24px;
  font-weight: 700;
}

.cat-stat .sample {
  font-size: 12px;
  color: #888;
}
</style>
