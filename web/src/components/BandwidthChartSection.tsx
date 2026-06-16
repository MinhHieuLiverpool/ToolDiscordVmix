import { useEffect, useState, useRef, useMemo } from 'react'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { fetchBandwidthStats } from '../services/api'
import type { BandwidthDoc } from '../services/api'
import { useDashboardContext } from '../hooks/useDashboardContext'

// Register ECharts modules
echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

interface BandwidthChartSectionProps {
    deviceFilter: string
    machines: any[]
}

interface IpwanBandwidthCardProps {
    doc: BandwidthDoc
    selectedDate: string
    timeFilter: '7h' | '24h'
    realTimeBw?: { sender: number; receiver: number }
}

function IpwanBandwidthCard({ doc, selectedDate, timeFilter, realTimeBw }: IpwanBandwidthCardProps) {
    const chartRef = useRef<HTMLDivElement>(null)
    const chartInstance = useRef<echarts.ECharts | null>(null)

    // Vibrant colors for the light theme chart
    const uploadColor = '#6366f1' // Bright Indigo for Upload
    const downloadColor = '#f97316' // Bright Orange for Download

    // Get all points from the database and sort by timestamp, filling gaps with 0
    const chartData = useMemo(() => {
        let history = doc.history || []
        
        const todayStr = new Date().toLocaleDateString('en-CA') // YYYY-MM-DD
        const isToday = selectedDate === todayStr

        if (isToday && realTimeBw) {
            history = [
                ...history,
                {
                    timestamp: new Date().toISOString(),
                    sender: realTimeBw.sender,
                    receiver: realTimeBw.receiver,
                }
            ]
        }

        let endTime: number
        if (isToday) {
            const now = new Date()
            now.setSeconds(0, 0)
            endTime = now.getTime()
        } else {
            endTime = new Date(`${selectedDate}T23:59:00`).getTime()
        }

        let startTime = new Date(`${selectedDate}T00:00:00`).getTime()

        if (timeFilter === '7h') {
            startTime = endTime - 7 * 60 * 60 * 1000
        }

        // Set grid interval: 5 mins for '7h', 10 mins for '24h'
        const intervalMs = timeFilter === '7h' ? 5 * 60 * 1000 : 10 * 60 * 1000

        const gridTimes: number[] = []
        let temp = startTime
        while (temp <= endTime) {
            gridTimes.push(temp)
            temp += intervalMs
        }
        if (gridTimes[gridTimes.length - 1] < endTime) {
            gridTimes.push(endTime)
        }

        const uploadPoints: [number, number][] = []
        const downloadPoints: [number, number][] = []

        gridTimes.forEach((gridTime) => {
            const windowStart = gridTime - intervalMs
            
            // Find all history records in this window
            const recordsInWindow = history.filter((h) => {
                const t = new Date(h.timestamp).getTime()
                return t >= windowStart && t <= gridTime
            })

            if (recordsInWindow.length > 0) {
                // Max bandwidth in this window to keep peaks
                const maxSender = Math.max(...recordsInWindow.map((r) => r.sender || 0))
                const maxReceiver = Math.max(...recordsInWindow.map((r) => r.receiver || 0))
                uploadPoints.push([gridTime, maxSender])
                downloadPoints.push([gridTime, maxReceiver])
            } else {
                // No records -> fill with 0
                uploadPoints.push([gridTime, 0])
                downloadPoints.push([gridTime, 0])
            }
        })

        return {
            uploadPoints,
            downloadPoints,
            minTime: startTime,
            maxTime: endTime,
        }
    }, [doc, selectedDate, timeFilter, realTimeBw])

    // Calculate stats
    const stats = useMemo(() => {
        let history = doc.history || []
        
        const todayStr = new Date().toLocaleDateString('en-CA') // YYYY-MM-DD
        const isToday = selectedDate === todayStr

        if (isToday && realTimeBw) {
            history = [
                ...history,
                {
                    timestamp: new Date().toISOString(),
                    sender: realTimeBw.sender,
                    receiver: realTimeBw.receiver,
                }
            ]
        }

        const senders = history.map((h) => h.sender)
        const receivers = history.map((h) => h.receiver)

        const maxSend = Math.max(doc.sender_max || 0, ...senders)
        const maxRecv = Math.max(doc.receiver_max || 0, ...receivers)

        const minSend = doc.sender_min || (senders.filter((s) => s > 0).length > 0 ? Math.min(...senders.filter((s) => s > 0)) : 0)
        const minRecv = doc.receiver_min || (receivers.filter((r) => r > 0).length > 0 ? Math.min(...receivers.filter((r) => r > 0)) : 0)

        const avgSend = senders.length > 0 ? senders.reduce((a, b) => a + b, 0) / senders.length : 0
        const avgRecv = receivers.length > 0 ? receivers.reduce((a, b) => a + b, 0) / receivers.length : 0

        const currSend = realTimeBw ? realTimeBw.sender : (senders.length > 0 ? senders[senders.length - 1] : 0)
        const currRecv = realTimeBw ? realTimeBw.receiver : (receivers.length > 0 ? receivers[receivers.length - 1] : 0)

        return {
            upload: { max: maxSend, min: minSend, avg: avgSend, curr: currSend },
            download: { max: maxRecv, min: minRecv, avg: avgRecv, curr: currRecv },
        }
    }, [doc, selectedDate, realTimeBw])

    const chartOption = useMemo(() => {
        return {
            backgroundColor: 'transparent',
            grid: {
                top: 15,
                right: 15,
                bottom: 20,
                left: 45,
            },
            tooltip: {
                trigger: 'axis' as const,
                backgroundColor: 'rgba(15,23,42,0.95)',
                borderColor: 'rgba(99,102,241,0.3)',
                borderWidth: 1,
                textStyle: {
                    color: '#f1f5f9',
                    fontSize: 11,
                    fontFamily: 'Inter, sans-serif',
                },
                formatter: (params: any[]) => {
                    if (!params || params.length === 0) return ''
                    const firstVal = params[0].value
                    const timestamp = Array.isArray(firstVal) ? firstVal[0] : firstVal
                    if (!timestamp) return ''

                    const d = new Date(Number(timestamp))
                    const hh = String(d.getHours()).padStart(2, '0')
                    const mm = String(d.getMinutes()).padStart(2, '0')
                    const timeStr = `${hh}:${mm}`

                    let html = `<div style="font-weight:700;margin-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:2px">${timeStr}</div>`
                    params.forEach((p) => {
                        const val = Array.isArray(p.value) ? p.value[1] : p.value
                        html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:16px;margin:3px 0">
                            <div style="display:flex;align-items:center;gap:6px">
                                <span style="width:6px;height:6px;border-radius:50%;background:${p.color};display:inline-block"></span>
                                <span>${p.seriesName}</span>
                            </div>
                            <span style="font-weight:700;font-family:monospace">${Number(val || 0).toFixed(2)} Mbps</span>
                        </div>`
                    })
                    return html
                },
            },
            xAxis: {
                type: 'time' as const,
                min: chartData.minTime,
                max: chartData.maxTime,
                axisLine: { lineStyle: { color: '#cbd5e1' } },
                axisTick: { show: false },
                axisLabel: {
                    color: '#64748b',
                    fontSize: 9,
                    fontWeight: 600,
                    formatter: (value: any) => {
                        const d = new Date(Number(value))
                        const hh = String(d.getHours()).padStart(2, '0')
                        const mm = String(d.getMinutes()).padStart(2, '0')
                        return `${hh}:${mm}`
                    }
                },
                splitLine: { show: false },
            },
            yAxis: {
                type: 'value' as const,
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: {
                    color: '#64748b',
                    fontSize: 9,
                    fontWeight: 600,
                    formatter: '{value} M',
                },
                splitLine: {
                    lineStyle: { color: '#f1f5f9', type: 'dashed' as const },
                },
            },
            series: [
                {
                    name: 'Tải lên (Upload)',
                    type: 'line',
                    data: chartData.uploadPoints,
                    smooth: true,
                    showSymbol: false,
                    lineStyle: {
                        width: 1.5,
                        color: uploadColor,
                        shadowColor: 'rgba(99, 102, 241, 0.25)',
                        shadowBlur: 6,
                        shadowOffsetY: 4,
                    },
                    itemStyle: { color: uploadColor },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(99,102,241,0.16)' },
                            { offset: 1, color: 'rgba(99,102,241,0.01)' },
                        ]),
                    },
                },
                {
                    name: 'Tải về (Download)',
                    type: 'line',
                    data: chartData.downloadPoints,
                    smooth: true,
                    showSymbol: false,
                    lineStyle: {
                        width: 1.5,
                        color: downloadColor,
                        shadowColor: 'rgba(249, 115, 22, 0.25)',
                        shadowBlur: 6,
                        shadowOffsetY: 4,
                    },
                    itemStyle: { color: downloadColor },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(249,115,22,0.16)' },
                            { offset: 1, color: 'rgba(249,115,22,0.01)' },
                        ]),
                    },
                },
            ],
        }
    }, [chartData, uploadColor, downloadColor])

    useEffect(() => {
        if (!chartRef.current) return

        const chart = echarts.init(chartRef.current, undefined, { renderer: 'canvas' })
        chartInstance.current = chart

        const resizeObserver = new ResizeObserver(() => {
            chart.resize()
        })

        resizeObserver.observe(chartRef.current)

        return () => {
            resizeObserver.disconnect()
            chart.dispose()
            chartInstance.current = null
        }
    }, [])

    useEffect(() => {
        if (chartInstance.current) {
            chartInstance.current.setOption(chartOption, { notMerge: true })
        }
    }, [chartOption])

    return (
        <div
            className="glass-card card-animate"
            style={{
                padding: '0.9rem 1.1rem',
                marginBottom: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
            }}
        >
            {/* Card Header */}
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    borderBottom: '1px solid #e2e8f0',
                    paddingBottom: '0.45rem',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                }}
            >
                <h3
                    style={{
                        margin: 0,
                        fontSize: '0.8rem',
                        fontWeight: 700,
                        color: '#0f172a',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.4rem',
                    }}
                >
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#6366f1' }} />
                    Mạng IP WAN: {doc.ipwan}
                </h3>
                <div style={{ display: 'flex', gap: '0.8rem', fontSize: '0.68rem', color: '#64748b', alignItems: 'center' }}>
                    {selectedDate === new Date().toLocaleDateString('en-CA') && (
                        <span style={{ marginRight: '0.5rem' }}>
                            Hiện tại: <strong style={{ color: '#10b981' }}>↑{stats.upload.curr.toFixed(2)} / ↓{stats.download.curr.toFixed(2)} Mbps</strong>
                        </span>
                    )}
                    <span>Upload Max: <strong style={{ color: '#4f46e5' }}>{stats.upload.max.toFixed(2)} Mbps</strong></span>
                    <span>Download Max: <strong style={{ color: '#d97706' }}>{stats.download.max.toFixed(2)} Mbps</strong></span>
                </div>
            </div>

            {/* Combined Chart */}
            <div style={{ width: '100%', height: 160 }} ref={chartRef} />

            {/* Stats Summary Table */}
            <div style={{ overflowX: 'auto', marginTop: '0.5rem' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.7rem', color: '#334155', textAlign: 'left' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid #cbd5e1', color: '#64748b' }}>
                            <th style={{ padding: '0.3rem 0.5rem' }}>Bản tin</th>
                            <th style={{ padding: '0.3rem 0.5rem' }}>Hiện tại</th>
                            <th style={{ padding: '0.3rem 0.5rem' }}>Cực đại (Max)</th>
                            <th style={{ padding: '0.3rem 0.5rem' }}>Cực tiểu (Min)</th>
                            <th style={{ padding: '0.3rem 0.5rem' }}>Trung bình (Avg)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style={{ borderBottom: '1px solid #f1f5f9', background: '#fafbfc' }}>
                            <td style={{ padding: '0.4rem 0.5rem', fontWeight: 700, color: uploadColor }}>Tải lên (Upload)</td>
                            <td style={{ padding: '0.4rem 0.5rem', fontFamily: 'monospace' }}>{stats.upload.curr.toFixed(2)} Mbps</td>
                            <td style={{ padding: '0.4rem 0.5rem', fontFamily: 'monospace', color: '#4f46e5', fontWeight: 700 }}>{stats.upload.max.toFixed(2)} Mbps</td>
                            <td style={{ padding: '0.4rem 0.5rem', fontFamily: 'monospace', color: '#0369a1' }}>{stats.upload.min.toFixed(2)} Mbps</td>
                            <td style={{ padding: '0.4rem 0.5rem', fontFamily: 'monospace' }}>{stats.upload.avg.toFixed(2)} Mbps</td>
                        </tr>
                        <tr>
                            <td style={{ padding: '0.4rem 0.5rem', fontWeight: 700, color: downloadColor }}>Tải về (Download)</td>
                            <td style={{ padding: '0.4rem 0.5rem', fontFamily: 'monospace' }}>{stats.download.curr.toFixed(2)} Mbps</td>
                            <td style={{ padding: '0.4rem 0.5rem', fontFamily: 'monospace', color: '#d97706', fontWeight: 700 }}>{stats.download.max.toFixed(2)} Mbps</td>
                            <td style={{ padding: '0.4rem 0.5rem', fontFamily: 'monospace', color: '#0369a1' }}>{stats.download.min.toFixed(2)} Mbps</td>
                            <td style={{ padding: '0.4rem 0.5rem', fontFamily: 'monospace' }}>{stats.download.avg.toFixed(2)} Mbps</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    )
}

export default function BandwidthChartSection({ deviceFilter, machines }: BandwidthChartSectionProps) {
    const { wsStatus } = useDashboardContext()

    const [selectedDate, setSelectedDate] = useState(() => {
        const d = new Date()
        return d.toLocaleDateString('en-CA')
    })
    const [bandwidthData, setBandwidthData] = useState<BandwidthDoc[]>([])
    const [timeFilter, setTimeFilter] = useState<'7h' | '24h'>('7h')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const apiDate = useMemo(() => {
        const parts = selectedDate.split('-')
        if (parts.length === 3) {
            return `${parts[2]}-${parts[1]}-${parts[0]}`
        }
        return ''
    }, [selectedDate])

    const loadStats = async (silent = false) => {
        if (!apiDate) return
        if (!silent) {
            setLoading(true)
        }
        setError(null)
        try {
            const data = await fetchBandwidthStats(apiDate)
            setBandwidthData(data)
        } catch (err) {
            console.error('Error fetching bandwidth stats:', err)
            if (!silent) {
                setError('Không thể tải dữ liệu băng thông.')
            }
        } finally {
            if (!silent) {
                setLoading(false)
            }
        }
    }

    useEffect(() => {
        void loadStats(false)

        const todayStr = new Date().toLocaleDateString('en-CA')
        const isToday = selectedDate === todayStr

        let intervalId: number | undefined
        if (isToday) {
            intervalId = window.setInterval(() => {
                void loadStats(true)
            }, 15000)
        }

        return () => {
            if (intervalId) {
                window.clearInterval(intervalId)
            }
        }
    }, [apiDate, selectedDate])

    const realTimeBwMap = useMemo(() => {
        const map = new Map<string, { sender: number; receiver: number }>()
        machines.forEach((m) => {
            const latest = m.latestItem?.data
            if (!latest) return
            const ipwan = latest.ipwan
            if (!ipwan) return
            
            // Check statusapp: active machines are statusapp === 1
            if (Number(latest.statusapp) !== 1) return
            
            const lastUpdatedStr = m.latestItem?.timestamp || latest.last_updated
            if (!lastUpdatedStr) return
            const lastUpdated = new Date(lastUpdatedStr).getTime()
            const oneMinAgo = Date.now() - 60000
            if (lastUpdated < oneMinAgo) return
            
            const sender = Number(latest.sender_mbps || 0)
            const receiver = Number(latest.receiver_mbps || 0)
            
            const curr = map.get(ipwan) || { sender: 0, receiver: 0 }
            map.set(ipwan, {
                sender: curr.sender + sender,
                receiver: curr.receiver + receiver,
            })
        })
        return map
    }, [machines])

    const filteredBandwidthDocs = useMemo(() => {
        if (deviceFilter === '__all__') {
            return bandwidthData
        }
        const selectedMachine = machines.find((m) => m.id === deviceFilter)
        const targetIpwan = selectedMachine?.latestItem?.data?.ipwan || ''
        if (!targetIpwan) return []
        return bandwidthData.filter((doc) => doc.ipwan === targetIpwan)
    }, [bandwidthData, deviceFilter, machines])


    return (
        <div className="bandwidth-section">
            {/* Toolbar */}
            <div className="bandwidth-toolbar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', gap: '1rem', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <label style={{ fontSize: '0.8rem', fontWeight: 700, color: '#475569' }} htmlFor="bandwidth-date">Chọn Ngày:</label>
                        <input
                            id="bandwidth-date"
                            type="date"
                            value={selectedDate}
                            onChange={(e) => setSelectedDate(e.target.value)}
                            style={{
                                padding: '0.4rem 0.75rem',
                                borderRadius: '10px',
                                border: '1px solid #cbd5e1',
                                fontSize: '0.8rem',
                                fontWeight: 600,
                                color: '#0f172a',
                                outline: 'none',
                            }}
                        />
                        {selectedDate === new Date().toLocaleDateString('en-CA') && wsStatus === 'connected' && (
                            <div
                                className="header-ws-badge header-ws-ok"
                                style={{
                                    padding: '0.25rem 0.6rem',
                                    fontSize: '0.65rem',
                                    borderRadius: '6px',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.3rem',
                                    fontWeight: 700,
                                    marginLeft: '0.5rem',
                                }}
                            >
                                <span className="header-ws-dot ws-pulse" />
                                REALTIME LIVE
                            </div>
                        )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <label style={{ fontSize: '0.8rem', fontWeight: 700, color: '#475569' }}>Khung giờ:</label>
                        <div style={{ display: 'inline-flex', background: '#f1f5f9', padding: '0.2rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                            <button
                                onClick={() => setTimeFilter('7h')}
                                style={{
                                    padding: '0.25rem 0.75rem',
                                    fontSize: '0.75rem',
                                    fontWeight: 700,
                                    borderRadius: '6px',
                                    border: 'none',
                                    background: timeFilter === '7h' ? '#fff' : 'transparent',
                                    color: timeFilter === '7h' ? '#6366f1' : '#64748b',
                                    boxShadow: timeFilter === '7h' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                }}
                                type="button"
                            >
                                7 giờ gần nhất
                            </button>
                            <button
                                onClick={() => setTimeFilter('24h')}
                                style={{
                                    padding: '0.25rem 0.75rem',
                                    fontSize: '0.75rem',
                                    fontWeight: 700,
                                    borderRadius: '6px',
                                    border: 'none',
                                    background: timeFilter === '24h' ? '#fff' : 'transparent',
                                    color: timeFilter === '24h' ? '#6366f1' : '#64748b',
                                    boxShadow: timeFilter === '24h' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                }}
                                type="button"
                            >
                                24 giờ (Cả ngày)
                            </button>
                        </div>
                    </div>
                </div>
                <button
                    onClick={() => void loadStats()}
                    disabled={loading}
                    className="refresh-btn"
                    style={{ padding: '0.4rem 1rem', fontSize: '0.75rem', fontWeight: 700 }}
                    type="button"
                >
                    LÀM MỚI
                </button>
            </div>



            {loading && (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem 0', color: '#6366f1', fontWeight: 700 }}>
                    Đang tải dữ liệu băng thông...
                </div>
            )}

            {error && (
                <div className="glass-card error-card" style={{ marginBottom: '1.5rem' }}>
                    {error}
                </div>
            )}

            {!loading && !error && filteredBandwidthDocs.length === 0 && (
                <div className="glass-card empty-card" style={{ marginBottom: '1.5rem', padding: '3rem' }}>
                    Chưa có dữ liệu băng thông IP WAN cho bộ lọc và ngày này.
                </div>
            )}

            {!loading && !error && filteredBandwidthDocs.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    {filteredBandwidthDocs.map((doc) => (
                        <IpwanBandwidthCard
                            key={doc.ipwan}
                            doc={doc}
                            selectedDate={selectedDate}
                            timeFilter={timeFilter}
                            realTimeBw={realTimeBwMap.get(doc.ipwan)}
                        />
                    ))}
                </div>
            )}
        </div>
    )
}
