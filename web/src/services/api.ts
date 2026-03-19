import axios from 'axios'
import { API_ENDPOINTS, BACKEND_BASE_URL, REQUEST_TIMEOUT_MS } from '../config/constants'

export interface BackendLogItem {
  timestamp: string
  data: {
    name: string
    ip: string
    ipwan: string
    status: string
    port: number | string
    statusapp: number
    ping: number | string | null
    ping_timeouts: number
    cpu: number | string | null
    memory: number | string | null
    vmix_recording: boolean
    vmix_streaming: boolean
    vmix_external: boolean
    resolution: string
    srt_quality: string
    srt_off_time?: string
  }
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

const apiClient = axios.create({
  baseURL: BACKEND_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
})

export async function fetchAllLogs(): Promise<BackendLogItem[]> {
  const response = await apiClient.get<BackendLogItem[]>(API_ENDPOINTS.logs)
  return response.data
}

export async function fetchStatistics(statisticsId: string, limit = 200): Promise<StatisticsResponse> {
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