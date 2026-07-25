import MachineStatusCard from '../../components/MachineStatusCard'
import { getMachineStatisticsId, type BackendLogItem } from '../../services/api'

export default function StatusByMachinePage({
  rows,
  loading,
  error,
  isEditMode = false,
}: {
  rows: BackendLogItem[]
  loading: boolean
  error: string
  isEditMode?: boolean
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
      {rows.map((item, index) => {
        const machineId = getMachineStatisticsId(item) || `${item.data.ip || 'no-ip'}-${item.data.name || 'no-name'}`
        return (
          <MachineStatusCard
            key={machineId}
            item={item}
            index={index}
            isEditMode={isEditMode}
          />
        )
      })}
    </div>
  )
}
