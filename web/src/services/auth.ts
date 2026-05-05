import axios from 'axios'
import { loginAccount } from './api'

const AUTH_STORAGE_KEY = 'vmix_monitor_authenticated'
const USERNAME_STORAGE_KEY = 'vmix_monitor_username'

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
    } else {
      setUsername('')
    }
    return {
      success,
      message: result.message,
    }
  } catch (error) {
    setAuthenticated(false)

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

export function logout(): void {
  setAuthenticated(false)
  setUsername('')
}
