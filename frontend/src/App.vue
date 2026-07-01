<template>
  <div id="miropolis-app" @mousemove="handleMouseMove">
    <!-- Global Animated Dynamic Geometric Grid Background Layer -->
    <div class="global-animated-grid-bg"></div>
    <div 
      class="global-interactive-grid-spotlight" 
      :style="{ '--mouse-x': `${mouseX}px`, '--mouse-y': `${mouseY}px` }"
    ></div>
    <div class="global-grid-fade-overlay"></div>

    <!-- App Views Content -->
    <div class="app-views-wrapper">
      <router-view v-slot="{ Component }">
        <transition name="fade-page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const mouseX = ref(-1000)
const mouseY = ref(-1000)

const handleMouseMove = (e) => {
  mouseX.value = e.clientX
  mouseY.value = e.clientY
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg-white: #FFFFFF;
  --bg-subtle: #F8FAFC;
  --bg-card: #FFFFFF;
  
  --text-black: #000000;
  --text-secondary: #475569;
  --text-muted: #94A3B8;
  
  --grid-line: #E2E8F0;
  --grid-line-dashed: rgba(15, 23, 42, 0.12);
  
  --border-subtle: #E2E8F0;
  --border-dark: #000000;
  
  --radius-sm: 8px;
  --radius-md: 16px;
  --radius-lg: 24px;
  --radius-pill: 9999px;
  --transition-smooth: cubic-bezier(0.16, 1, 0.3, 1);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body, html {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background-color: #FAFAFB;
  color: var(--text-black);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;
}

#miropolis-app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* ==========================================
   GLOBAL DYNAMIC ANIMATED GRID BACKGROUND
   ========================================== */
.global-animated-grid-bg {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(to right, rgba(15, 23, 42, 0.045) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(15, 23, 42, 0.045) 1px, transparent 1px);
  background-size: 40px 40px;
  animation: globalGridScroll 30s linear infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes globalGridScroll {
  0% { background-position: 0px 0px; }
  100% { background-position: -80px -80px; }
}

.global-interactive-grid-spotlight {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(to right, rgba(15, 23, 42, 0.16) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(15, 23, 42, 0.16) 1px, transparent 1px);
  background-size: 40px 40px;
  animation: globalGridScroll 30s linear infinite;
  mask-image: radial-gradient(
    320px circle at var(--mouse-x) var(--mouse-y),
    rgba(0, 0, 0, 1) 0%,
    transparent 100%
  );
  -webkit-mask-image: radial-gradient(
    320px circle at var(--mouse-x) var(--mouse-y),
    rgba(0, 0, 0, 1) 0%,
    transparent 100%
  );
  pointer-events: none;
  z-index: 1;
}

.global-grid-fade-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 50% 30%, transparent 20%, rgba(250, 250, 251, 0.88) 95%);
  pointer-events: none;
  z-index: 1;
}

/* Ensure all view wrappers allow the global animated background to show through */
.app-views-wrapper {
  position: relative;
  z-index: 2;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.landing-page-white,
.wizard-portal-white,
.main-view,
.simulation-view,
.simulation-run-view,
.report-view,
.interaction-view {
  background: transparent !important;
}

/* Page transitions */
.fade-page-enter-active,
.fade-page-leave-active {
  transition: opacity 0.25s var(--transition-smooth), transform 0.25s var(--transition-smooth);
}

.fade-page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.fade-page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

button {
  font-family: inherit;
  outline: none;
}
</style>
