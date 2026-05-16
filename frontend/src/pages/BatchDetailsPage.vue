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
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2">
            <input
              v-if="editingName"
              ref="nameInputRef"
              v-model="batchName"
              class="rounded-lg border border-gray-300 px-3 py-1.5 text-lg font-semibold text-gray-900 outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400"
              placeholder="Batch name..."
              @blur="saveBatchName"
              @keyup.enter="saveBatchName"
              @keyup.escape="cancelEditName"
            />
            <h2 v-else class="truncate text-xl font-semibold text-gray-900">
              {{ batch.name || `Batch ${batch.batch_id.slice(0, 16)}...` }}
            </h2>
            <button
              type="button"
              class="shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              :title="editingName ? 'Save' : 'Edit batch name'"
              @click="editingName ? saveBatchName() : startEditName()"
            >
              <svg v-if="editingName" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
              <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
            </button>
          </div>
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
        <button
          type="button"
          class="flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
          @click="showDeleteBatchModal = true"
        >
          <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          Delete Batch
        </button>
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
        <div class="flex items-center justify-between border-b border-gray-100 bg-gray-50/50 px-6 py-3">
          <span class="text-xs font-medium uppercase tracking-wider text-gray-500">Documents</span>
          <button
            type="button"
            class="flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
            :disabled="!batch.documents?.length || deletingAll"
            @click="showDeleteAllModal = true"
          >
            <svg v-if="deletingAll" class="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
            <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            {{ deletingAll ? 'Deleting...' : 'Delete All' }}
          </button>
        </div>
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">File</th>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Status</th>
              <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Verified</th>
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
              <td class="whitespace-nowrap px-6 py-4">
                <span
                  v-if="doc.approved"
                  class="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700"
                >
                  <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                  Approved
                </span>
                <span
                  v-else-if="doc.status === 'SUCCESS'"
                  class="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700"
                >
                  <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  Review Required
                </span>
                <span v-else class="text-xs text-gray-400">—</span>
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
                  <button
                    type="button"
                    :disabled="deletingDocs[doc.document_id]"
                    class="rounded-lg border border-red-200 px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                    :title="'Delete ' + doc.filename"
                    @click="deleteSingleDocument(doc.document_id)"
                  >
                    <svg v-if="deletingDocs[doc.document_id]" class="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
                    <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div class="mb-4 flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50">
            <svg class="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900">Add More Documents</p>
            <p class="text-xs text-gray-500">Drag & drop PDFs or click to browse</p>
          </div>
        </div>
        <div
          class="relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors"
          :class="[
            addingFiles ? 'border-indigo-300 bg-indigo-50' :
            addDragOver ? 'border-indigo-400 bg-indigo-50' : 'border-gray-300 bg-gray-50 hover:border-gray-400'
          ]"
          @dragenter.prevent="addDragOver = true"
          @dragover.prevent="addDragOver = true"
          @dragleave.prevent="addDragOver = false"
          @drop.prevent="onAddDrop"
          @click="triggerAddPicker"
        >
          <svg v-if="addingFiles" class="mb-2 h-8 w-8 animate-spin text-indigo-400" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
          <svg v-else class="mb-2 h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
          <p v-if="addingFiles" class="text-sm text-indigo-600">Uploading...</p>
          <p v-else class="text-sm text-gray-600">
            <span class="text-indigo-600">Click to choose</span> or drop PDFs here
          </p>
          <input
            ref="addFileInputRef"
            type="file"
            multiple
            accept=".pdf,application/pdf"
            class="hidden"
            @change="onAddFilePick"
          />
        </div>
        <div v-if="addFilesError" class="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {{ addFilesError }}
        </div>
        <div v-if="addFilesSuccess" class="mt-3 rounded border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
          {{ addFilesSuccess }}
        </div>
      </div>

      <div v-if="!batch.documents?.length" class="mt-6 rounded-xl border border-gray-200 bg-white p-8 text-center">
        <p class="text-sm text-gray-500">No documents in this batch.</p>
      </div>

      <Teleport to="body">
        <div v-if="showDeleteAllModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showDeleteAllModal = false">
          <div class="mx-4 w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h3 class="text-lg font-semibold text-gray-900">Delete All Documents?</h3>
            <p class="mt-2 text-sm text-gray-600">This will permanently delete all {{ batch.documents?.length ?? 0 }} documents and their PDF files. This action cannot be undone.</p>
            <div class="mt-6 flex justify-end gap-3">
              <button type="button" class="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50" @click="showDeleteAllModal = false">Cancel</button>
              <button type="button" :disabled="deletingAll" class="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60" @click="handleDeleteAll">
                <svg v-if="deletingAll" class="h-4 w-4 animate-spin" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
                {{ deletingAll ? 'Deleting...' : 'Delete All' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="showDeleteBatchModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showDeleteBatchModal = false">
          <div class="mx-4 w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h3 class="text-lg font-semibold text-gray-900">Delete Entire Batch?</h3>
            <p class="mt-2 text-sm text-gray-600">This will permanently delete this batch, all its documents, and their PDF files. This action cannot be undone.</p>
            <div class="mt-6 flex justify-end gap-3">
              <button type="button" class="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50" @click="showDeleteBatchModal = false">Cancel</button>
              <button type="button" :disabled="deletingAll" class="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60" @click="handleDeleteBatch">
                <svg v-if="deletingAll" class="h-4 w-4 animate-spin" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
                {{ deletingAll ? 'Deleting...' : 'Delete Batch' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { API_BASE } from '@/config'
import type { BatchDetail } from '@/stores/dashboard'

const route = useRoute()
const router = useRouter()

const batch = ref<BatchDetail | null>(null)
const initialLoading = ref(true)
const fetchError = ref<string | null>(null)
const pollingActive = ref(false)
const retrying = ref<Record<string, boolean>>({})
const retryError = ref<string | null>(null)
const downloading = ref(false)
const downloadSuccess = ref(false)
const downloadError = ref<string | null>(null)

// Add documents drag-drop (auto-upload)
const addDragOver = ref(false)
const addingFiles = ref(false)
const addFilesError = ref<string | null>(null)
const addFilesSuccess = ref<string | null>(null)
const addFileInputRef = ref<HTMLInputElement | null>(null)

// Batch naming
const editingName = ref(false)
const batchName = ref('')
const nameInputRef = ref<HTMLInputElement | null>(null)

// Delete state
const deletingDocs = ref<Record<string, boolean>>({})
const deletingAll = ref(false)
const showDeleteAllModal = ref(false)
const showDeleteBatchModal = ref(false)

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

function triggerAddPicker() {
  addFileInputRef.value?.click()
}

async function uploadFiles(files: File[]) {
  if (!files.length || addingFiles.value) return
  addingFiles.value = true
  addFilesError.value = null
  addFilesSuccess.value = null

  try {
    const form = new FormData()
    for (const f of files) {
      form.append('files', f)
    }
    await axios.post(`${API_BASE}/batch/${route.params.id}/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const count = files.length
    addFilesSuccess.value = `${count} file${count === 1 ? '' : 's'} added successfully`
    await fetchBatch()
    startPolling()
  } catch (err: any) {
    addFilesError.value = err?.response?.data?.detail || 'Upload failed'
  } finally {
    addingFiles.value = false
  }
}

function onAddFilePick(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files ? Array.from(input.files) : []
  input.value = ''
  if (files.length) {
    uploadFiles(files)
  }
}

function onAddDrop(e: DragEvent) {
  addDragOver.value = false
  const files = Array.from(e.dataTransfer?.files ?? []).filter(
    (f) => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'),
  )
  if (files.length) {
    uploadFiles(files)
  }
}

async function deleteSingleDocument(documentId: string) {
  deletingDocs.value[documentId] = true
  try {
    await axios.delete(`${API_BASE}/document/${documentId}`)
    await fetchBatch()
  } catch (err: any) {
    const msg = err?.response?.data?.detail || 'Failed to delete document'
    fetchError.value = msg
  } finally {
    deletingDocs.value[documentId] = false
  }
}

async function handleDeleteAll() {
  if (!batch.value) return
  deletingAll.value = true
  try {
    await axios.delete(`${API_BASE}/batch/${batch.value.batch_id}/documents`)
    showDeleteAllModal.value = false
    await fetchBatch()
  } catch (err: any) {
    const msg = err?.response?.data?.detail || 'Failed to delete documents'
    fetchError.value = msg
    showDeleteAllModal.value = false
  } finally {
    deletingAll.value = false
  }
}

async function handleDeleteBatch() {
  if (!batch.value) return
  deletingAll.value = true
  try {
    await axios.delete(`${API_BASE}/batch/${batch.value.batch_id}`)
    showDeleteBatchModal.value = false
    router.push('/')
  } catch (err: any) {
    const msg = err?.response?.data?.detail || 'Failed to delete batch'
    fetchError.value = msg
    showDeleteBatchModal.value = false
  } finally {
    deletingAll.value = false
  }
}

function startEditName() {
  batchName.value = batch.value?.name || ''
  editingName.value = true
  nextTick(() => nameInputRef.value?.focus())
}

async function saveBatchName() {
  editingName.value = false
  const name = batchName.value.trim()
  if (!name || !batch.value) return
  try {
    await axios.patch(`${API_BASE}/batch/${batch.value.batch_id}/name`, { name })
    if (batch.value) batch.value.name = name
  } catch {
    // non-blocking — name is optional
  }
}

function cancelEditName() {
  editingName.value = false
  batchName.value = ''
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
