<template>
  <div class="view-page">
    <MiroNavbar />
    <main class="page-main">
      <ScenarioLibrary />
    </main>
  </div>
</template>

<script setup>
import MiroNavbar from '../components/MiroNavbar.vue'
import ScenarioLibrary from '../components/ScenarioLibrary.vue'
</script>

<style scoped>
.view-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #FFF;
}
.page-main {
  flex: 1;
}
</style>
