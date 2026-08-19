// ── Runtime-aware backend URL ─────────────────────────────────────────────────
// Web được FastAPI serve → window.location.origin chính là địa chỉ server
// → tự động trỏ đúng dù LAN, WAN, hay VLAN đổi. Không cần .env!
//
// Fallback về VITE_BACKEND_BASE_URL chỉ khi cần trỏ sang server khác.

const _origin = typeof window !== 'undefined' ? window.location.origin : ''
const _envOverride = String(import.meta.env.VITE_BACKEND_BASE_URL || '').trim().replace(/\/+$/, '')

// origin hợp lệ = bắt đầu bằng http (không phải file:// hoặc rỗng)
const _isValidHttpOrigin = _origin.startsWith('http://') || _origin.startsWith('https://')

export const BACKEND_BASE_URL = (
  // 1. Ưu tiên env override nếu có
  _envOverride
  // 2. Dùng chính origin nếu là HTTP (same-server auto-detect)
  || (_isValidHttpOrigin ? _origin : '')
  // 3. Không bao giờ fallback về localhost — server phải được truy cập qua LAN/WAN
) || ''

export const API_ENDPOINTS = {
  logs: '/logs',
  ws: '/ws',
  login: '/login',
  accounts: '/accounts',
  speedtest: '/speedtest',
  statistics: '/statistics',
  statisticHours: '/statistic_hours',
} as const

const configuredTimeout = Number(import.meta.env.VITE_REQUEST_TIMEOUT_MS)

export const REQUEST_TIMEOUT_MS = Number.isFinite(configuredTimeout) && configuredTimeout > 0
  ? configuredTimeout
  : 30000

// ── WebSocket URL ─────────────────────────────────────────────────────────────
const _wsEnvOverride = String(import.meta.env.VITE_BACKEND_WS_URL || '').trim().replace(/\/+$/, '')

export const BACKEND_WS_URL = _wsEnvOverride
  || `${BACKEND_BASE_URL.replace(/^http/i, 'ws')}${API_ENDPOINTS.ws}`