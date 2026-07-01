<template>
  <div class="page">
    <div class="page-header">
      <h1>Settings</h1>
      <p>Manage your matching criteria and search preferences</p>
    </div>

    <div v-if="loading" class="loading-state">Loading settings…</div>

    <form v-else class="settings-layout" @submit.prevent="save">
      <div class="settings-card">
        <h3>Matching Criteria</h3>

        <div class="field-group">
          <label>Target Roles <span class="hint">(comma separated)</span></label>
          <input v-model="roles" type="text" placeholder="Développeur backend, Ingénieur backend" />
        </div>

        <div class="field-group">
          <label>Technologies <span class="hint">(comma separated)</span></label>
          <input v-model="tech" type="text" placeholder="python, fastapi, node, typescript" />
        </div>

        <div class="field-group">
          <label>Contract Types</label>
          <div class="chip-group">
            <button
              v-for="c in contractOptions"
              :key="c"
              type="button"
              class="chip"
              :class="{ 'chip-active': selectedContracts.includes(c) }"
              @click="toggleChip(selectedContracts, c)"
            >{{ c }}</button>
          </div>
        </div>

        <div class="field-group">
          <label>Locations <span class="hint">(comma separated)</span></label>
          <input v-model="locations" type="text" placeholder="paris, ile-de-france" />
        </div>

        <div class="field-group">
          <label>Minimum Match Score</label>
          <div class="range-row">
            <input v-model.number="minScore" type="range" min="0" max="1" step="0.05" class="range-input" />
            <span class="range-val">{{ Math.round(minScore * 100) }}%</span>
          </div>
        </div>
      </div>

      <div class="settings-card">
        <h3>Active Search Queries</h3>
        <ul class="query-list">
          <li v-for="(q, i) in (criteria?.search_queries ?? [])" :key="i" class="query-item">
            <span class="query-dot" /> {{ q }}
          </li>
          <li v-if="!criteria?.search_queries?.length" class="query-empty">Save your profile first to compile queries.</li>
        </ul>
      </div>

      <div class="save-row">
        <p v-if="saved" class="save-msg">✓ Settings saved</p>
        <button type="submit" class="btn-save" :disabled="saving">
          {{ saving ? 'Saving…' : 'Save Settings' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const { get } = useApi()
const config = useRuntimeConfig()

const loading = ref(true)
const saving = ref(false)
const saved = ref(false)
const criteria = ref<any>(null)

const roles = ref('')
const tech = ref('')
const locations = ref('')
const minScore = ref(0.5)
const selectedContracts = ref<string[]>([])

const contractOptions = ['cdi', 'alternance', 'cdd', 'stage']

const toggleChip = (arr: string[], val: string) => {
  const idx = arr.indexOf(val)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(val)
}

onMounted(async () => {
  loading.value = true
  try {
    const d = await get('/api/profile')
    criteria.value = d.matching_criteria
    if (criteria.value) {
      roles.value = (criteria.value.target_roles ?? []).join(', ')
      tech.value = (criteria.value.target_tech ?? []).join(', ')
      locations.value = (criteria.value.target_locations ?? []).join(', ')
      minScore.value = criteria.value.min_score ?? 0.5
      selectedContracts.value = criteria.value.target_contracts ?? []
    }
  } catch {}
  loading.value = false
})

const save = async () => {
  saving.value = true
  saved.value = false
  try {
    const profileData = await get('/api/profile')
    const p = profileData.profile
    await fetch(`${config.public.apiBase}/api/profile`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: p?.full_name || '',
        email: p?.email || '',
        phone: p?.phone,
        github_url: p?.github_url,
        linkedin_url: p?.linkedin_url,
        master_cv: p?.master_cv || '',
        target_roles: roles.value.split(',').map(s => s.trim()).filter(Boolean),
        target_tech: tech.value.split(',').map(s => s.trim()).filter(Boolean),
        target_contracts: selectedContracts.value,
        target_locations: locations.value.split(',').map(s => s.trim()).filter(Boolean),
      })
    })
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } catch {}
  saving.value = false
}
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 1.5rem; }
.page-header h1 { font-size: 1.5rem; font-weight: 700; color: #f1f5f9; }
.page-header p { font-size: 0.875rem; color: #64748b; margin-top: 0.25rem; }

.loading-state { color: #64748b; font-size: 0.875rem; padding: 2rem 0; }

.settings-layout { display: flex; flex-direction: column; gap: 1.25rem; }

.settings-card {
  background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px; padding: 1.5rem;
  display: flex; flex-direction: column; gap: 1.25rem;
}
.settings-card h3 { font-size: 0.925rem; font-weight: 600; color: #f1f5f9; text-transform: none; letter-spacing: 0; }

.field-group { display: flex; flex-direction: column; gap: 0.5rem; }
label { font-size: 0.8rem; font-weight: 500; color: #64748b; }
.hint { font-weight: 400; color: #334155; }

input[type="text"] {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px; padding: 0.65rem 0.875rem;
  font-size: 0.875rem; color: #e2e8f0; font-family: inherit; outline: none; transition: border-color 0.15s;
}
input[type="text"]::placeholder { color: #334155; }
input[type="text"]:focus { border-color: rgba(16,185,129,0.4); }

.chip-group { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.chip {
  font-size: 0.8rem; font-weight: 500; padding: 0.35rem 0.875rem; border-radius: 20px;
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  color: #94a3b8; transition: all 0.15s; text-transform: uppercase;
}
.chip:hover { color: #10b981; border-color: rgba(16,185,129,0.3); }
.chip-active { background: rgba(16,185,129,0.12); border-color: rgba(16,185,129,0.35); color: #10b981; }

.range-row { display: flex; align-items: center; gap: 1rem; }
.range-input { flex: 1; accent-color: #10b981; }
.range-val { font-size: 0.875rem; font-weight: 700; color: #10b981; min-width: 40px; }

.query-list { list-style: none; display: flex; flex-direction: column; gap: 0.5rem; }
.query-item { display: flex; align-items: flex-start; gap: 0.5rem; font-size: 0.82rem; color: #94a3b8; line-height: 1.4; }
.query-dot { width: 6px; height: 6px; border-radius: 50%; background: #10b981; flex-shrink: 0; margin-top: 5px; box-shadow: 0 0 6px rgba(16,185,129,0.5); }
.query-empty { font-size: 0.8rem; color: #475569; font-style: italic; }

.save-row { display: flex; align-items: center; justify-content: flex-end; gap: 1rem; }
.save-msg { font-size: 0.875rem; color: #10b981; }
.btn-save {
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff; border: none; border-radius: 10px;
  padding: 0.75rem 1.75rem; font-size: 0.9rem; font-weight: 600;
  transition: all 0.2s; box-shadow: 0 4px 12px rgba(16,185,129,0.3);
}
.btn-save:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(16,185,129,0.4); }
.btn-save:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
