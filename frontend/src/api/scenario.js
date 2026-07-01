import service, { requestWithRetry } from './index'

/**
 * Lancer la génération du scénario tendanciel
 * @param {Object} data - { simulation_id, force_regenerate? }
 */
export const generateScenario = (data) => {
  return requestWithRetry(() => service.post('/api/scenario/generate', data), 3, 1000)
}

/**
 * Obtenir le statut de génération du scénario tendanciel
 * @param {Object|string} data - { task_id } ou { simulation_id } ou taskId
 */
export const getScenarioStatus = (data) => {
  const payload = typeof data === 'string' ? { task_id: data } : data
  return service.post('/api/scenario/generate/status', payload)
}

/**
 * Obtenir le scénario tendanciel par son ID
 * @param {string} scenarioId
 */
export const getScenario = (scenarioId) => {
  return service.get(`/api/scenario/${scenarioId}`)
}

/**
 * Obtenir le dernier scénario généré pour une simulation
 * @param {string} simulationId
 */
export const getScenarioBySimulation = (simulationId) => {
  return service.get(`/api/scenario/by-simulation/${simulationId}`)
}
