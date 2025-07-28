<template>
  <el-card class="depth-card" header="Market Depth">
    <div class="depth-tables-row">
      <el-row style="width:100%;">
        <el-col :span="12">
          <el-table :data="bids" size="small" :show-header="true" class="bids-table" max-height="140" style="width:100%; height: 200px;">
            <el-table-column prop="price" label="BP" align="center" width="60"
              label-class-name="bid-header"
            >
              <template #default="{ row }">
                <span class="bid-color">{{ row.price }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="BV" align="center" width="60"
              label-class-name="bid-header"
            >
              <template #default="{ row }">
                <span class="bid-color">{{ row.amount }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
        <el-col :span="12">
          <el-table :data="asks" size="small" :show-header="true" class="asks-table" max-height="140" style="width:100%; margin-bottom: 0;">
            <el-table-column prop="price" label="AP" align="center" width="60"
              label-class-name="ask-header"
            >
              <template #default="{ row }">
                <span class="ask-color">{{ row.price }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="AV" align="center" width="60"
              label-class-name="ask-header"
            >
              <template #default="{ row }">
                <span class="ask-color">{{ row.amount }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
      </el-row>
    </div>
  </el-card>
  
</template>

<script setup lang="ts">

const props = defineProps<{
  bids: Array<any>,
  asks: Array<any>
}>()

</script>

<style scoped>
/* 盘口卡片紧凑样式 */
.depth-card {
  margin: 0;
  padding: 0;
  border-radius: 10px;
  box-shadow: 0 2px 8px #0001;
}
::v-deep(.depth-card .el-card__header) {
  padding: 4px 12px !important;
  min-height: 24px !important;
  font-size: 14px;
  background: #f9f9fa;
  border-bottom: 1px solid #ececec;
  line-height: 18px;
}
::v-deep(.depth-card .el-card__body) {
  padding: 0 !important;
  margin: 0 !important;
}
.depth-tables-row {
  width: 100%;
  min-width: 128px;
  display: flex;
  justify-content: center;
  margin-bottom: 0 !important;
}
.bids-table, .asks-table, .trade-tick-table {
  font-family: 'Menlo', 'Consolas', monospace;
  margin-bottom: 0 !important;
}
.bid-header {
  color: #24b36b !important;
  font-weight: 600 !important;
}
.ask-header {
  color: #e94f4f !important;
  font-weight: 600 !important;
}
.bids-table .bid-color, .trade-tick-table .bid-color {
  color: #24b36b;
  font-weight: 500;
}
.asks-table .ask-color, .trade-tick-table .ask-color {
  color: #e94f4f;
  font-weight: 500;
}
.el-table__header th,
.el-table__row td {
  padding: 1px 3px !important;
  text-align: center !important;
  font-size: 13px !important;
}

::v-deep(.el-table--small .el-table__cell) {
  min-width: 0 !important;
  padding: 1px 2px !important;
  text-align: center !important;
  vertical-align: middle !important;
  font-size: 8px !important;
}


</style>