<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1>Job Listings</h1>
        <p>All scraped jobs ranked by your profile match score</p>
      </div>
      <button class="btn-scan" :disabled="scanning" @click="triggerScraper">
        <span v-if="scanning" class="spinner-sm" />
        {{ scanning ? 'Scanning…' : 'Scan Job Boards' }}
      </button>
    </div>

    <div class="toolbar">
      <input v-model="search" class="search-input" placeholder="Search jobs, companies…" />
      <select v-model="contractFilter" class="filter-select">
        <option value="">All contracts</option>
        <option value="alternance">Alternance</option>
        <option value="cdi">CDI</option>
        <option value="cdd">CDD</option>
        <option value="stage">Stage</option>
      </select>
      <select v-model="sourceFilter" class="filter-select">
        <option value="">All sources</option>
        <option value="wttj">WTTJ</option>
        <option value="hellowork">HelloWork</option>
        <option value="francetravail">France Travail</option>
        <option value="lesjeudis">LesJeudis</option>
        <option value="remotive">Remotive</option>
      </select>
    </div>

    <div v-if="loading" class="loading-feed">
      <div v-for="i in 6" :key="i" class="skeleton-card" />
    </div>

    <div v-else class="job-table">
      <div class="table-header">
        <span>Job</span>
        <span>Location</span>
        <span>Source</span>
        <span>Contract</span>
        <span class="col-score">Score</span>
        <span></span>
      </div>
      <div v-for="job in filtered" :key="job.id" class="table-row">
        <div class="col-job">
          <div class="job-logo-sm">{{ (job.company || 'J')[0].toUpperCase() }}</div>
          <div>
            <div class="job-title">{{ job.title }}</div>
            <div class="job-company">{{ job.company }}</div>
          </div>
        </div>
        <span class="col-loc">{{ job.location || '—' }}</span>
        <span class="source-badge" :class="job.source">{{ job.source?.toUpperCase() }}</span>
        <span class="contract-badge" :class="job.contract_type?.toLowerCase()">{{ job.contract_type?.toUpperCase() || '—' }}</span>
        <div class="col-score">
          <div class="match-pill" :class="scoreClass(job.composite_score)">
            {{ Math.round((job.composite_score || 0) * 100) }}%
          </div>
        </div>
        <div class="col-actions">
          <a :href="job.url" target="_blank" class="btn-sm">View ↗</a>
        </div>
      </div>
      <div v-if="!filtered.length" class="empty-row">No jobs match your filters.</div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const { get, post } = useApi()
const jobs = ref<any[]>([])
const loading = ref(true)
const scanning = ref(false)
const search = ref('')
const contractFilter = ref('')
const sourceFilter = ref('')

const filtered = computed(() => jobs.value.filter(j => {
  if (contractFilter.value && j.contract_type?.toLowerCase() !== contractFilter.value) return false
  if (sourceFilter.value && j.source !== sourceFilter.value) return false
  if (search.value) {
    const q = search.value.toLowerCase()
    return j.title?.toLowerCase().includes(q) || j.company?.toLowerCase().includes(q)
  }
  return true
}))

const scoreClass = (s: number | null) => {
  const p = (s || 0) * 100
  if (p >= 75) return 'match-high'
  if (p >= 55) return 'match-mid'
  return 'match-low'
}

const fetchJobs = async () => {
  loading.value = true
  try { const d = await get('/api/jobs?limit=100'); jobs.value = d.jobs ?? d } catch {}
  loading.value = false
}

const triggerScraper = async () => {
  scanning.value = true
  try {
    await post('/api/scrape')
    setTimeout(async () => { await fetchJobs(); scanning.value = false }, 55000)
  } catch { scanning.value = false }
}

onMounted(fetchJobs)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 1.5rem; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.page-header h1 { font-size: 1.5rem; font-weight: 700; color: #f1f5f9; }
.page-header p { font-size: 0.875rem; color: #64748b; margin-top: 0.25rem; }

.toolbar { display: flex; gap: 0.75rem; flex-wrap: wrap; }

.search-input, .filter-select {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 0.625rem 0.875rem;
  font-size: 0.875rem;
  color: #e2e8f0;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s;
}
.search-input { flex: 1; min-width: 220px; }
.search-input::placeholder { color: #334155; }
.search-input:focus, .filter-select:focus { border-color: rgba(16,185,129,0.4); }

.loading-feed { display: flex; flex-direction: column; gap: 0.75rem; }
.skeleton-card {
  height: 64px; border-radius: 12px;
  background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }

.job-table { display: flex; flex-direction: column; gap: 2px; }

.table-header {
  display: grid;
  grid-template-columns: 1fr 140px 110px 120px 80px 80px;
  padding: 0.5rem 1.25rem;
  font-size: 0.75rem; color: #475569;
  text-transform: uppercase; letter-spacing: 0.5px;
}

.table-row {
  display: grid;
  grid-template-columns: 1fr 140px 110px 120px 80px 80px;
  align-items: center;
  padding: 0.875rem 1.25rem;
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 12px;
  transition: all 0.15s;
  gap: 0.5rem;
}
.table-row:hover { background: rgba(255,255,255,0.04); border-color: rgba(255,255,255,0.09); }

.col-job { display: flex; align-items: center; gap: 0.75rem; min-width: 0; }
.job-logo-sm {
  width: 36px; height: 36px; flex-shrink: 0;
  background: linear-gradient(135deg, #1e293b, #0f172a);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.9rem; font-weight: 700; color: #10b981;
}
.job-title { font-size: 0.875rem; font-weight: 600; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.job-company { font-size: 0.78rem; color: #64748b; margin-top: 2px; }

.col-loc { font-size: 0.82rem; color: #64748b; }

.source-badge {
  font-size: 0.68rem; font-weight: 700; padding: 0.2rem 0.55rem;
  border-radius: 5px; text-transform: uppercase; width: fit-content;
}
.source-badge.wttj { background: rgba(245,158,11,0.1); color: #f59e0b; border: 1px solid rgba(245,158,11,0.2); }
.source-badge.hellowork { background: rgba(20,184,166,0.1); color: #2dd4bf; border: 1px solid rgba(20,184,166,0.2); }
.source-badge.francetravail { background: rgba(59,130,246,0.1); color: #60a5fa; border: 1px solid rgba(59,130,246,0.2); }
.source-badge.lesjeudis { background: rgba(167,139,250,0.1); color: #c084fc; border: 1px solid rgba(167,139,250,0.2); }
.source-badge.remotive { background: rgba(99,102,241,0.1); color: #818cf8; border: 1px solid rgba(99,102,241,0.2); }

.contract-badge { font-size: 0.72rem; font-weight: 700; padding: 0.2rem 0.55rem; border-radius: 5px; text-transform: uppercase; width: fit-content; }
.contract-badge.alternance { background: rgba(16,185,129,0.12); color: #10b981; }
.contract-badge.cdi { background: rgba(99,102,241,0.12); color: #818cf8; }
.contract-badge.stage { background: rgba(245,158,11,0.12); color: #f59e0b; }
.contract-badge.cdd { background: rgba(59,130,246,0.12); color: #60a5fa; }

.col-score { display: flex; justify-content: center; }
.match-pill {
  font-size: 0.8rem; font-weight: 700;
  padding: 0.25rem 0.6rem; border-radius: 8px; border: 1.5px solid;
}
.match-high { border-color: #10b981; background: rgba(16,185,129,0.08); color: #10b981; }
.match-mid  { border-color: #3b82f6; background: rgba(59,130,246,0.08); color: #60a5fa; }
.match-low  { border-color: #f97316; background: rgba(249,115,22,0.08); color: #fb923c; }

.col-actions { display: flex; justify-content: flex-end; }
.btn-sm {
  font-size: 0.78rem; font-weight: 600;
  padding: 0.3rem 0.7rem; border-radius: 7px;
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  color: #94a3b8; transition: all 0.15s;
}
.btn-sm:hover { color: #e2e8f0; border-color: rgba(255,255,255,0.15); }

.empty-row { padding: 3rem; text-align: center; color: #475569; font-size: 0.875rem; }

.btn-scan {
  display: flex; align-items: center; gap: 0.375rem;
  background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.25);
  color: #10b981; border-radius: 10px; padding: 0.65rem 1.25rem;
  font-size: 0.875rem; font-weight: 600; transition: all 0.15s;
}
.btn-scan:hover:not(:disabled) { background: rgba(16,185,129,0.18); }
.btn-scan:disabled { opacity: 0.6; cursor: not-allowed; }

.spinner-sm {
  width: 12px; height: 12px;
  border: 2px solid rgba(255,255,255,0.2);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
