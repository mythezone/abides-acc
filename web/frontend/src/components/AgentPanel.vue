<template>
  <div v-if="agent">
    <el-row :gutter="16">
      <el-col :span="24" style="margin-bottom: 12px;">
        <el-card class="agent-block" header="Positions" style="overflow-x:auto;">
          <el-table class="agent-table" :data="agent.positions" size="small" border stripe empty-text="No positions" max-height="220" height="auto">
            <el-table-column prop="symbol" label="Symbol"/>
            <el-table-column prop="vol" label="Volume"/>
            <el-table-column prop="cost" label="Avg Price"/>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="24" style="margin-bottom: 12px;">
        <el-card class="agent-block" header="Orders" style="overflow-x:auto;">
          <el-table class="agent-table" :data="agent.orders" size="small" border stripe empty-text="No orders" max-height="220" height="auto">
            <el-table-column prop="id" label="Order ID"/>
            <el-table-column prop="symbol" label="Symbol"/>
            <el-table-column prop="price" label="Price"/>
            <el-table-column prop="status" label="Status"/>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="24" style="margin-bottom: 12px;">
        <el-card class="agent-block" header="Strategy Parameters">
          <ul style="padding-left:0;list-style:none;">
            <li><strong>Type：</strong>{{ agent.strategy.type }}</li>
            <li><strong>Parameter A：</strong>{{ agent.strategy.paramA }}</li>
            <li><strong>Parameter B：</strong>{{ agent.strategy.paramB }}</li>
          </ul>
        </el-card>
      </el-col>
      <el-col :span="24">
        <el-card class="agent-block" header="P&L / Cash">
          <ul style="padding-left:0;list-style:none;">
            <li><strong>P&L：</strong>
              <span :style="{color: agent.pnl >= 0 ? '#28c445' : '#fa3c3c'}">{{ agent.pnl }}</span>
            </li>
            <li><strong>Cash：</strong> {{ agent.cash }}</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
  <div v-else style="text-align:center;color:#aaa;padding:60px 0;">
    No agent data available.
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ agent: any }>()
</script>

<style scoped>
.agent-block {
  border-radius: 12px;
  box-shadow: 0 2px 8px 0 rgba(36,37,38,0.06);
  margin-bottom: 12px;
}
/* 缩小卡片header高度 */
::v-deep(.el-card__header) {
  padding: 6px 16px !important;
  min-height: 28px !important;
  font-size: 15px;
  background: #f9f9fa;
  border-bottom: 1px solid #ececec;
}

/* 表格紧凑美化 */
.agent-table .el-table__header th {
  height: 28px !important;
  padding: 4px 8px !important;
  background: #f6f7fb !important;
  font-size: 13px;
  color: #4a4a4a;
  border-bottom: 1px solid #ececec;
}
.agent-table .el-table__cell {
  height: 28px !important;
  padding: 3px 8px !important;
  font-size: 13px;
}
.agent-table .el-table__row:hover td {
  background: #f4f9fd !important;
}
.agent-table {
  border-radius: 8px;
  overflow: hidden;
}
</style>