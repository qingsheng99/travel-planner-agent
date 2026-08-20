/**
 * 用户画像状态管理模块
 * 负责用户偏好、旅行历史的获取与更新，与后端 /profile 相关 API 交互：
 * - GET  /profile               获取当前用户画像（偏好 + 旅行历史）
 * - PUT  /profile/preferences   增量更新偏好
 * - POST /profile/history       新增一条旅行历史
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

/** 旅行历史条目接口 */
interface TravelHistoryItem {
  destination: string // 目的地
  start_date?: string | null // 出发日期（ISO 字符串）
  end_date?: string | null // 结束日期（ISO 字符串）
  note?: string | null // 备注
}

/** 用户画像接口（后端 ProfileResponse 结构） */
interface ProfileData {
  user_id: number // 所属用户 ID
  preferences: Record<string, any> // 偏好键值对
  travel_history: TravelHistoryItem[] // 旅行历史记录
}

/** 画像 Store：管理用户偏好与旅行历史 */
export const useProfileStore = defineStore('profile', () => {
  const preferences = ref<Record<string, any>>({}) // 偏好键值对
  const travelHistory = ref<TravelHistoryItem[]>([]) // 旅行历史记录
  const loading = ref(false) // 加载状态标识

  /** 拉取当前用户画像（偏好 + 旅行历史） */
  async function fetchProfile() {
    loading.value = true
    try {
      const response = await api.get<ProfileData>('/profile')
      preferences.value = response.data.preferences || {}
      travelHistory.value = response.data.travel_history || []
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新用户偏好（后端为增量合并）
   * @param pres - 要提交的偏好键值对（前端提交全量当前编辑中的偏好）
   */
  async function updatePreferences(pres: Record<string, any>) {
    const response = await api.put<ProfileData>('/profile/preferences', {
      preferences: pres,
    })
    preferences.value = response.data.preferences || {}
    return response.data
  }

  /**
   * 新增一条旅行历史记录
   * @param item - 含 destination、日期、备注的条目
   */
  async function addTravelHistory(item: TravelHistoryItem) {
    const response = await api.post<ProfileData>('/profile/history', item)
    travelHistory.value = response.data.travel_history || []
    return response.data
  }

  return {
    preferences,
    travelHistory,
    loading,
    fetchProfile,
    updatePreferences,
    addTravelHistory,
  }
})