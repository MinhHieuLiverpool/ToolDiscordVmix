import { useMemo, useState, useRef, useEffect } from 'react'
import { useDashboardContext } from '../hooks/useDashboardContext'
import { 
    normalizeRecordList, 
    normalizeMultiRecordList, 
    type RecordItem, 
    type MultiRecordItem 
} from '../services/api'
import { useLanguage } from '../config/i18n'

function renderStatusPill(val: string | undefined) {
    if (!val) return <span style={{ color: '#94a3b8' }}>-</span>
    const cleanVal = val.replace(/^[🟢🔴]\s*/, '').trim()
    const isGreen = val.includes('🟢') || ['YES', 'ON', 'TRUE'].includes(cleanVal.toUpperCase())
    const isRed = val.includes('🔴') || ['NO', 'OFF', 'FALSE'].includes(cleanVal.toUpperCase())

    return (
        <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '3px',
            padding: '2px 6px',
            borderRadius: '4px',
            fontSize: '0.75rem',
            fontWeight: 600,
            background: isGreen ? '#d1fae5' : isRed ? '#fee2e2' : '#f1f5f9',
            color: isGreen ? '#065f46' : isRed ? '#991b1b' : '#64748b'
        }}>
            <span style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: isGreen ? '#10b981' : isRed ? '#ef4444' : '#94a3b8'
            }} />
            {cleanVal}
        </span>
    )
}

interface FlatRecordItem extends RecordItem {
    machineName: string
    machineIp: string
    port: string | number
    rowSpan: number
    isFirstOfMachine: boolean
}

interface FlatMultiRecordItem extends MultiRecordItem {
    machineName: string
    machineIp: string
    port: string | number
    rowSpan: number
    isFirstOfMachine: boolean
}

export default function RecordMulticorderPage() {
    const { t } = useLanguage()
    const { 
        rows, 
        loading, 
        error,
        selectedGame,
        setSelectedGame,
        gameAssignments,
        isGameLocked
    } = useDashboardContext() as any

    const [dropdownOpen, setDropdownOpen] = useState(false)
    const dropdownRef = useRef<HTMLDivElement>(null)

    // Close dropdown on outside click
    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setDropdownOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClick)
        return () => document.removeEventListener('mousedown', handleClick)
    }, [])

    const games = useMemo(() => {
        const list = [
            { id: '__all__', label: t('overview.allGames') }
        ]
        if (gameAssignments) {
            gameAssignments.forEach((assignment: any) => {
                if (assignment.game && assignment.visible_status !== 'OFF' && !list.some(g => g.id === assignment.game)) {
                    list.push({ id: assignment.game, label: assignment.game })
                }
            })
        }
        return list
    }, [gameAssignments, t])

    const selectedLabel = games.find(g => g.id === selectedGame)?.label || t('overview.selectGame')

    // ONLY get machines that have standard record OR multicorder configurations
    const filteredRows = useMemo(() => {
        return rows.filter((row: any) => {
            const recordList = normalizeRecordList(row.data.List_REcord)
            const multiRecordList = normalizeMultiRecordList(row.data.ListMultiREcord || (row.data as any).ListMultiRecord)
            
            return recordList.length > 0 || multiRecordList.length > 0
        })
    }, [rows])

    // Flat Record List for summary table
    const flatRecords = useMemo(() => {
        const list: FlatRecordItem[] = []
        filteredRows.forEach((row: any) => {
            const recList = normalizeRecordList(row.data.List_REcord)
            if (recList.length === 0) return
            recList.forEach((rec, idx) => {
                list.push({
                    ...rec,
                    machineName: row.data.name || 'Unknown',
                    machineIp: row.data.ip || '-',
                    port: row.data.port || '-',
                    rowSpan: recList.length,
                    isFirstOfMachine: idx === 0
                })
            })
        })
        return list
    }, [filteredRows])

    // Flat MultiRecord List for summary table
    const flatMultiRecords = useMemo(() => {
        const list: FlatMultiRecordItem[] = []
        filteredRows.forEach((row: any) => {
            const mRecList = normalizeMultiRecordList(row.data.ListMultiREcord || (row.data as any).ListMultiRecord)
            if (mRecList.length === 0) return
            mRecList.forEach((mRec, idx) => {
                list.push({
                    ...mRec,
                    machineName: row.data.name || 'Unknown',
                    machineIp: row.data.ip || '-',
                    port: row.data.port || '-',
                    rowSpan: mRecList.length,
                    isFirstOfMachine: idx === 0
                })
            })
        })
        return list
    }, [filteredRows])

    if (loading) {
        return (
            <>
                <div className="page-header flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 className="page-title">{t('record.title')}</h2>
                        <p className="page-description">{t('record.description')}</p>
                    </div>
                </div>
                <div className="vmix-grid" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    {Array.from({ length: 3 }).map((_, i) => (
                        <div key={`skel-${i}`} className="card-light skeleton-card-light shimmer-loading" style={{ height: '220px', borderRadius: '12px' }} />
                    ))}
                </div>
            </>
        )
    }

    if (error) {
        return (
            <>
                <div className="page-header">
                    <h2 className="page-title">{t('record.title')}</h2>
                </div>
                <div className="card-light error-card-light">{error}</div>
            </>
        )
    }

    return (
        <>
            <div className="page-header flex flex-col md:flex-row justify-between items-start md:items-center gap-4" style={{ marginBottom: '1.5rem' }}>
                <div>
                    <h2 className="page-title">{t('record.title')}</h2>
                    <p className="page-description">{t('record.description')}</p>
                </div>

                {/* Game Filter */}
                <div className="flex items-center gap-3 flex-wrap">
                    {!isGameLocked ? (
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-slate-400">{t('overview.gameChannel')}</span>
                            <div className="custom-dropdown" ref={dropdownRef} style={{ minWidth: '180px' }}>
                                <button
                                    type="button"
                                    className={`dropdown-trigger ${dropdownOpen ? 'dropdown-open' : ''}`}
                                    onClick={() => setDropdownOpen(!dropdownOpen)}
                                >
                                    <span className="dropdown-trigger-text">{selectedLabel}</span>
                                    <svg className={`dropdown-chevron ${dropdownOpen ? 'chevron-up' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                        <polyline points="6 9 12 15 18 9" />
                                    </svg>
                                </button>

                                {dropdownOpen && (
                                    <div className="dropdown-menu">
                                        <div className="dropdown-options">
                                            {games.map((g) => (
                                                <button
                                                    type="button"
                                                    key={g.id}
                                                    className={`dropdown-option ${selectedGame === g.id ? 'option-active' : ''}`}
                                                    onClick={() => {
                                                        setSelectedGame(g.id)
                                                        setDropdownOpen(false)
                                                    }}
                                                >
                                                    {g.label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        selectedGame !== '__all__' ? (
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 dark:bg-slate-900 rounded-lg">
                                <span className="text-xs font-semibold text-slate-400">{t('overview.gameChannel')}</span>
                                <span className="text-xs font-bold text-purple-600 dark:text-purple-400">{selectedLabel}</span>
                            </div>
                        ) : null
                    )}
                </div>
            </div>

            {filteredRows.length === 0 ? (
                <div className="card-light" style={{ padding: '2.5rem', textAlign: 'center', color: '#94a3b8' }}>
                    {t('record.noData')}
                </div>
            ) : (
                /* Consolidated Grid Table summary view directly */
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                    
                    {/* Consolidated Record Table */}
                    <div className="card-light table-card" style={{ padding: '1.5rem', border: '1px solid rgba(226, 232, 240, 0.8)' }}>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#1e293b', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            {t('record.standardTitle')}
                        </h3>
                        {flatRecords.length === 0 ? (
                            <div style={{ padding: '1.5rem', textAlign: 'center', color: '#94a3b8' }}>{t('record.noStandardData')}</div>
                        ) : (
                            <div className="table-scroll-shell" style={{ border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                                <div className="table-scroll">
                                    <table className="data-table compact-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                        <thead>
                                            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569', minWidth: '120px' }}>{t('record.thMachine')}</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569', minWidth: '120px' }}>IP</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>{t('record.thProfile')}</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>{t('record.thPath')}</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>{t('record.thFormat')}</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>{t('record.thResolution')}</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>{t('record.thFps')}</th>
                                                <th style={{ padding: '10px', textAlign: 'right', fontWeight: 700, color: '#475569' }}>{t('record.thVBitrate')}</th>
                                                <th style={{ padding: '10px', textAlign: 'right', fontWeight: 700, color: '#475569' }}>{t('record.thABitrate')}</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>{t('record.thDelay')}</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>{t('record.thHwAccel')}</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>{t('record.thAudio')}</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>{t('record.thCh')}</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>{t('record.thSrcCh')}</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>{t('record.thFrag')}</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {flatRecords.map((rec, rIdx) => (
                                                <tr key={`flat-rec-${rIdx}`} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                                    {rec.isFirstOfMachine && (
                                                        <>
                                                            <td rowSpan={rec.rowSpan} style={{ padding: '10px', fontWeight: 700, color: '#1e293b', background: '#f8fafc', borderRight: '1px solid #e2e8f0', verticalAlign: 'middle' }}>
                                                                {rec.machineName}
                                                            </td>
                                                            <td rowSpan={rec.rowSpan} className="mono" style={{ padding: '10px', color: '#64748b', background: '#f8fafc', borderRight: '1px solid #e2e8f0', verticalAlign: 'middle' }}>
                                                                {rec.machineIp}:{rec.port}
                                                            </td>
                                                        </>
                                                    )}
                                                    <td style={{ padding: '10px', fontWeight: 600, color: '#1e293b' }}>{rec.profile || '-'}</td>
                                                    <td style={{ padding: '10px', color: '#334155', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={rec.filename}>
                                                        {rec.filename || '-'}
                                                    </td>
                                                    <td style={{ padding: '10px', color: '#64748b' }}>{rec.format || '-'}</td>
                                                    <td style={{ padding: '10px', color: '#334155', fontFamily: 'monospace' }}>{rec.resolution || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'center', color: '#334155' }}>{rec.fps || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'right', color: '#0f766e', fontWeight: 600 }}>{rec.v_bitrate || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'right', color: '#0369a1' }}>{rec.a_bitrate || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'center', color: '#64748b' }}>{rec.audio_delay || '0'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'center' }}>{renderStatusPill(rec.hw_accel)}</td>
                                                    <td style={{ padding: '10px', textAlign: 'center' }}>{renderStatusPill(rec.audio_enabled)}</td>
                                                    <td style={{ padding: '10px', textAlign: 'center', color: '#64748b' }}>{rec.audio_channel || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'center', color: '#64748b' }}>{rec.source_channel || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'center' }}>{renderStatusPill(rec.fragmented)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Consolidated MultiCorder Table */}
                    <div className="card-light table-card" style={{ padding: '1.5rem', border: '1px solid rgba(226, 232, 240, 0.8)' }}>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#1e293b', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            {t('record.multiTitle')}
                        </h3>
                        {flatMultiRecords.length === 0 ? (
                            <div style={{ padding: '1.5rem', textAlign: 'center', color: '#94a3b8' }}>{t('record.noMultiData')}</div>
                        ) : (
                            <div className="table-scroll-shell" style={{ border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                                <div className="table-scroll">
                                    <table className="data-table compact-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                        <thead>
                                            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569', minWidth: '120px' }}>{t('record.thMachine')}</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569', minWidth: '120px' }}>IP</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>{t('record.thSourceName')}</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>{t('record.thStatus')}</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>{t('record.thFolder')}</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>{t('record.thFormat')}</th>
                                                <th style={{ padding: '10px', textAlign: 'right', fontWeight: 700, color: '#475569' }}>{t('record.thVBitrate')}</th>
                                                <th style={{ padding: '10px', textAlign: 'right', fontWeight: 700, color: '#475569' }}>{t('record.thABitrate')}</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>{t('record.thAudioSrc')}</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>{t('record.thInterval')}</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>{t('record.thShowAll')}</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {flatMultiRecords.map((mRec, mIdx) => (
                                                <tr key={`flat-multi-${mIdx}`} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                                    {mRec.isFirstOfMachine && (
                                                        <>
                                                            <td rowSpan={mRec.rowSpan} style={{ padding: '10px', fontWeight: 700, color: '#1e293b', background: '#f8fafc', borderRight: '1px solid #e2e8f0', verticalAlign: 'middle' }}>
                                                                {mRec.machineName}
                                                            </td>
                                                            <td rowSpan={mRec.rowSpan} className="mono" style={{ padding: '10px', color: '#64748b', background: '#f8fafc', borderRight: '1px solid #e2e8f0', verticalAlign: 'middle' }}>
                                                                {mRec.machineIp}:{mRec.port}
                                                            </td>
                                                        </>
                                                    )}
                                                    <td style={{ padding: '10px', fontWeight: 600, color: '#1e293b' }}>{mRec.source || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'center' }}>
                                                        {renderStatusPill(mRec.status)}
                                                    </td>
                                                    <td style={{ padding: '10px', color: '#334155', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={mRec.folder}>
                                                        {mRec.folder || '-'}
                                                    </td>
                                                    <td style={{ padding: '10px', color: '#64748b' }}>{mRec.format || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'right', color: '#0f766e', fontWeight: 600 }}>{mRec.v_bitrate || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'right', color: '#0369a1' }}>{mRec.a_bitrate || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'center', color: '#64748b' }}>{mRec.audio_src || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'center', color: '#64748b' }}>{mRec.interval || '-'}</td>
                                                    <td style={{ padding: '10px', textAlign: 'center' }}>{renderStatusPill(mRec.show_all)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </>
    )
}
