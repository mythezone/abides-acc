<template>
  <el-dialog
    :title="marketType === 'sim' ? '仿真市场下单' : '历史市场下单'"
    :model-value="visible"
    width="400px"
    @close="handleClose"
    @update:model-value="handleUpdate"
  >
    <el-form :model="order" label-width="60px">
      <!-- ...表单内容不变... -->
    </el-form>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" @click="handleSubmit">下单</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, defineProps, defineEmits } from 'vue'
const props = defineProps<{
  visible: boolean,
  marketType: 'real' | 'sim'
}>()
const emits = defineEmits(['update:visible', 'submit'])

const order = ref({
  direction: 'buy',
  symbol: '600001',
  price: 10.5,
  amount: 100
})

watch(() => props.visible, (val) => {
  if (val) resetForm()
})

function handleSubmit() {
  emits('submit', { ...order.value })
  close()
}
function close() {
  emits('update:visible', false)
}
function handleClose() {
  close()
}
function handleUpdate(val: boolean) {
  emits('update:visible', val)
}
function resetForm() {
  order.value = {
    direction: 'buy',
    symbol: '600001',
    price: 10.5,
    amount: 100
  }
}
</script>