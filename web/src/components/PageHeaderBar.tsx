import { useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { getUsername, logout } from '../services/auth'
import { showToast } from './ui/Toast'

type RouteTitle = {
    match: RegExp
    title: string
}

const ROUTE_TITLES: RouteTitle[] = [
    { match: /^\/dashboard\b/, title: 'Tổng quan' },
    { match: /^\/srt\b/, title: 'SRT' },
    { match: /^\/stream\b/, title: 'Stream' },
    { match: /^\/url-key\b/, title: 'URL & Key' },
    { match: /^\/ffmpeg\b/, title: 'FFmpeg' },
    { match: /^\/statistics\b/, title: 'Thống kê' },
    { match: /^\/vmix-monitor\b/, title: 'Vmix Monitor' },
    { match: /^\/viewsync\b/, title: 'ViewSync' },
    { match: /^\/viewsync\/multi\b/, title: 'ViewSync Multiview' },
    { match: /^\/speedtest\b/, title: 'Speedtest' },
    { match: /^\/account\/roles\b/, title: 'Phân quyền' },
    { match: /^\/account\b/, title: 'Tài khoản' },
]

export default function PageHeaderBar() {
    const location = useLocation()
    const navigate = useNavigate()

    const title = useMemo(() => {
        const found = ROUTE_TITLES.find((item) => item.match.test(location.pathname))
        return found ? found.title : 'Dashboard'
    }, [location.pathname])

    const username = getUsername() || 'account'

    const handleLogout = () => {
        logout()
        showToast('Đã đăng xuất thành công.', 'info')
        navigate('/login', { replace: true })
    }

    return (
        <header className="app-header">
            <div className="app-header-inner">
                <h1 className="app-header-title">{title}</h1>
                <div className="app-header-right">
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
                        LOGOUT
                    </button>
                </div>
            </div>
        </header>
    )
}
