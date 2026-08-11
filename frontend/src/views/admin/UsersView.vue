<template>
  <div class="users-page" v-loading="store.loading">
    <!-- 筛选栏 -->
    <div class="toolbar">
      <el-select v-model="store.filters.role" placeholder="全部角色" clearable style="width: 140px" @change="handleFilterChange">
        <el-option label="客户" value="customer" />
        <el-option label="客服" value="agent" />
        <el-option label="主管" value="supervisor" />
        <el-option label="管理员" value="admin" />
      </el-select>
      <el-select v-model="store.filters.is_active" placeholder="全部状态" clearable style="width: 140px" @change="handleFilterChange">
        <el-option label="启用" :value="true" />
        <el-option label="禁用" :value="false" />
      </el-select>
      <el-button @click="handleFilterChange">查询</el-button>
    </div>

    <!-- 用户表格 -->
    <el-table :data="store.users" style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="roleType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="ticket_count" label="工单数" width="80" />
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
          <el-button size="small" type="warning" @click="openResetDialog(row)">重置密码</el-button>
          <el-button size="small" :type="row.is_active ? 'danger' : 'success'" @click="toggleStatus(row)">
            {{ row.is_active ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="store.pagination.page"
      v-model:page-size="store.pagination.page_size"
      :total="store.pagination.total"
      layout="total, prev, pager, next"
      @current-change="handlePageChange"
      @size-change="handlePageChange"
      class="pagination"
    />

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑用户" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role" placeholder="选择角色" style="width: 100%">
            <el-option label="客户" value="customer" />
            <el-option label="客服" value="agent" />
            <el-option label="主管" value="supervisor" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetDialogVisible" title="重置密码" width="400px">
      <p>确定要重置用户 <strong>{{ resetTarget?.username }}</strong> 的密码吗？</p>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitReset">确认</el-button>
      </template>
    </el-dialog>

    <!-- 显示临时密码 -->
    <el-dialog v-model="tempPasswordDialogVisible" title="临时密码" width="400px" :close-on-click-modal="false">
      <p>请复制以下临时密码并告知用户：</p>
      <div class="temp-password-box">
        <el-input v-model="tempPassword" readonly>
          <template #append>
            <el-button @click="copyTempPassword">复制</el-button>
          </template>
        </el-input>
      </div>
      <template #footer>
        <el-button type="primary" @click="tempPasswordDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useUsersStore } from '@/stores'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useUsersStore()

const editDialogVisible = ref(false)
const resetDialogVisible = ref(false)
const tempPasswordDialogVisible = ref(false)
const submitting = ref(false)
const editForm = ref({ id: null, username: '', email: '', role: '' })
const resetTarget = ref(null)
const tempPassword = ref('')

const roleMap = {
  customer: { label: '客户', type: 'info' },
  agent: { label: '客服', type: 'primary' },
  supervisor: { label: '主管', type: 'warning' },
  admin: { label: '管理员', type: 'danger' },
}

const roleLabel = (role) => roleMap[role]?.label || role
const roleType = (role) => roleMap[role]?.type || 'info'

const formatDate = (value) => {
  if (!value) return ''
  const d = new Date(value)
  return d.toLocaleString('zh-CN', { hour12: false })
}

const handleFilterChange = () => {
  store.pagination.page = 1
  store.fetchUsers()
}

const handlePageChange = () => {
  store.fetchUsers()
}

const openEditDialog = (row) => {
  editForm.value = {
    id: row.id,
    username: row.username,
    email: row.email,
    role: row.role,
  }
  editDialogVisible.value = true
}

const submitEdit = async () => {
  submitting.value = true
  try {
    await store.updateUser(editForm.value.id, {
      username: editForm.value.username,
      email: editForm.value.email,
      role: editForm.value.role,
    })
    editDialogVisible.value = false
    await store.fetchUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
  } finally {
    submitting.value = false
  }
}

const openResetDialog = (row) => {
  resetTarget.value = row
  resetDialogVisible.value = true
}

const submitReset = async () => {
  submitting.value = true
  try {
    const res = await store.resetPassword(resetTarget.value.id)
    tempPassword.value = res.temp_password
    resetDialogVisible.value = false
    tempPasswordDialogVisible.value = true
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '重置密码失败')
  } finally {
    submitting.value = false
  }
}

const copyTempPassword = () => {
  navigator.clipboard.writeText(tempPassword.value).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

const toggleStatus = async (row) => {
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户 ${row.username} 吗？`,
      '确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await store.updateUser(row.id, { is_active: !row.is_active })
    await store.fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  }
}

onMounted(() => {
  store.fetchUsers()
})
</script>

<style scoped>
.users-page {
  padding: 20px;
}
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}
.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}
.temp-password-box {
  margin-top: 16px;
}
</style>
