import { defineStore } from 'pinia'

export interface Label {
  id: number
  name: string
  color: string
}

export const useLabelsStore = defineStore('labels', () => {
  const api = useApi()
  const labels = ref<Label[]>([])
  const fetched = ref(false)

  const fetchLabels = async (force = false) => {
    if (fetched.value && !force) return
    try {
      labels.value = await api<Label[]>('/api/labels/')
      fetched.value = true
    } catch {}
  }

  const createLabel = async (data: { name: string; color: string }) => {
    const label = await api<Label>('/api/labels/', { method: 'POST', body: data })
    labels.value.push(label)
    return label
  }

  const updateLabel = async (id: number, data: { name?: string; color?: string }) => {
    const label = await api<Label>(`/api/labels/${id}`, { method: 'PATCH', body: data })
    const idx = labels.value.findIndex(l => l.id === id)
    if (idx !== -1) labels.value[idx] = label
    return label
  }

  const deleteLabel = async (id: number) => {
    await api(`/api/labels/${id}`, { method: 'DELETE' })
    labels.value = labels.value.filter(l => l.id !== id)
  }

  return { labels, fetched, fetchLabels, createLabel, updateLabel, deleteLabel }
})
