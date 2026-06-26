import axios from 'axios'
import { loginAccount, fetchUserProfile } from './api'

const AUTH_STORAGE_KEY = 'vmix_monitor_authenticated'
const USERNAME_STORAGE_KEY = 'vmix_monitor_username'
const ROLE_STORAGE_KEY = 'vmix_monitor_user_role'
const PERMISSIONS_STORAGE_KEY = 'vmix_monitor_user_permissions'
const ALLOWED_CHANNELS_STORAGE_KEY = 'vmix_monitor_user_allowed_channels'

export type AuthResult = {
  success: boolean
  message?: string
}

export async function authenticate(username: string, password: string): Promise<AuthResult> {
  try {
    const result = await loginAccount(username.trim(), password)
    const success = result.success === true
    setAuthenticated(success)
    if (success) {
      setUsername(result.username || username.trim())
      setUserRole(result.role || '')
      setUserPermissions(result.permissions || [])
      setUserAllowedChannels((result as any).allowed_channels || [])
    } else {
      setUsername('')
      setUserRole('')
      setUserPermissions([])
      setUserAllowedChannels([])
    }
    return {
      success,
      message: result.message,
    }
  } catch (error) {
    setAuthenticated(false)
    setUsername('')
    setUserRole('')
    setUserPermissions([])
    setUserAllowedChannels([])

    if (axios.isAxiosError(error)) {
      const message = String(error.response?.data?.message || '').trim()
      return {
        success: false,
        message: message || 'Khong the ket noi backend de dang nhap.',
      }
    }

    return {
      success: false,
      message: 'Dang nhap that bai do loi khong xac dinh.',
    }
  }
}

export function isAuthenticated(): boolean {
  return localStorage.getItem(AUTH_STORAGE_KEY) === 'true'
}

export function setAuthenticated(value: boolean): void {
  localStorage.setItem(AUTH_STORAGE_KEY, value ? 'true' : 'false')
}

export function setUsername(username: string): void {
  const value = username.trim()
  if (value) {
    localStorage.setItem(USERNAME_STORAGE_KEY, value)
  } else {
    localStorage.removeItem(USERNAME_STORAGE_KEY)
  }
}

export function getUsername(): string {
  return localStorage.getItem(USERNAME_STORAGE_KEY) || ''
}

export function setUserRole(role: string): void {
  const value = role.trim()
  if (value) {
    localStorage.setItem(ROLE_STORAGE_KEY, value)
  } else {
    localStorage.removeItem(ROLE_STORAGE_KEY)
  }
}

export function getUserRole(): string {
  return localStorage.getItem(ROLE_STORAGE_KEY) || ''
}

export function setUserPermissions(permissions: string[]): void {
  if (permissions && permissions.length > 0) {
    localStorage.setItem(PERMISSIONS_STORAGE_KEY, JSON.stringify(permissions))
  } else {
    localStorage.removeItem(PERMISSIONS_STORAGE_KEY)
  }
}

export function getUserPermissions(): string[] {
  const stored = localStorage.getItem(PERMISSIONS_STORAGE_KEY)
  if (stored) {
    try {
      return JSON.parse(stored)
    } catch {
      return []
    }
  }
  return []
}

export function setUserAllowedChannels(channels: string[]): void {
  if (channels && channels.length > 0) {
    localStorage.setItem(ALLOWED_CHANNELS_STORAGE_KEY, JSON.stringify(channels))
  } else {
    localStorage.removeItem(ALLOWED_CHANNELS_STORAGE_KEY)
  }
}

export function getUserAllowedChannels(): string[] {
  const stored = localStorage.getItem(ALLOWED_CHANNELS_STORAGE_KEY)
  if (stored) {
    try {
      return JSON.parse(stored)
    } catch {
      return []
    }
  }
  return []
}

export function logout(): void {
  setAuthenticated(false)
  setUsername('')
  setUserRole('')
  setUserPermissions([])
  setUserAllowedChannels([])
}

export async function refreshUserSession(): Promise<boolean> {
  const username = getUsername()
  if (!username) return false
  try {
    const result = await fetchUserProfile(username)
    if (result.success) {
      setUserRole(result.role || '')
      setUserPermissions(result.permissions || [])
      setUserAllowedChannels(result.allowed_channels || [])
      return true
    } else {
      logout()
      return false
    }
  } catch (error) {
    console.error('Failed to refresh user session:', error)
    if (axios.isAxiosError(error) && (error.response?.status === 403 || error.response?.status === 404)) {
      logout()
      window.location.reload()
    }
    return false
  }
}
