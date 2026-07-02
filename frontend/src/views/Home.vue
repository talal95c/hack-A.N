<template>
  <div class="landing-page-white" :class="{ 'page-loaded': isLoaded }" @mousemove="handleMouseMove">
    <MiroNavbar />

    <!-- Stacked Floating 3D Doodle Stickers Layer (Full Viewport Width 100%) -->
    <div class="doodles-layer">
      <!-- DEPTH LAYER 3: FAR BACKGROUND (17 stickers) -->
      <div class="doodle-wrapper sticker-bg-1" :style="{ transform: `translate3d(${parallaxX * -12}px, ${parallaxY * -8}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker BG 1" class="doodle-img depth-bg float-low-1" /></div>
      <div class="doodle-wrapper sticker-bg-2" :style="{ transform: `translate3d(${parallaxX * 14}px, ${parallaxY * 10}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker BG 2" class="doodle-img depth-bg float-low-2" /></div>
      <div class="doodle-wrapper sticker-bg-3" :style="{ transform: `translate3d(${parallaxX * -10}px, ${parallaxY * 12}px, 0)` }"><img src="/doodle/doodle-4.png" alt="Sticker BG 3" class="doodle-img depth-bg float-low-3" /></div>
      <div class="doodle-wrapper sticker-bg-4" :style="{ transform: `translate3d(${parallaxX * 15}px, ${parallaxY * -10}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker BG 4" class="doodle-img depth-bg float-low-4" /></div>
      <div class="doodle-wrapper sticker-bg-5" :style="{ transform: `translate3d(${parallaxX * -14}px, ${parallaxY * 14}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker BG 5" class="doodle-img depth-bg float-low-1" /></div>
      <div class="doodle-wrapper sticker-bg-6" :style="{ transform: `translate3d(${parallaxX * 16}px, ${parallaxY * -12}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker BG 6" class="doodle-img depth-bg float-low-2" /></div>
      <div class="doodle-wrapper sticker-bg-7" :style="{ transform: `translate3d(${parallaxX * -15}px, ${parallaxY * 10}px, 0)` }"><img src="/doodle/doodle-4.png" alt="Sticker BG 7" class="doodle-img depth-bg float-low-3" /></div>
      <div class="doodle-wrapper sticker-bg-8" :style="{ transform: `translate3d(${parallaxX * 13}px, ${parallaxY * -14}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker BG 8" class="doodle-img depth-bg float-low-4" /></div>
      <div class="doodle-wrapper sticker-bg-9" :style="{ transform: `translate3d(${parallaxX * -11}px, ${parallaxY * -12}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker BG 9" class="doodle-img depth-bg float-low-1" /></div>
      <div class="doodle-wrapper sticker-bg-10" :style="{ transform: `translate3d(${parallaxX * 15}px, ${parallaxY * 14}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker BG 10" class="doodle-img depth-bg float-low-2" /></div>
      <div class="doodle-wrapper sticker-bg-11" :style="{ transform: `translate3d(${parallaxX * -13}px, ${parallaxY * 11}px, 0)` }"><img src="/doodle/doodle-4.png" alt="Sticker BG 11" class="doodle-img depth-bg float-low-3" /></div>
      <div class="doodle-wrapper sticker-bg-12" :style="{ transform: `translate3d(${parallaxX * 14}px, ${parallaxY * -11}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker BG 12" class="doodle-img depth-bg float-low-4" /></div>
      <div class="doodle-wrapper sticker-bg-13" :style="{ transform: `translate3d(${parallaxX * -15}px, ${parallaxY * 13}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker BG 13" class="doodle-img depth-bg float-low-1" /></div>
      <div class="doodle-wrapper sticker-bg-14" :style="{ transform: `translate3d(${parallaxX * 12}px, ${parallaxY * -10}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker BG 14" class="doodle-img depth-bg float-low-2" /></div>
      <div class="doodle-wrapper sticker-bg-15" :style="{ transform: `translate3d(${parallaxX * -14}px, ${parallaxY * 12}px, 0)` }"><img src="/doodle/doodle-4.png" alt="Sticker BG 15" class="doodle-img depth-bg float-low-3" /></div>
      <div class="doodle-wrapper sticker-bg-16" :style="{ transform: `translate3d(${parallaxX * 15}px, ${parallaxY * -13}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker BG 16" class="doodle-img depth-bg float-low-4" /></div>
      <div class="doodle-wrapper sticker-bg-17" :style="{ transform: `translate3d(${parallaxX * -11}px, ${parallaxY * 11}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker BG 17" class="doodle-img depth-bg float-low-1" /></div>

      <!-- DEPTH LAYER 2: MIDDLE LAYER (17 stickers) -->
      <div class="doodle-wrapper sticker-mid-1" :style="{ transform: `translate3d(${parallaxX * -25}px, ${parallaxY * -18}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker Mid 1" class="doodle-img depth-mid float-low-3" /></div>
      <div class="doodle-wrapper sticker-mid-2" :style="{ transform: `translate3d(${parallaxX * 28}px, ${parallaxY * 20}px, 0)` }"><img src="/doodle/doodle-4.png" alt="Sticker Mid 2" class="doodle-img depth-mid float-low-4" /></div>
      <div class="doodle-wrapper sticker-mid-3" :style="{ transform: `translate3d(${parallaxX * -22}px, ${parallaxY * 22}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker Mid 3" class="doodle-img depth-mid float-low-1" /></div>
      <div class="doodle-wrapper sticker-mid-4" :style="{ transform: `translate3d(${parallaxX * 26}px, ${parallaxY * -18}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker Mid 4" class="doodle-img depth-mid float-low-2" /></div>
      <div class="doodle-wrapper sticker-mid-5" :style="{ transform: `translate3d(${parallaxX * -24}px, ${parallaxY * 20}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker Mid 5" class="doodle-img depth-mid float-low-3" /></div>
      <div class="doodle-wrapper sticker-mid-6" :style="{ transform: `translate3d(${parallaxX * 30}px, ${parallaxY * -22}px, 0)` }"><img src="/doodle/doodle-4.png" alt="Sticker Mid 6" class="doodle-img depth-mid float-low-4" /></div>
      <div class="doodle-wrapper sticker-mid-7" :style="{ transform: `translate3d(${parallaxX * -26}px, ${parallaxY * 18}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker Mid 7" class="doodle-img depth-mid float-low-1" /></div>
      <div class="doodle-wrapper sticker-mid-8" :style="{ transform: `translate3d(${parallaxX * 28}px, ${parallaxY * -20}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker Mid 8" class="doodle-img depth-mid float-low-2" /></div>
      <div class="doodle-wrapper sticker-mid-9" :style="{ transform: `translate3d(${parallaxX * -24}px, ${parallaxY * -19}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker Mid 9" class="doodle-img depth-mid float-low-3" /></div>
      <div class="doodle-wrapper sticker-mid-10" :style="{ transform: `translate3d(${parallaxX * 27}px, ${parallaxY * 21}px, 0)` }"><img src="/doodle/doodle-4.png" alt="Sticker Mid 10" class="doodle-img depth-mid float-low-4" /></div>
      <div class="doodle-wrapper sticker-mid-11" :style="{ transform: `translate3d(${parallaxX * -23}px, ${parallaxY * 19}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker Mid 11" class="doodle-img depth-mid float-low-1" /></div>
      <div class="doodle-wrapper sticker-mid-12" :style="{ transform: `translate3d(${parallaxX * 29}px, ${parallaxY * -21}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker Mid 12" class="doodle-img depth-mid float-low-2" /></div>
      <div class="doodle-wrapper sticker-mid-13" :style="{ transform: `translate3d(${parallaxX * -25}px, ${parallaxY * 20}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker Mid 13" class="doodle-img depth-mid float-low-3" /></div>
      <div class="doodle-wrapper sticker-mid-14" :style="{ transform: `translate3d(${parallaxX * 27}px, ${parallaxY * -19}px, 0)` }"><img src="/doodle/doodle-4.png" alt="Sticker Mid 14" class="doodle-img depth-mid float-low-4" /></div>
      <div class="doodle-wrapper sticker-mid-15" :style="{ transform: `translate3d(${parallaxX * -23}px, ${parallaxY * 21}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker Mid 15" class="doodle-img depth-mid float-low-1" /></div>
      <div class="doodle-wrapper sticker-mid-16" :style="{ transform: `translate3d(${parallaxX * 28}px, ${parallaxY * -18}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker Mid 16" class="doodle-img depth-mid float-low-2" /></div>
      <div class="doodle-wrapper sticker-mid-17" :style="{ transform: `translate3d(${parallaxX * -26}px, ${parallaxY * 19}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker Mid 17" class="doodle-img depth-mid float-low-3" /></div>

      <!-- DEPTH LAYER 1: FOREGROUND LAYER (17 stickers) -->
      <div class="doodle-wrapper sticker-fg-1" :style="{ transform: `translate3d(${parallaxX * -45}px, ${parallaxY * -30}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker FG 1" class="doodle-img depth-fg float-low-2" /></div>
      <div class="doodle-wrapper sticker-fg-2" :style="{ transform: `translate3d(${parallaxX * 48}px, ${parallaxY * 35}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker FG 2" class="doodle-img depth-fg float-low-3" /></div>
      <div class="doodle-wrapper sticker-fg-3" :style="{ transform: `translate3d(${parallaxX * -40}px, ${parallaxY * 38}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker FG 3" class="doodle-img depth-fg float-low-4" /></div>
      <div class="doodle-wrapper sticker-fg-4" :style="{ transform: `translate3d(${parallaxX * 42}px, ${parallaxY * -34}px, 0)` }"><img src="/doodle/doodle-4.png" alt="Sticker FG 4" class="doodle-img depth-fg float-low-1" /></div>
      <div class="doodle-wrapper sticker-fg-5" :style="{ transform: `translate3d(${parallaxX * -46}px, ${parallaxY * 32}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker FG 5" class="doodle-img depth-fg float-low-2" /></div>
      <div class="doodle-wrapper sticker-fg-6" :style="{ transform: `translate3d(${parallaxX * 50}px, ${parallaxY * -36}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker FG 6" class="doodle-img depth-fg float-low-3" /></div>
      <div class="doodle-wrapper sticker-fg-7" :style="{ transform: `translate3d(${parallaxX * -44}px, ${parallaxY * 34}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker FG 7" class="doodle-img depth-fg float-low-4" /></div>
      <div class="doodle-wrapper sticker-fg-8" :style="{ transform: `translate3d(${parallaxX * 46}px, ${parallaxY * -32}px, 0)` }"><img src="/doodle/doodle-4.png" alt="Sticker FG 8" class="doodle-img depth-fg float-low-1" /></div>
      <div class="doodle-wrapper sticker-fg-9" :style="{ transform: `translate3d(${parallaxX * -42}px, ${parallaxY * -32}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker FG 9" class="doodle-img depth-fg float-low-2" /></div>
      <div class="doodle-wrapper sticker-fg-10" :style="{ transform: `translate3d(${parallaxX * 49}px, ${parallaxY * 36}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker FG 10" class="doodle-img depth-fg float-low-3" /></div>
      <div class="doodle-wrapper sticker-fg-11" :style="{ transform: `translate3d(${parallaxX * -41}px, ${parallaxY * 37}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker FG 11" class="doodle-img depth-fg float-low-4" /></div>
      <div class="doodle-wrapper sticker-fg-12" :style="{ transform: `translate3d(${parallaxX * 45}px, ${parallaxY * -33}px, 0)` }"><img src="/doodle/doodle-4.png" alt="Sticker FG 12" class="doodle-img depth-fg float-low-1" /></div>
      <div class="doodle-wrapper sticker-fg-13" :style="{ transform: `translate3d(${parallaxX * -44}px, ${parallaxY * 35}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker FG 13" class="doodle-img depth-fg float-low-2" /></div>
      <div class="doodle-wrapper sticker-fg-14" :style="{ transform: `translate3d(${parallaxX * 47}px, ${parallaxY * -34}px, 0)` }"><img src="/doodle/doodle-3.png" alt="Sticker FG 14" class="doodle-img depth-fg float-low-3" /></div>
      <div class="doodle-wrapper sticker-fg-15" :style="{ transform: `translate3d(${parallaxX * -43}px, ${parallaxY * 36}px, 0)` }"><img src="/doodle/doodle-2.png" alt="Sticker FG 15" class="doodle-img depth-fg float-low-4" /></div>
      <div class="doodle-wrapper sticker-fg-17" :style="{ transform: `translate3d(${parallaxX * -45}px, ${parallaxY * 33}px, 0)` }"><img src="/doodle/doodle-1.png" alt="Sticker FG 17" class="doodle-img depth-fg float-low-2" /></div>
    </div>

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
          <span class="bold-text line-reveal">l'impact de <span class="highlight-yellow">vos lois</span></span>
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
            <span class="btn-text">Lancer une simulation</span>
            <span class="btn-icon-circle">
              <svg class="btn-arrow-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="#000000" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </button>
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
const parallaxX = ref(0)
const parallaxY = ref(0)

const handleMouseMove = (e) => {
  mouseX.value = e.clientX
  mouseY.value = e.clientY
  if (typeof window !== 'undefined') {
    parallaxX.value = (e.clientX / window.innerWidth - 0.5) * 2
    parallaxY.value = (e.clientY / window.innerHeight - 0.5) * 2
  }
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
  padding: 15px 40px 20px;
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
  margin: 50px auto 50px;
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
  font-size: 54px;
  font-weight: 400;
  line-height: 1.15;
  letter-spacing: -1.5px;
  color: #000000;
  text-align: center;
  margin: 0 auto;
}

.bold-text { font-weight: 700; }

.highlight-yellow {
  background-color: #FFC800;
  color: #000000;
  padding: 2px 14px;
  border-radius: 4px;
  display: inline-block;
}

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
  position: relative;
  background: #000000;
  color: #FFFFFF;
  border: none;
  padding: 6px 6px 6px 28px;
  border-radius: 9999px;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 18px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
  transition: all 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: 20;
  overflow: hidden;
}

/* Framer Motion style light sweep shimmer effect */
.btn-black-pill::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(120deg, transparent 20%, rgba(255, 255, 255, 0.2) 50%, transparent 80%);
  transition: left 0.65s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 1;
  pointer-events: none;
}

.btn-black-pill:hover::after {
  left: 100%;
}

.btn-text {
  position: relative;
  z-index: 2;
  transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.btn-black-pill:hover .btn-text {
  transform: translateX(6px);
}

.btn-black-pill:hover {
  background: #262626;
  transform: translateY(-5px) scale(1.025);
  box-shadow: 0 24px 50px rgba(0, 0, 0, 0.35);
}

.btn-black-pill:active {
  transform: translateY(-1px) scale(0.985);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.22);
  transition: all 0.15s ease;
}

.btn-icon-circle {
  position: relative;
  z-index: 2;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #FFFFFF;
  color: #000000;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.btn-black-pill:hover .btn-icon-circle {
  transform: scale(1.15) rotate(-12deg);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
}

.btn-arrow, .btn-arrow-svg {
  display: inline-block;
  transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.btn-black-pill:hover .btn-arrow, .btn-black-pill:hover .btn-arrow-svg {
  transform: translateX(3px) scale(1.1);
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

/* ==========================================
   STACKED FLOATING 3D DOODLE STICKERS LAYER (BOTTOM)
   ========================================== */
.doodles-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
  overflow: hidden;
}

.doodle-wrapper {
  position: absolute;
  transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  will-change: transform;
}

.doodle-img {
  pointer-events: auto;
  max-width: 100%;
  height: auto;
  cursor: pointer;
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), filter 0.35s ease, opacity 0.35s ease;
  will-change: transform, filter;
}

/* DEPTH STYLING & BLUR EFFECTS */
.depth-bg {
  filter: blur(3.5px) drop-shadow(0 10px 20px rgba(0, 0, 0, 0.08));
  opacity: 0.55;
}

.depth-mid {
  filter: blur(1.5px) drop-shadow(0 15px 25px rgba(0, 0, 0, 0.12));
  opacity: 0.82;
}

.depth-fg {
  filter: blur(0px) drop-shadow(0 20px 35px rgba(0, 0, 0, 0.18));
  opacity: 1.0;
}

/* POP TO FRONT ON HOVER */
.doodle-img:hover {
  transform: scale(1.22) rotate(0deg) !important;
  filter: blur(0px) drop-shadow(0 28px 50px rgba(0, 0, 0, 0.3)) !important;
  opacity: 1 !important;
  z-index: 100;
}

/* POSITIONS RIGHT AT THE VERY BOTTOM (TOUT EN BAS, CONTINUOUS OVERLAPPING CHAIN) */
.sticker-bg-1  { left: 2%;  bottom: -2%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-fg-1  { left: 9%;  bottom: 4%;  width: clamp(155px, 14vw, 195px); z-index: 5; }
.sticker-mid-1 { left: 16%; bottom: 1%;  width: clamp(145px, 13vw, 180px); z-index: 3; }
.sticker-bg-2  { left: 23%; bottom: -3%; width: clamp(135px, 12vw, 170px); z-index: 2; }
.sticker-fg-2  { left: 31%; bottom: 6%;  width: clamp(160px, 15vw, 200px); z-index: 6; }
.sticker-mid-2 { left: 38%; bottom: 2%;  width: clamp(150px, 13vw, 185px); z-index: 4; }
.sticker-bg-3  { left: 46%; bottom: -2%; width: clamp(135px, 12vw, 170px); z-index: 2; }
.sticker-fg-3  { left: 54%; bottom: 5%;  width: clamp(160px, 15vw, 200px); z-index: 6; }
.sticker-mid-3 { left: 62%; bottom: 0%;  width: clamp(150px, 13vw, 185px); z-index: 4; }
.sticker-bg-4  { left: 70%; bottom: -3%; width: clamp(135px, 12vw, 170px); z-index: 2; }
.sticker-fg-4  { left: 78%; bottom: 4%;  width: clamp(155px, 14vw, 195px); z-index: 5; }
/* POSITIONS FILLING THE RED U-SHAPED ZONE (36 ULTRA-DENSE STACKED STICKERS) */
/* Left Mountain (Climbing vertically along the left corner) */
.sticker-bg-1  { left: -4%; bottom: -4%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-1 { left: -2%; bottom: 6%;  width: clamp(135px, 12vw, 170px); z-index: 3; }
.sticker-fg-1  { left: 0%;  bottom: 16%; width: clamp(140px, 13vw, 175px); z-index: 5; }
.sticker-bg-2  { left: -3%; bottom: 25%; width: clamp(125px, 11vw, 160px); z-index: 2; }
.sticker-mid-2 { left: 3%;  bottom: 19%; width: clamp(135px, 12vw, 170px); z-index: 4; }
.sticker-fg-2  { left: 5%;  bottom: 8%;  width: clamp(145px, 13vw, 180px); z-index: 6; }

/* Center Bottom Floor (Dense overlapping bed across the bottom) */
.sticker-bg-3  { left: 9%;  bottom: -5%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-3 { left: 13%; bottom: -1%; width: clamp(140px, 13vw, 175px); z-index: 4; }
.sticker-fg-3  { left: 17%; bottom: 2%;  width: clamp(145px, 13vw, 180px); z-index: 6; }
.sticker-bg-4  { left: 21%; bottom: -6%; width: clamp(125px, 11vw, 160px); z-index: 2; }
.sticker-mid-4 { left: 25%; bottom: -2%; width: clamp(135px, 12vw, 170px); z-index: 3; }
.sticker-fg-4  { left: 30%; bottom: 1%;  width: clamp(145px, 13vw, 180px); z-index: 5; }
.sticker-bg-5  { left: 34%; bottom: -5%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-5 { left: 39%; bottom: -1%; width: clamp(140px, 13vw, 175px); z-index: 4; }
.sticker-fg-5  { left: 44%; bottom: 2%;  width: clamp(145px, 13vw, 180px); z-index: 6; }
.sticker-bg-6  { left: 48%; bottom: -6%; width: clamp(125px, 11vw, 160px); z-index: 2; }
.sticker-mid-6 { left: 53%; bottom: -2%; width: clamp(135px, 12vw, 170px); z-index: 3; }
.sticker-fg-6  { left: 57%; bottom: 1%;  width: clamp(145px, 13vw, 180px); z-index: 5; }
.sticker-bg-7  { left: 62%; bottom: -5%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-7 { left: 66%; bottom: -1%; width: clamp(140px, 13vw, 175px); z-index: 4; }
.sticker-fg-7  { left: 71%; bottom: 3%;  width: clamp(145px, 13vw, 180px); z-index: 6; }

/* Right Mountain (Climbing vertically along the right corner) */
.sticker-bg-8  { left: 78%; bottom: -3%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-8 { left: 83%; bottom: 6%;  width: clamp(135px, 12vw, 170px); z-index: 3; }
.sticker-fg-8  { left: 88%; bottom: 16%; width: clamp(145px, 13vw, 180px); z-index: 5; }
.sticker-bg-9  { left: 91%; bottom: 25%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-9 { left: 87%; bottom: 19%; width: clamp(140px, 13vw, 175px); z-index: 4; }
.sticker-fg-9  { left: 84%; bottom: 8%;  width: clamp(150px, 14vw, 185px); z-index: 6; }

/* Extra Reinforcement Layers (Glued directly over the mounds & floor) */
.sticker-bg-10  { left: 2%;  bottom: 11%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-10 { left: 23%; bottom: 0%;  width: clamp(135px, 12vw, 170px); z-index: 3; }
.sticker-fg-10  { left: 41%; bottom: 1%;  width: clamp(145px, 13vw, 180px); z-index: 5; }
.sticker-bg-11  { left: 59%; bottom: -3%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-11 { left: 80%; bottom: 11%; width: clamp(135px, 12vw, 170px); z-index: 4; }
.sticker-fg-11  { left: 89%; bottom: 21%; width: clamp(140px, 13vw, 175px); z-index: 6; }
.sticker-bg-12  { left: 7%;  bottom: -4%; width: clamp(125px, 11vw, 160px); z-index: 2; }
.sticker-mid-12 { left: 49%; bottom: -3%; width: clamp(135px, 12vw, 170px); z-index: 3; }
.sticker-fg-12  { left: 86%; bottom: -1%; width: clamp(145px, 13vw, 180px); z-index: 5; }

/* Gap Fillers for Red Zones (Bottom left, bottom center, bottom right gaps) */
.sticker-bg-13  { left: -3%;  bottom: -4%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-13 { left: 4%;   bottom: -5%; width: clamp(135px, 12vw, 170px); z-index: 4; }
.sticker-fg-13  { left: 11%;  bottom: -3%; width: clamp(145px, 13vw, 180px); z-index: 6; }
.sticker-bg-14  { left: 32%;  bottom: -5%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-14 { left: 43%;  bottom: -4%; width: clamp(135px, 12vw, 170px); z-index: 3; }
.sticker-fg-14  { left: 51%;  bottom: -2%; width: clamp(145px, 13vw, 180px); z-index: 5; }
.sticker-bg-15  { left: 64%;  bottom: -5%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-15 { left: 72%;  bottom: -3%; width: clamp(135px, 12vw, 170px); z-index: 4; }
.sticker-fg-15  { left: 76%;  bottom: -1%; width: clamp(145px, 13vw, 180px); z-index: 6; }
.sticker-bg-16  { left: 84%;  bottom: -5%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-16 { left: 91%;  bottom: -3%; width: clamp(135px, 12vw, 170px); z-index: 4; }
.sticker-fg-16  { left: 93%;  bottom: 4%;  width: clamp(145px, 13vw, 180px); z-index: 6; }
.sticker-bg-17  { left: 18%;  bottom: -4%; width: clamp(130px, 12vw, 165px); z-index: 2; }
.sticker-mid-17 { left: 36%;  bottom: -2%; width: clamp(135px, 12vw, 170px); z-index: 3; }
.sticker-fg-17  { left: 56%;  bottom: -3%; width: clamp(145px, 13vw, 180px); z-index: 5; }

/* LOW-AMPLITUDE CONTINUOUS ANIMATIONS (DOES NOT RISE HIGH) */
@keyframes floatLow1 {
  0%, 100% { transform: translateY(0px) rotate(-14deg) scale(0.85); }
  50% { transform: translateY(-6px) rotate(-10deg) scale(0.87); }
}
@keyframes floatLow2 {
  0%, 100% { transform: translateY(0px) rotate(16deg) scale(0.85); }
  50% { transform: translateY(-8px) rotate(12deg) scale(0.87); }
}
@keyframes floatLow3 {
  0%, 100% { transform: translateY(0px) rotate(-10deg) scale(0.92); }
  50% { transform: translateY(-7px) rotate(-6deg) scale(0.94); }
}
@keyframes floatLow4 {
  0%, 100% { transform: translateY(0px) rotate(14deg) scale(0.92); }
  50% { transform: translateY(-8px) rotate(10deg) scale(0.94); }
}

.float-low-1 { animation: floatLow1 6.5s ease-in-out infinite; }
.float-low-2 { animation: floatLow2 7.2s ease-in-out infinite 0.5s; }
.float-low-3 { animation: floatLow3 6.8s ease-in-out infinite 0.8s; }
.float-low-4 { animation: floatLow4 7.5s ease-in-out infinite 0.3s; }

@media (max-width: 1024px) {
  .sticker-bg-1, .sticker-bg-3, .sticker-bg-5, .sticker-mid-2, .sticker-mid-5 { display: none; }
}

@media (max-width: 640px) {
  .doodles-layer .doodle-wrapper:not(.sticker-fg-1):not(.sticker-fg-4) { display: none; }
  .sticker-fg-1 { bottom: -2%; left: 2%; width: 110px; }
  .sticker-fg-4 { bottom: -2%; right: 2%; width: 110px; }
}
</style>
