<template>
  <div class="flex h-screen overflow-hidden bg-gray-50">
    <AppSidebar />
    <div class="flex flex-1 flex-col overflow-hidden">
      <AppNavbar />
      <main class="flex-1 overflow-y-auto p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/AppSidebar.vue'
import AppNavbar from '@/components/AppNavbar.vue'
</script>
