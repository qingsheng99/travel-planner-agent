<template>
  <AppLayout>
    <div class="main-content">
      <div class="page-header">
        <h1>偏好设置</h1>
        <el-button text @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
      </div>

      <el-row :gutter="20">
        <!-- 偏好设置卡片 -->
        <el-col :span="14">
          <el-card class="card" shadow="hover">
            <template #header>
              <span class="card-title">我的偏好</span>
              <span class="card-tip">这些偏好会在生成行程时被 AI 参考</span>
            </template>

            <div v-if="profileStore.loading" class="loading-area">
              <el-skeleton animated :rows="4" />
            </div>

            <template v-else>
              <!-- 动态键值编辑列表 -->
              <div v-for="(item, index) in prefRows" :key="index" class="pref-row">
                <el-input
                  v-model="item.key"
                  placeholder="偏好名称（如 饮食、预算）"
                  class="pref-key"
                  :disabled="!!item.originalKey"
                />
                <el-input
                  v-model="item.value"
                  placeholder="偏好值（如 清淡、低价）"
                  class="pref-value"
                />
                <el-button
                  circle
                  type="danger"
                  plain
                  :icon="Delete"
                  @click="removeRow(index)"
                />
              </div>

              <el-button class="add-btn" text type="primary" :icon="Plus" @click="addRow">
                添加偏好
              </el-button>

              <div class="footer">
                <el-button type="primary" :loading="savingPref" @click="savePreferences">
                  保存偏好
                </el-button>
              </div>
            </template>
          </el-card>
        </el-col>

        <!-- 旅行历史卡片 -->
        <el-col :span="10">
          <el-card class="card" shadow="hover">
            <template #header>
              <span class="card-title">旅行历史</span>
            </template>

            <div v-if="profileStore.loading" class="loading-area">
              <el-skeleton animated :rows="4" />
            </div>

            <template v-else>
              <!-- 旅行历史列表 -->
              <div v-if="profileStore.travelHistory.length === 0" class="empty-tip">
                还没有旅行记录，添加一条吧
              </div>
              <div v-for="(item, i) in profileStore.travelHistory" :key="i" class="history-item">
                <div class="history-head">
                  <span class="history-dest">{{ item.destination }}</span>
                  <el-tag size="small" type="info" effect="plain" v-if="item.start_date">
                    {{ item.start_date }}{{ item.end_date ? ` ~ ${item.end_date}` : '' }}
                  </el-tag>
                </div>
                <div v-if="item.note" class="history-note">{{ item.note }}</div>
              </div>

              <el-divider />

              <!-- 新增历史表单 -->
              <el-form :model="historyForm" label-width="70px" size="small">
                <el-form-item label="目的地">
                  <el-input v-model="historyForm.destination" placeholder="如 北京" />
                </el-form-item>
                <el-form-item label="出发日期">
                  <el-date-picker
                    v-model="historyForm.start_date"
                    type="date"
                    value-format="YYYY-MM-DD"
                    placeholder="选择日期"
                  />
                </el-form-item>
                <el-form-item label="返回日期">
                  <el-date-picker
                    v-model="historyForm.end_date"
                    type="date"
                    value-format="YYYY-MM-DD"
                    placeholder="选择日期"
                  />
                </el-form-item>
                <el-form-item label="备注">
                  <el-input v-model="historyForm.note" type="textarea" :rows="2" placeholder="想记录点什么？" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="savingHistory" @click="saveHistory">
                    添加记录
                  </el-button>
                </el-form-item>
              </el-form>
            </template>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
/**
 * 偏好设置页面
 * 展示并编辑用户偏好键值对，以及维护旅行历史记录。
 * 偏好数据后端采用“增量合并”策略，前端每次提交当前编辑中的全量偏好。
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import { useProfileStore } from '@/stores/profile'

/** 偏好编辑行接口 */
interface PrefRow {
  key: string // 偏好名称
  value: string // 偏好值
  originalKey?: string // 原始键（后端已存在时锁定键名，仅允许修改值）
}

const profileStore = useProfileStore()

/** 偏好编辑行数组 */
const prefRows = ref<PrefRow[]>([])
/** 保存偏好时的加载状态 */
const savingPref = ref(false)
/** 保存历史时的加载状态 */
const savingHistory = ref(false)

/** 旅行历史新增表单 */
const historyForm = reactive({
  destination: '',
  start_date: null as string | null,
  end_date: null as string | null,
  note: '',
})

onMounted(async () => {
  await loadProfile()
})

/**
 * 加载用户画像，并把后端 preferences 字典转换为可编辑的行数组
 */
async function loadProfile() {
  await profileStore.fetchProfile()
  prefRows.value = Object.entries(profileStore.preferences).map(([key, value]) => ({
    key,
    value: String(value),
    originalKey: key, // 已存在的偏好锁定键名
  }))
}

/** 新增一行空偏好 */
function addRow() {
  prefRows.value.push({ key: '', value: '' })
}

/**
 * 删除某行偏好
 * @param index - 行索引
 */
function removeRow(index: number) {
  prefRows.value.splice(index, 1)
}

/**
 * 保存偏好：过滤空键，提交全量偏好键值对
 */
async function savePreferences() {
  // 过滤掉键名为空的行
  const pres: Record<string, string> = {}
  for (const row of prefRows.value) {
    if (row.key.trim()) {
      pres[row.key.trim()] = row.value
    }
  }
  savingPref.value = true
  try {
    await profileStore.updatePreferences(pres)
    // 用后端返回的最新偏好重建编辑行
    prefRows.value = Object.entries(profileStore.preferences).map(([key, value]) => ({
      key,
      value: String(value),
      originalKey: key,
    }))
    ElMessage.success('偏好已保存')
  } finally {
    savingPref.value = false
  }
}

/**
 * 保存新的旅行历史记录
 */
async function saveHistory() {
  if (!historyForm.destination.trim()) {
    ElMessage.warning('请填写目的地')
    return
  }
  savingHistory.value = true
  try {
    await profileStore.addTravelHistory({
      destination: historyForm.destination.trim(),
      start_date: historyForm.start_date,
      end_date: historyForm.end_date,
      note: historyForm.note || undefined,
    })
    ElMessage.success('已添加旅行记录')
    // 重置表单
    historyForm.destination = ''
    historyForm.start_date = null
    historyForm.end_date = null
    historyForm.note = ''
  } finally {
    savingHistory.value = false
  }
}
</script>

<style scoped>
.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.card {
  border-radius: 12px;
}

.card-title {
  font-weight: 600;
  color: #303133;
}

.card-tip {
  float: right;
  font-size: 12px;
  color: #999;
  line-height: 24px;
}

.loading-area {
  padding: 12px 0;
}

.pref-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.pref-key {
  width: 40%;
}

.pref-value {
  flex: 1;
}

.add-btn {
  margin-bottom: 8px;
}

.footer {
  margin-top: 12px;
  text-align: right;
}

.empty-tip {
  color: #999;
  padding: 12px 0;
}

.history-item {
  padding: 10px 0;
  border-bottom: 1px dashed #ebeef5;
}

.history-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.history-dest {
  font-weight: 600;
  color: #303133;
}

.history-note {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}
</style>