<template>
  <aside
    class="flex flex-col bg-white border-r border-gray-200 shadow-sm transition-all duration-300"
    :class="collapsed ? 'w-16' : 'w-64'"
  >
    <div class="flex h-16 items-center border-b border-gray-200 px-4" :class="collapsed ? 'justify-center' : 'gap-2 justify-between'">
      <div class="flex items-center gap-2 min-w-0">
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
          O
        </div>
        <span v-show="!collapsed" class="truncate text-lg font-semibold text-gray-900">Onboarding</span>
      </div>
      <button
        type="button"
        class="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="collapsed = !collapsed"
      >
        <svg v-if="collapsed" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7"/></svg>
        <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7"/></svg>
      </button>
    </div>

    <nav class="flex-1 space-y-1 px-3 py-4">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors"
        :class="[
          isActive(item.path) ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
          collapsed ? 'justify-center px-2' : ''
        ]"
        :title="collapsed ? item.label : undefined"
      >
        <component :is="item.icon" class="h-5 w-5 shrink-0" />
        <span v-show="!collapsed" class="truncate">{{ item.label }}</span>
      </router-link>
    </nav>

    <div v-show="!collapsed" class="border-t border-gray-200 px-3 py-4">
      <div class="rounded-lg bg-gray-50 px-3 py-2.5">
        <p class="mb-1.5 text-xs font-medium text-gray-500">Gemini Model</p>
        <select
          v-model="selectedModel"
          class="w-full rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs text-gray-700 outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400"
          @change="onModelChange"
        >
          <option v-for="m in models" :key="m.value" :value="m.value">{{ m.label }}</option>
        </select>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { h, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { API_BASE } from '@/config'

const route = useRoute()
const collapsed = ref(false)
const selectedModel = ref('gemini-3.1-flash-lite')

const models = [
  { label: 'Gemini 3.1 Flash Lite', value: 'gemini-3.1-flash-lite' },
  { label: 'Gemini 3.1 Flash', value: 'gemini-3.1-flash' },
  { label: 'Gemini 2.5 Flash Lite', value: 'gemini-2.5-flash-lite' },
  { label: 'Gemini 2.5 Flash', value: 'gemini-2.5-flash' },
  { label: 'Gemini 2.0 Flash', value: 'gemini-2.0-flash' },
  { label: 'Gemini 1.5 Flash', value: 'gemini-1.5-flash' },
  { label: 'Gemini 1.5 Flash-8B', value: 'gemini-1.5-flash-8b' },
]

async function onModelChange() {
  try {
    await axios.patch(`${API_BASE}/settings/model`, { model: selectedModel.value })
  } catch {
    // non-blocking — model is optional to persist
  }
}

onMounted(async () => {
  try {
    const res = await axios.get(`${API_BASE}/settings/model`)
    selectedModel.value = res.data.model
  } catch {
    // use default
  }
})

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
