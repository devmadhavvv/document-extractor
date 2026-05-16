<template>
  <div>
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
      <DashboardCard
        label="Total Batches"
        :value="store.stats.total"
        :icon="LayersIcon"
        color="indigo"
        :loading="store.loading"
      />
      <DashboardCard
        label="Processing"
        :value="store.stats.processing"
        :icon="ClockIcon"
        color="amber"
        :loading="store.loading"
      />
      <DashboardCard
        label="Completed"
        :value="store.stats.completed"
        :icon="CheckIcon"
        color="green"
        :loading="store.loading"
      />
      <DashboardCard
        label="Failed"
        :value="store.stats.failed"
        :icon="XIcon"
        color="red"
        :loading="store.loading"
      />
    </div>

    <div class="mt-8">
      <h2 class="mb-4 text-lg font-semibold text-gray-900">Recent Uploads</h2>

      <div v-if="store.loading" class="space-y-3">
        <div v-for="i in 4" :key="i" class="h-16 animate-pulse rounded-xl bg-white shadow-sm" />
      </div>

      <div
        v-else-if="store.error"
        class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
      >
        {{ store.error }}
      </div>

      <div v-else-if="store.recentBatches.length === 0" class="rounded-xl border border-gray-200 bg-white p-8 text-center">
        <p class="text-sm text-gray-500">No batches uploaded yet.</p>
        <router-link to="/upload" class="mt-2 inline-block text-sm font-medium text-indigo-600 hover:text-indigo-500">
          Upload your first batch
        </router-link>
      </div>

      <div v-else class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Batch ID</th>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Status</th>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Files</th>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Created</th>
              <th class="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="batch in store.recentBatches.slice(0, 10)" :key="batch.batch_id" class="hover:bg-gray-50">
              <td class="whitespace-nowrap px-6 py-4">
                <span class="font-mono text-sm text-gray-900">{{ batch.batch_id.slice(0, 12) }}...</span>
              </td>
              <td class="whitespace-nowrap px-6 py-4">
                <span
                  class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                  :class="statusClass(batch.status)"
                >
                  {{ batch.status }}
                </span>
              </td>
              <td class="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                {{ batch.completed_files }}/{{ batch.total_files }}
              </td>
              <td class="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                {{ formatDate(batch.created_at) }}
              </td>
              <td class="whitespace-nowrap px-6 py-4 text-right">
                <router-link
                  :to="`/batch/${batch.batch_id}`"
                  class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
                >
                  View
                </router-link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted } from 'vue'
import DashboardCard from '@/components/DashboardCard.vue'
import { useDashboardStore } from '@/stores/dashboard'

const store = useDashboardStore()

const LayersIcon = {
  render() {
    return h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
      h('polygon', { points: '12 2 2 7 12 12 22 7 12 2' }),
      h('polyline', { points: '2 17 12 22 22 17' }),
      h('polyline', { points: '2 12 12 17 22 12' }),
    ])
  },
}

const ClockIcon = {
  render() {
    return h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
      h('circle', { cx: '12', cy: '12', r: '10' }),
      h('polyline', { points: '12 6 12 12 16 14' }),
    ])
  },
}

const CheckIcon = {
  render() {
    return h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
      h('path', { d: 'M22 11.08V12a10 10 0 1 1-5.93-9.14' }),
      h('polyline', { points: '22 4 12 14.01 9 11.01' }),
    ])
  },
}

const XIcon = {
  render() {
    return h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
      h('circle', { cx: '12', cy: '12', r: '10' }),
      h('line', { x1: '15', y1: '9', x2: '9', y2: '15' }),
      h('line', { x1: '9', y1: '9', x2: '15', y2: '15' }),
    ])
  },
}

function statusClass(status: string) {
  const map: Record<string, string> = {
    SUCCESS: 'bg-green-100 text-green-800',
    FAILED: 'bg-red-100 text-red-800',
    AI_PROCESSING: 'bg-amber-100 text-amber-800',
    PDF_CONVERSION: 'bg-blue-100 text-blue-800',
    QUEUED: 'bg-gray-100 text-gray-800',
  }
  return map[status] ?? 'bg-gray-100 text-gray-800'
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

onMounted(() => {
  store.fetchBatches()
})
</script>
