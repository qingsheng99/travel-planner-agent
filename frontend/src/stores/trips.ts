/**
 * 行程数据管理模块
 * 负责行程列表的获取、创建、详情查看及行程路线的保存，
 * 与后端 /trips 相关 API 进行交互。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

/** 行程完整信息接口 */
interface Trip {
  id: number
  title: string
  destination: string
  start_date: string | null
  end_date: string | null
  budget: Record<string, any> // 预算信息
  travelers: number // 旅行人数
  status: string // 行程状态
  itinerary: Record<string, any> // 行程路线数据
  created_at: string
}

/** 创建行程时提交的数据接口 */
interface TripCreateData {
  title: string
  destination: string
  start_date?: string | null
  end_date?: string | null
  budget?: Record<string, any>
  travelers?: number
}

/** 行程 Store：管理行程列表、当前行程及增删改查操作 */
export const useTripsStore = defineStore('trips', () => {
  const trips = ref<Trip[]>([]) // 行程列表
  const currentTrip = ref<Trip | null>(null) // 当前查看/编辑的行程
  const loading = ref(false) // 加载状态标识

  /** 获取所有行程列表 */
  async function fetchTrips() {
    loading.value = true
    try {
      const response = await api.get<Trip[]>('/trips')
      trips.value = response.data
    } finally {
      loading.value = false
    }
  }

  /**
   * 根据 ID 获取单个行程详情
   * @param tripId - 行程 ID
   * @returns 行程详情数据
   */
  async function fetchTrip(tripId: number) {
    const response = await api.get<Trip>(`/trips/${tripId}`)
    currentTrip.value = response.data
    return response.data
  }

  /**
   * 创建新行程
   * @param tripData - 行程基本信息
   * @returns 创建成功的行程数据
   */
  async function createTrip(tripData: TripCreateData) {
    const response = await api.post<Trip>('/trips', tripData)
    trips.value.unshift(response.data) // 新行程插入列表头部
    return response.data
  }

  /**
   * 保存行程路线
   * @param tripId - 行程 ID
   * @param itinerary - 路线数据
   * @returns 更新后的行程数据
   */
  async function saveItinerary(tripId: number, itinerary: Record<string, any>) {
    const response = await api.put<Trip>(`/trips/${tripId}/itinerary`, itinerary)
    currentTrip.value = response.data
    return response.data
  }

  return {
    trips,
    currentTrip,
    loading,
    fetchTrips,
    fetchTrip,
    createTrip,
    saveItinerary,
  }
})