/**
 * 应用入口文件
 * 负责初始化 Vue 应用、注册全局插件（Pinia、Router、Element Plus）及图标组件
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'leaflet/dist/leaflet.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

// 创建 Vue 应用实例
const app = createApp(App)
// 创建 Pinia 状态管理实例
const pinia = createPinia()

// 全局注册所有 Element Plus 图标组件，方便在模板中直接使用
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 注册全局插件
app.use(pinia)       // 状态管理
app.use(router)      // 路由
app.use(ElementPlus) // UI 组件库
// 挂载应用到 DOM 节点
app.mount('#app')