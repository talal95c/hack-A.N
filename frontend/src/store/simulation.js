import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSimulationStore = defineStore('simulation', () => {
  const currentScenarioId = ref(null)
  const activeScenarios = ref([])
  const comparisonList = ref([]) // IDs for multi-law comparison A/B/N
  const mapDataCache = ref({}) // Cache for map data by scenario ID

  function setCurrentScenario(id) {
    currentScenarioId.value = id
  }

  function toggleComparison(id) {
    const index = comparisonList.value.indexOf(id)
    if (index > -1) {
      comparisonList.value.splice(index, 1)
    } else {
      if (comparisonList.value.length < 4) {
        comparisonList.value.push(id)
      }
    }
  }

  function clearComparison() {
    comparisonList.value = []
  }

  function cacheMapData(id, data) {
    mapDataCache.value[id] = data
  }

  return {
    currentScenarioId,
    activeScenarios,
    comparisonList,
    mapDataCache,
    setCurrentScenario,
    toggleComparison,
    clearComparison,
    cacheMapData
  }
})
