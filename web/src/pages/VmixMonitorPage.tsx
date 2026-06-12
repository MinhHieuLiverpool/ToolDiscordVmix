import { useMemo, useState } from 'react'
import { useDashboardContext } from '../hooks/useDashboardContext'
import { toNumber } from '../types'
import type { BackendLogItem } from '../services/api'

function checkOn(value: unknown): boolean {
    const text = String(value || '').toUpperCase()
    return ['ONLINE', 'ON', '1', 'TRUE', 'RUNNING', 'LIVE', 'ACTIVE'].includes(text)
}

function MetricBadge({ label, value, unit, isHigh }: { label: string; value: string; unit?: string; isHigh?: boolean }) {
    const labelKey = label.trim().toUpperCase()
    const labelClass = labelKey === 'CPU'
        ? 'vmix-metric-label vmix-metric-label-cpu'
        : labelKey === 'RAM'
        ? 'vmix-metric-label vmix-metric-label-ram'
        : labelKey === 'GPU'
            ? 'vmix-metric-label vmix-metric-label-gpu'
            : 'vmix-metric-label'

    return (
        <div className={`vmix-metric-box ${isHigh ? 'vmix-metric-danger' : ''}`}>
            <div className={labelClass}>{label}</div>
            <div className={`vmix-metric-value ${isHigh ? 'text-danger' : ''}`}>
                {value}{unit && <span className="vmix-metric-unit">{unit}</span>}
            </div>
        </div>
    )
}

function StatusIndicator({ label, isOn, colorOn, colorOff }: { label: string; isOn: boolean; colorOn: string; colorOff: string }) {
    const bg = isOn ? colorOn : colorOff
    const textColor = isOn ? colorOn : '#94a3b8'
    return (
        <div className="vmix-status-chip" style={{ borderColor: bg }}>
            <span className="vmix-status-dot" style={{ background: bg }} />
            <span className="vmix-status-chip-label">{label}</span>
            <span className="vmix-status-chip-val" style={{ color: textColor, fontWeight: 800 }}>
                {isOn ? 'ON' : 'OFF'}
            </span>
        </div>
    )
}

function MachineMonitorCard({ item, index }: { item: BackendLogItem; index: number }) {
    const appOn = checkOn(item.data.statusapp)
    const recOn = checkOn(item.data.vmix_recording)
    const liveOn = checkOn(item.data.vmix_streaming)
    const extOn = checkOn(item.data.vmix_external)

    const cpuVal = toNumber(item.data.temperature)
    const ramVal = toNumber(item.data.memory)
    const gpuVal = toNumber(item.data.gpu)
    const rawSender = toNumber(item.data.sender_mbps)
    const rawReceiver = toNumber(item.data.receiver_mbps)

    const senderVal = rawSender !== null && rawSender > 0.02 ? rawSender : 0
    const receiverVal = rawReceiver !== null && rawReceiver > 0.02 ? rawReceiver : 0

    const cpuHigh = cpuVal !== null && cpuVal > 50
    const ramHigh = ramVal !== null && ramVal > 50
    const gpuHigh = gpuVal !== null && gpuVal > 50
    const hasOverload = cpuHigh || ramHigh || gpuHigh

    return (
        <div
            className={`card-light vmix-monitor-card ${hasOverload ? 'vmix-card-overload' : ''} ${appOn ? 'vmix-card-online' : 'vmix-card-offline'}`}
            style={{ animationDelay: `${index * 40}ms` }}
        >
            {/* Header */}
            <div className="vmix-card-header">
                <div>
                    <h3 className="vmix-card-name">{item.data.name || 'Unknown Device'}</h3>
                    <p className="vmix-card-ip mono">{item.data.ip || '-'}:{item.data.port || '-'}</p>
                </div>
                <span className={`pill-light ${appOn ? 'pill-light-on' : 'pill-light-off'}`}>
                    APP {appOn ? 'ON' : 'OFF'}
                </span>
            </div>

            {/* PC Metrics */}
            <div className="vmix-section-label">Thông số PC</div>
            <div className="vmix-metrics-grid">
                <MetricBadge label="CPU" value={cpuVal !== null ? `${cpuVal.toFixed(0)}` : '-'} unit="%" isHigh={cpuHigh} />
                <MetricBadge label="RAM" value={ramVal !== null ? `${ramVal.toFixed(0)}` : '-'} unit="%" isHigh={ramHigh} />
                <MetricBadge label="GPU" value={gpuVal !== null ? `${gpuVal.toFixed(0)}` : '-'} unit="%" isHigh={gpuHigh} />
                <MetricBadge 
                    label="PING" 
                    value={item.data.ping !== null && item.data.ping !== undefined ? String(item.data.ping) : '0'} 
                    unit="ms" 
                    isHigh={item.data.ping === null || item.data.ping === undefined}
                />
            </div>

            {/* Vmix Status - with distinct colors */}
            <div className="vmix-section-label">Vmix Status</div>
            <div className="vmix-status-chips">
                <StatusIndicator label="REC" isOn={recOn} colorOn="#ef4444" colorOff="#e2e8f0" />
                <StatusIndicator label="LIVE" isOn={liveOn} colorOn="#10b981" colorOff="#e2e8f0" />
                <StatusIndicator label="EXT" isOn={extOn} colorOn="#6366f1" colorOff="#e2e8f0" />
            </div>

            {/* Sender / Receiver */}
            <div className="vmix-section-label">Vmix Sender / Receiver</div>
            <div className="vmix-metrics-grid vmix-metrics-2col">
                <div className={`vmix-metric-box ${senderVal > 0 ? 'vmix-metric-active-sender' : ''}`}>
                    <div className="vmix-metric-label">SENDER</div>
                    <div className="vmix-metric-value" style={{ color: senderVal > 0 ? '#ec4899' : '#94a3b8' }}>
                        {senderVal.toFixed(2)}<span className="vmix-metric-unit"> Mbps</span>
                    </div>
                </div>
                <div className={`vmix-metric-box ${receiverVal > 0 ? 'vmix-metric-active-receiver' : ''}`}>
                    <div className="vmix-metric-label">RECEIVER</div>
                    <div className="vmix-metric-value" style={{ color: receiverVal > 0 ? '#f97316' : '#94a3b8' }}>
                        {receiverVal.toFixed(2)}<span className="vmix-metric-unit"> Mbps</span>
                    </div>
                </div>
            </div>

            {/* Extra Info */}
            <div className="vmix-extra-row">
                <span className="vmix-extra-label">Resolution:</span>
                <span className="vmix-extra-value mono">{item.data.resolution || '-'}</span>
            </div>
            <div className="vmix-extra-row">
                <span className="vmix-extra-label">MAC Address:</span>
                <span className="vmix-extra-value mono">{item.data.mac_address || '-'}</span>
            </div>
            <div className="vmix-extra-row">
                <span className="vmix-extra-label">Network Speed:</span>
                <span className="vmix-extra-value">{item.data.network_speed || '-'}</span>
            </div>
            <div className="vmix-extra-row">
                <span className="vmix-extra-label">WAN IP:</span>
                <span className="vmix-extra-value mono">{item.data.ipwan || '-'}</span>
            </div>
        </div>
    )
}

export default function VmixMonitorPage() {
    const { rows, loading, error } = useDashboardContext()
    const [searchTerm, setSearchTerm] = useState('')

    const filteredRows = useMemo(() => {
        if (!searchTerm.trim()) return rows
        const term = searchTerm.toLowerCase()
        return rows.filter(
            (item) =>
                (item.data.name || '').toLowerCase().includes(term) ||
                (item.data.ip || '').toLowerCase().includes(term),
        )
    }, [rows, searchTerm])

    if (loading) {
        return (
            <>
                <div className="page-header">
                    <h2 className="page-title">Vmix Monitor</h2>
                    <p className="page-description">Thông số PC và Vmix Sender/Receiver.</p>
                </div>
                <div className="vmix-grid">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <div key={`skel-${i}`} className="card-light skeleton-card-light shimmer-loading" />
                    ))}
                </div>
            </>
        )
    }

    if (error) {
        return (
            <>
                <div className="page-header">
                    <h2 className="page-title">Vmix Monitor</h2>
                </div>
                <div className="card-light error-card-light">{error}</div>
            </>
        )
    }

    return (
        <>
            <div className="page-header">
                <h2 className="page-title">Vmix Monitor</h2>
                <p className="page-description">Giám sát thông số PC và trạng thái Vmix Sender/Receiver theo thời gian thực.</p>
            </div>

            {/* Search */}
            <div className="table-toolbar">
                <div className="table-search-wrap">
                    <svg className="table-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                        className="table-search-input"
                        type="text"
                        placeholder="Tìm theo tên máy, IP..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            {filteredRows.length === 0 ? (
                <div className="card-light" style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
                    Chưa có dữ liệu.
                </div>
            ) : (
                <div className="vmix-grid">
                    {filteredRows.map((item, index) => (
                        <MachineMonitorCard
                            key={`${item.data.ip || 'ip'}-${item.data.port || 'port'}-${index}`}
                            item={item}
                            index={index}
                        />
                    ))}
                </div>
            )}
        </>
    )
}
