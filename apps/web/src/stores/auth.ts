import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'

export interface CurrentUser {
  id: string
  tenant_id: string
  tenant_code: string
  username: string
  email: string
  role: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null)

  async function login(tenant_code: string, username: string, password: string) {
    const response = await api.post<{ access_token: string }>('/auth/login', { tenant_code, username, password })
    sessionStorage.setItem('logiai_access_token', response.data.access_token)
    await loadUser()
  }

  async function loadUser() {
    const response = await api.get<CurrentUser>('/auth/me')
    user.value = response.data
  }

  function logout() {
    sessionStorage.removeItem('logiai_access_token')
    user.value = null
  }

  return { user, login, loadUser, logout }
})
