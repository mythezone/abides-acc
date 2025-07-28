<template>
  <el-dialog
    v-if="mode === 'dialog'"
    title="Placing Order"
    :model-value="visible"
    width="420px"
    @close="handleClose"
  >
    <OrderForm
      v-model:form="form"
      :readonly-symbol="true"
      @submit="submit"
      @cancel="handleClose"
    />
  </el-dialog>

  <el-card v-else class="order-entry-panel" style="margin-bottom: 16px; box-shadow: 0 2px 8px #0001;">
  <OrderForm
    v-model:form="form"
    :readonly-symbol="true"
    @submit="submit"
  />
</el-card>
</template>

<script setup lang="ts">
import { ref, watch, defineProps, defineEmits } from 'vue'
import OrderForm from './OrderForm.vue'

const props = defineProps({
  visible: Boolean,          // 仅弹窗模式用
  marketType: { type: String, default: 'real' },
  symbol: String,
  mode: { type: String, default: 'dialog' } // 新增：'dialog' | 'panel'
})
const emits = defineEmits(['close', 'submit'])

const form = ref({
  symbol: props.symbol,
  direction: 'buy',
  orderType: 'market',
  price: 10.5,
  amount: 100
})

watch(() => props.symbol, (val) => {
  form.value.symbol = val
})

function submit(order) {
  emits('submit', { ...order, marketType: props.marketType })
  if (props.mode === 'dialog') emits('close')
}

function handleClose() {
  emits('close')
}
</script>