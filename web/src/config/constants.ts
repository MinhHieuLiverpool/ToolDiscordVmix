const isLocalHost = typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname)

export const BACKEND_BASE_URL = isLocalHost
  ? 'http://localhost:8000'
  : 'https://tooldiscordvmix.onrender.com'

export const API_ENDPOINTS = {
  logs: '/logs',
  ws: '/ws',
  statistics: '/statistics',
  statisticHours: '/statistic_hours',
} as const

export const REQUEST_TIMEOUT_MS = 30000

export const BACKEND_WS_URL = `${BACKEND_BASE_URL.replace(/^http/i, 'ws')}${API_ENDPOINTS.ws}`