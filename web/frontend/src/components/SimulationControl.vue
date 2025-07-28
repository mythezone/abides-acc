<template>
  <!-- 下拉菜单模式 -->
  <el-dropdown v-if="mode === 'dropdown'">
    <el-button>
      Simulation Control
      <el-icon><ArrowDown /></el-icon>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item @click="emitStart">
          <el-icon style="vertical-align:middle;"><VideoPlay /></el-icon>
          <span style="margin-left: 4px;">Start</span>
        </el-dropdown-item>
        <el-dropdown-item @click="emitPause">
          <el-icon style="vertical-align:middle;"><VideoPause /></el-icon>
          <span style="margin-left: 4px;">Pause</span>
        </el-dropdown-item>
        <el-dropdown-item @click="emitStep">
          <el-icon style="vertical-align:middle;"><RefreshRight /></el-icon>
          <span style="margin-left: 4px;">Step</span>
        </el-dropdown-item>
        <el-dropdown-item @click="emitStop">
          <el-icon style="vertical-align:middle;"><CircleClose /></el-icon>
          <span style="margin-left: 4px;">Stop</span>
        </el-dropdown-item>
        <el-dropdown-item divided>
          <div style="width: 220px;">
            <div>Simulation Progress:</div>
            <el-progress :percentage="progress" style="margin: 4px 0;" />
            <div>Simu Time: {{ simTime }}</div>
          </div>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>

  <!-- 紧凑两行结构 inline 模式 -->
  <div v-else class="sim-inline-wrapper">
    <div class="sim-btn-group">
      <el-button
        v-for="item in btns"
        :key="item.title"
        size="small"
        circle
        :title="item.title"
        @click="item.click"
        style="margin-right:4px"
      >
        <el-icon :style="{ color: item.iconColor }">
          <component :is="item.icon" />
        </el-icon>
      </el-button>
    </div>
    <div class="sim-inline-info">
      <span class="sim-inline-progress">
        <el-icon style="margin-right:2px;"><RefreshRight /></el-icon>
        {{ progress }}%
      </span>
      <span class="sim-inline-time">
        <el-icon style="margin-right:2px;"><Clock /></el-icon>
        {{ simTime }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowDown, VideoPlay, VideoPause, RefreshRight, CircleClose, Clock, Edit } from '@element-plus/icons-vue'
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  mode: { type: String, default: 'dropdown' }, // 'dropdown' or 'inline'
  progress: { type: Number, default: 0 },
  simTime: { type: String, default: '' }
})
const emits = defineEmits(['start', 'pause', 'step', 'stop', 'order'])

function emitOrder() { emits('order') }
function emitStart() { emits('start') }
function emitPause() { emits('pause') }
function emitStep() { emits('step') }
function emitStop() { emits('stop') }

const btns = [
  { icon: Edit, title: 'Order', click: emitOrder, iconColor: '#4f8aff' },
  { icon: VideoPlay, title: 'Start', click: emitStart, iconColor: '#30d158' },
  { icon: VideoPause, title: 'Pause', click: emitPause, iconColor: '#ffb300' },
  { icon: RefreshRight, title: 'Step', click: emitStep, iconColor: '#409eff' },
  { icon: CircleClose, title: 'Stop', click: emitStop, iconColor: '#ff4d4f' }
]
</script>

<style scoped>
.sim-inline-wrapper {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 190px;
  height: 48px;
  justify-content: center;
}

.sim-btn-group {
  display: flex;
  align-items: center;
  height: 28px;
  margin-bottom: 2px;
}
.sim-btn-group .el-button {
  margin-right: 2px;
  padding: 0 5px;
}

.sim-inline-info {
  display: flex;
  align-items: center;
  font-size: 13px;
  margin-top: 0;
}

.sim-inline-progress {
  margin-right: 12px;
  font-size: 13px;
  color: #409eff;
  min-width: 44px;
  display: flex;
  align-items: center;
}
.sim-inline-time {
  font-size: 13px;
  color: #bbb;
  min-width: 78px;
  display: flex;
  align-items: center;
  white-space: nowrap;
}
</style>