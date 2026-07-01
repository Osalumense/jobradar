<template>
  <div class="shell">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-logo">
        <div class="logo-mark">JR</div>
        <span class="logo-text">JobRadar <em>AI</em></span>
      </div>

      <nav class="sidebar-nav">
        <NuxtLink to="/" class="nav-item" active-class="nav-active" exact>
          <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          Dashboard
        </NuxtLink>
        <NuxtLink to="/jobs" class="nav-item" active-class="nav-active">
          <svg viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>
          Job Listings
        </NuxtLink>
        <NuxtLink to="/pipeline" class="nav-item" active-class="nav-active">
          <svg viewBox="0 0 24 24"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          Applications
        </NuxtLink>
        <NuxtLink to="/analytics" class="nav-item" active-class="nav-active">
          <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          Analytics
        </NuxtLink>
        <NuxtLink to="/matches" class="nav-item" active-class="nav-active">
          <svg viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          Matches
        </NuxtLink>
        <NuxtLink to="/feats" class="nav-item" active-class="nav-active">
          <svg viewBox="0 0 24 24"><path d="M8 21h8M12 21v-4M5 3h14a1 1 0 0 1 1 1v5a7 7 0 0 1-14 0V4a1 1 0 0 1 1-1z"/></svg>
          Accomplishments
        </NuxtLink>

        <div class="nav-divider" />

        <NuxtLink to="/profile" class="nav-item" active-class="nav-active">
          <svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          Profile
        </NuxtLink>
        <NuxtLink to="/settings" class="nav-item" active-class="nav-active">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          Settings
        </NuxtLink>
      </nav>
    </aside>

    <!-- Main area -->
    <div class="main-area">
      <!-- Top bar -->
      <header class="topbar">
        <div class="topbar-right">
          <button class="icon-btn" aria-label="Notifications">
            <svg viewBox="0 0 24 24" width="18" height="18"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
            <span class="notif-dot" />
          </button>
          <div class="user-chip">
            <div class="user-avatar">{{ userInitial }}</div>
            <span class="user-name">{{ userName }}</span>
          </div>
          <button class="icon-btn logout-btn" @click="doLogout" title="Logout">
            <svg viewBox="0 0 24 24" width="16" height="16"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </button>
        </div>
      </header>

      <!-- Page content -->
      <main class="page-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'DefaultLayout' })

const { user, logout } = useAuth()

const userName = computed(() => user.value?.username ?? 'User')
const userInitial = computed(() => (user.value?.username ?? 'U')[0].toUpperCase())

const doLogout = async () => { await logout() }
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0d0f12; color: #e2e8f0; font-family: 'Outfit', sans-serif; min-height: 100vh; overflow-x: hidden; }
a { text-decoration: none; color: inherit; }
svg { fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
button { cursor: pointer; font-family: inherit; }
</style>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
}

/* ── Sidebar ── */
.sidebar {
  width: 220px;
  min-width: 220px;
  background: #111318;
  border-right: 1px solid rgba(255,255,255,0.05);
  display: flex;
  flex-direction: column;
  padding: 1.5rem 1rem;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0 0.5rem;
  margin-bottom: 2.25rem;
}

.logo-mark {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #10b981, #059669);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.5px;
  flex-shrink: 0;
}

.logo-text {
  font-size: 1rem;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: -0.3px;
}
.logo-text em {
  font-style: normal;
  color: #10b981;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.875rem;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 500;
  color: #64748b;
  transition: all 0.15s ease;
}
.nav-item svg { width: 17px; height: 17px; flex-shrink: 0; }
.nav-item:hover { color: #cbd5e1; background: rgba(255,255,255,0.04); }
.nav-active {
  background: rgba(16, 185, 129, 0.12) !important;
  color: #10b981 !important;
  font-weight: 600;
}
.nav-active svg { stroke: #10b981; }

.nav-divider {
  height: 1px;
  background: rgba(255,255,255,0.05);
  margin: 0.75rem 0.5rem;
}

/* ── Main area ── */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.topbar {
  height: 60px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 1.75rem;
  background: #0d0f12;
  position: sticky;
  top: 0;
  z-index: 10;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.15s;
}
.icon-btn:hover { color: #e2e8f0; background: rgba(255,255,255,0.07); }

.notif-dot {
  width: 7px;
  height: 7px;
  background: #10b981;
  border-radius: 50%;
  border: 1.5px solid #0d0f12;
  position: absolute;
  top: 5px;
  right: 5px;
  box-shadow: 0 0 6px rgba(16,185,129,0.5);
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 10px;
  padding: 0.35rem 0.875rem 0.35rem 0.45rem;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #10b981, #059669);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.user-name {
  font-size: 0.85rem;
  font-weight: 500;
  color: #cbd5e1;
  white-space: nowrap;
}

.logout-btn { color: #475569; }

.page-content {
  flex: 1;
  padding: 1.75rem 1.5rem;
  overflow-y: auto;
  min-width: 0;
}
</style>
