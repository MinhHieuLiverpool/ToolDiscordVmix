import { NavLink, useNavigate } from 'react-router-dom'
import { logout } from '../services/auth'
import { showToast } from './ui/Toast'
import { useState } from 'react'

type WsStatus = 'connecting' | 'connected' | 'disconnected'

const NAV_ITEMS = [
    {
        to: '/dashboard',
        label: 'Tổng quan',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7" />
                <rect x="14" y="3" width="7" height="7" />
                <rect x="14" y="14" width="7" height="7" />
                <rect x="3" y="14" width="7" height="7" />
            </svg>
        ),
    },
    {
        to: '/srt',
        label: 'SRT',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
            </svg>
        ),
    },
    {
        to: '/stream',
        label: 'Stream',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="23 7 16 12 23 17 23 7" />
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
        ),
    },
    {
        to: '/statistics',
        label: 'Thống kê',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
        ),
    },
    {
        to: '/vmix-monitor',
        label: 'Vmix Monitor',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
        ),
    },
]

export default function Sidebar({
    rows,
    totalOnline,
    wsStatus,
}: {
    rows: { length: number }
    totalOnline: number
    wsStatus: WsStatus
}) {
    const navigate = useNavigate()
    const [collapsed, setCollapsed] = useState(false)

    const handleLogout = () => {
        logout()
        showToast('Đã đăng xuất thành công.', 'info')
        navigate('/login', { replace: true })
    }

    const wsLabel = wsStatus === 'connected' ? 'CONNECTED' : wsStatus === 'connecting' ? 'CONNECTING...' : 'DISCONNECTED'
    const wsColorClass = wsStatus === 'connected' ? 'sidebar-ws-ok' : wsStatus === 'connecting' ? 'sidebar-ws-warn' : 'sidebar-ws-err'
    const totalOffline = rows.length - totalOnline

    return (
        <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
            {/* Brand */}
            <div className="sidebar-brand">
                <div className="sidebar-logo-circle">
                    <img src="/favicon.svg" alt="Vmix" className="sidebar-logo-img" />
                </div>
                {!collapsed && (
                    <div className="sidebar-brand-text">
                        <h1 className="sidebar-title">
                            <span className="sidebar-accent">Vmix</span> Monitor
                        </h1>
                        <p className="sidebar-subtitle">Fleet Performance</p>
                    </div>
                )}
                <button
                    type="button"
                    className="sidebar-toggle-btn"
                    onClick={() => setCollapsed(!collapsed)}
                    title={collapsed ? 'Mở rộng' : 'Thu gọn'}
                >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        {collapsed ? (
                            <polyline points="9 18 15 12 9 6" />
                        ) : (
                            <polyline points="15 18 9 12 15 6" />
                        )}
                    </svg>
                </button>
            </div>

            {/* KPI Summary */}
            {!collapsed && (
                <div className="sidebar-kpi">
                    <div className="sidebar-kpi-item">
                        <span className="sidebar-kpi-num">{rows.length}</span>
                        <span className="sidebar-kpi-label">Total</span>
                    </div>
                    <div className="sidebar-kpi-divider" />
                    <div className="sidebar-kpi-item sidebar-kpi-online">
                        <span className="sidebar-kpi-num">{totalOnline}</span>
                        <span className="sidebar-kpi-label">Online</span>
                    </div>
                    <div className="sidebar-kpi-divider" />
                    <div className="sidebar-kpi-item sidebar-kpi-offline">
                        <span className="sidebar-kpi-num">{totalOffline}</span>
                        <span className="sidebar-kpi-label">Offline</span>
                    </div>
                </div>
            )}

            {/* Navigation */}
            <nav className="sidebar-nav">
                <div className="sidebar-nav-label">{collapsed ? '—' : 'MENU'}</div>
                {NAV_ITEMS.map((item) => (
                    <NavLink
                        key={item.to}
                        to={item.to}
                        end={item.to === '/dashboard'}
                        className={({ isActive }) =>
                            `sidebar-nav-item ${isActive ? 'sidebar-nav-active' : ''}`
                        }
                        title={item.label}
                    >
                        <span className="sidebar-nav-icon">{item.icon}</span>
                        {!collapsed && <span className="sidebar-nav-text">{item.label}</span>}
                    </NavLink>
                ))}
            </nav>

            {/* Bottom section */}
            <div className="sidebar-bottom">
                {/* WS Badge */}
                <div className={`sidebar-ws-badge ${wsColorClass}`}>
                    <span className={`sidebar-ws-dot ${wsStatus === 'connected' ? 'ws-pulse' : ''}`} />
                    {!collapsed && <span className="sidebar-ws-text">{wsLabel}</span>}
                </div>

                {/* Logout */}
                <button className="sidebar-logout-btn" type="button" onClick={handleLogout} title="Đăng xuất">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="sidebar-logout-icon">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                        <polyline points="16 17 21 12 16 7" />
                        <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                    {!collapsed && <span>LOGOUT</span>}
                </button>
            </div>
        </aside>
    )
}
