import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface UserInfo {
  id: number
  username: string
  email: string
  avatar?: string
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function setUserInfo(info: UserInfo) {
    userInfo.value = info
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  function initFromStorage() {
    const storedToken = localStorage.getItem('token')
    if (storedToken) {
      token.value = storedToken
    }
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    setToken,
    setUserInfo,
    logout,
    initFromStorage
  }
})
