<template>
  <div class="create-ticket">
    <h2>提交工单</h2>
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item label="标题" prop="title">
        <el-input v-model="form.title" maxlength="200" show-word-limit />
      </el-form-item>
      <el-form-item label="分类" prop="category_id">
        <el-select v-model="form.category_id" placeholder="选择分类">
          <el-option v-for="cat in store.categories" :key="cat.id" :label="cat.name" :value="cat.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="优先级" prop="priority">
        <el-select v-model="form.priority">
          <el-option label="紧急" value="P0" />
          <el-option label="高" value="P1" />
          <el-option label="中" value="P2" />
          <el-option label="低" value="P3" />
        </el-select>
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input v-model="form.description" type="textarea" :rows="5" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="submit" :loading="store.loading">提交</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTicketsStore } from '@/stores'
import { ElMessage } from 'element-plus'
const router = useRouter()
const store = useTicketsStore()
const formRef = ref(null)
const form = reactive({ title: '', category_id: null, priority: 'P2', description: '' })
const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }, { max: 200, message: '最多200字符', trigger: 'blur' }],
  category_id: [{ required: true, message: '请选择分类', trigger: 'change' }],
  description: [{ required: true, message: '请输入描述', trigger: 'blur' }],
}
const submit = async () => {
  await formRef.value.validate()
  await store.createTicket({ ...form, source: 'web' })
  ElMessage.success('工单提交成功')
  router.push('/customer/tickets')
}
onMounted(() => store.fetchCategories())
</script>
