import { defineStore } from 'pinia'
import { ref } from 'vue'
import { agentSkillApi } from '@/api/agentSkills'
import { categoryApi } from '@/api/categories'
import { ticketApi } from '@/api/tickets'

export const useAgentSkillsStore = defineStore('agentSkills', () => {
  const skills = ref([])
  const agents = ref([])
  const categories = ref([])
  const loading = ref(false)

  async function fetchSkills() {
    loading.value = true
    try {
      const { data } = await agentSkillApi.list()
      skills.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchAgents() {
    const { data } = await ticketApi.getAgents()
    agents.value = data
  }

  async function fetchCategories() {
    const { data } = await categoryApi.list()
    categories.value = data
  }

  async function createSkill(payload) {
    const { data } = await agentSkillApi.create(payload)
    skills.value.push(data)
    return data
  }

  async function updateSkill(id, payload) {
    const { data } = await agentSkillApi.update(id, payload)
    const idx = skills.value.findIndex((s) => s.id === id)
    if (idx !== -1) {
      skills.value[idx] = data
    }
    return data
  }

  async function deleteSkill(id) {
    await agentSkillApi.delete(id)
    skills.value = skills.value.filter((s) => s.id !== id)
  }

  return {
    skills,
    agents,
    categories,
    loading,
    fetchSkills,
    fetchAgents,
    fetchCategories,
    createSkill,
    updateSkill,
    deleteSkill,
  }
})
