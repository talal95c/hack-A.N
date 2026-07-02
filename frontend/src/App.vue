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

/* ==========================================
   GLOBAL LANDING PAGE AESTHETICS (CARRIED OVER TO ALL PAGES)
   ========================================== */

/* CAD Architectural Dimension Badges Global */
.cad-dimension {
  display: inline-flex !important;
  align-items: center;
  gap: 10px;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px;
  color: #64748B;
  letter-spacing: 0.5px;
  padding: 4px 14px !important;
  border-radius: var(--radius-pill) !important;
  background: rgba(255, 255, 255, 0.8) !important;
  backdrop-filter: blur(8px);
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
  transition: all 0.25s ease;
}

.cad-dimension:hover {
  background: #FFFFFF !important;
  border-color: #000000 !important;
  color: #000000 !important;
}

/* Highlight Yellow & Blue Global Tokens */
.highlight-yellow {
  background-color: #FFC800;
  color: #000000;
  padding: 2px 14px;
  border-radius: 4px;
  display: inline-block;
  font-weight: 700;
}

.highlight-blue {
  background-color: #2563EB;
  color: #FFFFFF;
  padding: 2px 14px;
  border-radius: 4px;
  display: inline-block;
  font-weight: 700;
}

/* Sleek Wireframe Boxes Global Glassmorphism */
.wireframe-box {
  background: rgba(255, 255, 255, 0.88) !important;
  backdrop-filter: blur(12px);
  border: 1px solid #E2E8F0 !important;
  border-radius: 24px !important;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.035) !important;
  transition: all 0.25s ease;
}

.wireframe-box:hover {
  border-color: #CBD5E1 !important;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.065) !important;
}

/* Global Typography Enforcement matching Landing Page */
.main-view,
.main-view *,
.simulation-view,
.simulation-view *,
.simulation-run-view,
.simulation-run-view *,
.report-view,
.report-view *,
.interaction-view,
.interaction-view *,
.app-header,
.app-header *,
.content-area,
.content-area * {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

.brand,
.brand-name,
.step-num,
.sec-num,
code,
pre,
.mono,
.mono-font,
.uuid,
[class*="code"],
[class*="mono"] {
  font-family: 'JetBrains Mono', monospace !important;
}

/* Hide Technical API Note Texts Everywhere */
.api-note {
  display: none !important;
}

/* Brand Group Matching Landing Page Exactly */
.brand-group {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  cursor: pointer !important;
  user-select: none !important;
}

.brand-group .brand-logo {
  height: 28px !important;
  width: auto !important;
  object-fit: contain !important;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.brand-group:hover .brand-logo {
  transform: scale(1.06) !important;
}

.brand-group .brand-name {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important;
  font-size: 20px !important;
  color: #000000 !important;
  letter-spacing: -0.5px !important;
}

/* Global Switch Pill Buttons Matching Landing Page */
.view-switcher {
  border-radius: 9999px !important;
  background: #F1F5F9 !important;
  border: 1px solid #E2E8F0 !important;
  padding: 4px !important;
  gap: 4px !important;
}

.switch-btn {
  border-radius: 9999px !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 600 !important;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.switch-btn.active {
  background: #000000 !important;
  color: #FFFFFF !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}
</style>
