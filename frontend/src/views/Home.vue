<template>
  <div class="landing-page-white" :class="{ 'page-loaded': isLoaded }" @mousemove="handleMouseMove">
    <MiroNavbar />

    <!-- Pure White Wireframe Hero Content -->
    <main class="wireframe-hero">
      <div class="hero-center">
        <!-- CAD Architectural Dimension Line Above -->
        <div class="cad-dimension top-dim motion-element delay-1">
          <span class="cad-arrow left-arrow">|←</span>
          <span class="cad-label">Simulation & Analyse de lois</span>
          <span class="cad-arrow right-arrow">→|</span>
        </div>

        <h1 class="headline motion-element delay-2">
          <span class="line-reveal">nous anticipons</span><br />
          <span class="bold-text line-reveal">l'impact de vos lois</span>
        </h1>

        <!-- CAD Architectural Dimension Line Below -->
        <div class="cad-dimension bottom-dim motion-element delay-3">
          <span class="cad-arrow left-arrow">|←</span>
          <span class="cad-label">Calcul du pouvoir d'achat & vote des députés</span>
          <span class="cad-arrow right-arrow">→|</span>
        </div>

        <p class="subtitle motion-element delay-4">
          Testez vos propositions de loi et découvrez en direct leurs conséquences concrètes sur les Français et sur les 577 députés.
        </p>

        <div class="action-buttons motion-element delay-5">
          <button class="btn-black-pill motion-hover" @click="$router.push('/process/new')">
            <span>Lancer une simulation</span>
            <span class="btn-arrow">→</span>
          </button>
        </div>
      </div>

      <!-- Bottom Partners / Sources section -->
      <div class="partners-section motion-element delay-6">
        <div class="h-grid-line bottom-line"></div>
        <span class="partners-title">Données officielles :</span>
        <div class="partners-logos">
          <span class="partner-item">Assemblée nationale</span>
          <span class="partner-sep">•</span>
          <span class="partner-item">Données publiques (data.gouv)</span>
          <span class="partner-sep">•</span>
          <span class="partner-item">Calculateur de l'État (OpenFisca)</span>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import MiroNavbar from '../components/MiroNavbar.vue'

const router = useRouter()
const isLoaded = ref(false)
const mouseX = ref(-1000)
const mouseY = ref(-1000)

const handleMouseMove = (e) => {
  mouseX.value = e.clientX
  mouseY.value = e.clientY
}

onMounted(() => {
  setTimeout(() => {
    isLoaded.value = true
  }, 60)
})
</script>

<style scoped>
.landing-page-white {
  min-height: 100vh;
  background-color: #FFFFFF;
  display: flex;
  flex-direction: column;
  color: #000000;
  position: relative;
  overflow: hidden;
}

/* ==========================================
   DYNAMIC ANIMATED GRID BACKGROUND
   ========================================== */

/* Layer 1: Infinite Scrolling Minimalist Grid */
.animated-grid-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(to right, rgba(15, 23, 42, 0.045) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(15, 23, 42, 0.045) 1px, transparent 1px);
  background-size: 40px 40px;
  animation: gridScroll 30s linear infinite;
  z-index: 0;
}

@keyframes gridScroll {
  0% {
    background-position: 0px 0px;
  }
  100% {
    background-position: -80px -80px;
  }
}

/* Layer 2: Interactive Mouse Spotlight Grid Highlight */
.interactive-grid-spotlight {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(to right, rgba(15, 23, 42, 0.18) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(15, 23, 42, 0.18) 1px, transparent 1px);
  background-size: 40px 40px;
  animation: gridScroll 30s linear infinite;
  mask-image: radial-gradient(
    300px circle at var(--mouse-x) var(--mouse-y),
    rgba(0, 0, 0, 1) 0%,
    transparent 100%
  );
  -webkit-mask-image: radial-gradient(
    300px circle at var(--mouse-x) var(--mouse-y),
    rgba(0, 0, 0, 1) 0%,
    transparent 100%
  );
  pointer-events: none;
  z-index: 1;
}

/* Layer 3: Soft Edge Gradient Vignette Overlay to blend smoothly */
.grid-fade-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 50% 50%, transparent 40%, rgba(255, 255, 255, 0.85) 90%);
  pointer-events: none;
  z-index: 1;
}

/* ==========================================
   WIREFRAME HERO CONTENT
   ========================================== */
.wireframe-hero {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  padding: 60px 40px 20px;
  z-index: 2;
}

/* Staggered Motion Elements */
.motion-element {
  opacity: 0;
  transform: translateY(24px) scale(0.98);
  filter: blur(8px);
  transition: opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.8s cubic-bezier(0.16, 1, 0.3, 1),
              filter 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.page-loaded .motion-element {
  opacity: 1;
  transform: translateY(0) scale(1);
  filter: blur(0px);
}

.delay-1 { transition-delay: 0.15s; }
.delay-2 { transition-delay: 0.25s; }
.delay-3 { transition-delay: 0.35s; }
.delay-4 { transition-delay: 0.45s; }
.delay-5 { transition-delay: 0.55s; }
.delay-6 { transition-delay: 0.65s; }
.delay-7 { transition-delay: 0.75s; }

/* CAD Architectural Dimension Arrows */
.cad-arrow {
  display: inline-block;
  transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.page-loaded .left-arrow { transform: translateX(-4px); }
.page-loaded .right-arrow { transform: translateX(4px); }

.cad-dimension:hover .left-arrow { transform: translateX(-8px); color: #000; }
.cad-dimension:hover .right-arrow { transform: translateX(8px); color: #000; }

.hero-center {
  max-width: 820px;
  margin: 80px auto;
  text-align: center;
  position: relative;
}

.cad-dimension {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #64748B;
  letter-spacing: 0.5px;
  cursor: default;
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(226, 232, 240, 0.8);
  transition: all 0.3s;
}

.cad-dimension:hover {
  background-color: #FFFFFF;
  border-color: #000000;
}

.top-dim { margin-bottom: 20px; }
.bottom-dim { margin-top: 20px; margin-bottom: 40px; }

.headline {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 64px;
  font-weight: 400;
  line-height: 1.08;
  letter-spacing: -2px;
  color: #000000;
}

.bold-text { font-weight: 700; }

.subtitle {
  font-size: 18px;
  line-height: 1.6;
  color: #475569;
  max-width: 540px;
  margin: 0 auto 36px;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 28px;
}

.btn-black-pill {
  background: #000000;
  color: #FFFFFF;
  border: none;
  padding: 16px 36px;
  border-radius: var(--radius-pill);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.18);
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.btn-black-pill:hover {
  background: #1E293B;
  transform: translateY(-3px) scale(1.02);
  box-shadow: 0 18px 36px rgba(0, 0, 0, 0.28);
}

.btn-arrow {
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.btn-black-pill:hover .btn-arrow {
  transform: translateX(5px);
}

.btn-white-pill {
  background: #FFFFFF;
  color: #000000;
  border: 1px solid #CBD5E1;
  padding: 16px 32px;
  border-radius: var(--radius-pill);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.btn-white-pill:hover {
  background: #F8FAFC;
  border-color: #000000;
  transform: translateY(-3px) scale(1.02);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
}

.calibration-note {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #64748B;
  background: rgba(248, 250, 252, 0.85);
  backdrop-filter: blur(8px);
  padding: 8px 18px;
  border-radius: var(--radius-pill);
  border: 1px solid #E2E8F0;
  transition: all 0.3s;
}

.calibration-note:hover {
  border-color: #94A3B8;
  background: #FFF;
  box-shadow: 0 4px 12px rgba(0,0,0,0.04);
}

.pulse-icon {
  font-size: 14px;
  animation: pulseLock 2.5s infinite;
}

@keyframes pulseLock {
  0% { transform: scale(1); }
  50% { transform: scale(1.15); }
  100% { transform: scale(1); }
}

/* Partners Footer Section */
.partners-section {
  position: relative;
  padding: 32px 0 20px;
  text-align: center;
  margin-top: auto;
}

.h-grid-line {
  width: 100%;
  height: 1px;
  border-top: 1px dashed rgba(15, 23, 42, 0.15);
  margin-bottom: 20px;
}

.partners-title {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #94A3B8;
  margin-bottom: 16px;
  letter-spacing: 0.5px;
}

.partners-logos {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24px;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 14px;
  font-weight: 700;
  color: #334155;
}

.partner-item {
  transition: color 0.2s, transform 0.2s;
  cursor: default;
}

.partner-item:hover {
  color: #000;
  transform: translateY(-1px);
}

.sep { color: #CBD5E1; }

@media (max-width: 1024px) {
  .headline { font-size: 44px; }
}
</style>
