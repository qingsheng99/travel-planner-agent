<template>
  <div class="app-layout">
    <el-header class="header">
      <div class="header-left">
        <el-button v-if="showBack" text @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <span class="logo" @click="$router.push('/')">✈️ AI旅行规划助手</span>
      </div>
      <div class="nav">
        <el-button :type="isActive('/') ? 'primary' : 'default'" text @click="$router.push('/')">首页</el-button>
        <el-button :type="isActive('/trips') ? 'primary' : 'default'" text @click="$router.push('/trips')">我的行程</el-button>
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><User /></el-icon>
            {{ authStore.user?.username }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <div class="layout-body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

defineProps<{
  showBack?: boolean
}>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

function isActive(path: string): boolean {
  return route.path === path
}

function handleCommand(command: string) {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  background: #f5f7fa;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 0 40px;
  height: 64px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  font-size: 20px;
  font-weight: bold;
  color: #667eea;
  cursor: pointer;
  user-select: none;
}

.nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #666;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.user-info:hover {
  background: #f0f0f0;
}

.layout-body {
  min-height: calc(100vh - 64px);
}
</style>