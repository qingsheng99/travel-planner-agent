<template>
  <!-- 使用 Element Plus 的全局配置，设置语言为中文 -->
  <el-config-provider :locale="zhCn">
    <!-- 路由出口，根据当前 URL 渲染对应页面组件 -->
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
/**
 * 根组件
 * 配置 Element Plus 中文语言包，包裹全局路由视图
 */
import zhCn from 'element-plus/dist/locale/zh-cn.mjs' // 导入 Element Plus 中文语言包
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
</style>