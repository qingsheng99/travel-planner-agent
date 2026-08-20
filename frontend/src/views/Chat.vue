<template>
  <AppLayout :showBack="true">
    <div class="chat-wrapper">
      <div class="chat-panel">
        <div class="chat-messages" ref="messagesRef">
          <div v-if="chatStore.messages.length === 0" class="welcome">
            <el-empty description="开始对话，让AI帮您规划旅行">
              <template #image>
                <div style="font-size: 64px; margin-bottom: 10px;">🤖</div>
              </template>
              <div class="suggestions">
                <el-button
                  v-for="s in suggestions"
                  :key="s"
                  size="small"
                  round
                  @click="sendSuggestion(s)"
                >
                  {{ s }}
                </el-button>
              </div>
            </el-empty>
          </div>

          <div
            v-for="msg in chatStore.messages"
            :key="msg.id"
            class="message"
            :class="msg.role"
          >
            <div class="avatar">
              <el-avatar v-if="msg.role === 'user'" :size="36" icon="UserFilled" />
              <span v-else class="bot-avatar">🤖</span>
            </div>
            <div class="msg-content">
              <div class="bubble" v-html="formatMessage(msg.content)"></div>
              <div class="time">{{ formatTime(msg.timestamp) }}</div>
            </div>
          </div>

          <div v-if="chatStore.isStreaming" class="message assistant">
            <div class="avatar">
              <span class="bot-avatar">🤖</span>
            </div>
            <div class="msg-content">
              <div class="bubble typing-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input-area">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="2"
            placeholder="输入您的问题，AI 将为您规划旅行..."
            :disabled="chatStore.isStreaming"
            @keydown.enter.exact.prevent="sendMessage"
            resize="none"
            class="chat-textarea"
          />
          <el-button
            type="primary"
            :icon="Promotion"
            circle
            :loading="chatStore.isStreaming"
            :disabled="!inputMessage.trim()"
            @click="sendMessage"
            class="send-btn"
          />
        </div>
      </div>

      <div class="map-panel" v-if="showMap">
        <div class="map-header">
          <span>📍 {{ destination || '地图视图' }}</span>
          <el-button text size="small" @click="showMap = false">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <MapView
          ref="mapRef"
          :center="mapCenter"
          :zoom="12"
          :markers="mapMarkers"
        />
      </div>

      <div v-else class="map-toggle" @click="showMap = true">
        <el-button type="primary" circle>
          <el-icon><MapLocation /></el-icon>
        </el-button>
        <span>查看地图</span>
      </div>
    </div>
  </AppLayout>
</template>

<!--
  聊天页面 - 与 AI 助手对话，规划旅行行程
  支持流式对话、快捷建议、地图侧边栏视图
-->
<script setup lang="ts">
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import AppLayout from '@/components/AppLayout.vue'
import MapView from '@/components/MapView.vue'
import { Promotion } from '@element-plus/icons-vue'

const route = useRoute()
const chatStore = useChatStore()

// 用户输入的消息内容
const inputMessage = ref('')
// 消息列表容器的 DOM 引用，用于自动滚动到底部
const messagesRef = ref<HTMLElement>()
// 地图组件的实例引用
const mapRef = ref<InstanceType<typeof MapView>>()
// 是否显示地图侧边栏
const showMap = ref(false)
// 从路由参数中获取行程 ID 和目的地名称
const tripId = route.params.tripId as string | undefined
const destination = (route.query.destination as string) || ''

// 快捷建议列表，用户点击即可发送
const suggestions = [
  '帮我规划一个3天的行程',
  '推荐几个必去的景点',
  '怎么安排交通比较好？',
  '推荐当地美食和餐厅',
  '帮我做一份预算规划',
]

// 城市坐标映射表，用于在地图上定位目的地
const cityCoordinates: Record<string, [number, number]> = {
  '北京': [39.9042, 116.4074],
  '上海': [31.2304, 121.4737],
  '广州': [23.1291, 113.2644],
  '深圳': [22.5431, 114.0579],
  '杭州': [30.2741, 120.1551],
  '成都': [30.5728, 104.0668],
  '重庆': [29.4316, 106.9123],
  '西安': [34.2608, 108.9398],
  '南京': [32.0603, 118.7969],
  '武汉': [30.5928, 114.3055],
  '长沙': [28.2282, 112.9388],
  '厦门': [24.4798, 118.0894],
  '青岛': [36.0671, 120.3826],
  '大连': [38.9140, 121.6147],
  '三亚': [18.2528, 109.5120],
  '昆明': [25.0389, 102.7183],
  '哈尔滨': [45.8038, 126.5350],
  '拉萨': [29.6500, 91.1000],
  '东京': [35.6762, 139.6503],
  '巴黎': [48.8566, 2.3522],
  '曼谷': [13.7563, 100.5018],
  '新加坡': [1.3521, 103.8198],
}

/** 根据目的地名称自动匹配地图中心坐标 */
const mapCenter = computed<[number, number]>(() => {
  for (const [city, coords] of Object.entries(cityCoordinates)) {
    if (destination.includes(city)) return coords
  }
  return [39.9042, 116.4074] // 默认北京
})

/** 地图标记点，标记目的地位置 */
const mapMarkers = computed(() => {
  return [{ name: destination || '目的地', lat: mapCenter.value[0], lng: mapCenter.value[1] }]
})

/** 页面加载时清空旧消息，如果带有目的地参数则自动发一条问候消息 */
onMounted(() => {
  chatStore.clearMessages()
  if (destination) {
    showMap.value = true
    setTimeout(() => {
      chatStore.addMessage(
        'assistant',
        `您好！我是您的AI旅行助手 🤖\n\n我来帮您规划 **${destination}** 的旅程。告诉我您的需求：\n\n- 🗓 计划玩几天？\n- 💰 预算大概多少？\n- 🎯 有什么特别想去的地方或偏好吗？`
      )
    }, 500)
  }
})

/** 监听消息数量变化，新消息出现时自动滚动到底部 */
watch(() => chatStore.messages.length, () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
})

/** 点击快捷建议：将建议文本填入输入框并发送 */
function sendSuggestion(text: string) {
  inputMessage.value = text
  sendMessage()
}

/** 发送消息：调用 chatStore 的流式接口发送消息 */
async function sendMessage() {
  if (!inputMessage.value.trim() || chatStore.isStreaming) return

  const message = inputMessage.value
  inputMessage.value = ''

  await chatStore.startStream(message, tripId ? Number(tripId) : null, destination)
}

/** 格式化时间戳为 HH:mm 格式 */
function formatTime(timestamp: Date) {
  return new Date(timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

/** 格式化消息内容：将 Markdown 风格的文本转换为安全的 HTML */
function formatMessage(content: string) {
  return content
    .replace(/&/g, '&amp;')           // 转义 &
    .replace(/</g, '&lt;')            // 转义 <
    .replace(/>/g, '&gt;')            // 转义 >
    .replace(/\n/g, '<br>')           // 换行转 <br>
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // **加粗**
    .replace(/^### (.*$)/gm, '<h4>$1</h4>')             // ### 四级标题
    .replace(/^## (.*$)/gm, '<h3>$1</h3>')              // ## 三级标题
    .replace(/^# (.*$)/gm, '<h2>$1</h2>')               // # 二级标题
}
</script>

<style scoped>
.chat-wrapper {
  display: flex;
  height: calc(100vh - 64px);
  position: relative;
}

.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #f5f7fa;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.welcome {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 16px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 80%;
}

.message.user {
  margin-left: auto;
  flex-direction: row-reverse;
}

.message.assistant {
  margin-right: auto;
}

.avatar {
  flex-shrink: 0;
}

.bot-avatar {
  font-size: 28px;
  line-height: 36px;
}

.msg-content {
  display: flex;
  flex-direction: column;
}

.message.user .msg-content {
  align-items: flex-end;
}

.bubble {
  padding: 12px 16px;
  border-radius: 16px;
  line-height: 1.6;
  font-size: 14px;
  word-break: break-word;
}

.message.assistant .bubble {
  background: white;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.message.user .bubble {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-bottom-right-radius: 4px;
}

.bubble :deep(h2) {
  font-size: 18px;
  margin: 12px 0 8px 0;
  color: #667eea;
}

.bubble :deep(h3) {
  font-size: 16px;
  margin: 10px 0 6px 0;
  color: #555;
}

.bubble :deep(h4) {
  font-size: 15px;
  margin: 8px 0 4px 0;
  color: #666;
}

.bubble :deep(strong) {
  color: #667eea;
}

.message.user .bubble :deep(strong) {
  color: #fff;
}

.time {
  font-size: 12px;
  color: #bbb;
  margin-top: 4px;
}

.typing-dots {
  display: flex;
  gap: 4px;
  padding: 16px 20px;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  background: #667eea;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-8px); opacity: 1; }
}

.chat-input-area {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  background: white;
  border-top: 1px solid #eee;
  align-items: flex-end;
}

.chat-textarea :deep(.el-textarea__inner) {
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 14px;
  resize: none;
}

.send-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
}

.map-panel {
  width: 380px;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #eee;
  background: white;
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.map-panel .map-wrapper {
  flex: 1;
}

.map-toggle {
  position: fixed;
  bottom: 30px;
  right: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  z-index: 50;
}

.map-toggle span {
  font-size: 12px;
  color: #667eea;
  font-weight: 500;
}
</style>