import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { createContext, useContext, ReactNode } from 'react'
import axios from 'axios'

const rawApiBase = import.meta.env.VITE_API_BASE_URL?.trim()
const API_BASE = rawApiBase ? rawApiBase.replace(/\/+$/, '') : '/api'

interface User {
  id: number
  username: string
  email: string
  full_name?: string
  role: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

// Axios instance with interceptors
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth header
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE}/auth/refresh`, {
            refresh_token: refreshToken,
          })
          const { access_token } = response.data
          localStorage.setItem('access_token', access_token)
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        } catch (refreshError) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user')
          window.location.reload()
        }
      }
    }
    return Promise.reject(error)
  }
)

const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: JSON.parse(localStorage.getItem('user') || 'null'),
      accessToken: localStorage.getItem('access_token'),
      refreshToken: localStorage.getItem('refresh_token'),

      login: async (username: string, password: string) => {
        const formData = new URLSearchParams()
        formData.append('grant_type', 'password')
        formData.append('username', username)
        formData.append('password', password)
        formData.append('scope', '')
        formData.append('client_id', 'nms')

        const response = await api.post('/auth/login', formData, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        })

        const { access_token, refresh_token } = response.data

        localStorage.setItem('access_token', access_token)
        localStorage.setItem('refresh_token', refresh_token)

        // Get user info
        const userResponse = await api.get('/auth/me')
        localStorage.setItem('user', JSON.stringify(userResponse.data))

        set({
          user: userResponse.data,
          accessToken: access_token,
          refreshToken: refresh_token,
        })
      },

      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        set({ user: null, accessToken: null, refreshToken: null })
      },

      get isAuthenticated() {
        return !!get().accessToken && !!get().user
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
)

// React context for easier access
const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const auth = useAuthStore()
  const providerValue = auth
  return (
    <AuthContext.Provider value={providerValue}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export { api }
