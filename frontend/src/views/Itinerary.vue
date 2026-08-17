<template>
  <AppLayout :showBack="true">
    <div class="itinerary-wrapper" v-loading="loading">
      <template v-if="loadError">
        <el-result icon="error" title="加载失败" sub-title="无法获取行程数据">
          <template #extra>
            <el-button type="primary" @click="loadTrip">重试</el-button>
            <el-button @click="$router.push('/trips')">返回列表</el-button>
          </template>
        </el-result>
      </template>

      <template v-else-if="trip">
        <div class="content-panel">
          <el-card class="info-card">
            <template #header>
              <div class="card-header">
                <h2>{{ trip.title }}</h2>
                <el-tag
                  :type="trip.status === 'planned' ? 'success' : 'warning'"
                  effect="plain"
                  size="large"
                >
                  {{ trip.status === 'planned' ? '已规划' : '规划中' }}
                </el-tag>
              </div>
            </template>

            <el-descriptions :column="2" border class="trip-meta">
              <el-descriptions-item label="目的地">
                <el-icon><Location /></el-icon>
                {{ trip.destination }}
              </el-descriptions-item>
              <el-descriptions-item label="出行人数">
                <el-icon><User /></el-icon>
                {{ trip.travelers }} 人
              </el-descriptions-item>
              <el-descriptions-item label="日期" v-if="trip.start_date">
                {{ formatDate(trip.start_date) }}
                <template v-if="trip.end_date"> — {{ formatDate(trip.end_date) }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="预算" v-if="trip.budget?.min">
                ¥{{ trip.budget.min }} ~ ¥{{ trip.budget.max }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card class="itinerary-card" v-if="trip.itinerary?.content">
            <template #header>
              <span class="section-title">📋 行程安排</span>
            </template>
            <div class="content-text" v-html="formatItinerary(trip.itinerary.content)"></div>
          </el-card>

          <el-empty
            v-else
            description="AI 正在规划中，前往对话页面继续完善"
            :image-size="120"
          >
            <el-button type="primary" @click="$router.push(`/chat/${trip.id}`)">
              前往对话
            </el-button>
          </el-empty>

          <div class="actions" v-if="trip.itinerary?.content">
            <el-button type="primary" @click="$router.push(`/chat/${trip.id}`)">
              <el-icon><ChatDotRound /></el-icon>
              继续对话修改
            </el-button>
            <el-button @click="handleExport">
              <el-icon><Download /></el-icon>
              导出 Markdown
            </el-button>
            <el-button @click="handleCopyContent">
              <el-icon><CopyDocument /></el-icon>
              复制内容
            </el-button>
          </div>
        </div>

        <div class="map-panel">
          <div class="map-header">
            <span>📍 {{ trip.destination }}</span>
          </div>
          <MapView
            :center="mapCenter"
            :zoom="12"
            :markers="mapMarkers"
          />
        </div>
      </template>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useTripsStore } from '@/stores/trips'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/AppLayout.vue'
import MapView from '@/components/MapView.vue'
import dayjs from 'dayjs'

interface Trip {
  id: number
  title: string
  destination: string
  start_date?: string | null
  end_date?: string | null
  budget?: Record<string, any>
  travelers: number
  status: string
  itinerary: { content?: string } | null
}

const route = useRoute()
const tripsStore = useTripsStore()
const loading = ref(true)
const loadError = ref(false)
const trip = ref<Trip | null>(null)

const cityCoordinates: Record<string, [number, number]> = {
  '北京': [39.9042, 116.4074], '上海': [31.2304, 121.4737],
  '广州': [23.1291, 113.2644], '深圳': [22.5431, 114.0579],
  '杭州': [30.2741, 120.1551], '成都': [30.5728, 104.0668],
  '重庆': [29.4316, 106.9123], '西安': [34.2608, 108.9398],
  '南京': [32.0603, 118.7969], '武汉': [30.5928, 114.3055],
  '长沙': [28.2282, 112.9388], '厦门': [24.4798, 118.0894],
  '青岛': [36.0671, 120.3826], '大连': [38.9140, 121.6147],
  '三亚': [18.2528, 109.5120], '昆明': [25.0389, 102.7183],
  '哈尔滨': [45.8038, 126.5350], '拉萨': [29.6500, 91.1000],
  '东京': [35.6762, 139.6503], '巴黎': [48.8566, 2.3522],
  '曼谷': [13.7563, 100.5018], '新加坡': [1.3521, 103.8198],
}

const mapCenter = computed<[number, number]>(() => {
  if (!trip.value) return [39.9042, 116.4074]
  for (const [city, coords] of Object.entries(cityCoordinates)) {
    if (trip.value.destination.includes(city)) return coords
  }
  return [39.9042, 116.4074]
})

const mapMarkers = computed(() => {
  return trip.value
    ? [{ name: trip.value.destination, lat: mapCenter.value[0], lng: mapCenter.value[1] }]
    : []
})

async function loadTrip() {
  loading.value = true
  loadError.value = false
  try {
    trip.value = await tripsStore.fetchTrip(Number(route.params.tripId))
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadTrip()
})

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD')
}

function formatItinerary(content: string) {
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
}

function handleExport() {
  if (!trip.value?.itinerary?.content) return
  const content = `# ${trip.value.title}\n\n目的地：${trip.value.destination}\n\n${trip.value.itinerary.content}`
  const blob = new Blob([content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${trip.value.title}_行程.md`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('行程已导出')
}

async function handleCopyContent() {
  if (!trip.value?.itinerary?.content) return
  try {
    await navigator.clipboard.writeText(trip.value.itinerary.content)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.itinerary-wrapper {
  display: flex;
  height: calc(100vh - 64px);
}

.content-panel {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  min-width: 0;
}

.info-card {
  margin-bottom: 24px;
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  color: #333;
  font-size: 22px;
}

.trip-meta {
  margin-bottom: 0;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.itinerary-card {
  margin-bottom: 24px;
  border-radius: 12px;
}

.content-text {
  line-height: 1.8;
  color: #444;
  font-size: 15px;
}

.content-text :deep(h1) {
  font-size: 22px;
  color: #667eea;
  margin: 20px 0 10px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid #667eea;
}

.content-text :deep(h2) {
  font-size: 18px;
  color: #555;
  margin: 16px 0 8px 0;
  padding-left: 10px;
  border-left: 3px solid #667eea;
}

.content-text :deep(h3) {
  font-size: 16px;
  color: #666;
  margin: 12px 0 6px 0;
}

.content-text :deep(strong) {
  color: #667eea;
}

.actions {
  padding: 20px 0;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.map-panel {
  width: 380px;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #eee;
  background: white;
  flex-shrink: 0;
}

.map-header {
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  display: flex;
  align-items: center;
  gap: 6px;
}

.map-panel :deep(.map-wrapper) {
  flex: 1;
}
</style>