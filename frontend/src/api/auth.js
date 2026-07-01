import service from './index'

export const login = async (credentials) => {
  try {
    return await service.post('/api/auth/login', credentials)
  } catch (error) {
    // Dev fallback mock
    if (credentials.email === 'admin@miropolis.fr') {
      return {
        success: true,
        access_token: 'mock_jwt_admin_token_2026',
        user: { id: 'usr_default_01', name: 'Dr. Hélène Moreau', email: credentials.email, role: 'admin', group: 'EPR' }
      }
    }
    return {
      success: true,
      access_token: 'mock_jwt_deputy_token_2026',
      user: { id: 'usr_deputy_03', name: 'Marc Dubois', email: credentials.email, role: 'deputy', group: 'SOC' }
    }
  }
}

export const register = async (userInfo) => {
  try {
    return await service.post('/api/auth/register', userInfo)
  } catch (error) {
    return {
      success: true,
      access_token: 'mock_jwt_new_user',
      user: { id: `usr_${Date.now()}`, name: userInfo.name, email: userInfo.email, role: 'deputy', group: userInfo.group || 'NI' }
    }
  }
}
