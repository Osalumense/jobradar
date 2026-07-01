<template>
  <div class="page">
    <div class="page-header">
      <h1>Top Matches</h1>
      <p>Jobs with the highest compatibility to your profile</p>
    </div>

    <div v-if="loading" class="loading-feed">
      <div v-for="i in 5" :key="i" class="skeleton-card" />
    </div>

    <div v-else class="matches-list">
      <div v-for="(job, idx) in topJobs" :key="job.id" class="match-row">
        <div class="rank">#{{ idx + 1 }}</div>
        <div class="match-logo">{{ (job.company || 'J')[0].toUpperCase() }}</div>
        <div class="match-info">
          <div class="match-title">{{ job.title }}</div>
          <div class="match-sub">{{ job.company }} · {{ job.location || 'Remote' }}</div>
        </div>
        <div class="score-pills">
          <div class="spill green">Semantic {{ pct(job.semantic_score) }}</div>
          <div class="spill blue">Keywords {{ pct(job.tfidf_score) }}</div>
          <div class="spill purple">Recency {{ pct(job.recency_score) }}</div>
        </div>
        <div class="big-score" :class="scoreClass(job.composite_score)">
          {{ Math.round((job.composite_score || 0) * 100) }}%
          <span>match</span>
        </div>
        <a :href="job.url" target="_blank" class="btn-view">View ↗</a>
      </div>

      <div v-if="!topJobs.length" class="empty">
        <p>No scored jobs yet — run a rescore from the Dashboard.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const { get } = useApi()
const jobs = ref<any[]>([])
const loading = ref(true)

const topJobs = computed(() =>
  [...jobs.value]
    .filter(j => j.composite_score != null)
    .sort((a, b) => b.composite_score - a.composite_score)
    .slice(0, 20)
)

const scoreClass = (s: number | null) => {
  const p = (s || 0) * 100
  if (p >= 75) return 'score-high'
  if (p >= 55) return 'score-mid'
  return 'score-low'
}

const pct = (v: number | null | undefined) => v == null ? '—' : `${Math.round(v * 100)}%`

onMounted(async () => {
  loading.value = true
  try { const d = await get('/api/jobs?limit=100'); jobs.value = d.jobs ?? d } catch {}
  loading.value = false
})
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 1.5rem; }
.page-header h1 { font-size: 1.5rem; font-weight: 700; color: #f1f5f9; }
.page-header p { font-size: 0.875rem; color: #64748b; margin-top: 0.25rem; }

.loading-feed { display: flex; flex-direction: column; gap: 0.75rem; }
.skeleton-card { height: 72px; border-radius: 12px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); animation: shimmer 1.4s infinite; }
@keyframes shimmer { 0%,100% { opacity: 0.6; } 50% { opacity: 1; } }

.matches-list { display: flex; flex-direction: column; gap: 0.625rem; }

.match-row {
  display: flex; align-items: center; gap: 1rem;
  background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px; padding: 1rem 1.25rem;
  transition: all 0.15s;
}
.match-row:hover { background: rgba(255,255,255,0.04); border-color: rgba(255,255,255,0.09); }

.rank { font-size: 1rem; font-weight: 700; color: #334155; width: 28px; flex-shrink: 0; text-align: center; }

.match-logo {
  width: 40px; height: 40px; flex-shrink: 0;
  background: linear-gradient(135deg, #1e293b, #0f172a);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 700; color: #10b981;
}

.match-info { flex: 1; min-width: 0; }
.match-title { font-size: 0.9rem; font-weight: 600; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.match-sub { font-size: 0.78rem; color: #64748b; margin-top: 2px; }

.score-pills { display: flex; gap: 0.375rem; flex-shrink: 0; }
.spill { font-size: 0.72rem; font-weight: 500; padding: 0.2rem 0.55rem; border-radius: 6px; border: 1px solid; }
.spill.green { border-color: rgba(16,185,129,0.25); color: #10b981; background: rgba(16,185,129,0.07); }
.spill.blue  { border-color: rgba(59,130,246,0.25);  color: #60a5fa; background: rgba(59,130,246,0.07); }
.spill.purple{ border-color: rgba(167,139,250,0.25); color: #c084fc; background: rgba(167,139,250,0.07); }

.big-score {
  flex-shrink: 0; font-size: 1.25rem; font-weight: 700;
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  width: 60px;
}
.big-score span { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.7; }
.score-high { color: #10b981; }
.score-mid  { color: #60a5fa; }
.score-low  { color: #fb923c; }

.btn-view {
  flex-shrink: 0; font-size: 0.8rem; font-weight: 600;
  padding: 0.45rem 0.875rem; border-radius: 8px;
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  color: #94a3b8; transition: all 0.15s;
}
.btn-view:hover { color: #e2e8f0; border-color: rgba(255,255,255,0.15); }

.empty { padding: 3rem; text-align: center; color: #475569; font-size: 0.875rem; }
</style>
