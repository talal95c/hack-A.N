<template>
  <div class="login-view">
    <MiroNavbar />
    
    <div class="auth-container">
      <div class="auth-box">
        <div class="brand-head">
          <span class="logo">⚖️</span>
          <h2>MIROPOLIS</h2>
          <p>Portail d'Accréditation Parlementaire & Législative</p>
        </div>

        <div class="auth-tabs">
          <button 
            class="tab" 
            :class="{ active: mode === 'login' }"
            @click="mode = 'login'"
          >
            Connexion
          </button>
          <button 
            class="tab" 
            :class="{ active: mode === 'register' }"
            @click="mode = 'register'"
          >
            Inscription
          </button>
        </div>

        <form @submit.prevent="handleSubmit" class="auth-form">
          <div v-if="mode === 'register'" class="form-field">
            <label>Nom complet / Titre</label>
            <input v-model="form.name" type="text" placeholder="Dr. Hélène Moreau (Députée)" required />
          </div>

          <div class="form-field">
            <label>Email institutionnel</label>
            <input v-model="form.email" type="email" placeholder="nom@assemblee-nationale.fr" required />
          </div>

          <div class="form-field">
            <label>Mot de passe / Clé API</label>
            <input v-model="form.password" type="password" placeholder="••••••••••••" required />
          </div>

          <div v-if="mode === 'register'" class="form-field">
            <label>Groupe Parlementaire / Affiliation</label>
            <select v-model="form.group">
              <option value="EPR">EPR - Ensemble pour la République</option>
              <option value="RN">RN - Rassemblement National</option>
              <option value="LFI-NFP">LFI-NFP - La France Insoumise</option>
              <option value="SOC">SOC - Socialistes et apparentés</option>
              <option value="DR">DR - Droite Républicaine</option>
              <option value="EcoS">EcoS - Écologiste et Social</option>
              <option value="Dem">Dem - Les Démocrates</option>
              <option value="NI">NI - Non Inscrits / Observateur externe</option>
            </select>
          </div>

          <div v-if="error" class="error-msg">{{ error }}</div>

          <button type="submit" class="submit-btn" :disabled="loading">
            <span v-if="loading" class="spinner-sm"></span>
            {{ mode === 'login' ? 'Accéder au Portail' : 'Demande d\'accréditation' }}
          </button>
        </form>

        <div class="quick-demo-accounts">
          <span class="hint-label">Comptes d'essai rapides (Dev) :</span>
          <div class="demo-btns">
            <button type="button" @click="quickLogin('admin@miropolis.fr')">Dr. Moreau (Admin)</button>
            <button type="button" @click="quickLogin('m.dubois@assemblee-nationale.fr')">M. Dubois (Député)</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { login, register } from '../api/auth'
import MiroNavbar from '../components/MiroNavbar.vue'

const router = useRouter()
const authStore = useAuthStore()

const mode = ref('login')
const loading = ref(false)
const error = ref('')

const form = ref({
  name: '',
  email: '',
  password: '',
  group: 'EPR'
})

const handleSubmit = async () => {
  error.value = ''
  loading.value = true
  try {
    let res
    if (mode.value === 'login') {
      res = await login({ email: form.value.email, password: form.value.password })
    } else {
      res = await register(form.value)
    }

    if (res?.success && res.access_token) {
      authStore.setAuth(res.access_token, res.user)
      router.push('/scenarios')
    } else {
      error.value = res?.error || 'Erreur d\'authentification'
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const quickLogin = async (email) => {
  form.value.email = email
  form.value.password = 'demo1234'
  mode.value = 'login'
  await handleSubmit()
}
</script>

<style scoped>
.login-view {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #FAFAFA;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.auth-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.auth-box {
  width: 100%;
  max-width: 440px;
  background: #FFF;
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  padding: 32px;
  box-shadow: 0 12px 32px rgba(0,0,0,0.04);
}

.brand-head {
  text-align: center;
  margin-bottom: 24px;
}

.brand-head .logo {
  font-size: 32px;
}

.brand-head h2 {
  font-family: 'JetBrains Mono', monospace;
  font-size: 24px;
  font-weight: 800;
  margin: 8px 0 4px 0;
}

.brand-head p {
  color: #666;
  font-size: 13px;
  margin: 0;
}

.auth-tabs {
  display: flex;
  border-bottom: 1px solid #EAEAEA;
  margin-bottom: 24px;
}

.tab {
  flex: 1;
  background: none;
  border: none;
  padding: 12px;
  font-weight: 700;
  font-size: 14px;
  color: #888;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tab.active {
  color: #000;
  border-bottom-color: #FF4500;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field label {
  font-size: 12px;
  font-weight: 700;
  color: #444;
}

.form-field input, .form-field select {
  padding: 10px 12px;
  border: 1px solid #DDD;
  border-radius: 6px;
  font-family: inherit;
  font-size: 14px;
}

.submit-btn {
  background: #000;
  color: #FFF;
  border: none;
  padding: 14px;
  border-radius: 6px;
  font-weight: 700;
  font-size: 14px;
  margin-top: 8px;
  cursor: pointer;
}

.submit-btn:hover {
  background: #222;
}

.error-msg {
  background: #FFEBEE;
  color: #C62828;
  padding: 10px;
  border-radius: 4px;
  font-size: 13px;
}

.quick-demo-accounts {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px dashed #EAEAEA;
}

.hint-label {
  display: block;
  font-size: 11px;
  color: #888;
  margin-bottom: 8px;
}

.demo-btns {
  display: flex;
  gap: 8px;
}

.demo-btns button {
  flex: 1;
  background: #F5F5F5;
  border: 1px solid #DDD;
  padding: 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}
</style>
