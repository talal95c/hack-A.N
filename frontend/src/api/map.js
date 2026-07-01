import service from './index'
import mockMapData from '../mocks/mapData.json'

export const getMapData = async (simulationId, granularity = 'region') => {
  try {
    return await service.get(`/api/simulation/${simulationId}/map-data`, {
      params: { granularity }
    })
  } catch (error) {
    console.warn(`[Mock API] getMapData fallback for ${simulationId}`)
    return mockMapData
  }
}

export const buildMapData = async (simulationId) => {
  try {
    return await service.post(`/api/simulation/${simulationId}/map-data/build`)
  } catch (error) {
    console.warn(`[Mock API] buildMapData fallback for ${simulationId}`)
    return {
      success: true,
      data: mockMapData
    }
  }
}
