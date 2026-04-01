import { useState } from 'react'
import { toNumber } from '../types'
import { normalizeSrtList, normalizeStreamList, type BackendLogItem } from '../services/api'
import Dialog from './ui/Dialog'
import { renderStreamCard, toOnOff } from './DialogHelpers'

function checkOn(value: unknown): boolean {
    const text = String(value || '').toUpperCase()
    return ['ONLINE', 'ON', '1', 'TRUE', 'RUNNING', 'LIVE', 'ACTIVE'].includes(text)
}

export default function MachineStatusCard({
    item,
    index,
}: {
    item: BackendLogItem
    index: number
}) {
    const [isStreamOpen, setIsStreamOpen] = useState(false)

    const srtOnline = checkOn(item.data.status)
    const appOn = checkOn(item.data.statusapp)
    const recOn = checkOn(item.data.vmix_recording)
    const liveOn = checkOn(item.data.vmix_streaming)

    const cpuVal = toNumber(item.data.temperature)
    const ramVal = toNumber(item.data.memory)
    const gpuVal = toNumber(item.data.gpu)
    const rawSender = toNumber(item.data.sender_mbps)
    const rawReceiver = toNumber(item.data.receiver_mbps)

    const senderVal = (rawSender !== null && rawSender > 0.02) ? rawSender : 0
    const receiverVal = (rawReceiver !== null && rawReceiver > 0.02) ? rawReceiver : 0

    const cpuHigh = cpuVal !== null && cpuVal > 50
    const ramHigh = ramVal !== null && ramVal > 50
    const gpuHigh = gpuVal !== null && gpuVal > 50
    const hasHighUsage = cpuHigh || ramHigh || gpuHigh

    const timeText = (() => {
        const raw = item.timestamp || ''
        const d = new Date(raw)
        if (Number.isNaN(d.getTime())) return raw || '-'
        return d.toLocaleString('vi-VN', { hour12: false })
    })()

    const onOff = (v: boolean) => (v ? 'ON' : 'OFF')

    const srtList = normalizeSrtList(item.data.SRT)
    const streamList = normalizeStreamList(item.data.stream)

    return (
        <div
            className={`glass-card card-animate machine-card ${srtOnline ? 'card-online' : 'card-offline'} ${hasHighUsage ? 'card-overload' : ''}`}
            style={{ animationDelay: `${index * 40}ms` }}
        >
            {/* Header */}
            <div className="card-header">
                <h3 className="card-name">{item.data.name || 'Unknown Device'}</h3>
                <span className={`status-badge ${srtOnline ? 'badge-online' : 'badge-offline'}`}>
                    <span className={`status-dot ${srtOnline ? 'dot-online' : 'dot-offline'}`} />
                    SRT {onOff(srtOnline)}
                </span>
            </div>

            {/* IP info */}
            <div className="card-info">
                <div className="info-row">
                    <span className="info-label">NETWORK</span>
                    <span className="info-value mono" style={{ fontSize: '0.6rem' }}>
                        {item.data.ip || '-'}{item.data.port ? `:${item.data.port}` : ''}
                    </span>
                </div>
                <div className="info-row">
                    <span className="info-label">WAN</span>
                    <span className="info-value mono" style={{ fontSize: '0.6rem' }}>{item.data.ipwan || '-'}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">RESOLUTION</span>
                    <span className="info-value mono" style={{ fontSize: '0.6rem' }}>{item.data.resolution || '-'}</span>
                </div>
            </div>

            <div className="card-divider" />

            {/* Metrics Row 1: Core Usage */}
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

            {/* Metrics Row 2: Networking */}
            <div className="card-metrics">
                <div className="metric-box">
                    <div className="metric-label">PING</div>
                    <div className="metric-value metric-ping">{item.data.ping ?? '0'}<span className="metric-unit">ms</span></div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">SENDER</div>
                    <div className="metric-value metric-sender">
                        {senderVal.toFixed(2)}<span className="metric-unit">Mbps</span>
                    </div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">RECV</div>
                    <div className="metric-value metric-receiver">
                        {receiverVal.toFixed(2)}<span className="metric-unit">Mbps</span>
                    </div>
                </div>
            </div>

            {/* Metrics Row 3: App Status (VITAL) */}
            <div className="card-metrics">
                <div className={`metric-box ${!appOn ? 'metric-box-danger' : ''}`}>
                    <div className="metric-label">APP</div>
                    <div className={`metric-value ${appOn ? 'metric-ping' : 'metric-danger'}`}>{onOff(appOn)}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">REC</div>
                    <div className={`metric-value ${recOn ? 'metric-ping' : 'metric-warn'}`}>{onOff(recOn)}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">LIVE</div>
                    <div className={`metric-value ${liveOn ? 'metric-ping' : 'metric-warn'}`}>{onOff(liveOn)}</div>
                </div>
            </div>

            {/* Mini SRT Table */}
            {srtList.length > 0 && (
                <div className="mini-srt-table-wrap">
                    <table className="mini-srt-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Port</th>
                                <th>Quality</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {srtList.map((s, i) => {
                                const st = toOnOff(s.status)
                                return (
                                    <tr 
                                        key={`${item.data.name || 'machine'}-${item.data.ip || 'ip'}-${index}`}
                                        className={hasHighUsage ? 'row-overload' : ''}
                                    >
                                        <td>{s.nameSRT || `SRT ${i + 1}`}</td>
                                        <td className="mono">{s.port || '-'}</td>
                                        <td>{s.quality || '-'}</td>
                                        <td>
                                            <span className={`mini-srt-tag ${st === 'ON' ? 'mini-srt-tag-on' : 'mini-srt-tag-off'}`}>
                                                {st}
                                            </span>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Stream Detail Action */}
            {streamList.length > 0 && (
                <div className="card-stream-action">
                    <button
                        className="btn-stream-full"
                        onClick={() => setIsStreamOpen(true)}
                    >
                        Stream Full ({streamList.length})
                    </button>
                </div>
            )}

            <div className="card-timestamp">{timeText}</div>

            {/* Stream Dialog */}
            <Dialog
                open={isStreamOpen}
                onClose={() => setIsStreamOpen(false)}
                title={`Vmix Stream - ${item.data.name || 'Unknown'}`}
            >
                <div className="dialog-detail-grid">
                    {streamList.map((s, i) => renderStreamCard(s, i))}
                </div>
            </Dialog>
        </div>
    )
}
