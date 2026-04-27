import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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

/* ─── Constants ───────────────────────────────────────── */
const REALTIME_POLL_MS_SINGLE = 5000
const REALTIME_POLL_MS_ALL = 10000
const DAILY_POLL_MS = 30000
const REALTIME_LIMIT_SINGLE = 60
const REALTIME_LIMIT_ALL = 40

export function useDashboardData() {
    /* ─── Machine list (từ WebSocket) ─── */
    const [rows, setRows] = useState<BackendLogItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
    const wsRef = useRef<WebSocket | null>(null)
    const reconnectTimerRef = useRef<number | null>(null)

    /* ─── View & Filters ─── */
    const [activeView, setActiveView] = useState<TimeFilter>('realtime')
    const [deviceFilter, setDeviceFilter] = useState<DeviceFilter>('__all__')

    /* ─── Realtime metrics ─── */
    const [realtimeMap, setRealtimeMap] = useState<Map<string, MachineMetrics>>(new Map())
    const [realtimeLoading, setRealtimeLoading] = useState(false)
    const realtimeInFlightRef = useRef(false)
    const realtimeAbortRef = useRef(false)

    /* ─── Daily metrics ─── */
    const [dailyMap, setDailyMap] = useState<Map<string, MachineMetrics>>(new Map())
    const [dailyLoading, setDailyLoading] = useState(false)
    const dailyInFlightRef = useRef(false)

    const machineOptionsRef = useRef<Array<{ id: string; label: string }>>([])

    /* ─── Derived ─── */
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
        return { id, label, history: [{ timeLabel: nowLabel, cpu, ram }] }
    }, [latestRowByMachineId])

    useEffect(() => {
        machineOptionsRef.current = onlineMachineOptions
    }, [onlineMachineOptions])

    const totalOnline = useMemo(
        () => rows.filter((item) => ['ONLINE', 'ON'].includes(String(item.data.status || '').toUpperCase())).length,
        [rows],
    )

    const currentMetrics = activeView === 'realtime' ? realtimeMap : dailyMap
    const currentLoading = activeView === 'realtime' ? realtimeLoading : dailyLoading

    const filteredMachines = useMemo(() => {
        const validIds = new Set(onlineMachineOptions.map((item) => item.id))
        return Array.from(currentMetrics.values())
            .filter((m) => validIds.has(m.id))
            .map((m) => ({
                ...m,
                latestItem: latestRowByMachineId.get(m.id),
            }))
    }, [currentMetrics, onlineMachineOptions, latestRowByMachineId])

    /* ═══════════════════════════════════════════════════════════
     * WebSocket
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
     * REALTIME
     * ═══════════════════════════════════════════════════════════ */
    const loadRealtimeStats = useCallback(async () => {
        if (realtimeInFlightRef.current) return
        realtimeInFlightRef.current = true
        try {
            const options = machineOptionsRef.current
            if (options.length === 0) return

            if (deviceFilter !== '__all__') {
                const opt = options.find((o) => o.id === deviceFilter)
                if (!opt) {
                    setRealtimeMap(new Map())
                    return
                }
                try {
                    setRealtimeLoading(true)
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
                    setRealtimeMap(new Map([[opt.id, metric]]))
                } catch (err) {
                    console.error(`Stats error ${opt.id}`, err)
                    setRealtimeMap(new Map([[opt.id, buildFallbackMetric(opt.id, opt.label)]]))
                } finally {
                    setRealtimeLoading(false)
                }
                return
            }

            /* Tất cả máy */
            realtimeAbortRef.current = false
            setRealtimeLoading(true)
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

            if (realtimeAbortRef.current) return

            setRealtimeMap((prev) => {
                const next = new Map<string, MachineMetrics>()
                prev.forEach((value, key) => {
                    if (validIds.has(key)) next.set(key, value)
                })
                for (let i = 0; i < settled.length; i++) {
                    const item = settled[i]
                    const opt = options[i]
                    if (item.status === 'fulfilled') {
                        const hasHistory = item.value.history.length > 0
                        next.set(
                            item.value.id,
                            hasHistory
                                ? { id: item.value.id, label: item.value.label, history: item.value.history }
                                : buildFallbackMetric(item.value.id, item.value.label),
                        )
                    } else {
                        console.error(`Stats error ${opt.id}`, item.reason)
                        next.set(opt.id, buildFallbackMetric(opt.id, opt.label))
                    }
                }
                return next
            })
            setRealtimeLoading(false)
        } finally {
            realtimeInFlightRef.current = false
        }
    }, [buildFallbackMetric, deviceFilter])

    /* ═══════════════════════════════════════════════════════════
     * DAILY
     * ═══════════════════════════════════════════════════════════ */
    const loadDailyStats = useCallback(async () => {
        if (dailyInFlightRef.current) return
        dailyInFlightRef.current = true
        setDailyLoading(true)
        try {
            const options = machineOptionsRef.current
            if (deviceFilter !== '__all__') {
                if (!options.some((o) => o.id === deviceFilter)) {
                    setDailyMap(new Map())
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
                setDailyMap(new Map([[doc.id, metric]]))
            } else {
                const docs: StatisticHoursResponse[] = await fetchAllStatisticHours()
                const validIds = new Set(options.map((m) => m.id))
                if (validIds.size === 0) {
                    setDailyMap(new Map())
                    return
                }
                setDailyMap((prev) => {
                    const next = new Map<string, MachineMetrics>()
                    prev.forEach((value, key) => {
                        if (validIds.has(key)) next.set(key, value)
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
            setDailyLoading(false)
            dailyInFlightRef.current = false
        }
    }, [buildFallbackMetric, deviceFilter])

    /* ═══════════════════════════════════════════════════════════
     * Effects: only load data for the ACTIVE view
     * ═══════════════════════════════════════════════════════════ */
    useEffect(() => {
        if (activeView !== 'realtime') return

        realtimeAbortRef.current = true
        void loadRealtimeStats()
        const pollMs = deviceFilter === '__all__' ? REALTIME_POLL_MS_ALL : REALTIME_POLL_MS_SINGLE
        const id = window.setInterval(() => void loadRealtimeStats(), pollMs)
        return () => {
            realtimeAbortRef.current = true
            window.clearInterval(id)
        }
    }, [activeView, deviceFilter, loadRealtimeStats])

    useEffect(() => {
        if (activeView !== 'daily') return

        void loadDailyStats()
        const id = window.setInterval(() => void loadDailyStats(), DAILY_POLL_MS)
        return () => window.clearInterval(id)
    }, [activeView, deviceFilter, loadDailyStats])

    return {
        rows,
        loading,
        error,
        wsStatus,
        activeView,
        setActiveView,
        deviceFilter,
        setDeviceFilter,
        totalOnline,
        onlineMachineOptions,
        filteredMachines,
        currentLoading,
        loadData,
    }
}
