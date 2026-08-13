import { useEffect, useState, useMemo } from 'react'
import axios from 'axios'
import { showToast } from '../components/ui/Toast'
import { BACKEND_BASE_URL } from '../config/constants'
import { useDashboardContext } from '../hooks/useDashboardContext'
import { normalizeSrtList } from '../services/api'
import { hasActionPermission } from '../services/auth'

const MODULE_KEY = 'Notification'

interface RuleCondition {
  parameter: string
  operator: string
  value: string
  enabled: boolean
  alert_cooldown?: number
}

interface WebhookItem {
  id: string
  name: string
  type: 'Discord' | 'Seatalk'
  url: string
  enabled: boolean
  statusnotification?: number
  devices: string[]
  rules: RuleCondition[]
  alert_cooldown?: number
  srt_auto_send?: boolean
  srt_streams?: string[]
}

interface DeviceOption {
  id: string
  name: string
  type: 'desktop' | 'mobile'
}

// Available standard parameters to choose/tick
const DEFAULT_PARAMETERS = [
  { parameter: 'isOnline', label: 'Đổi trạng thái kết nối (ON/OFF)', operator: '=', defaultValue: 'off' },
  { parameter: 'temperature', label: 'Nhiệt độ CPU/Pin quá cao (°C)', operator: '>', defaultValue: '45' },
  { parameter: 'cpuLoad', label: 'Tải CPU quá cao (%)', operator: '>', defaultValue: '85' },
  { parameter: 'memory', label: 'Sử dụng RAM quá cao (%)', operator: '>', defaultValue: '90' },
  { parameter: 'gpu', label: 'Sử dụng GPU quá cao (Desktop %)', operator: '>', defaultValue: '90' },
  { parameter: 'fps', label: 'Khung hình FPS quá thấp (Mobile)', operator: '<', defaultValue: '40' },
  { parameter: 'packetLoss', label: 'Mất gói Packet Loss quá cao (Mobile %)', operator: '>', defaultValue: '5' },
  { parameter: 'networkChange', label: 'Đổi loại mạng (Mobile: LAN/WiFi/4G)', operator: '=', defaultValue: 'any' },
  { parameter: 'status', label: 'Trạng thái luồng SRT bị ngắt (OFF)', operator: '=', defaultValue: 'OFF' },
  { parameter: 'stream_health', label: 'Stream Health cảnh báo (VÀNG)', operator: '=', defaultValue: 'VÀNG' },
  { parameter: 'stream_dropped', label: 'Stream Source Drop quá cao (frames)', operator: '>', defaultValue: '100' },
  { parameter: 'vmix_recording', label: 'Dừng Ghi hình vMix (Record OFF)', operator: '=', defaultValue: 'False' },
  { parameter: 'vmix_streaming', label: 'Dừng Phát sóng vMix (Stream OFF)', operator: '=', defaultValue: 'False' },
  { parameter: 'vmix_external', label: 'Tắt External Output vMix', operator: '=', defaultValue: 'False' },
  { parameter: 'vmix_multicorder', label: 'Tắt MultiCorder vMix', operator: '=', defaultValue: 'False' },
]

// State-transition parameters use a single dropdown instead of operator + value.
const ONLINE_TRANSITIONS = [
  { value: 'off', label: 'ON → OFF (mất kết nối)' },
  { value: 'on', label: 'OFF → ON (kết nối lại)' },
  { value: 'any', label: 'Cả hai chiều (ON ↔ OFF)' },
]

// Map legacy stored isOnline values to the new transition tokens.
function normalizeOnlineValue(v: string): string {
  const t = String(v || '').trim().toLowerCase()
  if (t === 'on' || t === 'true' || t === 'online' || t === 'to_on') return 'on'
  if (t === 'any' || t === 'both' || t === 'change') return 'any'
  return 'off'
}

const NETWORK_TRANSITIONS = [
  { value: 'any', label: 'Bất kỳ thay đổi nào' },
  { value: 'lan>wifi', label: 'LAN → WiFi' },
  { value: 'lan>mobile', label: 'LAN → Mạng di động' },
  { value: 'wifi>lan', label: 'WiFi → LAN' },
  { value: 'wifi>mobile', label: 'WiFi → Mạng di động' },
  { value: 'mobile>lan', label: 'Mạng di động → LAN' },
  { value: 'mobile>wifi', label: 'Mạng di động → WiFi' },
]

export default function NotificationPage() {
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([])
  const [devices, setDevices] = useState<DeviceOption[]>([])
  const [loading, setLoading] = useState(true)

  const canAdd = hasActionPermission(MODULE_KEY, 'add')
  const canEdit = hasActionPermission(MODULE_KEY, 'edit')
  const canDelete = hasActionPermission(MODULE_KEY, 'delete')
  const canToggle = hasActionPermission(MODULE_KEY, 'toggle')

  // Webhook Modal / Form states
  const [modalOpen, setModalOpen] = useState(false)
  const [editingWebhook, setEditingWebhook] = useState<WebhookItem | null>(null)
  
  const [whName, setWhName] = useState('')
  const [whType, setWhType] = useState<'Discord' | 'Seatalk'>('Discord')
  const [whUrl, setWhUrl] = useState('')
  const [whEnabled, setWhEnabled] = useState(true)
  const [whDevices, setWhDevices] = useState<string[]>(['all'])
  // Device targeting mode: all devices / individually picked / by channel
  const [deviceMode, setDeviceMode] = useState<'all' | 'devices' | 'channels'>('all')
  const [whChannels, setWhChannels] = useState<string[]>([])
  
  // Rule checkboxes/values state in Form
  const [ruleStates, setRuleStates] = useState<Record<string, { enabled: boolean; operator: string; value: string; alert_cooldown: number }>>({})

  // SRT states in Form
  const [whSrtAutoSend, setWhSrtAutoSend] = useState(false)
  const [whSrtStreams, setWhSrtStreams] = useState<string[]>(['all'])

  // SRT trigger states
  const [sendingSrt, setSendingSrt] = useState(false)

  const { rows, gameAssignments } = useDashboardContext()

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [whRes, devRes] = await Promise.all([
        axios.get(`${BACKEND_BASE_URL}/api/notifications/webhooks`),
        axios.get(`${BACKEND_BASE_URL}/api/notifications/devices`)
      ])
      
      if (whRes.data.status === 'success') setWebhooks(whRes.data.data)
      if (devRes.data.status === 'success') setDevices(devRes.data.data)
    } catch (err: any) {
      console.error(err)
      showToast('Lỗi tải dữ liệu cấu hình thông báo!', 'error')
    } finally {
      setLoading(false)
    }
  }

  // --- Webhook Actions ---
  const handleOpenModal = (wh: WebhookItem | null = null) => {
    const initialRuleStates: Record<string, { enabled: boolean; operator: string; value: string; alert_cooldown: number }> = {}
    DEFAULT_PARAMETERS.forEach(p => {
      initialRuleStates[p.parameter] = {
        enabled: false,
        operator: p.operator,
        value: p.defaultValue,
        alert_cooldown: 60
      }
    })

    if (wh) {
      setEditingWebhook(wh)
      setWhName(wh.name)
      setWhType(wh.type)
      setWhUrl(wh.url)
      setWhEnabled(wh.statusnotification !== 0)
      const devs = wh.devices && wh.devices.length ? wh.devices : ['all']
      if (devs.includes('all')) {
        setDeviceMode('all')
        setWhDevices(['all'])
        setWhChannels([])
      } else if (devs.some(d => typeof d === 'string' && d.startsWith('channel:'))) {
        setDeviceMode('channels')
        setWhChannels(devs.filter(d => d.startsWith('channel:')).map(d => d.slice('channel:'.length)))
        setWhDevices([])
      } else {
        setDeviceMode('devices')
        setWhDevices(devs)
        setWhChannels([])
      }
      setWhSrtAutoSend(!!wh.srt_auto_send)
      setWhSrtStreams(wh.srt_streams || ['all'])
      
      if (wh.rules && Array.isArray(wh.rules)) {
        wh.rules.forEach(r => {
          if (initialRuleStates[r.parameter]) {
            initialRuleStates[r.parameter] = {
              enabled: r.enabled,
              operator: r.operator,
              value: r.value,
              alert_cooldown: r.alert_cooldown ?? 60
            }
          }
        })
      }
    } else {
      setEditingWebhook(null)
      setWhName('')
      setWhType('Discord')
      setWhUrl('')
      setWhEnabled(true)
      setWhDevices(['all'])
      setDeviceMode('all')
      setWhChannels([])
      setWhSrtAutoSend(false)
      setWhSrtStreams(['all'])
    }
    
    setRuleStates(initialRuleStates)
    setModalOpen(true)
  }

  const handleSaveWebhook = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!whName.trim() || !whUrl.trim()) {
      showToast('Vui lòng nhập Tên kênh và Đường dẫn Webhook!', 'error')
      return
    }

    let devicesPayload: string[]
    if (deviceMode === 'all') {
      devicesPayload = ['all']
    } else if (deviceMode === 'channels') {
      if (whChannels.length === 0) {
        showToast('Vui lòng chọn ít nhất một kênh!', 'error')
        return
      }
      devicesPayload = whChannels.map(g => `channel:${g}`)
    } else {
      const picked = whDevices.filter(d => d !== 'all')
      if (picked.length === 0) {
        showToast('Vui lòng chọn ít nhất một thiết bị!', 'error')
        return
      }
      devicesPayload = picked
    }

    const assembledRules: RuleCondition[] = DEFAULT_PARAMETERS.map(p => {
      const state = ruleStates[p.parameter]
      return {
        parameter: p.parameter,
        operator: state?.operator || p.operator,
        value: state?.value || p.defaultValue,
        enabled: !!state?.enabled,
        alert_cooldown: state?.alert_cooldown !== undefined ? Math.max(10, parseInt(String(state.alert_cooldown)) || 60) : 60
      }
    })

    try {
      const payload = {
        id: editingWebhook?.id,
        name: whName,
        type: whType,
        url: whUrl,
        enabled: whEnabled,
        statusnotification: whEnabled ? 1 : 0,
        devices: devicesPayload,
        rules: assembledRules,
        alert_cooldown: 60,
        srt_auto_send: whSrtAutoSend,
        srt_streams: whSrtStreams
      }
      
      const response = await axios.post(`${BACKEND_BASE_URL}/api/notifications/webhooks`, payload)
      if (response.data.status === 'success') {
        showToast(editingWebhook ? 'Cập nhật Webhook thành công!' : 'Thêm Webhook mới thành công!', 'success')
        setModalOpen(false)
        fetchData()
      }
    } catch (err: any) {
      showToast('Lỗi lưu cấu hình Webhook!', 'error')
    }
  }

  const handleDeleteWebhook = async (id: string) => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa kênh Webhook này?')) return
    try {
      const response = await axios.delete(`${BACKEND_BASE_URL}/api/notifications/webhooks/${id}`)
      if (response.data.status === 'success') {
        showToast('Đã xóa kênh Webhook thành công!', 'success')
        fetchData()
      }
    } catch (err) {
      showToast('Lỗi khi xóa Webhook!', 'error')
    }
  }

  const handleToggleWebhookEnabled = async (wh: WebhookItem) => {
    try {
      const response = await axios.post(`${BACKEND_BASE_URL}/api/notifications/webhooks/toggle-status`, {
        webhook_id: wh.id
      })
      if (response.data.status === 'success') {
        const newStatus = response.data.statusnotification
        const srtNote = response.data.srt_sent ? ' (đã gửi báo cáo SRT)' : ''
        showToast(`Đã ${newStatus === 1 ? 'bật' : 'tắt'} kênh Webhook thành công!${srtNote}`, 'success')
        fetchData()
      }
    } catch (err) {
      showToast('Lỗi thay đổi trạng thái Webhook!', 'error')
    }
  }

  const handleEnableAllWebhooks = async () => {
    try {
      const res = await axios.post(`${BACKEND_BASE_URL}/api/notifications/webhooks/enable-all`)
      if (res.data.status === 'success') {
        showToast(res.data.message || 'Đã bật tất cả kênh Webhook!', 'success')
        fetchData()
      }
    } catch (err) {
      showToast('Lỗi bật tất cả Webhook!', 'error')
    }
  }

  const handleDeviceSelect = (devId: string) => {
    if (devId === 'all') {
      if (whDevices.includes('all')) {
        setWhDevices([])
      } else {
        setWhDevices(['all'])
      }
      return
    }
    
    let updated = [...whDevices].filter(d => d !== 'all')
    if (updated.includes(devId)) {
      updated = updated.filter(d => d !== devId)
    } else {
      updated.push(devId)
    }
    setWhDevices(updated)
  }

  const handleChannelToggle = (game: string) => {
    setWhChannels(prev => (prev.includes(game) ? prev.filter(g => g !== game) : [...prev, game]))
  }

  const handleRuleCheckToggle = (parameter: string) => {
    setRuleStates(prev => ({
      ...prev,
      [parameter]: {
        ...prev[parameter],
        enabled: !prev[parameter]?.enabled
      }
    }))
  }

  const handleRuleStateChange = (parameter: string, field: 'operator' | 'value' | 'alert_cooldown', val: any) => {
    setRuleStates(prev => ({
      ...prev,
      [parameter]: {
        ...prev[parameter],
        [field]: val
      }
    }))
  }

  // --- SRT Tab Actions ---
  const handleSrtStreamSelect = (srtId: string) => {
    if (srtId === 'all') {
      if (whSrtStreams.includes('all')) {
        setWhSrtStreams([])
      } else {
        setWhSrtStreams(['all'])
      }
      return
    }
    
    let updated = [...whSrtStreams].filter(s => s !== 'all')
    if (updated.includes(srtId)) {
      updated = updated.filter(s => s !== srtId)
    } else {
      updated.push(srtId)
    }
    setWhSrtStreams(updated)
  }

  const handleSendAllSrtNow = async () => {
    setSendingSrt(true)
    try {
      const res = await axios.post(`${BACKEND_BASE_URL}/api/notifications/srt-settings/send-all`)
      if (res.data.status === 'success') {
        showToast(res.data.message || 'Đã gửi báo cáo SRT thành công!', 'success')
      }
    } catch (err: any) {
      showToast(err.response?.data?.message || 'Lỗi gửi danh sách SRT!', 'error')
    } finally {
      setSendingSrt(false)
    }
  }

  const allAvailableSrts = useMemo(() => {
    const list: { machineName: string; name: string; port: string; id: string; hostname: string; type: string }[] = []
    if (!rows || !Array.isArray(rows)) return list
    rows.forEach(row => {
      const machineName = row.data?.name || 'Unknown'
      const srtList = normalizeSrtList(row.data?.SRT)
      srtList.forEach(srt => {
        const srtNameDisplay = srt.nameSRT || srt.name || '-'
        const srtNameForId = srt.nameSRT || srt.name || ''
        const port = String(srt.port || '')
        const hostname = srt.hostname || row.data?.ipwan || row.data?.ip || '-'
        const type = srt.type || '-'
        if (port) {
          const id = `${machineName}/${srtNameForId}:${port}`
          if (!list.some(item => item.id === id)) {
            list.push({
              machineName,
              name: srtNameDisplay,
              port,
              id,
              hostname,
              type
            })
          }
        }
      })
    })
    return list
  }, [rows])

  return (
    <div className="p-6 text-slate-800 dark:text-slate-100 min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-200 dark:border-slate-800 gap-4">
        <div>
          <h1 className="text-2xl font-black text-rose-600 dark:text-rose-500 uppercase tracking-wider flex items-center gap-2">
            🔔 Kênh Thông Báo & Cảnh Báo
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Thiết lập các liên kết Webhook (Discord / Seatalk), chỉ định các thiết bị cần theo dõi và tick chọn các điều kiện cảnh báo chi tiết.
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleSendAllSrtNow}
            disabled={sendingSrt}
            className="px-4 py-2.5 text-xs font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/20 hover:bg-indigo-100 dark:hover:bg-indigo-900/35 border border-indigo-100 dark:border-indigo-900/30 rounded-[10px] transition-all disabled:opacity-50 flex items-center gap-1.5"
          >
            {sendingSrt ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-slate-300 border-t-indigo-600 rounded-full animate-spin"></div>
                Đang gửi SRT...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                Báo cáo SRT ngay
              </>
            )}
          </button>
          {canToggle && (
            <button
              onClick={handleEnableAllWebhooks}
              className="px-4 py-2.5 text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/20 hover:bg-emerald-100 dark:hover:bg-emerald-900/35 border border-emerald-100 dark:border-emerald-900/30 rounded-[10px] transition-all flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Bật tất cả kênh
            </button>
          )}
          {canAdd && (
            <button
              onClick={() => handleOpenModal()}
              className="px-4 py-2.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-[10px] shadow-sm transition-all flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Tạo kênh thông báo mới
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-8 h-8 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin mb-3"></div>
          <span className="text-xs font-bold text-slate-400">Đang tải cấu hình thông báo...</span>
        </div>
      ) : (
        <>
        {webhooks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 bg-white dark:bg-slate-900/30 border border-slate-200 dark:border-slate-900 rounded-[12px] p-6 text-center mt-6">
            <svg className="w-12 h-12 text-slate-300 dark:text-slate-700 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9z" />
            </svg>
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">Chưa có kênh thông báo nào</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">
              Tạo một kênh liên kết Webhook đến Discord hoặc SeaTalk và cấu hình các rule giám sát đi kèm.
            </p>
          </div>
        ) : (
          <div className="bg-white dark:bg-slate-900/40 rounded-[12px] border border-slate-200 dark:border-slate-800/80 overflow-hidden shadow-sm mt-6">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-3 px-5">Tên kênh & Nền tảng</th>
                    <th className="py-3 px-5">Thiết bị áp dụng</th>
                    <th className="py-3 px-5">Điều kiện cảnh báo</th>
                    <th className="py-3 px-5 w-28 text-center">Hoạt động</th>
                    <th className="py-3 px-5 w-28 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-900">
                  {webhooks.map((wh) => {
                    const activeRulesCount = (wh.rules || []).filter(r => r.enabled).length;
                    return (
                      <tr key={wh.id} className="text-xs hover:bg-slate-50/50 dark:hover:bg-slate-900/10 transition-all">
                        <td className="py-3.5 px-5">
                          <div className="flex flex-col gap-1">
                            <div className="flex items-center gap-2">
                              <span className="font-black text-slate-800 dark:text-slate-200 text-sm">
                                {wh.name}
                              </span>
                              <span className={`px-2 py-0.5 rounded-[4px] text-[10px] font-bold leading-none ${
                                wh.type === 'Discord'
                                  ? 'bg-blue-50 text-blue-500 border border-blue-100 dark:bg-blue-950/20 dark:border-blue-900/30'
                                  : 'bg-indigo-50 text-indigo-500 border border-indigo-100 dark:bg-indigo-950/20 dark:border-indigo-900/30'
                              }`}>
                                {wh.type}
                              </span>
                            </div>
                            <span className="text-[10px] font-mono text-slate-400 max-w-xs truncate" title={wh.url}>
                              {wh.url}
                            </span>
                          </div>
                        </td>
                        
                        <td className="py-3.5 px-5">
                          <div className="flex flex-wrap gap-1 max-w-xs">
                            {wh.devices?.includes('all') ? (
                              <span className="text-[10px] px-1.5 py-0.5 bg-indigo-50 dark:bg-indigo-950/25 text-indigo-600 dark:text-indigo-400 rounded font-bold border border-indigo-100 dark:border-indigo-900/30">
                                Tất cả thiết bị
                              </span>
                            ) : wh.devices?.length ? (
                              wh.devices.map(dId => {
                                if (typeof dId === 'string' && dId.startsWith('channel:')) {
                                  const gameName = dId.slice('channel:'.length)
                                  return (
                                    <span key={dId} className="text-[9.5px] px-1.5 py-0.5 bg-purple-50 dark:bg-purple-950/25 text-purple-600 dark:text-purple-400 rounded font-bold border border-purple-100 dark:border-purple-900/30">
                                      📺 {gameName}
                                    </span>
                                  )
                                }
                                const dev = devices.find(d => d.id === dId)
                                return (
                                  <span key={dId} className="text-[9.5px] px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded border border-slate-200/50 dark:border-slate-700/50">
                                    {dev ? dev.name : dId}
                                  </span>
                                )
                              })
                            ) : (
                              <span className="text-[10px] text-slate-400 italic">Không áp dụng</span>
                            )}
                          </div>
                        </td>

                        <td className="py-3.5 px-5">
                          <div className="flex flex-wrap gap-1 max-w-sm">
                            {wh.rules && Array.isArray(wh.rules) && activeRulesCount > 0 ? (
                              wh.rules.filter(r => r.enabled).map(r => {
                                const matchingParam = DEFAULT_PARAMETERS.find(dp => dp.parameter === r.parameter);
                                return (
                                  <span
                                    key={r.parameter}
                                    className="text-[10px] px-1.5 py-0.5 bg-rose-50 dark:bg-rose-950/15 text-rose-600 dark:text-rose-400 rounded font-mono font-bold border border-rose-100 dark:border-rose-900/25 mr-1 mb-1 inline-block"
                                    title={matchingParam?.label}
                                  >
                                    📌 {r.parameter} {r.operator} {r.value}
                                  </span>
                                )
                              })
                            ) : (
                              <span className="text-[10px] text-slate-400 italic">Không có điều kiện nào</span>
                            )}
                          </div>
                        </td>

                        <td className="py-3.5 px-5 text-center">
                          <button
                            onClick={() => canToggle && handleToggleWebhookEnabled(wh)}
                            disabled={!canToggle}
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-[6px] text-[11px] font-bold transition-all ${!canToggle ? 'cursor-not-allowed opacity-70' : ''} ${
                              wh.statusnotification !== 0
                                ? 'bg-emerald-50 text-emerald-600 border border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-900/30'
                                : 'bg-slate-100 text-slate-400 border border-slate-200 dark:bg-slate-800/40 dark:border-slate-800'
                            }`}
                            title={!canToggle ? 'Bạn không có quyền bật/tắt kênh' : (wh.statusnotification !== 0 ? 'Tạm tắt kênh' : 'Bật kênh')}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${wh.statusnotification !== 0 ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                            {wh.statusnotification !== 0 ? 'Bật' : 'Tắt'}
                          </button>
                        </td>

                        <td className="py-3.5 px-5 text-right">
                          <div className="flex gap-2 justify-end">
                            {canEdit && (
                              <button
                                onClick={() => handleOpenModal(wh)}
                                className="text-slate-400 hover:text-sky-500 transition-colors p-1"
                                title="Sửa cấu hình & Rule"
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                              </button>
                            )}
                            {canDelete && (
                              <button
                                onClick={() => handleDeleteWebhook(wh.id)}
                                className="text-slate-400 hover:text-rose-500 transition-colors p-1"
                                title="Xóa kênh"
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            )}
                            {!canEdit && !canDelete && (
                              <span className="text-[11px] text-slate-400 italic">—</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </>
      )}

      {/* Webhook and Rules Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
          <div className="w-full max-w-4xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-[16px] shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-900/50">
              <h3 className="text-sm font-black text-rose-600 dark:text-rose-500 uppercase tracking-wide">
                {editingWebhook ? '✏️ Cập nhật Kênh Thông Báo' : '➕ Thêm Kênh Thông Báo Mới'}
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <form onSubmit={handleSaveWebhook}>
              <div className="p-6 space-y-5 text-xs overflow-y-auto max-h-[70vh]">
                
                {/* Basic info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block font-bold text-slate-500 uppercase mb-1.5">Tên kênh hiển thị</label>
                    <input
                      type="text"
                      required
                      value={whName}
                      onChange={(e) => setWhName(e.target.value)}
                      className="w-full px-3 py-2 border rounded-[10px] border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-indigo-500 text-xs font-semibold"
                      placeholder="VD: Discord Minh Hieu, SeaTalk Nhóm Kỹ Thuật..."
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-slate-500 uppercase mb-1.5">Nền tảng</label>
                    <div className="flex gap-4 mt-2.5">
                      <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700 dark:text-slate-300">
                        <input
                          type="radio"
                          name="webhook_platform"
                          value="Discord"
                          checked={whType === 'Discord'}
                          onChange={() => setWhType('Discord')}
                          className="text-indigo-600 focus:ring-indigo-500"
                        />
                        Discord
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700 dark:text-slate-300">
                        <input
                          type="radio"
                          name="webhook_platform"
                          value="Seatalk"
                          checked={whType === 'Seatalk'}
                          onChange={() => setWhType('Seatalk')}
                          className="text-indigo-600 focus:ring-indigo-500"
                        />
                        SeaTalk
                      </label>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-slate-500 uppercase mb-1.5">Đường dẫn Webhook URL</label>
                  <input
                    type="url"
                    required
                    value={whUrl}
                    onChange={(e) => setWhUrl(e.target.value)}
                    className="w-full px-3 py-2 border rounded-[10px] border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-indigo-500 text-xs font-mono"
                    placeholder="https://discord.com/api/webhooks/... hoặc https://openapi.seatalk.io/..."
                  />
                </div>

                {/* Apply Devices Section */}
                <div>
                  <label className="block font-bold text-slate-500 uppercase mb-1.5">Phạm vi áp dụng cho Webhook này</label>

                  {/* Mode selector: 1 of 3 */}
                  <div className="flex flex-wrap gap-4 mb-3">
                    <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700 dark:text-slate-300">
                      <input
                        type="radio"
                        name="device_mode"
                        checked={deviceMode === 'all'}
                        onChange={() => setDeviceMode('all')}
                        className="text-indigo-600 focus:ring-indigo-500"
                      />
                      Tất cả thiết bị
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700 dark:text-slate-300">
                      <input
                        type="radio"
                        name="device_mode"
                        checked={deviceMode === 'devices'}
                        onChange={() => setDeviceMode('devices')}
                        className="text-indigo-600 focus:ring-indigo-500"
                      />
                      Chọn từng thiết bị
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700 dark:text-slate-300">
                      <input
                        type="radio"
                        name="device_mode"
                        checked={deviceMode === 'channels'}
                        onChange={() => setDeviceMode('channels')}
                        className="text-indigo-600 focus:ring-indigo-500"
                      />
                      Theo kênh
                    </label>
                  </div>

                  {deviceMode === 'all' && (
                    <div className="border border-slate-200 dark:border-slate-800 rounded-[10px] p-3 text-slate-500 dark:text-slate-400 bg-slate-50/50 dark:bg-slate-900/30">
                      Áp dụng cho <span className="font-bold text-indigo-600 dark:text-indigo-400">tất cả thiết bị</span> (Desktop &amp; Mobile).
                    </div>
                  )}

                  {deviceMode === 'devices' && (
                    <div className="border border-slate-200 dark:border-slate-800 rounded-[10px] p-3 max-h-40 overflow-y-auto">
                      {devices.length === 0 ? (
                        <p className="text-slate-400 italic py-1">Không tìm thấy thiết bị nào.</p>
                      ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
                          {devices.map(dev => (
                            <label key={dev.id} className="flex items-center gap-2 font-semibold text-slate-600 dark:text-slate-300 cursor-pointer py-0.5">
                              <input
                                type="checkbox"
                                checked={whDevices.includes(dev.id)}
                                onChange={() => handleDeviceSelect(dev.id)}
                                className="rounded text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                              />
                              <span className="flex items-center gap-1.5 truncate">
                                <span className={`w-1.5 h-1.5 rounded-full ${dev.type === 'desktop' ? 'bg-sky-500' : 'bg-rose-500'}`} />
                                {dev.name} ({dev.type})
                              </span>
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {deviceMode === 'channels' && (
                    <div className="border border-slate-200 dark:border-slate-800 rounded-[10px] p-3 max-h-40 overflow-y-auto">
                      {(!gameAssignments || gameAssignments.length === 0) ? (
                        <p className="text-slate-400 italic py-1">Chưa có kênh nào. Hãy tạo kênh ở trang Quản lý Kênh.</p>
                      ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
                          {gameAssignments.map(a => (
                            <label key={a.game} className="flex items-center gap-2 font-semibold text-slate-600 dark:text-slate-300 cursor-pointer py-0.5">
                              <input
                                type="checkbox"
                                checked={whChannels.includes(a.game)}
                                onChange={() => handleChannelToggle(a.game)}
                                className="rounded text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                              />
                              <span className="flex items-center gap-1.5 truncate">
                                <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                                {a.game}
                                <span className="text-[10px] text-slate-400">({(a.machines || []).length} máy)</span>
                              </span>
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>



                {/* SRT Config */}
                <div className="border-t border-slate-100 dark:border-slate-800/80 pt-4">
                  <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-[10px] mb-3">
                    <div>
                      <span className="block font-bold text-slate-700 dark:text-slate-300">Kích hoạt Auto Send SRT</span>
                      <span className="text-[11px] text-slate-400">Tự động giám sát và thông báo trạng thái luồng SRT (ON/OFF) gửi tới Webhook này.</span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={whSrtAutoSend}
                        onChange={(e) => setWhSrtAutoSend(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-slate-300 dark:bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                    </label>
                  </div>

                  {whSrtAutoSend && (
                    <div className="space-y-2 animate-in fade-in slide-in-from-top-1 duration-150">
                      <span className="block font-bold text-slate-500 uppercase">Chọn danh sách SRT cần theo dõi:</span>
                      <div className="border border-slate-200 dark:border-slate-800 rounded-[10px] p-3 max-h-48 overflow-y-auto space-y-2 bg-slate-50/50 dark:bg-slate-900/30 text-xs">
                        <label className="flex items-center gap-2 font-bold text-indigo-600 dark:text-indigo-400 cursor-pointer mb-2">
                          <input
                            type="checkbox"
                            checked={whSrtStreams.includes('all')}
                            onChange={() => handleSrtStreamSelect('all')}
                            className="rounded text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                          />
                          Tất cả các luồng SRT
                        </label>
                        
                        {allAvailableSrts.length === 0 ? (
                          <p className="text-slate-400 italic py-1">Không có luồng SRT nào hoạt động hoặc được tìm thấy.</p>
                        ) : (
                          <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
                            <table className="w-full text-left border-collapse bg-white dark:bg-slate-900">
                              <thead>
                                <tr className="bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                  <th className="py-2 px-3 w-10 text-center">
                                    <input
                                      type="checkbox"
                                      checked={whSrtStreams.includes('all')}
                                      onChange={() => handleSrtStreamSelect('all')}
                                      className="rounded text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                                    />
                                  </th>
                                  <th className="py-2 px-3">Tên máy</th>
                                  <th className="py-2 px-3">Tên SRT</th>
                                  <th className="py-2 px-3">Port</th>
                                  <th className="py-2 px-3">Type</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                {allAvailableSrts.map(srt => {
                                  const isSelected = whSrtStreams.includes(srt.id) || whSrtStreams.includes('all');
                                  return (
                                    <tr
                                      key={srt.id}
                                      className={`text-[11px] transition-all hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer ${
                                        isSelected ? 'bg-indigo-50/20 dark:bg-indigo-950/10' : ''
                                      }`}
                                      onClick={() => {
                                        if (!whSrtStreams.includes('all')) {
                                          handleSrtStreamSelect(srt.id);
                                        }
                                      }}
                                    >
                                      <td className="py-1.5 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                                        <input
                                          type="checkbox"
                                          checked={isSelected}
                                          onChange={() => handleSrtStreamSelect(srt.id)}
                                          disabled={whSrtStreams.includes('all')}
                                          className="rounded text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5 disabled:opacity-50"
                                        />
                                      </td>
                                      <td className="py-1.5 px-3 font-bold text-slate-700 dark:text-slate-200">
                                        {srt.machineName}
                                      </td>
                                      <td className="py-1.5 px-3 text-indigo-600 dark:text-indigo-400 font-bold">
                                        {srt.name}
                                      </td>
                                      <td className="py-1.5 px-3 font-mono font-semibold text-slate-600 dark:text-slate-300">
                                        {srt.port}
                                      </td>
                                      <td className="py-1.5 px-3">
                                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold leading-none uppercase ${
                                          srt.type.toLowerCase() === 'caller'
                                            ? 'bg-blue-50 text-blue-600 dark:bg-blue-950/30 dark:text-blue-400 border border-blue-100 dark:border-blue-900/30'
                                            : 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/30'
                                        }`}>
                                          {srt.type}
                                        </span>
                                      </td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Checked parameter conditions */}
                <div>
                  <label className="block font-bold text-slate-500 uppercase mb-1.5">
                    Tick chọn và thiết lập điều kiện cảnh báo gửi tới Webhook này
                  </label>
                  <div className="border border-slate-200 dark:border-slate-800 rounded-[10px] overflow-hidden">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                          <th className="py-2 px-3 text-center w-12">Dùng</th>
                          <th className="py-2 px-3">Nội dung cảnh báo</th>
                          <th className="py-2 px-3 w-24">Phép toán</th>
                          <th className="py-2 px-3 w-28">Ngưỡng</th>
                          <th className="py-2 px-3 w-28">Quét lại (giây)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-900">
                        {DEFAULT_PARAMETERS.map(p => {
                          const state = ruleStates[p.parameter] || { enabled: false, operator: p.operator, value: p.defaultValue, alert_cooldown: 60 };
                          return (
                            <tr key={p.parameter} className={`hover:bg-slate-50/50 dark:hover:bg-slate-900/10 transition-all ${state.enabled ? 'bg-indigo-50/10 dark:bg-indigo-950/5' : ''}`}>
                              <td className="py-2.5 px-3 text-center">
                                <input
                                  type="checkbox"
                                  checked={state.enabled}
                                  onChange={() => handleRuleCheckToggle(p.parameter)}
                                  className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                                />
                              </td>
                              <td className="py-2.5 px-3">
                                <span className={`font-semibold ${state.enabled ? 'text-slate-800 dark:text-slate-100 font-bold' : 'text-slate-400 dark:text-slate-500'}`}>
                                  {p.label}
                                </span>
                                <span className="block text-[9.5px] text-slate-400 font-mono mt-0.5">
                                  Key: {p.parameter}
                                </span>
                              </td>
                              {p.parameter === 'networkChange' ? (
                                <td className="py-2.5 px-3" colSpan={2}>
                                  <select
                                    value={state.value}
                                    disabled={!state.enabled}
                                    onChange={(e) => handleRuleStateChange(p.parameter, 'value', e.target.value)}
                                    className="w-full px-2 py-1 border rounded-[6px] border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 font-bold text-[11px] disabled:opacity-50"
                                  >
                                    {NETWORK_TRANSITIONS.map(t => (
                                      <option key={t.value} value={t.value}>{t.label}</option>
                                    ))}
                                  </select>
                                </td>
                              ) : p.parameter === 'isOnline' ? (
                                <td className="py-2.5 px-3" colSpan={2}>
                                  <select
                                    value={normalizeOnlineValue(state.value)}
                                    disabled={!state.enabled}
                                    onChange={(e) => handleRuleStateChange(p.parameter, 'value', e.target.value)}
                                    className="w-full px-2 py-1 border rounded-[6px] border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 font-bold text-[11px] disabled:opacity-50"
                                  >
                                    {ONLINE_TRANSITIONS.map(t => (
                                      <option key={t.value} value={t.value}>{t.label}</option>
                                    ))}
                                  </select>
                                </td>
                              ) : (
                                <>
                                  <td className="py-2.5 px-3">
                                    <select
                                      value={state.operator}
                                      disabled={!state.enabled}
                                      onChange={(e) => handleRuleStateChange(p.parameter, 'operator', e.target.value)}
                                      className="w-full px-1.5 py-1 border rounded-[6px] border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 font-bold text-[11px] disabled:opacity-50"
                                    >
                                      <option value="=">=</option>
                                      <option value="!=">!=</option>
                                      <option value=">">&gt;</option>
                                      <option value="<">&lt;</option>
                                      <option value=">=">&gt;=</option>
                                      <option value="<=">&lt;=</option>
                                    </select>
                                  </td>
                                  <td className="py-2.5 px-3">
                                    <input
                                      type="text"
                                      required={state.enabled}
                                      disabled={!state.enabled}
                                      value={state.value}
                                      onChange={(e) => handleRuleStateChange(p.parameter, 'value', e.target.value)}
                                      className="w-full px-2 py-1 border rounded-[6px] border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-[11px] font-mono font-bold disabled:opacity-50"
                                    />
                                  </td>
                                </>
                              )}
                              <td className="py-2.5 px-3">
                                <input
                                  type="number"
                                  min={10}
                                  required={state.enabled}
                                  disabled={!state.enabled}
                                  value={state.alert_cooldown !== undefined ? state.alert_cooldown : 60}
                                  onChange={(e) => handleRuleStateChange(p.parameter, 'alert_cooldown', e.target.value)}
                                  className="w-full px-2 py-1 border rounded-[6px] border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-[11px] font-mono font-bold disabled:opacity-50"
                                />
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
              <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-2 bg-slate-50/50 dark:bg-slate-900/50">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 text-xs font-bold text-slate-500 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 rounded-[10px] transition-all"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-[10px] shadow-sm transition-all"
                >
                  {editingWebhook ? 'Lưu cập nhật' : 'Thêm mới'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
