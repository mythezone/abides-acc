<template>
  <el-card header="Trade History" class="trade-tick-card">
    <el-table :data="trades" :show-header="true" class="trade-tick-table" style="width:95%; height:200px;">
      <el-table-column   label="T" prop="time"  align="center" />
      <el-table-column   label="P" prop="price"  align="center">
        <template #default="{ row }">
          <span :class="row.direction === 'buy' ? 'bid-color' : 'ask-color'">{{ row.price }}</span>
        </template>
      </el-table-column>
      <el-table-column   label="Q" prop="amount"  align="center" />
      <el-table-column   label="D" prop="direction"  align="center">
        <template #default="{ row }">
          <span :style="{color: row.direction === 'buy' ? '#24b36b' : '#e94f4f'}">
            {{ row.direction === 'buy' ? 'B' : 'S' }}
          </span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
const props = defineProps<{ trades: Array<any> }>()
</script>

<style scoped>
.trade-tick-table {
  line-height: 1em;

  font-size: 8px;
  white-space: nowrap;
}

::v-deep(.trade-tick-table .el-table__cell) {
  min-width: 0 !important;
  padding: 1px 2px !important;
  text-align: center !important;
  vertical-align: middle !important;
  font-size: 8px !important;
}



/* 高亮买卖颜色 */
.trade-tick-table .bid-color { color: #24b36b; font-weight: 500; }
.trade-tick-table .ask-color { color: #e94f4f; font-weight: 500; }

</style>
