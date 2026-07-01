<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1>Applications</h1>
        <p>Drag jobs between stages to track your pipeline</p>
      </div>
    </div>

    <div v-if="loading" class="board-skeleton">
      <div v-for="i in 5" :key="i" class="col-skeleton" />
    </div>

    <div v-else class="kanban-board">
      <div v-for="stage in stages" :key="stage.value" class="kanban-col">
        <div class="col-header">
          <span class="col-dot" :style="{ background: stage.color }" />
          <span class="col-title">{{ stage.label }}</span>
          <span class="col-count">{{ byStage(stage.value).length }}</span>
        </div>
        <div class="col-cards">
          <div
            v-for="job in byStage(stage.value)"
            :key="job.id"
            class="kanban-card"
          >
            <div class="kcard-header">
              <span class="kcard-logo">{{ (job.company || 'J')[0].toUpperCase() }}</span>
              <div>
                <div class="kcard-title">{{ job.title }}</div>
                <div class="kcard-company">{{ job.company }}</div>
              </div>
            </div>
            <div class="kcard-footer">
              <span class="kcard-loc">{{ job.location || 'Remote' }}</span>
              <div class="kcard-score" :class="scoreClass(job.composite_score)">
                {{ Math.round((job.composite_score || 0) * 100) }}%
              </div>
            </div>
            <div class="kcard-actions">
              <button
                v-for="s in stages.filter(st => st.value !== stage.value)"
                :key="s.value"
                class="move-btn"
                @click="moveJob(job.id, s.value)"
              >→ {{ s.label }}</button>
            </div>
          </div>
          <div v-if="!byStage(stage.value).length" class="col-empty">
            No jobs here
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const { get } = useApi()
const config = useRuntimeConfig()

const jobs = ref<any[]>([])
const loading = ref(true)

const stages = [
  { label: 'New', value: 'new', color: '#475569' },
  { label: 'Reviewed', value: 'reviewed', color: '#6366f1' },
  { label: 'Applied', value: 'applied', color: '#10b981' },
  { label: 'Interviewing', value: 'interviewing', color: '#f59e0b' },
  { label: 'Offer', value: 'offer', color: '#10b981' },
]

const byStage = (s: string) => jobs.value.filter(j => (j.status || 'new') === s)

const scoreClass = (s: number | null) => {
  const p = (s || 0) * 100
  if (p >= 75) return 'score-high'
  if (p >= 55) return 'score-mid'
  return 'score-low'
}

const moveJob = async (jobId: string, newStatus: string) => {
  try {
    await fetch(`${config.public.apiBase}/api/jobs/${jobId}/status`, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    })
    const j = jobs.value.find(j => j.id === jobId)
    if (j) j.status = newStatus
  } catch {}
}

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

.board-skeleton { display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; }
.col-skeleton {
  height: 320px; border-radius: 14px;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; } }

.kanban-board {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1rem;
  align-items: start;
}

.kanban-col {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 14px;
  overflow: hidden;
}

.col-header {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.875rem 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.col-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.col-title { font-size: 0.85rem; font-weight: 600; color: #cbd5e1; flex: 1; }
.col-count {
  font-size: 0.75rem; font-weight: 700; min-width: 20px; height: 20px;
  background: rgba(255,255,255,0.06); border-radius: 10px;
  display: flex; align-items: center; justify-content: center; color: #64748b;
}

.col-cards { padding: 0.75rem; display: flex; flex-direction: column; gap: 0.625rem; }

.kanban-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 10px;
  padding: 0.875rem;
  display: flex; flex-direction: column; gap: 0.625rem;
}

.kcard-header { display: flex; align-items: flex-start; gap: 0.625rem; }
.kcard-logo {
  width: 32px; height: 32px; flex-shrink: 0; border-radius: 7px;
  background: linear-gradient(135deg, #1e293b, #0f172a);
  border: 1px solid rgba(255,255,255,0.07);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.875rem; font-weight: 700; color: #10b981;
}
.kcard-title { font-size: 0.8rem; font-weight: 600; color: #f1f5f9; line-height: 1.3; word-break: break-word; overflow-wrap: break-word; }
.kcard-company { font-size: 0.72rem; color: #64748b; margin-top: 2px; }

.kcard-footer { display: flex; justify-content: space-between; align-items: center; }
.kcard-loc { font-size: 0.72rem; color: #475569; }
.kcard-score { font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 6px; border: 1.5px solid; }
.score-high { border-color: #10b981; color: #10b981; }
.score-mid  { border-color: #3b82f6; color: #60a5fa; }
.score-low  { border-color: #f97316; color: #fb923c; }

.kcard-actions { display: flex; flex-wrap: wrap; gap: 0.3rem; border-top: 1px solid rgba(255,255,255,0.04); padding-top: 0.5rem; }
.move-btn {
  font-size: 0.68rem; padding: 0.2rem 0.5rem; border-radius: 5px;
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
  color: #64748b; transition: all 0.15s;
}
.move-btn:hover { color: #10b981; border-color: rgba(16,185,129,0.3); }

.col-empty { padding: 1.5rem 0; text-align: center; font-size: 0.78rem; color: #334155; }
</style>
