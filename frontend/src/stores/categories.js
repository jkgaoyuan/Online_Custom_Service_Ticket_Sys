import { defineStore } from 'pinia'
import { ref } from 'vue'
import { categoryApi } from '@/api/categories'

export const useCategoriesStore = defineStore('categories', () => {
  const categories = ref([])
  const loading = ref(false)

  async function fetchCategories() {
    loading.value = true
    try {
      const response = await categoryApi.list()
      categories.value = response.data
    } finally {
      loading.value = false
    }
  }

  async function createCategory(data) {
    const response = await categoryApi.create(data)
    return response.data
  }

  async function updateCategory(id, data) {
    const response = await categoryApi.update(id, data)
    return response.data
  }

  async function deleteCategory(id) {
    const response = await categoryApi.delete(id)
    return response.data
  }

  return {
    categories,
    loading,
    fetchCategories,
    createCategory,
    updateCategory,
    deleteCategory,
  }
})
