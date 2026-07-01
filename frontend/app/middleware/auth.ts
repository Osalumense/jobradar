const PUBLIC = ['/login', '/register', '/forgot-password', '/reset-password']

export default defineNuxtRouteMiddleware(async (to) => {
  if (PUBLIC.includes(to.path)) return
  const { check } = useAuth()
  const u = await check()
  if (!u) return navigateTo('/login')
})
