import { useMemo, useState } from 'react'
import { useDashboardContext } from '../hooks/useDashboardContext'
import { normalizeSrtList, type BackendSrtItem } from '../services/api'
import { toOnOff, renderTypePill } from '../components/DialogHelpers'
import { useLanguage } from '../config/i18n'

interface MachineGroup {
    machineName: string
    machineIp: string
    srtList: BackendSrtItem[]
}

export default function SrtPage() {
    const { t } = useLanguage()
    const { rows, loading, error } = useDashboardContext()
    const [searchTerm, setSearchTerm] = useState('')

    // Group SRT data by machine
    const machineGroups = useMemo(() => {
        const groups: MachineGroup[] = []
        rows.forEach((item) => {
            const srtList = normalizeSrtList(item.data.SRT)
            if (srtList.length === 0) return
            groups.push({
                machineName: item.data.name || 'Unknown',
                machineIp: `${item.data.ip || '-'}:${item.data.port || '-'}`,
                srtList,
            })
        })
        return groups
    }, [rows])

    const filteredGroups = useMemo(() => {
        if (!searchTerm.trim()) return machineGroups
        const term = searchTerm.toLowerCase()
        return machineGroups.filter(
            (g) =>
                g.machineName.toLowerCase().includes(term) ||
                g.machineIp.toLowerCase().includes(term) ||
                g.srtList.some((s) => (s.nameSRT || '').toLowerCase().includes(term)),
        )
    }, [machineGroups, searchTerm])

    const totalSrt = useMemo(() => filteredGroups.reduce((acc, g) => acc + g.srtList.length, 0), [filteredGroups])
    const totalOnline = useMemo(
        () => filteredGroups.reduce((acc, g) => acc + g.srtList.filter((s) => toOnOff(s.status) === 'ON').length, 0),
        [filteredGroups],
    )
    const totalOffline = totalSrt - totalOnline

    if (loading) {
        return (
            <>
                <div className="page-header">
                    <h2 className="page-title">{t('srt.title')}</h2>
                    <p className="page-description">{t('srt.description')}</p>
                </div>
                <div className="loading-skeleton-table">
                    {Array.from({ length: 5 }).map((_, i) => (
                        <div key={`skel-${i}`} className="skeleton-row shimmer-loading" />
                    ))}
                </div>
            </>
        )
    }

    if (error) {
        return (
            <>
                <div className="page-header">
                    <h2 className="page-title">{t('srt.title')}</h2>
                </div>
                <div className="card-light error-card-light">{error}</div>
            </>
        )
    }

    return (
        <>
            <div className="page-header">
                <h2 className="page-title">{t('srt.title')}</h2>
                <p className="page-description">{t('srt.description')}</p>
            </div>

            {/* Summary Cards */}
            <div className="srt-summary-row">
                <div className="summary-card">
                    <span className="summary-card-num">{totalSrt}</span>
                    <span className="summary-card-label">{t('srt.totalStreams')}</span>
                </div>
                <div className="summary-card summary-card-online">
                    <span className="summary-card-num">{totalOnline}</span>
                    <span className="summary-card-label">{t('srt.running')}</span>
                </div>
                <div className="summary-card summary-card-offline">
                    <span className="summary-card-num">{totalOffline}</span>
                    <span className="summary-card-label">{t('srt.stopped')}</span>
                </div>
            </div>

            {/* Search */}
            <div className="table-toolbar">
                <div className="table-search-wrap">
                    <svg className="table-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                        className="table-search-input"
                        type="text"
                        placeholder={t('srt.searchPlaceholder')}
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            {/* Table with merged machine rows */}
            <div className="card-light table-card">
                <div className="table-scroll-shell">
                    <div className="table-scroll">
                        <table className="data-table compact-table">
                            <thead>
                                <tr>
                                    <th>{t('srt.thMachine')}</th>
                                    <th>IP</th>
                                    <th>{t('srt.thName')}</th>
                                    <th>{t('srt.thPort')}</th>
                                    <th>{t('srt.thType')}</th>
                                    <th>{t('srt.thHost')}</th>
                                    <th>Stream ID</th>
                                    <th>Quality</th>
                                    <th>{t('srt.thStatus')}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredGroups.length === 0 ? (
                                    <tr>
                                        <td colSpan={9} className="table-empty-cell">
                                            {t('srt.noData')}
                                        </td>
                                    </tr>
                                ) : (
                                    filteredGroups.map((group, gi) =>
                                        group.srtList.map((srt, si) => {
                                            const st = toOnOff(srt.status)
                                            const isFirst = si === 0
                                            return (
                                                <tr key={`srt-${gi}-${si}`} className={gi % 2 === 0 ? '' : 'row-alt'}>
                                                    {isFirst && (
                                                        <>
                                                            <td rowSpan={group.srtList.length} className="table-machine-name merged-cell">
                                                                {group.machineName}
                                                            </td>
                                                            <td rowSpan={group.srtList.length} className="mono table-ip merged-cell">
                                                                {group.machineIp}
                                                            </td>
                                                        </>
                                                    )}
                                                    <td>{srt.nameSRT || '-'}</td>
                                                    <td className="mono">{srt.port || '-'}</td>
                                                    <td>{renderTypePill(srt.type)}</td>
                                                    <td>{srt.hostname || '-'}</td>
                                                    <td className="mono">{srt.stream_id || '-'}</td>
                                                    <td>{srt.quality || '-'}</td>
                                                    <td>
                                                        <span className={`pill-light ${st === 'ON' ? 'pill-light-on' : 'pill-light-off'}`}>
                                                            {st}
                                                        </span>
                                                    </td>
                                                </tr>
                                            )
                                        }),
                                    )
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </>
    )
}
