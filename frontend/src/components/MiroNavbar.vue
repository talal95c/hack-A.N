<template>
  <header class="miro-navbar" role="banner">
    <div class="nav-brand" @click="$router.push('/')">
      <span class="logo-icon">⚖️</span>
      <span class="brand-name">MIROPOLIS</span>
      <span class="brand-tag">PARLEMENT & PROSPECTIVE</span>
    </div>

    <nav class="nav-menu" role="navigation" aria-label="Menu principal">
      <router-link to="/" class="nav-item" active-class="active" exact-active-class="active">{{ $t('nav.home') }}</router-link>
      <router-link to="/scenarios" class="nav-item" active-class="active">{{ $t('nav.scenarios') }}</router-link>
      <router-link to="/comparison" class="nav-item" active-class="active">
        {{ $t('nav.comparison') }}
        <span v-if="compCount > 0" class="badge-count">{{ compCount }}</span>
      </router-link>
      <router-link to="/backtesting" class="nav-item" active-class="active">{{ $t('nav.backtesting') }}</router-link>
      <router-link v-if="authStore.userRole === 'admin'" to="/admin" class="nav-item" active-class="active">{{ $t('nav.admin') }}</router-link>
    </nav>

    <div class="nav-right">
      <LanguageSwitcher />
      
      <!-- User / Auth -->
      <div v-if="authStore.isAuthenticated" class="user-pill" @click="$router.push('/admin')">
        <span class="user-avatar">🏛️</span>
        <div class="user-details">
          <span class="user-name">{{ authStore.user?.name || 'Député' }}</span>
          <span class="user-role">{{ authStore.userRole }}</span>
        </div>
      </div>
      <button v-else class="login-btn" @click="$router.push('/login')">
        Connexion Espace Député
      </button>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../store/auth'
import { useSimulationStore } from '../store/simulation'
import LanguageSwitcher from './LanguageSwitcher.vue'

const authStore = useAuthStore()
const simStore = useSimulationStore()

const compCount = computed(() => simStore.comparisonList.length)
</script>

<style scoped>
.miro-navbar {
  height: 64px;
  background: #000;
  color: #FFF;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  border-bottom: 1px solid #222;
  position: sticky;
  top: 0;
  z-index: 1000;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.logo-icon {
  font-size: 20px;
}

.brand-name {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 1px;
}

.brand-tag {
  background: #FF4500;
  color: #FFF;
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 2px;
}

.nav-menu {
  display: flex;
  gap: 8px;
}

.nav-item {
  color: #BBB;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 6px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.nav-item:hover {
  color: #FFF;
  background: rgba(255,255,255,0.08);
}

.nav-item.active {
  color: #FFF;
  background: rgba(255,255,255,0.15);
}

.badge-count {
  background: #FF4500;
  color: #FFF;
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 10px;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #1A1A1A;
  border: 1px solid #333;
  padding: 6px 12px;
  border-radius: 20px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.user-pill:hover {
  border-color: #FF4500;
}

.user-avatar {
  font-size: 16px;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
}

.user-role {
  font-size: 10px;
  color: #FF4500;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
}

.login-btn {
  background: #FFF;
  color: #000;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
</style>
