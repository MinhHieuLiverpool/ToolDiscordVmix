import MachineChartCard from './MachineChartCard'
import type { MachineMetrics, TimeFilter } from '../types'

export default function ChartSection({
    machines,
    chartLoading,
    totalMachines,
    timeFilter,
    showXAxisLabels = true,
}: {
    machines: MachineMetrics[]
    chartLoading: boolean
    totalMachines: number
    timeFilter: TimeFilter
    showXAxisLabels?: boolean
}) {
    if (chartLoading && machines.length === 0) {
        return (
            <section className="charts-section">
                <div className="charts-grid">
                    {Array.from({ length: Math.min(totalMachines || 3, 6) }).map((_, i) => (
                        <div key={`skel-${i}`} className="glass-card skeleton-chart shimmer-loading" />
                    ))}
                </div>
            </section>
        )
    }

    if (machines.length === 0) {
        return (
            <section className="charts-section">
                <div className="glass-card empty-card">Chưa có dữ liệu biểu đồ.</div>
            </section>
        )
    }

    return (
        <section className="charts-section">
            <div className="charts-grid">
                {machines.map((machine) => (
                    <MachineChartCard
                        key={machine.id}
                        machine={machine}
                        timeFilter={timeFilter}
                        showXAxisLabels={showXAxisLabels}
                    />
                ))}
            </div>
        </section>
    )
}
