import { useMemo, useState, useRef, useEffect } from 'react'
import { useDashboardContext } from '../hooks/useDashboardContext'
import { 
    normalizeRecordList, 
    normalizeMultiRecordList, 
    type RecordItem, 
    type MultiRecordItem 
} from '../services/api'

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
            { id: '__all__', label: 'Tất cả Game' }
        ]
        if (gameAssignments) {
            gameAssignments.forEach((assignment: any) => {
                if (assignment.game && assignment.visible_status !== 'OFF' && !list.some(g => g.id === assignment.game)) {
                    list.push({ id: assignment.game, label: assignment.game })
                }
            })
        }
        return list
    }, [gameAssignments])

    const selectedLabel = games.find(g => g.id === selectedGame)?.label || 'Chọn Game'

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
                        <h2 className="page-title">Record & MultiCorder</h2>
                        <p className="page-description">Thông số và cấu hình ghi vMix từ tất cả các máy.</p>
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
                    <h2 className="page-title">Record & MultiCorder</h2>
                </div>
                <div className="card-light error-card-light">{error}</div>
            </>
        )
    }

    return (
        <>
            <div className="page-header flex flex-col md:flex-row justify-between items-start md:items-center gap-4" style={{ marginBottom: '1.5rem' }}>
                <div>
                    <h2 className="page-title">Record & MultiCorder</h2>
                    <p className="page-description">Cấu hình ghi thông thường (Standard Record) và ghi đa kênh (MultiCorder) của vMix theo thời gian thực.</p>
                </div>

                {/* Game Filter */}
                <div className="flex items-center gap-3 flex-wrap">
                    {!isGameLocked ? (
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-slate-400">Kênh Game:</span>
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
                                <span className="text-xs font-semibold text-slate-400">Kênh Game:</span>
                                <span className="text-xs font-bold text-purple-600 dark:text-purple-400">{selectedLabel}</span>
                            </div>
                        ) : null
                    )}
                </div>
            </div>

            {filteredRows.length === 0 ? (
                <div className="card-light" style={{ padding: '2.5rem', textAlign: 'center', color: '#94a3b8' }}>
                    Chưa có dữ liệu từ backend hoặc không tìm thấy máy có cấu hình phù hợp.
                </div>
            ) : (
                /* Consolidated Grid Table summary view directly */
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                    
                    {/* Consolidated Record Table */}
                    <div className="card-light table-card" style={{ padding: '1.5rem', border: '1px solid rgba(226, 232, 240, 0.8)' }}>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#1e293b', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            BẢNG TỔNG HỢP RECORD (STANDARD RECORDING)
                        </h3>
                        {flatRecords.length === 0 ? (
                            <div style={{ padding: '1.5rem', textAlign: 'center', color: '#94a3b8' }}>Không có cấu hình ghi.</div>
                        ) : (
                            <div className="table-scroll-shell" style={{ border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                                <div className="table-scroll">
                                    <table className="data-table compact-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                        <thead>
                                            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569', minWidth: '120px' }}>Máy</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569', minWidth: '120px' }}>IP</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>Profile</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>Đường dẫn lưu file</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>Định dạng</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>Độ phân giải</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>FPS</th>
                                                <th style={{ padding: '10px', textAlign: 'right', fontWeight: 700, color: '#475569' }}>V.Bitrate</th>
                                                <th style={{ padding: '10px', textAlign: 'right', fontWeight: 700, color: '#475569' }}>A.Bitrate</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>Delay</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>HW Accel</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>Audio</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>Ch</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>Src Ch</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>Frag</th>
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
                            BẢNG TỔNG HỢP MULTICORDER
                        </h3>
                        {flatMultiRecords.length === 0 ? (
                            <div style={{ padding: '1.5rem', textAlign: 'center', color: '#94a3b8' }}>Không có cấu hình MultiCorder.</div>
                        ) : (
                            <div className="table-scroll-shell" style={{ border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                                <div className="table-scroll">
                                    <table className="data-table compact-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                        <thead>
                                            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569', minWidth: '120px' }}>Máy</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569', minWidth: '120px' }}>IP</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>Source Name</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>Trạng thái</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>Thư mục lưu</th>
                                                <th style={{ padding: '10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>Định dạng</th>
                                                <th style={{ padding: '10px', textAlign: 'right', fontWeight: 700, color: '#475569' }}>V.Bitrate</th>
                                                <th style={{ padding: '10px', textAlign: 'right', fontWeight: 700, color: '#475569' }}>A.Bitrate</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>Audio Src</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>Interval</th>
                                                <th style={{ padding: '10px', textAlign: 'center', fontWeight: 700, color: '#475569' }}>Show All</th>
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
