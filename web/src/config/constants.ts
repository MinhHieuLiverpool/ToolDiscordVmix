// ── Runtime-aware backend URL ─────────────────────────────────────────────────
// Ưu tiên đọc từ .env (VITE_BACKEND_BASE_URL), hỗ trợ auto-detect origin khi build SPA
const _origin = typeof window !== 'undefined' ? window.location.origin : ''
const _hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost'

let _envOverride = String(import.meta.env.VITE_BACKEND_BASE_URL || '').trim().replace(/\/+$/, '')

// Tự động sửa 0.0.0.0 thành hostname hiện tại (vì browser không kết nối được tới 0.0.0.0)
if (_envOverride.includes('://0.0.0.0')) {
  const host = (_hostname && _hostname !== '0.0.0.0') ? _hostname : 'localhost'
  _envOverride = _envOverride.replace('://0.0.0.0', `://${host}`)
}

// Nếu truy cập từ máy khác trong LAN (hostname != localhost) mà .env cấu hình localhost,
// tự động trỏ tới IP LAN hiện tại
if (_hostname && _hostname !== 'localhost' && _hostname !== '127.0.0.1' && _envOverride.includes('://localhost')) {
  _envOverride = _envOverride.replace('://localhost', `://${_hostname}`)
}

// origin hợp lệ = bắt đầu bằng http (không phải file:// hoặc rỗng)
const _isValidHttpOrigin = _origin.startsWith('http://') || _origin.startsWith('https://')

export const BACKEND_BASE_URL = (
  // 1. Ưu tiên cấu hình từ .env
  _envOverride
  // 2. Dùng origin nếu cùng host (FastAPI serve static SPA)
  || (_isValidHttpOrigin ? _origin : '')
  // 3. Fallback mặc định
  || 'http://localhost:8001'
)

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
let _wsEnvOverride = String(import.meta.env.VITE_BACKEND_WS_URL || '').trim().replace(/\/+$/, '')

// Sửa lỗi cú pháp nếu vô tình gõ ws// thay vì ws://
if (_wsEnvOverride.startsWith('ws//')) {
  _wsEnvOverride = _wsEnvOverride.replace(/^ws\/\//, 'ws://')
} else if (_wsEnvOverride.startsWith('wss//')) {
  _wsEnvOverride = _wsEnvOverride.replace(/^wss\/\//, 'wss://')
}

if (_wsEnvOverride.includes('://0.0.0.0')) {
  const host = (_hostname && _hostname !== '0.0.0.0') ? _hostname : 'localhost'
  _wsEnvOverride = _wsEnvOverride.replace('://0.0.0.0', `://${host}`)
}

if (_hostname && _hostname !== 'localhost' && _hostname !== '127.0.0.1' && _wsEnvOverride.includes('://localhost')) {
  _wsEnvOverride = _wsEnvOverride.replace('://localhost', `://${_hostname}`)
}

export const BACKEND_WS_URL = _wsEnvOverride
  || `${BACKEND_BASE_URL.replace(/^http/i, 'ws')}${API_ENDPOINTS.ws}`