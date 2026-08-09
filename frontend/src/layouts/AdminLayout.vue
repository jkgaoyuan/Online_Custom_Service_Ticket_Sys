<template>
  <el-container class="layout-container">
    <el-aside width="200px">
      <el-menu default-active="1">
        <el-menu-item index="1">
          <el-icon><UserFilled /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="2" @click="$router.push('/admin/reports')">
          <el-icon><TrendCharts /></el-icon>
          <span>数据报表</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>管理后台</el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { TrendCharts, UserFilled } from '@element-plus/icons-vue'
</script>

<style scoped>
.layout-container {
  height: 100vh;
}
</style>
