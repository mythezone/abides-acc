<template>
  <el-card header="仿真日志">
    <div style="max-height:120px; overflow-y: auto;">
      <ul>
        <li v-for="(line, idx) in logs" :key="idx">{{ line }}</li>
      </ul>
    </div>
  </el-card>
</template>

<script setup lang="ts">
const logs = [
  '14:33:00 [INFO] 仿真启动，市场开盘',
  '14:33:01 [AGENT-A] 买入 600001 1000股 @ 10.3',
  '14:33:03 [AGENT-B] 卖出 600002 500股 @ 8.8',
  '14:33:05 [USER] 买入 600001 200股 @ 10.4',
  '14:33:10 [INFO] 仿真暂停'
]
</script>