import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

interface Trip {
  id: number
  title: string
  destination: string
  start_date: string | null
  end_date: string | null
  budget: Record<string, any>
  travelers: number
  status: string
  itinerary: Record<string, any>
  created_at: string
}

interface TripCreateData {
  title: string
  destination: string
  start_date?: string | null
  end_date?: string | null
  budget?: Record<string, any>
  travelers?: number
}

export const useTripsStore = defineStore('trips', () => {
  const trips = ref<Trip[]>([])
  const currentTrip = ref<Trip | null>(null)
  const loading = ref(false)

  async function fetchTrips() {
    loading.value = true
    try {
      const response = await api.get<Trip[]>('/trips')
      trips.value = response.data
    } finally {
      loading.value = false
    }
  }

  async function fetchTrip(tripId: number) {
    const response = await api.get<Trip>(`/trips/${tripId}`)
    currentTrip.value = response.data
    return response.data
  }

  async function createTrip(tripData: TripCreateData) {
    const response = await api.post<Trip>('/trips', tripData)
    trips.value.unshift(response.data)
    return response.data
  }

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