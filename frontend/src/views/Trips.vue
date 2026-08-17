<template>
  <AppLayout>
    <div class="main-content">
      <div class="page-header">
        <h1>我的行程</h1>
        <el-button type="primary" @click="$router.push('/')">
          <el-icon><Plus /></el-icon>
          创建新行程
        </el-button>
      </div>

      <div v-if="tripsStore.loading" class="loading-area">
        <el-skeleton animated>
          <template #template>
            <el-skeleton-item v-for="i in 3" :key="i" variant="rect" style="height: 180px; margin-bottom: 20px; border-radius: 12px;" />
          </template>
        </el-skeleton>
      </div>

      <el-empty
        v-else-if="tripsStore.trips.length === 0"
        description="还没有行程，去创建一个吧"
        :image-size="160"
      >
        <el-button type="primary" @click="$router.push('/')">创建行程</el-button>
      </el-empty>

      <el-row :gutter="20" v-else>
        <el-col :span="8" v-for="trip in tripsStore.trips" :key="trip.id" class="trip-col">
          <el-card class="trip-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span class="card-title">{{ trip.title }}</span>
                <el-tag
                  :type="trip.status === 'planned' ? 'success' : 'warning'"
                  size="small"
                  effect="plain"
                >
                  {{ trip.status === 'planned' ? '已规划' : '规划中' }}
                </el-tag>
              </div>
            </template>
            <div class="card-body">
              <p class="info">
                <el-icon><Location /></el-icon>
                {{ trip.destination }}
              </p>
              <p class="info" v-if="trip.start_date">
                <el-icon><Calendar /></el-icon>
                {{ formatDate(trip.start_date) }}
                <template v-if="trip.end_date"> — {{ formatDate(trip.end_date) }}</template>
              </p>
              <p class="info">
                <el-icon><User /></el-icon>
                {{ trip.travelers }} 人出行
              </p>
              <p class="info" v-if="trip.budget?.min">
                <el-icon><Money /></el-icon>
                ¥{{ trip.budget.min }} ~ ¥{{ trip.budget.max }}
              </p>
            </div>
            <div class="actions">
              <el-button
                type="primary"
                size="small"
                @click="$router.push(`/chat/${trip.id}`)"
              >
                {{ trip.status === 'planned' ? '查看对话' : '继续规划' }}
              </el-button>
              <el-button
                v-if="trip.itinerary?.content"
                size="small"
                plain
                @click="$router.push(`/itinerary/${trip.id}`)"
              >
                查看行程
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTripsStore } from '@/stores/trips'
import AppLayout from '@/components/AppLayout.vue'
import dayjs from 'dayjs'

const router = useRouter()
const authStore = useAuthStore()
const tripsStore = useTripsStore()

onMounted(() => {
  authStore.fetchUser()
  tripsStore.fetchTrips()
})

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD')
}
</script>

<style scoped>
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
  font-size: 28px;
}

.loading-area {
  padding: 20px 0;
}

.trip-col {
  margin-bottom: 20px;
}

.trip-card {
  border-radius: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.trip-card:hover {
  transform: translateY(-4px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-weight: 600;
  color: #333;
  font-size: 16px;
}

.card-body {
  min-height: 120px;
}

.info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
  margin: 10px 0;
  font-size: 14px;
}

.info .el-icon {
  color: #999;
}

.actions {
  margin-top: 10px;
  padding-top: 15px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  gap: 10px;
}
</style>