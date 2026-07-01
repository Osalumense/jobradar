<template>
  <div class="auth-card">
    <div class="auth-logo">
      <div class="logo-mark">JR</div>
      <div>
        <div class="brand">JobRadar <em>AI</em></div>
        <div class="tagline">Track your career. Land your role.</div>
      </div>
    </div>

    <form class="auth-form" @submit.prevent="submit">
      <div class="field">
        <label>Email</label>
        <input v-model="email" type="email" placeholder="you@example.com" autocomplete="email" required />
      </div>
      <div class="field">
        <label>Password</label>
        <div class="input-wrap">
          <input v-model="password" :type="showPw ? 'text' : 'password'" placeholder="••••••••" autocomplete="current-password" required />
          <button type="button" class="pw-toggle" @click="showPw = !showPw">
            {{ showPw ? 'Hide' : 'Show' }}
          </button>
        </div>
      </div>

      <div class="form-foot">
        <NuxtLink to="/forgot-password" class="link-muted">Forgot password?</NuxtLink>
      </div>

      <p v-if="error" class="error-msg">{{ error }}</p>

      <button type="submit" class="btn-submit" :disabled="loading">
        <span v-if="loading" class="spinner" />
        {{ loading ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>

    <p class="switch-link">
      Don't have an account?
      <NuxtLink to="/register">Create one</NuxtLink>
    </p>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const { login } = useAuth()
const email = ref('')
const password = ref('')
const showPw = ref(false)
const error = ref('')
const loading = ref(false)

const submit = async () => {
  error.value = ''
  loading.value = true
  try {
    await login(email.value, password.value)
    await navigateTo('/')
  } catch (e: any) {
    error.value = e.message || 'Invalid credentials'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-card {
  width: 100%; max-width: 420px;
  background: rgba(17,19,24,0.85);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 20px; padding: 2.5rem 2.25rem;
  backdrop-filter: blur(20px); position: relative; z-index: 1;
}
.auth-logo { display: flex; align-items: center; gap: 0.875rem; margin-bottom: 2rem; }
.logo-mark {
  width: 44px; height: 44px; border-radius: 12px;
  background: linear-gradient(135deg,#10b981,#059669);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.875rem; font-weight: 800; color: #fff; flex-shrink: 0;
}
.brand { font-size: 1.25rem; font-weight: 700; color: #f1f5f9; }
.brand em { font-style: normal; color: #10b981; }
.tagline { font-size: 0.8rem; color: #475569; margin-top: 2px; }

.auth-form { display: flex; flex-direction: column; gap: 1.125rem; }
.field { display: flex; flex-direction: column; gap: 0.5rem; }
label { font-size: 0.78rem; font-weight: 500; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }

input {
  width: 100%; box-sizing: border-box; background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
  padding: 0.75rem 1rem; font-family: inherit; font-size: 0.9rem;
  color: #e2e8f0; outline: none; transition: border-color 0.15s;
}
input::placeholder { color: #334155; }
input:focus { border-color: rgba(16,185,129,0.45); }

.input-wrap { position: relative; width: 100%; }
.input-wrap input { padding-right: 4.5rem; box-sizing: border-box; }
.pw-toggle {
  position: absolute; right: 0.875rem; top: 50%; transform: translateY(-50%);
  background: none; border: none; color: #475569; font-size: 0.78rem;
  font-weight: 500; cursor: pointer; transition: color 0.15s;
}
.pw-toggle:hover { color: #10b981; }

.form-foot { display: flex; justify-content: flex-end; }
.link-muted { font-size: 0.82rem; color: #475569; transition: color 0.15s; }
.link-muted:hover { color: #10b981; }

.error-msg {
  font-size: 0.85rem; color: #f87171;
  background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.2);
  border-radius: 8px; padding: 0.625rem 0.875rem;
}

.btn-submit {
  margin-top: 0.25rem;
  background: linear-gradient(135deg,#10b981,#059669); color: #fff; border: none;
  border-radius: 10px; padding: 0.85rem; font-size: 0.925rem; font-weight: 600;
  letter-spacing: 0.2px; transition: all 0.2s;
  display: flex; align-items: center; justify-content: center; gap: 0.5rem;
  box-shadow: 0 4px 14px rgba(16,185,129,0.3);
}
.btn-submit:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(16,185,129,0.4); }
.btn-submit:disabled { opacity: 0.65; cursor: not-allowed; }

.switch-link { text-align: center; margin-top: 1.5rem; font-size: 0.85rem; color: #475569; }
.switch-link a { color: #10b981; font-weight: 500; margin-left: 0.25rem; }
.switch-link a:hover { text-decoration: underline; }

.spinner {
  width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
