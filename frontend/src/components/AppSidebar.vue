<template>
  <aside class="flex w-64 flex-col bg-white border-r border-gray-200 shadow-sm">
    <div class="flex h-16 items-center gap-2 border-b border-gray-200 px-6">
      <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
        O
      </div>
      <span class="text-lg font-semibold text-gray-900">Onboarding</span>
    </div>

    <nav class="flex-1 space-y-1 px-3 py-4">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors"
        :class="isActive(item.path) ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'"
      >
        <component :is="item.icon" class="h-5 w-5" />
        {{ item.label }}
      </router-link>
    </nav>

    <div class="border-t border-gray-200 px-3 py-4">
      <div class="rounded-lg bg-gray-50 px-3 py-2">
        <p class="text-xs font-medium text-gray-500">API Status</p>
        <div class="mt-1 flex items-center gap-2">
          <span class="h-2 w-2 rounded-full bg-green-500" />
          <span class="text-sm text-gray-700">Connected</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { h } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const DashboardIcon = {
  render() {
    return h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
      h('rect', { x: '3', y: '3', width: '7', height: '7' }),
      h('rect', { x: '14', y: '3', width: '7', height: '7' }),
      h('rect', { x: '14', y: '14', width: '7', height: '7' }),
      h('rect', { x: '3', y: '14', width: '7', height: '7' }),
    ])
  },
}

const UploadIcon = {
  render() {
    return h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
      h('path', { d: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4' }),
      h('polyline', { points: '17 8 12 3 7 8' }),
      h('line', { x1: '12', y1: '3', x2: '12', y2: '15' }),
    ])
  },
}

const navItems = [
  { label: 'Dashboard', path: '/', icon: DashboardIcon },
  { label: 'Upload Batch', path: '/upload', icon: UploadIcon },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>
