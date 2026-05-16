<template>
  <div
    class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
  >
    <div class="flex items-center gap-4">
      <div
        class="flex h-12 w-12 items-center justify-center rounded-lg"
        :class="iconBg"
      >
        <component :is="icon" class="h-6 w-6" :class="iconColor" />
      </div>
      <div>
        <p class="text-sm font-medium text-gray-500">{{ label }}</p>
        <p v-if="!loading" class="text-2xl font-bold text-gray-900">{{ value }}</p>
        <div v-else class="mt-1 h-8 w-16 animate-pulse rounded bg-gray-200" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { h, computed } from 'vue'

const props = defineProps<{
  label: string
  value: number | string
  icon: any
  color: 'indigo' | 'amber' | 'green' | 'red'
  loading?: boolean
}>()

const iconBg = computed(() => {
  const map: Record<string, string> = {
    indigo: 'bg-indigo-50',
    amber: 'bg-amber-50',
    green: 'bg-green-50',
    red: 'bg-red-50',
  }
  return map[props.color]
})

const iconColor = computed(() => {
  const map: Record<string, string> = {
    indigo: 'text-indigo-600',
    amber: 'text-amber-600',
    green: 'text-green-600',
    red: 'text-red-600',
  }
  return map[props.color]
})
</script>
