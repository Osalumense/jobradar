<template>
  <div class="feats-page">
    <div class="page-header">
      <div>
        <h1>Accomplishments</h1>
        <p>Your achievements bank. The AI draws from these when tailoring your applications.</p>
      </div>
      <button class="btn-add" @click="showForm = true">+ Add accomplishment</button>
    </div>

    <!-- Add form -->
    <div v-if="showForm" class="feat-form-card">
      <h3>New accomplishment</h3>
      <div class="form-fields">
        <div class="field">
          <label>Title <span class="req">*</span></label>
          <input v-model="form.title" type="text" placeholder="e.g. Built async job queue that cut latency by 60%" />
        </div>
        <div class="field">
          <label>Description <span class="req">*</span></label>
          <textarea v-model="form.description" rows="4" placeholder="Describe what you did, the impact, the metrics. Be specific — the more detail, the better the AI can use it." />
        </div>
        <div class="field">
          <label>Skills / Technologies</label>
          <input v-model="skillsInput" type="text" placeholder="python, redis, fastapi (comma separated)" />
        </div>
      </div>
      <p v-if="formError" class="error-msg">{{ formError }}</p>
      <div class="form-actions">
        <button class="btn-cancel" @click="cancelForm">Cancel</button>
        <button class="btn-save" :disabled="saving || !form.title || !form.description" @click="saveFeat">
          <span v-if="saving" class="spinner" />
          {{ saving ? 'Saving…' : 'Save accomplishment' }}
        </button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!loading && feats.length === 0 && !showForm" class="empty-state">
      <div class="empty-icon">🏆</div>
      <h3>No accomplishments yet</h3>
      <p>Add your achievements, metrics, and project highlights. The AI uses these to write stronger, more specific applications.</p>
      <button class="btn-add" @click="showForm = true">Add your first one</button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <span class="spinner" /> Loading accomplishments…
    </div>

    <!-- Feats grid -->
    <ConfirmModal
      v-model="showConfirm"
      title="Delete accomplishment?"
      message="This will permanently remove it from your achievements bank and it won't be used in future applications."
      confirm-label="Delete"
      cancel-label="Keep it"
      @confirm="confirmDelete"
    />

    <div v-if="feats.length > 0" class="feats-grid">
      <div v-for="feat in feats" :key="feat.id" class="feat-card">
        <div class="feat-header">
          <h3>{{ feat.title }}</h3>
          <button class="btn-delete" @click="deleteFeat(feat.id)" title="Delete">✕</button>
        </div>
        <p class="feat-desc">{{ feat.description }}</p>
        <div v-if="feat.skills_used?.length" class="skill-chips">
          <span v-for="s in feat.skills_used" :key="s" class="skill-chip">{{ s }}</span>
        </div>
        <div class="feat-date">Added {{ formatDate(feat.created_at) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const config = useRuntimeConfig()
const api = config.public.apiBase

const feats = ref<any[]>([])
const loading = ref(true)
const showForm = ref(false)
const saving = ref(false)
const formError = ref('')
const skillsInput = ref('')

const form = reactive({ title: '', description: '' })

const fetchFeats = async () => {
  loading.value = true
  try {
    const res = await fetch(`${api}/api/feats`, { credentials: 'include' })
    feats.value = res.ok ? await res.json() : []
  } finally {
    loading.value = false
  }
}

const saveFeat = async () => {
  formError.value = ''
  saving.value = true
  try {
    const skills = skillsInput.value.split(',').map(s => s.trim().toLowerCase()).filter(Boolean)
    const res = await fetch(`${api}/api/feats`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: form.title, description: form.description, skills_used: skills })
    })
    if (!res.ok) throw new Error('Failed to save')
    cancelForm()
    await fetchFeats()
  } catch (e: any) {
    formError.value = e.message || 'Failed to save accomplishment'
  } finally {
    saving.value = false
  }
}

const showConfirm = ref(false)
const pendingDeleteId = ref<string | null>(null)

const deleteFeat = (id: string) => {
  pendingDeleteId.value = id
  showConfirm.value = true
}

const confirmDelete = async () => {
  if (!pendingDeleteId.value) return
  showConfirm.value = false
  await fetch(`${api}/api/feats/${pendingDeleteId.value}`, { method: 'DELETE', credentials: 'include' })
  feats.value = feats.value.filter(f => f.id !== pendingDeleteId.value)
  pendingDeleteId.value = null
}

const cancelForm = () => {
  showForm.value = false
  form.title = ''
  form.description = ''
  skillsInput.value = ''
  formError.value = ''
}

const formatDate = (d: string) => new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

onMounted(fetchFeats)
</script>

<style scoped>
.feats-page { max-width: 900px; }

.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 1rem; margin-bottom: 2rem;
}
.page-header h1 { font-size: 1.5rem; font-weight: 700; color: #f1f5f9; }
.page-header p { font-size: 0.875rem; color: #64748b; margin-top: 0.25rem; }

.btn-add {
  background: linear-gradient(135deg,#10b981,#059669); color: #fff;
  border: none; border-radius: 10px; padding: 0.65rem 1.25rem;
  font-size: 0.875rem; font-weight: 600; white-space: nowrap;
  box-shadow: 0 4px 12px rgba(16,185,129,0.25); transition: all 0.2s;
}
.btn-add:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(16,185,129,0.35); }

.feat-form-card {
  background: rgba(17,19,24,0.8); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px; padding: 1.75rem; margin-bottom: 2rem;
}
.feat-form-card h3 { font-size: 1rem; font-weight: 600; color: #f1f5f9; margin-bottom: 1.25rem; }

.form-fields { display: flex; flex-direction: column; gap: 1rem; }
.field { display: flex; flex-direction: column; gap: 0.4rem; }
label { font-size: 0.78rem; font-weight: 500; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
.req { color: #10b981; }
input, textarea {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px; padding: 0.7rem 0.875rem; font-family: inherit;
  font-size: 0.875rem; color: #e2e8f0; outline: none; transition: border-color 0.15s; width: 100%;
}
input:focus, textarea:focus { border-color: rgba(16,185,129,0.45); }
textarea { resize: vertical; line-height: 1.6; }

.error-msg {
  font-size: 0.85rem; color: #f87171; margin-top: 0.75rem;
  background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.2);
  border-radius: 8px; padding: 0.625rem 0.875rem;
}

.form-actions { display: flex; gap: 0.75rem; justify-content: flex-end; margin-top: 1.25rem; }
.btn-cancel {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  color: #64748b; border-radius: 10px; padding: 0.65rem 1.25rem;
  font-size: 0.875rem; font-weight: 500; transition: all 0.15s;
}
.btn-cancel:hover { color: #cbd5e1; }
.btn-save {
  background: linear-gradient(135deg,#10b981,#059669); color: #fff; border: none;
  border-radius: 10px; padding: 0.65rem 1.5rem; font-size: 0.875rem; font-weight: 600;
  display: flex; align-items: center; gap: 0.5rem; transition: all 0.2s;
}
.btn-save:disabled { opacity: 0.55; cursor: not-allowed; }

.empty-state {
  text-align: center; padding: 4rem 2rem;
  background: rgba(17,19,24,0.5); border: 1px dashed rgba(255,255,255,0.08); border-radius: 14px;
}
.empty-icon { font-size: 2.5rem; margin-bottom: 1rem; }
.empty-state h3 { font-size: 1.1rem; font-weight: 600; color: #f1f5f9; margin-bottom: 0.5rem; }
.empty-state p { font-size: 0.875rem; color: #64748b; max-width: 400px; margin: 0 auto 1.5rem; line-height: 1.6; }

.loading-state { display: flex; align-items: center; gap: 0.75rem; color: #475569; font-size: 0.875rem; padding: 2rem 0; }

.feats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 1rem; }

.feat-card {
  background: rgba(17,19,24,0.8); border: 1px solid rgba(255,255,255,0.07);
  border-radius: 12px; padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem;
  transition: border-color 0.15s;
}
.feat-card:hover { border-color: rgba(255,255,255,0.12); }

.feat-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; }
.feat-header h3 { font-size: 0.95rem; font-weight: 600; color: #f1f5f9; line-height: 1.4; }
.btn-delete {
  background: none; border: none; color: #334155; font-size: 0.75rem;
  padding: 0.2rem 0.4rem; border-radius: 4px; flex-shrink: 0; transition: all 0.15s;
}
.btn-delete:hover { color: #f87171; background: rgba(248,113,113,0.1); }

.feat-desc { font-size: 0.85rem; color: #94a3b8; line-height: 1.6; }

.skill-chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.skill-chip {
  font-size: 0.72rem; font-weight: 500; padding: 0.25rem 0.6rem;
  background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2);
  color: #10b981; border-radius: 6px;
}

.feat-date { font-size: 0.75rem; color: #334155; margin-top: auto; }

.spinner {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
