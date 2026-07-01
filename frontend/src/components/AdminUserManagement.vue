<template>
  <div class="admin-user-management">
    <div class="header">
      <div class="titles">
        <h2>{{ $t('admin.title') }}</h2>
        <p class="subtitle">{{ $t('admin.subtitle') }}</p>
      </div>
      <div class="auth-role-pill">
        Rôle actif : <strong class="badge">{{ authStore.userRole }}</strong>
      </div>
    </div>

    <!-- Permission check -->
    <div v-if="authStore.userRole !== 'admin'" class="unauthorized-box">
      <span class="lock-icon">🔒</span>
      <h3>Accès restreint</h3>
      <p>La gestion des comptes et des accréditations parlementaires est réservée aux administrateurs.</p>
    </div>

    <div v-else class="content-body">
      <div class="table-card">
        <div class="card-head">
          <h3>{{ $t('admin.userList') }} ({{ users.length }})</h3>
        </div>

        <table>
          <thead>
            <tr>
              <th>Nom & Email</th>
              <th>Groupe Politique / Affiliation</th>
              <th>Statut</th>
              <th>Rôle Actuel</th>
              <th>Action de Réattribution</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>
                <div class="user-info">
                  <span class="u-name">{{ user.name }}</span>
                  <span class="u-email">{{ user.email }}</span>
                </div>
              </td>
              <td>
                <span class="grp-badge">{{ user.group || 'N/A' }}</span>
              </td>
              <td>
                <span class="status-pill active">{{ user.status }}</span>
              </td>
              <td>
                <span class="role-badge" :class="user.role">{{ getRoleLabel(user.role) }}</span>
              </td>
              <td>
                <div class="role-selector">
                  <select v-model="user.newRole" class="role-select">
                    <option value="admin">{{ $t('admin.roleAdmin') }}</option>
                    <option value="analyst">{{ $t('admin.roleAnalyst') }}</option>
                    <option value="deputy">{{ $t('admin.roleDeputy') }}</option>
                    <option value="viewer">{{ $t('admin.roleViewer') }}</option>
                  </select>
                  <button 
                    class="save-btn" 
                    :disabled="user.role === user.newRole || updatingId === user.id"
                    @click="changeRole(user)"
                  >
                    Mettre à jour
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../store/auth'
import { getUsers, updateUserRole } from '../api/admin'

const { t } = useI18n()
const authStore = useAuthStore()

const users = ref([])
const updatingId = ref(null)

const loadUsers = async () => {
  const res = await getUsers()
  if (res?.success) {
    users.value = (res.users || []).map(u => ({
      ...u,
      newRole: u.role
    }))
  }
}

const getRoleLabel = (role) => {
  switch (role) {
    case 'admin': return t('admin.roleAdmin')
    case 'analyst': return t('admin.roleAnalyst')
    case 'deputy': return t('admin.roleDeputy')
    case 'viewer': return t('admin.roleViewer')
    default: return role
  }
}

const changeRole = async (user) => {
  updatingId.value = user.id
  const res = await updateUserRole(user.id, user.newRole)
  if (res?.success) {
    user.role = user.newRole
  }
  updatingId.value = null
}

onMounted(loadUsers)
</script>

<style scoped>
.admin-user-management {
  padding: 32px 40px;
  background: #FFF;
  min-height: 100vh;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.header {
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

.auth-role-pill {
  font-size: 13px;
  background: #FAFAFA;
  border: 1px solid #DDD;
  padding: 8px 16px;
  border-radius: 6px;
}

.auth-role-pill .badge {
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  background: #000;
  color: #FFF;
  padding: 2px 6px;
  border-radius: 4px;
}

.unauthorized-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: #FAFAFA;
  border: 1px dashed #DDD;
  border-radius: 8px;
  text-align: center;
  padding: 40px;
}

.lock-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.table-card {
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  overflow: hidden;
}

.card-head {
  padding: 16px 20px;
  background: #FAFAFA;
  border-bottom: 1px solid #EAEAEA;
}

.card-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 16px 20px;
  border-bottom: 1px solid #EAEAEA;
  text-align: left;
}

th {
  background: #F5F5F5;
  font-weight: 700;
  font-size: 13px;
}

.user-info {
  display: flex;
  flex-direction: column;
}

.u-name {
  font-weight: 700;
  font-size: 14px;
}

.u-email {
  font-size: 12px;
  color: #888;
}

.grp-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  background: #EEE;
  padding: 4px 8px;
  border-radius: 4px;
}

.status-pill {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  background: #E8F5E9;
  color: #2E7D32;
  padding: 4px 8px;
  border-radius: 12px;
}

.role-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.role-badge.admin { background: #000; color: #FFF; }
.role-badge.analyst { background: #E3F2FD; color: #1565C0; }
.role-badge.deputy { background: #FFF3E0; color: #E65100; }
.role-badge.viewer { background: #F5F5F5; color: #666; }

.role-selector {
  display: flex;
  gap: 8px;
}

.role-select {
  padding: 6px 10px;
  border: 1px solid #DDD;
  border-radius: 4px;
  font-family: inherit;
  font-size: 12px;
}

.save-btn {
  background: #000;
  color: #FFF;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.save-btn:disabled {
  background: #E0E0E0;
  color: #999;
  cursor: not-allowed;
}
</style>
