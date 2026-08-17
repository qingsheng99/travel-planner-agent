import { defineStore } from 'pinia'
import { ref } from 'vue'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)

  function addMessage(role: 'user' | 'assistant', content: string) {
    messages.value.push({
      id: Date.now(),
      role,
      content,
      timestamp: new Date(),
    })
  }

  function startStream(message: string, tripId: number | null = null, destination: string | null = null): Promise<string> {
    isStreaming.value = true
    addMessage('user', message)

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
          const reader = response.body!.getReader()
          const decoder = new TextDecoder()
          let currentResponse = ''
          let assistantMessageId: number | null = null

          function read() {
            reader.read().then(({ done, value }) => {
              if (done) {
                isStreaming.value = false
                resolve(currentResponse)
                return
              }

              const chunk = decoder.decode(value)
              const lines = chunk.split('\n')

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.slice(6))

                    if (data.type === 'token') {
                      currentResponse += data.content
                      if (!assistantMessageId) {
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
                    }
                  } catch {
                    // ignore parse errors
                  }
                }
              }

              read()
            }).catch(reject)
          }

          read()
        })
        .catch(reject)
    })
  }

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