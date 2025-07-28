<template>
  <el-container>
    <el-header style="padding:0;">
      <TopNavBar />
      <MainMenu />
    </el-header>
    <el-main style="padding-top: 10px;">
      <router-view />
    </el-main>
  </el-container>
</template>
<script setup lang="ts">
import TopNavBar from './components/topNavBar.vue'
import MainMenu from './components/MainMenu.vue'
</script>