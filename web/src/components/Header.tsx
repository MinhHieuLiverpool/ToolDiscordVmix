import type { BackendLogItem } from '../services/api'

type WsStatus = 'connecting' | 'connected' | 'disconnected'

export default function Header({
    rows,
    totalOnline,
    wsStatus,
    onLogout,
}: {
    rows: BackendLogItem[]
    totalOnline: number
    wsStatus: WsStatus
    onLogout: () => void
}) {
    const totalOffline = rows.length - totalOnline

    const wsLabel = wsStatus === 'connected' ? 'CONNECTED' : wsStatus === 'connecting' ? 'CONNECTING...' : 'DISCONNECTED'
    const wsColorClass = wsStatus === 'connected' ? 'header-ws-ok' : wsStatus === 'connecting' ? 'header-ws-warn' : 'header-ws-err'

    return (
        <div className="header-top">
            {/* Left: Branding */}
            <div className="header-left">
                <div className="header-brand-row">
                    <div className="header-logo-circle">
                        <img src="/favicon.svg" alt="Vmix Monitor Logo" className="header-logo-img" />
                    </div>
                    <div>
                        <h1 className="header-title">
                            <span className="gradient-text">Vmix</span> Monitor
                        </h1>
                        <p className="header-subtitle">
                            Realtime Fleet Performance
                        </p>
                    </div>
                </div>
            </div>

            {/* Center: System KPIs */}
            <div className="header-center">
                <div className="header-kpi-row">
                    <div className="header-kpi">
                        <span className="header-kpi-number">{rows.length}</span>
                        <span className="header-kpi-label">TOTAL</span>
                    </div>
                    <div className="header-kpi-divider" />
                    <div className="header-kpi header-kpi-online">
                        <span className="header-kpi-number">{totalOnline}</span>
                        <span className="header-kpi-label">ONLINE</span>
                    </div>
                    <div className="header-kpi-divider" />
                    <div className="header-kpi header-kpi-offline">
                        <span className="header-kpi-number">{totalOffline}</span>
                        <span className="header-kpi-label">OFFLINE</span>
                    </div>
                </div>
            </div>

            {/* Right: WS Status + Logout */}
            <div className="header-right">
                <div className={`header-ws-badge ${wsColorClass}`}>
                    <span className={`header-ws-dot ${wsStatus === 'connected' ? 'ws-pulse' : ''}`} />
                    <span className="header-ws-text">{wsLabel}</span>
                </div>
                <button className="logout-btn" type="button" onClick={onLogout}>
                    <span style={{ fontSize: '1.1rem', marginRight: '4px' }}>⎋</span>
                    LOGOUT
                </button>
            </div>
        </div>
    )
}
