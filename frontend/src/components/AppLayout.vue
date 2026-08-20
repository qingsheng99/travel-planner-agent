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
              <el-dropdown-item command="preferences">
                <el-icon><Setting /></el-icon>
                偏好设置
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
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
/**
 * 应用全局布局组件
 * 提供顶部导航栏（含返回按钮、Logo、导航菜单、用户下拉菜单）
 * 和主体内容插槽。
 */
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

/** 是否显示返回按钮 */
defineProps<{
  showBack?: boolean
}>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

/**
 * 判断当前路由是否与指定路径匹配，用于高亮导航项
 * @param path - 目标路径
 * @returns 是否匹配
 */
function isActive(path: string): boolean {
  return route.path === path
}

/**
 * 处理下拉菜单命令
 * @param command - 命令标识
 */
function handleCommand(command: string) {
  if (command === 'logout') {
    authStore.logout() // 清除登录态
    router.push('/login') // 跳转到登录页
  } else if (command === 'preferences') {
    router.push('/preferences') // 跳转到偏好设置页
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