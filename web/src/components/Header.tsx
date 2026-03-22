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

    return (
        <div className="header-top">
            <div className="header-left">
                <div className="header-brand-row">
                    <div className="header-logo-circle">
                        <span className="header-logo-icon">⚡</span>
                    </div>
                    <div>
                        <p className="header-tag">Performance Dashboard</p>
                        <h1 className="header-title">
                            <span className="gradient-text">Vmix</span> Monitor
                        </h1>
                    </div>
                </div>
                <p className="header-subtitle">
                    Giám sát CPU, RAM & GPU realtime — mỗi máy 1 biểu đồ
                </p>
            </div>

            <div className="header-right">
                <div className="header-stats">
                    <div className="stat-card stat-total">
                        <div className="stat-card-icon">🖥️</div>
                        <div className="stat-card-content">
                            <span className="stat-number">{rows.length}</span>
                            <span className="stat-label">Tổng máy</span>
                        </div>
                    </div>
                    <div className="stat-card stat-online">
                        <div className="stat-card-icon">🟢</div>
                        <div className="stat-card-content">
                            <span className="stat-number">{totalOnline}</span>
                            <span className="stat-label">Online</span>
                        </div>
                    </div>
                    <div className="stat-card stat-offline">
                        <div className="stat-card-icon">🔴</div>
                        <div className="stat-card-content">
                            <span className="stat-number">{totalOffline}</span>
                            <span className="stat-label">Offline</span>
                        </div>
                    </div>
                    <div
                        className={`stat-card ${wsStatus === 'connected'
                            ? 'stat-ws-ok'
                            : wsStatus === 'connecting'
                                ? 'stat-ws-warn'
                                : 'stat-ws-err'
                            }`}
                    >
                        <div className="stat-card-icon">
                            <span className={`ws-indicator ${wsStatus === 'connected' ? 'ws-pulse' : ''}`} />
                        </div>
                        <div className="stat-card-content">
                            <span className="stat-number stat-number-sm">
                                {wsStatus === 'connected' ? 'Live' : wsStatus === 'connecting' ? '...' : 'Off'}
                            </span>
                            <span className="stat-label">WebSocket</span>
                        </div>
                    </div>
                </div>

                <button className="logout-btn" type="button" onClick={onLogout}>
                    <svg className="logout-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                        <polyline points="16 17 21 12 16 7" />
                        <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                    Đăng xuất
                </button>
            </div>
        </div>
    )
}
