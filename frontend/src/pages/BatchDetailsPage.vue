<template>
  <div>
    <div v-if="initialLoading" class="space-y-4">
      <div class="h-8 w-64 animate-pulse rounded bg-gray-200" />
      <div class="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <div v-for="i in 3" :key="i" class="h-24 animate-pulse rounded-xl bg-white shadow-sm" />
      </div>
      <div class="h-64 animate-pulse rounded-xl bg-white shadow-sm" />
    </div>

    <div
      v-else-if="fetchError"
      class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
    >
      {{ fetchError }}
    </div>

    <template v-else-if="batch">
      <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 class="text-xl font-semibold text-gray-900">
            Batch {{ batch.batch_id.slice(0, 16) }}...
          </h2>
          <p class="mt-0.5 text-sm text-gray-500">
            Created {{ formatDate(batch.created_at) }}
          </p>
        </div>
        <span
          class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium"
          :class="statusBadgeClass(batch.status)"
        >
          <span v-if="isProcessing(batch.status)" class="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
          {{ batch.status }}
        </span>
      </div>

      <div class="mb-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div class="mb-3 flex items-center justify-between text-sm">
          <span class="font-medium text-gray-700">Processing Progress</span>
          <span class="text-gray-500">{{ batch.completed_files }}/{{ batch.total_files }} files</span>
        </div>
        <div class="overflow-hidden rounded-full bg-gray-200">
          <div
            class="h-2.5 rounded-full transition-all duration-500 ease-out"
            :class="progressBarClass"
            :style="{ width: `${progressPercent}%` }"
          />
        </div>
        <div class="mt-3 flex gap-4 text-xs text-gray-500">
          <span>{{ statusCount('SUCCESS') }} succeeded</span>
          <span>{{ statusCount('FAILED') }} failed</span>
          <span>{{ statusCount('QUEUED') + statusCount('PDF_CONVERSION') + statusCount('AI_PROCESSING') }} in progress</span>
        </div>
      </div>

      <div v-if="pollingActive" class="mb-4 flex items-center gap-2 text-xs text-amber-600">
        <span class="h-2 w-2 animate-pulse rounded-full bg-amber-500" />
        Auto-refreshing every 2s
      </div>

      <div class="mb-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50">
              <svg class="h-5 w-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-900">Excel Export</p>
              <p class="text-xs text-gray-500">
                {{ batch.excel_exported_at ? `Last generated ${formatDate(batch.excel_exported_at)}` : 'Not yet generated' }}
              </p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span v-if="downloadSuccess" class="flex items-center gap-1.5 text-sm text-green-600">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
              Downloaded
            </span>
            <button
              type="button"
              class="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50"
              :class="downloading ? 'bg-gray-100 text-gray-400' : 'bg-indigo-600 text-white hover:bg-indigo-700'"
              :disabled="downloading || downloadSuccess"
              @click="handleDownload"
            >
              <svg v-if="downloading" class="h-4 w-4 animate-spin" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
              <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
              {{ downloading ? 'Generating…' : 'Download XLSX' }}
            </button>
          </div>
        </div>
        <div v-if="downloadError" class="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {{ downloadError }}
        </div>
        <div v-if="retryError" class="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {{ retryError }}
        </div>
      </div>

      <div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">File</th>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Status</th>
              <th class="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="doc in batch.documents" :key="doc.document_id" class="hover:bg-gray-50">
              <td class="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                {{ doc.filename }}
              </td>
              <td class="whitespace-nowrap px-6 py-4">
                <span
                  class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                  :class="statusBadgeClass(doc.status)"
                  :title="doc.status === 'FAILED' ? (doc.error_message || 'Unknown error') : undefined"
                >
                  <span v-if="isProcessing(doc.status)" class="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
                  {{ statusLabel(doc.status) }}
                </span>
              </td>
              <td class="whitespace-nowrap px-6 py-4 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    v-if="doc.status === 'FAILED'"
                    type="button"
                    :disabled="retrying[doc.document_id]"
                    class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                    @click="retryDocument(doc.document_id)"
                  >
                    {{ retrying[doc.document_id] ? 'Retrying...' : 'Retry' }}
                  </button>
                  <router-link
                    v-if="doc.status === 'SUCCESS'"
                    :to="`/document/${doc.document_id}`"
                    class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
                  >
                    Review
                  </router-link>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-6 rounded-xl border border-dashed border-gray-300 bg-white p-5 shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50">
              <svg class="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-900">Add More Documents</p>
              <p class="text-xs text-gray-500">Upload additional PDFs to this batch</p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span v-if="addFiles.length > 0" class="text-sm text-gray-600">{{ addFiles.length }} file{{ addFiles.length === 1 ? '' : 's' }} selected</span>
            <button
              type="button"
              class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              @click="triggerFilePicker"
            >
              Choose Files
            </button>
            <button
              v-if="addFiles.length > 0"
              type="button"
              :disabled="addingFiles"
              class="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-60"
              @click="uploadToBatch"
            >
              <svg v-if="addingFiles" class="h-4 w-4 animate-spin" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
              {{ addingFiles ? 'Uploading...' : 'Upload' }}
            </button>
            <button
              v-if="addFiles.length > 0"
              type="button"
              :disabled="addingFiles"
              class="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50"
              @click="clearAddFiles"
            >
              Clear
            </button>
          </div>
        </div>
        <div v-if="addFiles.length > 0" class="mt-3 space-y-1">
          <div v-for="(f, i) in addFiles" :key="i" class="flex items-center justify-between rounded bg-gray-50 px-3 py-1.5 text-sm">
            <span class="truncate text-gray-700">{{ f.name }}</span>
            <span class="ml-2 shrink-0 text-xs text-gray-400">{{ (f.size / 1024).toFixed(1) }} KB</span>
          </div>
        </div>
        <div v-if="addFilesError" class="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {{ addFilesError }}
        </div>
        <div v-if="addFilesSuccess" class="mt-3 rounded border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
          {{ addFilesSuccess }}
        </div>
        <input
          ref="fileInputRef"
          type="file"
          multiple
          accept=".pdf,application/pdf"
          class="hidden"
          @change="onAddFilesChange"
        >
      </div>

      <div v-if="!batch.documents?.length" class="mt-6 rounded-xl border border-gray-200 bg-white p-8 text-center">
        <p class="text-sm text-gray-500">No documents in this batch.</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { API_BASE } from '@/config'
import type { BatchDetail } from '@/stores/dashboard'

const route = useRoute()

const batch = ref<BatchDetail | null>(null)
const initialLoading = ref(true)
const fetchError = ref<string | null>(null)
const pollingActive = ref(false)
const retrying = ref<Record<string, boolean>>({})
const retryError = ref<string | null>(null)
const downloading = ref(false)
const downloadSuccess = ref(false)
const downloadError = ref<string | null>(null)
const addFiles = ref<File[]>([])
const addingFiles = ref(false)
const addFilesError = ref<string | null>(null)
const addFilesSuccess = ref<string | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

let pollTimer: ReturnType<typeof setInterval> | null = null

const progressPercent = computed(() => {
  if (!batch.value || batch.value.total_files === 0) return 0
  return Math.round((batch.value.completed_files / batch.value.total_files) * 100)
})

const progressBarClass = computed(() => {
  if (!batch.value) return 'bg-gray-400'
  if (batch.value.status === 'FAILED') return 'bg-red-500'
  if (batch.value.status === 'SUCCESS') return 'bg-green-500'
  return 'bg-indigo-500'
})

const terminalStatuses = new Set(['SUCCESS', 'FAILED'])

function isProcessing(status: string) {
  return !terminalStatuses.has(status)
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    QUEUED: 'Queued',
    PDF_CONVERSION: 'Converting PDF',
    AI_PROCESSING: 'Processing',
    SUCCESS: 'Success',
    FAILED: 'Failed',
  }
  return map[status] ?? status
}

function statusBadgeClass(status: string) {
  const map: Record<string, string> = {
    SUCCESS: 'bg-green-100 text-green-800',
    FAILED: 'bg-red-100 text-red-800',
    AI_PROCESSING: 'bg-amber-100 text-amber-800',
    PDF_CONVERSION: 'bg-blue-100 text-blue-800',
    QUEUED: 'bg-gray-100 text-gray-600',
  }
  return map[status] ?? 'bg-gray-100 text-gray-600'
}

function statusCount(status: string): number {
  if (!batch.value?.status_counts) return 0
  return batch.value.status_counts[status] ?? 0
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function fetchBatch() {
  try {
    const res = await axios.get(`${API_BASE}/batch/${route.params.id}`)
    batch.value = res.data as BatchDetail
    fetchError.value = null
    downloadError.value = null

    if (terminalStatuses.has(batch.value.status)) {
      stopPolling()
    }
  } catch (err: any) {
    if (!initialLoading.value) {
      fetchError.value = err?.response?.data?.detail || err.message || 'Failed to fetch batch'
    }
    stopPolling()
  } finally {
    initialLoading.value = false
  }
}

function startPolling() {
  if (pollTimer) return
  pollingActive.value = true
  pollTimer = setInterval(fetchBatch, 2500)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  pollingActive.value = false
}

async function retryDocument(documentId: string) {
  retrying.value[documentId] = true
  retryError.value = null
  try {
    await axios.post(`${API_BASE}/document/${documentId}/retry`)
    await fetchBatch()
    startPolling()
  } catch (err: any) {
    retryError.value = err?.response?.data?.detail || 'Retry failed'
  } finally {
    retrying.value[documentId] = false
  }
}

function triggerFilePicker() {
  fileInputRef.value?.click()
}

function onAddFilesChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    const files = Array.from(input.files).filter(
      (f) => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'),
    )
    addFiles.value = files
    addFilesError.value = null
    addFilesSuccess.value = null
  }
  input.value = ''
}

async function uploadToBatch() {
  if (!addFiles.value.length || addingFiles.value) return
  addingFiles.value = true
  addFilesError.value = null
  addFilesSuccess.value = null

  try {
    const form = new FormData()
    for (const f of addFiles.value) {
      form.append('files', f)
    }
    await axios.post(`${API_BASE}/batch/${route.params.id}/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    addFilesSuccess.value = `${addFiles.value.length} file${addFiles.value.length === 1 ? '' : 's'} added successfully`
    addFiles.value = []
    await fetchBatch()
    startPolling()
  } catch (err: any) {
    addFilesError.value = err?.response?.data?.detail || 'Upload failed'
  } finally {
    addingFiles.value = false
  }
}

function clearAddFiles() {
  addFiles.value = []
  addFilesError.value = null
  addFilesSuccess.value = null
}

async function handleDownload() {
  downloading.value = true
  downloadError.value = null
  try {
    const res = await axios.get(`${API_BASE}/batch/${route.params.id}/download-excel`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    const disposition = res.headers['content-disposition']
    const match = disposition?.match(/filename="?(.+?)"?$/)
    link.download = match?.[1] ?? `batch-${route.params.id}.xlsx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    downloadSuccess.value = true
    await fetchBatch()
  } catch (err: any) {
    if (err?.response?.data instanceof Blob) {
      try {
        const text = await err.response.data.text()
        const json = JSON.parse(text)
        downloadError.value = json?.detail || text
      } catch {
        downloadError.value = 'Download failed'
      }
    } else {
      downloadError.value = err?.response?.data?.detail || err?.message || 'Download failed'
    }
  } finally {
    downloading.value = false
  }
}

onMounted(async () => {
  await fetchBatch()
  if (batch.value && !terminalStatuses.has(batch.value.status)) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>
