import { useMemo, useState } from 'react'
import { toNumber } from '../types'
import {
    normalizeSrtList,
    normalizeStreamList,
    normalizeStreamKeysList,
    type BackendLogItem,
} from '../services/api'
import Dialog from './ui/Dialog'
import { renderSrtCard, renderStreamCard } from './DialogHelpers'

export default function MachineStatusCard({
    item,
    index,
}: {
    item: BackendLogItem
    index: number
}) {
    const isOn = (value: unknown): boolean => ['ONLINE', 'ON', '1', 'TRUE', 'RUNNING', 'LIVE', 'ACTIVE'].includes(String(value || '').toUpperCase())

    const srtList = normalizeSrtList(item.data.SRT)
    const streamList = normalizeStreamList(item.data.stream)
    const streamKeysList = normalizeStreamKeysList(item.data.stream_keys)

    const appOn = Number(item.data.statusapp) === 1
    const srtOnlineCount = srtList.filter((s) => isOn(s.status)).length
    const streamActiveCount = streamList.filter((s) => isOn(s.runtime)).length

    const srtOnline = appOn || srtOnlineCount > 0
    const cpuVal = toNumber(item.data.temperature ?? item.data.cpu)
    const ramVal = toNumber(item.data.memory ?? item.data.ram)
    const gpuVal = toNumber(item.data.gpu)
    const senderVal = toNumber(item.data.sender_mbps)
    const receiverVal = toNumber(item.data.receiver_mbps)
    const cpuHigh = cpuVal !== null && cpuVal > 50
    const ramHigh = ramVal !== null && ramVal > 50
    const hasHighUsage = cpuHigh || ramHigh
    const recOn = Boolean(item.data.vmix_recording)
    const liveOn = Boolean(item.data.vmix_streaming)
    const extOn = Boolean(item.data.vmix_external)
    const pidVmix = String(item.data.PIDVMIX ?? '').trim() || '-'

    const timeText = (() => {
        const raw = item.timestamp || ''
        const d = new Date(raw)
        if (Number.isNaN(d.getTime())) return raw || '-'
        return d.toLocaleString('vi-VN', { hour12: false })
    })()

    const onOff = (v: boolean) => (v ? 'ON' : 'OFF')
    const fmtMbps = (value: number | null) => (value !== null ? `${value.toFixed(2)}` : '-')
    const machineKeySeed = `${item.data.name || 'unknown'}|${item.data.ip || 'no-ip'}|${item.timestamp || 'no-ts'}|${index}`
    const [streamOpen, setStreamOpen] = useState(false)
    const [srtOpen, setSrtOpen] = useState(false)
    const [streamKeysOpen, setStreamKeysOpen] = useState(false)


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
                    <span className="info-label">PID VMIX</span>
                    <span className="info-value mono">{pidVmix}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">REC | LIVE</span>
                    <span className="info-value">{onOff(recOn)} | {onOff(liveOn)}</span>
                </div>
            </div>

            <div className="card-divider" />

            {/* Metrics */}
            <div className="card-metrics">
                <div className={`metric-box ${cpuHigh ? 'metric-box-danger' : ''}`}>
                    <div className="metric-label metric-label-cpu">CPU</div>
                    <div className={`metric-value ${cpuHigh ? 'metric-danger' : 'metric-cpu'}`}>
                        {cpuVal !== null ? `${cpuVal.toFixed(0)}%` : '-'}
                    </div>
                </div>
                <div className={`metric-box ${ramHigh ? 'metric-box-danger' : ''}`}>
                    <div className="metric-label metric-label-ram">RAM</div>
                    <div className={`metric-value ${ramHigh ? 'metric-danger' : 'metric-ram'}`}>
                        {ramVal !== null ? `${ramVal.toFixed(0)}%` : '-'}
                    </div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">Ping</div>
                    <div className="metric-value metric-ping">{item.data.ping ?? '-'}</div>
                </div>
            </div>

            <div className="card-metrics">
                <div className="metric-box">
                    <div className="metric-label">APP</div>
                    <div className={`metric-value ${appOn ? 'metric-ping' : 'metric-warn'}`}>{onOff(appOn)}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">Timeout</div>
                    <div className="metric-value metric-cpu">{item.data.ping_timeouts ?? 0}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">EXT</div>
                    <div className={`metric-value ${extOn ? 'metric-ping' : 'metric-cpu'}`}>{onOff(extOn)}</div>
                </div>
            </div>

            <div className="card-metrics">
                <div className="metric-box">
                    <div className="metric-label metric-label-gpu">GPU</div>
                    <div className="metric-value metric-warn">{gpuVal !== null ? `${gpuVal.toFixed(0)}%` : '-'}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">Sender</div>
                    <div className="metric-value metric-ping">{fmtMbps(senderVal)} Mbps</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">Receiver</div>
                    <div className="metric-value metric-ping">{fmtMbps(receiverVal)} Mbps</div>
                </div>
            </div>

            <div className="card-metrics">
                <div className="metric-box">
                    <div className="metric-label">PID VMIX</div>
                    <div className="metric-value mono">{pidVmix}</div>
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

            {/* Extra info */}
            <div className="card-extra">
                <div className="info-row">
                    <span className="info-label">Resolution</span>
                    <span className="info-value">{item.data.resolution || '-'}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">MAC Address</span>
                    <span className="info-value mono">{item.data.mac_address || '-'}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">Network Speed</span>
                    <span className="info-value">{item.data.network_speed || '-'}</span>
                </div>
            </div>

            <div className="card-footer">
                <div className="card-footer-actions">
                    <button
                        type="button"
                        className="card-footer-btn"
                        onClick={() => setSrtOpen(true)}
                        disabled={srtList.length === 0}
                    >
                        SRT ({srtOnlineCount}/{srtList.length})
                    </button>
                    <button
                        type="button"
                        className="card-footer-btn"
                        onClick={() => setStreamOpen(true)}
                        disabled={streamList.length === 0}
                    >
                        Stream ({streamActiveCount}/{streamList.length})
                    </button>
                    <button
                        type="button"
                        className="card-footer-btn"
                        onClick={() => setStreamKeysOpen(true)}
                        disabled={streamKeysList.length === 0}
                    >
                        Stream Key ({streamKeysList.length})
                    </button>
                </div>
                <span className="card-timestamp">{timeText}</span>
            </div>

            <Dialog
                open={srtOpen}
                onClose={() => setSrtOpen(false)}
                title={`SRT · ${item.data.name || 'Unknown'}`}
            >
                {srtList.length > 0 ? (
                    <div className="dialog-detail-grid">
                        {srtList.map(renderSrtCard)}
                    </div>
                ) : (
                    <div className="dialog-empty-state">Không có dữ liệu SRT.</div>
                )}
            </Dialog>

            <Dialog
                open={streamOpen}
                onClose={() => setStreamOpen(false)}
                title={`Stream · ${item.data.name || 'Unknown'}`}
            >
                {streamList.length > 0 ? (
                    <div className="dialog-detail-grid">
                        {streamList.map((stream, idx) => {
                            const matchedKey = streamKeysList.find((sk) => sk.stream === stream.stream)
                            return renderStreamCard(stream, idx, matchedKey)
                        })}
                    </div>
                ) : (
                    <div className="dialog-empty-state">Không có dữ liệu stream.</div>
                )}
            </Dialog>

            <Dialog
                open={streamKeysOpen}
                onClose={() => setStreamKeysOpen(false)}
                title={`Stream Key · ${item.data.name || 'Unknown'}`}
            >
                {streamKeysList.length > 0 ? (
                    <div className="dialog-detail-grid">
                        {streamKeysList.map((keyItem, keyIndex) => (
                            <div key={`${machineKeySeed}::streamkey::${keyIndex}`} className="dialog-detail-card">
                                <div className="dialog-detail-card-header">
                                    <span className="dialog-detail-card-title">{keyItem.stream || `Stream Key ${keyIndex + 1}`}</span>
                                </div>
                                <div className="dialog-detail-row">
                                    <span className="dialog-detail-key">URL</span>
                                    <span className="dialog-detail-value mono" style={{ wordBreak: 'break-all' }}>{keyItem.url || '-'}</span>
                                </div>
                                <div className="dialog-detail-row">
                                    <span className="dialog-detail-key">Key</span>
                                    <span className="dialog-detail-value mono" style={{ wordBreak: 'break-all' }}>{keyItem.key || '-'}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="dialog-empty-state">Không có dữ liệu Stream Key.</div>
                )}
            </Dialog>

        </div>
    )
}
