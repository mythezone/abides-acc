<template>
  <el-row align="middle" style="height: 60px; background: #2d3a4b; color: #fff;">
    <el-col :span="6" class="header-left" @click="$router.push('/')">
      <img class="lab-logo" :src="logoUrl" alt="logo" />
      <span style="font-weight: bold; font-size: 22px; padding-left: 16px;">SCALIBREX</span>
    </el-col>
    <el-col :span="12">
      <span>Full-scaled Market Simulator</span>
    </el-col>
    <el-col :span="6" style="text-align: right; padding-right: 16px;">
      <SimulationControl
        mode="inline"
        :progress="progress"
        :simTime="simTime"
        @order="handleOrder"
        @start="startSim"
        @pause="pauseSim"
        @step="stepSim"
        @stop="stopSim"
      />
      <PlaceOrderPanel
        v-if="orderPanelVisible"
        :visible="orderPanelVisible"
        mode="dialog"
        :symbol="'000001'"
        :marketType="'real'"
        @submit="onOrderSubmit"
        @close="() => orderPanelVisible = false"
        @cancel="() => orderPanelVisible = false"
      />
    </el-col>
  </el-row>
  
</template>

<script setup lang="ts">
import SimulationControl from './SimulationControl.vue'
import PlaceOrderPanel from './PlaceOrderPanel.vue'
import { ref } from 'vue'
import { ElNotification } from 'element-plus'

const orderPanelVisible = ref(false)
const logoUrl = '/img/logo.jpeg'

const progress = ref(63)
const simTime = ref('2024-07-28 14:33:00')
function startSim() {
  ElNotification({
  message: 'Start Simulation',
  type: 'success',
  position: 'top-right',
  duration: 1000,
  customClass: 'custom-center-notice'
})
}
function stopSim() {
  ElNotification({
    message: 'Stop Simulation',
    type: 'error',
    position: 'top-right',
    duration: 1000,
    customClass: 'custom-center-notice'
  })
}
function pauseSim() {
  ElNotification({
    message: 'Pause Simulation',
    type: 'warning',
    position: 'top-right',
    duration: 1000,
    customClass: 'custom-center-notice'
  })
}
function stepSim() {
  ElNotification({
    message: 'Step Simulation',
    type: 'info',
    position: 'top-right',
    duration: 1000,
    customClass: 'custom-center-notice'
  })
}
function handleOrder() {
  // 打开下单弹窗、或做其它下单逻辑
  orderPanelVisible.value = true
}

function onOrderSubmit(orderData) {
  // 这里可以发请求或者通知
  ElNotification({
    message: '订单已提交',
    type: 'success',
    duration: 1500
  })
  orderPanelVisible.value = false
}

</script>

<style scoped>

.header-left {
  display: flex;
  align-items: center;
  cursor: pointer;
  /* gap: 5px; */
  padding-left: 16px;
}
.lab-logo {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  object-fit: contain;
  /* background: #fff; */
  /* box-shadow: 0 1px 5px #e5eafc; */
}
</style>

<style>
/* 自定义通知样式，让它显示在页面上方中间 */
.custom-center-notice {
  left: 50% !important;
  right: auto !important;
  transform: translateX(-50%) !important;
}
</style>