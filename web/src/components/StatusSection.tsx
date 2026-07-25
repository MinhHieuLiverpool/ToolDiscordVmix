import { useEffect, useState } from 'react'
import StatusByMachinePage from '../pages/status/StatusByMachinePage'
import StatusByTablePage from '../pages/status/StatusByTablePage'
import type { BackendLogItem } from '../services/api'

type StatusViewMode = 'machine' | 'table'

const STATUS_VIEW_STORAGE_KEY = 'vmix:status:view-mode'

export default function StatusSection({
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
    const [viewMode, setViewMode] = useState<StatusViewMode>('machine')

    useEffect(() => {
        const saved = window.localStorage.getItem(STATUS_VIEW_STORAGE_KEY)
        if (saved === 'machine' || saved === 'table') {
            setViewMode(saved)
        }
    }, [])

    useEffect(() => {
        window.localStorage.setItem(STATUS_VIEW_STORAGE_KEY, viewMode)
    }, [viewMode])

    return (
        <section className="cards-section">
            <div className="status-header-row">
                <h2 className="section-title status-section-title">
                    <span className="gradient-text">Trạng thái máy</span>
                </h2>

                <div className="status-view-nav" role="tablist" aria-label="Machine status view mode">
                    <button
                        type="button"
                        role="tab"
                        aria-selected={viewMode === 'machine'}
                        className={`status-view-btn ${viewMode === 'machine' ? 'status-view-btn-active' : ''}`}
                        onClick={() => setViewMode('machine')}
                    >
                        Theo từng máy
                    </button>
                    <button
                        type="button"
                        role="tab"
                        aria-selected={viewMode === 'table'}
                        className={`status-view-btn ${viewMode === 'table' ? 'status-view-btn-active' : ''}`}
                        onClick={() => setViewMode('table')}
                    >
                        Bảng tổng hợp
                    </button>
                </div>
            </div>

            {viewMode === 'machine' ? (
                <StatusByMachinePage rows={rows} loading={loading} error={error} isEditMode={isEditMode} />
            ) : (
                <StatusByTablePage rows={rows} loading={loading} error={error} />
            )}
        </section>
    )
}
