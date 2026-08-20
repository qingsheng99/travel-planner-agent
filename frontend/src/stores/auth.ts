/**
 * 用户认证状态管理模块
 * 负责管理用户的登录令牌、用户信息、登录/注册/登出等操作，
 * 令牌持久化存储在 localStorage 中。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

/** 用户信息接口 */
interface User {
  id: number
  email: string
  username: string
}

/** 认证 Store：管理用户登录态与身份信息 */
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token') || null) // JWT 令牌，优先从 localStorage 恢复
  const user = ref<User | null>(null) // 当前登录用户信息

  /** 是否已登录（计算属性，由 token 是否存在决定） */
  const isAuthenticated = computed(() => !!token.value)

  /**
   * 用户登录
   * @param email - 用户邮箱
   * @param password - 用户密码
   */
  async function login(email: string, password: string) {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)

    const response = await api.post('/auth/login', formData)
    token.value = response.data.access_token // 保存令牌
    localStorage.setItem('token', token.value!) // 持久化到本地存储
    await fetchUser() // 登录成功后获取用户信息
  }

  /**
   * 用户注册
   * @param email - 注册邮箱
   * @param username - 用户名
   * @param password - 密码
   */
  async function register(email: string, username: string, password: string) {
    await api.post('/auth/register', { email, username, password })
  }

  /** 获取当前登录用户信息 */
  async function fetchUser() {
    if (token.value) {
      const response = await api.get('/auth/me')
      user.value = response.data
    }
  }

  /** 退出登录：清除令牌和用户信息 */
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