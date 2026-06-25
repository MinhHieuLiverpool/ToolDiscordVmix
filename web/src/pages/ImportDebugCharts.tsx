import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
    GridComponent,
    TooltipComponent,
    LegendComponent,
    TitleComponent,
    DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// Register ECharts modules
echarts.use([
    LineChart,
    GridComponent,
    TooltipComponent,
    LegendComponent,
    TitleComponent,
    DataZoomComponent,
    CanvasRenderer
])

type ParsedLogLine = {
    timestamp?: string // Optional
    timeOnly: string // HH:MM:SS
    dateOnly?: string // Optional
    machineName: string
    ip?: string
    ipwan?: string
    rawJson: string
}

const parseMetrics = (rawJson: string) => {
    try {
        const obj = JSON.parse(rawJson)
        
        let cpu = 0
        if (obj.cpu !== undefined && obj.cpu !== null) cpu = parseFloat(obj.cpu)
        else if (obj.temperature !== undefined && obj.temperature !== null) cpu = parseFloat(obj.temperature)
        
        let ram = 0
        if (obj.ram !== undefined && obj.ram !== null) ram = parseFloat(obj.ram)
        else if (obj.memory !== undefined && obj.memory !== null) ram = parseFloat(obj.memory)
        
        let gpu = 0
        if (obj.gpu !== undefined && obj.gpu !== null) gpu = parseFloat(obj.gpu)
        
        let ping = 0
        if (obj.ping !== undefined && obj.ping !== null) {
            const pVal = parseFloat(obj.ping)
            if (!isNaN(pVal)) ping = pVal
        }
        
        let sender = 0
        if (obj.sender_mbps !== undefined && obj.sender_mbps !== null) sender = parseFloat(obj.sender_mbps)
        
        let receiver = 0
        if (obj.receiver_mbps !== undefined && obj.receiver_mbps !== null) receiver = parseFloat(obj.receiver_mbps)
        
        return { cpu, ram, gpu, ping, sender, receiver }
    } catch (e) {
        return { cpu: 0, ram: 0, gpu: 0, ping: 0, sender: 0, receiver: 0 }
    }
}

export default function ImportDebugChartsPage() {
    const location = useLocation()
    const navigate = useNavigate()

    const state = useMemo(() => {
        try {
            const stored = sessionStorage.getItem('debug_chart_data')
            if (stored) {
                return JSON.parse(stored) as { logs?: ParsedLogLine[]; fileName?: string }
            }
        } catch (e) {
            console.error('Failed to parse debug_chart_data from sessionStorage', e)
        }
        return location.state as { logs?: ParsedLogLine[]; fileName?: string } | null
    }, [location.state])

    const logLines = state?.logs || []
    const fileName = state?.fileName || 'Offline logs'

    // Get list of unique machine names
    const uniqueMachines = useMemo(() => {
        const names = logLines.map((l) => l.machineName).filter(Boolean)
        return Array.from(new Set(names)).sort()
    }, [logLines])

    const [selectedMachine, setSelectedMachine] = useState<string>('')

    // Default to the first machine if available
    useEffect(() => {
        if (uniqueMachines.length > 0 && !selectedMachine) {
            setSelectedMachine(uniqueMachines[0])
        }
    }, [uniqueMachines, selectedMachine])

    // Filter logs for the selected machine and sample every 5 seconds
    const machineLogs = useMemo(() => {
        if (!selectedMachine) return []
        const rawLogs = logLines.filter((l) => l.machineName === selectedMachine)

        const sampled: ParsedLogLine[] = []
        let lastSeconds = -99999

        rawLogs.forEach((log) => {
            const parts = log.timeOnly.split(':')
            const hrs = parseInt(parts[0], 10)
            const mins = parts[1] ? parseInt(parts[1], 10) : 0
            const secs = parts[2] ? parseInt(parts[2], 10) : 0

            if (isNaN(hrs)) return

            const currentSeconds = hrs * 3600 + mins * 60 + secs
            if (currentSeconds - lastSeconds >= 5 || currentSeconds < lastSeconds) {
                sampled.push(log)
                lastSeconds = currentSeconds
            }
        })

        return sampled
    }, [logLines, selectedMachine])

    // Calculate statistics
    const stats = useMemo(() => {
        if (machineLogs.length === 0) return null
        let totalCpu = 0, maxCpu = 0
        let totalRam = 0, maxRam = 0
        let totalGpu = 0, maxGpu = 0
        let totalPing = 0, maxPing = 0, pingCount = 0
        let maxSender = 0, maxReceiver = 0

        machineLogs.forEach((log) => {
            const m = parseMetrics(log.rawJson)
            totalCpu += m.cpu
            if (m.cpu > maxCpu) maxCpu = m.cpu
            
            totalRam += m.ram
            if (m.ram > maxRam) maxRam = m.ram

            totalGpu += m.gpu
            if (m.gpu > maxGpu) maxGpu = m.gpu

            if (m.ping > 0) {
                totalPing += m.ping
                pingCount++
                if (m.ping > maxPing) maxPing = m.ping
            }

            if (m.sender > maxSender) maxSender = m.sender
            if (m.receiver > maxReceiver) maxReceiver = m.receiver
        })

        const count = machineLogs.length
        return {
            avgCpu: totalCpu / count,
            maxCpu,
            avgRam: totalRam / count,
            maxRam,
            avgGpu: totalGpu / count,
            maxGpu,
            avgPing: pingCount > 0 ? totalPing / pingCount : 0,
            maxPing,
            maxSender,
            maxReceiver,
        }
    }, [machineLogs])

    // Chart refs
    const systemChartRef = useRef<HTMLDivElement>(null)
    const bandwidthChartRef = useRef<HTMLDivElement>(null)
    const pingChartRef = useRef<HTMLDivElement>(null)

    // Chart instances
    const systemChartInst = useRef<echarts.ECharts | null>(null)
    const bandwidthChartInst = useRef<echarts.ECharts | null>(null)
    const pingChartInst = useRef<echarts.ECharts | null>(null)

    // Destroy and initialize charts on logs/machine change
    useEffect(() => {
        if (machineLogs.length === 0) return

        const timeline = machineLogs.map((l) => l.timeOnly)
        const parsedData = machineLogs.map((l) => parseMetrics(l.rawJson))

        const cpus = parsedData.map((d) => d.cpu)
        const rams = parsedData.map((d) => d.ram)
        const gpus = parsedData.map((d) => d.gpu)
        const pings = parsedData.map((d) => d.ping)
        const senders = parsedData.map((d) => d.sender)
        const receivers = parsedData.map((d) => d.receiver)

        // Calculate a reasonable default start percentage to zoom to show the last ~300 data points by default
        const defaultZoomStart = Math.max(0, 100 - (100 * 300) / Math.max(1, timeline.length))

        // Initialize System Resources Chart
        if (systemChartRef.current) {
            if (!systemChartInst.current) {
                systemChartInst.current = echarts.init(systemChartRef.current)
            }
            systemChartInst.current.setOption({
                title: { text: 'Hiệu Năng Hệ Thống (%)', textStyle: { fontSize: 13, fontWeight: 700, color: '#334155', fontFamily: 'Inter' } },
                grid: { top: 40, right: 15, bottom: 55, left: 35 },
                tooltip: { 
                    trigger: 'axis',
                    backgroundColor: 'rgba(255, 255, 255, 0.98)',
                    borderColor: '#e2e8f0',
                    borderWidth: 1,
                    textStyle: { color: '#1e293b', fontSize: 11, fontFamily: 'Inter' },
                    shadowColor: 'rgba(0, 0, 0, 0.05)',
                    shadowBlur: 10
                },
                legend: { data: ['CPU', 'RAM', 'GPU'], right: 10, top: 0, textStyle: { color: '#64748b', fontSize: 11 } },
                xAxis: { 
                    type: 'category', 
                    data: timeline, 
                    axisLabel: { color: '#64748b', fontSize: 9 },
                    axisLine: { lineStyle: { color: '#cbd5e1' } }
                },
                yAxis: { 
                    type: 'value', 
                    min: 0, 
                    max: 100, 
                    splitLine: { lineStyle: { color: 'rgba(226, 232, 240, 0.6)', type: 'dashed' } },
                    axisLabel: { color: '#64748b', fontSize: 9 }
                },
                dataZoom: [
                    { type: 'slider', show: true, xAxisIndex: [0], start: defaultZoomStart, end: 100, bottom: 5, height: 16, textStyle: { color: '#64748b', fontSize: 9 } },
                    { type: 'inside', xAxisIndex: [0], start: defaultZoomStart, end: 100 }
                ],
                series: [
                    { 
                        name: 'CPU', 
                        type: 'line', 
                        data: cpus, 
                        color: '#6366f1', 
                        showSymbol: false, 
                        smooth: true,
                        lineStyle: { width: 2 },
                        areaStyle: {
                            color: {
                                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: 'rgba(99, 102, 241, 0.15)' },
                                    { offset: 1, color: 'rgba(99, 102, 241, 0)' }
                                ]
                            }
                        }
                    },
                    { 
                        name: 'RAM', 
                        type: 'line', 
                        data: rams, 
                        color: '#0ea5e9', 
                        showSymbol: false, 
                        smooth: true,
                        lineStyle: { width: 2 },
                        areaStyle: {
                            color: {
                                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: 'rgba(14, 165, 233, 0.15)' },
                                    { offset: 1, color: 'rgba(14, 165, 233, 0)' }
                                ]
                            }
                        }
                    },
                    { 
                        name: 'GPU', 
                        type: 'line', 
                        data: gpus, 
                        color: '#f97316', 
                        showSymbol: false, 
                        smooth: true,
                        lineStyle: { width: 2 },
                        areaStyle: {
                            color: {
                                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: 'rgba(249, 115, 22, 0.15)' },
                                    { offset: 1, color: 'rgba(249, 115, 22, 0)' }
                                ]
                            }
                        }
                    },
                ]
            })
        }

        // Initialize Bandwidth Chart
        if (bandwidthChartRef.current) {
            if (!bandwidthChartInst.current) {
                bandwidthChartInst.current = echarts.init(bandwidthChartRef.current)
            }
            bandwidthChartInst.current.setOption({
                title: { text: 'Băng thông mạng (Mbps)', textStyle: { fontSize: 13, fontWeight: 700, color: '#334155', fontFamily: 'Inter' } },
                grid: { top: 40, right: 15, bottom: 55, left: 35 },
                tooltip: { 
                    trigger: 'axis',
                    backgroundColor: 'rgba(255, 255, 255, 0.98)',
                    borderColor: '#e2e8f0',
                    borderWidth: 1,
                    textStyle: { color: '#1e293b', fontSize: 11, fontFamily: 'Inter' },
                    shadowColor: 'rgba(0, 0, 0, 0.05)',
                    shadowBlur: 10
                },
                legend: { data: ['Sender', 'Receiver'], right: 10, top: 0, textStyle: { color: '#64748b', fontSize: 11 } },
                xAxis: { 
                    type: 'category', 
                    data: timeline, 
                    axisLabel: { color: '#64748b', fontSize: 9 },
                    axisLine: { lineStyle: { color: '#cbd5e1' } }
                },
                yAxis: { 
                    type: 'value', 
                    splitLine: { lineStyle: { color: 'rgba(226, 232, 240, 0.6)', type: 'dashed' } },
                    axisLabel: { color: '#64748b', fontSize: 9 }
                },
                dataZoom: [
                    { type: 'slider', show: true, xAxisIndex: [0], start: defaultZoomStart, end: 100, bottom: 5, height: 16, textStyle: { color: '#64748b', fontSize: 9 } },
                    { type: 'inside', xAxisIndex: [0], start: defaultZoomStart, end: 100 }
                ],
                series: [
                    { 
                        name: 'Sender', 
                        type: 'line', 
                        data: senders, 
                        color: '#10b981', 
                        showSymbol: false, 
                        smooth: true,
                        lineStyle: { width: 2 },
                        areaStyle: {
                            color: {
                                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: 'rgba(16, 185, 129, 0.12)' },
                                    { offset: 1, color: 'rgba(16, 185, 129, 0)' }
                                ]
                            }
                        }
                    },
                    { 
                        name: 'Receiver', 
                        type: 'line', 
                        data: receivers, 
                        color: '#ec4899', 
                        showSymbol: false, 
                        smooth: true,
                        lineStyle: { width: 2 },
                        areaStyle: {
                            color: {
                                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: 'rgba(236, 72, 153, 0.12)' },
                                    { offset: 1, color: 'rgba(236, 72, 153, 0)' }
                                ]
                            }
                        }
                    },
                ]
            })
        }

        // Initialize Ping Chart
        if (pingChartRef.current) {
            if (!pingChartInst.current) {
                pingChartInst.current = echarts.init(pingChartRef.current)
            }
            pingChartInst.current.setOption({
                title: { text: 'Độ trễ Ping (ms)', textStyle: { fontSize: 13, fontWeight: 700, color: '#334155', fontFamily: 'Inter' } },
                grid: { top: 35, right: 15, bottom: 55, left: 35 },
                tooltip: { 
                    trigger: 'axis',
                    backgroundColor: 'rgba(255, 255, 255, 0.98)',
                    borderColor: '#e2e8f0',
                    borderWidth: 1,
                    textStyle: { color: '#1e293b', fontSize: 11, fontFamily: 'Inter' },
                    shadowColor: 'rgba(0, 0, 0, 0.05)',
                    shadowBlur: 10
                },
                legend: { data: ['Ping'], right: 10, top: 0, textStyle: { color: '#64748b', fontSize: 11 } },
                xAxis: { 
                    type: 'category', 
                    data: timeline, 
                    axisLabel: { color: '#64748b', fontSize: 9 },
                    axisLine: { lineStyle: { color: '#cbd5e1' } }
                },
                yAxis: { 
                    type: 'value', 
                    splitLine: { lineStyle: { color: 'rgba(226, 232, 240, 0.6)', type: 'dashed' } },
                    axisLabel: { color: '#64748b', fontSize: 9 }
                },
                dataZoom: [
                    { type: 'slider', show: true, xAxisIndex: [0], start: defaultZoomStart, end: 100, bottom: 5, height: 16, textStyle: { color: '#64748b', fontSize: 9 } },
                    { type: 'inside', xAxisIndex: [0], start: defaultZoomStart, end: 100 }
                ],
                series: [
                    { 
                        name: 'Ping', 
                        type: 'line', 
                        data: pings, 
                        color: '#f59e0b', 
                        showSymbol: false, 
                        smooth: true,
                        lineStyle: { width: 2 },
                        areaStyle: {
                            color: {
                                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [
                                    { offset: 0, color: 'rgba(245, 158, 11, 0.12)' },
                                    { offset: 1, color: 'rgba(245, 158, 11, 0)' }
                                ]
                            }
                        }
                    }
                ]
            })
        }

    }, [machineLogs])

    // Cleanup ECharts instances on unmount
    useEffect(() => {
        return () => {
            systemChartInst.current?.dispose()
            systemChartInst.current = null
            bandwidthChartInst.current?.dispose()
            bandwidthChartInst.current = null
            pingChartInst.current?.dispose()
            pingChartInst.current = null
        }
    }, [])

    // Resize handlers
    useEffect(() => {
        const handleResize = () => {
            systemChartInst.current?.resize()
            bandwidthChartInst.current?.resize()
            pingChartInst.current?.resize()
        }
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [])

    if (logLines.length === 0) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center', minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', backgroundColor: '#f8fafc' }}>
                <h3 style={{ color: '#64748b', marginBottom: '1rem' }}>Không có dữ liệu log debug để vẽ biểu đồ.</h3>
                <button className="viewsync-primary-btn" type="button" onClick={() => navigate('/debug-logs/import')}>
                    Quay lại trang Import Logs
                </button>
            </div>
        )
    }

    return (
        <div style={{ padding: '1.5rem 2rem 2.5rem', minHeight: '100vh', backgroundColor: '#f8fafc', boxSizing: 'border-box' }}>
            <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.2rem' }}>
                            <h2 className="page-title" style={{ margin: 0, fontSize: '1.5rem', fontWeight: 800, color: '#0f172a' }}>Biểu đồ Phân tích Log Debug</h2>
                        </div>
                        <p className="page-description" style={{ color: '#475569', fontSize: '0.85rem', margin: 0 }}>
                            Đang phân tích tệp: <strong style={{ color: '#6366f1', textDecoration: 'underline' }}>{fileName}</strong> &bull; <span style={{ color: '#0ea5e9', fontWeight: 600 }}>{logLines.length} dòng logs</span>
                        </p>
                    </div>
                    <button
                        className="viewsync-outline-btn"
                        type="button"
                        onClick={() => {
                            if (window.opener || window.history.length <= 1) {
                                window.close()
                            } else {
                                navigate('/debug-logs/import', { state })
                            }
                        }}
                        style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                    >
                        &times; Đóng trang / Quay lại
                    </button>
                </div>

                {/* Selection and stats block */}
                <div className="card-light" style={{ padding: '1.25rem', marginBottom: '1.5rem', boxShadow: '0 4px 20px -2px rgba(148, 163, 184, 0.08), 0 2px 8px -1px rgba(148, 163, 184, 0.04)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1.5rem' }}>
                        <div style={{ minWidth: '240px' }}>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>Chọn thiết bị phân tích</label>
                            <select
                                value={selectedMachine}
                                onChange={(e) => setSelectedMachine(e.target.value)}
                                style={{
                                    border: '1px solid #e2e8f0',
                                    borderRadius: '8px',
                                    padding: '0.45rem 0.75rem',
                                    width: '100%',
                                    fontSize: '0.85rem',
                                    backgroundColor: '#fff',
                                    color: '#1e293b',
                                    outline: 'none',
                                    cursor: 'pointer'
                                }}
                            >
                                {uniqueMachines.map((m) => (
                                    <option key={m} value={m}>{m}</option>
                                ))}
                            </select>
                        </div>

                        {stats && (
                            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', flexGrow: 1, justifyContent: 'flex-end' }}>
                                <div style={{ padding: '0.5rem 0.85rem', background: 'linear-gradient(135deg, #f5f3ff 0%, #edd4ff 100%)', border: '1px solid #d8b4fe', borderRadius: '10px', textAlign: 'center', minWidth: '95px', boxShadow: '0 2px 4px rgba(124,58,237,0.02)' }}>
                                    <div style={{ fontSize: '0.65rem', color: '#6d28d9', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.15rem' }}>CPU (Avg/Max)</div>
                                    <div style={{ fontSize: '0.95rem', color: '#5b21b6', fontWeight: 800 }}>{stats.avgCpu.toFixed(1)}% / {stats.maxCpu.toFixed(1)}%</div>
                                </div>
                                <div style={{ padding: '0.5rem 0.85rem', background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)', border: '1px solid #bae6fd', borderRadius: '10px', textAlign: 'center', minWidth: '95px', boxShadow: '0 2px 4px rgba(14,165,233,0.02)' }}>
                                    <div style={{ fontSize: '0.65rem', color: '#0369a1', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.15rem' }}>RAM (Avg/Max)</div>
                                    <div style={{ fontSize: '0.95rem', color: '#075985', fontWeight: 800 }}>{stats.avgRam.toFixed(1)}% / {stats.maxRam.toFixed(1)}%</div>
                                </div>
                                <div style={{ padding: '0.5rem 0.85rem', background: 'linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%)', border: '1px solid #fed7aa', borderRadius: '10px', textAlign: 'center', minWidth: '95px', boxShadow: '0 2px 4px rgba(249,115,22,0.02)' }}>
                                    <div style={{ fontSize: '0.65rem', color: '#c2410c', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.15rem' }}>GPU (Avg/Max)</div>
                                    <div style={{ fontSize: '0.95rem', color: '#9a3412', fontWeight: 800 }}>{stats.avgGpu.toFixed(1)}% / {stats.maxGpu.toFixed(1)}%</div>
                                </div>
                                <div style={{ padding: '0.5rem 0.85rem', background: 'linear-gradient(135deg, #fefce8 0%, #fef9c3 100%)', border: '1px solid #fef08a', borderRadius: '10px', textAlign: 'center', minWidth: '95px', boxShadow: '0 2px 4px rgba(234,179,8,0.02)' }}>
                                    <div style={{ fontSize: '0.65rem', color: '#a16207', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.15rem' }}>Ping (Avg/Max)</div>
                                    <div style={{ fontSize: '0.95rem', color: '#854d0e', fontWeight: 800 }}>{stats.avgPing.toFixed(0)}ms / {stats.maxPing.toFixed(0)}ms</div>
                                </div>
                                <div style={{ padding: '0.5rem 0.85rem', background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)', border: '1px solid #bbf7d0', borderRadius: '10px', textAlign: 'center', minWidth: '115px', boxShadow: '0 2px 4px rgba(16,185,129,0.02)' }}>
                                    <div style={{ fontSize: '0.65rem', color: '#15803d', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.15rem' }}>Băng thông (Max S/R)</div>
                                    <div style={{ fontSize: '0.95rem', color: '#166534', fontWeight: 800 }}>{stats.maxSender.toFixed(1)}M / {stats.maxReceiver.toFixed(1)}M</div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Charts grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                    <div className="card-light" style={{ padding: '1.25rem', border: '1px solid #e2e8f0', boxShadow: '0 4px 20px -2px rgba(148, 163, 184, 0.08), 0 2px 8px -1px rgba(148, 163, 184, 0.04)' }}>
                        <div ref={systemChartRef} style={{ width: '100%', height: '200px' }} />
                    </div>
                    <div className="card-light" style={{ padding: '1.25rem', border: '1px solid #e2e8f0', boxShadow: '0 4px 20px -2px rgba(148, 163, 184, 0.08), 0 2px 8px -1px rgba(148, 163, 184, 0.04)' }}>
                        <div ref={bandwidthChartRef} style={{ width: '100%', height: '200px' }} />
                    </div>
                    <div className="card-light" style={{ padding: '1.25rem', border: '1px solid #e2e8f0', boxShadow: '0 4px 20px -2px rgba(148, 163, 184, 0.08), 0 2px 8px -1px rgba(148, 163, 184, 0.04)' }}>
                        <div ref={pingChartRef} style={{ width: '100%', height: '200px' }} />
                    </div>
                </div>
            </div>
        </div>
    )
}
