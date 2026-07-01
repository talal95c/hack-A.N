<template>
  <div class="view-page">
    <MiroNavbar />
    <main class="page-main">
      <AdminUserManagement />
    </main>
  </div>
</template>

<script setup>
import MiroNavbar from '../components/MiroNavbar.vue'
import AdminUserManagement from '../components/AdminUserManagement.vue'
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
