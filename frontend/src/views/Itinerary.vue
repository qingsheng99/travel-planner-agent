<template>
  <div class="itinerary-container">
    <el-header class="header">
      <div class="header-left">
        <el-button text @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <span class="title">📋 行程详情</span>
      </div>
    </el-header>
    
    <div class="main-content" v-loading="loading">
      <el-card v-if="trip" class="itinerary-card">
        <template #header>
          <div class="card-header">
            <h2>{{ trip.title }}</h2>
            <el-tag type="success">已规划</el-tag>
          </div>
        </template>
        
        <div class="trip-meta">
          <el-descriptions :column="3" border>
            <el-descriptions-item label="目的地">
              <el-icon><Location /></el-icon> {{ trip.destination }}
            </el-descriptions-item>
            <el-descriptions-item label="出行人数">{{ trip.travelers }} 人</el-descriptions-item>
            <el-descriptions-item label="状态">{{ trip.status === 'planned' ? '已规划' : '规划中' }}</el-descriptions-item>
          </el-descriptions>
        </div>
        
        <div class="itinerary-content" v-if="trip.itinerary?.content">
          <h3>行程安排</h3>
          <div class="content-text" v-html="formatItinerary(trip.itinerary.content)"></div>
        </div>
        
        <div class="actions">
          <el-button type="primary" @click="$router.push(`/chat/${trip.id}`)">
            <el-icon><ChatDotRound /></el-icon>
            继续对话修改
          </el-button>
          <el-button @click="handleExport">
            <el-icon><Download /></el-icon>
            导出行程
          </el-button>
        </div>
      </el-card>
      
      <el-empty v-else-if="!loading" description="未找到行程" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTripsStore } from '@/stores/trips'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Location, ChatDotRound, Download } from '@element-plus/icons-vue'

interface Trip {
  id: number
  title: string
  destination: string
  travelers: number
  status: string
  itinerary: { content?: string }
}

const route = useRoute()
const tripsStore = useTripsStore()
const loading = ref(true)
const trip = ref<Trip | null>(null)

onMounted(async () => {
  try {
    trip.value = await tripsStore.fetchTrip(Number(route.params.tripId))
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

function formatItinerary(content: string) {
  return content
    .replace(/\n/g, '<br>')
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
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
</script>

<style scoped>
.itinerary-container {
  min-height: 100vh;
  background: #f5f7fa;
}
.header {
  display: flex;
  align-items: center;
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 0 20px;
  height: 60px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}
.title {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}
.main-content {
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-header h2 {
  margin: 0;
  color: #333;
}
.trip-meta {
  margin-bottom: 30px;
}
.itinerary-content h3 {
  color: #333;
  margin: 20px 0 15px 0;
  padding-bottom: 10px;
  border-bottom: 2px solid #667eea;
}
.content-text {
  line-height: 1.8;
  color: #444;
  white-space: pre-wrap;
}
.content-text :deep(h3) {
  color: #667eea;
  margin-top: 20px;
}
.actions {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 15px;
}
</style>
