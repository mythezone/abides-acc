<template>
  <el-card class="realtime-line-card" header="Realtime Line Chart">
    <v-chart :option="option" :style="{ height: '400px', width: '90%', margin: '0 auto' }" />
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import VChart from 'vue-echarts'
import 'echarts'

const props = defineProps({
  data: Array // [{ time: '09:30', price: 10.25 }, ...]
})

const option = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: props.data.map(i => i.time)
  },
  yAxis: { type: 'value', scale: true },
  series: [{
    type: 'line',
    data: props.data.map(i => i.price),
    smooth: true,
    symbol: 'none',
    lineStyle: { width: 2 }
  }]
}))
</script>

<style scoped>
.realtime-line-card {
  padding: 0;
  margin: 0;
  border-radius: 10px;
  box-shadow: 0 2px 8px #0001;
}
</style>