<template>
  <el-card header="KLineChart">
    <KLineChart :data="klineData" />
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import KLineChart from './KLineChart.vue'

const klineData = ref([
  { timestamp: 1714281600000, open: 10.2, close: 10.8, high: 11.0, low: 10.1, volume: 20000 },
  { timestamp: 1714285200000, open: 10.8, close: 11.1, high: 11.3, low: 10.7, volume: 25000 },
  { timestamp: 1714288800000, open: 11.1, close: 10.9, high: 11.2, low: 10.8, volume: 18000 },
  // ...更多数据
])
</script>