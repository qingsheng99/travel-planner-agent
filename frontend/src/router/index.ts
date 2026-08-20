/**
 * 路由配置模块
 * 定义应用所有页面路由及导航守卫，控制页面访问权限
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

/**
 * 路由表定义
 * - guest: 仅未登录用户可以访问（如登录/注册页）
 * - requiresAuth: 需要登录才能访问
 */
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'), // 懒加载登录页
    meta: { guest: true }, // 仅游客可访问
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'), // 懒加载注册页
    meta: { guest: true }, // 仅游客可访问
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'), // 懒加载首页
    meta: { requiresAuth: true }, // 需要登录
  },
  {
    path: '/trips',
    name: 'Trips',
    component: () => import('@/views/Trips.vue'), // 懒加载行程列表页
    meta: { requiresAuth: true }, // 需要登录
  },
  {
    path: '/chat/:tripId?',
    name: 'Chat',
    component: () => import('@/views/Chat.vue'), // 懒加载聊天页（可选行程 ID）
    meta: { requiresAuth: true }, // 需要登录
  },
  {
    path: '/itinerary/:tripId',
    name: 'Itinerary',
    component: () => import('@/views/Itinerary.vue'), // 懒加载行程详情页
    meta: { requiresAuth: true }, // 需要登录
  },
  {
    path: '/preferences',
    name: 'Preferences',
    component: () => import('@/views/Preferences.vue'), // 懒加载偏好设置页
    meta: { requiresAuth: true }, // 需要登录
  },
]

// 创建路由实例，使用 HTML5 History 模式
const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * 全局前置导航守卫
 * 根据路由 meta 信息和登录状态控制页面跳转：
 * - 未登录访问需认证页面 → 跳转 /login
 * - 已登录访问游客页面 → 跳转 /
 * - 其他情况正常放行
 */
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore() // 获取认证状态

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // 需要登录但未登录，重定向到登录页
    next('/login')
  } else if (to.meta.guest && authStore.isAuthenticated) {
    // 已登录用户访问游客页面（如登录页），重定向到首页
    next('/')
  } else {
    // 正常放行
    next()
  }
})

export default router