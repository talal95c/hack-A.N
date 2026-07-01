<template>
  <div class="wizard-portal-white">
    <MiroNavbar />

    <main class="wizard-container">
      <!-- Header -->
      <div class="wizard-header motion-item delay-1">
        <div class="breadcrumb">
          <button class="back-btn" @click="$router.push('/')">← Retour à l'accueil</button>
        </div>
        <div class="cad-dimension">
          <span class="cad-arrow">|←</span>
          <span class="cad-label">Ajout et analyse d'une nouvelle loi</span>
          <span class="cad-arrow">→|</span>
        </div>
        <h1>lancer une <span class="bold-text">nouvelle simulation</span></h1>
        <p class="subtitle">Déposez vos textes ou amendements pour découvrir immédiatement leur impact sur le budget des ménages et sur le vote des députés.</p>
      </div>

      <div class="h-grid-line motion-item delay-2"></div>

      <!-- Main Form & Drop Zone Grid -->
      <div class="wizard-grid motion-item delay-3">
        <!-- Left: Drag & Drop Document Upload Box -->
        <div class="upload-section wireframe-box">
          <div class="section-top">
            <span class="sec-num">01</span>
            <h3>Dépôt des Documents (<span class="bold-text">PDF, DOCX, TXT</span>)</h3>
          </div>

          <div 
            class="drop-zone"
            :class="{ 'is-dragging': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="triggerFileInput"
          >
            <input 
              ref="fileInput" 
              type="file" 
              multiple 
              accept=".pdf,.docx,.doc,.txt,.json" 
              class="hidden-file-input" 
              @change="handleFileSelect"
            />

            <div class="drop-content">
              <span class="drop-icon" style="font-family: monospace; font-size: 32px; color: #94A3B8;">+</span>
              <p class="drop-main-text">
                <strong>Glissez-déposez vos fichiers législatifs ici</strong> ou <span class="link-text">parcourez</span>
              </p>
              <p class="drop-sub-text">Formats acceptés : PDF, DOCX, TXT (propositions de loi, exposés des motifs, amendements)</p>
            </div>
          </div>

          <!-- File List -->
          <div v-if="uploadedFiles.length > 0" class="file-list">
            <div class="file-list-title">Fichiers importés ({{ uploadedFiles.length }}) :</div>
            <div v-for="(file, index) in uploadedFiles" :key="index" class="file-item">
              <div class="file-info">
                <span class="file-type-badge">{{ getFileExtension(file.name) }}</span>
                <span class="file-name">{{ file.name }}</span>
                <span class="file-size">({{ formatSize(file.size) }})</span>
              </div>
              <button class="remove-file-btn" @click.stop="removeFile(index)">×</button>
            </div>
          </div>

          <!-- Sample Quick Fill button for Demo -->
          <div v-if="uploadedFiles.length === 0" class="sample-demo-fill">
            <span class="sample-hint">Ou chargez un texte d'exemple pour tester immédiatement :</span>
            <button class="btn-sample" @click.stop="loadSampleFile">
              Charger "Proposition_Loi_Réforme_Logement_APL_2026.pdf"
            </button>
          </div>
        </div>

        <!-- Right: Parameters & Metadata -->
        <div class="params-section wireframe-box">
          <div class="section-top">
            <span class="sec-num">02</span>
            <h3>Réglages de la <span class="bold-text">simulation</span></h3>
          </div>

          <div class="form-group">
            <label>Titre de la Réforme législative</label>
            <input 
              v-model="form.title" 
              type="text" 
              placeholder="ex: Réforme de l'Aide Personnalisée au Logement (APL) 2026" 
            />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Groupe Parlementaire / Auteur</label>
              <select v-model="form.author">
                <option value="EPR">EPR (Ensemble pour la République)</option>
                <option value="LFI-NFP">LFI-NFP (La France Insoumise)</option>
                <option value="RN">RN (Rassemblement National)</option>
                <option value="SOC">SOC (Socialistes et apparentés)</option>
                <option value="DR">DR (Droite Républicaine)</option>
                <option value="Gouvernement">Projet de loi gouvernemental</option>
              </select>
            </div>

            <div class="form-group">
              <label>Domaine de calcul</label>
              <select v-model="form.openfiscaModel">
                <option value="logement_apl">Aides au logement (APL)</option>
                <option value="impot_revenu">Impôt sur le revenu et prestations</option>
                <option value="transition_energ">Taxe carbone & Chèque énergie</option>
                <option value="custom">Calcul personnalisé (13 régions)</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>Points importants ou objectifs prioritaires</label>
            <textarea 
              v-model="form.requirement" 
              rows="4" 
              placeholder="Précisez les personnes concernées (ex: étudiants, locataires, familles modestes) ou les points à surveiller..."
            ></textarea>
          </div>

          <div class="form-footer">
            <div class="status-tip">
              <span class="dot-green"></span>
              <span>Moteur prêt pour le calcul en direct</span>
            </div>
            <button 
              class="btn-submit-simulation" 
              :disabled="uploadedFiles.length === 0 && !form.title"
              @click="launchSimulation"
            >
              <span>Lancer une simulation avec les agents IA →</span>
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { setPendingUpload } from '../store/pendingUpload'
import MiroNavbar from '../components/MiroNavbar.vue'

const router = useRouter()
const fileInput = ref(null)
const isDragging = ref(false)
const uploadedFiles = ref([])

const form = reactive({
  title: 'Proposition de Loi : Réforme du barème APL 2026',
  author: 'EPR',
  openfiscaModel: 'logement_apl',
  requirement: "Analyser l'impact d'une revalorisation forfaitaire de +15€ des APL pour les étudiants en zone tendue et son accueil au sein des 577 sièges."
})

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (e) => {
  const files = Array.from(e.target.files || [])
  files.forEach(f => {
    if (!uploadedFiles.value.some(uf => uf.name === f.name)) {
      uploadedFiles.value.push(f)
    }
  })
}

const handleDrop = (e) => {
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files || [])
  files.forEach(f => {
    if (!uploadedFiles.value.some(uf => uf.name === f.name)) {
      uploadedFiles.value.push(f)
    }
  })
}

const removeFile = (idx) => {
  uploadedFiles.value.splice(idx, 1)
}

const getFileExtension = (filename) => {
  return filename.split('.').pop().toUpperCase()
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const loadSampleFile = () => {
  const sampleContent = "Proposition de loi nº 1482 relative au soutien au pouvoir d'achat par la réévaluation des aides personnalisées au logement (APL)..."
  const blob = new Blob([sampleContent], { type: 'application/pdf' })
  const mockFile = new File([blob], 'Proposition_Loi_Réforme_Logement_APL_2026.pdf', { type: 'application/pdf' })
  uploadedFiles.value.push(mockFile)
}

const launchSimulation = () => {
  const fullReq = `[${form.author}] ${form.title} (Domaine de calcul: ${form.openfiscaModel}) - ${form.requirement}`
  setPendingUpload(uploadedFiles.value, fullReq)
  
  // Navigate to Circuit A (MainView.vue) to generate ontology and launch simulation with AI agents
  router.push('/process/start')
}
</script>

<style scoped>
.wizard-portal-white {
  min-height: 100vh;
  background: #FAFAFB;
  color: #0F172A;
}

.wizard-container {
  max-width: 1360px;
  margin: 0 auto;
  padding: 48px 48px 80px;
  position: relative;
  min-height: calc(100vh - 72px);
}

.breadcrumb {
  margin-bottom: 20px;
}

.back-btn {
  background: none;
  border: none;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #64748B;
  cursor: pointer;
  padding: 8px 14px;
  margin-left: -14px;
  border-radius: 8px;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.back-btn:hover {
  color: #0F172A;
  background: #F1F5F9;
}

.cad-dimension {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #64748B;
  margin-bottom: 12px;
}

.cad-arrow { color: #94A3B8; font-weight: 600; }

.wizard-header {
  margin-bottom: 32px;
}

.wizard-header h1 {
  font-size: 48px;
  font-weight: 400;
  letter-spacing: -1.5px;
  margin-bottom: 12px;
  color: #000000;
}

.bold-text { font-weight: 700; }

.subtitle {
  color: #475569;
  font-size: 17px;
  max-width: 760px;
  line-height: 1.6;
}

.h-grid-line {
  width: 100%;
  height: 1px;
  background: #E2E8F0;
  margin: 36px 0 44px;
}

.wizard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
  align-items: stretch;
}

.wireframe-box {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 24px;
  padding: 40px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.025);
  transition: box-shadow 0.25s ease, border-color 0.25s ease;
}

.wireframe-box:hover {
  border-color: #CBD5E1;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.05);
}

.section-top {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 32px;
}

.sec-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 700;
  background: #000000;
  color: #FFFFFF;
  padding: 5px 10px;
  border-radius: 8px;
}

.section-top h3 {
  font-size: 22px;
  font-weight: 400;
  color: #0F172A;
}

/* Drop Zone */
.drop-zone {
  border: 2px dashed #CBD5E1;
  background: #F8FAFC;
  border-radius: 20px;
  padding: 64px 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s ease;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 280px;
}

.drop-zone:hover, .drop-zone.is-dragging {
  border-color: #000000;
  background: #F1F5F9;
}

.hidden-file-input { display: none; }

.drop-icon {
  font-size: 52px;
  display: block;
  margin-bottom: 20px;
}

.drop-main-text {
  font-size: 16px;
  color: #0F172A;
  margin-bottom: 10px;
}

.link-text { text-decoration: underline; font-weight: 600; }

.drop-sub-text {
  font-size: 13px;
  color: #64748B;
  max-width: 380px;
  line-height: 1.5;
}

/* File List */
.file-list {
  margin-top: 28px;
  border-top: 1px solid #E2E8F0;
  padding-top: 24px;
}

.file-list-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 14px;
  color: #0F172A;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  padding: 12px 16px;
  border-radius: 12px;
  margin-bottom: 10px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  overflow: hidden;
}

.file-type-badge {
  background: #0F172A;
  color: #FFF;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
}

.file-name { font-weight: 600; color: #0F172A; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 260px; }
.file-size { color: #64748B; font-size: 13px; }

.remove-file-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #94A3B8;
  padding: 0 6px;
}

.remove-file-btn:hover { color: #DC2626; }

.sample-demo-fill {
  margin-top: 28px;
  text-align: center;
}

.sample-hint {
  display: block;
  font-size: 13px;
  color: #64748B;
  margin-bottom: 12px;
}

.btn-sample {
  background: #FFFFFF;
  border: 1px dashed #0F172A;
  color: #0F172A;
  padding: 12px 20px;
  border-radius: 9999px;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-sample:hover { background: #0F172A; color: #FFF; border-style: solid; }

/* Params Form */
.form-group {
  margin-bottom: 24px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 10px;
  color: #0F172A;
}

.form-group input, .form-group select, .form-group textarea {
  width: 100%;
  padding: 14px 18px;
  border: 1px solid #CBD5E1;
  border-radius: 12px;
  font-family: inherit;
  font-size: 14.5px;
  color: #0F172A;
  background: #FFF;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-group input:focus, .form-group select:focus, .form-group textarea:focus {
  border-color: #000000;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.05);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.form-footer {
  margin-top: auto;
  padding-top: 32px;
  border-top: 1px solid #F1F5F9;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.status-tip {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #64748B;
  font-weight: 500;
}

.dot-green {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #10B981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
}

.btn-submit-simulation {
  background: #000000;
  color: #FFFFFF;
  border: none;
  padding: 18px 24px;
  border-radius: 9999px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}

.btn-submit-simulation:hover:not(:disabled) {
  background: #1E293B;
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.18);
}

.btn-submit-simulation:disabled {
  background: #94A3B8;
  cursor: not-allowed;
  opacity: 0.7;
}

.motion-item {
  animation: slideFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes slideFadeIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.delay-1 { animation-delay: 0.1s; }
.delay-2 { animation-delay: 0.2s; }
.delay-3 { animation-delay: 0.3s; }

@media (max-width: 1024px) {
  .wizard-grid { grid-template-columns: 1fr; gap: 28px; }
  .wizard-container { padding: 32px 24px 60px; }
}
</style>
