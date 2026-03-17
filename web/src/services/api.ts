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

const apiClient = axios.create({
  baseURL: BACKEND_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
})

export async function fetchAllLogs(): Promise<BackendLogItem[]> {
  const response = await apiClient.get<BackendLogItem[]>(API_ENDPOINTS.logs)
  return response.data
}