<template>
  <div class="publish-review-panel">
    <div class="panel-header">
      <h3>📋 {{ $t('review.title') }}</h3>
      <p class="subtitle">{{ $t('review.subtitle') }}</p>
    </div>

    <div class="status-banner" :class="scenarioStatus">
      <span class="status-label">{{ $t('review.currentStatus') }}</span>
      <span class="status-badge" :class="scenarioStatus">{{ getStatusText(scenarioStatus) }}</span>
    </div>

    <!-- Alert banner if 409 triggered -->
    <div v-if="errorMessage" class="alert-box error" role="alert">
      <span class="alert-icon">⚠️</span>
      <div class="alert-text">
        <strong>Rejet par le serveur (HTTP 409) :</strong>
        <p>{{ errorMessage }}</p>
      </div>
    </div>

    <!-- Success messages -->
    <div v-if="successMessage" class="alert-box success" role="status">
      <span class="alert-icon">✓</span>
      <p>{{ successMessage }}</p>
    </div>

    <!-- Step 1: Human Review -->
    <div class="step-section">
      <div class="step-num">ÉTAPE 1</div>
      <div class="step-body">
        <h4>Validation Méthodologique & Revue d'Expert</h4>
        <p>Attestation formelle que l'ontologie, les marges d'erreur et les projections OpenFisca ont été vérifiées.</p>
        
        <textarea 
          v-model="reviewComments" 
          placeholder="Notes d'audit et remarques méthodologiques pour le rapport..."
          rows="3"
          :disabled="scenarioStatus === 'published'"
        ></textarea>

        <button 
          class="btn-review"
          :disabled="reviewing || scenarioStatus === 'published' || scenarioStatus === 'reviewed'"
          @click="handleReview"
        >
          <span v-if="reviewing" class="spinner-sm"></span>
          {{ scenarioStatus === 'reviewed' || scenarioStatus === 'published' ? '✓ Scénario déjà revu' : $t('review.markReviewedBtn') }}
        </button>
      </div>
    </div>

    <!-- Step 2: External Publication -->
    <div class="step-section">
      <div class="step-num">ÉTAPE 2</div>
      <div class="step-body">
        <h4>Diffusion Publique & Transmission Parlementaire</h4>
        <p>Rend le scénario consultable dans la Bibliothèque officielle et dans les rapports publics.</p>
        <p class="warning-hint">{{ $t('review.publishLockedHint') }}</p>

        <button 
          class="btn-publish"
          :disabled="publishing || scenarioStatus === 'published' || scenarioStatus !== 'reviewed'"
          @click="handlePublish"
        >
          <span v-if="publishing" class="spinner-sm"></span>
          {{ scenarioStatus === 'published' ? '✓ Scénario officiellement publié' : $t('review.publishBtn') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { reviewScenario, publishScenario } from '../api/scenarios'

const props = defineProps({
  scenarioId: {
    type: String,
    required: true
  },
  initialStatus: {
    type: String,
    default: 'draft'
  }
})

const emit = defineEmits(['status-changed'])

const { t } = useI18n()

const scenarioStatus = ref(props.initialStatus)
const reviewComments = ref('')
const reviewing = ref(false)
const publishing = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const getStatusText = (status) => {
  switch (status) {
    case 'draft': return t('scenarios.statusDraft')
    case 'reviewed': return t('scenarios.statusReviewed')
    case 'published': return t('scenarios.statusPublished')
    default: return status
  }
}

const handleReview = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  reviewing.value = true
  try {
    const res = await reviewScenario(props.scenarioId, reviewComments.value)
    if (res.success) {
      scenarioStatus.value = 'reviewed'
      successMessage.value = t('review.successReviewed')
      emit('status-changed', 'reviewed')
    }
  } catch (err) {
    errorMessage.value = err.message || 'Erreur lors de la revue'
  } finally {
    reviewing.value = false
  }
}

const handlePublish = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  publishing.value = true
  try {
    const res = await publishScenario(props.scenarioId)
    if (res.success) {
      scenarioStatus.value = 'published'
      successMessage.value = t('review.successPublished')
      emit('status-changed', 'published')
    }
  } catch (err) {
    if (err.response?.status === 409 || err.message.includes('409')) {
      errorMessage.value = t('review.error409')
    } else {
      errorMessage.value = err.message || 'Erreur de publication'
    }
  } finally {
    publishing.value = false
  }
}
</script>

<style scoped>
.publish-review-panel {
  background: #FFF;
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  padding: 24px;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.panel-header {
  margin-bottom: 20px;
}

.panel-header h3 {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 6px 0;
}

.subtitle {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.status-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #FAFAFA;
  padding: 12px 16px;
  border-radius: 6px;
  border: 1px solid #EAEAEA;
  margin-bottom: 24px;
}

.status-label {
  font-size: 13px;
  font-weight: 600;
  color: #444;
}

.status-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 4px;
}

.status-badge.draft { background: #E0E0E0; color: #444; }
.status-badge.reviewed { background: #E3F2FD; color: #1565C0; }
.status-badge.published { background: #E8F5E9; color: #2E7D32; }

.alert-box {
  display: flex;
  gap: 12px;
  padding: 14px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.alert-box.error {
  background: #FFEBEE;
  border: 1px solid #FFCDD2;
  color: #C62828;
}

.alert-box.success {
  background: #E8F5E9;
  border: 1px solid #C8E6C9;
  color: #2E7D32;
}

.alert-icon {
  font-size: 18px;
}

.step-section {
  display: flex;
  gap: 20px;
  margin-bottom: 24px;
  padding: 20px;
  background: #FCFCFC;
  border: 1px solid #EAEAEA;
  border-radius: 6px;
}

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  background: #000;
  color: #FFF;
  padding: 4px 8px;
  height: fit-content;
  border-radius: 4px;
}

.step-body {
  flex: 1;
}

.step-body h4 {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 6px 0;
}

.step-body p {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  margin: 0 0 12px 0;
}

.warning-hint {
  font-size: 12px;
  color: #D32F2F;
  background: #FFF5F5;
  padding: 8px 12px;
  border-left: 3px solid #D32F2F;
}

textarea {
  width: 100%;
  border: 1px solid #DDD;
  border-radius: 6px;
  padding: 10px;
  font-family: inherit;
  font-size: 13px;
  margin-bottom: 12px;
}

.btn-review {
  background: #1565C0;
  color: #FFF;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.btn-review:disabled {
  background: #B0BEC5;
  cursor: not-allowed;
}

.btn-publish {
  background: #2E7D32;
  color: #FFF;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-weight: 700;
  cursor: pointer;
}

.btn-publish:disabled {
  background: #E0E0E0;
  color: #888;
  cursor: not-allowed;
}
</style>
