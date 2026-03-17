export const BACKEND_BASE_URL = 'https://tooldiscordvmix.onrender.com'

export const API_ENDPOINTS = {
  logs: '/logs',
  ws: '/ws',
} as const

export const REQUEST_TIMEOUT_MS = 30000

export const BACKEND_WS_URL = `${BACKEND_BASE_URL.replace(/^http/i, 'ws')}${API_ENDPOINTS.ws}`