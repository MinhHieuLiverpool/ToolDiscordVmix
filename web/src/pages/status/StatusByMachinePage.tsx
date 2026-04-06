import MachineStatusCard from '../../components/MachineStatusCard'
import { getMachineStatisticsId, type BackendLogItem } from '../../services/api'

export default function StatusByMachinePage({
  rows,
  loading,
  error,
}: {
  rows: BackendLogItem[]
  loading: boolean
  error: string
}) {
  if (loading) {
    return (
      <div className="status-cards-grid">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={`skeleton-${i}`} className="glass-card skeleton-card shimmer-loading" />
        ))}
      </div>
    )
  }

  if (error) {
    return <div className="glass-card error-card">{error}</div>
  }

  if (rows.length === 0) {
    return <div className="glass-card empty-card">Chưa có dữ liệu từ backend.</div>
  }

  return (
    <div className="status-cards-grid">
      {rows.map((item, index) => (
        <MachineStatusCard
          key={`${getMachineStatisticsId(item) || `${item.data.ip || 'no-ip'}`}::${index}`}
          item={item}
          index={index}
        />
      ))}
    </div>
  )
}
