<template>
  <el-menu class="el-menu-vertical-demo" style="height:100%;" :default-active="activeSymbol">
    <el-menu-item
      v-for="stock in stocks"
      :key="stock"
      :index="stock"
      @click="handleSelect(stock)"
    >
      <span>{{ stock }}</span>
    </el-menu-item>
  </el-menu>
</template>

<script setup lang="ts">
import { ref, defineEmits } from 'vue'
const stocks = ['000001', '000002', '000063', '000333', '002230', '002415'] // 深证示例
const activeSymbol = ref(stocks[0])
const emits = defineEmits(['symbol-change'])

function handleSelect(symbol) {
  activeSymbol.value = symbol
  emits('symbol-change', symbol)
}
</script>

<style scoped>
::v-deep(.el-menu-item) {
  height: 30px !important;
  line-height: 30px !important;
  padding: 0 12px !important;
  font-size: 14px;
  border-radius: 6px !important;
  margin-bottom: 0 !important;
}
::v-deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, #47b7ff 0%, #4f8aff 100%);
  color: #fff !important;
}
::v-deep(.el-menu-item:hover) {
  background: #e6f2ff !important;
  color: #409eff;
}
</style>