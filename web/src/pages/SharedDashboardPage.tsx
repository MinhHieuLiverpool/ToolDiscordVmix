import { useState, useEffect } from 'react'
import { useDashboardContext } from '../hooks/useDashboardContext'
import type { DashboardContextType } from './DashboardLayout'
import OverviewPage from './OverviewPage'
import SrtPage from './SrtPage'
import StreamPage from './StreamPage'
import UrlKeyPage from './UrlKeyPage'
import FfmpegPage from './FfmpegPage'
import StatisticsPage from './StatisticsPage'
import VmixMonitorPage from './VmixMonitorPage'
import MobileMonitorPage from './MobileMonitorPage'
import SpeedtestPage from './SpeedtestPage'
import DebugLogPage from './DebugLogPage'

export default function SharedDashboardPage() {
    const context = useDashboardContext() as DashboardContextType & { 
        allowedFeatures?: string[]
        allowedMachines?: string[] 
    }
    
    const { 
        allowedFeatures = [], 
        loading, 
        error, 
        wsStatus 
    } = context

    const [activeTab, setActiveTab] = useState('')

    // Set initial active tab when allowedFeatures are loaded
    useEffect(() => {
        if (allowedFeatures.length > 0 && !activeTab) {
            setActiveTab(allowedFeatures[0])
        }
    }, [allowedFeatures, activeTab])

    if (error) {
        return (
            <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6 text-white">
                <div className="bg-slate-950/40 border border-rose-500/25 rounded-2xl p-8 max-w-md w-full text-center shadow-2xl flex flex-col items-center gap-4">
                    <svg className="w-16 h-16 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
                    </svg>
                    <h2 className="text-lg font-black text-rose-400 uppercase tracking-wider">Lỗi truy cập</h2>
                    <p className="text-slate-400 text-sm font-semibold">{error}</p>
                </div>
            </div>
        )
    }

    if (loading && allowedFeatures.length === 0) {
        return (
            <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6 text-white">
                <div className="flex flex-col items-center gap-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500"></div>
                    <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Đang tải cấu hình chia sẻ...</p>
                </div>
            </div>
        )
    }

    const renderActiveComponent = () => {
        switch (activeTab) {
            case 'Tổng quan':
                return <OverviewPage />
            case 'SRT':
                return <SrtPage />
            case 'Thông số Stream':
                return <StreamPage />
            case 'URL & Key':
                return <UrlKeyPage />
            case 'FFmpeg':
                return <FfmpegPage />
            case 'Thống kê':
                return <StatisticsPage />
            case 'Vmix Monitor':
                return <VmixMonitorPage />
            case 'Mobile Monitor':
                return <MobileMonitorPage />
            case 'Speedtest':
                return <SpeedtestPage />
            case 'Debug Log':
                return <DebugLogPage />
            default:
                return null
        }
    }

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col shared-dashboard-view">
            {/* Custom Top Navigation bar */}
            <header className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-100 dark:border-slate-800/80 px-4 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-8 bg-purple-600 rounded-lg flex items-center justify-center">
                        <img src="/favicon.svg" alt="Vmix" className="h-5 w-5" />
                    </div>
                    <div>
                        <h1 className="text-sm font-black tracking-wider text-slate-800 dark:text-slate-100 uppercase">
                            Vmix Monitor <span className="text-purple-600 dark:text-purple-400">Shared</span>
                        </h1>
                        <p className="text-[10px] text-slate-400 font-semibold uppercase leading-none mt-0.5">Trang xem giám sát trực tiếp</p>
                    </div>
                </div>

                {/* Horizontal Navigation Tabs */}
                <div className="flex items-center gap-1 overflow-x-auto py-1 max-w-full">
                    {allowedFeatures.map((feat) => {
                        const isActive = activeTab === feat
                        return (
                            <button
                                key={feat}
                                onClick={() => setActiveTab(feat)}
                                className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 select-none ${
                                    isActive
                                        ? 'bg-purple-600 text-white shadow-md shadow-purple-500/10'
                                        : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50'
                                }`}
                            >
                                {feat}
                            </button>
                        )
                    })}
                </div>

                {/* Connection Status Indicator */}
                <div className="flex items-center gap-2 shrink-0">
                    <span className={`h-2.5 w-2.5 rounded-full ${
                        wsStatus === 'connected' 
                            ? 'bg-emerald-500 animate-pulse' 
                            : wsStatus === 'connecting' 
                            ? 'bg-amber-500' 
                            : 'bg-rose-500'
                    }`} />
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider select-none">
                        {wsStatus === 'connected' ? 'Trực tiếp' : wsStatus === 'connecting' ? 'Kết nối...' : 'Mất kết nối'}
                    </span>
                </div>
            </header>

            {/* Main content wrapper */}
            <main className="flex-1 px-4 py-6 w-full">
                <div className="animate-fade-in">
                    {renderActiveComponent()}
                </div>
            </main>
        </div>
    )
}
