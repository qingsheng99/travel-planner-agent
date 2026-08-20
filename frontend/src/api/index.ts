/**
 * API 请求模块
 * 基于 axios 封装 HTTP 客户端，统一配置请求前缀、超时时间，
 * 并添加请求/响应拦截器处理 Token 认证和全局错误提示
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例，配置基础 URL 和请求超时时间
const api = axios.create({
  baseURL: '/api/v1', // 后端 API 基础路径
  timeout: 30000,      // 请求超时时间（毫秒）
})

/**
 * 请求拦截器
 * 在发送请求前自动附加 JWT Token（从 localStorage 中读取）
 */
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token') // 从本地存储获取 token
    if (token) {
      config.headers.Authorization = `Bearer ${token}` // 设置 Authorization 请求头
    }
    return config
  },
  (error) => Promise.reject(error), // 请求配置出错时直接抛出
)

/**
 * 响应拦截器
 * 统一处理响应错误：401 跳转登录、其他错误通过 Element Plus 消息提示
 */
api.interceptors.response.use(
  (response) => response, // 正常响应直接返回
  (error) => {
    if (error.response) {
      // 服务器返回了错误状态码
      const status = error.response.status
      const message = error.response.data?.detail || '请求失败' // 优先使用后端返回的错误详情

      if (status === 401) {
        // 未授权：清除本地 token 并跳转到登录页
        localStorage.removeItem('token')
        window.location.href = '/login'
      }

      ElMessage.error(message) // 弹出错误提示
    } else {
      // 网络层错误（如断网、超时）
      ElMessage.error('网络错误，请检查连接')
    }
    return Promise.reject(error) // 继续抛出错误，供调用方处理
  },
)

export default api