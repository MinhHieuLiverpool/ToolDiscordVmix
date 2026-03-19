const isLocalHost = typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname)
const DEFAULT_LOCAL_BACKEND_BASE_URL = 'http://localhost:8000'
const DEFAULT_PROD_BACKEND_BASE_URL = 'https://tooldiscordvmix.onrender.com'

const configuredBackendBaseUrl = String(import.meta.env.VITE_BACKEND_BASE_URL || '')
  .trim()
  .replace(/\/+$/, '')

export const BACKEND_BASE_URL = configuredBackendBaseUrl || (
  isLocalHost ? DEFAULT_LOCAL_BACKEND_BASE_URL : DEFAULT_PROD_BACKEND_BASE_URL
)

export const API_ENDPOINTS = {
  logs: '/logs',
  ws: '/ws',
  login: '/login',
  statistics: '/statistics',
  statisticHours: '/statistic_hours',
} as const

const configuredTimeout = Number(import.meta.env.VITE_REQUEST_TIMEOUT_MS)

export const REQUEST_TIMEOUT_MS = Number.isFinite(configuredTimeout) && configuredTimeout > 0
  ? configuredTimeout
  : 30000

const configuredBackendWsUrl = String(import.meta.env.VITE_BACKEND_WS_URL || '')
  .trim()
  .replace(/\/+$/, '')

export const BACKEND_WS_URL = configuredBackendWsUrl
  || `${BACKEND_BASE_URL.replace(/^http/i, 'ws')}${API_ENDPOINTS.ws}`