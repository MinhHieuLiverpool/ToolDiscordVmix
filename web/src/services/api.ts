import axios from 'axios'
import { API_ENDPOINTS, BACKEND_BASE_URL, REQUEST_TIMEOUT_MS } from '../config/constants'

export interface BackendSrtItem {
  nameSRT?: string
  port?: number | string
  quality?: string
  status?: string
  type?: string
  hostname?: string
  stream_id?: string
  title?: string
}

export interface BackendStreamItem {
  stream?: string
  runtime?: string
  health?: string
  vbit?: string
  size?: string
  abit?: string
  level?: string
  preset?: string
  aformat?: string
  channels?: string
  keyframe?: string
  actual?: number | string
  target?: number | string
  ratio?: string
  speed?: string
  dropped?: number | string
  file?: string
}

export interface BackendStreamKeyItem {
  stream?: string
  url?: string
  key?: string
}

export interface BackendFfmpegItem {
  name?: string
  pid?: number
  send?: number
  recv?: number
}

export interface BackendLogItem {
  timestamp: string
  data: {
    name: string
    ip: string
    ipwan: string
    status?: string
    port?: number | string
    statusapp: number
    ping: number | string | null
    ping_timeouts: number
    cpu?: number | string | null
    temperature?: number | string | null
    memory?: number | string | null
    ram?: number | string | null
    gpu?: number | string | null
    sender_mbps?: number | string | null
    receiver_mbps?: number | string | null
    mac_address?: string
    network_speed?: string
    PIDVMIX?: string | number | null
    vmix_recording: boolean
    vmix_streaming: boolean
    vmix_external: boolean
    resolution: string
    SRT?: BackendSrtItem[] | BackendSrtItem
    stream?: BackendStreamItem[] | BackendStreamItem
    stream_keys?: BackendStreamKeyItem[] | BackendStreamKeyItem
    ffmpeg?: BackendFfmpegItem[] | BackendFfmpegItem
    srt_quality?: string
    srt_off_time?: string
  }
}

export function normalizeSrtList(rawValue: BackendLogItem['data']['SRT']): BackendSrtItem[] {
  if (Array.isArray(rawValue)) {
    return rawValue.filter((item): item is BackendSrtItem => typeof item === 'object' && item !== null)
  }
  if (rawValue && typeof rawValue === 'object') {
    return [rawValue]
  }
  return []
}

export function normalizeStreamList(rawValue: BackendLogItem['data']['stream']): BackendStreamItem[] {
  if (Array.isArray(rawValue)) {
    return rawValue.filter((item): item is BackendStreamItem => typeof item === 'object' && item !== null)
  }
  if (rawValue && typeof rawValue === 'object') {
    return [rawValue]
  }
  return []
}

export function normalizeStreamKeysList(rawValue: BackendLogItem['data']['stream_keys']): BackendStreamKeyItem[] {
  if (Array.isArray(rawValue)) {
    return rawValue.filter((item): item is BackendStreamKeyItem => typeof item === 'object' && item !== null)
  }
  if (rawValue && typeof rawValue === 'object') {
    return [rawValue]
  }
  return []
}

export function normalizeFfmpegList(rawValue: BackendLogItem['data']['ffmpeg']): BackendFfmpegItem[] {
  if (Array.isArray(rawValue)) {
    return rawValue.filter((item): item is BackendFfmpegItem => typeof item === 'object' && item !== null)
  }
  if (rawValue && typeof rawValue === 'object') {
    return [rawValue]
  }
  return []
}

export function getMachineStatisticsId(item: BackendLogItem): string {
  const ip = String(item.data.ip || '').trim()
  const name = String(item.data.name || '').trim()

  if (ip) {
    return `${ip}:${name}`
  }
  return name
}

export interface StatisticsPoint {
  cpu: number | string | null
  ram: number | string | null
  gpu?: number | string | null
  time: string
}

export interface StatisticsResponse {
  id: string
  data: StatisticsPoint[]
  updated_at?: string
}

export interface StatisticHoursPoint {
  window_start: string
  window_end: string
  avg_cpu: number | null
  avg_ram: number | null
  avg_gpu?: number | null
  samples: number
  cpu_points: number
  ram_points: number
  gpu_points?: number
  calculated_at: string
}

export interface StatisticHoursResponse {
  id: string
  data: StatisticHoursPoint[]
  updated_at?: string
}

export interface LoginResponse {
  success: boolean
  username?: string
  message?: string
  role?: string
  permissions?: string[]
}

export interface BackendAccountItem {
  username?: string
  password?: string
  created_at?: string
  email?: string
  phone?: string
  is_locked?: boolean
  role?: string
}

export interface BackendRoleItem {
  role_key: string
  name: string
  description: string
  permissions: string[]
  created_at?: string
}

export interface SpeedtestResponse {
  success: boolean
  timestamp?: string
  ping_ms?: number | null
  download_bps?: number | null
  upload_bps?: number | null
  download_mbps?: number | null
  upload_mbps?: number | null
  ipwan?: string | null
  isp?: string | null
  server?: Record<string, unknown>
  raw?: {
    client?: {
      ip?: string
      isp?: string
      isp_name?: string
      ispName?: string
    }
  }
  message?: string
  error?: string
}

const apiClient = axios.create({
  baseURL: BACKEND_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
})

export async function fetchAllLogs(): Promise<BackendLogItem[]> {
  const response = await apiClient.get<BackendLogItem[]>(API_ENDPOINTS.logs)
  return response.data
}

export async function loginAccount(username: string, password: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>(API_ENDPOINTS.login, { username, password })
  return response.data
}

export async function fetchAccounts(): Promise<BackendAccountItem[]> {
  const response = await apiClient.get<BackendAccountItem[]>(API_ENDPOINTS.accounts)
  return response.data
}

export async function createAccount(payload: {
  username: string
  password?: string
  email?: string
  phone?: string
  role?: string
}): Promise<{ success: boolean; username?: string; message?: string }> {
  const response = await apiClient.post('/create_account', payload)
  return response.data
}

export async function updateAccount(payload: {
  username: string
  password?: string
  email?: string
  phone?: string
  is_locked?: boolean
  role?: string
}): Promise<{ success: boolean; username?: string; message?: string }> {
  const response = await apiClient.post('/update_account', payload)
  return response.data
}

export async function deleteAccount(username: string): Promise<{ success: boolean; deleted?: number; message?: string }> {
  const response = await apiClient.post('/delete_account', { username })
  return response.data
}

export async function fetchRoles(): Promise<BackendRoleItem[]> {
  const response = await apiClient.get<BackendRoleItem[]>('/roles')
  return response.data
}

export async function createRole(payload: {
  role_key: string
  name: string
  description: string
  permissions: string[]
}): Promise<{ success: boolean; role_key?: string; message?: string }> {
  const response = await apiClient.post('/create_role', payload)
  return response.data
}

export async function updateRole(payload: {
  role_key: string
  name?: string
  description?: string
  permissions?: string[]
}): Promise<{ success: boolean; role_key?: string; message?: string }> {
  const response = await apiClient.post('/update_role', payload)
  return response.data
}

export async function deleteRole(role_key: string): Promise<{ success: boolean; deleted?: number; message?: string }> {
  const response = await apiClient.post('/delete_role', { role_key })
  return response.data
}

export async function fetchSpeedtest(): Promise<SpeedtestResponse> {
  const response = await apiClient.get<SpeedtestResponse>(API_ENDPOINTS.speedtest)
  return response.data
}

export async function fetchStatistics(statisticsId: string, limit = 60): Promise<StatisticsResponse> {
  const response = await apiClient.get<StatisticsResponse>(
    `${API_ENDPOINTS.statistics}/${encodeURIComponent(statisticsId)}`,
    { params: { limit } },
  )
  return response.data
}

export async function fetchAllStatisticHours(): Promise<StatisticHoursResponse[]> {
  const response = await apiClient.get<StatisticHoursResponse[]>(API_ENDPOINTS.statisticHours)
  return response.data
}

export async function fetchStatisticHours(statisticsId: string): Promise<StatisticHoursResponse> {
  const response = await apiClient.get<StatisticHoursResponse>(
    `${API_ENDPOINTS.statisticHours}/${encodeURIComponent(statisticsId)}`,
  )
  return response.data
}