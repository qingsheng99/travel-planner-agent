<template>
  <AppLayout>
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
                <el-input
                  v-model="tripForm.destination"
                  placeholder="例如：北京、东京、巴黎..."
                  size="large"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="行程名称">
                <el-input
                  v-model="tripForm.title"
                  placeholder="给这次旅行起个名字"
                  size="large"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="出发日期">
                <el-date-picker
                  v-model="tripForm.startDate"
                  type="date"
                  placeholder="选择日期"
                  size="large"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="返回日期">
                <el-date-picker
                  v-model="tripForm.endDate"
                  type="date"
                  placeholder="选择日期"
                  size="large"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="出行人数">
                <el-input-number
                  v-model="tripForm.travelers"
                  :min="1"
                  :max="10"
                  size="large"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="预算范围（元）">
            <el-slider v-model="budgetRange" range :min="500" :max="50000" :step="500" />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              style="width: 200px"
              :loading="creating"
              @click="startPlanning"
            >
              开始规划
              <el-icon><Promotion /></el-icon>
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <div v-if="tripsStore.loading" class="section-loading">
        <el-skeleton :rows="2" animated />
      </div>

      <div v-else-if="tripsStore.trips.length > 0" class="recent-trips">
        <div class="section-header">
          <h2>最近行程</h2>
          <el-button text type="primary" @click="$router.push('/trips')">
            查看全部
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
        <el-row :gutter="20">
          <el-col :span="8" v-for="trip in tripsStore.trips.slice(0, 3)" :key="trip.id">
            <el-card class="trip-card" shadow="hover" @click="goToChat(trip.id)">
              <h3>{{ trip.title }}</h3>
              <p class="destination">📍 {{ trip.destination }}</p>
              <p class="travelers" v-if="trip.travelers">👥 {{ trip.travelers }} 人</p>
              <div class="card-footer">
                <el-tag :type="trip.status === 'planned' ? 'success' : 'warning'" size="small">
                  {{ trip.status === 'planned' ? '已规划' : '规划中' }}
                </el-tag>
                <span class="cta">继续对话 →</span>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>
  </AppLayout>
</template>

<!--
  首页 - AI旅行规划助手的主页面
  提供行程规划表单（目的地、日期、人数、预算），展示最近创建的行程列表
-->
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTripsStore } from '@/stores/trips'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/AppLayout.vue'

const router = useRouter()
const authStore = useAuthStore()
const tripsStore = useTripsStore()

// 是否正在创建行程（控制按钮加载状态）
const creating = ref(false)
// 预算范围滑块的值，默认 2000 ~ 10000 元
const budgetRange = ref([2000, 10000])

// 行程表单数据模型
const tripForm = reactive({
  title: '',           // 行程名称
  destination: '',     // 目的地
  startDate: null as string | null,  // 出发日期
  endDate: null as string | null,    // 返回日期
  travelers: 2,        // 出行人数，默认 2 人
})

/** 页面加载时获取用户信息和已有行程列表 */
onMounted(() => {
  authStore.fetchUser()
  tripsStore.fetchTrips()
})

/** 跳转到指定行程的对话页面 */
function goToChat(tripId: number) {
  router.push(`/chat/${tripId}`)
}

/** 开始规划：验证表单数据，创建行程，然后跳转到对话页面 */
async function startPlanning() {
  // 校验目的地是否已填写
  if (!tripForm.destination) {
    ElMessage.warning('请输入目的地')
    return
  }
  // 如果未填写行程名称，自动生成
  if (!tripForm.title) {
    tripForm.title = `${tripForm.destination}之旅`
  }

  creating.value = true
  try {
    // 调用 store 创建新行程
    const trip = await tripsStore.createTrip({
      title: tripForm.title,
      destination: tripForm.destination,
      start_date: tripForm.startDate,
      end_date: tripForm.endDate,
      travelers: tripForm.travelers,
      budget: { min: budgetRange.value[0], max: budgetRange.value[1] },
    })
    ElMessage.success('行程已创建')
    // 跳转到对话页面，同时携带目的地参数
    router.push(`/chat/${trip.id}?destination=${encodeURIComponent(tripForm.destination)}`)
  } catch {
    // 错误已在 api 拦截器中处理
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 16px;
}

.hero-section p {
  font-size: 18px;
  color: #666;
}

.planner-card {
  margin-bottom: 40px;
  border-radius: 12px;
}

.planner-card :deep(.el-card__body) {
  padding: 30px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  color: #333;
  margin: 0;
}

.section-loading {
  padding: 40px 0;
}

.recent-trips {
  margin-top: 10px;
}

.trip-card {
  cursor: pointer;
  border-radius: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.trip-card:hover {
  transform: translateY(-4px);
}

.trip-card h3 {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 18px;
}

.destination {
  color: #666;
  margin: 0 0 6px 0;
}

.travelers {
  color: #999;
  margin: 0 0 12px 0;
  font-size: 14px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cta {
  color: #667eea;
  font-size: 13px;
  font-weight: 500;
}
</style>