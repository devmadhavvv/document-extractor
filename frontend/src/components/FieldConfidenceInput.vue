<template>
  <div class="space-y-1">
    <div class="flex items-center justify-between">
      <label class="text-xs font-medium text-gray-600">{{ label }}</label>
      <span
        class="inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium leading-none"
        :class="confidenceColorClass"
      >{{ confidence }}%</span>
    </div>

    <div class="relative">
      <input
        :value="modelValue ?? extractedValue ?? ''"
        :class="[
          'w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none transition-colors',
          validationClass,
          disabled ? 'cursor-not-allowed bg-gray-50 text-gray-400' : '',
        ]"
        :disabled="disabled"
        :placeholder="extractedValue || label"
        @input="onInput"
        @blur="onBlur"
      />
      <div
        v-if="error"
        class="mt-1 text-[11px] leading-tight text-red-500"
      >{{ error }}</div>
    </div>

    <div v-if="extractedValue && modelValue !== extractedValue" class="flex items-center gap-1 text-[10px] text-gray-400">
      <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      Extracted: {{ extractedValue }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  fieldKey: string
  label: string
  extractedValue: string | null
  confidence: number
  modelValue: string | null
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const error = ref<string | null>(null)
const touched = ref(false)

const VALIDATORS: Record<string, (val: string) => string | null> = {
  employee_code: (v) => v.length === 0 ? 'Required' : null,
  candidate_name: (v) => v.length === 0 ? 'Required' : null,
  father_name: () => null,
  date_of_birth: validateDate,
  date_of_joining: validateDate,
  aadhaar_number: validateAadhaar,
  pan_number: validatePAN,
  gender: () => null,
  marital_status: () => null,
  address: () => null,
  bank_account_number: (v) => v.length > 0 && !/^\d+$/.test(v) ? 'Must be digits only' : null,
  ifsc_code: validateIFSC,
}

const confidenceColorClass = computed(() => {
  if (props.confidence > 85) return 'bg-green-100 text-green-700'
  if (props.confidence >= 60) return 'bg-amber-100 text-amber-700'
  return 'bg-red-100 text-red-700'
})

const validationClass = computed(() => {
  if (!touched.value && !error.value) return 'border-gray-200 focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400'
  if (error.value) return 'border-red-300 focus:border-red-400 focus:ring-1 focus:ring-red-400'
  return 'border-green-300 focus:border-green-400 focus:ring-1 focus:ring-green-400'
})

const TRANSFORM_UPPER = new Set([
  'employee_code', 'candidate_name', 'father_name', 'gender', 'marital_status',
])

function transform(value: string): string {
  if (TRANSFORM_UPPER.has(props.fieldKey)) {
    return value.toUpperCase()
  }
  return value
}

function validateDate(val: string): string | null {
  if (!val) return null
  if (!/^\d{2}\/\d{2}\/\d{4}$/.test(val)) return 'Use DD/MM/YYYY format'
  const [d, m, y] = val.split('/').map(Number)
  if (m < 1 || m > 12) return 'Invalid month'
  if (d < 1 || d > 31) return 'Invalid day'
  if (y < 1900 || y > 2100) return 'Invalid year'
  return null
}

function validatePAN(val: string): string | null {
  if (!val) return null
  const cleaned = val.toUpperCase()
  if (!/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(cleaned)) return 'Format: AAAAA9999A'
  return null
}

function validateAadhaar(val: string): string | null {
  if (!val) return null
  const digits = val.replace(/\s|-/g, '')
  if (!/^\d{12}$/.test(digits)) return 'Must be 12 digits'
  return null
}

function validateIFSC(val: string): string | null {
  if (!val) return null
  const cleaned = val.toUpperCase()
  if (!/^[A-Z]{4}0[A-Z0-9]{6}$/.test(cleaned)) return 'Format: AAAA0XXXXX'
  return null
}

function onInput(e: Event) {
  const raw = (e.target as HTMLInputElement).value
  const transformed = transform(raw)
  if (transformed !== raw) {
    ;(e.target as HTMLInputElement).value = transformed
  }
  error.value = validate(transformed)
  emit('update:modelValue', transformed)
}

function onBlur() {
  touched.value = true
  const current = props.modelValue ?? props.extractedValue ?? ''
  error.value = validate(current)
}

function validate(val: string): string | null {
  const validator = VALIDATORS[props.fieldKey]
  if (validator) return validator(val)
  return null
}

function validateAll() {
  touched.value = true
  const current = props.modelValue ?? props.extractedValue ?? ''
  error.value = validate(current)
  return error.value === null
}

defineExpose({ validateAll })
</script>
