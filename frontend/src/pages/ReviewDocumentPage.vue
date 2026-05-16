<template>
  <div class="flex h-full flex-col">
    <div v-if="loading" class="space-y-4 p-6">
      <div class="h-8 w-64 animate-pulse rounded bg-gray-200" />
      <div class="flex gap-4">
        <div class="h-[70vh] flex-1 animate-pulse rounded-xl bg-white shadow-sm" />
        <div class="h-[70vh] w-96 animate-pulse rounded-xl bg-white shadow-sm" />
      </div>
    </div>

    <div
      v-else-if="error"
      class="m-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
    >
      {{ error }}
    </div>

    <template v-else-if="document">
      <div class="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
        <div class="flex min-w-0 items-center gap-4">
          <router-link
            :to="`/batch/${document.batch_id}`"
            class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
          </router-link>
          <div class="min-w-0">
            <h2 class="truncate text-sm font-semibold text-gray-900">{{ document.filename }}</h2>
            <p class="text-xs text-gray-500">{{ document.status }}</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-30"
            :disabled="!prevDocId"
            @click="navigateTo(prevDocId)"
          >
            Previous
          </button>
          <span class="text-xs text-gray-400">{{ navIndex }} / {{ navTotal }}</span>
          <button
            type="button"
            class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-30"
            :disabled="!nextDocId"
            @click="navigateTo(nextDocId)"
          >
            Next
          </button>
        </div>
      </div>

      <div class="flex flex-1 flex-col overflow-hidden lg:flex-row">
        <div class="flex-1 overflow-hidden">
          <PdfViewer :source="pdfUrl" @rendered="onPdfRendered" />
        </div>
        <div class="w-full border-t border-gray-200 lg:w-96 lg:shrink-0 lg:border-t-0 lg:border-l">
          <ReviewSidebar
            :key="document.document_id"
            :document="document"
            @approved="onApproved"
            @saved="onSaved"
            @approve-error="onApproveError"
          />
        </div>
      </div>
    </template>
    <ToastNotification ref="toastRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import PdfViewer from '@/components/PdfViewer.vue'
import ReviewSidebar from '@/components/ReviewSidebar.vue'
import ToastNotification from '@/components/ToastNotification.vue'
import { API_BASE } from '@/config'
const route = useRoute()
const router = useRouter()

const document = ref<DocumentData | null>(null)
const batch = ref<BatchDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const pdfUrl = computed(() => `${API_BASE}/document/${route.params.id}/pdf`)

const navDocuments = computed(() => {
  if (!batch.value?.documents) return []
  return batch.value.documents.filter((d: BatchDocument) => d.status === 'SUCCESS')
})

const navIndex = computed(() => {
  const idx = navDocuments.value.findIndex((d: BatchDocument) => d.document_id === route.params.id)
  return idx === -1 ? 0 : idx + 1
})

const navTotal = computed(() => navDocuments.value.length)

const prevDocId = computed(() => {
  const idx = navDocuments.value.findIndex((d: BatchDocument) => d.document_id === route.params.id)
  return idx > 0 ? navDocuments.value[idx - 1].document_id : null
})

const nextDocId = computed(() => {
  const idx = navDocuments.value.findIndex((d: BatchDocument) => d.document_id === route.params.id)
  return idx < navDocuments.value.length - 1 ? navDocuments.value[idx + 1].document_id : null
})

async function fetchData(docId: string) {
  loading.value = true
  error.value = null
  try {
    const docRes = await axios.get(`${API_BASE}/document/${docId}`)
    document.value = docRes.data as DocumentData

    if (document.value.batch_id) {
      const batchRes = await axios.get(`${API_BASE}/batch/${document.value.batch_id}`)
      batch.value = batchRes.data as BatchDetail
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err.message || 'Failed to load document'
  } finally {
    loading.value = false
  }
}

const toastRef = ref<InstanceType<typeof ToastNotification> | null>(null)

function navigateTo(docId: string | null) {
  if (!docId) return
  router.push(`/document/${docId}`)
}

async function onApproved() {
  if (!document.value) return
  toastRef.value?.addToast('Document approved', 'success')
  await fetchData(document.value.document_id)
  const next = nextDocId.value
  if (next) {
    setTimeout(() => navigateTo(next), 1200)
  } else {
    toastRef.value?.addToast('All documents in this batch have been approved', 'success')
  }
}

function onSaved() {
  if (!document.value) return
  toastRef.value?.addToast('Changes saved', 'success')
  fetchData(document.value.document_id)
}

function onApproveError(msg: string) {
  toastRef.value?.addToast(msg, 'error')
}

watch(() => route.params.id, (newId) => {
  if (newId) fetchData(newId as string)
}, { immediate: true })
</script>
