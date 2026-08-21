<template>
  <el-container class="layout-container">
    <el-aside width="200px">
      <el-menu :default-active="$route.path" router>
        <el-menu-item index="/customer/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/customer/tickets">
          <el-icon><Tickets /></el-icon>
          <span>我的工单</span>
        </el-menu-item>
        <el-menu-item index="/customer/tickets/new">
          <el-icon><CirclePlus /></el-icon>
          <span>提交工单</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-content">
          <span class="header-title">客户中心</span>
          <div class="header-right">
            <span v-if="authStore.user" class="username">{{ authStore.user.username }}</span>
            <el-button type="danger" size="small" @click="handleLogout">退出登录</el-button>
          </div>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useAuthStore } from '@/stores'

const authStore = useAuthStore()

function handleLogout() {
  authStore.logout()
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}
.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}
.header-title {
  font-size: 18px;
  font-weight: 600;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.username {
  font-size: 14px;
  color: #606266;
}
</style>
