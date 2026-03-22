import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BACKEND_WS_URL } from '../config/constants'
import {
    fetchAllLogs,
    fetchStatistics,
    fetchAllStatisticHours,
    fetchStatisticHours,
} from '../services/api'
import type {
    BackendLogItem,
    StatisticHoursResponse,
} from '../services/api'
import type { DeviceFilter, MachineMetrics, MetricPoint, TimeFilter } from '../types'
import { toNumber } from '../types'

import Header from '../components/Header'
import FilterBar from '../components/FilterBar'
import ChartSection from '../components/ChartSection'
import StatusSection from '../components/StatusSection'
import { showToast } from '../components/ui/Toast'
import { logout } from '../services/auth'

const REQUEST_INTERVAL_MS = 5000
const REQUEST_INTERVAL_ALL_MS = 10000
const REALTIME_LIMIT_SINGLE = 120
const REALTIME_LIMIT_ALL = 60

export default function Dashboard() {
    const navigate = useNavigate()
    /* ─── Machine list (từ WebSocket, không cần gọi API riêng) ─── */
    const [rows, setRows] = useState<BackendLogItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
    const wsRef = useRef<WebSocket | null>(null)
    const reconnectTimerRef = useRef<number | null>(null)

    /* ─── Filters ───────────────────────────────────────── */
    const [deviceFilter, setDeviceFilter] = useState<DeviceFilter>('__all__')
    const [timeFilter, setTimeFilter] = useState<TimeFilter>('realtime')

    /* ─── Metric data per machine ───────────────────────── */
    const [metricsMap, setMetricsMap] = useState<Map<string, MachineMetrics>>(new Map())
    const [chartLoading, setChartLoading] = useState(false)
    const abortRef = useRef(false)
    const realtimeInFlightRef = useRef(false)
    const dailyInFlightRef = useRef(false)
    const machineOptionsRef = useRef<Array<{ id: string; label: string }>>([])

    /* ─── Derived ───────────────────────────────────────── */
    const machineOptions = useMemo(() => {
        const map = new Map<string, { id: string; label: string }>()
        rows.forEach((item) => {
            const ip = String(item.data.ip || '').trim()
            const port = String(item.data.port || '').trim()
            if (!ip && !port) return
            const id = `${ip}:${port}`
            const name = String(item.data.name || 'Unknown')
            map.set(id, { id, label: `${name} (${id})` })
        })
        return Array.from(map.values())
    }, [rows])

    const latestRowByMachineId = useMemo(() => {
        const map = new Map<string, BackendLogItem>()
        rows.forEach((item) => {
            const ip = String(item.data.ip || '').trim()
            const port = String(item.data.port || '').trim()
            if (!ip && !port) return
            const id = `${ip}:${port}`
            map.set(id, item)
        })
        return map
    }, [rows])

    const onlineMachineOptions = useMemo(() => {
        return machineOptions.filter((opt) => {
            const row = latestRowByMachineId.get(opt.id)
            return Number(row?.data.statusapp ?? 0) === 1
        })
    }, [machineOptions, latestRowByMachineId])

    const buildFallbackMetric = useCallback((id: string, label: string): MachineMetrics => {
        const row = latestRowByMachineId.get(id)
        const cpu = toNumber(row?.data.cpu) ?? 0
        const ram = toNumber(row?.data.memory) ?? 0
        const nowLabel = new Date().toLocaleTimeString('vi-VN', { hour12: false })
        return {
            id,
            label,
            history: [{ timeLabel: nowLabel, cpu, ram }],
        }
    }, [latestRowByMachineId])

    useEffect(() => {
        machineOptionsRef.current = onlineMachineOptions
    }, [onlineMachineOptions])

    const totalOnline = useMemo(
        () => rows.filter((item) => ['ONLINE', 'ON'].includes(item.data.status?.toUpperCase())).length,
        [rows],
    )

    const filteredMachines = useMemo(
        () => {
            const validIds = new Set(onlineMachineOptions.map((item) => item.id))
            return Array.from(metricsMap.values()).filter((machine) => validIds.has(machine.id))
        },
        [metricsMap, onlineMachineOptions],
    )

    const handleLogout = useCallback(() => {
        logout()
        showToast('Đã đăng xuất thành công.', 'info')
        navigate('/login', { replace: true })
    }, [navigate])

    /* ═══════════════════════════════════════════════════════════
     * WebSocket: nhận dữ liệu realtime cho danh sách máy
     * ═══════════════════════════════════════════════════════════ */
    const loadData = useCallback(async () => {
        try {
            setError('')
            const data = await fetchAllLogs()
            setRows(data)
        } catch (err) {
            setError('Không thể lấy dữ liệu từ backend.')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }, [])

    const connectWebSocket = useCallback(() => {
        setWsStatus('connecting')
        const ws = new WebSocket(BACKEND_WS_URL)
        wsRef.current = ws

        ws.onopen = () => {
            setWsStatus('connected')
            setError('')
        }
        ws.onmessage = (event) => {
            try {
                const incoming = JSON.parse(event.data) as BackendLogItem[]
                setRows(incoming)
                setLoading(false)
            } catch (e) {
                console.error(e)
            }
        }
        ws.onerror = () => setError('WebSocket gặp lỗi, đang thử kết nối lại...')
        ws.onclose = () => {
            setWsStatus('disconnected')
            if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current)
            reconnectTimerRef.current = window.setTimeout(connectWebSocket, 3000)
        }
    }, [])

    useEffect(() => {
        connectWebSocket()
        return () => {
            if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current)
            wsRef.current?.close()
        }
    }, [connectWebSocket])

    /* ═══════════════════════════════════════════════════════════
     * REALTIME: Gọi API statistics theo bộ lọc
    *   - 1 máy → 1 API call, poll 3s
    *   - Tất cả → gọi tuần tự 3s/máy
     * ═══════════════════════════════════════════════════════════ */
    const loadRealtimeStats = useCallback(async () => {
        if (realtimeInFlightRef.current) return
        realtimeInFlightRef.current = true
        try {
            const options = machineOptionsRef.current
            if (options.length === 0) return

            /* --- 1 máy cụ thể --- */
            if (deviceFilter !== '__all__') {
                const opt = options.find((o) => o.id === deviceFilter)
                if (!opt) {
                    setMetricsMap(new Map())
                    return
                }
                try {
                    setChartLoading(true)
                    const payload = await fetchStatistics(opt.id, REALTIME_LIMIT_SINGLE)
                    const history: MetricPoint[] = (payload.data || [])
                        .map((p) => {
                            const cpu = toNumber(p.cpu) ?? 0
                            const ram = toNumber(p.ram) ?? 0
                            const d = new Date(p.time)
                            const timeLabel = Number.isNaN(d.getTime())
                                ? String(p.time || '').slice(11, 19)
                                : d.toLocaleTimeString('vi-VN', { hour12: false })
                            return { timeLabel, cpu, ram }
                        })
                        .slice(-REALTIME_LIMIT_SINGLE)
                    const metric = history.length > 0
                        ? { id: opt.id, label: opt.label, history }
                        : buildFallbackMetric(opt.id, opt.label)
                    setMetricsMap(new Map([[opt.id, metric]]))
                } catch (err) {
                    console.error(`Stats error ${opt.id}`, err)
                    setMetricsMap(new Map([[opt.id, buildFallbackMetric(opt.id, opt.label)]]))
                } finally {
                    setChartLoading(false)
                }
                return
            }

            /* --- Tất cả: gọi đồng loạt mỗi chu kỳ --- */
            abortRef.current = false
            setChartLoading(true)
            if (options.length === 0) {
                setMetricsMap(new Map())
                return
            }
            const validIds = new Set(options.map((m) => m.id))

            const settled = await Promise.allSettled(
                options.map(async (opt) => {
                    const payload = await fetchStatistics(opt.id, REALTIME_LIMIT_ALL)
                    const history: MetricPoint[] = (payload.data || [])
                        .map((p) => {
                            const cpu = toNumber(p.cpu) ?? 0
                            const ram = toNumber(p.ram) ?? 0
                            const d = new Date(p.time)
                            const timeLabel = Number.isNaN(d.getTime())
                                ? String(p.time || '').slice(11, 19)
                                : d.toLocaleTimeString('vi-VN', { hour12: false })
                            return { timeLabel, cpu, ram }
                        })
                        .slice(-REALTIME_LIMIT_ALL)
                    return { id: opt.id, label: opt.label, history }
                }),
            )

            if (abortRef.current) return

            setMetricsMap((prev) => {
                const next = new Map<string, MachineMetrics>()

                // Giữ dữ liệu cũ cho máy hợp lệ hiện tại
                prev.forEach((value, key) => {
                    if (validIds.has(key)) {
                        next.set(key, value)
                    }
                })

                for (let i = 0; i < settled.length; i++) {
                    const item = settled[i]
                    const opt = options[i]
                    if (item.status === 'fulfilled') {
                        const hasHistory = item.value.history.length > 0
                        next.set(
                            item.value.id,
                            hasHistory
                                ? {
                                    id: item.value.id,
                                    label: item.value.label,
                                    history: item.value.history,
                                }
                                : buildFallbackMetric(item.value.id, item.value.label),
                        )
                    } else {
                        console.error(`Stats error ${opt.id}`, item.reason)
                        next.set(opt.id, buildFallbackMetric(opt.id, opt.label))
                    }
                }

                return next
            })
            setChartLoading(false)
        } finally {
            realtimeInFlightRef.current = false
        }
    }, [buildFallbackMetric, deviceFilter])

    /* ═══════════════════════════════════════════════════════════
     * DAILY: Gọi statistic_hours
     *   - 1 máy → /statistic_hours/{id}
     *   - Tất cả → /statistic_hours (1 API call bulk)
     * ═══════════════════════════════════════════════════════════ */
    const loadDailyStats = useCallback(async () => {
        if (dailyInFlightRef.current) return
        dailyInFlightRef.current = true

        setChartLoading(true)
        try {
            const options = machineOptionsRef.current
            if (deviceFilter !== '__all__') {
                if (!options.some((o) => o.id === deviceFilter)) {
                    setMetricsMap(new Map())
                    return
                }
                const doc: StatisticHoursResponse = await fetchStatisticHours(deviceFilter)
                const opt = options.find((o) => o.id === deviceFilter)
                const label = opt?.label ?? doc.id
                const history: MetricPoint[] = (doc.data || []).map((p) => {
                    const d = new Date(p.window_start)
                    const timeLabel = Number.isNaN(d.getTime())
                        ? String(p.window_start || '').slice(11, 16)
                        : d.toLocaleTimeString('vi-VN', { hour12: false, hour: '2-digit', minute: '2-digit' })
                    return { timeLabel, cpu: p.avg_cpu ?? 0, ram: p.avg_ram ?? 0 }
                })
                const metric = history.length > 0
                    ? { id: doc.id, label, history }
                    : buildFallbackMetric(doc.id, label)
                setMetricsMap(new Map([[doc.id, metric]]))
            } else {
                const docs: StatisticHoursResponse[] = await fetchAllStatisticHours()
                const validIds = new Set(options.map((m) => m.id))
                if (validIds.size === 0) {
                    setMetricsMap(new Map())
                    return
                }
                setMetricsMap((prev) => {
                    const next = new Map<string, MachineMetrics>()

                    // Giữ data cũ cho máy chưa kịp có bản ghi daily mới
                    prev.forEach((value, key) => {
                        if (validIds.has(key)) {
                            next.set(key, value)
                        }
                    })

                    for (const doc of docs) {
                        const opt = options.find((o) => o.id === doc.id)
                        const label = opt?.label ?? doc.id
                        const history: MetricPoint[] = (doc.data || []).map((p) => {
                            const d = new Date(p.window_start)
                            const timeLabel = Number.isNaN(d.getTime())
                                ? String(p.window_start || '').slice(11, 16)
                                : d.toLocaleTimeString('vi-VN', { hour12: false, hour: '2-digit', minute: '2-digit' })
                            return { timeLabel, cpu: p.avg_cpu ?? 0, ram: p.avg_ram ?? 0 }
                        })
                        const metric = history.length > 0
                            ? { id: doc.id, label, history }
                            : buildFallbackMetric(doc.id, label)
                        next.set(doc.id, metric)
                    }

                    for (const opt of options) {
                        if (!next.has(opt.id)) {
                            next.set(opt.id, buildFallbackMetric(opt.id, opt.label))
                        }
                    }

                    return next
                })
            }
        } catch (err) {
            console.error('Daily stats error', err)
        } finally {
            setChartLoading(false)
            dailyInFlightRef.current = false
        }
    }, [buildFallbackMetric, deviceFilter])

    /* ═══════════════════════════════════════════════════════════
     * Effect: load dữ liệu khi filter thay đổi
     * ═══════════════════════════════════════════════════════════ */
    useEffect(() => {
        // Abort sequential fetch cũ
        abortRef.current = true

        if (timeFilter === 'realtime') {
            void loadRealtimeStats()
            const pollMs = deviceFilter === '__all__' ? REQUEST_INTERVAL_ALL_MS : REQUEST_INTERVAL_MS
            const id = window.setInterval(() => void loadRealtimeStats(), pollMs)
            return () => {
                abortRef.current = true
                window.clearInterval(id)
            }
        } else {
            void loadDailyStats()
            const id = window.setInterval(() => void loadDailyStats(), REQUEST_INTERVAL_MS)
            return () => window.clearInterval(id)
        }
    }, [timeFilter, deviceFilter, loadRealtimeStats, loadDailyStats])

    /* ═══════════════════════════════════════════════════════════
     * Render
     * ═══════════════════════════════════════════════════════════ */
    return (
        <div className="app-shell">
            <header className="dashboard-header">
                <Header rows={rows} totalOnline={totalOnline} wsStatus={wsStatus} onLogout={handleLogout} />
                <FilterBar
                    deviceFilter={deviceFilter}
                    setDeviceFilter={setDeviceFilter}
                    timeFilter={timeFilter}
                    setTimeFilter={setTimeFilter}
                    machineOptions={onlineMachineOptions}
                    onRefresh={() => void loadData()}
                />
            </header>

            <ChartSection
                machines={filteredMachines}
                chartLoading={chartLoading}
                totalMachines={onlineMachineOptions.length}
                timeFilter={timeFilter}
            />

            <StatusSection rows={rows} loading={loading} error={error} />

            <footer className="app-footer">
                Built for ToolDiscordVmix · Performance Monitor
            </footer>
        </div>
    )
}
