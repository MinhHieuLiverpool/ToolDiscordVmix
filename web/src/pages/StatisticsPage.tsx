import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
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

    const location = useLocation()
    const navigate = useNavigate()

    // Sync URL path changes to context state
    useEffect(() => {
        if (location.pathname === '/statistics/ping') {
            if (activeView !== 'daily') {
                setActiveView('daily')
            }
        } else if (location.pathname === '/statistics/realtime' || location.pathname === '/statistics') {
            if (activeView !== 'realtime') {
                setActiveView('realtime')
            }
        }
    }, [location.pathname, activeView, setActiveView])

    // Custom setActiveView handler to navigate to the correct URL path
    const handleSetActiveView = (view: 'realtime' | 'daily') => {
        setActiveView(view)
        if (view === 'daily') {
            navigate('/statistics/ping')
        } else {
            navigate('/statistics/realtime')
        }
    }

    return (
        <>
            <div className="page-header">
                <h2 className="page-title">Thống kê</h2>
                <p className="page-description">Biểu đồ hiệu suất CPU, RAM và GPU theo thời gian thực và lịch sử.</p>
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
                                <span className="accent-text">Ping</span>
                                <span className="section-desc"> — lịch sử ping (ms)</span>
                            </>
                        )}
                    </h3>
                    <FilterBar
                        deviceFilter={deviceFilter}
                        setDeviceFilter={setDeviceFilter}
                        activeView={activeView}
                        setActiveView={handleSetActiveView}
                        machineOptions={onlineMachineOptions}
                        onRefresh={() => void loadData()}
                    />
                </div>
                <ChartSection
                    machines={filteredMachines}
                    chartLoading={currentLoading}
                    totalMachines={onlineMachineOptions.length}
                    timeFilter={activeView}
                    showXAxisLabels={false}
                />
            </div>
        </>
    )
}
