<template>
  <header class="navbar-minimal" role="banner">
    <div class="nav-container">
      <!-- Left spacer to maintain exact visual balance -->
      <div class="nav-left"></div>

      <!-- Center Brand Logo & Name -->
      <div class="nav-center-brand" @click="$router.push('/')">
        <img src="../assets/logo/miropolis-logo-black.png" alt="MiroPolis Logo" class="brand-logo" />
        <span class="brand-name">MiroPolis.</span>
      </div>

      <!-- Right Minimalist Action -->
      <div class="nav-right">
        <button class="btn-minimal-create" @click="$router.push('/process/new')">
          <span>Nouvelle simulation</span>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
</script>

<style scoped>
.navbar-minimal {
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  height: 72px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
  transition: all 0.2s ease;
}

.nav-container {
  max-width: 1360px;
  height: 100%;
  margin: 0 auto;
  padding: 0 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
}

/* Brand Section Centered */
.nav-center-brand {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
}

.brand-logo {
  height: 28px;
  width: auto;
  object-fit: contain;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.nav-center-brand:hover .brand-logo {
  transform: scale(1.06);
}

.brand-name {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-weight: 700;
  font-size: 20px;
  color: #000000;
  letter-spacing: -0.5px;
}

/* Right Action Button */
.nav-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-left: auto;
}

.btn-minimal-create {
  background: #000000;
  color: #FFFFFF;
  border: none;
  padding: 10px 20px;
  border-radius: 9999px;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.btn-minimal-create:hover {
  background: #1E293B;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}

@media (max-width: 768px) {
  .nav-container { padding: 0 20px; }
}

@media (max-width: 640px) {
  .nav-center-brand {
    position: static;
    transform: none;
  }
}
</style>
