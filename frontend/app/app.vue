<template>
  <div class="app-container">
    <header class="navbar">
      <div class="logo">
        <span class="logo-icon">📡</span>
        <h1>JobRadar <span class="accent">AI</span></h1>
      </div>
      <div class="user-profile">
        <img src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=100&q=80" alt="Avatar" class="avatar" />
        <div class="user-info">
          <span class="username">{{ profileName }}</span>
          <span class="user-role">Ingénieur Logiciel & IA</span>
        </div>
      </div>
    </header>

    <main class="dashboard-layout">
      <!-- Sidebar / Config -->
      <aside class="config-panel glass">
        <div class="section-title">
          <h2>Target Radar Profile</h2>
          <span class="badge active">{{ contractLabel }}</span>
        </div>

        <div class="profile-card">
          <p class="summary">Admis à l'EFREI Paris pour la rentrée 2026 en Majeure LSI. Recherche d'un contrat d'apprentissage de 3 ans.</p>
          
          <div class="details-list">
            <div class="detail-item">
              <span class="label">Location:</span>
              <span class="value">{{ profileLocation }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Email:</span>
              <span class="value">{{ profileEmail }}</span>
            </div>
          </div>
        </div>

        <div class="divider"></div>

        <h3>Active Search Queries (LLM Compiled)</h3>
        <ul class="queries-list">
          <li v-for="(query, idx) in compiledQueries" :key="idx" class="query-chip">
            <span class="chip-dot"></span>
            {{ query }}
          </li>
          <li v-if="compiledQueries.length === 0" class="empty-state">
            No queries compiled. Set up your profile first.
          </li>
        </ul>

        <div class="divider"></div>

        <h3>Core Technologies</h3>
        <div class="tech-tags">
          <span v-for="tech in techTags" :key="tech" class="tech-tag">{{ tech }}</span>
        </div>
      </aside>

      <!-- Main Feed -->
      <section class="feed-panel">
        <div class="feed-header">
          <h2>Pipeline Discover Feed</h2>
          <button class="btn-primary shimmer" :disabled="scanning" @click="triggerScraper">
            <span class="icon">{{ scanning ? '⏳' : '🔄' }}</span> 
            {{ scanning ? 'Scanning real-time...' : 'Scan Job Boards Now' }}
          </button>
        </div>

        <div class="job-grid">
          <!-- Live Scraped Jobs -->
          <div v-for="job in jobs" :key="job.id" class="job-card glass hover-lift">
            <div class="card-header">
              <span class="company-logo">{{ job.company.charAt(0) }}</span>
              <div class="job-title-wrapper">
                <h4>{{ job.title }}</h4>
                <span class="company-name">{{ job.company }}</span>
              </div>
              <div class="match-badge" :class="getScoreClass(job.composite_score)">
                <span class="score-num">{{ Math.round((job.composite_score || 0) * 100) }}%</span>
                <span class="score-label">match</span>
              </div>
            </div>

            <!-- Truncate description preview -->
            <p class="job-description">{{ getExcerpt(job.description) }}</p>

            <div class="job-metadata">
              <span class="meta-tag"><span class="icon">📍</span> {{ job.location || 'Paris' }}</span>
              <span class="meta-tag"><span class="icon">📄</span> {{ job.contract_type ? job.contract_type.toUpperCase() : 'CDI' }}</span>
              <span class="meta-tag source-tag" :class="job.source">{{ job.source.toUpperCase() }}</span>
            </div>

            <div class="card-actions">
              <!-- Open link in a new tab -->
              <a :href="job.url" target="_blank" class="btn-secondary-link">View Posting ↗</a>
              <button class="btn-accent">Tailor Application</button>
            </div>
          </div>

          <!-- Empty Feed State -->
          <div v-if="jobs.length === 0" class="empty-feed glass">
            <span class="empty-icon">📭</span>
            <h3>No jobs scanned yet</h3>
            <p>Click "Scan Job Boards Now" to trigger a live WTTJ scraping pipeline.</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const SCORER_API_URL = "http://localhost:9089"

// States
const compiledQueries = ref([])
const techTags = ref([])
const jobs = ref([])
const scanning = ref(false)

const profileName = ref("Stephen Akugbe")
const profileEmail = ref("akugbestephen3@gmail.com")
const profileLocation = ref("Paris, France")
const contractLabel = ref("Alternance")

// Fetch Initial Data on Mount
const fetchProfileData = async () => {
  try {
    const res = await fetch(`${SCORER_API_URL}/api/profile`)
    if (res.ok) {
      const data = await res.json()
      if (data.matching_criteria) {
        compiledQueries.value = data.matching_criteria.search_queries || []
        techTags.value = data.matching_criteria.target_tech || []
        contractLabel.value = (data.matching_criteria.target_contracts || ["alternance"])[0]
      }
      if (data.profile) {
        profileName.value = data.profile.full_name || "Stephen Akugbe"
        profileEmail.value = data.profile.email || "akugbestephen3@gmail.com"
      }
    }
  } catch (err) {
    console.error("Failed to load profile details:", err)
  }
}

const fetchJobs = async () => {
  try {
    const res = await fetch(`${SCORER_API_URL}/api/jobs?limit=15`)
    if (res.ok) {
      jobs.value = await res.json()
    }
  } catch (err) {
    console.error("Failed to load jobs list:", err)
  }
}

onMounted(() => {
  fetchProfileData()
  fetchJobs()
})

const getExcerpt = (text) => {
  if (!text) return ""
  return text.length > 200 ? text.substring(0, 200) + "..." : text
}

const getScoreClass = (score) => {
  const pct = (score || 0) * 100
  if (pct >= 80) return 'score-high'
  if (pct >= 70) return 'score-mid'
  return 'score-low'
}

// Trigger Live Backend Scraper
const triggerScraper = async () => {
  scanning.value = true
  try {
    const res = await fetch(`${SCORER_API_URL}/api/scrape`, { method: "POST" })
    if (res.ok) {
      alert("Scraper triggered! Live scanner is fetching jobs, applying Upstash deduplication, and scoring via Gemini. This takes 10-15 seconds...")
      
      // Poll database every 5 seconds for new listings
      let attempts = 0
      const interval = setInterval(async () => {
        await fetchJobs()
        attempts++
        if (attempts >= 4) {
          clearInterval(interval)
          scanning.value = false
        }
      }, 5000)
    } else {
      scanning.value = false
      alert("Failed to initiate scraper.")
    }
  } catch (err) {
    scanning.value = false
    console.error("Scraper connection error:", err)
  }
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background-color: #0b0d11;
  color: #e2e8f0;
  font-family: 'Outfit', sans-serif;
  overflow-x: hidden;
  min-height: 100vh;
}

.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 1.5rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.logo-icon {
  font-size: 2rem;
}

.logo h1 {
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.accent {
  background: linear-gradient(135deg, #a78bfa, #818cf8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: rgba(255, 255, 255, 0.03);
  padding: 0.5rem 1rem;
  border-radius: 50px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
}

.user-info {
  display: flex;
  flex-direction: column;
}

.username {
  font-size: 0.875rem;
  font-weight: 500;
}

.user-role {
  font-size: 0.75rem;
  color: #94a3b8;
}

.dashboard-layout {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 2.5rem;
  align-items: start;
}

/* Glassmorphism utility */
.glass {
  background: rgba(17, 22, 31, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
}

.config-panel {
  padding: 2rem;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-title h2 {
  font-size: 1.25rem;
  font-weight: 600;
}

.badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.75rem;
  border-radius: 50px;
  text-transform: uppercase;
}

.badge.active {
  background: rgba(167, 139, 250, 0.15);
  color: #c084fc;
  border: 1px solid rgba(167, 139, 250, 0.3);
}

.profile-card {
  margin-bottom: 1.5rem;
}

.summary {
  font-size: 0.938rem;
  color: #94a3b8;
  line-height: 1.6;
  margin-bottom: 1.25rem;
}

.details-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
}

.label {
  color: #64748b;
}

.value {
  color: #e2e8f0;
  font-weight: 500;
}

.divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.05);
  margin: 1.5rem 0;
}

h3 {
  font-size: 0.938rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #64748b;
  margin-bottom: 1rem;
}

.queries-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.query-chip {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-size: 0.875rem;
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.02);
  padding: 0.5rem 0.875rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.03);
}

.chip-dot {
  width: 6px;
  height: 6px;
  background-color: #818cf8;
  border-radius: 50%;
  box-shadow: 0 0 8px #818cf8;
}

.empty-state {
  font-size: 0.875rem;
  color: #64748b;
  font-style: italic;
}

.tech-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tech-tag {
  font-size: 0.813rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 0.375rem 0.75rem;
  border-radius: 6px;
  color: #94a3b8;
  text-transform: capitalize;
}

.feed-panel {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
}

.feed-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feed-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
}

.btn-primary {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: white;
  border: none;
  padding: 0.75rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: inherit;
  font-size: 0.875rem;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-primary:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4);
}

.job-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

.job-card {
  padding: 1.75rem;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.hover-lift:hover {
  transform: translateY(-4px);
  border-color: rgba(167, 139, 250, 0.15);
  box-shadow: 0 12px 30px rgba(10, 12, 16, 0.5), 0 0 15px rgba(167, 139, 250, 0.05);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.company-logo {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #1e293b, #0f172a);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  font-weight: 700;
  color: #a78bfa;
}

.job-title-wrapper {
  flex-grow: 1;
}

.job-title-wrapper h4 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.company-name {
  font-size: 0.875rem;
  color: #64748b;
}

.match-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border-width: 2px;
  border-style: solid;
}

.score-high {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.05);
  color: #34d399;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.15);
}

.score-mid {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.05);
  color: #60a5fa;
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.15);
}

.score-low {
  border-color: #f97316;
  background: rgba(249, 115, 22, 0.05);
  color: #fb923c;
}

.score-num {
  font-size: 1.125rem;
  font-weight: 700;
  line-height: 1;
}

.score-label {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 1px;
}

.job-description {
  font-size: 0.938rem;
  color: #94a3b8;
  line-height: 1.6;
  margin-bottom: 1.25rem;
}

.job-metadata {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.meta-tag {
  font-size: 0.813rem;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.source-tag {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
}

.source-tag.wttj {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.source-tag.apec {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.card-actions {
  display: flex;
  gap: 1rem;
}

.btn-secondary-link {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.875rem;
  text-decoration: none;
  transition: all 0.2s;
  display: inline-block;
}

.btn-secondary-link:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.15);
  color: white;
}

.btn-accent {
  background: rgba(167, 139, 250, 0.1);
  border: 1px solid rgba(167, 139, 250, 0.2);
  color: #c084fc;
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.btn-accent:hover {
  background: rgba(167, 139, 250, 0.18);
  border-color: rgba(167, 139, 250, 0.35);
}

.empty-feed {
  padding: 4rem 2rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #64748b;
  border-style: dashed;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-feed h3 {
  color: #e2e8f0;
  margin-bottom: 0.5rem;
}
</style>
