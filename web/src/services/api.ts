import axios from 'axios'
import { API_ENDPOINTS, BACKEND_BASE_URL, REQUEST_TIMEOUT_MS } from '../config/constants'

export interface BackendSrtItem {
  nameSRT?: string
  port?: number | string
  quality?: string
  status?: string
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
    vmix_recording: boolean
    vmix_streaming: boolean
    vmix_external: boolean
    resolution: string
    SRT?: BackendSrtItem[] | BackendSrtItem
    stream?: BackendStreamItem[] | BackendStreamItem
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

export function getMachineStatisticsId(item: BackendLogItem): string {
  const ip = String(item.data.ip || '').trim()
  const explicitPort = String(item.data.port || '').trim()
  const srtPort = String(normalizeSrtList(item.data.SRT)[0]?.port || '').trim()
  const selectedPort = explicitPort || srtPort

  if (ip || selectedPort) {
    return `${ip}:${selectedPort}`
  }
  return String(item.data.name || '').trim()
}

export interface StatisticsPoint {
  cpu: number | string | null
  ram: number | string | null
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
  samples: number
  cpu_points: number
  ram_points: number
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