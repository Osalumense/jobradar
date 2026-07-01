<template>
  <div class="page">
    <div class="page-header">
      <h1>Profile</h1>
      <p>Your master CV and personal details</p>
    </div>

    <div v-if="loading" class="loading-state">Loading profile…</div>

    <div v-else class="profile-layout">
      <div class="profile-card">
        <div class="profile-hero">
          <div class="profile-avatar">{{ initial }}</div>
          <div>
            <div class="profile-name">{{ profile?.full_name || 'No name set' }}</div>
            <div class="profile-email">{{ profile?.email || '—' }}</div>
          </div>
        </div>

        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">Phone</span>
            <span class="info-val">{{ profile?.phone || '—' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">GitHub</span>
            <a v-if="profile?.github_url" :href="profile.github_url" target="_blank" class="info-link">{{ profile.github_url }}</a>
            <span v-else class="info-val">—</span>
          </div>
          <div class="info-item">
            <span class="info-label">LinkedIn</span>
            <a v-if="profile?.linkedin_url" :href="profile.linkedin_url" target="_blank" class="info-link">{{ profile.linkedin_url }}</a>
            <span v-else class="info-val">—</span>
          </div>
        </div>
      </div>

      <div class="cv-card">
        <h3>Master CV</h3>
        <pre class="cv-text">{{ profile?.master_cv || 'No CV uploaded yet.' }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const { get } = useApi()
const profile = ref<any>(null)
const loading = ref(true)

const initial = computed(() => (profile.value?.full_name || 'U')[0].toUpperCase())

onMounted(async () => {
  loading.value = true
  try { const d = await get('/api/profile'); profile.value = d.profile } catch {}
  loading.value = false
})
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 1.5rem; }
.page-header h1 { font-size: 1.5rem; font-weight: 700; color: #f1f5f9; }
.page-header p { font-size: 0.875rem; color: #64748b; margin-top: 0.25rem; }

.loading-state { color: #64748b; font-size: 0.875rem; padding: 2rem 0; }

.profile-layout { display: grid; grid-template-columns: 340px 1fr; gap: 1.5rem; align-items: start; }

.profile-card, .cv-card {
  background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px; padding: 1.5rem;
}

.profile-hero { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; }
.profile-avatar {
  width: 56px; height: 56px; border-radius: 50%; flex-shrink: 0;
  background: linear-gradient(135deg, #10b981, #059669);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem; font-weight: 700; color: #fff;
}
.profile-name { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; }
.profile-email { font-size: 0.85rem; color: #64748b; margin-top: 3px; }

.info-grid { display: flex; flex-direction: column; gap: 0.875rem; }
.info-item { display: flex; flex-direction: column; gap: 0.25rem; }
.info-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.5px; color: #475569; }
.info-val { font-size: 0.875rem; color: #cbd5e1; }
.info-link { font-size: 0.875rem; color: #10b981; word-break: break-all; }
.info-link:hover { text-decoration: underline; }

.cv-card h3 { font-size: 0.925rem; font-weight: 600; color: #f1f5f9; margin-bottom: 1rem; text-transform: none; letter-spacing: 0; }
.cv-text {
  font-family: 'Outfit', sans-serif; font-size: 0.82rem; color: #94a3b8;
  line-height: 1.7; white-space: pre-wrap; word-break: break-word;
  max-height: 600px; overflow-y: auto;
}
</style>
