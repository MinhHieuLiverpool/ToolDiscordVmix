import axios from 'axios'
import { API_ENDPOINTS, BACKEND_BASE_URL, REQUEST_TIMEOUT_MS } from '../config/constants'

export interface BackendSrtItem {
  nameSRT?: string
  name?: string
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

export interface RecordItem {
  profile: string
  filename: string
  format: string
  resolution: string
  fps: string
  v_bitrate: string
  a_bitrate: string
  audio_delay: string
  hw_accel?: string
  audio_enabled?: string
  audio_channel?: string
  source_channel?: string
  fragmented?: string
}

export interface MultiRecordItem {
  source: string
  status: string
  folder: string
  format: string
  v_bitrate: string
  a_bitrate: string
  audio_src?: string
  interval?: string
  show_all?: string
}

export interface BackendLogItem {
  timestamp: string
  data: {
    name: string
    name_edit?: string
    ip: string
    ipwan: string
    status?: string
    port?: number | string
    statusapp: number
    ping: number | string | null
    ping_isp?: number | string | null
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
    vmix_multicorder?: boolean
    MultirecordingStatus?: boolean
    List_REcord?: RecordItem[]
    ListMultiREcord?: MultiRecordItem[]
    ListMultiRecord?: MultiRecordItem[]
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

export function normalizeRecordList(rawValue: unknown): RecordItem[] {
  let parsed = rawValue
  if (typeof rawValue === 'string') {
    try {
      parsed = JSON.parse(rawValue)
    } catch (e) {
      console.error('Failed to parse List_REcord JSON string:', e)
    }
  }
  if (Array.isArray(parsed)) {
    return parsed.filter((item): item is RecordItem => typeof item === 'object' && item !== null)
  }
  return []
}

export function normalizeMultiRecordList(rawValue: unknown): MultiRecordItem[] {
  let parsed = rawValue
  if (typeof rawValue === 'string') {
    try {
      parsed = JSON.parse(rawValue)
    } catch (e) {
      console.error('Failed to parse ListMultiREcord JSON string:', e)
    }
  }
  if (Array.isArray(parsed)) {
    return parsed.filter((item): item is MultiRecordItem => typeof item === 'object' && item !== null)
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
  allowed_channels?: string[]
}

export interface BackendAccountItem {
  username?: string
  password?: string
  created_at?: string
  email?: string
  phone?: string
  is_locked?: boolean
  role?: string
  allowed_channels?: string[]
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

export async function fetchUserProfile(username: string): Promise<LoginResponse> {
  const response = await apiClient.get<LoginResponse>(`/user_profile/${encodeURIComponent(username)}`)
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
  allowed_channels?: string[]
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
  allowed_channels?: string[]
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

export interface BandwidthHistoryItem {
  timestamp: string
  sender: number
  receiver: number
}

export interface BandwidthDoc {
  ipwan: string
  date: string
  sender_max: number
  receiver_max: number
  sender_min?: number
  receiver_min?: number
  last_updated: string
  history: BandwidthHistoryItem[]
}

export async function fetchBandwidthStats(date?: string): Promise<BandwidthDoc[]> {
  const response = await apiClient.get<BandwidthDoc[]>('/bandwidth', {
    params: { date }
  })
  return response.data
}

export async function updateNameEdit(name: string, nameEdit: string): Promise<{ success: boolean; message?: string }> {
  const response = await apiClient.post<{ success: boolean; message?: string }>('/update_name_edit', { name, name_edit: nameEdit })
  return response.data
}

export interface GameSelectedResponse {
  game: string
  machines: string[]
  visible_status?: 'ON' | 'OFF'
  hidden_machines?: string[]
  machine_labels?: Record<string, string>
}

export async function fetchGameSelected(): Promise<GameSelectedResponse[]> {
  const response = await apiClient.get<GameSelectedResponse[]>('/load_game_selected')
  return response.data
}

export async function saveGameSelected(game: string, machines: string[], visibleStatus?: 'ON' | 'OFF'): Promise<{ success: boolean; message?: string }> {
  const response = await apiClient.post<{ success: boolean; message?: string }>('/save_game_selected', { game, machines, visible_status: visibleStatus })
  return response.data
}

export async function deleteGameSelected(game: string): Promise<{ success: boolean; message?: string }> {
  const response = await apiClient.post<{ success: boolean; message?: string }>('/delete_game_selected', { game })
  return response.data
}

export async function toggleVisibleStatus(game: string, visibleStatus: 'ON' | 'OFF'): Promise<{ success: boolean; message?: string }> {
  const response = await apiClient.post<{ success: boolean; message?: string }>('/toggle_visible_status', { game, visible_status: visibleStatus })
  return response.data
}

export async function toggleMachineVisibility(game: string, machine: string, hidden: boolean): Promise<{ success: boolean; message?: string }> {
  const response = await apiClient.post<{ success: boolean; message?: string }>('/toggle_machine_visibility', { game, machine, hidden })
  return response.data
}


export interface SharedWebConfig {
  uuid: string
  allowed_features: string[]
  allowed_machines: string[]
  selected_game?: string
  share_type?: 'game' | 'machines'
  created_at: string
}

export interface SharedWebConfigResponse {
  success: boolean
  data?: SharedWebConfig
  message?: string
}

export async function createSharedWebConfig(allowedFeatures: string[], allowedMachines: string[], selectedGame?: string, shareType?: 'game' | 'machines'): Promise<{ success: boolean; uuid?: string; message?: string }> {
  const response = await apiClient.post<{ success: boolean; uuid?: string; message?: string }>('/create_shared_web', {
    allowed_features: allowedFeatures,
    allowed_machines: allowedMachines,
    selected_game: selectedGame || '__all__',
    share_type: shareType || 'machines'
  })
  return response.data
}

export async function fetchSharedWebConfig(uuid: string): Promise<SharedWebConfigResponse> {
  const response = await apiClient.get<SharedWebConfigResponse>(`/shared_web_config/${encodeURIComponent(uuid)}`)
  return response.data
}

export async function listSharedWebConfigs(): Promise<SharedWebConfig[]> {
  const response = await apiClient.get<SharedWebConfig[]>('/list_shared_web')
  return response.data
}

export async function deleteSharedWebConfig(uuid: string): Promise<{ success: boolean; message?: string }> {
  const response = await apiClient.delete<{ success: boolean; message?: string }>(`/delete_shared_web/${encodeURIComponent(uuid)}`)
  return response.data
}

export async function updateSharedWebConfig(uuid: string, allowedFeatures: string[], allowedMachines: string[], selectedGame?: string, shareType?: 'game' | 'machines'): Promise<{ success: boolean; message?: string }> {
  const response = await apiClient.post<{ success: boolean; message?: string }>(`/update_shared_web/${encodeURIComponent(uuid)}`, {
    allowed_features: allowedFeatures,
    allowed_machines: allowedMachines,
    selected_game: selectedGame || '__all__',
    share_type: shareType || 'machines'
  })
  return response.data
}

export async function fetchDbDebugLogs(): Promise<any[]> {
  const response = await apiClient.get<any[]>('/load_debug_logs')
  return response.data
}

export function getDownloadDebugLogsUrl(timeStart?: string, timeEnd?: string): string {
  const params = new URLSearchParams()
  if (timeStart) params.append('timeStart', timeStart)
  if (timeEnd) params.append('timeEnd', timeEnd)
  const queryString = params.toString()
  return `${BACKEND_BASE_URL}/download_debug_logs${queryString ? '?' + queryString : ''}`
}

