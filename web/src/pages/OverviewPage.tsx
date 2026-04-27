import { useDashboardContext } from '../hooks/useDashboardContext'
import StatusSection from '../components/StatusSection'

export default function OverviewPage() {
    const {
        rows,
        loading,
        error,
    } = useDashboardContext()

    return (
        <>
            <div className="page-header">
                <h2 className="page-title">
                    Tổng quan
                </h2>
                <p className="page-description">Xem tổng thể trạng thái hệ thống và danh sách máy.</p>
            </div>

            <StatusSection rows={rows} loading={loading} error={error} />
        </>
    )
}
