<template>
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div v-if="modelValue" class="confirm-backdrop" @click.self="$emit('update:modelValue', false)">
        <div class="confirm-card">
          <div class="confirm-icon-wrap">
            <svg viewBox="0 0 24 24" class="confirm-icon"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          </div>
          <h3 class="confirm-title">{{ title }}</h3>
          <p class="confirm-body">{{ message }}</p>
          <div class="confirm-actions">
            <button class="btn-cancel" @click="$emit('update:modelValue', false)">{{ cancelLabel }}</button>
            <button class="btn-confirm" @click="$emit('confirm')">{{ confirmLabel }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean
  title?: string
  message?: string
  confirmLabel?: string
  cancelLabel?: string
}>()

defineEmits(['update:modelValue', 'confirm'])
</script>

<style scoped>
.confirm-backdrop {
  position: fixed; inset: 0; z-index: 2000;
  background: rgba(0,0,0,0.65); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; padding: 1rem;
}

.confirm-card {
  background: #161920; border: 1px solid rgba(255,255,255,0.09);
  border-radius: 16px; padding: 2rem 1.75rem;
  width: 100%; max-width: 360px;
  box-shadow: 0 24px 60px rgba(0,0,0,0.6);
  display: flex; flex-direction: column; align-items: center; gap: 0.875rem;
  text-align: center;
}

.confirm-icon-wrap {
  width: 48px; height: 48px; border-radius: 12px;
  background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2);
  display: flex; align-items: center; justify-content: center;
}
.confirm-icon {
  width: 22px; height: 22px; stroke: #f87171; fill: none;
  stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
}

.confirm-title { font-size: 1rem; font-weight: 700; color: #f1f5f9; }
.confirm-body { font-size: 0.875rem; color: #64748b; line-height: 1.6; }

.confirm-actions {
  display: flex; gap: 0.625rem; width: 100%; margin-top: 0.5rem;
}

.btn-cancel {
  flex: 1; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.09);
  color: #94a3b8; border-radius: 10px; padding: 0.7rem 1rem;
  font-size: 0.875rem; font-weight: 500; transition: all 0.15s;
}
.btn-cancel:hover { color: #f1f5f9; border-color: rgba(255,255,255,0.15); }

.btn-confirm {
  flex: 1; background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.3);
  color: #f87171; border-radius: 10px; padding: 0.7rem 1rem;
  font-size: 0.875rem; font-weight: 600; transition: all 0.15s;
}
.btn-confirm:hover { background: rgba(239,68,68,0.2); border-color: rgba(239,68,68,0.5); color: #fca5a5; }

.confirm-fade-enter-active, .confirm-fade-leave-active { transition: opacity 0.18s ease; }
.confirm-fade-enter-from, .confirm-fade-leave-to { opacity: 0; }
</style>
