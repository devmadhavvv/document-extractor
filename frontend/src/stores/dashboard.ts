import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { API_BASE } from '@/config'

export interface Batch {
  batch_id: string
  name?: string | null
  status: string
  total_files: number
  completed_files: number
  failed_files: number
  created_at: string | null
  status_counts: Record<string, number>
}

export interface BatchDocument {
  document_id: string
  filename: string
  status: string
  approved: boolean
  error_message: string | null
}

export interface BatchDetail extends Batch {
  documents: BatchDocument[]
  excel_exported_at?: string | null
}

export const useDashboardStore = defineStore('dashboard', () => {
  const batches = ref<Batch[]>([])
  const currentBatch = ref<BatchDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const totalBatches = computed(() => batches.value.length)

  const processingBatches = computed(() =>
    batches.value.filter((b) => b.status === 'AI_PROCESSING' || b.status === 'QUEUED' || b.status === 'PDF_CONVERSION'),
  )

  const completedBatches = computed(() =>
    batches.value.filter((b) => b.status === 'SUCCESS'),
  )

  const failedBatches = computed(() =>
    batches.value.filter((b) => b.status === 'FAILED'),
  )

  const recentBatches = computed(() =>
    [...batches.value].sort((a, b) => {
      if (!a.created_at || !b.created_at) return 0
      return b.created_at.localeCompare(a.created_at)
    }),
  )

  const stats = computed(() => ({
    total: totalBatches.value,
    processing: processingBatches.value.length,
    completed: completedBatches.value.length,
    failed: failedBatches.value.length,
  }))

  async function fetchBatches() {
    loading.value = true
    error.value = null
    try {
      const res = await fetch(`${API_BASE}/batches`)
      if (!res.ok) throw new Error(`Failed to fetch batches: ${res.status}`)
      batches.value = await res.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchBatchDetail(batchId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await fetch(`${API_BASE}/batch/${batchId}`)
      if (!res.ok) throw new Error(`Failed to fetch batch: ${res.status}`)
      currentBatch.value = await res.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  return {
    batches,
    currentBatch,
    loading,
    error,
    totalBatches,
    processingBatches,
    completedBatches,
    failedBatches,
    recentBatches,
    stats,
    fetchBatches,
    fetchBatchDetail,
  }
})
