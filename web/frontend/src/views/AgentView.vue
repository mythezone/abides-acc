<template>
  <div class="agent-view-wrapper">
    <el-row style="height: 100%;">
      <el-col :span="4" class="agent-sidebar-col">
        <AgentSideBar
          :agents="agentList"
          :activeAgentId="activeAgentId"
          @agent-change="onAgentChange"
        />
      </el-col>
      <el-col :span="20" class="agent-main-col">
        <el-card v-if="activeAgent" class="agent-main-card" :header="`Agent Panel - ${activeAgent.name}`">
          <AgentPanel :agent="activeAgent" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import AgentSideBar from '../components/AgentSideBar.vue'
import AgentPanel from '../components/AgentPanel.vue'


// 模拟数据：10个Agent
const agentList = [
  { id: 'A1', name: 'Policy Alpha' },
  { id: 'A2', name: 'Policy Beta' },
  { id: 'A3', name: 'Policy Gamma' },
  { id: 'A4', name: 'Policy Delta' },
  { id: 'A5', name: 'Policy Epsilon' },
  { id: 'A6', name: 'Policy Zeta' },
  { id: 'A7', name: 'Policy Eta' },
  { id: 'A8', name: 'Policy Theta' },
  { id: 'A9', name: 'Policy Iota' },
  { id: 'A10', name: 'Policy Kappa' }
]

// 10个Agent的详细模拟数据, All in English

const agentDataMap = {
  'A1': { strategy: { type: 'Moving Average Breakout', paramA: 10, paramB: 20 }, pnl: 1000, cash: 100000, positions: [{ symbol: '000001', vol: 200, cost: 10 }], orders: [{ id: 'O1', symbol: '000001', price: 10.2, status: 'Deal' }] },
  'A2': { strategy: { type: 'Momentum', paramA: 15, paramB: 30 }, pnl: 1500, cash: 98000, positions: [{ symbol: '000002', vol: 300, cost: 20 }], orders: [{ id: 'O2', symbol: '000002', price: 20.3, status: 'Pending' }] },
  'A3': { strategy: { type: 'High-Frequency Market Making', paramA: 5, paramB: 12 }, pnl: -800, cash: 102000, positions: [{ symbol: '000063', vol: 120, cost: 40 }], orders: [{ id: 'O3', symbol: '000063', price: 40.8, status: 'Deal' }] },
  'A4': { strategy: { type: 'Multi-Factor', paramA: 9, paramB: 22 }, pnl: 2600, cash: 95000, positions: [{ symbol: '000333', vol: 50, cost: 50 }], orders: [{ id: 'O4', symbol: '000333', price: 50.5, status: 'Deal' }] },
  'A5': { strategy: { type: 'Trend Following', paramA: 20, paramB: 50 }, pnl: 1200, cash: 98000, positions: [{ symbol: '002230', vol: 110, cost: 18 }], orders: [{ id: 'O5', symbol: '002230', price: 18.2, status: 'Pending' }] },
  'A6': { strategy: { type: 'Arbitrage', paramA: 2, paramB: 8 }, pnl: 2100, cash: 105000, positions: [{ symbol: '002415', vol: 30, cost: 30 }], orders: [{ id: 'O6', symbol: '002415', price: 30.7, status: 'Deal' }] },
  'A7': { strategy: { type: 'Reversal', paramA: 7, paramB: 19 }, pnl: -600, cash: 97000, positions: [{ symbol: '000725', vol: 80, cost: 15 }], orders: [{ id: 'O7', symbol: '000725', price: 15.2, status: 'Pending' }] },
  'A8': { strategy: { type: 'Grid', paramA: 11, paramB: 24 }, pnl: 800, cash: 100000, positions: [{ symbol: '000651', vol: 60, cost: 60 }], orders: [{ id: 'O8', symbol: '000651', price: 60.4, status: 'Deal' }] },
  'A9': { strategy: { type: 'Machine Learning', paramA: 13, paramB: 27 }, pnl: 3300, cash: 92000, positions: [{ symbol: '002142', vol: 70, cost: 26 }], orders: [{ id: 'O9', symbol: '002142', price: 26.1, status: 'Deal' }] },
  'A10': { strategy: { type: 'Swing', paramA: 17, paramB: 34 }, pnl: 500, cash: 99000, positions: [{ symbol: '000776', vol: 90, cost: 12 }], orders: [{ id: 'O10', symbol: '000776', price: 12.8, status: 'Pending' }] },
}

const activeAgentId = ref(agentList[0].id)
const activeAgent = computed(() => {
  const base = agentDataMap[activeAgentId.value]
  if (!base) return null
  // agent对象增加 id、name 字段便于AgentPanel展示
  return { ...base, id: activeAgentId.value, name: agentList.find(a => a.id === activeAgentId.value)?.name }
})

function onAgentChange(id: string) {
  activeAgentId.value = id
}
</script>

<style scoped>
.agent-view-wrapper {
  min-height: calc(100vh - 80px); /* 根据导航+菜单实际高度调整 */
  background: #f5f7fa;
  padding: 72px 0 0 0;
}

/* .agent-sidebar-col {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 2px 16px 0 rgba(36,37,38,0.06);
  min-height: 600px;
  margin-top: 8px;
  margin-left: 10px;
  padding: 18px 0;
  transition: box-shadow 0.3s;
} */

.agent-main-col {
  padding-left: 28px;
  padding-right: 24px;
  min-height: 600px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.agent-main-card {
  border-radius: 16px;
  box-shadow: 0 2px 16px 0 rgba(36,37,38,0.08);
  background: #fff;
  min-height: 480px;
  margin-top: 8px;
  /* 你可以根据实际内容调整min-height */
}

/* 悬浮高亮AgentSideBar菜单项 */
.el-menu-vertical-demo .el-menu-item {
  border-radius: 8px !important;
  margin: 4px 12px;
  transition: background 0.2s, color 0.2s;
}
.el-menu-vertical-demo .el-menu-item.is-active {
  background: linear-gradient(90deg, #47b7ff 0%, #4f8aff 100%);
  color: #fff !important;
}
.el-menu-vertical-demo .el-menu-item:hover {
  background: #e6f2ff;
  color: #409eff;
}
</style>