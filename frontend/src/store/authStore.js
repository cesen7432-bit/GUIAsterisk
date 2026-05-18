import { create } from 'zustand'
import api from '../api/client'

export const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('access_token'),

  login: async (email, password) => {
    const params = new URLSearchParams({ username: email, password })
    const { data } = await api.post('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    localStorage.setItem('access_token', data.access_token)
    set({ token: data.access_token })
    const me = await api.get('/auth/me')
    set({ user: me.data })
    return me.data
  },

  logout: () => {
    localStorage.removeItem('access_token')
    set({ user: null, token: null })
  },

  fetchMe: async () => {
    try {
      const { data } = await api.get('/auth/me')
      set({ user: data })
    } catch {
      set({ user: null, token: null })
      localStorage.removeItem('access_token')
    }
  },
}))
