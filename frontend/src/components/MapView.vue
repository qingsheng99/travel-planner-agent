<template>
  <div class="map-wrapper">
    <div ref="mapContainer" class="map-container"></div>
    <div v-if="loading" class="map-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载地图...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 地图视图组件
 * 基于 Leaflet 封装，使用高德地图瓦片，
 * 支持标记点展示、点击弹窗、地图中心平移等功能。
 */
import { ref, onMounted, watch, nextTick } from 'vue'
import L from 'leaflet'
import type { LatLngExpression } from 'leaflet'

/** 组件属性：地图中心、缩放级别、标记点列表 */
const props = defineProps<{
  center?: [number, number] // 地图中心经纬度，默认北京
  zoom?: number // 缩放级别，默认 13
  markers?: Array<{ name: string; lat: number; lng: number; description?: string }> // 标记点数组
}>()

const mapContainer = ref<HTMLElement>() // 地图容器 DOM 引用
const loading = ref(true) // 地图加载状态

let map: L.Map | null = null // Leaflet 地图实例
let markerLayer: L.LayerGroup | null = null // 标记点图层组

/** 初始化地图 */
function initMap() {
  if (!mapContainer.value) return

  const defaultCenter: LatLngExpression = props.center || [39.9042, 116.4074] // 默认北京坐标
  const defaultZoom = props.zoom || 13

  // 创建 Leaflet 地图实例
  map = L.map(mapContainer.value, {
    center: defaultCenter,
    zoom: defaultZoom,
    zoomControl: true,
  })

  // 加载高德地图瓦片
  L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
    subdomains: ['1', '2', '3', '4'],
    attribution: '&copy; 高德地图',
    maxZoom: 18,
  }).addTo(map)

  markerLayer = L.layerGroup().addTo(map) // 初始化标记点图层

  loading.value = false
}

/** 更新地图上的标记点（清除旧标记，添加新标记） */
function updateMarkers() {
  if (!markerLayer || !props.markers) return

  markerLayer.clearLayers() // 清空现有标记

  props.markers.forEach((m) => {
    const marker = L.marker([m.lat, m.lng]) // 创建标记
    // 构建弹窗内容（有点击描述时显示描述）
    const popupContent = m.description
      ? `<strong>${m.name}</strong><br/>${m.description}`
      : `<strong>${m.name}</strong>`
    marker.bindPopup(popupContent) // 绑定弹窗
    markerLayer!.addLayer(marker) // 添加到图层
  })
}

/**
 * 将地图平移到指定中心点
 * @param center - 目标经纬度
 * @param zoom - 可选的目标缩放级别
 */
function panTo(center: [number, number], zoom?: number) {
  if (!map) return
  map.setView(center, zoom || map.getZoom(), { animate: true })
}

// 组件挂载后初始化地图并渲染标记
onMounted(() => {
  nextTick(() => {
    initMap()
    updateMarkers()
  })
})

// 监听标记点变化，实时更新
watch(() => props.markers, () => {
  updateMarkers()
}, { deep: true })

// 监听中心点变化，自动平移地图
watch(() => props.center, (newCenter) => {
  if (newCenter && map) {
    panTo(newCenter)
  }
})

// 向父组件暴露 panTo 方法
defineExpose({ panTo })
</script>

<style scoped>
.map-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 300px;
  border-radius: 8px;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
  min-height: 300px;
}

.map-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.9);
  padding: 12px 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 1000;
}
</style>