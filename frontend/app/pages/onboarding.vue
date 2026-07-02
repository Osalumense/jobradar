<template>
  <div class="onboarding-shell">
    <div class="onboarding-card">
      <!-- Header -->
      <div class="ob-header">
        <div class="logo-mark">JR</div>
        <div>
          <h1>Set up your job radar</h1>
          <p>Tell us what you're looking for so we can find the right jobs for you.</p>
        </div>
      </div>

      <!-- Step indicators -->
      <div class="steps">
        <div v-for="i in totalSteps" :key="i" class="step-dot" :class="{ active: step === i, done: step > i }" />
      </div>

      <!-- Step 1: Personal info -->
      <div v-if="step === 1" class="ob-step">
        <h2>About you</h2>
        <div class="field-grid">
          <div class="field">
            <label>Full name <span class="req">*</span></label>
            <input v-model="form.full_name" type="text" placeholder="Stephen Akugbe" required />
          </div>
          <div class="field">
            <label>Phone</label>
            <input v-model="form.phone" type="tel" placeholder="+33 7 00 00 00 00" />
          </div>
          <div class="field">
            <label>GitHub URL</label>
            <input v-model="form.github_url" type="url" placeholder="https://github.com/username" />
          </div>
          <div class="field">
            <label>LinkedIn URL</label>
            <input v-model="form.linkedin_url" type="url" placeholder="https://linkedin.com/in/username" />
          </div>
        </div>
      </div>

      <!-- Step 2: CV upload -->
      <div v-if="step === 2" class="ob-step">
        <h2>Your CV</h2>
        <p class="ob-hint">We extract the text to build your semantic profile. Supports PDF, Word (.docx), or plain text.</p>

        <!-- Upload zone -->
        <label class="upload-zone" :class="{ 'has-file': cvFileName, 'uploading': cvUploading }">
          <input type="file" accept=".pdf,.docx,.txt,.md" class="file-input" @change="handleCVUpload" />
          <template v-if="cvUploading">
            <span class="spinner" style="width:22px;height:22px;border-width:3px" />
            <span class="upload-label">Extracting text…</span>
          </template>
          <template v-else-if="cvFileName">
            <svg viewBox="0 0 24 24" class="upload-icon success-icon"><polyline points="20 6 9 17 4 12"/></svg>
            <span class="upload-label">{{ cvFileName }}</span>
            <span class="upload-sub">Click to replace</span>
          </template>
          <template v-else>
            <svg viewBox="0 0 24 24" class="upload-icon"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <span class="upload-label">Click to upload your CV</span>
            <span class="upload-sub">PDF, DOCX, TXT — or paste below</span>
          </template>
        </label>

        <p v-if="cvUploadError" class="upload-error">{{ cvUploadError }}</p>

        <div class="cv-divider"><span>or paste text manually</span></div>

        <textarea
          v-model="form.master_cv"
          class="cv-area"
          placeholder="## Stephen Akugbe&#10;Backend Engineer, Python, Node.js, FastAPI…&#10;&#10;## Experience&#10;…"
          rows="8"
        />
        <div class="char-count" :class="{ good: form.master_cv.length >= 500 }">
          {{ form.master_cv.length }} chars
          <span v-if="form.master_cv.length < 300" class="char-hint">(aim for 500+)</span>
        </div>
      </div>

      <!-- Step 3: Job preferences -->
      <div v-if="step === 3" class="ob-step">
        <h2>What are you looking for?</h2>

        <div class="field">
          <label>Target roles <span class="req">*</span></label>
          <input v-model="rolesInput" type="text" placeholder="Développeur backend, Ingénieur logiciel" />
          <span class="field-hint">Separate multiple roles with commas</span>
        </div>

        <div class="field">
          <label>Contract types</label>
          <div class="chip-row">
            <button
              v-for="c in contractOptions"
              :key="c.value"
              type="button"
              class="chip"
              :class="{ active: form.target_contracts.includes(c.value) }"
              @click="toggleArr(form.target_contracts, c.value)"
            >{{ c.label }}</button>
          </div>
        </div>

        <div class="field">
          <label>Target locations</label>
          <input v-model="locationsInput" type="text" placeholder="Paris, Île-de-France, Remote" />
          <span class="field-hint">Separate multiple locations with commas</span>
        </div>
      </div>

      <!-- Step 4: Tech stack -->
      <div v-if="step === 4" class="ob-step">
        <h2>Your tech stack</h2>
        <p class="ob-hint">Select everything you work with — we use this for keyword matching on top of semantic similarity.</p>

        <div class="tech-grid">
          <button
            v-for="t in allTech"
            :key="t"
            type="button"
            class="tech-chip"
            :class="{ active: form.target_tech.includes(t) }"
            @click="toggleArr(form.target_tech, t)"
          >{{ t }}</button>
        </div>

        <div class="field" style="margin-top:1.25rem">
          <label>Other technologies</label>
          <input v-model="extraTech" type="text" placeholder="e.g. deno, bun, elixir" />
          <span class="field-hint">Comma separated — these will be added to your stack</span>
        </div>
      </div>

      <!-- Step 5: Review -->
      <div v-if="step === 5" class="ob-step">
        <h2>Review & finish</h2>
        <div class="review-grid">
          <div class="review-item"><span class="rv-label">Name</span><span class="rv-val">{{ form.full_name || '—' }}</span></div>
          <div class="review-item"><span class="rv-label">Roles</span><span class="rv-val">{{ parsedRoles.join(', ') || '—' }}</span></div>
          <div class="review-item"><span class="rv-label">Contracts</span><span class="rv-val">{{ form.target_contracts.join(', ') || '—' }}</span></div>
          <div class="review-item"><span class="rv-label">Locations</span><span class="rv-val">{{ parsedLocations.join(', ') || '—' }}</span></div>
          <div class="review-item"><span class="rv-label">Tech</span><span class="rv-val">{{ allSelectedTech.join(', ') || '—' }}</span></div>
          <div class="review-item"><span class="rv-label">CV</span><span class="rv-val">{{ form.master_cv.length }} chars pasted</span></div>
        </div>
        <p class="ob-hint" style="margin-top:1rem">You can update all of this anytime from Settings.</p>
      </div>

      <p v-if="error" class="error-msg">{{ error }}</p>

      <!-- Navigation -->
      <div class="ob-nav">
        <button v-if="step > 1" type="button" class="btn-back" @click="step--">← Back</button>
        <div style="flex:1" />
        <button
          v-if="step < totalSteps"
          type="button"
          class="btn-next"
          :disabled="!canNext"
          @click="next"
        >Continue →</button>
        <button
          v-else
          type="button"
          class="btn-finish"
          :disabled="saving"
          @click="finish"
        >
          <span v-if="saving" class="spinner" />
          {{ saving ? 'Setting up your radar…' : 'Launch my radar 🚀' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'auth', middleware: 'auth' })

const { user } = useAuth()
const config = useRuntimeConfig()
const api = config.public.apiBase

const step = ref(1)
const totalSteps = 5
const saving = ref(false)
const error = ref('')
const cvFileName = ref('')
const cvUploading = ref(false)
const cvUploadError = ref('')

const handleCVUpload = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  cvUploadError.value = ''
  cvUploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${api}/api/profile/parse-cv`, {
      method: 'POST',
      credentials: 'include',
      body: fd,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Could not read file')
    }
    const data = await res.json()
    form.master_cv = data.text
    cvFileName.value = file.name
  } catch (e: any) {
    cvUploadError.value = e.message || 'Upload failed. Try pasting your CV text instead.'
  } finally {
    cvUploading.value = false
  }
}

const form = reactive({
  full_name: '',
  phone: '',
  github_url: '',
  linkedin_url: '',
  master_cv: '',
  target_contracts: [] as string[],
  target_tech: [] as string[],
})

const rolesInput = ref('')
const locationsInput = ref('')
const extraTech = ref('')

const contractOptions = [
  { label: 'Alternance', value: 'alternance' },
  { label: 'CDI', value: 'cdi' },
  { label: 'CDD', value: 'cdd' },
  { label: 'Stage', value: 'stage' },
  { label: 'Freelance', value: 'freelance' },
]

const allTech = [
  'Python', 'Node.js', 'TypeScript', 'JavaScript', 'FastAPI', 'NestJS',
  'Express', 'Django', 'Flask', 'React', 'Vue', 'Nuxt', 'Next.js',
  'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes',
  'AWS', 'GCP', 'Azure', 'GraphQL', 'REST', 'CI/CD', 'PHP', 'Laravel',
  'Go', 'Rust', 'Java', 'Spring Boot', 'C#', '.NET', 'Terraform',
]

const parsedRoles = computed(() => rolesInput.value.split(',').map(s => s.trim()).filter(Boolean))
const parsedLocations = computed(() => locationsInput.value.split(',').map(s => s.trim()).filter(Boolean))
const parsedExtraTech = computed(() => extraTech.value.split(',').map(s => s.trim()).filter(Boolean))
const allSelectedTech = computed(() => [...form.target_tech, ...parsedExtraTech.value])

const toggleArr = (arr: string[], val: string) => {
  const i = arr.indexOf(val)
  if (i >= 0) arr.splice(i, 1)
  else arr.push(val)
}

const canNext = computed(() => {
  if (step.value === 1) return !!form.full_name.trim()
  if (step.value === 2) return form.master_cv.length >= 100
  if (step.value === 3) return parsedRoles.value.length > 0
  return true
})

const next = () => { if (canNext.value) step.value++ }

const finish = async () => {
  saving.value = true
  error.value = ''
  try {
    const email = user.value?.email || ''
    await fetch(`${api}/api/profile`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: form.full_name,
        email,
        phone: form.phone || null,
        github_url: form.github_url || null,
        linkedin_url: form.linkedin_url || null,
        master_cv: form.master_cv,
        target_roles: parsedRoles.value,
        target_tech: allSelectedTech.value.map(t => t.toLowerCase()),
        target_contracts: form.target_contracts,
        target_locations: parsedLocations.value,
      })
    })
    // Mark onboarding complete so middleware doesn't redirect back
    const onboardingDone = useState<boolean | null>('onboarding.done')
    onboardingDone.value = true
    await navigateTo('/')
  } catch (e: any) {
    error.value = 'Failed to save profile. Please try again.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.onboarding-shell {
  min-height: 100vh; background: #0d0f12;
  display: flex; align-items: flex-start; justify-content: center;
  padding: 3rem 1rem 4rem;
}

.onboarding-card {
  width: 100%; max-width: 640px;
  background: rgba(17,19,24,0.9); border: 1px solid rgba(255,255,255,0.07);
  border-radius: 20px; padding: 2.5rem 2.5rem 2rem;
  backdrop-filter: blur(20px);
}

.ob-header { display: flex; align-items: flex-start; gap: 1rem; margin-bottom: 1.75rem; }
.logo-mark {
  width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
  background: linear-gradient(135deg,#10b981,#059669);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.875rem; font-weight: 800; color: #fff;
}
.ob-header h1 { font-size: 1.3rem; font-weight: 700; color: #f1f5f9; margin-bottom: 0.2rem; }
.ob-header p { font-size: 0.85rem; color: #64748b; }

.steps { display: flex; gap: 0.5rem; margin-bottom: 2rem; }
.step-dot {
  flex: 1; height: 4px; border-radius: 2px; background: rgba(255,255,255,0.07);
  transition: background 0.3s;
}
.step-dot.active { background: #10b981; }
.step-dot.done { background: rgba(16,185,129,0.4); }

.ob-step { display: flex; flex-direction: column; gap: 1.25rem; min-height: 280px; }
.ob-step h2 { font-size: 1.1rem; font-weight: 600; color: #f1f5f9; }
.ob-hint { font-size: 0.85rem; color: #64748b; line-height: 1.6; }

.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.field { display: flex; flex-direction: column; gap: 0.4rem; }
label { font-size: 0.78rem; font-weight: 500; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
.req { color: #10b981; }
.field-hint { font-size: 0.75rem; color: #334155; }

input, textarea {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px; padding: 0.7rem 0.875rem; font-family: inherit;
  font-size: 0.875rem; color: #e2e8f0; outline: none; transition: border-color 0.15s;
  width: 100%;
}
input::placeholder, textarea::placeholder { color: #334155; }
input:focus, textarea:focus { border-color: rgba(16,185,129,0.45); }
textarea { resize: vertical; line-height: 1.6; }

.char-count { font-size: 0.78rem; color: #475569; text-align: right; }
.char-count.good { color: #10b981; }
.char-hint { margin-left: 0.5rem; }

.chip-row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.chip {
  font-size: 0.8rem; font-weight: 500; padding: 0.4rem 0.9rem; border-radius: 20px;
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  color: #94a3b8; transition: all 0.15s; cursor: pointer;
}
.chip:hover { border-color: rgba(16,185,129,0.3); color: #10b981; }
.chip.active { background: rgba(16,185,129,0.12); border-color: rgba(16,185,129,0.4); color: #10b981; }

.tech-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.tech-chip {
  font-size: 0.78rem; font-weight: 500; padding: 0.35rem 0.75rem; border-radius: 8px;
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
  color: #64748b; transition: all 0.15s; cursor: pointer;
}
.tech-chip:hover { color: #cbd5e1; border-color: rgba(255,255,255,0.12); }
.tech-chip.active { background: rgba(16,185,129,0.1); border-color: rgba(16,185,129,0.35); color: #10b981; }

.review-grid { display: flex; flex-direction: column; gap: 0.75rem; }
.review-item { display: flex; gap: 1rem; align-items: baseline; padding: 0.625rem 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
.rv-label { font-size: 0.78rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; min-width: 80px; }
.rv-val { font-size: 0.875rem; color: #cbd5e1; flex: 1; }

.error-msg {
  font-size: 0.85rem; color: #f87171; background: rgba(248,113,113,0.08);
  border: 1px solid rgba(248,113,113,0.2); border-radius: 8px; padding: 0.625rem 0.875rem;
}

.ob-nav { display: flex; align-items: center; gap: 0.75rem; margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid rgba(255,255,255,0.05); }

.btn-back {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  color: #64748b; border-radius: 10px; padding: 0.7rem 1.25rem;
  font-size: 0.875rem; font-weight: 500; transition: all 0.15s;
}
.btn-back:hover { color: #cbd5e1; border-color: rgba(255,255,255,0.14); }

.btn-next, .btn-finish {
  background: linear-gradient(135deg,#10b981,#059669); color: #fff; border: none;
  border-radius: 10px; padding: 0.75rem 1.75rem; font-size: 0.9rem; font-weight: 600;
  transition: all 0.2s; display: flex; align-items: center; gap: 0.5rem;
  box-shadow: 0 4px 12px rgba(16,185,129,0.3);
}
.btn-next:hover:not(:disabled), .btn-finish:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(16,185,129,0.4); }
.btn-next:disabled, .btn-finish:disabled { opacity: 0.55; cursor: not-allowed; }

.spinner {
  width: 15px; height: 15px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* CV upload */
.file-input { display: none; }

.upload-zone {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 0.5rem; padding: 2rem 1.5rem;
  border: 2px dashed rgba(255,255,255,0.1); border-radius: 12px;
  background: rgba(255,255,255,0.02); transition: all 0.2s; text-align: center;
  cursor: pointer;
}
.upload-zone:hover { border-color: rgba(16,185,129,0.4); background: rgba(16,185,129,0.04); }
.upload-zone.has-file { border-color: rgba(16,185,129,0.35); border-style: solid; background: rgba(16,185,129,0.06); }
.upload-zone.uploading { pointer-events: none; opacity: 0.7; }

.upload-icon {
  width: 28px; height: 28px; stroke: #475569; fill: none;
  stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
}
.success-icon { stroke: #10b981; }
.upload-label { font-size: 0.9rem; font-weight: 500; color: #cbd5e1; }
.upload-zone.has-file .upload-label { color: #10b981; }
.upload-sub { font-size: 0.78rem; color: #475569; }
.upload-error { font-size: 0.82rem; color: #f87171; background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.2); border-radius: 8px; padding: 0.5rem 0.75rem; }

.cv-divider {
  display: flex; align-items: center; gap: 0.75rem;
  color: #334155; font-size: 0.75rem;
}
.cv-divider::before, .cv-divider::after { content: ''; flex: 1; height: 1px; background: rgba(255,255,255,0.06); }
</style>
