import { NavLink, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { getUserPermissions, getUserRole } from '../services/auth'

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
        label: 'Stream',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="23 7 16 12 23 17 23 7" />
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
        ),
        children: [
            {
                to: '/stream',
                label: 'Thông số Stream',
                icon: (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="20" x2="18" y2="10" />
                        <line x1="12" y1="20" x2="12" y2="4" />
                        <line x1="6" y1="20" x2="6" y2="14" />
                    </svg>
                ),
            },
            {
                to: '/url-key',
                label: 'URL & Key',
                icon: (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                    </svg>
                ),
            },
        ],
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
    {
        to: '/record-multicorder',
        label: 'Record & MultiCorder',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <circle cx="12" cy="12" r="3" fill="currentColor" />
            </svg>
        ),
    },
    {
        to: '/mobile-monitor',
        label: 'Mobile Monitor',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="5" y="2" width="14" height="20" rx="2" ry="2" />
                <line x1="12" y1="18" x2="12.01" y2="18" />
            </svg>
        ),
    },
    {
        to: '/viewsync',
        label: 'ViewSync',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 3" />
                <path d="M6 16l-2 2" />
                <path d="M18 16l2 2" />
            </svg>
        ),
    },
    {
        to: '/speedtest',
        label: 'Speedtest',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="13" r="8" />
                <path d="M12 3v2" />
                <path d="M16.24 7.76l1.42-1.42" />
                <path d="M7.76 7.76 6.34 6.34" />
                <path d="M12 13l3.5-3.5" />
            </svg>
        ),
    },
    {
        to: '/debug-logs',
        label: 'Debug Log',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
            </svg>
        ),
    },
    {
        to: '/create-web-url',
        label: 'CreateWebURL',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
        ),
    },
    {
        to: '/game-channels',
        label: 'Quản lý Kênh',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="9" y1="9" x2="15" y2="9" />
                <line x1="9" y1="13" x2="15" y2="13" />
                <line x1="9" y1="17" x2="13" y2="17" />
            </svg>
        ),
    },
    {
        label: 'Người dùng',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
            </svg>
        ),
        children: [
            {
                to: '/account',
                label: 'Tài khoản',
                icon: (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="7" r="4" />
                        <path d="M5.5 21a6.5 6.5 0 0 1 13 0" />
                    </svg>
                ),
            },
            {
                to: '/account/roles',
                label: 'Phân quyền',
                icon: (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="3" width="7" height="7" />
                        <rect x="14" y="3" width="7" height="7" />
                        <rect x="3" y="14" width="7" height="7" />
                        <path d="M14 14h7v7h-7z" />
                    </svg>
                ),
            },
        ],
    },
]

type NavItem = (typeof NAV_ITEMS)[number]

export default function Sidebar() {
    const location = useLocation()
    const [collapsed, setCollapsed] = useState(false)
    const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({ Stream: true, 'Người dùng': true })

    const permissions = getUserPermissions()
    const userRole = getUserRole().toLowerCase()
    const isAdmin = userRole === 'admin'

    const filteredNavItems = NAV_ITEMS.map((item) => {
        if ('children' in item && item.children) {
            const filteredChildren = item.children.filter((child) => permissions.includes(child.label) || isAdmin)
            if (filteredChildren.length === 0) return null
            return {
                ...item,
                children: filteredChildren,
            }
        }
        if (permissions.includes(item.label) || isAdmin) {
            return item
        }
        return null
    }).filter((item): item is typeof NAV_ITEMS[number] => item !== null)

    const toggleGroup = (label: string) => {
        setExpandedGroups((prev) => ({ ...prev, [label]: !prev[label] }))
    }

    const isGroupActive = (item: NavItem) => {
        if (!('children' in item) || !item.children) return false
        return item.children.some((child) => location.pathname === child.to)
    }

    const renderNavItem = (item: NavItem) => {
        if ('children' in item && item.children) {
            const isExpanded = expandedGroups[item.label] ?? false
            const groupActive = isGroupActive(item)

            return (
                <div key={item.label} className="sidebar-nav-group">
                    <button
                        type="button"
                        className={`sidebar-nav-item sidebar-nav-group-toggle ${groupActive ? 'sidebar-nav-group-active' : ''}`}
                        onClick={() => toggleGroup(item.label)}
                        title={item.label}
                    >
                        <span className="sidebar-nav-icon">{item.icon}</span>
                        {!collapsed && (
                            <>
                                <span className="sidebar-nav-text">{item.label}</span>
                                <svg
                                    className={`sidebar-nav-chevron ${isExpanded ? 'sidebar-nav-chevron-open' : ''}`}
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                >
                                    <polyline points="6 9 12 15 18 9" />
                                </svg>
                            </>
                        )}
                    </button>
                    {!collapsed && isExpanded && (
                        <div className="sidebar-nav-children">
                            {item.children.map((child) => (
                                <NavLink
                                    key={child.to}
                                    to={child.to}
                                    end
                                    className={({ isActive }) =>
                                        `sidebar-nav-item sidebar-nav-child ${isActive ? 'sidebar-nav-active' : ''}`
                                    }
                                    title={child.label}
                                >
                                    <span className="sidebar-nav-icon sidebar-nav-child-icon">{child.icon}</span>
                                    <span className="sidebar-nav-text">{child.label}</span>
                                </NavLink>
                            ))}
                        </div>
                    )}
                </div>
            )
        }

        // Regular nav item
        const navTo = 'to' in item ? item.to : undefined
        if (!navTo) return null

        return (
            <NavLink
                key={navTo}
                to={navTo}
                end={navTo === '/dashboard'}
                className={({ isActive }) =>
                    `sidebar-nav-item ${isActive ? 'sidebar-nav-active' : ''}`
                }
                title={item.label}
            >
                <span className="sidebar-nav-icon">{item.icon}</span>
                {!collapsed && <span className="sidebar-nav-text">{item.label}</span>}
            </NavLink>
        )
    }

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
                {!collapsed && (
                    <button
                        type="button"
                        className="sidebar-toggle-btn"
                        onClick={() => setCollapsed(true)}
                        title="Thu gọn"
                    >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="15 18 9 12 15 6" />
                        </svg>
                    </button>
                )}
            </div>

            {/* Navigation */}
            <nav className="sidebar-nav">
                <div className="sidebar-nav-label">{collapsed ? '—' : 'MENU'}</div>
                {filteredNavItems.map((item) => renderNavItem(item))}
            </nav>

            {/* Bottom section */}
            <div className="sidebar-bottom">
                {collapsed && (
                    <button
                        type="button"
                        className="sidebar-toggle-btn sidebar-toggle-btn-bottom"
                        onClick={() => setCollapsed(false)}
                        title="Mở rộng"
                    >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="9 18 15 12 9 6" />
                        </svg>
                    </button>
                )}

                {/* Logout */}
            </div>
        </aside>
    )
}
