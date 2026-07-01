<template>
  <Teleport to="body">
    <div v-if="modelValue" class="modal-backdrop" @click.self="$emit('update:modelValue', false)">
      <div class="modal-shell">
        <!-- Header -->
        <div class="modal-header">
          <div>
            <div class="modal-label">Prepare application</div>
            <h2 class="modal-title">{{ job?.title }}</h2>
            <div class="modal-sub">{{ job?.company }}</div>
          </div>
          <button class="modal-close" @click="$emit('update:modelValue', false)">✕</button>
        </div>

        <!-- Step 1: Feat suggestion -->
        <div v-if="step === 'feats'" class="modal-body">
          <div v-if="loadingFeats" class="center-state">
            <span class="spinner-lg" />
            <p>Analysing job and ranking your accomplishments…</p>
          </div>
          <template v-else>
            <div class="step-intro">
              <h3>Select relevant accomplishments</h3>
              <p>AI has pre-selected the most relevant ones. Uncheck what doesn't fit, or add more.</p>
            </div>

            <div v-if="rankedFeats.length === 0" class="no-feats-hint">
              You have no accomplishments yet. <NuxtLink to="/feats">Add some first →</NuxtLink>
            </div>

            <div v-else class="feats-list">
              <label v-for="feat in rankedFeats" :key="feat.id" class="feat-row" :class="{ selected: selectedIds.has(feat.id) }">
                <input type="checkbox" :checked="selectedIds.has(feat.id)" @change="toggleFeat(feat.id)" />
                <div class="feat-info">
                  <div class="feat-row-title">{{ feat.title }}</div>
                  <div class="feat-row-desc">{{ feat.description.slice(0, 120) }}{{ feat.description.length > 120 ? '…' : '' }}</div>
                  <div v-if="feat.reason" class="feat-reason">
                    <span class="reason-dot" :class="feat.suggested ? 'good' : 'dim'" />
                    {{ feat.reason }}
                  </div>
                </div>
              </label>
            </div>

            <div class="step-footer">
              <span class="sel-count">{{ selectedIds.size }} selected</span>
              <button class="btn-primary" @click="step = 'questions'">Continue →</button>
            </div>
          </template>
        </div>

        <!-- Step 2: Application questions -->
        <div v-if="step === 'questions'" class="modal-body">
          <div class="step-intro">
            <h3>Application questions <span class="optional">(optional)</span></h3>
            <p>Paste the questions from the application form. The AI will write a tailored answer for each one.</p>
          </div>
          <textarea
            v-model="questionsText"
            class="questions-area"
            rows="10"
            placeholder="e.g.&#10;1. Why are you interested in this role?&#10;2. Describe a challenging technical problem you solved.&#10;3. What experience do you have with distributed systems?"
          />
          <div class="step-footer">
            <button class="btn-back" @click="step = 'feats'">← Back</button>
            <button class="btn-primary" :disabled="generating" @click="generate">
              <span v-if="generating" class="spinner" />
              {{ generating ? 'Generating…' : 'Generate application ✨' }}
            </button>
          </div>
        </div>

        <!-- Step 3: Generating -->
        <div v-if="step === 'generating'" class="modal-body center-state">
          <span class="spinner-lg" />
          <p class="gen-label">Tailoring your application with Gemini…</p>
          <p class="gen-sub">Writing CV · Cover letter{{ questionsText ? ' · Q&A answers' : '' }}</p>
        </div>

        <!-- Step 4: Results -->
        <div v-if="step === 'results'" class="modal-body results-body">
          <div class="result-tabs">
            <button v-for="t in availableTabs" :key="t.key" class="result-tab" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">
              {{ t.label }}
            </button>
          </div>

          <!-- CV tab -->
          <div v-if="activeTab === 'cv'" class="result-panel">
            <div class="panel-actions">
              <button class="btn-copy" @click="copyText(materials.tailored_cv)">{{ copied === 'cv' ? '✓ Copied' : 'Copy markdown' }}</button>
              <button class="btn-pdf" @click="printCV">Download PDF</button>
            </div>
            <div class="cv-preview" v-html="renderedCV" />
          </div>

          <!-- Cover letter tab -->
          <div v-if="activeTab === 'cl'" class="result-panel">
            <div class="panel-actions">
              <button class="btn-copy" @click="copyText(materials.cover_letter)">{{ copied === 'cl' ? '✓ Copied' : 'Copy text' }}</button>
            </div>
            <div class="text-preview">{{ materials.cover_letter }}</div>
          </div>

          <!-- Q&A tab -->
          <div v-if="activeTab === 'qa'" class="result-panel">
            <div class="qa-pairs">
              <div v-for="(pair, i) in parsedQA" :key="i" class="qa-pair">
                <div class="qa-q">{{ pair.q }}</div>
                <div class="qa-a">{{ pair.a }}</div>
                <button class="btn-copy-sm" @click="copyText(pair.a)">{{ copied === `qa-${i}` ? '✓' : 'Copy' }}</button>
              </div>
            </div>
          </div>

          <div class="step-footer" style="margin-top:1rem">
            <button class="btn-back" @click="step = 'feats'; resetResults()">Generate again</button>
          </div>
        </div>

        <!-- Error -->
        <div v-if="step === 'error'" class="modal-body center-state error-state">
          <div class="error-icon">⚠</div>
          <p>{{ errorMsg }}</p>
          <button class="btn-back" @click="step = 'questions'">← Try again</button>
        </div>
      </div>

      <!-- Hidden print area for PDF -->
      <div id="cv-print-area" v-html="renderedCV" />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
interface Job { id: string; title: string; company: string; description?: string }

const props = defineProps<{ modelValue: boolean; job: Job | null }>()
const emit = defineEmits(['update:modelValue'])

const config = useRuntimeConfig()
const api = config.public.apiBase

const step = ref<'feats'|'questions'|'generating'|'results'|'error'>('feats')
const loadingFeats = ref(false)
const generating = ref(false)
const errorMsg = ref('')
const questionsText = ref('')
const rankedFeats = ref<any[]>([])
const selectedIds = ref(new Set<string>())
const materials = ref<any>({})
const activeTab = ref('cv')
const copied = ref('')

const availableTabs = computed(() => {
  const tabs = [{ key: 'cv', label: '📄 Tailored CV' }, { key: 'cl', label: '✉️ Cover Letter' }]
  if (materials.value.qa_answers) tabs.push({ key: 'qa', label: '💬 Q&A Answers' })
  return tabs
})

// Simple markdown → HTML (no external lib needed)
const renderedCV = computed(() => {
  if (!materials.value.tailored_cv) return ''
  return materials.value.tailored_cv
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hul])/gm, '')
    .replace(/^(.+)$/gm, (line) => line.startsWith('<') ? line : `<p>${line}</p>`)
    .replace(/<p><\/p>/g, '')
})

const parsedQA = computed(() => {
  if (!materials.value.qa_answers) return []
  const pairs: { q: string; a: string }[] = []
  const blocks = materials.value.qa_answers.split(/\n\s*\n/)
  for (const block of blocks) {
    const qMatch = block.match(/\*\*Q:\s*(.+?)\*\*/s)
    const aMatch = block.match(/A:\s*(.+)/s)
    if (qMatch && aMatch) {
      pairs.push({ q: qMatch[1].trim(), a: aMatch[1].trim() })
    }
  }
  return pairs
})

const toggleFeat = (id: string) => {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
}

const copyText = async (text: string, key = 'cv') => {
  await navigator.clipboard.writeText(text)
  copied.value = key
  setTimeout(() => { copied.value = '' }, 2000)
}

const loadSuggestions = async () => {
  if (!props.job) return
  loadingFeats.value = true
  step.value = 'feats'
  try {
    const res = await fetch(`${api}/api/jobs/${props.job.id}/suggest-feats`, {
      method: 'POST', credentials: 'include'
    })
    const data = res.ok ? await res.json() : { feats: [] }
    rankedFeats.value = data.feats
    selectedIds.value = new Set(data.feats.filter((f: any) => f.suggested !== false).map((f: any) => f.id))
  } catch {
    rankedFeats.value = []
  } finally {
    loadingFeats.value = false
  }
}

const generate = async () => {
  if (!props.job) return
  step.value = 'generating'
  generating.value = true
  try {
    const res = await fetch(`${api}/api/jobs/${props.job.id}/materials`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        selected_feat_ids: [...selectedIds.value],
        application_questions: questionsText.value || null
      })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Generation failed')
    }
    materials.value = await res.json()
    activeTab.value = 'cv'
    step.value = 'results'
  } catch (e: any) {
    errorMsg.value = e.message || 'Failed to generate application materials.'
    step.value = 'error'
  } finally {
    generating.value = false
  }
}

const printCV = () => {
  window.print()
}

const resetResults = () => {
  materials.value = {}
  questionsText.value = ''
  loadSuggestions()
}

watch(() => props.modelValue, (open) => {
  if (open && props.job) {
    step.value = 'feats'
    materials.value = {}
    questionsText.value = ''
    errorMsg.value = ''
    loadSuggestions()
  }
})
</script>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
  display: flex; align-items: flex-start; justify-content: center;
  padding: 2rem 1rem; overflow-y: auto;
}

.modal-shell {
  width: 100%; max-width: 720px;
  background: #111318; border: 1px solid rgba(255,255,255,0.09);
  border-radius: 18px; overflow: hidden;
  box-shadow: 0 24px 64px rgba(0,0,0,0.6);
}

.modal-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 1rem; padding: 1.5rem 1.75rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.modal-label { font-size: 0.72rem; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 0.3rem; }
.modal-title { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; }
.modal-sub { font-size: 0.85rem; color: #64748b; margin-top: 0.2rem; }
.modal-close { background: rgba(255,255,255,0.05); border: none; color: #475569; width: 30px; height: 30px; border-radius: 8px; font-size: 0.85rem; transition: all 0.15s; flex-shrink: 0; }
.modal-close:hover { color: #f1f5f9; background: rgba(255,255,255,0.1); }

.modal-body { padding: 1.5rem 1.75rem; }

.center-state {
  display: flex; flex-direction: column; align-items: center; gap: 1rem;
  padding: 3rem 1.75rem; text-align: center;
}
.center-state p { font-size: 0.9rem; color: #64748b; }

.step-intro { margin-bottom: 1.25rem; }
.step-intro h3 { font-size: 1rem; font-weight: 600; color: #f1f5f9; margin-bottom: 0.3rem; }
.step-intro p { font-size: 0.85rem; color: #64748b; }
.optional { color: #334155; font-weight: 400; font-size: 0.8rem; }

.no-feats-hint { font-size: 0.875rem; color: #475569; padding: 1.5rem 0; }
.no-feats-hint a { color: #10b981; }

.feats-list { display: flex; flex-direction: column; gap: 0.5rem; max-height: 380px; overflow-y: auto; padding-right: 0.25rem; }
.feat-row {
  display: flex; align-items: flex-start; gap: 0.875rem;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px; padding: 0.875rem 1rem; cursor: pointer; transition: all 0.15s;
}
.feat-row:hover { border-color: rgba(255,255,255,0.1); }
.feat-row.selected { border-color: rgba(16,185,129,0.3); background: rgba(16,185,129,0.05); }
.feat-row input[type=checkbox] { margin-top: 2px; accent-color: #10b981; flex-shrink: 0; }
.feat-info { flex: 1; min-width: 0; }
.feat-row-title { font-size: 0.875rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.2rem; }
.feat-row-desc { font-size: 0.8rem; color: #64748b; line-height: 1.5; }
.feat-reason { font-size: 0.75rem; color: #475569; margin-top: 0.4rem; display: flex; align-items: center; gap: 0.4rem; }
.reason-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.reason-dot.good { background: #10b981; }
.reason-dot.dim { background: #334155; }

.step-footer { display: flex; align-items: center; justify-content: space-between; margin-top: 1.25rem; padding-top: 1.25rem; border-top: 1px solid rgba(255,255,255,0.05); }
.sel-count { font-size: 0.8rem; color: #64748b; }

.btn-primary {
  background: linear-gradient(135deg,#10b981,#059669); color: #fff; border: none;
  border-radius: 10px; padding: 0.7rem 1.5rem; font-size: 0.875rem; font-weight: 600;
  display: flex; align-items: center; gap: 0.5rem; transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(16,185,129,0.3);
}
.btn-primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(16,185,129,0.4); }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }

.btn-back {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  color: #64748b; border-radius: 10px; padding: 0.65rem 1.125rem;
  font-size: 0.875rem; font-weight: 500; transition: all 0.15s;
}
.btn-back:hover { color: #cbd5e1; }

.questions-area {
  width: 100%; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px; padding: 0.875rem 1rem; font-family: inherit;
  font-size: 0.875rem; color: #e2e8f0; outline: none; resize: vertical;
  line-height: 1.7; transition: border-color 0.15s;
}
.questions-area:focus { border-color: rgba(16,185,129,0.4); }
.questions-area::placeholder { color: #334155; }

.gen-label { font-size: 1rem; font-weight: 600; color: #f1f5f9; }
.gen-sub { font-size: 0.85rem; color: #64748b; }

.results-body {}
.result-tabs { display: flex; gap: 0.375rem; margin-bottom: 1.25rem; }
.result-tab {
  padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.82rem; font-weight: 500;
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
  color: #64748b; transition: all 0.15s;
}
.result-tab:hover { color: #cbd5e1; }
.result-tab.active { background: rgba(16,185,129,0.1); border-color: rgba(16,185,129,0.3); color: #10b981; }

.result-panel { display: flex; flex-direction: column; gap: 0.75rem; }
.panel-actions { display: flex; gap: 0.5rem; justify-content: flex-end; }

.btn-copy, .btn-pdf {
  font-size: 0.78rem; font-weight: 500; padding: 0.4rem 0.875rem; border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.04);
  color: #94a3b8; transition: all 0.15s;
}
.btn-copy:hover { color: #f1f5f9; border-color: rgba(255,255,255,0.18); }
.btn-pdf {
  background: rgba(16,185,129,0.1); border-color: rgba(16,185,129,0.3); color: #10b981;
}
.btn-pdf:hover { background: rgba(16,185,129,0.18); }

.cv-preview {
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px; padding: 1.5rem; max-height: 420px; overflow-y: auto;
  font-size: 0.875rem; line-height: 1.7; color: #e2e8f0;
}
.cv-preview :deep(h1) { font-size: 1.25rem; font-weight: 700; color: #f1f5f9; margin-bottom: 0.5rem; }
.cv-preview :deep(h2) { font-size: 1rem; font-weight: 700; color: #10b981; margin: 1rem 0 0.4rem; border-bottom: 1px solid rgba(16,185,129,0.2); padding-bottom: 0.25rem; }
.cv-preview :deep(h3) { font-size: 0.9rem; font-weight: 600; color: #cbd5e1; margin: 0.75rem 0 0.25rem; }
.cv-preview :deep(ul) { padding-left: 1.25rem; }
.cv-preview :deep(li) { margin-bottom: 0.25rem; color: #94a3b8; }
.cv-preview :deep(strong) { color: #f1f5f9; }
.cv-preview :deep(p) { margin-bottom: 0.5rem; color: #94a3b8; }

.text-preview {
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px; padding: 1.5rem; max-height: 420px; overflow-y: auto;
  font-size: 0.875rem; line-height: 1.85; color: #cbd5e1; white-space: pre-wrap;
}

.qa-pairs { display: flex; flex-direction: column; gap: 1rem; max-height: 420px; overflow-y: auto; }
.qa-pair {
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px; padding: 1rem 1.125rem; position: relative;
}
.qa-q { font-size: 0.825rem; font-weight: 600; color: #10b981; margin-bottom: 0.5rem; }
.qa-a { font-size: 0.875rem; color: #94a3b8; line-height: 1.7; padding-right: 3rem; }
.btn-copy-sm {
  position: absolute; top: 0.75rem; right: 0.875rem;
  font-size: 0.72rem; font-weight: 500; padding: 0.25rem 0.6rem; border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.04);
  color: #64748b; transition: all 0.15s;
}
.btn-copy-sm:hover { color: #f1f5f9; }

.error-state { gap: 1rem; }
.error-icon { font-size: 2rem; }
.error-state p { font-size: 0.875rem; color: #f87171; }

.spinner {
  width: 15px; height: 15px; border: 2px solid rgba(255,255,255,0.25);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block;
}
.spinner-lg {
  width: 36px; height: 36px; border: 3px solid rgba(16,185,129,0.2);
  border-top-color: #10b981; border-radius: 50%; animation: spin 0.8s linear infinite; display: block;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>

<style>
/* Print styles for CV PDF — global so they apply to the hidden print area */
@media print {
  body > *:not(#cv-print-area) { display: none !important; }
  #cv-print-area {
    display: block !important;
    font-family: Georgia, serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #000;
    padding: 2cm;
    max-width: 100%;
  }
  #cv-print-area h1 { font-size: 18pt; margin-bottom: 4pt; }
  #cv-print-area h2 { font-size: 13pt; border-bottom: 1px solid #ccc; padding-bottom: 3pt; margin-top: 14pt; margin-bottom: 6pt; }
  #cv-print-area h3 { font-size: 11pt; font-weight: bold; margin-bottom: 2pt; }
  #cv-print-area ul { margin-left: 16pt; }
  #cv-print-area li { margin-bottom: 2pt; }
  #cv-print-area p { margin-bottom: 6pt; }
}
#cv-print-area { display: none; }
</style>
