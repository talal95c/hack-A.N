import service from './index'
import mockScenarios from '../mocks/scenarios.json'

let localScenarios = [...mockScenarios.data]

export const listScenarios = async () => {
  try {
    return await service.get('/api/scenarios')
  } catch (error) {
    return { success: true, data: localScenarios }
  }
}

export const getScenario = async (id) => {
  try {
    return await service.get(`/api/scenarios/${id}`)
  } catch (error) {
    const found = localScenarios.find(s => s.id === id)
    return { success: !!found, data: found || null }
  }
}

export const reviewScenario = async (id, comments = '') => {
  try {
    return await service.post(`/api/scenarios/${id}/review`, { comments })
  } catch (error) {
    const s = localScenarios.find(x => x.id === id)
    if (s) s.status = 'reviewed'
    return { success: true, status: 'reviewed' }
  }
}

export const publishScenario = async (id) => {
  try {
    return await service.post(`/api/scenarios/${id}/publish`)
  } catch (error) {
    const s = localScenarios.find(x => x.id === id)
    // Enforce GEMINI.md §4 rule in mock fallback if not reviewed
    if (s && s.status !== 'reviewed' && s.status !== 'published') {
      const err = new Error('Le scénario doit être revu avant d\'être publié (HTTP 409)')
      err.response = { status: 409, data: { message: 'Must review before publishing' } }
      throw err
    }
    if (s) s.status = 'published'
    return { success: true, status: 'published' }
  }
}
