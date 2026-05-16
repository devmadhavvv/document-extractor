<template>
  <header class="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6 shadow-sm">
    <div>
      <h1 class="text-lg font-semibold text-gray-900">{{ pageTitle }}</h1>
      <p v-if="pageSubtitle" class="text-sm text-gray-500">{{ pageSubtitle }}</p>
    </div>
    <div class="flex items-center gap-4">
      <button
        type="button"
        class="rounded-lg border border-gray-200 bg-white p-2 text-gray-500 hover:bg-gray-50 hover:text-gray-700"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      </button>
      <div class="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-sm font-medium text-indigo-700">
        A
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const titles: Record<string, { title: string; subtitle: string }> = {
  dashboard: { title: 'Dashboard', subtitle: 'Overview of all onboarding batches' },
  'batch-details': { title: 'Batch Details', subtitle: 'View and manage batch documents' },
  'review-document': { title: 'Review Document', subtitle: 'Verify extracted document data' },
}

const pageTitle = computed(() => {
  const name = route.name as string
  return titles[name]?.title ?? 'Onboarding HRMS'
})

const pageSubtitle = computed(() => {
  const name = route.name as string
  return titles[name]?.subtitle ?? ''
})
</script>
