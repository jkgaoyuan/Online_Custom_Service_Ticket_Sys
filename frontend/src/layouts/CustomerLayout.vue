<template>
  <el-container class="layout-container">
    <el-aside width="200px">
      <el-menu default-active="1">
        <el-menu-item index="1">
          <el-icon><HomeFilled /></el-icon>
          <span>我的工单</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>客户中心</el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout-container {
  height: 100vh;
}
</style>
