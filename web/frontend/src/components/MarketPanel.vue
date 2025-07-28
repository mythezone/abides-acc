<template>
  <el-card :header="marketType === 'real' ? 'Real Market' : 'Simulated Market'" style="width: 100%; min-width: 600px; font-size: 15px; font-weight: 500;height: 450px;">
    <el-row :gutter="16" align="top">
      <!-- K线图在左 -->
      <el-col :span="16">
        <!-- 关键：K线图设置高度和宽度 -->
        <!-- <KLineChart :data="klineData" style="height: 340px; width: 100%;" /> -->
        <el-tabs v-model="activeTab">
          <el-tab-pane label="KLineChart" name="kline">
            <KLineChart :data="klineData" />
          </el-tab-pane>
          <el-tab-pane label="Realtime Line Chart" name="realtime">
            <RealtimeLineChart :data="realtimeData" />
          </el-tab-pane>
        </el-tabs>
      </el-col>
      <!-- 盘口+下单按钮在右 -->
      <el-col :span="8">
        <div style="display: flex; flex-direction: column; height: 170px; justify-content: flex-start;">
          <MarketDepth :bids="bids" :asks="asks" />
        </div>
        <div style="display: flex; flex-direction: column; height: 170px; justify-content: flex-start;">
          <TradeHistory :trades="trades" />
        </div>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup lang="ts">
import { defineProps, defineEmits } from 'vue'
import KLineChart from './KLineChart.vue'
import MarketDepth from './MarketDepth.vue'
import TradeHistory from './TradeHistory.vue'
import RealtimeLineChart from './RealtimeLineChart.vue'
import { ref } from 'vue'

const activeTab = ref('kline')
const props = defineProps<{
  klineData: Array<any>,
  bids: Array<any>,
  asks: Array<any>,
  marketType: 'real' | 'sim'
}>()
const emits = defineEmits(['order'])

function placeOrder() {
  emits('order', { marketType: props.marketType, symbol: props.klineData[0]?.symbol || '600001' })
}

// 示例实时数据
const realtimeData = [          
  { time: '09:30', price: 10.2 },
  { time: '09:31', price: 10.22 },
  { time: '09:32', price: 10.25 },
  { time: '09:33', price: 10.23 },
  { time: '09:34', price: 10.24 },
  { time: '09:35', price: 10.26 },
  { time: '09:36', price: 10.28 },
  { time: '09:37', price: 10.27 },
  { time: '09:38', price: 10.29 },
  { time: '09:39', price: 10.3 },
  { time: '09:40', price: 10.31 }
]

// 模拟逐笔成交数据
const trades = [
  { time: '14:25:31', price: 10.23, amount: 300, direction: 'buy' },
  { time: '14:25:29', price: 10.22, amount: 500, direction: 'sell' },
  { time: '14:25:28', price: 10.24, amount: 120, direction: 'buy' },
  { time: '14:25:25', price: 10.21, amount: 450, direction: 'sell' },
  { time: '14:25:23', price: 10.25, amount: 200, direction: 'buy' },
  { time: '14:25:20', price: 10.21, amount: 600, direction: 'sell' },
  { time: '14:25:19', price: 10.24, amount: 80,  direction: 'buy' }
]
</script>

<style scoped>
::v-deep(.el-card__header) {
  font-size: 12px;
  padding: 2px 18px !important;
  min-height: 20px !important;
  margin: 0 !important;
}
::v-deep(.el-card__body) {
  padding: 8px !important;
  margin: 4px !important;
}
</style>