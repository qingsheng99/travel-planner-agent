<template>
  <div class="trips-container">
    <el-header class="header">
      <div class="logo">✈️ AI旅行规划助手</div>
      <div class="nav">
        <el-button type="text" @click="$router.push('/')">首页</el-button>
        <el-button type="text" @click="$router.push('/trips')">我的行程</el-button>
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><User /></el-icon>
            {{ authStore.user?.username }}
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    
    <div class="main-content">
      <div class="page-header">
        <h1>我的行程</h1>
        <el-button type="primary" @click="$router.push('/')">
          <el-icon><Plus /></el-icon>
          创建新行程
        </el-button>
      </div>
      
      <el-empty v-if="tripsStore.trips.length === 0 && !tripsStore.loading" description="还没有行程，去创建一个吧" />
      
      <el-row :gutter="20" v-else>
        <el-col :span="8" v-for="trip in tripsStore.trips" :key="trip.id" class="trip-col">
          <el-card class="trip-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>{{ trip.title }}</span>
                <el-tag :type="trip.status === 'planned' ? 'success' : 'warning'" size="small">
                  {{ trip.status === 'planned' ? '已规划' : '规划中' }}
                </el-tag>
              </div>
            </template>
            <p class="info">
              <el-icon><Location /></el-icon>
              {{ trip.destination }}
            </p>
            <p class="info" v-if="trip.start_date">
              <el-icon><Calendar /></el-icon>
              {{ formatDate(trip.start_date) }} - {{ trip.end_date ? formatDate(trip.end_date) : '' }}
            </p>
            <p class="info">
              <el-icon><User /></el-icon>
              {{ trip.travelers }} 人
            </p>
            <div class="actions">
              <el-button type="primary" size="small" @click="$router.push(`/chat/${trip.id}`)">
                {{ trip.status === 'planned' ? '查看对话' : '继续规划' }}
              </el-button>
              <el-button v-if="trip.itinerary?.content" size="small" @click="$router.push(`/itinerary/${trip.id}`)">
                查看行程
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTripsStore } from '@/stores/trips'
import dayjs from 'dayjs'

const router = useRouter()
const authStore = useAuthStore()
const tripsStore = useTripsStore()

onMounted(() => {
  authStore.fetchUser()
  tripsStore.fetchTrips()
})

function handleCommand(command: string) {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD')
}
</script>

<style scoped>
.trips-container {
  min-height: 100vh;
  background: #f5f7fa;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 0 40px;
}
.logo {
  font-size: 20px;
  font-weight: bold;
  color: #667eea;
}
.nav {
  display: flex;
  align-items: center;
  gap: 20px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #666;
}
.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}
.page-header h1 {
  color: #333;
  margin: 0;
}
.trip-col {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
  margin: 8px 0;
}
.actions {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}
</style>
