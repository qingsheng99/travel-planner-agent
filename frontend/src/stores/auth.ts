import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

interface User {
  id: number
  email: string
  username: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token') || null)
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  async function login(email: string, password: string) {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)

    const response = await api.post('/auth/login', formData)
    token.value = response.data.access_token
    localStorage.setItem('token', token.value!)
    await fetchUser()
  }

  async function register(email: string, username: string, password: string) {
    await api.post('/auth/register', { email, username, password })
  }

  async function fetchUser() {
    if (token.value) {
      const response = await api.get('/auth/me')
      user.value = response.data
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    register,
    fetchUser,
    logout,
  }
})