<template>
  <el-card header="Simulation Progress Monitor">
    <div>Progress：</div>
    <el-progress :percentage="progress" style="width: 300px;" />
    <div>Simulation Time：{{ now }}</div>
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const progress = ref(63)
const now = ref('2024-07-28 14:33:00')
</script>