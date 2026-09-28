import axios from 'axios'

const rawBase = import.meta.env.VITE_API_BASE_URL as string | undefined
const baseURL = rawBase ? `${rawBase.replace(/\/+$/, '')}/api/v1` : '/api/v1'

export const api = axios.create({ baseURL })

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('logiai_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
