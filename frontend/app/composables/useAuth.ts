export const useAuth = () => {
  const config = useRuntimeConfig()
  const api = config.public.apiBase

  const user = useState<{ email: string; user_id: string } | null>('auth.user', () => null)
  const checked = useState<boolean>('auth.checked', () => false)

  const login = async (email: string, password: string) => {
    const res = await fetch(`${api}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
    user.value = { email: data.email, user_id: data.user_id }
    return data
  }

  const register = async (email: string, password: string) => {
    const res = await fetch(`${api}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Registration failed')
    }
    return res.json()
  }

  const logout = async () => {
    await fetch(`${api}/api/auth/logout`, { method: 'POST', credentials: 'include' }).catch(() => {})
    user.value = null
    checked.value = false
    await navigateTo('/login')
  }

  const check = async () => {
    if (checked.value) return user.value
    try {
      const res = await fetch(`${api}/api/auth/me`, { credentials: 'include' })
      if (res.ok) {
        const data = await res.json()
        user.value = { email: data.email, user_id: data.user_id }
      } else {
        user.value = null
      }
    } catch {
      user.value = null
    }
    checked.value = true
    return user.value
  }

  const forgotPassword = async (email: string) => {
    const res = await fetch(`${api}/api/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    })
    if (!res.ok) throw new Error('Request failed')
    return res.json()
  }

  const resetPassword = async (token: string, newPassword: string) => {
    const res = await fetch(`${api}/api/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Reset failed')
    }
    return res.json()
  }

  return { user, login, register, logout, check, forgotPassword, resetPassword }
}
