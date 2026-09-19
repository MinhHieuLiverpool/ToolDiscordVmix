import { useDashboardContext } from '../hooks/useDashboardContext'
import FilterBar from '../components/FilterBar'
import ChartSection from '../components/ChartSection'
import BandwidthChartSection from '../components/BandwidthChartSection'
import { useLanguage } from '../config/i18n'

export default function StatisticsPage() {
    const { t } = useLanguage()
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
                <h2 className="page-title">{t('statistics.title')}</h2>
                <p className="page-description">{t('statistics.desc')}</p>
            </div>

            <div className="page-section">
                <div className="section-header-bar">
                    <h3 className="section-heading">
                        {activeView === 'realtime' ? (
                            <>
                                <span className="accent-text">{t('statistics.realtime')}</span>
                                <span className="section-desc"> — {t('statistics.realtimeDesc')}</span>
                            </>
                        ) : (
                            <>
                                <span className="accent-text">{t('statistics.bandwidth')}</span>
                                <span className="section-desc"> — {t('statistics.bandwidthDesc')}</span>
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
                        dailyLabel={t('statistics.bandwidth')}
                        dailyDesc={t('statistics.bandwidthDesc')}
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

