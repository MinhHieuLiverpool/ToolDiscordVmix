import MachineStatusCard from './MachineStatusCard'
import type { BackendLogItem } from '../services/api'

export default function StatusSection({
    rows,
    loading,
    error,
}: {
    rows: BackendLogItem[]
    loading: boolean
    error: string
}) {
    return (
        <section className="cards-section">
            <h2 className="section-title">
                <span className="gradient-text">Trạng thái máy</span>
            </h2>

            {loading ? (
                <div className="status-cards-grid">
                    {Array.from({ length: 5 }).map((_, i) => (
                        <div key={`skeleton-${i}`} className="glass-card skeleton-card shimmer-loading" />
                    ))}
                </div>
            ) : error ? (
                <div className="glass-card error-card">{error}</div>
            ) : rows.length === 0 ? (
                <div className="glass-card empty-card">Chưa có dữ liệu từ backend.</div>
            ) : (
                <div className="status-cards-grid">
                    {rows.map((item, index) => (
                        <MachineStatusCard
                            key={`${item.data.ip || 'no-ip'}:${item.data.port || 'no-port'}`}
                            item={item}
                            index={index}
                        />
                    ))}
                </div>
            )}
        </section>
    )
}
