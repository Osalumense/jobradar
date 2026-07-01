export const useApi = () => {
  const config = useRuntimeConfig()
  const base = config.public.apiBase

  const get = async (path: string) => {
    const res = await fetch(`${base}${path}`, { credentials: 'include' })
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
    return res.json()
  }

  const post = async (path: string, body?: unknown) => {
    const res = await fetch(`${base}${path}`, {
      method: 'POST',
      credentials: 'include',
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined
    })
    if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
    return res.json()
  }

  return { get, post }
}
