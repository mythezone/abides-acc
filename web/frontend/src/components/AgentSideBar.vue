<template>
  <el-menu
    :default-active="activeAgentId"
    class="el-menu-vertical-demo"
    style="height: 100%;"
  >
    <el-menu-item
      v-for="agent in agents"
      :key="agent.id"
      :index="agent.id"
      @click="selectAgent(agent.id)"
    >
      {{ agent.name }}
    </el-menu-item>
  </el-menu>
</template>

<script setup lang="ts">
const props = defineProps<{
  agents: Array<{ id: string, name: string }>
  activeAgentId: string
}>()
const emits = defineEmits(['agent-change'])
function selectAgent(id: string) {
  emits('agent-change', id)
}
</script>

<style scoped>
::v-deep(.el-menu-item) {
  height: 32px !important;
  line-height: 32px !important;
  padding: 0 14px !important;
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