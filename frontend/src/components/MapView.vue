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
import { ref, onMounted, watch, nextTick } from 'vue'
import L from 'leaflet'
import type { LatLngExpression } from 'leaflet'

const props = defineProps<{
  center?: [number, number]
  zoom?: number
  markers?: Array<{ name: string; lat: number; lng: number; description?: string }>
}>()

const mapContainer = ref<HTMLElement>()
const loading = ref(true)

let map: L.Map | null = null
let markerLayer: L.LayerGroup | null = null

function initMap() {
  if (!mapContainer.value) return

  const defaultCenter: LatLngExpression = props.center || [39.9042, 116.4074]
  const defaultZoom = props.zoom || 13

  map = L.map(mapContainer.value, {
    center: defaultCenter,
    zoom: defaultZoom,
    zoomControl: true,
  })

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map)

  markerLayer = L.layerGroup().addTo(map)

  loading.value = false
}

function updateMarkers() {
  if (!markerLayer || !props.markers) return

  markerLayer.clearLayers()

  props.markers.forEach((m) => {
    const marker = L.marker([m.lat, m.lng])
    const popupContent = m.description
      ? `<strong>${m.name}</strong><br/>${m.description}`
      : `<strong>${m.name}</strong>`
    marker.bindPopup(popupContent)
    markerLayer!.addLayer(marker)
  })
}

function panTo(center: [number, number], zoom?: number) {
  if (!map) return
  map.setView(center, zoom || map.getZoom(), { animate: true })
}

onMounted(() => {
  nextTick(() => {
    initMap()
    updateMarkers()
  })
})

watch(() => props.markers, () => {
  updateMarkers()
}, { deep: true })

watch(() => props.center, (newCenter) => {
  if (newCenter && map) {
    panTo(newCenter)
  }
})

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