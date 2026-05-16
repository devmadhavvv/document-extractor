<template>
  <div
    class="relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors"
    :class="isDragOver ? 'border-indigo-400 bg-indigo-50' : 'border-gray-300 bg-white hover:border-gray-400'"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
    @click="openPicker"
  >
    <input
      ref="fileInput"
      type="file"
      multiple
      accept=".pdf,application/pdf"
      class="hidden"
      @change="onFilePick"
    />

    <div class="flex h-14 w-14 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
    </div>

    <p class="mt-4 text-sm font-medium text-gray-700">
      <span class="text-indigo-600">Click to upload</span> or drag and drop
    </p>
    <p class="mt-1 text-xs text-gray-500">PDF files only, up to 10MB each</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  (e: 'files-added', files: File[]): void
}>()

const isDragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

function openPicker() {
  fileInput.value?.click()
}

function onDragEnter() {
  isDragOver.value = true
}

function onDragOver() {
  isDragOver.value = true
}

function onDragLeave() {
  isDragOver.value = false
}

function onDrop(e: DragEvent) {
  isDragOver.value = false
  const files = Array.from(e.dataTransfer?.files ?? [])
  emit('files-added', files)
}

function onFilePick(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  if (files.length) {
    emit('files-added', files)
  }
  input.value = ''
}
</script>
