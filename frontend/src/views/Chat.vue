<template>
  <div class="chat-container">
    <el-header class="header">
      <div class="header-left">
        <el-button text @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <span class="title">💬 AI旅行助手</span>
        <span v-if="destination" class="destination">📍 {{ destination }}</span>
      </div>
    </el-header>
    
    <div class="chat-messages" ref="messagesRef">
      <div v-if="chatStore.messages.length === 0" class="welcome">
        <el-empty description="开始对话，让AI帮您规划旅行">
          <template #image>
            <div style="font-size: 60px">🤖</div>
          </template>
          <div class="suggestions">
            <el-button v-for="s in suggestions" :key="s" size="small" @click="sendSuggestion(s)">
              {{ s }}
            </el-button>
          </div>
        </el-empty>
      </div>
      
      <div v-for="msg in chatStore.messages" :key="msg.id" class="message" :class="msg.role">
        <div class="avatar">
          <el-icon v-if="msg.role === 'user'"><User /></el-icon>
          <span v-else>🤖</span>
        </div>
        <div class="content">
          <div class="bubble" v-html="formatMessage(msg.content)"></div>
          <div class="time">{{ formatTime(msg.timestamp) }}</div>
        </div>
      </div>
      
      <div v-if="chatStore.isStreaming" class="message assistant">
        <div class="avatar">🤖</div>
        <div class="content">
          <div class="bubble">
            <span class="typing"><span>.</span><span>.</span><span>.</span></span>
          </div>
        </div>
      </div>
    </div>
    
    <div class="chat-input">
      <el-input
        v-model="inputMessage"
        type="textarea"
        :rows="2"
        placeholder="输入您的问题..."
        :disabled="chatStore.isStreaming"
        @keydown.enter.exact.prevent="sendMessage"
        resize="none"
      />
      <el-button type="primary" :icon="Promotion" circle :loading="chatStore.isStreaming" @click="sendMessage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useTripsStore } from '@/stores/trips'
import { Promotion } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const tripsStore = useTripsStore()

const inputMessage = ref('')
const messagesRef = ref<HTMLElement>()
const tripId = route.params.tripId as string | undefined
const destination = (route.query.destination as string) || ''

const suggestions = [
  '帮我规划一个3天的行程',
  '那里天气怎么样？',
  '有什么推荐的景点？',
  '交通怎么安排比较好？'
]

onMounted(() => {
  chatStore.clearMessages()
  if (destination) {
    setTimeout(() => {
      chatStore.addMessage('assistant', `您好！我是您的AI旅行助手。我来帮您规划${destination}的旅程。您有多少天时间？有什么特别想去的地方或者偏好吗？`)
    }, 500)
  }
})

watch(() => chatStore.messages, () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}, { deep: true })

function sendSuggestion(text: string) {
  inputMessage.value = text
  sendMessage()
}

async function sendMessage() {
  if (!inputMessage.value.trim() || chatStore.isStreaming) return
  
  const message = inputMessage.value
  inputMessage.value = ''
  
  await chatStore.startStream(message, tripId ? Number(tripId) : null, destination)
}

function formatTime(timestamp: Date) {
  return new Date(timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function formatMessage(content: string) {
  return content.replace(/\n/g, '<br>')
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
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
.destination {
  color: #667eea;
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
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}
.message.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #667eea;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 20px;
}
.message.user .avatar {
  background: #67c23a;
}
.content {
  max-width: 70%;
}
.bubble {
  padding: 12px 16px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  line-height: 1.6;
  word-break: break-word;
}
.message.user .bubble {
  background: #667eea;
  color: white;
}
.time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
  text-align: right;
}
.message.user .time {
  text-align: left;
}
.typing span {
  animation: blink 1.4s infinite;
}
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink {
  0%, 80%, 100% { opacity: 0; }
  40% { opacity: 1; }
}
.chat-input {
  display: flex;
  gap: 10px;
  padding: 20px;
  background: white;
  border-top: 1px solid #eee;
  align-items: flex-end;
}
.chat-input :deep(.el-textarea__inner) {
  border-radius: 20px;
  padding: 12px 20px;
}
</style>
