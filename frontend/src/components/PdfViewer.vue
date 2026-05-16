<template>
  <div class="flex h-full flex-col">
    <div class="flex items-center justify-between border-b border-gray-200 px-4 py-2">
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="rounded p-1.5 text-gray-500 hover:bg-gray-100 disabled:opacity-30"
          :disabled="zoom <= zoomPresets[0]"
          @click="zoomOut"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7"/></svg>
        </button>
        <span class="min-w-[3rem] text-center text-xs font-medium text-gray-600">{{ Math.round(zoom * 100) }}%</span>
        <button
          type="button"
          class="rounded p-1.5 text-gray-500 hover:bg-gray-100 disabled:opacity-30"
          :disabled="zoom >= zoomPresets[zoomPresets.length - 1]"
          @click="zoomIn"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM11 8v6m-3-3h6"/></svg>
        </button>
      </div>
      <select
        class="rounded border border-gray-200 px-2 py-1 text-xs focus:border-indigo-400 focus:outline-none"
        :value="zoom"
        @change="setZoom(Number(($event.target as HTMLSelectElement).value))"
      >
        <option v-for="p in zoomPresets" :key="p" :value="p">{{ p * 100 }}%</option>
      </select>
    </div>

    <div ref="scrollContainer" class="flex-1 overflow-auto bg-gray-100">
      <div v-if="loading" class="flex items-center justify-center py-24">
        <div class="flex flex-col items-center gap-3">
          <div class="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
          <p class="text-sm text-gray-500">Loading PDF…</p>
        </div>
      </div>

      <div v-else-if="loadError" class="flex items-center justify-center py-24">
        <p class="text-sm text-red-600">{{ loadError }}</p>
      </div>

      <div v-show="!loading && !loadError" :style="{ minWidth: pdfWidth + 'px' }" class="mx-auto">
        <VuePdfEmbed
          :source="source"
          :width="pdfWidth"
          class="shadow-md"
          @rendered="onRender"
          @loaded="onLoad"
          @loading-failed="onLoadFail"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'

defineProps<{
  source: string
}>()

const emit = defineEmits<{
  rendered: []
}>()

const zoomPresets = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2]
const zoom = ref(1)
const loading = ref(true)
const loadError = ref<string | null>(null)
const containerWidth = ref(800)

const scrollContainer = ref<HTMLElement | null>(null)
let resizeObserver: ResizeObserver | null = null

const pdfWidth = computed(() => Math.round(containerWidth.value * zoom.value))

function zoomIn() {
  const next = zoomPresets.find((p) => p > zoom.value)
  if (next) zoom.value = next
}

function zoomOut() {
  const prev = [...zoomPresets].reverse().find((p) => p < zoom.value)
  if (prev) zoom.value = prev
}

function setZoom(val: number) {
  zoom.value = val
}

function onLoad() {
  loading.value = false
}

function onRender() {
  emit('rendered')
}

function onLoadFail(err: Error) {
  loadError.value = err.message || 'Failed to load PDF'
  loading.value = false
}

onMounted(() => {
  if (scrollContainer.value) {
    containerWidth.value = scrollContainer.value.clientWidth - 32
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        containerWidth.value = entry.contentRect.width - 32
      }
    })
    resizeObserver.observe(scrollContainer.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})
</script>
