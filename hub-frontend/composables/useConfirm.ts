const _state = reactive({
  open: false,
  title: 'Confirmar',
  message: '',
  confirmLabel: 'Confirmar',
  danger: true,
  resolve: null as ((value: boolean) => void) | null,
})

export const useConfirm = () => {
  const confirm = (
    message: string,
    options?: { title?: string; confirmLabel?: string; danger?: boolean }
  ): Promise<boolean> => {
    return new Promise((resolve) => {
      _state.message = message
      _state.title = options?.title ?? 'Confirmar'
      _state.confirmLabel = options?.confirmLabel ?? 'Confirmar'
      _state.danger = options?.danger ?? true
      _state.resolve = resolve
      _state.open = true
    })
  }

  const _accept = () => {
    _state.open = false
    _state.resolve?.(true)
    _state.resolve = null
  }

  const _cancel = () => {
    _state.open = false
    _state.resolve?.(false)
    _state.resolve = null
  }

  return { _state, confirm, _accept, _cancel }
}
