<template>
  <el-form :model="form" label-width="80px">
    <el-form-item label="Code">
      <el-input v-model="form.symbol" :readonly="readonlySymbol"/>
    </el-form-item>
    <el-form-item label="Direction" v-if="form.orderType!=='cancel'">
      <el-select v-model="form.direction">
        <el-option label="Buy" value="buy" />
        <el-option label="Sell" value="sell" />
      </el-select>
    </el-form-item>
    <el-form-item label="Type">
      <el-select v-model="form.orderType">
        <el-option label="Market Order" value="market" />
        <el-option label="Limit Order" value="limit" />
        <el-option label="Modify Order" value="modify" />
        <el-option label="Cancel Order" value="cancel" />
      </el-select>
    </el-form-item>
    <el-form-item label="ID" v-if="form.orderType==='modify'||form.orderType==='cancel'">
      <el-input v-model="form.orderId"/>
    </el-form-item>
    <el-form-item label="Price" v-if="form.orderType==='limit'||form.orderType==='modify'">
      <el-input-number v-model="form.price" :min="0" :step="0.01"/>
    </el-form-item>
    <el-form-item label="Quantity" v-if="form.orderType!=='cancel'">
      <el-input-number v-model="form.amount" :min="1" />
    </el-form-item>
    <el-form-item>
      <el-button @click="$emit('cancel')" v-if="showCancel">Cancel</el-button>
      <el-button type="primary" @click="onSubmit">Submit</el-button>
    </el-form-item>
  </el-form>
</template>
<script setup lang="ts">
const props = defineProps({
  form: Object,
  readonlySymbol: Boolean,
  showCancel: { type: Boolean, default: false }
})
const emits = defineEmits(['submit', 'cancel'])
function onSubmit() {
  emits('submit', props.form)
}
</script>