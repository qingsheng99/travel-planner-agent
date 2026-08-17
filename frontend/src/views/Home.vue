<template>
  <div class="home-container">
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
      <div class="hero-section">
        <h1>让AI为您规划完美旅程</h1>
        <p>告诉我们您想去哪里，AI助手将为您定制个性化旅行方案</p>
      </div>
      
      <el-card class="planner-card">
        <el-form :model="tripForm" label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="目的地">
                <el-input v-model="tripForm.destination" placeholder="例如：北京、东京、巴黎..." size="large" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="行程名称">
                <el-input v-model="tripForm.title" placeholder="给这次旅行起个名字" size="large" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="出发日期">
                <el-date-picker v-model="tripForm.startDate" type="date" placeholder="选择日期" size="large" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="返回日期">
                <el-date-picker v-model="tripForm.endDate" type="date" placeholder="选择日期" size="large" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="出行人数">
                <el-input-number v-model="tripForm.travelers" :min="1" :max="10" size="large" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="预算范围（元）">
            <el-slider v-model="budgetRange" range :min="500" :max="50000" :step="500" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="large" style="width: 200px" :loading="creating" @click="startPlanning">
              开始规划
              <el-icon><Promotion /></el-icon>
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
      
      <div v-if="tripsStore.trips.length > 0" class="recent-trips">
        <h2>最近行程</h2>
        <el-row :gutter="20">
          <el-col :span="8" v-for="trip in tripsStore.trips.slice(0, 3)" :key="trip.id">
            <el-card class="trip-card" shadow="hover" @click="$router.push(`/chat/${trip.id}`)">
              <h3>{{ trip.title }}</h3>
              <p class="destination">📍 {{ trip.destination }}</p>
              <p class="status">
                <el-tag :type="trip.status === 'planned' ? 'success' : 'warning'">
                  {{ trip.status === 'planned' ? '已规划' : '规划中' }}
                </el-tag>
              </p>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTripsStore } from '@/stores/trips'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const tripsStore = useTripsStore()
const creating = ref(false)
const budgetRange = ref([2000, 10000])

const tripForm = reactive({
  title: '',
  destination: '',
  startDate: null,
  endDate: null,
  travelers: 2
})

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

async function startPlanning() {
  if (!tripForm.destination) {
    ElMessage.warning('请输入目的地')
    return
  }
  if (!tripForm.title) {
    tripForm.title = `${tripForm.destination}之旅`
  }
  
  creating.value = true
  try {
    const trip = await tripsStore.createTrip({
      title: tripForm.title,
      destination: tripForm.destination,
      start_date: tripForm.startDate,
      end_date: tripForm.endDate,
      travelers: tripForm.travelers,
      budget: { min: budgetRange.value[0], max: budgetRange.value[1] }
    })
    ElMessage.success('行程创建成功')
    router.push(`/chat/${trip.id}?destination=${encodeURIComponent(tripForm.destination)}`)
  } catch (e) {
    console.error(e)
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.home-container {
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
  max-width: 1000px;
  margin: 0 auto;
  padding: 40px 20px;
}
.hero-section {
  text-align: center;
  margin-bottom: 40px;
}
.hero-section h1 {
  font-size: 42px;
  color: #333;
  margin-bottom: 16px;
}
.hero-section p {
  font-size: 18px;
  color: #666;
}
.planner-card {
  margin-bottom: 40px;
}
.recent-trips h2 {
  margin-bottom: 20px;
  color: #333;
}
.trip-card {
  cursor: pointer;
  margin-bottom: 20px;
}
.trip-card h3 {
  margin: 0 0 10px 0;
  color: #333;
}
.destination {
  color: #666;
  margin: 0 0 10px 0;
}
</style>
