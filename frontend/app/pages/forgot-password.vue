<template>
  <div class="auth-card">
    <div class="auth-logo">
      <div class="logo-mark">JR</div>
      <div>
        <div class="brand">JobRadar <em>AI</em></div>
        <div class="tagline">We'll send a reset link to your inbox.</div>
      </div>
    </div>

    <div v-if="sent" class="success-box">
      <div class="success-icon">✓</div>
      <h3>Check your inbox</h3>
      <p>If an account exists for <strong>{{ sentEmail }}</strong>, a password reset link has been sent. It expires in 1 hour.</p>
      <NuxtLink to="/login" class="back-link">← Back to sign in</NuxtLink>
    </div>

    <template v-else>
      <form class="auth-form" @submit.prevent="submit">
        <div class="field">
          <label>Email address</label>
          <input v-model="email" type="email" placeholder="you@example.com" autocomplete="email" required />
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <button type="submit" class="btn-submit" :disabled="loading">
          <span v-if="loading" class="spinner" />
          {{ loading ? 'Sending…' : 'Send reset link' }}
        </button>
      </form>

      <p class="switch-link">
        Remember it?
        <NuxtLink to="/login">Sign in</NuxtLink>
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const { forgotPassword } = useAuth()
const email = ref('')
const sentEmail = ref('')
const sent = ref(false)
const error = ref('')
const loading = ref(false)

const submit = async () => {
  error.value = ''
  loading.value = true
  try {
    await forgotPassword(email.value)
    sentEmail.value = email.value
    sent.value = true
  } catch {
    // Don't reveal whether email exists — always show success
    sentEmail.value = email.value
    sent.value = true
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-card {
  width: 100%; max-width: 420px;
  background: rgba(17,19,24,0.85); border: 1px solid rgba(255,255,255,0.07);
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
  width: 100%; background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
  padding: 0.75rem 1rem; font-family: inherit; font-size: 0.9rem;
  color: #e2e8f0; outline: none; transition: border-color 0.15s;
}
input::placeholder { color: #334155; }
input:focus { border-color: rgba(16,185,129,0.45); }

.error-msg {
  font-size: 0.85rem; color: #f87171;
  background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.2);
  border-radius: 8px; padding: 0.625rem 0.875rem;
}

.btn-submit {
  margin-top: 0.25rem; background: linear-gradient(135deg,#10b981,#059669);
  color: #fff; border: none; border-radius: 10px; padding: 0.85rem;
  font-size: 0.925rem; font-weight: 600; transition: all 0.2s;
  display: flex; align-items: center; justify-content: center; gap: 0.5rem;
  box-shadow: 0 4px 14px rgba(16,185,129,0.3);
}
.btn-submit:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(16,185,129,0.4); }
.btn-submit:disabled { opacity: 0.55; cursor: not-allowed; }

.switch-link { text-align: center; margin-top: 1.5rem; font-size: 0.85rem; color: #475569; }
.switch-link a { color: #10b981; font-weight: 500; margin-left: 0.25rem; }
.switch-link a:hover { text-decoration: underline; }

.success-box {
  text-align: center; padding: 1rem 0 0.5rem;
  display: flex; flex-direction: column; align-items: center; gap: 0.75rem;
}
.success-icon {
  width: 52px; height: 52px; border-radius: 50%;
  background: rgba(16,185,129,0.12); border: 2px solid rgba(16,185,129,0.3);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem; color: #10b981;
}
.success-box h3 { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; }
.success-box p { font-size: 0.875rem; color: #64748b; line-height: 1.6; }
.success-box strong { color: #cbd5e1; }
.back-link { font-size: 0.875rem; color: #10b981; font-weight: 500; margin-top: 0.5rem; }
.back-link:hover { text-decoration: underline; }

.spinner {
  width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
