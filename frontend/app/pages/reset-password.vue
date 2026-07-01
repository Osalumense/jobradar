<template>
  <div class="auth-card">
    <div class="auth-logo">
      <div class="logo-mark">JR</div>
      <div>
        <div class="brand">JobRadar <em>AI</em></div>
        <div class="tagline">Choose a new password.</div>
      </div>
    </div>

    <div v-if="!token" class="error-box">
      <p>Invalid or missing reset link. <NuxtLink to="/forgot-password">Request a new one</NuxtLink>.</p>
    </div>

    <div v-else-if="done" class="success-box">
      <div class="success-icon">✓</div>
      <h3>Password updated</h3>
      <p>Your password has been reset. You can now sign in with your new credentials.</p>
      <NuxtLink to="/login" class="btn-go">Sign in →</NuxtLink>
    </div>

    <template v-else>
      <form class="auth-form" @submit.prevent="submit">
        <div class="field">
          <label>New password</label>
          <div class="input-wrap">
            <input v-model="password" :type="showPw ? 'text' : 'password'" placeholder="At least 8 characters" autocomplete="new-password" required minlength="8" />
            <button type="button" class="pw-toggle" @click="showPw = !showPw">{{ showPw ? 'Hide' : 'Show' }}</button>
          </div>
          <div class="pw-strength">
            <div class="strength-bar"><div class="strength-fill" :style="{ width: strengthWidth, background: strengthColor }" /></div>
            <span class="strength-label" :style="{ color: strengthColor }">{{ strengthLabel }}</span>
          </div>
        </div>
        <div class="field">
          <label>Confirm password</label>
          <input v-model="confirm" :type="showPw ? 'text' : 'password'" placeholder="••••••••" autocomplete="new-password" required />
          <span v-if="confirm && confirm !== password" class="field-error">Passwords don't match</span>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <button type="submit" class="btn-submit" :disabled="loading || (!!confirm && confirm !== password)">
          <span v-if="loading" class="spinner" />
          {{ loading ? 'Updating…' : 'Reset password' }}
        </button>
      </form>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const { resetPassword } = useAuth()
const route = useRoute()
const token = computed(() => route.query.token as string | undefined)

const password = ref('')
const confirm = ref('')
const showPw = ref(false)
const error = ref('')
const loading = ref(false)
const done = ref(false)

const strengthScore = computed(() => {
  const p = password.value; let score = 0
  if (p.length >= 8) score++; if (p.length >= 12) score++
  if (/[A-Z]/.test(p)) score++; if (/[0-9]/.test(p)) score++
  if (/[^A-Za-z0-9]/.test(p)) score++
  return score
})
const strengthWidth = computed(() => `${Math.min(100, strengthScore.value * 20)}%`)
const strengthColor = computed(() => {
  const s = strengthScore.value
  if (s <= 1) return '#ef4444'; if (s <= 2) return '#f97316'
  if (s <= 3) return '#eab308'; return '#10b981'
})
const strengthLabel = computed(() => {
  if (!password.value) return ''
  const s = strengthScore.value
  if (s <= 1) return 'Weak'; if (s <= 2) return 'Fair'; if (s <= 3) return 'Good'; return 'Strong'
})

const submit = async () => {
  if (password.value !== confirm.value || !token.value) return
  error.value = ''
  loading.value = true
  try {
    await resetPassword(token.value, password.value)
    done.value = true
  } catch (e: any) {
    error.value = e.message || 'Reset failed. The link may have expired.'
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

.pw-strength { display: flex; align-items: center; gap: 0.625rem; margin-top: 0.25rem; }
.strength-bar { flex: 1; height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.strength-fill { height: 100%; border-radius: 2px; transition: all 0.3s; }
.strength-label { font-size: 0.72rem; font-weight: 600; min-width: 40px; }
.field-error { font-size: 0.78rem; color: #f87171; }

.error-msg {
  font-size: 0.85rem; color: #f87171;
  background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.2);
  border-radius: 8px; padding: 0.625rem 0.875rem;
}
.error-box {
  font-size: 0.875rem; color: #64748b; text-align: center; padding: 1rem 0;
}
.error-box a { color: #10b981; }

.btn-submit {
  margin-top: 0.25rem; background: linear-gradient(135deg,#10b981,#059669);
  color: #fff; border: none; border-radius: 10px; padding: 0.85rem;
  font-size: 0.925rem; font-weight: 600; transition: all 0.2s;
  display: flex; align-items: center; justify-content: center; gap: 0.5rem;
  box-shadow: 0 4px 14px rgba(16,185,129,0.3);
}
.btn-submit:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(16,185,129,0.4); }
.btn-submit:disabled { opacity: 0.55; cursor: not-allowed; }

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
.btn-go {
  display: inline-block; margin-top: 0.5rem;
  background: linear-gradient(135deg,#10b981,#059669); color: #fff;
  border-radius: 10px; padding: 0.75rem 2rem; font-size: 0.9rem; font-weight: 600;
  box-shadow: 0 4px 14px rgba(16,185,129,0.3);
}
.btn-go:hover { transform: translateY(-1px); }

.spinner {
  width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
