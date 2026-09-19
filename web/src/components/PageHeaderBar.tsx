import { useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { getUsername, logout } from '../services/auth'
import { showToast } from './ui/Toast'
import { useLanguage } from '../config/i18n'
import LanguageToggle from './LanguageToggle'

type RouteTitle = {
    match: RegExp
    titleKey: string
}

const ROUTE_TITLES: RouteTitle[] = [
    { match: /^\/dashboard\b/, titleKey: 'pageHeader.overview' },
    { match: /^\/srt\b/, titleKey: 'pageHeader.srt' },
    { match: /^\/stream\b/, titleKey: 'pageHeader.stream' },
    { match: /^\/url-key\b/, titleKey: 'pageHeader.urlKey' },
    { match: /^\/ffmpeg\b/, titleKey: 'pageHeader.ffmpeg' },
    { match: /^\/statistics\b/, titleKey: 'pageHeader.statistics' },
    { match: /^\/vmix-monitor\b/, titleKey: 'pageHeader.vmixMonitor' },
    { match: /^\/record-multicorder\b/, titleKey: 'pageHeader.recordMulticorder' },
    { match: /^\/mobile-monitor\b/, titleKey: 'pageHeader.mobileMonitor' },
    { match: /^\/notification\b/, titleKey: 'pageHeader.notification' },
    { match: /^\/game-channels\b/, titleKey: 'pageHeader.gameChannels' },
    { match: /^\/create-web-url\b/, titleKey: 'pageHeader.createWebUrl' },
    { match: /^\/viewsync\/multi\b/, titleKey: 'pageHeader.viewSyncMulti' },
    { match: /^\/viewsync\b/, titleKey: 'pageHeader.viewSync' },
    { match: /^\/speedtest\b/, titleKey: 'pageHeader.speedtest' },
    { match: /^\/account\/roles\b/, titleKey: 'pageHeader.roles' },
    { match: /^\/account\b/, titleKey: 'pageHeader.account' },
    { match: /^\/debug-logs\/import\b/, titleKey: 'pageHeader.importDebug' },
    { match: /^\/debug-logs\b/, titleKey: 'pageHeader.debugLog' },
]

export default function PageHeaderBar() {
    const location = useLocation()
    const navigate = useNavigate()
    const { t } = useLanguage()

    const title = useMemo(() => {
        const found = ROUTE_TITLES.find((item) => item.match.test(location.pathname))
        return found ? t(found.titleKey) : 'Dashboard'
    }, [location.pathname, t])

    const username = getUsername() || 'account'

    const handleLogout = () => {
        logout()
        showToast(t('auth.logoutSuccess'), 'info')
        navigate('/login', { replace: true })
    }

    return (
        <header className="app-header">
            <div className="app-header-inner">
                <h1 className="app-header-title">{title}</h1>
                <div className="app-header-right">
                    {/* Language Toggle */}
                    <LanguageToggle />

                    <span className="account-pill">
                        <span className="account-icon" aria-hidden="true">
                            <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                                <path
                                    fill="currentColor"
                                    d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-4.41 0-8 2.24-8 5v1h16v-1c0-2.76-3.59-5-8-5Z"
                                />
                            </svg>
                        </span>
                        <span className="account-name">{username}</span>
                    </span>
                    <button className="header-logout-btn" type="button" onClick={handleLogout}>
                        {t('auth.logout')}
                    </button>
                </div>
            </div>
        </header>
    )
}

