import { useDashboardContext } from '../hooks/useDashboardContext'
import FilterBar from '../components/FilterBar'
import ChartSection from '../components/ChartSection'

export default function StatisticsPage() {
    const {
        activeView,
        setActiveView,
        deviceFilter,
        setDeviceFilter,
        onlineMachineOptions,
        filteredMachines,
        currentLoading,
        loadData,
    } = useDashboardContext()

    const onlineMachines = filteredMachines.filter(
        (machine) => Number(machine.latestItem?.data.statusapp ?? 0) === 1,
    )

    return (
        <>
            <div className="page-header">
                <h2 className="page-title">Thống kê</h2>
                <p className="page-description">Biểu đồ hiệu suất CPU & RAM theo thời gian thực và lịch sử.</p>
            </div>

            <div className="page-section">
                <div className="section-header-bar">
                    <h3 className="section-heading">
                        {activeView === 'realtime' ? (
                            <>
                                <span className="accent-text">Realtime</span>
                                <span className="section-desc"> — 3 phút cuốn chiếu</span>
                            </>
                        ) : (
                            <>
                                <span className="accent-text">Cả ngày</span>
                                <span className="section-desc"> — lịch sử trung bình 15 phút</span>
                            </>
                        )}
                    </h3>
                    <FilterBar
                        deviceFilter={deviceFilter}
                        setDeviceFilter={setDeviceFilter}
                        activeView={activeView}
                        setActiveView={setActiveView}
                        machineOptions={onlineMachineOptions}
                        onRefresh={() => void loadData()}
                    />
                </div>
                <ChartSection
                    machines={onlineMachines}
                    chartLoading={currentLoading}
                    totalMachines={onlineMachineOptions.length}
                    timeFilter={activeView}
                    showXAxisLabels={false}
                />
            </div>
        </>
    )
}
