// Estado global de conversas não lidas — persiste entre rotas
export const useUnread = () => {
  const ids = useState<number[]>('unread-conv-ids', () => [])

  const add = (id: number) => {
    if (!ids.value.includes(id)) ids.value.push(id)
  }

  const remove = (id: number) => {
    ids.value = ids.value.filter(x => x !== id)
  }

  const has = (id: number) => ids.value.includes(id)

  const total = computed(() => ids.value.length)

  return { ids, add, remove, has, total }
}
