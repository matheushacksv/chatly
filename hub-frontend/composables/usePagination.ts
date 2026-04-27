import type { ComputedRef, Ref } from 'vue'

export const usePagination = <T>(
  source: ComputedRef<T[]> | Ref<T[]>,
  pageSize = 20,
) => {
  const page = ref(1)

  const totalPages = computed(() => Math.max(1, Math.ceil(source.value.length / pageSize)))

  const paged = computed(() => {
    const start = (page.value - 1) * pageSize
    return source.value.slice(start, start + pageSize)
  })

  // Volta para a primeira página sempre que a fonte mudar (busca, filtro, etc.)
  watch(() => source.value.length, () => { page.value = 1 })

  const prev   = () => { if (page.value > 1) page.value-- }
  const next   = () => { if (page.value < totalPages.value) page.value++ }
  const goTo   = (n: number) => { page.value = Math.max(1, Math.min(n, totalPages.value)) }

  return { page, totalPages, paged, prev, next, goTo }
}
