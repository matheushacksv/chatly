export const useNotifications = () => {
  const permission = ref<NotificationPermission>(
    process.client && 'Notification' in window ? Notification.permission : 'default'
  )

  const requestPermission = async () => {
    if (!process.client || !('Notification' in window)) return
    const result = await Notification.requestPermission()
    permission.value = result
  }

  const send = (title: string, body: string) => {
    if (!process.client || permission.value !== 'granted') return
    new Notification(title, { body, icon: '/favicon.ico' })
  }

  return { permission, requestPermission, send }
}
