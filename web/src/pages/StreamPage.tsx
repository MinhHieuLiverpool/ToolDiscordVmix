import { useMemo, useState } from 'react'
import { useDashboardContext } from '../hooks/useDashboardContext'
import { normalizeStreamList, type BackendStreamItem } from '../services/api'
import { formatBitrate, toOnOff } from '../components/DialogHelpers'

interface MachineStreamGroup {
    machineName: string
    machineIp: string
    streamList: BackendStreamItem[]
}

export default function StreamPage() {
    const { rows, loading, error } = useDashboardContext()
    const [searchTerm, setSearchTerm] = useState('')

    // Group stream data by machine
    const machineGroups = useMemo(() => {
        const groups: MachineStreamGroup[] = []
        rows.forEach((item) => {
            const streamList = normalizeStreamList(item.data.stream)
            if (streamList.length === 0) return
            groups.push({
                machineName: item.data.name || 'Unknown',
                machineIp: `${item.data.ip || '-'}:${item.data.port || '-'}`,
                streamList,
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
                g.streamList.some((s) => (s.stream || '').toLowerCase().includes(term)),
        )
    }, [machineGroups, searchTerm])

    const totalStreams = useMemo(() => filteredGroups.reduce((acc, g) => acc + g.streamList.length, 0), [filteredGroups])
    const totalRunning = useMemo(
        () => filteredGroups.reduce((acc, g) => acc + g.streamList.filter((s) => toOnOff(s.runtime) === 'ON').length, 0),
        [filteredGroups],
    )
    const totalStopped = totalStreams - totalRunning

    if (loading) {
        return (
            <>
                <div className="page-header">
                    <h2 className="page-title">Stream</h2>
                    <p className="page-description">Thông số stream từ tất cả các máy.</p>
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
                    <h2 className="page-title">Stream</h2>
                </div>
                <div className="card-light error-card-light">{error}</div>
            </>
        )
    }

    return (
        <>
            <div className="page-header">
                <h2 className="page-title">Stream</h2>
                <p className="page-description">Tổng hợp thông số stream từ tất cả các máy trong hệ thống.</p>
            </div>

            {/* Summary Cards */}
            <div className="srt-summary-row">
                <div className="summary-card">
                    <span className="summary-card-num">{totalStreams}</span>
                    <span className="summary-card-label">Tổng Stream</span>
                </div>
                <div className="summary-card summary-card-online">
                    <span className="summary-card-num">{totalRunning}</span>
                    <span className="summary-card-label">Đang chạy</span>
                </div>
                <div className="summary-card summary-card-offline">
                    <span className="summary-card-num">{totalStopped}</span>
                    <span className="summary-card-label">Dừng</span>
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
                        placeholder="Tìm theo tên máy, IP, tên stream..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            {/* Table with merged machine rows */}
            <div className="card-light table-card">
                <div className="table-scroll-shell">
                    <div className="table-scroll">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Máy</th>
                                    <th>IP</th>
                                    <th>Stream</th>
                                    <th>Runtime</th>
                                    <th>Health</th>
                                    <th>Video Bitrate</th>
                                    <th>Size</th>
                                    <th>Audio Bitrate</th>
                                    <th>Level</th>
                                    <th>Preset</th>
                                    <th>Keyframe</th>
                                    <th>Actual</th>
                                    <th>Target</th>
                                    <th>Speed</th>
                                    <th>Dropped</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredGroups.length === 0 ? (
                                    <tr>
                                        <td colSpan={15} className="table-empty-cell">
                                            Không có dữ liệu Stream.
                                        </td>
                                    </tr>
                                ) : (
                                    filteredGroups.map((group, gi) =>
                                        group.streamList.map((stream, si) => {
                                            const runtimeText = toOnOff(stream.runtime)
                                            const healthText = String(stream.health || '-').toUpperCase()
                                            const healthClass =
                                                healthText === 'GOOD' || healthText === 'XANH'
                                                    ? 'health-dot-good'
                                                    : healthText === 'BAD' || healthText === 'DO' || healthText === 'ĐỎ'
                                                        ? 'health-dot-bad'
                                                        : healthText === 'VANG' || healthText === 'VÀNG'
                                                            ? 'health-dot-warn'
                                                            : ''
                                            const isFirst = si === 0
                                            return (
                                                <tr key={`stream-${gi}-${si}`} className={gi % 2 === 0 ? '' : 'row-alt'}>
                                                    {isFirst && (
                                                        <>
                                                            <td rowSpan={group.streamList.length} className="table-machine-name merged-cell">
                                                                {group.machineName}
                                                            </td>
                                                            <td rowSpan={group.streamList.length} className="mono table-ip merged-cell">
                                                                {group.machineIp}
                                                            </td>
                                                        </>
                                                    )}
                                                    <td>{stream.stream || '-'}</td>
                                                    <td>
                                                        <span className={`pill-light ${runtimeText === 'ON' ? 'pill-light-on' : 'pill-light-off'}`}>
                                                            {runtimeText}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <span className="health-dot-wrap">
                                                            <span className={`health-dot ${healthClass}`} title={healthText} />
                                                            <span className="health-dot-text">{healthText}</span>
                                                        </span>
                                                    </td>
                                                    <td>{formatBitrate(stream.vbit)}</td>
                                                    <td>{stream.size || '-'}</td>
                                                    <td>{formatBitrate(stream.abit)}</td>
                                                    <td>{stream.level || '-'}</td>
                                                    <td>{stream.preset || '-'}</td>
                                                    <td>{stream.keyframe || '-'}</td>
                                                    <td>{stream.actual ?? '-'}</td>
                                                    <td>{stream.target ?? '-'}</td>
                                                    <td>{stream.speed || '-'}</td>
                                                    <td>{stream.dropped ?? '-'}</td>
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
