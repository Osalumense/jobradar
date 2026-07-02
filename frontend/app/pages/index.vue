<template>
  <div class="dashboard">
    <!-- Greeting -->
    <div class="greeting">
      <h1>Welcome back, {{ firstName }}!</h1>
      <p>Let's track your career.</p>
    </div>

    <!-- Quick stats -->
    <section class="stats-row">
      <div class="stat-card">
        <div class="stat-label">Total Applications</div>
        <div class="stat-value">{{ stats.totalApps }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Interviews</div>
        <div class="stat-value">{{ stats.interviews }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Offers</div>
        <div class="stat-value">{{ stats.offers }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Saved Jobs</div>
        <div class="stat-value">{{ jobs.length }}</div>
      </div>
    </section>

    <!-- Feed + Filter panel -->
    <div class="feed-layout">

      <!-- Job feed -->
      <section class="feed-col">
        <div class="feed-header">
          <h2>Recent Job Postings</h2>
          <div class="feed-header-right">
            <div class="source-select-wrap">
              <span class="source-label">Source:</span>
              <select v-model="sourceFilter" class="source-select">
                <option value="">All</option>
                <option value="wttj">WTTJ</option>
                <option value="hellowork">HelloWork</option>
                <option value="francetravail">France Travail</option>
                <option value="lesjeudis">LesJeudis</option>
                <option value="remotive">Remotive</option>
              </select>
            </div>
            <button class="btn-scan" :class="{ scanning }" :disabled="scanning" @click="triggerScraper">
              <span v-if="scanning" class="spinner-sm" />
              <svg v-else viewBox="0 0 24 24" width="14" height="14"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
              {{ scanning ? 'Scanning…' : 'Scan Now' }}
            </button>
          </div>
        </div>

        <div v-if="matching" class="matching-banner">
          <span class="spinner-sm" />
          Matching jobs to your profile… this takes about a minute.
          <button class="btn-refresh" @click="fetchJobs">Refresh</button>
        </div>

        <div v-if="loading && jobs.length === 0" class="loading-feed">
          <div v-for="i in 4" :key="i" class="skeleton-card" />
        </div>

        <div v-else class="job-list">
          <div
            v-for="job in filteredJobs"
            :key="job.id"
            class="job-card"
            @click="openJob(job)"
          >
            <div class="job-logo">
              <span>{{ (job.company || 'J')[0].toUpperCase() }}</span>
            </div>

            <div class="job-info">
              <div class="job-title">{{ job.title }}</div>
              <div class="job-meta">
                {{ job.company }} •
                <span class="contract-badge" :class="job.contract_type?.toLowerCase()">{{ job.contract_type?.toUpperCase() || 'CDI' }}</span>
              </div>
              <div class="job-location">
                <svg viewBox="0 0 24 24" width="12" height="12"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                {{ job.location || 'Remote' }}
              </div>
            </div>

            <div class="match-pill" :class="scoreClass(job.composite_score)">
              <span class="match-pct">{{ Math.round((job.composite_score || 0) * 100) }}%</span>
              <span class="match-label">match</span>
            </div>
          </div>

          <!-- Pagination -->
          <div class="load-more-row">
            <div v-if="loadingMore" class="loading-more">
              <span class="spinner-sm" /> Loading more jobs…
            </div>
            <button v-else-if="!allLoaded && jobs.length > 0" class="btn-load-more" @click="loadMore">
              Load more <span class="load-more-count">({{ jobs.length }} / {{ total }})</span>
            </button>
            <div v-else-if="allLoaded && jobs.length > 0" class="all-loaded">
              All {{ total }} jobs loaded
            </div>
          </div>

          <div v-if="filteredJobs.length === 0 && !loading" class="empty-feed">
            <svg viewBox="0 0 24 24" width="40" height="40"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <p>No jobs yet — click <strong>Scan Now</strong> to fetch from all sources.</p>
          </div>
        </div>
      </section>

      <!-- Right panel -->
      <aside class="right-panel">
        <!-- Filter -->
        <div class="panel-card">
          <h3 class="panel-title">Filter</h3>

          <div class="filter-section">
            <div class="filter-label">Job Type</div>
            <div class="filter-chips">
              <button
                v-for="t in contractTypes"
                :key="t.value"
                class="chip"
                :class="{ 'chip-active': selectedContracts.includes(t.value) }"
                @click="toggleContract(t.value)"
              >{{ t.label }}</button>
            </div>
          </div>

          <div class="filter-section">
            <div class="filter-label">Location</div>
            <input v-model="locationFilter" class="filter-input" placeholder="e.g. Paris" />
          </div>

          <button class="btn-rescore" :disabled="rescoring" @click="doRescore">
            <span v-if="rescoring" class="spinner-sm" />
            {{ rescoring ? 'Rescoring…' : 'Rescore All Jobs' }}
          </button>
        </div>

        <!-- Pipeline -->
        <div class="panel-card">
          <h3 class="panel-title">My Application Pipeline</h3>
          <div class="pipeline-tabs">
            <button
              v-for="s in pipelineStages"
              :key="s.value"
              class="pipeline-tab"
              :class="{ 'tab-active': pipelineFilter === s.value }"
              @click="pipelineFilter = s.value"
            >{{ s.label }}</button>
          </div>
          <div class="pipeline-count">
            <span class="pipeline-num">{{ pipelineCount }}</span>
            <span class="pipeline-sub">jobs in this stage</span>
          </div>
        </div>

        <!-- Search queries -->
        <div class="panel-card">
          <h3 class="panel-title">Active Search Queries</h3>
          <ul class="query-list">
            <li v-for="(q, i) in searchQueries" :key="i" class="query-item">
              <span class="query-dot" />
              {{ q }}
            </li>
            <li v-if="!searchQueries.length" class="query-empty">No queries — set up your profile.</li>
          </ul>
        </div>
      </aside>
    </div>

    <!-- Job detail drawer -->
    <Transition name="drawer">
      <div v-if="activeJob" class="drawer-backdrop" @click.self="activeJob = null">
        <div class="drawer">
          <div class="drawer-header">
            <div class="drawer-logo">{{ (activeJob.company || 'J')[0].toUpperCase() }}</div>
            <div class="drawer-meta">
              <div class="drawer-title">{{ activeJob.title }}</div>
              <div class="drawer-company">{{ activeJob.company }} · {{ activeJob.location }}</div>
            </div>
            <button class="drawer-close" @click="activeJob = null">
              <svg viewBox="0 0 24 24" width="18" height="18"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <div class="score-breakdown">
            <div class="score-item score-green">
              <span class="score-val">{{ pct(activeJob.semantic_score) }}</span>
              <span class="score-key">Semantic</span>
            </div>
            <div class="score-item score-blue">
              <span class="score-val">{{ pct(activeJob.tfidf_score) }}</span>
              <span class="score-key">Keywords</span>
            </div>
            <div class="score-item score-purple">
              <span class="score-val">{{ pct(activeJob.recency_score) }}</span>
              <span class="score-key">Recency</span>
            </div>
          </div>

          <div class="drawer-desc" v-html="formatDesc(activeJob.description)" />

          <div class="drawer-actions">
            <a :href="activeJob.url" target="_blank" class="btn-view">View Posting ↗</a>
            <button class="btn-prepare" @click="openApply(activeJob)">✨ Prepare Application</button>
          </div>
        </div>
      </div>
    </Transition>

    <ApplicationModal v-model="showApplyModal" :job="applyJob" />
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const { user } = useAuth()
const { get, post } = useApi()

const firstName = computed(() => {
  const name = user.value?.username || 'there'
  return name.charAt(0).toUpperCase() + name.slice(1)
})

const PAGE_SIZE = 20

const jobs = ref<any[]>([])
const total = ref(0)
const offset = ref(0)
const loadingMore = ref(false)
const allLoaded = ref(false)
const searchQueries = ref<string[]>([])
const loading = ref(true)
const scanning = ref(false)
const rescoring = ref(false)
const activeJob = ref<any>(null)
const showApplyModal = ref(false)
const applyJob = ref<any>(null)

const openApply = (job: any) => {
  applyJob.value = job
  showApplyModal.value = true
}
const sourceFilter = ref('')
const locationFilter = ref('')
const selectedContracts = ref<string[]>([])
const pipelineFilter = ref('applied')

const contractTypes = [
  { label: 'CDI', value: 'cdi' },
  { label: 'Alternance', value: 'alternance' },
  { label: 'Internship', value: 'stage' },
  { label: 'CDD', value: 'cdd' },
]

const pipelineStages = [
  { label: 'Applied', value: 'applied' },
  { label: 'Reviewing', value: 'reviewed' },
  { label: 'Interviewing', value: 'interviewing' },
  { label: 'Offer', value: 'offer' },
]

const stats = computed(() => ({
  totalApps: jobs.value.filter(j => j.status !== 'new').length,
  interviews: jobs.value.filter(j => j.status === 'interviewing').length,
  offers: jobs.value.filter(j => j.status === 'offer').length,
}))

const pipelineCount = computed(() =>
  jobs.value.filter(j => j.status === pipelineFilter.value).length
)

const filteredJobs = computed(() => {
  return jobs.value.filter(j => {
    if (sourceFilter.value && j.source !== sourceFilter.value) return false
    if (locationFilter.value && !j.location?.toLowerCase().includes(locationFilter.value.toLowerCase())) return false
    if (selectedContracts.value.length && !selectedContracts.value.includes(j.contract_type?.toLowerCase())) return false
    return true
  })
})

const toggleContract = (v: string) => {
  const idx = selectedContracts.value.indexOf(v)
  if (idx >= 0) selectedContracts.value.splice(idx, 1)
  else selectedContracts.value.push(v)
}

const scoreClass = (s: number | null) => {
  const p = (s || 0) * 100
  if (p >= 75) return 'match-high'
  if (p >= 55) return 'match-mid'
  return 'match-low'
}

const pct = (v: number | null | undefined) =>
  v == null ? '—' : `${Math.round(v * 100)}%`

const formatDesc = (txt: string) =>
  (txt || '').replace(/<[^>]+>/g, '').slice(0, 800) + '…'

const openJob = (job: any) => { activeJob.value = job }

const matching = ref(false)

const fetchJobs = async () => {
  loading.value = true
  offset.value = 0
  allLoaded.value = false
  try {
    const data = await get(`/api/jobs?limit=${PAGE_SIZE}&offset=0`)
    jobs.value = data.jobs ?? []
    total.value = data.total ?? 0
    allLoaded.value = jobs.value.length >= total.value
  } catch {}
  loading.value = false
}

const loadMore = async () => {
  if (loadingMore.value || allLoaded.value) return
  loadingMore.value = true
  try {
    const nextOffset = offset.value + PAGE_SIZE
    const data = await get(`/api/jobs?limit=${PAGE_SIZE}&offset=${nextOffset}`)
    const newJobs = data.jobs ?? []
    jobs.value = [...jobs.value, ...newJobs]
    offset.value = nextOffset
    total.value = data.total ?? total.value
    allLoaded.value = jobs.value.length >= total.value
  } catch {}
  loadingMore.value = false
}

const autoMatchIfNeeded = async () => {
  const hasScores = jobs.value.some(j => j.composite_score != null)
  if (!hasScores && jobs.value.length > 0) {
    matching.value = true
    try {
      await post('/api/rescore?limit=100')
      let attempts = 0
      const iv = setInterval(async () => {
        await fetchJobs()
        const done = jobs.value.some(j => j.composite_score != null)
        if (done || ++attempts >= 12) {
          clearInterval(iv)
          matching.value = false
        }
      }, 8000)
    } catch {
      matching.value = false
    }
  }
}

const fetchProfile = async () => {
  try {
    const data = await get('/api/profile')
    searchQueries.value = data.matching_criteria?.search_queries ?? []
  } catch {}
}

const triggerScraper = async () => {
  scanning.value = true
  try {
    await post('/api/scrape')
    const prevTotal = total.value
    let attempts = 0
    const iv = setInterval(async () => {
      await fetchJobs()
      attempts++
      if (total.value > prevTotal || attempts >= 20) {
        clearInterval(iv)
        scanning.value = false
      }
    }, 9000)
  } catch { scanning.value = false }
}

const doRescore = async () => {
  rescoring.value = true
  try {
    await post('/api/rescore?limit=100')
    setTimeout(async () => { await fetchJobs(); rescoring.value = false }, 65000)
  } catch { rescoring.value = false }
}

onMounted(async () => {
  await fetchJobs()
  fetchProfile()
  autoMatchIfNeeded()
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 1.75rem; }

/* Greeting */
.greeting h1 { font-size: 1.75rem; font-weight: 700; color: #f1f5f9; line-height: 1.2; }
.greeting p { font-size: 1rem; color: #64748b; margin-top: 0.25rem; }

/* Stats */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}
@media (max-width: 900px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
}
.stat-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 1.25rem 1.5rem;
}
.stat-label { font-size: 0.8rem; color: #64748b; margin-bottom: 0.5rem; }
.stat-value { font-size: 2rem; font-weight: 700; color: #f1f5f9; line-height: 1; }

/* Layout */
.feed-layout {
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: 1.25rem;
  align-items: start;
}
@media (max-width: 900px) {
  .feed-layout { grid-template-columns: 1fr; }
  .right-panel { display: grid; grid-template-columns: 1fr 1fr; }
}

/* Feed */
.feed-col { display: flex; flex-direction: column; gap: 1rem; }

.feed-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.feed-header h2 { font-size: 1.05rem; font-weight: 600; color: #f1f5f9; }
.feed-header-right { display: flex; align-items: center; gap: 0.75rem; }

.source-select-wrap { display: flex; align-items: center; gap: 0.5rem; }
.source-label { font-size: 0.8rem; color: #64748b; }
.source-select {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  color: #cbd5e1;
  font-family: inherit;
  font-size: 0.8rem;
  padding: 0.3rem 0.6rem;
  outline: none;
}

.btn-scan {
  display: flex; align-items: center; gap: 0.375rem;
  background: rgba(16,185,129,0.1);
  border: 1px solid rgba(16,185,129,0.25);
  color: #10b981;
  border-radius: 8px;
  padding: 0.4rem 0.875rem;
  font-size: 0.8rem;
  font-weight: 600;
  transition: all 0.15s;
}
.btn-scan:hover:not(:disabled) { background: rgba(16,185,129,0.18); }
.btn-scan:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-scan.scanning { opacity: 0.7; }

/* Skeletons */
.loading-feed { display: flex; flex-direction: column; gap: 0.75rem; }
.load-more-row { padding: 1.5rem 0; display: flex; justify-content: center; }
.loading-more { display: flex; align-items: center; gap: 0.5rem; color: #64748b; font-size: 0.85rem; }
.all-loaded { color: #374151; font-size: 0.8rem; }
.btn-load-more {
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  color: #94a3b8; border-radius: 10px; padding: 0.6rem 1.5rem;
  font-size: 0.875rem; transition: all 0.15s;
}
.btn-load-more:hover { background: rgba(255,255,255,0.09); color: #e2e8f0; border-color: rgba(255,255,255,0.18); }
.load-more-count { color: #475569; font-size: 0.8rem; }
.matching-banner {
  display: flex; align-items: center; gap: 0.75rem;
  background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2);
  border-radius: 10px; padding: 0.75rem 1rem;
  font-size: 0.875rem; color: #6ee7b7; margin-bottom: 0.5rem;
}
.btn-refresh {
  margin-left: auto; background: none; border: 1px solid rgba(16,185,129,0.4);
  color: #6ee7b7; border-radius: 6px; padding: 0.25rem 0.6rem;
  font-size: 0.8rem;
}
.btn-refresh:hover { background: rgba(16,185,129,0.1); }

.skeleton-card {
  height: 88px; border-radius: 14px;
  background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }

/* Job cards */
.job-list { display: flex; flex-direction: column; gap: 0.75rem; }

.job-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 1.125rem 1.25rem;
  cursor: pointer;
  transition: all 0.15s ease;
}
.job-card:hover {
  background: rgba(255,255,255,0.045);
  border-color: rgba(255,255,255,0.1);
  transform: translateY(-1px);
}

.job-logo {
  width: 44px; height: 44px; flex-shrink: 0;
  background: linear-gradient(135deg, #1e293b, #0f172a);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; font-weight: 700; color: #10b981;
}

.job-info { flex: 1; min-width: 0; }
.job-title { font-size: 0.925rem; font-weight: 600; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.job-meta { font-size: 0.8rem; color: #64748b; margin: 0.2rem 0; display: flex; align-items: center; gap: 0.375rem; }
.job-location { font-size: 0.78rem; color: #475569; display: flex; align-items: center; gap: 0.25rem; }

.contract-badge {
  font-size: 0.7rem; font-weight: 700; padding: 0.1rem 0.45rem;
  border-radius: 4px; text-transform: uppercase;
}
.contract-badge.alternance { background: rgba(16,185,129,0.12); color: #10b981; }
.contract-badge.cdi { background: rgba(99,102,241,0.12); color: #818cf8; }
.contract-badge.stage { background: rgba(245,158,11,0.12); color: #f59e0b; }
.contract-badge.cdd { background: rgba(59,130,246,0.12); color: #60a5fa; }

/* Match pill — rounded square like the mockup */
.match-pill {
  flex-shrink: 0;
  width: 62px; height: 62px;
  border-radius: 14px;
  border: 2px solid;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 1px;
}
.match-high { border-color: #10b981; background: rgba(16,185,129,0.08); color: #10b981; box-shadow: 0 0 12px rgba(16,185,129,0.2); }
.match-mid  { border-color: #3b82f6; background: rgba(59,130,246,0.08); color: #60a5fa; box-shadow: 0 0 12px rgba(59,130,246,0.15); }
.match-low  { border-color: #f97316; background: rgba(249,115,22,0.08); color: #fb923c; }

.match-pct { font-size: 1rem; font-weight: 700; line-height: 1; }
.match-label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; }

.empty-feed {
  padding: 3rem 2rem;
  text-align: center;
  color: #475569;
  display: flex; flex-direction: column; align-items: center; gap: 1rem;
  border: 1px dashed rgba(255,255,255,0.06);
  border-radius: 14px;
}
.empty-feed strong { color: #10b981; }

/* Right panel */
.right-panel { display: flex; flex-direction: column; gap: 1rem; min-width: 0; overflow: hidden; }

.panel-card {
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 1.25rem;
  overflow: hidden;
  min-width: 0;
}

.panel-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 1rem;
  text-transform: none;
  letter-spacing: 0;
}

.filter-section { margin-bottom: 1rem; }
.filter-label { font-size: 0.75rem; color: #64748b; margin-bottom: 0.5rem; }
.filter-chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }

.chip {
  font-size: 0.78rem; font-weight: 500;
  padding: 0.3rem 0.7rem; border-radius: 20px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: #94a3b8;
  transition: all 0.15s;
}
.chip:hover { border-color: rgba(16,185,129,0.3); color: #10b981; }
.chip-active { background: rgba(16,185,129,0.12); border-color: rgba(16,185,129,0.35); color: #10b981; }

.filter-input {
  width: 100%;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 0.5rem 0.75rem;
  font-size: 0.85rem;
  color: #e2e8f0;
  font-family: inherit;
  outline: none;
}
.filter-input::placeholder { color: #334155; }
.filter-input:focus { border-color: rgba(16,185,129,0.4); }

.btn-rescore {
  width: 100%; margin-top: 0.25rem;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 0.6rem;
  color: #94a3b8;
  font-size: 0.83rem;
  font-weight: 500;
  display: flex; align-items: center; justify-content: center; gap: 0.5rem;
  transition: all 0.15s;
}
.btn-rescore:hover:not(:disabled) { color: #e2e8f0; border-color: rgba(255,255,255,0.14); }
.btn-rescore:disabled { opacity: 0.5; cursor: not-allowed; }

/* Pipeline */
.pipeline-tabs { display: flex; flex-wrap: wrap; gap: 0.375rem; margin-bottom: 1rem; }
.pipeline-tab {
  font-size: 0.78rem; font-weight: 500; padding: 0.3rem 0.75rem;
  border-radius: 20px; border: 1px solid rgba(255,255,255,0.07);
  background: transparent; color: #64748b; transition: all 0.15s;
}
.pipeline-tab:hover { color: #cbd5e1; }
.tab-active { background: rgba(16,185,129,0.12); border-color: rgba(16,185,129,0.3); color: #10b981; }

.pipeline-count { display: flex; align-items: baseline; gap: 0.5rem; }
.pipeline-num { font-size: 2rem; font-weight: 700; color: #f1f5f9; }
.pipeline-sub { font-size: 0.8rem; color: #475569; }

/* Queries */
.query-list { list-style: none; display: flex; flex-direction: column; gap: 0.5rem; }
.query-item { display: flex; align-items: flex-start; gap: 0.5rem; font-size: 0.8rem; color: #94a3b8; line-height: 1.4; }
.query-dot { width: 6px; height: 6px; border-radius: 50%; background: #10b981; flex-shrink: 0; margin-top: 5px; box-shadow: 0 0 6px rgba(16,185,129,0.5); }
.query-empty { font-size: 0.8rem; color: #475569; font-style: italic; }

/* Spinner */
.spinner-sm {
  width: 12px; height: 12px;
  border: 2px solid rgba(255,255,255,0.2);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Drawer */
.drawer-backdrop {
  position: fixed; inset: 0; z-index: 50;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(4px);
  display: flex; justify-content: flex-end;
}
.drawer {
  width: 480px; max-width: 95vw;
  background: #13161d;
  border-left: 1px solid rgba(255,255,255,0.07);
  height: 100%;
  overflow-y: auto;
  padding: 2rem;
  display: flex; flex-direction: column; gap: 1.5rem;
}
.drawer-header { display: flex; align-items: center; gap: 1rem; }
.drawer-logo {
  width: 48px; height: 48px; flex-shrink: 0;
  background: linear-gradient(135deg, #1e293b, #0f172a);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.25rem; font-weight: 700; color: #10b981;
}
.drawer-meta { flex: 1; min-width: 0; }
.drawer-title { font-size: 1.05rem; font-weight: 600; color: #f1f5f9; }
.drawer-company { font-size: 0.85rem; color: #64748b; margin-top: 0.2rem; }
.drawer-close {
  width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0;
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
  color: #64748b; display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.drawer-close:hover { color: #e2e8f0; }

.score-breakdown { display: flex; gap: 0.75rem; }
.score-item {
  flex: 1; border-radius: 10px; padding: 0.875rem;
  display: flex; flex-direction: column; align-items: center; gap: 0.25rem;
  border: 1px solid;
}
.score-val { font-size: 1.25rem; font-weight: 700; }
.score-key { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.7; }
.score-green { border-color: rgba(16,185,129,0.3); background: rgba(16,185,129,0.06); color: #10b981; }
.score-blue  { border-color: rgba(59,130,246,0.3);  background: rgba(59,130,246,0.06);  color: #60a5fa; }
.score-purple{ border-color: rgba(167,139,250,0.3); background: rgba(167,139,250,0.06); color: #c084fc; }

.drawer-desc {
  font-size: 0.875rem; color: #94a3b8; line-height: 1.75;
  white-space: pre-wrap;
}
.drawer-actions { margin-top: auto; }
.btn-view {
  display: inline-flex; align-items: center;
  background: rgba(16,185,129,0.1);
  border: 1px solid rgba(16,185,129,0.25);
  color: #10b981;
  padding: 0.7rem 1.25rem;
  border-radius: 10px;
  font-size: 0.875rem; font-weight: 600;
  transition: all 0.15s;
}
.btn-view:hover { background: rgba(16,185,129,0.18); }

.btn-prepare {
  display: inline-flex; align-items: center; gap: 0.4rem;
  background: linear-gradient(135deg,#10b981,#059669); color: #fff; border: none;
  padding: 0.7rem 1.25rem; border-radius: 10px;
  font-size: 0.875rem; font-weight: 600; transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(16,185,129,0.3);
}
.btn-prepare:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(16,185,129,0.4); }

.drawer-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }

/* Drawer transition */
.drawer-enter-active, .drawer-leave-active { transition: transform 0.25s ease; }
.drawer-enter-from, .drawer-leave-to { transform: translateX(100%); }
.drawer-enter-from .drawer-backdrop, .drawer-leave-to .drawer-backdrop { opacity: 0; }
</style>
