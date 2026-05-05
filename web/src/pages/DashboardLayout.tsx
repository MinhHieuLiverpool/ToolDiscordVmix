import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import PageHeaderBar from '../components/PageHeaderBar'
import { useDashboardData } from '../hooks/useDashboardData'

export type DashboardContextType = ReturnType<typeof useDashboardData>

export default function DashboardLayout() {
    const data = useDashboardData()

    return (
        <div className="layout-shell">
            <Sidebar />
            <main className="layout-main">
                <PageHeaderBar />
                <Outlet context={data} />
            </main>
        </div>
    )
}
