import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || null)
  const user = ref(JSON.parse(localStorage.getItem('current_user') || 'null'))

  const isAuthenticated = computed(() => !!token.value)
  const userRole = computed(() => user.value?.role || 'deputy') // admin | analyst | deputy | viewer

  function setAuth(newToken, newUser) {
    token.value = newToken
    user.value = newUser
    if (newToken) {
      localStorage.setItem('access_token', newToken)
    } else {
      localStorage.removeItem('access_token')
    }
    if (newUser) {
      localStorage.setItem('current_user', JSON.stringify(newUser))
    } else {
      localStorage.removeItem('current_user')
    }
  }

  function logout() {
    setAuth(null, null)
  }

  // Initial user setup for standalone dev if none exists
  if (!user.value) {
    user.value = {
      id: 'usr_default_01',
      name: 'Dr. Hélène Moreau',
      email: 'h.moreau@assemblee-nationale.fr',
      role: 'admin',
      group: 'EPR'
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    userRole,
    setAuth,
    logout
  }
})
