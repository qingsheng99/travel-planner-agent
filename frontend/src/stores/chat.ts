/**
 * AI 对话聊天状态管理模块
 * 管理聊天消息列表、SSE 流式对话请求，
 * 支持实时逐 token 渲染 AI 回复内容。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

/** 单条聊天消息的接口定义 */
interface ChatMessage {
  id: number
  role: 'user' | 'assistant' // 消息发送者：用户或 AI 助手
  content: string
  timestamp: Date
}

/** 聊天 Store：管理对话消息与流式请求 */
export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([]) // 聊天消息列表
  const isStreaming = ref(false) // 是否正在流式接收 AI 回复

  /**
   * 添加一条消息到对话列表
   * @param role - 消息角色（用户/助手）
   * @param content - 消息内容
   */
  function addMessage(role: 'user' | 'assistant', content: string) {
    messages.value.push({
      id: Date.now(),
      role,
      content,
      timestamp: new Date(),
    })
  }

  /**
   * 发起流式对话请求（SSE）
   * @param message - 用户输入的消息
   * @param tripId - 关联的行程 ID（可选）
   * @param destination - 关联的目的地（可选）
   * @returns 完整回复内容的 Promise
   */
  function startStream(message: string, tripId: number | null = null, destination: string | null = null): Promise<string> {
    isStreaming.value = true
    addMessage('user', message) // 先将用户消息加入列表

    const token = localStorage.getItem('token')
    const url = new URL('/api/v1/chat/stream', window.location.origin)

    return new Promise<string>((resolve, reject) => {
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message, trip_id: tripId, destination }),
      })
        .then((response) => {
          if (!response.ok || !response.body) {
            throw new Error(`聊天请求失败（${response.status}）`)
          }

          const reader = response.body.getReader() // 获取流读取器
          const decoder = new TextDecoder()
          let currentResponse = '' // 累积的 AI 回复内容
          let assistantMessageId: number | null = null // AI 回复消息 ID（首次 token 时创建）
          let pending = ''

          function handleLine(line: string) {
            if (!line.startsWith('data: ')) return

            try {
              const data = JSON.parse(line.slice(6))

              if (data.type === 'token') {
                currentResponse += data.content
                if (assistantMessageId === null) {
                  assistantMessageId = Date.now()
                  messages.value.push({
                    id: assistantMessageId,
                    role: 'assistant',
                    content: currentResponse,
                    timestamp: new Date(),
                  })
                } else {
                  const msg = messages.value.find((m) => m.id === assistantMessageId)
                  if (msg) msg.content = currentResponse
                }
              } else if (data.type === 'error') {
                throw new Error(data.content || '聊天服务处理失败')
              }
            } catch (error) {
              if (error instanceof SyntaxError) return
              throw error
            }
          }

          /** 递归读取流中的每个数据块 */
          function read(): void {
            reader.read().then(({ done, value }) => {
              if (done) {
                pending += decoder.decode()
                for (const line of pending.split('\n')) handleLine(line.trim())
                isStreaming.value = false
                resolve(currentResponse) // 流结束，返回完整内容
                return
              }

              pending += decoder.decode(value, { stream: true })
              const lines = pending.split('\n')
              pending = lines.pop() || ''

              try {
                for (const line of lines) handleLine(line.trim())
              } catch (error) {
                reader.cancel()
                throw error
              }

              read()
            }).catch((error) => {
              isStreaming.value = false
              reject(error)
            })
          }

          read()
        })
        .catch((error) => {
          isStreaming.value = false
          reject(error)
        })
    })
  }

  /** 清空所有聊天消息 */
  function clearMessages() {
    messages.value = []
  }

  return {
    messages,
    isStreaming,
    addMessage,
    startStream,
    clearMessages,
  }
})
