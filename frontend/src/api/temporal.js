import service from './index'
import mockTemporal from '../mocks/temporal.json'
import mockComparison from '../mocks/comparison.json'
import mockBacktesting from '../mocks/backtesting.json'
import mockUsers from '../mocks/users.json'

// --- Temporal ---
export const getTemporalRounds = async (scenarioId) => {
  try {
    return await service.get(`/api/temporal/scenario/${scenarioId}/rounds`)
  } catch (error) {
    return mockTemporal
  }
}

// --- Comparison ---
export const compareScenarios = async (ids = []) => {
  try {
    return await service.get('/api/comparison/runs', { params: { ids: ids.join(',') } })
  } catch (error) {
    return mockComparison
  }
}

// --- Backtesting ---
export const getBacktestingRuns = async () => {
  try {
    return await service.get('/api/backtesting/runs')
  } catch (error) {
    return mockBacktesting
  }
}

// --- Admin Users ---
let localUsers = [...mockUsers.users]

export const getUsers = async () => {
  try {
    return await service.get('/api/admin/users')
  } catch (error) {
    return { success: true, users: localUsers }
  }
}

export const updateUserRole = async (userId, newRole) => {
  try {
    return await service.put(`/api/admin/users/${userId}/role`, { role: newRole })
  } catch (error) {
    const u = localUsers.find(x => x.id === userId)
    if (u) u.role = newRole
    return { success: true, user: u }
  }
}
