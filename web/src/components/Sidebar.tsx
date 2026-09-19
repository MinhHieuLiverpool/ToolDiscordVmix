import { NavLink, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { getUserPermissions, getUserRole } from '../services/auth'
import { useLanguage } from '../config/i18n'

// permissionLabel = original Vietnamese label used for permission checks (backend)
// labelKey = i18n key for display
const NAV_ITEMS = [
    {
        to: '/dashboard',
        permissionLabel: 'Tổng quan',
        labelKey: 'sidebar.overview',
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
        permissionLabel: 'SRT',
        labelKey: 'sidebar.srt',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
            </svg>
        ),
    },
    {
        permissionLabel: 'Stream',
        labelKey: 'sidebar.stream',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="23 7 16 12 23 17 23 7" />
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
        ),
        children: [
            {
                to: '/stream',
                permissionLabel: 'Thông số Stream',
                labelKey: 'sidebar.streamParams',
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
                permissionLabel: 'URL & Key',
                labelKey: 'sidebar.urlKey',
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
        permissionLabel: 'Thống kê',
        labelKey: 'sidebar.statistics',
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
        permissionLabel: 'Vmix Monitor',
        labelKey: 'sidebar.vmixMonitor',
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
        permissionLabel: 'Record & MultiCorder',
        labelKey: 'sidebar.recordMulticorder',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <circle cx="12" cy="12" r="3" fill="currentColor" />
            </svg>
        ),
    },
    {
        to: '/mobile-monitor',
        permissionLabel: 'Mobile Monitor',
        labelKey: 'sidebar.mobileMonitor',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="5" y="2" width="14" height="20" rx="2" ry="2" />
                <line x1="12" y1="18" x2="12.01" y2="18" />
            </svg>
        ),
    },
    {
        to: '/viewsync',
        permissionLabel: 'ViewSync',
        labelKey: 'sidebar.viewSync',
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
        permissionLabel: 'Speedtest',
        labelKey: 'sidebar.speedtest',
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
        permissionLabel: 'Debug Log',
        labelKey: 'sidebar.debugLog',
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
        permissionLabel: 'CreateWebURL',
        labelKey: 'sidebar.createWebUrl',
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
        permissionLabel: 'Quản lý Kênh',
        labelKey: 'sidebar.gameChannels',
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
        to: '/notification',
        permissionLabel: 'Notification',
        labelKey: 'sidebar.notification',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9z" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
        ),
    },
    {
        permissionLabel: 'Người dùng',
        labelKey: 'sidebar.users',
        icon: (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
            </svg>
        ),
        children: [
            {
                to: '/account',
                permissionLabel: 'Tài khoản',
                labelKey: 'sidebar.account',
                icon: (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="7" r="4" />
                        <path d="M5.5 21a6.5 6.5 0 0 1 13 0" />
                    </svg>
                ),
            },
            {
                to: '/account/roles',
                permissionLabel: 'Phân quyền',
                labelKey: 'sidebar.roles',
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
    const { t } = useLanguage()

    const permissions = getUserPermissions()
    const userRole = getUserRole().toLowerCase()
    const isAdmin = userRole === 'admin'

    const filteredNavItems = NAV_ITEMS.map((item) => {
        if ('children' in item && item.children) {
            const filteredChildren = item.children.filter((child) => permissions.includes(child.permissionLabel) || isAdmin)
            if (filteredChildren.length === 0) return null
            return {
                ...item,
                children: filteredChildren,
            }
        }
        if (permissions.includes(item.permissionLabel) || isAdmin) {
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
            const isExpanded = expandedGroups[item.permissionLabel] ?? false
            const groupActive = isGroupActive(item)

            return (
                <div key={item.permissionLabel} className="sidebar-nav-group">
                    <button
                        type="button"
                        className={`sidebar-nav-item sidebar-nav-group-toggle ${groupActive ? 'sidebar-nav-group-active' : ''}`}
                        onClick={() => toggleGroup(item.permissionLabel)}
                        title={t(item.labelKey)}
                    >
                        <span className="sidebar-nav-icon">{item.icon}</span>
                        {!collapsed && (
                            <>
                                <span className="sidebar-nav-text">{t(item.labelKey)}</span>
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
                                    title={t(child.labelKey)}
                                >
                                    <span className="sidebar-nav-icon sidebar-nav-child-icon">{child.icon}</span>
                                    <span className="sidebar-nav-text">{t(child.labelKey)}</span>
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
                title={t(item.labelKey)}
            >
                <span className="sidebar-nav-icon">{item.icon}</span>
                {!collapsed && <span className="sidebar-nav-text">{t(item.labelKey)}</span>}
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
                        title={t('sidebar.collapse')}
                    >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="15 18 9 12 15 6" />
                        </svg>
                    </button>
                )}
            </div>

            {/* Navigation */}
            <nav className="sidebar-nav">
                <div className="sidebar-nav-label">{collapsed ? '—' : t('sidebar.menu')}</div>
                {filteredNavItems.map((item) => renderNavItem(item))}
            </nav>

            {/* Bottom section */}
            <div className="sidebar-bottom">
                {collapsed && (
                    <button
                        type="button"
                        className="sidebar-toggle-btn sidebar-toggle-btn-bottom"
                        onClick={() => setCollapsed(false)}
                        title={t('sidebar.expand')}
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

