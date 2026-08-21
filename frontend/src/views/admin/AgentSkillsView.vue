<template>
  <div class="agent-skills-management">
    <h2>技能配置</h2>

    <div class="filter-bar">
      <el-button type="primary" @click="openCreate">新增技能</el-button>
    </div>

    <el-table :data="skillsStore.skills" v-loading="skillsStore.loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="agent_name" label="客服" />
      <el-table-column prop="category_name" label="分类" />
      <el-table-column prop="proficiency" label="熟练度">
        <template #default="{ row }">
          <el-rate v-model="row.proficiency" disabled show-score text-color="#ff9900" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑技能' : '新增技能'" width="400px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="客服">
          <el-select v-model="form.agent_id" placeholder="请选择客服" :disabled="isEdit">
            <el-option
              v-for="agent in skillsStore.agents"
              :key="agent.id"
              :label="agent.username"
              :value="agent.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category_id" placeholder="请选择分类" :disabled="isEdit">
            <el-option
              v-for="cat in skillsStore.categories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="熟练度">
          <el-slider v-model="form.proficiency" :min="1" :max="5" show-stops />
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
import { useAgentSkillsStore } from '@/stores/agentSkills'
import { ElMessage, ElMessageBox } from 'element-plus'

const skillsStore = useAgentSkillsStore()

const dialogVisible = ref(false)
const submitLoading = ref(false)
const isEdit = ref(false)
const form = reactive({ id: null, agent_id: null, category_id: null, proficiency: 3 })

function openCreate() {
  isEdit.value = false
  form.id = null
  form.agent_id = null
  form.category_id = null
  form.proficiency = 3
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  form.id = row.id
  form.agent_id = row.agent_id
  form.category_id = row.category_id
  form.proficiency = row.proficiency
  dialogVisible.value = true
}

async function submitForm() {
  submitLoading.value = true
  try {
    const payload = {
      agent_id: form.agent_id,
      category_id: form.category_id,
      proficiency: form.proficiency,
    }
    if (isEdit.value) {
      await skillsStore.updateSkill(form.id, payload)
      ElMessage.success('更新成功')
    } else {
      await skillsStore.createSkill(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await skillsStore.fetchSkills()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除客服 ${row.agent_name} 的 ${row.category_name} 技能？`, '确认删除')
    await skillsStore.deleteSkill(row.id)
    ElMessage.success('删除成功')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

onMounted(async () => {
  await skillsStore.fetchSkills()
  await skillsStore.fetchAgents()
  await skillsStore.fetchCategories()
})
</script>

<style scoped>
.agent-skills-management { padding: 24px; }
.filter-bar { display: flex; justify-content: flex-end; margin-bottom: 16px; }
</style>
