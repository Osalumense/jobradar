<template>
  <div class="page">
    <div class="page-header">
      <h1>Analytics</h1>
      <p>Pipeline performance and scoring insights</p>
    </div>

    <div class="analytics-grid">
      <div class="metric-card">
        <div class="metric-label">Total Jobs Scraped</div>
        <div class="metric-value">{{ jobs.length }}</div>
        <div class="metric-sub">across all sources</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Avg Match Score</div>
        <div class="metric-value">{{ avgScore }}%</div>
        <div class="metric-sub">composite</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">High Matches (≥75%)</div>
        <div class="metric-value">{{ highMatches }}</div>
        <div class="metric-sub">jobs</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Sources Active</div>
        <div class="metric-value">{{ sourcesCount }}</div>
        <div class="metric-sub">scrapers</div>
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-card">
        <h3>Jobs by Source</h3>
        <div class="bar-chart">
          <div v-for="(count, src) in bySource" :key="src" class="bar-row">
            <span class="bar-label">{{ String(src).toUpperCase() }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: barWidth(count as number) }" />
            </div>
            <span class="bar-count">{{ count }}</span>
          </div>
        </div>
      </div>
      <div class="chart-card">
        <h3>Score Distribution</h3>
        <div class="dist-bars">
          <div class="dist-row">
            <span class="dist-label dist-high">High (≥75%)</span>
            <div class="dist-bar">
              <div class="dist-fill fill-high" :style="{ width: distWidth(highMatches) }" />
            </div>
            <span class="dist-count">{{ highMatches }}</span>
          </div>
          <div class="dist-row">
            <span class="dist-label dist-mid">Mid (55–74%)</span>
            <div class="dist-bar">
              <div class="dist-fill fill-mid" :style="{ width: distWidth(midMatches) }" />
            </div>
            <span class="dist-count">{{ midMatches }}</span>
          </div>
          <div class="dist-row">
            <span class="dist-label dist-low">Low (&lt;55%)</span>
            <div class="dist-bar">
              <div class="dist-fill fill-low" :style="{ width: distWidth(lowMatches) }" />
            </div>
            <span class="dist-count">{{ lowMatches }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const { get } = useApi()
const jobs = ref<any[]>([])

onMounted(async () => {
  try { const d = await get('/api/jobs?limit=200'); jobs.value = d.jobs ?? d } catch {}
})

const avgScore = computed(() => {
  const scored = jobs.value.filter(j => j.composite_score != null)
  if (!scored.length) return 0
  return Math.round(scored.reduce((s, j) => s + j.composite_score, 0) / scored.length * 100)
})

const highMatches = computed(() => jobs.value.filter(j => (j.composite_score || 0) >= 0.75).length)
const midMatches  = computed(() => jobs.value.filter(j => { const s = (j.composite_score || 0); return s >= 0.55 && s < 0.75 }).length)
const lowMatches  = computed(() => jobs.value.filter(j => (j.composite_score || 0) < 0.55).length)

const bySource = computed(() => {
  const map: Record<string, number> = {}
  jobs.value.forEach(j => { map[j.source || 'unknown'] = (map[j.source || 'unknown'] || 0) + 1 })
  return map
})
const sourcesCount = computed(() => Object.keys(bySource.value).length)

const maxCount = computed(() => Math.max(...Object.values(bySource.value) as number[], 1))
const barWidth = (n: number) => `${Math.round((n / maxCount.value) * 100)}%`
const distWidth = (n: number) => `${jobs.value.length ? Math.round((n / jobs.value.length) * 100) : 0}%`
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 1.75rem; }
.page-header h1 { font-size: 1.5rem; font-weight: 700; color: #f1f5f9; }
.page-header p { font-size: 0.875rem; color: #64748b; margin-top: 0.25rem; }

.analytics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
.metric-card {
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px; padding: 1.5rem;
}
.metric-label { font-size: 0.8rem; color: #64748b; margin-bottom: 0.5rem; }
.metric-value { font-size: 2.25rem; font-weight: 700; color: #f1f5f9; line-height: 1; }
.metric-sub { font-size: 0.75rem; color: #475569; margin-top: 0.375rem; }

.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.chart-card {
  background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px; padding: 1.5rem;
}
.chart-card h3 { font-size: 0.925rem; font-weight: 600; color: #f1f5f9; margin-bottom: 1.25rem; text-transform: none; letter-spacing: 0; }

.bar-chart { display: flex; flex-direction: column; gap: 0.75rem; }
.bar-row { display: flex; align-items: center; gap: 0.75rem; }
.bar-label { font-size: 0.72rem; color: #64748b; width: 90px; flex-shrink: 0; text-align: right; }
.bar-track { flex: 1; height: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; background: linear-gradient(90deg, #10b981, #059669); border-radius: 4px; transition: width 0.6s ease; }
.bar-count { font-size: 0.75rem; color: #475569; width: 24px; text-align: right; }

.dist-bars { display: flex; flex-direction: column; gap: 1rem; }
.dist-row { display: flex; align-items: center; gap: 0.75rem; }
.dist-label { font-size: 0.78rem; font-weight: 500; width: 110px; flex-shrink: 0; }
.dist-high { color: #10b981; }
.dist-mid  { color: #60a5fa; }
.dist-low  { color: #fb923c; }
.dist-bar { flex: 1; height: 10px; background: rgba(255,255,255,0.05); border-radius: 5px; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 5px; transition: width 0.6s ease; }
.fill-high { background: linear-gradient(90deg, #10b981, #059669); }
.fill-mid  { background: linear-gradient(90deg, #3b82f6, #2563eb); }
.fill-low  { background: linear-gradient(90deg, #f97316, #ea580c); }
.dist-count { font-size: 0.75rem; color: #475569; width: 24px; }
</style>
