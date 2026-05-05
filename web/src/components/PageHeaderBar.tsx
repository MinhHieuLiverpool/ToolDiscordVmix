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
                        <span className="account-dot" />
                        {username}
                    </span>
                    <button className="header-logout-btn" type="button" onClick={handleLogout}>
                        LOGOUT
                    </button>
                </div>
            </div>
        </header>
    )
}
