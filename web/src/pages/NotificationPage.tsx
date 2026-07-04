import { useEffect, useState } from 'react'
import axios from 'axios'
import { showToast } from '../components/ui/Toast'
import { BACKEND_BASE_URL } from '../config/constants'

interface RuleCondition {
  parameter: string
  operator: string
  value: string
  enabled: boolean
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
}

interface DeviceOption {
  id: string
  name: string
  type: 'desktop' | 'mobile'
}

// Available standard parameters to choose/tick
const DEFAULT_PARAMETERS = [
  { parameter: 'isOnline', label: 'Thiết bị ngoại tuyến (Offline)', operator: '=', defaultValue: 'False' },
  { parameter: 'temperature', label: 'Nhiệt độ CPU/Pin quá cao (°C)', operator: '>', defaultValue: '45' },
  { parameter: 'cpuLoad', label: 'Tải CPU quá cao (%)', operator: '>', defaultValue: '85' },
  { parameter: 'memory', label: 'Sử dụng RAM quá cao (%)', operator: '>', defaultValue: '90' },
  { parameter: 'gpu', label: 'Sử dụng GPU quá cao (Desktop %)', operator: '>', defaultValue: '90' },
  { parameter: 'fps', label: 'Khung hình FPS quá thấp (Mobile)', operator: '<', defaultValue: '40' },
  { parameter: 'packetLoss', label: 'Mất gói Packet Loss quá cao (Mobile %)', operator: '>', defaultValue: '5' },
  { parameter: 'status', label: 'Trạng thái luồng SRT bị ngắt (OFF)', operator: '=', defaultValue: 'OFF' },
  { parameter: 'vmix_recording', label: 'Dừng Ghi hình vMix (Record OFF)', operator: '=', defaultValue: 'False' },
  { parameter: 'vmix_streaming', label: 'Dừng Phát sóng vMix (Stream OFF)', operator: '=', defaultValue: 'False' },
  { parameter: 'vmix_external', label: 'Tắt External Output vMix', operator: '=', defaultValue: 'False' },
  { parameter: 'vmix_multicorder', label: 'Tắt MultiCorder vMix', operator: '=', defaultValue: 'False' },
]

export default function NotificationPage() {
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([])
  const [devices, setDevices] = useState<DeviceOption[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'channels' | 'srt'>('channels')



  // Webhook Modal / Form states
  const [modalOpen, setModalOpen] = useState(false)
  const [editingWebhook, setEditingWebhook] = useState<WebhookItem | null>(null)
  
  const [whName, setWhName] = useState('')
  const [whType, setWhType] = useState<'Discord' | 'Seatalk'>('Discord')
  const [whUrl, setWhUrl] = useState('')
  const [whEnabled, setWhEnabled] = useState(true)
  const [whDevices, setWhDevices] = useState<string[]>(['all'])
  
  // Rule checkboxes/values state in Form
  const [ruleStates, setRuleStates] = useState<Record<string, { enabled: boolean; operator: string; value: string }>>({})

  // SRT settings states
  const [srtAutoSend, setSrtAutoSend] = useState(false)
  const [globalActive, setGlobalActive] = useState(false)
  const [srtWebhooks, setSrtWebhooks] = useState<string[]>([])
  const [srtDevices, setSrtDevices] = useState<string[]>(['all'])
  const [sendingSrt, setSendingSrt] = useState(false)
  const [savingSrt, setSavingSrt] = useState(false)
  const [savingGlobal, setSavingGlobal] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [whRes, devRes, srtRes] = await Promise.all([
        axios.get(`${BACKEND_BASE_URL}/api/notifications/webhooks`),
        axios.get(`${BACKEND_BASE_URL}/api/notifications/devices`),
        axios.get(`${BACKEND_BASE_URL}/api/notifications/srt-settings`)
      ])
      
      if (whRes.data.status === 'success') setWebhooks(whRes.data.data)
      if (devRes.data.status === 'success') setDevices(devRes.data.data)
      if (srtRes.data.status === 'success' && srtRes.data.data) {
        setSrtAutoSend(!!srtRes.data.data.auto_send)
        setSrtWebhooks(srtRes.data.data.webhooks || [])
        setSrtDevices(srtRes.data.data.devices || ['all'])
        setGlobalActive(!!srtRes.data.data.active)
      }
    } catch (err: any) {
      console.error(err)
      showToast('Lỗi tải dữ liệu cấu hình thông báo!', 'error')
    } finally {
      setLoading(false)
    }
  }

  // --- Toggle Global Engine Switch ---
  const handleToggleGlobalActive = async () => {
    setSavingGlobal(true)
    const nextState = !globalActive
    try {
      const payload = {
        auto_send: srtAutoSend,
        webhooks: srtWebhooks,
        devices: srtDevices,
        active: nextState
      }
      const res = await axios.post(`${BACKEND_BASE_URL}/api/notifications/srt-settings`, payload)
      if (res.data.status === 'success') {
        setGlobalActive(nextState)
        showToast(nextState ? 'Đã bật gửi thông báo hệ thống!' : 'Đã tắt gửi thông báo hệ thống!', 'success')
      }
    } catch (err) {
      showToast('Lỗi khi thay đổi trạng thái gửi thông báo!', 'error')
    } finally {
      setSavingGlobal(false)
    }
  }

  // --- Webhook Actions ---
  const handleOpenModal = (wh: WebhookItem | null = null) => {
    const initialRuleStates: Record<string, { enabled: boolean; operator: string; value: string }> = {}
    DEFAULT_PARAMETERS.forEach(p => {
      initialRuleStates[p.parameter] = {
        enabled: false,
        operator: p.operator,
        value: p.defaultValue
      }
    })

    if (wh) {
      setEditingWebhook(wh)
      setWhName(wh.name)
      setWhType(wh.type)
      setWhUrl(wh.url)
      setWhEnabled(wh.statusnotification !== 0)
      setWhDevices(wh.devices || ['all'])
      
      if (wh.rules && Array.isArray(wh.rules)) {
        wh.rules.forEach(r => {
          if (initialRuleStates[r.parameter]) {
            initialRuleStates[r.parameter] = {
              enabled: r.enabled,
              operator: r.operator,
              value: r.value
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

    const assembledRules: RuleCondition[] = DEFAULT_PARAMETERS.map(p => {
      const state = ruleStates[p.parameter]
      return {
        parameter: p.parameter,
        operator: state?.operator || p.operator,
        value: state?.value || p.defaultValue,
        enabled: !!state?.enabled
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
        devices: whDevices,
        rules: assembledRules
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
      const nextStatus = wh.statusnotification === 0 ? 1 : 0;
      const payload = {
        ...wh,
        statusnotification: nextStatus,
        enabled: nextStatus === 1
      }
      const response = await axios.post(`${BACKEND_BASE_URL}/api/notifications/webhooks`, payload)
      if (response.data.status === 'success') {
        showToast(`Đã ${nextStatus === 1 ? 'bật' : 'tắt'} kênh Webhook thành công!`, 'success')
        fetchData()
      }
    } catch (err) {
      showToast('Lỗi thay đổi trạng thái Webhook!', 'error')
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

  const handleRuleCheckToggle = (parameter: string) => {
    setRuleStates(prev => ({
      ...prev,
      [parameter]: {
        ...prev[parameter],
        enabled: !prev[parameter]?.enabled
      }
    }))
  }

  const handleRuleStateChange = (parameter: string, field: 'operator' | 'value', val: string) => {
    setRuleStates(prev => ({
      ...prev,
      [parameter]: {
        ...prev[parameter],
        [field]: val
      }
    }))
  }

  // --- SRT Tab Actions ---
  const handleSaveSrtSettings = async () => {
    setSavingSrt(true)
    try {
      const payload = {
        auto_send: srtAutoSend,
        webhooks: srtWebhooks,
        devices: srtDevices,
        active: globalActive
      }
      const res = await axios.post(`${BACKEND_BASE_URL}/api/notifications/srt-settings`, payload)
      if (res.data.status === 'success') {
        showToast('Lưu cấu hình SRT thành công!', 'success')
      }
    } catch (err) {
      showToast('Lỗi lưu cấu hình SRT!', 'error')
    } finally {
      setSavingSrt(false)
    }
  }

  const handleSendAllSrtNow = async () => {
    if (srtWebhooks.length === 0) {
      showToast('Vui lòng chọn ít nhất một Webhook để gửi báo cáo SRT!', 'error')
      return
    }
    setSendingSrt(true)
    try {
      const payload = {
        auto_send: srtAutoSend,
        webhooks: srtWebhooks,
        devices: srtDevices,
        active: globalActive
      }
      await axios.post(`${BACKEND_BASE_URL}/api/notifications/srt-settings`, payload)
      
      const res = await axios.post(`${BACKEND_BASE_URL}/api/notifications/srt-settings/send-all`)
      if (res.data.status === 'success') {
        showToast(res.data.message || 'Đã gửi toàn bộ list SRT thành công!', 'success')
      }
    } catch (err: any) {
      showToast(err.response?.data?.message || 'Lỗi gửi danh sách SRT!', 'error')
    } finally {
      setSendingSrt(false)
    }
  }

  const handleSrtWebhookToggle = (whId: string) => {
    if (srtWebhooks.includes(whId)) {
      setSrtWebhooks(srtWebhooks.filter(id => id !== whId))
    } else {
      setSrtWebhooks([...srtWebhooks, whId])
    }
  }

  const handleSrtDeviceSelect = (devId: string) => {
    if (devId === 'all') {
      if (srtDevices.includes('all')) {
        setSrtDevices([])
      } else {
        setSrtDevices(['all'])
      }
      return
    }
    
    let updated = [...srtDevices].filter(d => d !== 'all')
    if (updated.includes(devId)) {
      updated = updated.filter(d => d !== devId)
    } else {
      updated.push(devId)
    }
    setSrtDevices(updated)
  }

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
          {activeTab === 'channels' && (
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

      {/* Tabs */}
      <div className="flex gap-4 my-6 border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={() => setActiveTab('channels')}
          className={`pb-3 text-sm font-black transition-all ${
            activeTab === 'channels'
              ? 'text-indigo-600 border-b-2 border-indigo-600 dark:text-indigo-400 dark:border-indigo-400'
              : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'
          }`}
        >
          Kênh Webhook & Cảnh báo ({webhooks.length})
        </button>
        <button
          onClick={() => setActiveTab('srt')}
          className={`pb-3 text-sm font-black transition-all ${
            activeTab === 'srt'
              ? 'text-indigo-600 border-b-2 border-indigo-600 dark:text-indigo-400 dark:border-indigo-400'
              : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'
          }`}
        >
          Cấu hình SRT Auto Send 📡
        </button>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-8 h-8 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin mb-3"></div>
          <span className="text-xs font-bold text-slate-400">Đang tải cấu hình thông báo...</span>
        </div>
      ) : activeTab === 'channels' ? (
        webhooks.length === 0 ? (
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
                            onClick={() => handleToggleWebhookEnabled(wh)}
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-[6px] text-[11px] font-bold transition-all ${
                              wh.statusnotification !== 0
                                ? 'bg-emerald-50 text-emerald-600 border border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-900/30'
                                : 'bg-slate-100 text-slate-400 border border-slate-200 dark:bg-slate-800/40 dark:border-slate-800'
                            }`}
                            title={wh.statusnotification !== 0 ? 'Tạm tắt kênh' : 'Bật kênh'}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${wh.statusnotification !== 0 ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                            {wh.statusnotification !== 0 ? 'Bật' : 'Tắt'}
                          </button>
                        </td>

                        <td className="py-3.5 px-5 text-right">
                          <div className="flex gap-2 justify-end">
                            <button
                              onClick={() => handleOpenModal(wh)}
                              className="text-slate-400 hover:text-sky-500 transition-colors p-1"
                              title="Sửa cấu hình & Rule"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                              </svg>
                            </button>
                            <button
                              onClick={() => handleDeleteWebhook(wh.id)}
                              className="text-slate-400 hover:text-rose-500 transition-colors p-1"
                              title="Xóa kênh"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )
      ) : (
        /* SRT Settings Tab */
        <div className="max-w-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 rounded-[12px] p-6 shadow-sm mt-6">
          <h2 className="text-base font-black text-slate-800 dark:text-slate-100 uppercase mb-2">
            📡 Cấu hình Auto Send SRT Status
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
            Bật tính năng này để hệ thống tự động kiểm tra và đồng bộ trạng thái SRT của tất cả các máy. Gửi tin nhắn về Discord/SeaTalk đúng định dạng quy định.
          </p>

          <div className="space-y-6 text-xs">
            {/* Global Enable Toggle */}
            <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-[10px]">
              <div>
                <span className="block font-bold text-slate-700 dark:text-slate-300">Kích hoạt cảnh báo SRT toàn hệ thống</span>
                <span className="text-[11px] text-slate-400">Bật hoặc tắt toàn bộ cơ chế gửi thông báo SRT cho cấu hình hiện tại.</span>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={globalActive}
                  onChange={handleToggleGlobalActive}
                  disabled={savingGlobal}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-slate-300 dark:bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600 opacity-100 disabled:opacity-60"></div>
              </label>
            </div>

            {/* Enabled Toggle */}
            <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-[10px]">
              <div>
                <span className="block font-bold text-slate-700 dark:text-slate-300">Kích hoạt Auto Send SRT</span>
                <span className="text-[11px] text-slate-400">Tự động giám sát và thông báo trạng thái luồng SRT (ON/OFF) của toàn bộ hệ thống.</span>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={srtAutoSend}
                  onChange={(e) => setSrtAutoSend(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-slate-300 dark:bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
              </label>
            </div>

            {/* Target Webhooks */}
            <div>
              <span className="block font-bold text-slate-500 uppercase mb-2">Gửi tin nhắn SRT về Kênh Webhook:</span>
              {webhooks.length === 0 ? (
                <p className="text-rose-500 font-bold">* Vui lòng tạo ít nhất một Kênh Webhook ở tab bên cạnh.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 border border-slate-200 dark:border-slate-800 rounded-[10px] p-3 bg-slate-50/50 dark:bg-slate-900/30">
                  {webhooks.map(wh => (
                    <label key={wh.id} className="flex items-center gap-2 font-semibold text-slate-700 dark:text-slate-300 cursor-pointer py-1.5 px-2 hover:bg-slate-100/50 dark:hover:bg-slate-800/40 rounded">
                      <input
                        type="checkbox"
                        checked={srtWebhooks.includes(wh.id)}
                        onChange={() => handleSrtWebhookToggle(wh.id)}
                        className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                      />
                      <span>{wh.name} ({wh.type})</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {/* Apply Devices Section for SRT */}
            <div>
              <span className="block font-bold text-slate-500 uppercase mb-2">Chọn thiết bị áp dụng theo dõi SRT:</span>
              <div className="border border-slate-200 dark:border-slate-800 rounded-[10px] p-3 max-h-40 overflow-y-auto space-y-2 bg-slate-50/50 dark:bg-slate-900/30">
                <label className="flex items-center gap-2 font-bold text-indigo-600 dark:text-indigo-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={srtDevices.includes('all')}
                    onChange={() => handleSrtDeviceSelect('all')}
                    className="rounded text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                  />
                  Tất cả thiết bị (Desktop & Mobile)
                </label>
                <div className="h-px bg-slate-200 dark:bg-slate-800 my-2"></div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                  {devices.map(dev => (
                    <label key={dev.id} className="flex items-center gap-2 font-semibold text-slate-600 dark:text-slate-300 cursor-pointer py-0.5 pl-1">
                      <input
                        type="checkbox"
                        checked={srtDevices.includes(dev.id)}
                        onChange={() => handleSrtDeviceSelect(dev.id)}
                        disabled={srtDevices.includes('all')}
                        className="rounded text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5 disabled:opacity-50"
                      />
                      <span className="flex items-center gap-1.5 truncate">
                        <span className={`w-1.5 h-1.5 rounded-full ${dev.type === 'desktop' ? 'bg-sky-500' : 'bg-rose-500'}`} />
                        {dev.name} ({dev.type})
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* Message Format Example Card */}
            <div className="p-4 bg-slate-100/50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 rounded-[10px] font-mono">
              <span className="block font-bold text-[10px] text-slate-400 uppercase mb-2">Định dạng tin nhắn gửi đi:</span>
              <p className="text-slate-800 dark:text-slate-200">
                [SRT][PC-POV-01] SRT OFF | IPWAN: 101.53.36.132 | PORT: 5001
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-between items-center border-t border-slate-100 dark:border-slate-800 pt-5 gap-3">
              <button
                type="button"
                onClick={handleSendAllSrtNow}
                disabled={sendingSrt || webhooks.length === 0}
                className="px-4 py-2.5 text-xs font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/20 hover:bg-indigo-100 dark:hover:bg-indigo-900/35 border border-indigo-100 dark:border-indigo-900/30 rounded-[10px] transition-all disabled:opacity-50 flex items-center gap-1.5"
              >
                {sendingSrt ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-slate-300 border-t-indigo-600 rounded-full animate-spin"></div>
                    Đang gửi toàn bộ...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                    Bật gửi ngay (Gửi toàn bộ máy)
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={handleSaveSrtSettings}
                disabled={savingSrt}
                className="px-4 py-2.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-[10px] shadow-sm transition-all disabled:opacity-50 flex items-center gap-1.5"
              >
                {savingSrt ? 'Đang lưu...' : 'Lưu cấu hình SRT'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Webhook and Rules Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-[16px] shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
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
                  <label className="block font-bold text-slate-500 uppercase mb-1.5">Chọn thiết bị áp dụng cho Webhook này</label>
                  <div className="border border-slate-200 dark:border-slate-800 rounded-[10px] p-3 max-h-36 overflow-y-auto space-y-2">
                    <label className="flex items-center gap-2 font-bold text-indigo-600 dark:text-indigo-400 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={whDevices.includes('all')}
                        onChange={() => handleDeviceSelect('all')}
                        className="rounded text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                      />
                      Tất cả thiết bị (Desktop & Mobile)
                    </label>
                    <div className="h-px bg-slate-100 dark:bg-slate-800/80 my-2"></div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
                      {devices.map(dev => (
                        <label key={dev.id} className="flex items-center gap-2 font-semibold text-slate-600 dark:text-slate-300 cursor-pointer py-0.5">
                          <input
                            type="checkbox"
                            checked={whDevices.includes(dev.id)}
                            onChange={() => handleDeviceSelect(dev.id)}
                            disabled={whDevices.includes('all')}
                            className="rounded text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5 disabled:opacity-50"
                          />
                          <span className="flex items-center gap-1.5 truncate">
                            <span className={`w-1.5 h-1.5 rounded-full ${dev.type === 'desktop' ? 'bg-sky-500' : 'bg-rose-500'}`} />
                            {dev.name} ({dev.type})
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
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
                          <th className="py-2 px-3 w-28">Phép toán</th>
                          <th className="py-2 px-3 w-32">Ngưỡng</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-900">
                        {DEFAULT_PARAMETERS.map(p => {
                          const state = ruleStates[p.parameter] || { enabled: false, operator: p.operator, value: p.defaultValue };
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
