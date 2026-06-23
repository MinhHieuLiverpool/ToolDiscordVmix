import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { showToast } from '../components/ui/Toast'

// Types based on the backend data structure
export interface MobileLogItem {
  deviceId: string
  deviceName: string
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
      <div className={`p-1 rounded transition-all ${isHigh ? 'bg-rose-50/50 dark:bg-rose-950/10' : 'bg-slate-50/80 dark:bg-slate-900/30'} flex flex-col items-center justify-center`}>
          <div className={`text-[7px] font-bold tracking-wider mb-0.5 uppercase px-0.5 rounded leading-none ${labelClass}`}>
              {label}
          </div>
          <div className={`text-[10px] font-black leading-none ${isHigh ? 'text-rose-500' : 'text-slate-800 dark:text-slate-200'}`}>
              {value}<span className="text-[7px] font-semibold text-slate-400 ml-0.5">{unit}</span>
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
      <div className="flex justify-between items-center text-[7.5px] py-0.2">
          <span className="text-slate-500 dark:text-slate-400 font-semibold">{label}:</span>
          <span className={`font-bold ${badgeColor} truncate max-w-[55px]`} title={value}>
              {value}
          </span>
      </div>
  )
}

function MobileDeviceCard({ item, index }: { item: MobileLogItem; index: number }) {
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
          className={`bg-white dark:bg-slate-900/45 rounded-lg border-y-0 border-r-0 border-l-[3px] border-solid p-2 shadow-sm transition-all duration-300 hover:shadow-md relative overflow-hidden ${
              isOnline ? 'border-l-emerald-500' : 'border-l-slate-300 dark:border-l-slate-700'
          }`}
          style={{ animationDelay: `${index * 40}ms` }}
      >
          {/* Header */}
          <div className="flex justify-between items-start mb-1.5">
              <div className="flex-1 min-w-0 pr-0.5">
                  <h3 className="text-[10px] font-black text-slate-800 dark:text-slate-100 truncate flex items-center gap-0.5" title={item.deviceName || 'Ẩn danh'}>
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isOnline ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
                      {item.deviceName || 'Ẩn danh'}
                  </h3>
                  <div className="flex items-center gap-0.5 mt-0.5">
                      <span
                          onClick={() => item.deviceId && copyToClipboard(item.deviceId)}
                          className="text-[7.5px] font-mono text-slate-400 hover:text-sky-500 cursor-pointer transition-colors truncate max-w-[65px]"
                          title="Click để copy Device ID"
                      >
                          ID: {item.deviceId || '-'}
                      </span>
                  </div>
              </div>
              <div className="flex flex-col items-end gap-0.5 shrink-0">
                  <span className={`inline-flex items-center px-0.5 py-0.2 rounded text-[7px] font-bold border leading-none ${
                      isOnline
                          ? 'bg-emerald-50 text-emerald-500 border-emerald-100 dark:bg-emerald-950/20 dark:border-emerald-900/30'
                          : 'bg-slate-50 text-slate-400 border-slate-100 dark:bg-slate-800/40 dark:border-slate-800'
                  }`}>
                      {isOnline ? 'ON' : 'OFF'}
                  </span>
                  <span className="text-[7px] font-bold text-sky-500 bg-sky-50 dark:bg-sky-950/30 border border-sky-100 dark:border-sky-900/20 px-0.5 py-0.2 rounded leading-none">
                      {item.networkType || '-'}
                  </span>
              </div>
          </div>

          {/* Performance Grid */}
          <div className="grid grid-cols-3 gap-0.5 mb-1.5">
              <MetricBadge label="CPU" value={item.cpuLoad !== null ? item.cpuLoad : '-'} unit="%" isHigh={isCpuHigh} />
              <MetricBadge label="RAM" value={item.ramUsagePercent !== null ? item.ramUsagePercent : '-'} unit="%" isHigh={isRamHigh} />
              <MetricBadge label="FPS" value={item.fps !== null ? item.fps : '-'} unit="" />
          </div>

          {/* Progress Bars */}
          <div className="space-y-1 mb-1.5 bg-slate-50/50 dark:bg-slate-900/20 p-1 rounded">
              {/* CPU load */}
              <div>
                  <div className="flex justify-between text-[7.5px] font-bold text-slate-500 dark:text-slate-400 mb-0.5 leading-none">
                      <span>CPU</span>
                      <span>{item.cpuLoad}%</span>
                  </div>
                  <div className="h-[2px] bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
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
                  <div className="flex justify-between text-[7.5px] font-bold text-slate-500 dark:text-slate-400 mb-0.5 leading-none">
                      <span>RAM ({ramUsedGB}/{ramTotalGB}G)</span>
                      <span>{item.ramUsagePercent}%</span>
                  </div>
                  <div className="h-[2px] bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
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
          <div className="space-y-0 mb-1.5 text-[7.5px]">
              <div className="flex justify-between py-0.2">
                  <span className="text-slate-400">Local IP:</span>
                  <span className="font-mono font-bold text-slate-700 dark:text-slate-300 truncate max-w-[70px]" title={item.localIp}>{item.localIp || '-'}</span>
              </div>
              <div className="flex justify-between py-0.2">
                  <span className="text-slate-400">WAN IP:</span>
                  <span className="font-mono font-bold text-slate-700 dark:text-slate-300 truncate max-w-[70px]" title={item.wanIp}>{item.wanIp || '-'}</span>
              </div>
              <div className="flex justify-between py-0.2">
                  <span className="text-slate-400">Gateway:</span>
                  <span className="font-mono font-bold text-slate-700 dark:text-slate-300 truncate max-w-[70px]" title={item.gatewayIp}>{item.gatewayIp || '-'}</span>
              </div>
          </div>

          {/* Ping Diagnostics */}
          <div className="mb-1.5">
              <div className="text-[7.5px] font-bold text-slate-400 tracking-wide uppercase mb-0.5 leading-none">Ping</div>
              <div className="flex flex-col gap-0">
                  <PingRowCompact label="Gateway" value={item.pingGateway || '-'} />
                  <PingRowCompact label="Google" value={item.ping8888 || '-'} />
                  <PingRowCompact label="Server" value={item.serverPing || '-'} />
              </div>
          </div>

          {/* Bandwidth Speed */}
          <div className="mb-1.5">
              <div className="text-[7.5px] font-bold text-slate-400 tracking-wide uppercase mb-0.5 leading-none">Băng thông</div>
              <div className="grid grid-cols-2 gap-0.5">
                  <div className="flex items-center justify-between p-0.5 bg-pink-50/10 dark:bg-pink-950/5 rounded">
                      <span className="text-[5.5px] font-bold text-pink-400 uppercase tracking-wider">TX</span>
                      <span className="text-[8px] font-black text-pink-600 dark:text-pink-400 truncate leading-none">{item.txSpeedMbps.toFixed(2)}</span>
                  </div>

                  <div className="flex items-center justify-between p-0.5 bg-orange-50/10 dark:bg-orange-950/5 rounded">
                      <span className="text-[5.5px] font-bold text-orange-400 uppercase tracking-wider">RX</span>
                      <span className="text-[8px] font-black text-orange-600 dark:text-orange-400 truncate leading-none">{item.rxSpeedMbps.toFixed(2)}</span>
                  </div>
              </div>
          </div>

          {/* Battery Section */}
          <div className="mb-1.5 bg-slate-50/30 dark:bg-slate-900/10 p-1 rounded">
              <div className="flex justify-between items-center text-[7.5px] mb-0.5 leading-none">
                  <span className="font-bold text-slate-500 dark:text-slate-400">
                      Pin & Nhiệt
                  </span>
                  {item.isCharging && (
                      <span className="text-[6px] font-black text-amber-500">
                          SẠC
                      </span>
                  )}
              </div>
              <div className="grid grid-cols-2 gap-0.5 items-center">
                  <div>
                      <div className="flex justify-between text-[7.5px] text-slate-400 font-bold leading-none">
                          <span>{item.batteryLevel}%</span>
                      </div>
                      <div className="h-[2px] bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden mt-0.5">
                          <div
                              className={`h-full rounded-full ${
                                  item.batteryLevel < 20 ? 'bg-rose-500' : item.batteryLevel < 40 ? 'bg-amber-500' : 'bg-emerald-500'
                              }`}
                              style={{ width: `${item.batteryLevel}%` }}
                          />
                      </div>
                  </div>
                  <div className="text-right">
                      <span className={`text-[8px] font-black ${isTempHigh ? 'text-rose-500' : 'text-slate-700 dark:text-slate-300'} leading-none`}>
                          {item.temperature.toFixed(1)}°C
                      </span>
                  </div>
              </div>
          </div>

          {/* Footer - Updated time */}
          <div className="flex justify-between items-center text-[7.5px] font-bold text-slate-400 pt-1 leading-none">
              <span className="truncate max-w-[55px]">
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

  // Filter logs based on search term
  const filteredLogs = useMemo(() => {
    if (!searchTerm.trim()) return logs
    const term = searchTerm.toLowerCase()
    return logs.filter(
      (item) =>
        (item.deviceName || '').toLowerCase().includes(term) ||
        (item.deviceId || '').toLowerCase().includes(term) ||
        (item.localIp || '').toLowerCase().includes(term) ||
        (item.networkType || '').toLowerCase().includes(term)
    )
  }, [logs, searchTerm])

  // KPI calculations
  const kpis = useMemo(() => {
    const total = logs.length
    let onlineCount = 0
    let totalTemp = 0
    let tempCount = 0
    let totalSpeed = 0

    const now = new Date().getTime()
    logs.forEach((item) => {
      try {
        const logTime = new Date(item.timestamp).getTime()
        const isOnline = (now - logTime) < 20000
        if (isOnline) onlineCount++
      } catch {}

      if (item.temperature > 0) {
        totalTemp += item.temperature
        tempCount++
      }
      totalSpeed += (item.txSpeedMbps + item.rxSpeedMbps)
    })

    return {
      total,
      online: onlineCount,
      offline: total - onlineCount,
      avgTemp: tempCount > 0 ? (totalTemp / tempCount).toFixed(1) : '-',
      totalBandwidth: totalSpeed.toFixed(1)
    }
  }, [logs])

  if (loading && logs.length === 0) {
    return (
      <div className="p-6">
        <div className="page-header mb-6">
          <h2 className="page-title text-2xl font-black text-slate-800 dark:text-slate-100">Mobile Monitor</h2>
          <p className="page-description text-slate-500 text-sm">Đang tải cấu hình thiết bị chạy ngầm...</p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 gap-2">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={`skel-${i}`} className="bg-white dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800/80 rounded-xl p-3 h-80 shimmer-loading" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="page-header mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="page-title text-2xl font-black text-slate-800 dark:text-slate-100">Mobile Monitor</h2>
          <p className="page-description text-slate-500 text-sm">Theo dõi, kiểm tra hiệu năng phần cứng và trạng thái kết nối mạng của các thiết bị di động.</p>
        </div>
        <button
          onClick={() => {
            setLoading(true)
            void fetchMobileLogs()
          }}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl text-xs flex items-center gap-1.5 transition-colors self-start md:self-auto"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
          </svg>
          Làm mới
        </button>
      </div>

      {/* KPI Section */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-slate-900/45 rounded-2xl border border-slate-100 dark:border-slate-800/80 p-4 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-sky-50 dark:bg-sky-950/20 text-sky-500 rounded-xl">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <rect x="5" y="2" width="14" height="20" rx="2" ry="2" />
              <line x1="12" y1="18" x2="12.01" y2="18" />
            </svg>
          </div>
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Tổng số thiết bị</div>
            <div className="text-xl font-black text-slate-800 dark:text-slate-100">{kpis.total} máy</div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900/45 rounded-2xl border border-slate-100 dark:border-slate-800/80 p-4 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-emerald-50 dark:bg-emerald-950/20 text-emerald-500 rounded-xl">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Đang hoạt động</div>
            <div className="text-xl font-black text-emerald-500">{kpis.online} online</div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900/45 rounded-2xl border border-slate-100 dark:border-slate-800/80 p-4 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-rose-50 dark:bg-rose-950/20 text-rose-500 rounded-xl">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Mất kết nối</div>
            <div className="text-xl font-black text-rose-500">{kpis.offline} máy</div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900/45 rounded-2xl border border-slate-100 dark:border-slate-800/80 p-4 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-amber-50 dark:bg-amber-950/20 text-amber-500 rounded-xl">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </div>
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Nhiệt độ Pin TB</div>
            <div className="text-xl font-black text-slate-800 dark:text-slate-100">{kpis.avgTemp}°C</div>
          </div>
        </div>
      </div>

      {/* Toolbar Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
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
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 gap-2">
          {filteredLogs.map((item, index) => (
            <MobileDeviceCard
              key={item.deviceId || index}
              item={item}
              index={index}
            />
          ))}
        </div>
      )}
    </div>
  )
}
