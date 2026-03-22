import { toNumber } from '../types'
import type { BackendLogItem } from '../services/api'

export default function MachineStatusCard({
    item,
    index,
}: {
    item: BackendLogItem
    index: number
}) {
    const srtOnline = ['ONLINE', 'ON', '1', 'TRUE'].includes(String(item.data.status || '').toUpperCase())
    const cpuVal = toNumber(item.data.cpu)
    const ramVal = toNumber(item.data.memory)
    const gpuVal = toNumber(item.data.gpu)
    const senderVal = toNumber(item.data.sender_mbps)
    const receiverVal = toNumber(item.data.receiver_mbps)
    const cpuHigh = cpuVal !== null && cpuVal > 50
    const ramHigh = ramVal !== null && ramVal > 50
    const gpuHigh = gpuVal !== null && gpuVal > 80
    const hasHighUsage = cpuHigh || ramHigh
    const appOn = Number(item.data.statusapp) === 1
    const recOn = Boolean(item.data.vmix_recording)
    const liveOn = Boolean(item.data.vmix_streaming)
    const extOn = Boolean(item.data.vmix_external)

    const timeText = (() => {
        const raw = item.timestamp || ''
        const d = new Date(raw)
        if (Number.isNaN(d.getTime())) return raw || '-'
        return d.toLocaleString('vi-VN', { hour12: false })
    })()

    const onOff = (v: boolean) => (v ? 'ON' : 'OFF')

    return (
        <div
            className={`glass-card card-animate machine-card ${srtOnline ? 'card-online' : 'card-offline'} ${hasHighUsage ? 'card-overload' : ''}`}
            style={{ animationDelay: `${index * 40}ms` }}
        >
            {/* Header */}
            <div className="card-header">
                <h3 className="card-name">{item.data.name || 'Unknown'}</h3>
                <span className={`status-badge ${srtOnline ? 'badge-online' : 'badge-offline'}`}>
                    <span className={`status-dot ${srtOnline ? 'dot-online' : 'dot-offline'}`} />
                    {onOff(srtOnline)}
                </span>
            </div>

            {/* IP info */}
            <div className="card-info">
                <div className="info-row">
                    <span className="info-label">IP</span>
                    <span className="info-value mono">{item.data.ip || '-'}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">WAN</span>
                    <span className="info-value mono">{item.data.ipwan || '-'}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">Port</span>
                    <span className="info-value mono">{item.data.port || '-'}</span>
                </div>
            </div>

            <div className="card-divider" />

            {/* Metrics Row 1: CPU / RAM / Ping */}
            <div className="card-metrics">
                <div className={`metric-box ${cpuHigh ? 'metric-box-danger' : ''}`}>
                    <div className="metric-label">CPU</div>
                    <div className={`metric-value ${cpuHigh ? 'metric-danger' : 'metric-cpu'}`}>
                        {cpuVal !== null ? `${cpuVal.toFixed(0)}%` : '-'}
                    </div>
                </div>
                <div className={`metric-box ${ramHigh ? 'metric-box-danger' : ''}`}>
                    <div className="metric-label">RAM</div>
                    <div className={`metric-value ${ramHigh ? 'metric-danger' : 'metric-ram'}`}>
                        {ramVal !== null ? `${ramVal.toFixed(0)}%` : '-'}
                    </div>
                </div>
                <div className={`metric-box ${gpuHigh ? 'metric-box-danger' : ''}`}>
                    <div className="metric-label">GPU</div>
                    <div className={`metric-value ${gpuHigh ? 'metric-danger' : 'metric-gpu'}`}>
                        {gpuVal !== null ? `${gpuVal.toFixed(0)}%` : '-'}
                    </div>
                </div>
            </div>

            {/* Metrics Row 2: Ping / APP / EXT */}
            <div className="card-metrics">
                <div className="metric-box">
                    <div className="metric-label">Ping</div>
                    <div className="metric-value metric-ping">{item.data.ping ?? '-'}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">APP</div>
                    <div className={`metric-value ${appOn ? 'metric-ping' : 'metric-warn'}`}>{onOff(appOn)}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">Timeout</div>
                    <div className="metric-value metric-cpu">{item.data.ping_timeouts ?? 0}</div>
                </div>
            </div>

            {/* Metrics Row 3: Sender / Receiver / EXT */}
            <div className="card-metrics">
                <div className="metric-box">
                    <div className="metric-label">Sender</div>
                    <div className="metric-value metric-sender">
                        {senderVal !== null ? `${senderVal.toFixed(1)}` : '-'}
                        {senderVal !== null && <span className="metric-unit">Mbps</span>}
                    </div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">Receiver</div>
                    <div className="metric-value metric-receiver">
                        {receiverVal !== null ? `${receiverVal.toFixed(1)}` : '-'}
                        {receiverVal !== null && <span className="metric-unit">Mbps</span>}
                    </div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">EXT</div>
                    <div className={`metric-value ${extOn ? 'metric-ping' : 'metric-cpu'}`}>{onOff(extOn)}</div>
                </div>
            </div>

            {/* Extra info */}
            <div className="card-extra">
                <div className="info-row">
                    <span className="info-label">Resolution</span>
                    <span className="info-value">{item.data.resolution || '-'}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">SRT</span>
                    <span
                        className={`info-value ${item.data.srt_quality?.toUpperCase() === 'GOOD'
                                ? 'srt-good'
                                : item.data.srt_quality?.toUpperCase() === 'BAD'
                                    ? 'srt-bad'
                                    : ''
                            }`}
                    >
                        {item.data.srt_quality || '-'}
                    </span>
                </div>
                <div className="info-row">
                    <span className="info-label">vMix</span>
                    <span className="info-value">
                        REC {onOff(recOn)} | LIVE {onOff(liveOn)}
                    </span>
                </div>
                {item.data.srt_off_time ? (
                    <div className="info-row">
                        <span className="info-label">SRT Off</span>
                        <span className="info-value mono">{item.data.srt_off_time}</span>
                    </div>
                ) : null}
            </div>

            <div className="card-timestamp">{timeText}</div>
        </div>
    )
}
