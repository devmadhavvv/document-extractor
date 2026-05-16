<template>
  <div class="flex h-full flex-col">
    <div class="border-b border-gray-200 px-4 py-3">
      <div class="flex items-start justify-between gap-2">
        <div class="min-w-0 flex-1">
          <h3 class="truncate text-sm font-semibold text-gray-900">{{ document.filename }}</h3>
          <p class="mt-0.5 text-xs text-gray-500">{{ document.document_id.slice(0, 12) }}…</p>
        </div>
        <span
          class="inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium"
          :class="statusBadgeClass"
        >{{ document.status }}</span>
      </div>
    </div>

    <div class="sticky top-0 z-10 border-b border-gray-100 bg-white px-4 py-3">
      <div class="flex items-center justify-between">
        <h4 class="text-xs font-semibold uppercase tracking-wider text-gray-500">Verify Extracted Fields</h4>
        <button
          v-if="hasUnsavedChanges"
          type="button"
          class="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          :disabled="saving"
          @click="handleSave"
        >
          {{ saving ? 'Saving…' : 'Save Changes' }}
        </button>
      </div>
    </div>

    <div class="flex-1 space-y-5 overflow-y-auto px-4 py-4">
      <div class="space-y-4">
        <FieldConfidenceInput
          v-for="field in fields"
          :key="field.key"
          ref="fieldRefs"
          :field-key="field.key"
          :label="field.label"
          :extracted-value="field.extracted"
          :confidence="field.confidence"
          :model-value="formValues[field.key] ?? null"
          :disabled="document.approved"
          @update:model-value="onFieldUpdate(field.key, $event)"
        />
      </div>

      <div v-if="saveError" class="rounded-lg bg-red-50 p-3 text-xs text-red-600">{{ saveError }}</div>

      <div v-if="saveSuccess" class="rounded-lg bg-green-50 p-3 text-xs text-green-600">Changes saved successfully</div>

      <div class="border-t border-gray-100 pt-4">
        <button
          type="button"
          class="flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
          :class="document.approved ? 'bg-green-50 text-green-700' : 'bg-indigo-600 text-white hover:bg-indigo-700'"
          :disabled="document.approved || approving || saving"
          @click="handleApprove"
        >
          <svg v-if="document.approved" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
          <svg v-else-if="approving" class="h-4 w-4 animate-spin" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" /><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" /></svg>
          {{ document.approved ? 'Approved' : approving ? 'Approving…' : 'Approve Document' }}
        </button>
      </div>

      <details class="group">
        <summary class="flex cursor-pointer items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-500 hover:text-gray-700">
          <svg class="h-3 w-3 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
          Raw Extracted JSON
        </summary>
        <pre class="mt-2 overflow-x-auto rounded-lg bg-gray-50 p-3 text-[11px] leading-relaxed text-gray-600">{{ prettyJson }}</pre>
      </details>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import axios from 'axios'
import FieldConfidenceInput from './FieldConfidenceInput.vue'
import { API_BASE } from '@/config'

const FIELD_LABELS: Record<string, string> = {
  employee_code: 'Employee Code',
  candidate_name: 'Candidate Name',
  father_name: "Father's Name",
  date_of_birth: 'Date of Birth',
  date_of_joining: 'Date of Joining',
  aadhaar_number: 'Aadhaar Number',
  pan_number: 'PAN Number',
  mobile_number: 'Mobile Number',
  gender: 'Gender',
  marital_status: 'Marital Status',
  address: 'Address',
  bank_account_number: 'Bank Account Number',
  ifsc_code: 'IFSC Code',
}

interface ExtractedField {
  value: string | null
  confidence: number
}

export interface DocumentData {
  document_id: string
  batch_id?: string
  filename: string
  status: string
  extracted_json: Record<string, ExtractedField> | null
  verified_json: Record<string, ExtractedField> | null
  approved: boolean
  error_message: string | null
}

interface Field {
  key: string
  label: string
  extracted: string
  confidence: number
}

const props = defineProps<{
  document: DocumentData
}>()

const emit = defineEmits<{
  approved: []
  saved: []
  'approve-error': [message: string]
}>()

const approving = ref(false)
const saving = ref(false)
const saveError = ref<string | null>(null)
const saveSuccess = ref(false)
const fieldRefs = ref<InstanceType<typeof FieldConfidenceInput>[]>([])
const formValues = reactive<Record<string, string>>({})

const fields = computed<Field[]>(() => {
  const extracted = props.document.extracted_json ?? {}
  return Object.entries(FIELD_LABELS).map(([key, label]) => {
    const ext = extracted[key] as ExtractedField | undefined
    return {
      key,
      label,
      extracted: ext?.value ?? '',
      confidence: ext?.confidence ?? 0,
    }
  })
})

const statusBadgeClass = computed(() => {
  const map: Record<string, string> = {
    SUCCESS: 'bg-green-100 text-green-800',
    FAILED: 'bg-red-100 text-red-800',
    AI_PROCESSING: 'bg-amber-100 text-amber-800',
    PDF_CONVERSION: 'bg-blue-100 text-blue-800',
    QUEUED: 'bg-gray-100 text-gray-600',
  }
  return map[props.document.status] ?? 'bg-gray-100 text-gray-600'
})

const prettyJson = computed(() => {
  if (!props.document.extracted_json) return '{}'
  return JSON.stringify(props.document.extracted_json, null, 2)
})

const hasUnsavedChanges = computed(() => {
  const verified = props.document.verified_json ?? {}
  return Object.keys(FIELD_LABELS).some((key) => {
    const formVal = formValues[key]
    if (formVal === undefined) return false
    const verifiedVal = verified[key]?.value ?? ''
    return formVal !== verifiedVal
  })
})

function onFieldUpdate(key: string, value: string) {
  formValues[key] = value
  saveError.value = null
  saveSuccess.value = false
}

function initForm() {
  const verified = props.document.verified_json ?? {}
  for (const key of Object.keys(FIELD_LABELS)) {
    const verifiedVal = (verified[key] as ExtractedField | undefined)?.value
    const extractedVal = (props.document.extracted_json?.[key] as ExtractedField | undefined)?.value
    formValues[key] = verifiedVal ?? extractedVal ?? ''
  }
}

async function handleSave() {
  saving.value = true
  saveError.value = null
  saveSuccess.value = false

  const payload: Record<string, { value: string; confidence: number }> = {}
  const extracted = props.document.extracted_json ?? {}
  for (const [key] of Object.entries(FIELD_LABELS)) {
    if (formValues[key] !== undefined && formValues[key] !== '') {
      const ext = extracted[key] as ExtractedField | undefined
      payload[key] = {
        value: formValues[key],
        confidence: ext?.confidence ?? 100,
      }
    }
  }

  try {
    await axios.patch(`${API_BASE}/document/${props.document.document_id}`, {
      verified_json: payload,
    })
    saveSuccess.value = true
    emit('saved')
  } catch (err: any) {
    saveError.value = err?.response?.data?.detail || 'Failed to save changes'
  } finally {
    saving.value = false
  }
}

async function handleApprove() {
  if (props.document.approved || approving.value || saving.value) return

  approving.value = true
  try {
    if (hasUnsavedChanges.value) {
      const payload: Record<string, { value: string; confidence: number }> = {}
      const extracted = props.document.extracted_json ?? {}
      for (const [key] of Object.entries(FIELD_LABELS)) {
        if (formValues[key] !== undefined && formValues[key] !== '') {
          const ext = extracted[key] as ExtractedField | undefined
          payload[key] = {
            value: formValues[key],
            confidence: ext?.confidence ?? 100,
          }
        }
      }
      await axios.patch(`${API_BASE}/document/${props.document.document_id}`, {
        verified_json: payload,
      })
    }
    await axios.post(`${API_BASE}/document/${props.document.document_id}/approve`)
    emit('approved')
  } catch (err: any) {
    const msg = err?.response?.data?.detail || 'Failed to approve document'
    emit('approve-error', msg)
  } finally {
    approving.value = false
  }
}

watch(() => props.document.document_id, () => {
  saveError.value = null
  saveSuccess.value = false
  initForm()
}, { immediate: true })
</script>
