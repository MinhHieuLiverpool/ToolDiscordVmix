import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import { useDashboardData } from '../hooks/useDashboardData'

export type DashboardContextType = ReturnType<typeof useDashboardData>

export default function DashboardLayout() {
    const data = useDashboardData()

    return (
        <div className="layout-shell">
            <Sidebar
                rows={data.rows}
                totalOnline={data.totalOnline}
                wsStatus={data.wsStatus}
            />
            <main className="layout-main">
                <Outlet context={data} />
            </main>
        </div>
    )
}
