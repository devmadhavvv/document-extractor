<template>
  <div v-if="files.length" class="rounded-xl border border-gray-200 bg-white shadow-sm">
    <div class="flex items-center justify-between border-b border-gray-100 px-5 py-3">
      <p class="text-sm font-medium text-gray-700">
        {{ files.length }} file{{ files.length === 1 ? '' : 's' }} selected
      </p>
      <span class="text-xs text-gray-400">
        {{ formatTotalSize(files) }}
      </span>
    </div>

    <ul class="divide-y divide-gray-100">
      <li
        v-for="(file, index) in files"
        :key="file.name + file.size + file.lastModified"
        class="flex items-center justify-between px-5 py-3"
      >
        <div class="flex items-center gap-3 overflow-hidden">
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-50 text-red-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <div class="min-w-0">
            <p class="truncate text-sm font-medium text-gray-900">{{ file.name }}</p>
            <p class="text-xs text-gray-500">{{ formatSize(file.size) }}</p>
          </div>
        </div>

        <button
          type="button"
          class="ml-3 shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          @click="$emit('remove-file', index)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  files: File[]
}>()

defineEmits<{
  (e: 'remove-file', index: number): void
}>()

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatTotalSize(files: File[]) {
  const total = files.reduce((sum, f) => sum + f.size, 0)
  return formatSize(total)
}
</script>
