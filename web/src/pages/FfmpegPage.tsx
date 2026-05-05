import { useMemo, useState } from 'react'
import { useDashboardContext } from '../hooks/useDashboardContext'
import { normalizeFfmpegList, type BackendFfmpegItem } from '../services/api'

interface MachineFfmpegGroup {
    machineName: string
    machineIp: string
    ffmpegList: BackendFfmpegItem[]
}

function formatMbps(value: number | undefined | null): string {
    if (value === null || value === undefined) return '-'
    return `${value.toFixed(3)} Mbps`
}

export default function FfmpegPage() {
    const { rows, loading, error } = useDashboardContext()
    const [searchTerm, setSearchTerm] = useState('')

    const machineGroups = useMemo(() => {
        const groups: MachineFfmpegGroup[] = []
        rows.forEach((item) => {
            const ffmpegList = normalizeFfmpegList(item.data.ffmpeg)
            if (ffmpegList.length === 0) return
            groups.push({
                machineName: item.data.name || 'Unknown',
                machineIp: item.data.ip || '-',
                ffmpegList,
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
                g.ffmpegList.some(
                    (f) =>
                        (f.name || '').toLowerCase().includes(term) ||
                        String(f.pid || '').includes(term),
                ),
        )
    }, [machineGroups, searchTerm])

    const totalProcesses = useMemo(() => filteredGroups.reduce((acc, g) => acc + g.ffmpegList.length, 0), [filteredGroups])
    const totalSending = useMemo(
        () =>
            filteredGroups.reduce(
                (acc, g) => acc + g.ffmpegList.filter((f) => (f.send ?? 0) > 0.001).length,
                0,
            ),
        [filteredGroups],
    )

    if (loading) {
        return (
            <>
                <div className="page-header">
                    <h2 className="page-title">FFmpeg</h2>
                    <p className="page-description">Thông tin process FFmpeg từ tất cả các máy.</p>
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
                    <h2 className="page-title">FFmpeg</h2>
                </div>
                <div className="card-light error-card-light">{error}</div>
            </>
        )
    }

    return (
        <>
            <div className="page-header">
                <h2 className="page-title">FFmpeg</h2>
                <p className="page-description">Tổng hợp thông tin FFmpeg processes và băng thông từ tất cả các máy.</p>
            </div>

            {/* Summary Cards */}
            <div className="srt-summary-row">
                <div className="summary-card">
                    <span className="summary-card-num">{filteredGroups.length}</span>
                    <span className="summary-card-label">Máy</span>
                </div>
                <div className="summary-card summary-card-online">
                    <span className="summary-card-num">{totalProcesses}</span>
                    <span className="summary-card-label">Tổng Process</span>
                </div>
                <div className="summary-card" style={{ borderColor: 'rgba(245,158,11,.2)' }}>
                    <span className="summary-card-num" style={{ color: '#f59e0b' }}>{totalSending}</span>
                    <span className="summary-card-label">Đang gửi</span>
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
                        placeholder="Tìm theo tên máy, IP, PID..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            {/* Table */}
            <div className="card-light table-card">
                <div className="table-scroll-shell">
                    <div className="table-scroll">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Máy</th>
                                    <th>IP</th>
                                    <th>Process Name</th>
                                    <th>PID</th>
                                    <th>Send (Mbps)</th>
                                    <th>Receive (Mbps)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredGroups.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="table-empty-cell">
                                            Không có dữ liệu FFmpeg.
                                        </td>
                                    </tr>
                                ) : (
                                    filteredGroups.map((group, gi) =>
                                        group.ffmpegList.map((ff, fi) => {
                                            const isFirst = fi === 0
                                            const isSending = (ff.send ?? 0) > 0.001
                                            const isReceiving = (ff.recv ?? 0) > 0.001
                                            return (
                                                <tr key={`ff-${gi}-${fi}`} className={gi % 2 === 0 ? '' : 'row-alt'}>
                                                    {isFirst && (
                                                        <>
                                                            <td rowSpan={group.ffmpegList.length} className="table-machine-name merged-cell">
                                                                {group.machineName}
                                                            </td>
                                                            <td rowSpan={group.ffmpegList.length} className="mono table-ip merged-cell">
                                                                {group.machineIp}
                                                            </td>
                                                        </>
                                                    )}
                                                    <td style={{ fontWeight: 600 }}>
                                                        <span className="ffmpeg-process-name">{ff.name || '-'}</span>
                                                    </td>
                                                    <td className="mono" style={{ fontSize: '.75rem', color: '#64748b' }}>
                                                        {ff.pid || '-'}
                                                    </td>
                                                    <td>
                                                        <span className={`ffmpeg-bw-value ${isSending ? 'ffmpeg-bw-active' : ''}`}>
                                                            {formatMbps(ff.send)}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <span className={`ffmpeg-bw-value ${isReceiving ? 'ffmpeg-bw-recv-active' : ''}`}>
                                                            {formatMbps(ff.recv)}
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
