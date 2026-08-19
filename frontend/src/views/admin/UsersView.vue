<template>
  <div class="users-management">
    <h2>用户管理</h2>

    <!-- 筛选区域 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-select v-model="filterRole" placeholder="角色" clearable @change="handleFilter">
          <el-option label="全部" value="" />
          <el-option label="客户" value="customer" />
          <el-option label="客服" value="agent" />
          <el-option label="主管" value="supervisor" />
          <el-option label="管理员" value="admin" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable @change="handleFilter">
          <el-option label="全部" value="" />
          <el-option label="启用" :value="true" />
          <el-option label="禁用" :value="false" />
        </el-select>
      </div>
      <el-button type="primary" @click="openCreate">新增用户</el-button>
    </div>

    <!-- 用户表格 -->
    <el-table :data="usersStore.users" v-loading="usersStore.loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="role" label="角色">
        <template #default="{ row }">
          <el-tag :type="roleTagType(row.role)">{{ roleLabel(row.role) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="ticket_count" label="工单数" width="80" />
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="warning" @click="openResetPassword(row)">重置密码</el-button>
          <el-button
            size="small"
            :type="row.is_active ? 'danger' : 'success'"
            @click="toggleStatus(row)"
          >
            {{ row.is_active ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="usersStore.total"
      layout="total, prev, pager, next"
      @change="handleFilter"
    />

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑用户" width="400px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role">
            <el-option label="客户" value="customer" />
            <el-option label="客服" value="agent" />
            <el-option label="主管" value="supervisor" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEdit" :loading="editLoading">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增用户弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新增用户" width="400px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="createForm.username" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="createForm.email" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="createForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role" placeholder="请选择角色">
            <el-option label="客户" value="customer" />
            <el-option label="客服" value="agent" />
            <el-option label="主管" value="supervisor" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate" :loading="createLoading">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="resetDialogVisible" title="重置密码" width="400px">
      <p>确定重置用户 <strong>{{ resetTarget?.username }}</strong> 的密码？</p>
      <p class="warning-text">重置后将生成临时密码，请妥善保存。</p>
      <div v-if="tempPassword" class="temp-password-box">
        <p>临时密码：<code>{{ tempPassword }}</code></p>
        <el-button size="small" @click="copyPassword">复制</el-button>
      </div>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button v-if="!tempPassword" type="warning" @click="confirmReset" :loading="resetLoading">确认重置</el-button>
        <el-button v-else type="primary" @click="resetDialogVisible = false">完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useUsersStore } from '@/stores/users'
import { ElMessage, ElMessageBox } from 'element-plus'

const usersStore = useUsersStore()

const filterRole = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

const editDialogVisible = ref(false)
const editLoading = ref(false)
const editForm = reactive({ id: null, username: '', email: '', role: '' })

const createDialogVisible = ref(false)
const createLoading = ref(false)
const createForm = reactive({ username: '', email: '', password: '', role: '' })

const resetDialogVisible = ref(false)
const resetLoading = ref(false)
const resetTarget = ref(null)
const tempPassword = ref('')

function roleTagType(role) {
  const map = { customer: 'info', agent: 'primary', supervisor: 'warning', admin: 'danger' }
  return map[role] || 'info'
}
function roleLabel(role) {
  const map = { customer: '客户', agent: '客服', supervisor: '主管', admin: '管理员' }
  return map[role] || role
}
function formatDate(d) {
  return d ? new Date(d).toLocaleString() : '-'
}

async function handleFilter() {
  const params = { page: currentPage.value, page_size: pageSize.value }
  if (filterRole.value) params.role = filterRole.value
  if (filterStatus.value !== '') params.is_active = filterStatus.value
  await usersStore.fetchUsers(params)
}

function openEdit(row) {
  editForm.id = row.id
  editForm.username = row.username
  editForm.email = row.email
  editForm.role = row.role
  editDialogVisible.value = true
}

async function submitEdit() {
  editLoading.value = true
  try {
    await usersStore.updateUser(editForm.id, {
      username: editForm.username,
      email: editForm.email,
      role: editForm.role,
    })
    ElMessage.success('保存成功')
    editDialogVisible.value = false
    await handleFilter()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    editLoading.value = false
  }
}

function openCreate() {
  createForm.username = ''
  createForm.email = ''
  createForm.password = ''
  createForm.role = ''
  createDialogVisible.value = true
}

async function submitCreate() {
  createLoading.value = true
  try {
    await usersStore.createUser({
      username: createForm.username,
      email: createForm.email,
      password: createForm.password,
      role: createForm.role,
    })
    ElMessage.success('创建成功')
    createDialogVisible.value = false
    await handleFilter()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    createLoading.value = false
  }
}

function openResetPassword(row) {
  resetTarget.value = row
  tempPassword.value = ''
  resetDialogVisible.value = true
}

async function confirmReset() {
  resetLoading.value = true
  try {
    const result = await usersStore.resetPassword(resetTarget.value.id)
    tempPassword.value = result.temp_password
    ElMessage.success('密码已重置')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重置失败')
  } finally {
    resetLoading.value = false
  }
}

function copyPassword() {
  navigator.clipboard.writeText(tempPassword.value)
  ElMessage.success('已复制到剪贴板')
}

async function toggleStatus(row) {
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定${action}用户 ${row.username}？`, '确认')
    await usersStore.updateUser(row.id, { is_active: !row.is_active })
    ElMessage.success(`${action}成功`)
    await handleFilter()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '操作失败')
    }
  }
}

onMounted(() => handleFilter())
</script>

<style scoped>
.users-management { padding: 24px; }
.filter-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.filter-left { display: flex; gap: 12px; }
.warning-text { color: #e6a23c; font-size: 13px; margin-top: 8px; }
.temp-password-box { margin-top: 16px; padding: 12px; background: #f5f7fa; border-radius: 4px; }
.temp-password-box code { font-size: 16px; font-weight: bold; color: #409eff; }
</style>
