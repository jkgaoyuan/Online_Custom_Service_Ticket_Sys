import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ticketApi, replyApi } from '@/api/tickets'
import { categoryApi } from '@/api/categories'

export const useTicketsStore = defineStore('tickets', () => {
  const tickets = ref([])
  const currentTicket = ref(null)
  const replies = ref([])
  const categories = ref([])
  const pagination = ref({ total: 0, page: 1, page_size: 20 })
  const loading = ref(false)

  const fetchCategories = async () => {
    const { data } = await categoryApi.list()
    categories.value = data
  }

  const fetchTickets = async (params = {}) => {
    loading.value = true
    try {
      const { data } = await ticketApi.list(params)
      tickets.value = data.items
      pagination.value = { total: data.total, page: data.page, page_size: data.page_size }
    } finally {
      loading.value = false
    }
  }

  const fetchTicket = async (id) => {
    loading.value = true
    try {
      const { data } = await ticketApi.get(id)
      currentTicket.value = data
    } finally {
      loading.value = false
    }
  }

  const fetchReplies = async (ticketId) => {
    const { data } = await replyApi.list(ticketId)
    replies.value = data
  }

  const createTicket = async (payload) => {
    const { data } = await ticketApi.create(payload)
    return data
  }

  const replyTicket = async (ticketId, payload) => {
    const { data } = await ticketApi.reply(ticketId, payload)
    replies.value.push(data)
    return data
  }

  const updateStatus = async (ticketId, status) => {
    const { data } = await ticketApi.updateStatus(ticketId, status)
    currentTicket.value = data
    return data
  }

  const assignTicket = async (ticketId, assigneeId) => {
    const { data } = await ticketApi.assign(ticketId, assigneeId)
    currentTicket.value = data
    return data
  }

  const submitSatisfaction = async (ticketId, payload) => {
    const { data } = await ticketApi.submitSatisfaction(ticketId, payload)
    currentTicket.value = data
    return data
  }

  const transferTicket = async (ticketId, payload) => {
    const { data } = await ticketApi.transfer(ticketId, payload)
    currentTicket.value = data
    return data
  }

  const assistTicket = async (ticketId, payload) => {
    const { data } = await ticketApi.assist(ticketId, payload)
    if (currentTicket.value) {
      currentTicket.value.collaborations = currentTicket.value.collaborations || []
      currentTicket.value.collaborations.unshift(data)
    }
    return data
  }

  return {
    tickets, currentTicket, replies, categories, pagination, loading,
    fetchCategories, fetchTickets, fetchTicket, fetchReplies,
    createTicket, replyTicket, updateStatus, assignTicket, submitSatisfaction,
    transferTicket, assistTicket,
  }
})
