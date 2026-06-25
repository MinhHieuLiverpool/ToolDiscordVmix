import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { BACKEND_WS_URL } from '../config/constants'
import {
    fetchAllLogs,
    fetchStatistics,
    fetchAllStatisticHours,
    fetchStatisticHours,
    normalizeSrtList,
    fetchGameSelected,
    type GameSelectedResponse,
} from '../services/api'
import type {
    BackendLogItem,
    StatisticHoursResponse,
} from '../services/api'
import type { DeviceFilter, MachineMetrics, MetricPoint, TimeFilter } from '../types'
import { toNumber } from '../types'

/* ─── Constants ───────────────────────────────────────── */
const REALTIME_MAX_POINTS = 360
const INITIAL_HISTORY_LIMIT = 60
const REALTIME_WINDOW_MS = 3 * 60 * 1000
const REALTIME_STORAGE_KEY = 'vmix-realtime-history-v1'
const REALTIME_STORAGE_TS_KEY = 'vmix-realtime-history-ts-v1'
const REALTIME_STORAGE_TTL_MS = 3 * 60 * 1000

function clampRealtimeHistory(history: MetricPoint[], nowMs: number): MetricPoint[] {
    const windowStart = nowMs - REALTIME_WINDOW_MS
    const windowed = history.filter((point) => (point.timeMs ?? nowMs) >= windowStart)
    if (windowed.length <= REALTIME_MAX_POINTS) return windowed
    return windowed.slice(windowed.length - REALTIME_MAX_POINTS)
}

/**
 * Build machine key matching server's _build_statistics_id(ip, port, name).
 * Server format: f"{ip}:{port}" if ip or port, else fallback_name.
 * Since most machines don't send 'port' field, result is typically "ip:".
 */
function buildMachineId(item: BackendLogItem): string {
    const ip = String(item.data.ip || '').trim()
    const port = String(item.data.port || '').trim()
    // Try SRT port as fallback (matches server's fallback logic)
    const srtPort = port || String(normalizeSrtList(item.data.SRT)[0]?.port || '').trim()
    if (ip || srtPort) return `${ip}:${srtPort}`
    return String(item.data.name || '').trim()
}

function sortLogs(logs: BackendLogItem[]): BackendLogItem[] {
    return [...logs].sort((a, b) => {
        const nameA = String(a.data.name || '').toLowerCase()
        const nameB = String(b.data.name || '').toLowerCase()
        if (nameA !== nameB) {
            return nameA.localeCompare(nameB)
        }
        const ipA = String(a.data.ip || '')
        const ipB = String(b.data.ip || '')
        return ipA.localeCompare(ipB)
    })
}

export function useDashboardData() {
    /* ─── Machine list (từ WebSocket) ─── */
    const [allRows, setAllRows] = useState<BackendLogItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')

    /* ─── Game Selection (global filter) ─── */
    const [selectedGame, setSelectedGame] = useState(() => {
        return window.localStorage.getItem('vmix:overview:selected-game') || '__all__'
    })

    const [gameAssignments, setGameAssignments] = useState<GameSelectedResponse[]>([])

    const loadAssignments = useCallback(async () => {
        try {
            const data = await fetchGameSelected()
            setGameAssignments(data)
        } catch (err) {
            console.error('Error loading game assignments:', err)
        }
    }, [])

    useEffect(() => {
        loadAssignments()
    }, [loadAssignments])

    const rows = useMemo(() => {
        if (selectedGame === '__all__') {
            return allRows.filter((row) => {
                const machineName = row.data.name
                const memberChannels = gameAssignments.filter(a => a.machines.includes(machineName))
                if (memberChannels.length === 0) return true
                return memberChannels.some(a => {
                    const channelIsOn = a.visible_status !== 'OFF'
                    const machineIsNotHiddenInChannel = !(a.hidden_machines || []).includes(machineName)
                    return channelIsOn && machineIsNotHiddenInChannel
                })
            })
        }

        const assignment = gameAssignments.find(a => a.game === selectedGame)
        if (!assignment || assignment.visible_status === 'OFF') return []

        const hiddenMachines = assignment.hidden_machines || []
        return allRows.filter((row) => {
            return assignment.machines.includes(row.data.name) && !hiddenMachines.includes(row.data.name)
        })
    }, [allRows, selectedGame, gameAssignments])

    /* ─── Debug logs ─── */
    const [debugLogs, setDebugLogs] = useState<string[]>([])
    const clearDebugLogs = useCallback(() => setDebugLogs([]), [])
    const wsRef = useRef<WebSocket | null>(null)
    const reconnectTimerRef = useRef<number | null>(null)

    /* ─── View & Filters ─── */
    const [activeView, setActiveView] = useState<TimeFilter>('realtime')
    const [deviceFilter, setDeviceFilter] = useState<DeviceFilter>('__all__')

    /* ─── Realtime metrics (loaded once + appended from WS) ─── */
    const [realtimeMap, setRealtimeMap] = useState<Map<string, MachineMetrics>>(new Map())
    const [realtimeLoading, setRealtimeLoading] = useState(false)
    const realtimeInitialLoadedRef = useRef(false)
    const realtimeStorageLoadedRef = useRef(false)
    const realtimeStorageTimerRef = useRef<number | null>(null)

    /* ─── Daily metrics (loaded once) ─── */
    const [dailyMap, setDailyMap] = useState<Map<string, MachineMetrics>>(new Map())
    const [dailyLoading, setDailyLoading] = useState(false)
    const dailyInitialLoadedRef = useRef(false)

    /* ─── All machine options ─── */
    const machineOptions = useMemo(() => {
        const map = new Map<string, { id: string; label: string }>()
        rows.forEach((item) => {
            const id = buildMachineId(item)
            if (!id) return
            const name = String(item.data.name || 'Unknown')
            const ip = String(item.data.ip || '')
            map.set(id, { id, label: `${name} (${ip})` })
        })
        return Array.from(map.values())
    }, [rows])

    const latestRowByMachineId = useMemo(() => {
        const map = new Map<string, BackendLogItem>()
        rows.forEach((item) => {
            const id = buildMachineId(item)
            if (!id) return
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

    const machineOptionsRef = useRef<Array<{ id: string; label: string }>>([])
    useEffect(() => {
        machineOptionsRef.current = machineOptions
    }, [machineOptions])

    const buildFallbackMetric = useCallback((id: string, label: string): MachineMetrics => {
        const row = latestRowByMachineId.get(id)
        const cpu = toNumber(row?.data.temperature ?? row?.data.cpu) ?? 0
        const ram = toNumber(row?.data.memory) ?? 0
        const gpu = toNumber(row?.data.gpu) ?? 0
        const timeMs = Date.now()
        const nowLabel = new Date().toLocaleTimeString('vi-VN', { hour12: false })
        return { id, label, history: [{ timeLabel: nowLabel, cpu, ram, gpu, timeMs }] }
    }, [latestRowByMachineId])

    const totalOnline = useMemo(
        () => rows.filter((item) => Number(item.data.statusapp ?? 0) === 1).length,
        [rows],
    )

    const currentMetrics = activeView === 'realtime' ? realtimeMap : dailyMap
    const currentLoading = activeView === 'realtime' ? realtimeLoading : dailyLoading

    const filteredMachines = useMemo(() => {
        const allIds = new Set(machineOptions.map((item) => item.id))
        return Array.from(currentMetrics.values())
            .filter((m) => allIds.has(m.id))
            .map((m) => ({
                ...m,
                latestItem: latestRowByMachineId.get(m.id),
            }))
    }, [currentMetrics, machineOptions, latestRowByMachineId])

    /* ═══════════════════════════════════════════════════════════
     * WebSocket
     * ═══════════════════════════════════════════════════════════ */
    const loadData = useCallback(async () => {
        try {
            setError('')
            const data = await fetchAllLogs()
            setAllRows(sortLogs(data))

            const d = new Date()
            const hh = String(d.getHours()).padStart(2, '0')
            const mm = String(d.getMinutes()).padStart(2, '0')
            const ss = String(d.getSeconds()).padStart(2, '0')
            const day = String(d.getDate()).padStart(2, '0')
            const month = String(d.getMonth() + 1).padStart(2, '0')
            const year = d.getFullYear()
            const formatTimeDate = `[ ${hh}:${mm}:${ss} - ${day}/${month}/${year} ]`

            const newLogs = data.map((item) => {
                const name = item.data.name || 'Unknown'
                const ip = item.data.ip || '-'
                const ipwan = item.data.ipwan || '-'
                const responseParams = JSON.stringify(item.data)
                return `${formatTimeDate} - ${name} - ${ip} - ${ipwan} - ${responseParams}`
            })

            setDebugLogs((prev) => {
                const combined = [...newLogs, ...prev]
                return combined.slice(0, 1000)
            })
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
                setAllRows(sortLogs(incoming))
                setLoading(false)

                const d = new Date()
                const hh = String(d.getHours()).padStart(2, '0')
                const mm = String(d.getMinutes()).padStart(2, '0')
                const ss = String(d.getSeconds()).padStart(2, '0')
                const day = String(d.getDate()).padStart(2, '0')
                const month = String(d.getMonth() + 1).padStart(2, '0')
                const year = d.getFullYear()
                const formatTimeDate = `[ ${hh}:${mm}:${ss} - ${day}/${month}/${year} ]`

                const newLogs = incoming.map((item) => {
                    const name = item.data.name || 'Unknown'
                    const ip = item.data.ip || '-'
                    const ipwan = item.data.ipwan || '-'
                    const responseParams = JSON.stringify(item.data)
                    return `${formatTimeDate} - ${name} - ${ip} - ${ipwan} - ${responseParams}`
                })

                setDebugLogs((prev) => {
                    const combined = [...newLogs, ...prev]
                    return combined.slice(0, 1000)
                })
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
     * REALTIME CHART — Load 1 lần + append từ WebSocket
     * ═══════════════════════════════════════════════════════════ */
    const loadInitialRealtimeStats = useCallback(async () => {
        if (realtimeInitialLoadedRef.current) return
        const options = machineOptionsRef.current
        if (options.length === 0) return

        realtimeInitialLoadedRef.current = true
        setRealtimeLoading(true)

        try {
            const settled = await Promise.allSettled(
                options.map(async (opt) => {
                    const payload = await fetchStatistics(opt.id, INITIAL_HISTORY_LIMIT)
                    const history: MetricPoint[] = (payload.data || [])
                        .map((p) => {
                            const cpu = toNumber(p.cpu) ?? 0
                            const ram = toNumber(p.ram) ?? 0
                            const gpu = toNumber(p.gpu) ?? 0
                            const d = new Date(p.time)
                            const timeMs = Number.isNaN(d.getTime()) ? Date.now() : d.getTime()
                            const timeLabel = Number.isNaN(d.getTime())
                                ? String(p.time || '').slice(11, 19)
                                : d.toLocaleTimeString('vi-VN', { hour12: false })
                            return { timeLabel, cpu, ram, gpu, timeMs }
                        })
                        .slice(-INITIAL_HISTORY_LIMIT)
                    const nowMs = Date.now()
                    return { id: opt.id, label: opt.label, history: clampRealtimeHistory(history, nowMs) }
                }),
            )

            const next = new Map<string, MachineMetrics>()
            for (let i = 0; i < settled.length; i++) {
                const item = settled[i]
                const opt = options[i]
                if (item.status === 'fulfilled' && item.value.history.length > 0) {
                    next.set(item.value.id, item.value)
                } else {
                    next.set(opt.id, buildFallbackMetric(opt.id, opt.label))
                }
            }
            setRealtimeMap(next)
            console.log(`✓ Loaded history for ${next.size} machines (one-time)`)
        } catch (err) {
            console.error('Initial realtime stats load error', err)
        } finally {
            setRealtimeLoading(false)
        }
    }, [buildFallbackMetric])

    useEffect(() => {
        if (activeView !== 'realtime') return
        if (machineOptions.length > 0 && !realtimeInitialLoadedRef.current) {
            void loadInitialRealtimeStats()
        }
    }, [activeView, machineOptions, loadInitialRealtimeStats])

    useEffect(() => {
        if (activeView !== 'realtime') return
        if (realtimeStorageLoadedRef.current) return

        realtimeStorageLoadedRef.current = true
        try {
            const raw = window.localStorage.getItem(REALTIME_STORAGE_KEY)
            const rawTs = window.localStorage.getItem(REALTIME_STORAGE_TS_KEY)
            const lastSaved = rawTs ? Number.parseInt(rawTs, 10) : 0
            if (!raw || !Number.isFinite(lastSaved)) return

            const nowMs = Date.now()
            if (nowMs - lastSaved > REALTIME_STORAGE_TTL_MS) return

            const parsed = JSON.parse(raw) as Array<MachineMetrics>
            if (!Array.isArray(parsed)) return

            const next = new Map<string, MachineMetrics>()
            parsed.forEach((metric) => {
                const history = clampRealtimeHistory(metric.history || [], nowMs)
                if (history.length === 0) return
                next.set(metric.id, { ...metric, history })
            })

            if (next.size > 0) {
                setRealtimeMap(next)
                realtimeInitialLoadedRef.current = true
            }
        } catch (err) {
            console.warn('Failed to restore realtime history cache', err)
        }
    }, [activeView])

    /* ─── Append từ WebSocket rows ─── */
    const prevRowsRef = useRef<BackendLogItem[]>([])

    useEffect(() => {
        if (activeView !== 'realtime') return
        if (!realtimeInitialLoadedRef.current) return
        if (rows === prevRowsRef.current) return
        prevRowsRef.current = rows

        setRealtimeMap((prev) => {
            const next = new Map(prev)
            const nowMs = Date.now()
            const nowLabel = new Date().toLocaleTimeString('vi-VN', { hour12: false })

            rows.forEach((item) => {
                const id = buildMachineId(item)
                if (!id) return

                const cpu = toNumber(item.data.temperature ?? item.data.cpu) ?? 0
                const ram = toNumber(item.data.memory) ?? 0
                const gpu = toNumber(item.data.gpu) ?? 0
                const newPoint: MetricPoint = { timeLabel: nowLabel, cpu, ram, gpu, timeMs: nowMs }

                const existing = next.get(id)
                if (existing) {
                    const lastPoint = existing.history[existing.history.length - 1]
                    if (lastPoint && lastPoint.timeLabel === nowLabel) return
                    const updatedHistory = clampRealtimeHistory([...existing.history, newPoint], nowMs)
                    next.set(id, { ...existing, history: updatedHistory })
                } else {
                    const name = String(item.data.name || 'Unknown')
                    const ip = String(item.data.ip || '')
                    next.set(id, { id, label: `${name} (${ip})`, history: [newPoint] })
                }
            })

            return next
        })
    }, [rows, activeView])

    useEffect(() => {
        if (activeView !== 'realtime') return

        if (realtimeStorageTimerRef.current) {
            window.clearTimeout(realtimeStorageTimerRef.current)
        }

        realtimeStorageTimerRef.current = window.setTimeout(() => {
            try {
                const payload = Array.from(realtimeMap.values())
                window.localStorage.setItem(REALTIME_STORAGE_KEY, JSON.stringify(payload))
                window.localStorage.setItem(REALTIME_STORAGE_TS_KEY, String(Date.now()))
            } catch (err) {
                console.warn('Failed to save realtime history cache', err)
            }
        }, 1000)

        return () => {
            if (realtimeStorageTimerRef.current) {
                window.clearTimeout(realtimeStorageTimerRef.current)
            }
        }
    }, [activeView, realtimeMap])

    /* ═══════════════════════════════════════════════════════════
     * DAILY — Load 1 lần duy nhất
     * ═══════════════════════════════════════════════════════════ */
    const loadInitialDailyStats = useCallback(async () => {
        if (dailyInitialLoadedRef.current) return
        dailyInitialLoadedRef.current = true
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
                        return { timeLabel, cpu: p.avg_cpu ?? 0, ram: p.avg_ram ?? 0, gpu: p.avg_gpu ?? 0 }
                })
                const metric = history.length > 0
                    ? { id: doc.id, label, history }
                    : buildFallbackMetric(doc.id, label)
                setDailyMap(new Map([[doc.id, metric]]))
            } else {
                const docs: StatisticHoursResponse[] = await fetchAllStatisticHours()
                const next = new Map<string, MachineMetrics>()
                for (const doc of docs) {
                    const opt = options.find((o) => o.id === doc.id)
                    const label = opt?.label ?? doc.id
                    const history: MetricPoint[] = (doc.data || []).map((p) => {
                        const d = new Date(p.window_start)
                        const timeLabel = Number.isNaN(d.getTime())
                            ? String(p.window_start || '').slice(11, 16)
                            : d.toLocaleTimeString('vi-VN', { hour12: false, hour: '2-digit', minute: '2-digit' })
                            return { timeLabel, cpu: p.avg_cpu ?? 0, ram: p.avg_ram ?? 0, gpu: p.avg_gpu ?? 0 }
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
                setDailyMap(next)
            }
        } catch (err) {
            console.error('Daily stats error', err)
        } finally {
            setDailyLoading(false)
        }
    }, [buildFallbackMetric, deviceFilter])

    useEffect(() => {
        dailyInitialLoadedRef.current = false
    }, [deviceFilter])

    useEffect(() => {
        if (activeView !== 'daily') return
        if (machineOptions.length > 0 && !dailyInitialLoadedRef.current) {
            void loadInitialDailyStats()
        }
    }, [activeView, machineOptions, loadInitialDailyStats])

    return {
        rows,
        allRows,
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
        debugLogs,
        clearDebugLogs,
        selectedGame,
        setSelectedGame,
        gameAssignments,
        loadAssignments,
    }
}
