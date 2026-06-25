import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { showToast } from '../components/ui/Toast'
import { useDashboardContext } from '../hooks/useDashboardContext'

// Types based on the backend data structure
export interface MobileLogItem {
  deviceId: string
  deviceName: string
  name_device?: string
  wanIp: string
  pingGateway: string
  ping8888: string
  serverIp: string
  serverPing: string
  cpuLoad: number
  localIp: string
  gatewayIp: string
  cpuModel: string
  cpuCores: number
  ramTotal: number
  ramFree: number
  ramUsed: number
  ramUsagePercent: number
  txSpeedMbps: number
  rxSpeedMbps: number
  batteryLevel: number
  isCharging: boolean
  chargeSource: string
  temperature: number
  networkType: string
  fps: number
  packetLoss: number
  timestamp: string
}

function MetricBadge({ label, value, unit, isHigh }: { label: string; value: string | number; unit?: string; isHigh?: boolean }) {
  const labelKey = label.trim().toUpperCase()
  const labelClass = labelKey === 'CPU'
      ? 'text-sky-500 bg-sky-50 dark:bg-sky-950/30'
      : labelKey === 'RAM'
      ? 'text-emerald-500 bg-emerald-50 dark:bg-emerald-950/30'
      : labelKey === 'FPS'
      ? 'text-purple-500 bg-purple-50 dark:bg-purple-950/30'
      : 'text-slate-500 bg-slate-50 dark:bg-slate-900/30'

  return (
      <div className={`p-1.5 rounded-[6px] transition-all ${isHigh ? 'bg-rose-50/50 dark:bg-rose-950/10' : 'bg-slate-50/80 dark:bg-slate-900/30'} flex flex-col items-center justify-center`}>
          <div className={`text-[9px] font-bold tracking-wider mb-0.5 uppercase px-1 rounded leading-none ${labelClass}`}>
              {label}
          </div>
          <div className={`text-[12px] font-black leading-none ${isHigh ? 'text-rose-500' : 'text-slate-800 dark:text-slate-200'}`}>
              {value}<span className="text-[9px] font-semibold text-slate-400 ml-0.5">{unit}</span>
          </div>
      </div>
  )
}

function PingRowCompact({ label, value }: { label: string; value: string }) {
  const isTimeout = value.toLowerCase().includes('timeout') || value.toLowerCase().includes('error')
  const numericVal = parseFloat(value)
  const isHighPing = !isTimeout && numericVal > 80
  const isMediumPing = !isTimeout && numericVal > 30

  const badgeColor = isTimeout
      ? 'text-rose-500 dark:text-rose-400'
      : isHighPing
      ? 'text-amber-500 dark:text-amber-400'
      : isMediumPing
      ? 'text-yellow-600 dark:text-yellow-400'
      : 'text-emerald-500 dark:text-emerald-400'

  return (
      <div className="flex justify-between items-center text-[10px] py-0.5">
          <span className="text-slate-500 dark:text-slate-400 font-semibold">{label}:</span>
          <span className={`font-bold ${badgeColor} truncate max-w-[90px]`} title={value}>
              {value}
          </span>
      </div>
  )
}

function MobileDeviceCard({ item, index, onNameUpdated }: { item: MobileLogItem; index: number; onNameUpdated?: () => void }) {
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(item.name_device || '')

  useEffect(() => {
    if (!isEditing) {
      setEditValue(item.name_device || '')
    }
  }, [item.name_device, isEditing])

  const handleSave = async () => {
    try {
      // Gọi API PATCH để cập nhật name_device
      await axios.patch(`https://mobile-monitor.onrender.com/api/mobile-logs/${item.deviceId}`, {
        name_device: editValue
      })
      showToast('Đã cập nhật tên thiết bị!', 'success')
      setIsEditing(false)
      if (onNameUpdated) onNameUpdated()
    } catch (err: any) {
      console.error(err)
      showToast('Lỗi cập nhật tên thiết bị!', 'error')
    }
  }

  // Check if device is online: last packet received within 20 seconds
  const isOnline = useMemo(() => {
    try {
      const now = new Date().getTime()
      const logTime = new Date(item.timestamp).getTime()
      return (now - logTime) < 20000 // 20 seconds
    } catch {
      return false
    }
  }, [item.timestamp])

  const ramTotalGB = (item.ramTotal / (1024 * 1024 * 1024)).toFixed(1)
  const ramUsedGB = (item.ramUsed / (1024 * 1024 * 1024)).toFixed(1)

  const isCpuHigh = item.cpuLoad > 75
  const isRamHigh = item.ramUsagePercent > 85
  const isTempHigh = item.temperature > 40

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    showToast('Đã copy Device ID vào clipboard!', 'success')
  }

  return (
      <div
          className="bg-white dark:bg-slate-900/45 rounded-[10px] p-4 shadow-sm transition-all duration-300 hover:shadow-md relative overflow-hidden"
          style={{ animationDelay: `${index * 40}ms` }}
      >
          {/* Header */}
          <div className="flex justify-between items-start mb-2">
              <div className="flex-1 min-w-0 pr-1">
                  {isEditing ? (
                      <div className="flex items-center gap-1.5 w-full mb-1">
                          <input
                              type="text"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              className="text-[11px] px-2 py-1 border rounded-[6px] border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-rose-600 dark:text-rose-400 focus:outline-none focus:border-indigo-500 w-full font-black uppercase"
                              placeholder="TÊN THIẾT BỊ..."
                              autoFocus
                              onKeyDown={(e) => {
                                  if (e.key === 'Enter') handleSave()
                                  if (e.key === 'Escape') setIsEditing(false)
                              }}
                          />
                          <button onClick={handleSave} className="text-emerald-500 hover:text-emerald-600 shrink-0" title="Lưu">
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3.5">
                                  <polyline points="20 6 9 17 4 12" />
                              </svg>
                          </button>
                          <button onClick={() => setIsEditing(false)} className="text-rose-500 hover:text-rose-600 shrink-0" title="Hủy">
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3.5">
                                  <line x1="18" y1="6" x2="6" y2="18" />
                                  <line x1="6" y1="6" x2="18" y2="18" />
                              </svg>
                          </button>
                      </div>
                  ) : (
                      <>
                          {/* Tên custom màu đỏ in hoa in đậm ở dòng trên */}
                          {item.name_device && (
                              <div className="text-[11px] font-black text-rose-600 dark:text-rose-400 uppercase tracking-wider mb-0.5 break-all">
                                  {item.name_device}
                              </div>
                          )}
                          <h3 className="text-[12px] font-black text-slate-800 dark:text-slate-100 flex items-center gap-1 flex-wrap" title={item.deviceName || 'Ẩn danh'}>
                              <span className="break-all">{item.deviceName || 'Ẩn danh'}</span>
                              <button
                                  onClick={() => setIsEditing(true)}
                                  className="text-slate-400 hover:text-indigo-500 transition-colors ml-0.5 shrink-0"
                                  title="Đặt/Sửa tên thiết bị"
                              >
                                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                                  </svg>
                              </button>
                          </h3>
                          <div className="flex items-center gap-0.5 mt-0.5">
                              <span
                                  onClick={() => item.deviceId && copyToClipboard(item.deviceId)}
                                  className="text-[9px] font-mono text-slate-400 hover:text-sky-500 cursor-pointer transition-colors break-all"
                                  title="Click để copy Device ID"
                              >
                                  ID: {item.deviceId || '-'}
                              </span>
                          </div>
                      </>
                  )}
              </div>
              <div className="flex flex-col items-end gap-1 shrink-0">
                  <span className={`inline-flex items-center px-1 py-0.5 rounded-[4px] text-[9px] font-bold border leading-none ${
                      isOnline
                          ? 'bg-emerald-50 text-emerald-500 border-emerald-100 dark:bg-emerald-950/20 dark:border-emerald-900/30'
                          : 'bg-slate-50 text-slate-400 border-slate-100 dark:bg-slate-800/40 dark:border-slate-800'
                  }`}>
                      {isOnline ? 'ON' : 'OFF'}
                  </span>
                  <span className="text-[9px] font-bold text-sky-500 bg-sky-50 dark:bg-sky-950/30 border border-sky-100 dark:border-sky-900/20 px-1 py-0.5 rounded-[4px] leading-none">
                      {item.networkType || '-'}
                  </span>
              </div>
          </div>

          {/* Performance Grid */}
          <div className="grid grid-cols-3 gap-1 mb-2">
              <MetricBadge label="CPU" value={item.cpuLoad !== null ? item.cpuLoad : '-'} unit="%" isHigh={isCpuHigh} />
              <MetricBadge label="RAM" value={item.ramUsagePercent !== null ? item.ramUsagePercent : '-'} unit="%" isHigh={isRamHigh} />
              <MetricBadge label="FPS" value={item.fps !== null ? item.fps : '-'} unit="" />
          </div>

          {/* Progress Bars */}
          <div className="space-y-1.5 mb-2 bg-slate-50/50 dark:bg-slate-900/20 p-1.5 rounded-[8px]">
              {/* CPU load */}
              <div>
                  <div className="flex justify-between text-[10px] font-bold text-slate-500 dark:text-slate-400 mb-1 leading-none">
                      <span>CPU</span>
                      <span>{item.cpuLoad}%</span>
                  </div>
                  <div className="h-[4px] bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div
                          className={`h-full rounded-full transition-all duration-500 ${
                              isCpuHigh ? 'bg-rose-500' : item.cpuLoad > 45 ? 'bg-amber-500' : 'bg-sky-500'
                          }`}
                          style={{ width: `${item.cpuLoad}%` }}
                      />
                  </div>
              </div>

              {/* RAM load */}
              <div>
                  <div className="flex justify-between text-[10px] font-bold text-slate-500 dark:text-slate-400 mb-1 leading-none">
                      <span>RAM ({ramUsedGB}/{ramTotalGB}G)</span>
                      <span>{item.ramUsagePercent}%</span>
                  </div>
                  <div className="h-[4px] bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div
                          className={`h-full rounded-full transition-all duration-500 ${
                              isRamHigh ? 'bg-rose-500' : item.ramUsagePercent > 65 ? 'bg-amber-500' : 'bg-emerald-500'
                          }`}
                          style={{ width: `${item.ramUsagePercent}%` }}
                      />
                  </div>
              </div>
          </div>

          {/* Network details */}
          <div className="space-y-0.5 mb-2 text-[10px]">
              <div className="flex justify-between py-0.5">
                  <span className="text-slate-400">Local IP:</span>
                  <span className="font-mono font-bold text-slate-700 dark:text-slate-300 truncate max-w-[120px]" title={item.localIp}>{item.localIp || '-'}</span>
              </div>
              <div className="flex justify-between py-0.5">
                  <span className="text-slate-400">WAN IP:</span>
                  <span className="font-mono font-bold text-slate-700 dark:text-slate-300 truncate max-w-[120px]" title={item.wanIp}>{item.wanIp || '-'}</span>
              </div>
              <div className="flex justify-between py-0.5">
                  <span className="text-slate-400">Gateway:</span>
                  <span className="font-mono font-bold text-slate-700 dark:text-slate-300 truncate max-w-[120px]" title={item.gatewayIp}>{item.gatewayIp || '-'}</span>
              </div>
          </div>

          {/* Ping Diagnostics */}
          <div className="mb-2">
              <div className="text-[10px] font-bold text-slate-400 tracking-wide uppercase mb-1 leading-none">Ping</div>
              <div className="flex flex-col gap-0.5">
                  <PingRowCompact label="Gateway" value={item.pingGateway || '-'} />
                  <PingRowCompact label="Google" value={item.ping8888 || '-'} />
                  <PingRowCompact label="Server" value={item.serverPing || '-'} />
              </div>
          </div>

          {/* Bandwidth Speed */}
          <div className="mb-2">
              <div className="text-[10px] font-bold text-slate-400 tracking-wide uppercase mb-1 leading-none">Băng thông</div>
              <div className="grid grid-cols-2 gap-1">
                  <div className="flex items-center justify-between p-1 bg-pink-50/10 dark:bg-pink-950/5 rounded-[6px]">
                      <span className="text-[8px] font-bold text-pink-400 uppercase tracking-wider">TX</span>
                      <span className="text-[11px] font-black text-pink-600 dark:text-pink-400 truncate leading-none">{item.txSpeedMbps.toFixed(2)}</span>
                  </div>

                  <div className="flex items-center justify-between p-1 bg-orange-50/10 dark:bg-orange-950/5 rounded-[6px]">
                      <span className="text-[8px] font-bold text-orange-400 uppercase tracking-wider">RX</span>
                      <span className="text-[11px] font-black text-orange-600 dark:text-orange-400 truncate leading-none">{item.rxSpeedMbps.toFixed(2)}</span>
                  </div>
              </div>
          </div>

          {/* Battery Section */}
          <div className="mb-2 bg-slate-50/30 dark:bg-slate-900/10 p-1.5 rounded-[8px]">
              <div className="flex justify-between items-center text-[10px] mb-1 leading-none">
                  <span className="font-bold text-slate-500 dark:text-slate-400">
                      Pin & Nhiệt
                  </span>
                  {item.isCharging && (
                      <span className="text-[8px] font-black text-amber-500">
                          SẠC
                      </span>
                  )}
              </div>
              <div className="grid grid-cols-2 gap-1 items-center">
                  <div>
                      <div className="flex justify-between text-[10px] text-slate-400 font-bold leading-none">
                          <span>{item.batteryLevel}%</span>
                      </div>
                      <div className="h-[4px] bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden mt-1">
                          <div
                              className={`h-full rounded-full ${
                                  item.batteryLevel < 20 ? 'bg-rose-500' : item.batteryLevel < 40 ? 'bg-amber-500' : 'bg-emerald-500'
                              }`}
                              style={{ width: `${item.batteryLevel}%` }}
                          />
                      </div>
                  </div>
                  <div className="text-right">
                      <span className={`text-[11px] font-black ${isTempHigh ? 'text-rose-500' : 'text-slate-700 dark:text-slate-300'} leading-none`}>
                          {item.temperature.toFixed(1)}°C
                      </span>
                  </div>
              </div>
          </div>

          {/* Footer - Updated time */}
          <div className="flex justify-between items-center text-[10px] font-bold text-slate-400 pt-1 leading-none">
              <span className="truncate max-w-[90px]">
                  {new Date(item.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span>
                  PL: <span className={item.packetLoss > 0 ? 'text-rose-500' : 'text-emerald-500'}>{item.packetLoss}%</span>
              </span>
          </div>
      </div>
  )
}

export default function MobileMonitorPage() {
  const [logs, setLogs] = useState<MobileLogItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [networkFilter, setNetworkFilter] = useState('all')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)

  let allowedMachines: string[] | undefined
  try {
    const ctx = useDashboardContext() as any
    allowedMachines = ctx?.allowedMachines
  } catch {
    // outside dashboard layout context
  }

  const fetchMobileLogs = async () => {
    try {
      const response = await axios.get('https://mobile-monitor.onrender.com/api/mobile-logs?limit=50')
      if (response.data && response.data.status === 'success') {
        const rawData = response.data.data || []
        const sortedData = [...rawData].sort((a: MobileLogItem, b: MobileLogItem) => {
          const nameA = (a.deviceName || '').toLowerCase()
          const nameB = (b.deviceName || '').toLowerCase()
          if (nameA < nameB) return -1
          if (nameA > nameB) return 1
          
          const idA = (a.deviceId || '').toLowerCase()
          const idB = (b.deviceId || '').toLowerCase()
          if (idA < idB) return -1
          if (idA > idB) return 1
          return 0
        })
        setLogs(sortedData)
        setError('')
      } else {
        setError('Không thể định dạng dữ liệu từ server.')
      }
    } catch (err: any) {
      console.error(err)
      setError('Lỗi kết nối tới máy chủ lưu trữ Mobile Monitor.')
    } finally {
      setLoading(false)
    }
  }

  // Periodic polling every 3 seconds
  useEffect(() => {
    void fetchMobileLogs()
    const interval = setInterval(() => {
      void fetchMobileLogs()
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  // Filter logs based on search term and network type
  const filteredLogs = useMemo(() => {
    let result = logs

    if (allowedMachines && allowedMachines.length > 0) {
      result = result.filter((item) => 
        allowedMachines.includes(item.deviceName) || 
        allowedMachines.includes(item.name_device || '')
      )
    }

    // Filter by network type
    if (networkFilter !== 'all') {
      result = result.filter((item) => {
        const netType = (item.networkType || '').toLowerCase()
        if (networkFilter === 'lan') {
          return netType.includes('lan') || netType.includes('ethernet')
        }
        if (networkFilter === 'wifi') {
          return netType.includes('wifi') || netType.includes('wi-fi')
        }
        if (networkFilter === 'mobile') {
          return netType.includes('mobile') || netType.includes('cellular') || netType.includes('4g') || netType.includes('5g') || netType.includes('3g') || netType.includes('lte')
        }
        return true
      })
    }

    if (!searchTerm.trim()) return result
    const term = searchTerm.toLowerCase()
    return result.filter(
      (item) =>
        (item.deviceName || '').toLowerCase().includes(term) ||
        (item.deviceId || '').toLowerCase().includes(term) ||
        (item.localIp || '').toLowerCase().includes(term) ||
        (item.networkType || '').toLowerCase().includes(term)
    )
  }, [logs, searchTerm, networkFilter, allowedMachines])


  if (loading && logs.length === 0) {
    return (
      <div className="p-6">
        <div className="page-header mb-6">
          <h2 className="page-title text-2xl font-black text-slate-800 dark:text-slate-100">Mobile Monitor</h2>
          <p className="page-description text-slate-500 text-sm">Đang tải cấu hình thiết bị chạy ngầm...</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={`skel-${i}`} className="bg-white dark:bg-slate-900/40 rounded-[10px] p-4 h-[420px] shimmer-loading" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Toolbar Search & Filters */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="relative max-w-md flex-1 min-w-[240px]">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <input
            className="w-full pl-9 pr-4 py-2.5 bg-white dark:bg-slate-900/45 border border-slate-200 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700/60 focus:border-indigo-500 dark:focus:border-indigo-500/70 focus:outline-none rounded-xl text-xs font-semibold text-slate-800 dark:text-slate-100 transition-all shadow-sm"
            type="text"
            placeholder="Tìm theo tên điện thoại, ID, IP hoặc Loại mạng..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* Lọc theo Network */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center justify-between pl-3 pr-8 py-2.5 bg-white dark:bg-slate-900/45 border border-slate-200 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700/60 focus:border-indigo-500 dark:focus:border-indigo-500/70 focus:outline-none rounded-xl text-xs font-semibold text-slate-800 dark:text-slate-100 transition-all shadow-sm cursor-pointer min-w-[130px]"
          >
            <span>
              {networkFilter === 'all' && 'Tất cả mạng'}
              {networkFilter === 'lan' && 'LAN'}
              {networkFilter === 'wifi' && 'Wifi'}
              {networkFilter === 'mobile' && 'Mạng di động'}
            </span>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400">
              <svg className={`h-3.5 w-3.5 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
              </svg>
            </div>
          </button>

          {isDropdownOpen && (
            <>
              {/* Overlay để bấm ra ngoài thì đóng */}
              <div 
                className="fixed inset-0 z-10" 
                onClick={() => setIsDropdownOpen(false)}
              />
              <div className="absolute right-0 mt-1.5 w-full min-w-[140px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-lg py-1.5 z-20 animate-in fade-in slide-in-from-top-1 duration-150">
                {[
                  { value: 'all', label: 'Tất cả mạng' },
                  { value: 'lan', label: 'LAN' },
                  { value: 'wifi', label: 'Wifi' },
                  { value: 'mobile', label: 'Mạng di động' }
                ].map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      setNetworkFilter(opt.value)
                      setIsDropdownOpen(false)
                    }}
                    className={`w-full text-left px-3 py-2 text-xs font-medium hover:bg-indigo-50 dark:hover:bg-indigo-950/40 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors flex items-center justify-between ${
                      networkFilter === opt.value 
                        ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50/50 dark:bg-indigo-950/20 font-semibold' 
                        : 'text-slate-700 dark:text-slate-200'
                    }`}
                  >
                    <span>{opt.label}</span>
                    {networkFilter === opt.value && (
                      <svg className="h-3 w-3 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <button
          onClick={() => {
            setLoading(true)
            void fetchMobileLogs()
          }}
          className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl text-xs flex items-center gap-1.5 transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
          </svg>
          Làm mới
        </button>
      </div>

      {/* Main Grid */}
      {error ? (
        <div className="bg-rose-50 border border-rose-100 dark:bg-rose-950/15 dark:border-rose-900/30 text-rose-600 dark:text-rose-400 p-4 rounded-2xl text-xs font-semibold">
          ⚠️ {error}
        </div>
      ) : filteredLogs.length === 0 ? (
        <div className="bg-white dark:bg-slate-900/45 border border-slate-100 dark:border-slate-800/80 rounded-2xl p-12 text-center text-slate-400 font-bold shadow-sm">
          Không tìm thấy thiết bị di động nào phù hợp.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredLogs.map((item, index) => (
            <MobileDeviceCard
              key={item.deviceId || index}
              item={item}
              index={index}
              onNameUpdated={fetchMobileLogs}
            />
          ))}
        </div>
      )}
    </div>
  )
}
