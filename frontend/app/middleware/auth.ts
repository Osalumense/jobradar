const PUBLIC = ['/login', '/register', '/forgot-password', '/reset-password']

export default defineNuxtRouteMiddleware(async (to) => {
  if (PUBLIC.includes(to.path)) return

  const { check } = useAuth()
  const u = await check()
  if (!u) return navigateTo('/login')

  // Already heading to onboarding — let them through
  if (to.path === '/onboarding') return

  // Check if onboarding is complete (profile has a CV saved)
  const config = useRuntimeConfig()
  const onboardingDone = useState<boolean | null>('onboarding.done', () => null)

  if (onboardingDone.value === null) {
    try {
      const res = await fetch(`${config.public.apiBase}/api/profile`, { credentials: 'include' })
      const data = res.ok ? await res.json() : {}
      onboardingDone.value = !!(data.profile?.master_cv)
    } catch {
      onboardingDone.value = true // network failure — don't redirect loop
    }
  }

  if (!onboardingDone.value) return navigateTo('/onboarding')
})
