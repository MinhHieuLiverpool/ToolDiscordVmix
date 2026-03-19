import type { BackendLogItem } from '../services/api'

type WsStatus = 'connecting' | 'connected' | 'disconnected'

export default function Header({
    rows,
    totalOnline,
    wsStatus,
}: {
    rows: BackendLogItem[]
    totalOnline: number
    wsStatus: WsStatus
}) {
    return (
        <div className="header-top">
            <div>
                <p className="header-tag">⚡ ToolDiscordVmix</p>
                <h1 className="header-title">
                    <span className="gradient-text">Performance</span> Monitor
                </h1>
                <p className="header-subtitle">
                    Real-time CPU &amp; RAM monitoring — mỗi máy 1 biểu đồ
                </p>
            </div>
            <div className="header-stats">
                <div className="stat-pill stat-total">
                    <span className="stat-number">{rows.length}</span>
                    <span className="stat-label">Tổng máy</span>
                </div>
                <div className="stat-pill stat-online">
                    <span className="stat-number">{totalOnline}</span>
                    <span className="stat-label">Online</span>
                </div>
                <div className="stat-pill stat-offline">
                    <span className="stat-number">{rows.length - totalOnline}</span>
                    <span className="stat-label">Offline</span>
                </div>
                <div
                    className={`stat-pill ${wsStatus === 'connected'
                            ? 'stat-ws-ok'
                            : wsStatus === 'connecting'
                                ? 'stat-ws-warn'
                                : 'stat-ws-err'
                        }`}
                >
                    <span className="stat-number ws-dot">●</span>
                    <span className="stat-label">WS: {wsStatus}</span>
                </div>
            </div>
        </div>
    )
}
