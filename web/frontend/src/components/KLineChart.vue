<template>
  <div class="kline-chart-container">
    <div ref="mainChart" class="kline-main" />
    <div ref="volumeChart" class="kline-volume" />
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { init } from 'klinecharts'
const props = defineProps<{ data: Array<any> }>()
const mainChart = ref(null)
const volumeChart = ref(null)
let chart = null
onMounted(() => {
  if (mainChart.value) {
    chart = init(mainChart.value)
    chart.createIndicator('VOL', false, { id: 'c1' }) // klinecharts示例，自动加成交量
    chart.applyNewData(props.data)
  }
})
watch(() => props.data, (newData) => {
  if (chart) chart.applyNewData(newData)
})
</script>
<style scoped>
.kline-chart-container { width: 100%; }
.kline-main { height: 340px; }
.kline-volume { height: 24px; }
</style>