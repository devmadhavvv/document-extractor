<template>
  <div class="mx-auto max-w-2xl">
    <h2 class="mb-1 text-xl font-semibold text-gray-900">Upload Batch</h2>
    <p class="mb-6 text-sm text-gray-500">Select PDF documents to create a new onboarding batch.</p>

    <div class="space-y-5">
      <UploadDropzone @files-added="onFilesAdded" />

      <div v-if="invalidFiles.length" class="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
        <p class="font-medium">Invalid files skipped:</p>
        <ul class="mt-1 list-inside list-disc">
          <li v-for="f in invalidFiles" :key="f.name">{{ f.name }}</li>
        </ul>
      </div>

      <UploadFileList
        :files="validFiles"
        @remove-file="removeFile"
      />

      <div v-if="validFiles.length" class="flex items-center gap-4">
        <button
          type="button"
          :disabled="uploading"
          class="flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
          @click="startUpload"
        >
          <svg
            v-if="uploading"
            class="h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {{ uploading ? 'Uploading...' : `Upload ${validFiles.length} file${validFiles.length === 1 ? '' : 's'}` }}
        </button>

        <button
          type="button"
          :disabled="uploading"
          class="text-sm font-medium text-gray-500 hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
          @click="clearAll"
        >
          Clear all
        </button>
      </div>

      <div
        v-if="uploadProgress > 0 && uploadProgress < 100"
        class="overflow-hidden rounded-full bg-gray-200"
      >
        <div
          class="h-2 rounded-full bg-indigo-600 transition-all duration-300"
          :style="{ width: `${uploadProgress}%` }"
        />
      </div>

      <div
        v-if="uploadError"
        class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
      >
        {{ uploadError }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { API_BASE } from '@/config'
import UploadDropzone from '@/components/UploadDropzone.vue'
import UploadFileList from '@/components/UploadFileList.vue'

const router = useRouter()

const selectedFiles = ref<File[]>([])
const invalidFiles = ref<{ name: string }[]>([])
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadError = ref<string | null>(null)

const validFiles = computed(() =>
  selectedFiles.value.filter((f) => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')),
)

function isPDF(file: File) {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}

function onFilesAdded(files: File[]) {
  const bad: { name: string }[] = []
  const good: File[] = []

  for (const f of files) {
    if (isPDF(f)) {
      good.push(f)
    } else {
      bad.push({ name: f.name })
    }
  }

  if (bad.length) {
    invalidFiles.value = [...invalidFiles.value, ...bad]
  }

  if (good.length) {
    const existing = new Set(selectedFiles.value.map((f) => `${f.name}-${f.size}`))
    const deduped = good.filter((f) => !existing.has(`${f.name}-${f.size}`))
    selectedFiles.value = [...selectedFiles.value, ...deduped]
  }
}

function removeFile(index: number) {
  selectedFiles.value.splice(index, 1)
}

function clearAll() {
  selectedFiles.value = []
  invalidFiles.value = []
  uploadError.value = null
  uploadProgress.value = 0
}

async function startUpload() {
  if (!validFiles.value.length || uploading.value) return

  uploading.value = true
  uploadProgress.value = 0
  uploadError.value = null

  try {
    const form = new FormData()
    for (const file of validFiles.value) {
      form.append('files', file)
    }

    const { data } = await axios.post(`${API_BASE}/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total) {
          uploadProgress.value = Math.round((e.loaded / e.total) * 100)
        }
      },
    })

    router.push(`/batch/${data.batch_id}`)
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err.message || 'Upload failed'
    uploadError.value = msg
  } finally {
    uploading.value = false
  }
}
</script>
