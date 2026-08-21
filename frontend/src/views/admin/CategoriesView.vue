<template>
  <div class="categories-management">
    <h2>分类管理</h2>

    <div class="filter-bar">
      <div class="filter-left" />
      <el-button type="primary" @click="openCreate">新增分类</el-button>
    </div>

    <el-table :data="categoriesStore.categories" v-loading="categoriesStore.loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="code" label="Code" />
      <el-table-column prop="priority" label="优先级" width="100">
        <template #default="{ row }">
          <el-tag :type="priorityTagType(row.priority)">{{ row.priority }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="SLA 配置">
        <template #default="{ row }">
          <div class="sla-text">
            首次响应: {{ row.sla_config?.first_resp_hours ?? '-' }}h
            / 解决时限: {{ row.sla_config?.resolution_hours ?? '-' }}h
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑分类' : '新增分类'" width="480px">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入分类名称" />
        </el-form-item>
        <el-form-item label="Code" prop="code">
          <el-input v-model="form.code" placeholder="请输入分类 code" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="form.priority" placeholder="请选择优先级">
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
            <el-option label="P4" value="P4" />
          </el-select>
        </el-form-item>
        <el-form-item label="首次响应(h)" prop="first_resp_hours">
          <el-input-number v-model="form.first_resp_hours" :min="1" :max="168" />
        </el-form-item>
        <el-form-item label="解决时限(h)" prop="resolution_hours">
          <el-input-number v-model="form.resolution_hours" :min="1" :max="720" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useCategoriesStore } from '@/stores/categories'
import { ElMessage, ElMessageBox } from 'element-plus'

const categoriesStore = useCategoriesStore()

const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)

const form = reactive({
  id: null,
  name: '',
  code: '',
  priority: 'P1',
  first_resp_hours: 4,
  resolution_hours: 24,
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入 Code', trigger: 'blur' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
}

function priorityTagType(priority) {
  const map = { P1: 'danger', P2: 'warning', P3: 'primary', P4: 'info' }
  return map[priority] || 'info'
}

function formatDate(d) {
  return d ? new Date(d).toLocaleString() : '-'
}

function resetForm() {
  form.id = null
  form.name = ''
  form.code = ''
  form.priority = 'P1'
  form.first_resp_hours = 4
  form.resolution_hours = 24
}

function openCreate() {
  resetForm()
  isEdit.value = false
  dialogVisible.value = true
}

function openEdit(row) {
  form.id = row.id
  form.name = row.name
  form.code = row.code
  form.priority = row.priority
  form.first_resp_hours = row.sla_config?.first_resp_hours ?? 4
  form.resolution_hours = row.sla_config?.resolution_hours ?? 24
  isEdit.value = true
  dialogVisible.value = true
}

async function submitForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    const payload = {
      name: form.name,
      code: form.code,
      priority: form.priority,
      sla_config: {
        first_resp_hours: form.first_resp_hours,
        resolution_hours: form.resolution_hours,
      },
    }
    if (isEdit.value) {
      await categoriesStore.updateCategory(form.id, payload)
      ElMessage.success('更新成功')
    } else {
      await categoriesStore.createCategory(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await categoriesStore.fetchCategories()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || (isEdit.value ? '更新失败' : '创建失败'))
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除分类 "${row.name}"？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await categoriesStore.deleteCategory(row.id)
    ElMessage.success('删除成功')
    await categoriesStore.fetchCategories()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

onMounted(() => categoriesStore.fetchCategories())
</script>

<style scoped>
.categories-management { padding: 24px; }
.filter-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.filter-left { display: flex; gap: 12px; }
.sla-text { font-size: 13px; color: #606266; }
</style>
