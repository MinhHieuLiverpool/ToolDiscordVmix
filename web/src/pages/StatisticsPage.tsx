import { useDashboardContext } from '../hooks/useDashboardContext'
import FilterBar from '../components/FilterBar'
import ChartSection from '../components/ChartSection'
import BandwidthChartSection from '../components/BandwidthChartSection'

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

    return (
        <>
            <div className="page-header">
                <h2 className="page-title">Thống kê</h2>
                <p className="page-description">Biểu đồ hiệu suất CPU, RAM, GPU theo thời gian thực và băng thông IP WAN.</p>
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
                                <span className="accent-text">Băng thông</span>
                                <span className="section-desc"> — lịch sử theo ngày</span>
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
                        dailyLabel="Băng thông"
                        dailyDesc="Theo ngày"
                    />
                </div>

                {activeView === 'realtime' ? (
                    <ChartSection
                        machines={filteredMachines}
                        chartLoading={currentLoading}
                        totalMachines={onlineMachineOptions.length}
                        timeFilter={activeView}
                        showXAxisLabels={false}
                    />
                ) : (
                    <BandwidthChartSection
                        deviceFilter={deviceFilter}
                        machines={filteredMachines}
                    />
                )}
            </div>
        </>
    )
}

