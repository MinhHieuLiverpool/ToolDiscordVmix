import { useMemo, useState, useCallback } from 'react'
import { useDashboardContext } from '../hooks/useDashboardContext'
import { normalizeStreamKeysList, type BackendStreamKeyItem } from '../services/api'

interface MachineStreamKeyGroup {
    machineName: string
    machineIp: string
    keys: BackendStreamKeyItem[]
}

/* ── Eye icons (show / hide) ─────────────────── */
const EyeIcon = () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}>
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
    </svg>
)
const EyeOffIcon = () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}>
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
        <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
        <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
        <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
)

function maskKey(key: string): string {
    if (!key || key === '-') return '-'
    if (key.length <= 6) return '•'.repeat(key.length)
    return `${key.substring(0, 4)}${'•'.repeat(Math.min(12, key.length - 4))}${key.substring(key.length - 2)}`
}

export default function UrlKeyPage() {
    const { rows, loading, error } = useDashboardContext()
    const [searchTerm, setSearchTerm] = useState('')
    // Track which keys are revealed: "gi-ki" => true
    const [revealedKeys, setRevealedKeys] = useState<Record<string, boolean>>({})

    const toggleKey = useCallback((id: string) => {
        setRevealedKeys((prev) => ({ ...prev, [id]: !prev[id] }))
    }, [])

    const machineGroups = useMemo(() => {
        const groups: MachineStreamKeyGroup[] = []
        rows.forEach((item) => {
            const keys = normalizeStreamKeysList(item.data.stream_keys)
            if (keys.length === 0) return
            groups.push({
                machineName: item.data.name || 'Unknown',
                machineIp: item.data.ip || '-',
                keys,
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
                g.keys.some(
                    (k) =>
                        (k.stream || '').toLowerCase().includes(term) ||
                        (k.url || '').toLowerCase().includes(term) ||
                        (k.key || '').toLowerCase().includes(term),
                ),
        )
    }, [machineGroups, searchTerm])

    const totalKeys = useMemo(() => filteredGroups.reduce((acc, g) => acc + g.keys.length, 0), [filteredGroups])
    const totalWithUrl = useMemo(
        () =>
            filteredGroups.reduce(
                (acc, g) => acc + g.keys.filter((k) => k.url && k.url !== '-' && k.url !== '(trong)').length,
                0,
            ),
        [filteredGroups],
    )

    if (loading) {
        return (
            <>
                <div className="page-header">
                    <h2 className="page-title">URL & Key</h2>
                    <p className="page-description">Stream URL và Key từ tất cả các máy.</p>
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
                    <h2 className="page-title">URL & Key</h2>
                </div>
                <div className="card-light error-card-light">{error}</div>
            </>
        )
    }

    return (
        <>
            <div className="page-header">
                <h2 className="page-title">URL & Key</h2>
                <p className="page-description">Tổng hợp URL và stream key từ tất cả các máy trong hệ thống.</p>
            </div>

            {/* Summary Cards */}
            <div className="srt-summary-row">
                <div className="summary-card">
                    <span className="summary-card-num">{filteredGroups.length}</span>
                    <span className="summary-card-label">Máy</span>
                </div>
                <div className="summary-card summary-card-online">
                    <span className="summary-card-num">{totalKeys}</span>
                    <span className="summary-card-label">Tổng Stream</span>
                </div>
                <div className="summary-card" style={{ borderColor: 'rgba(99,102,241,.2)' }}>
                    <span className="summary-card-num" style={{ color: '#6366f1' }}>{totalWithUrl}</span>
                    <span className="summary-card-label">Có URL</span>
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
                        placeholder="Tìm theo tên máy, IP, URL, key..."
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
                                    <th>Stream</th>
                                    <th>URL</th>
                                    <th>Key</th>
                                    <th style={{ width: 60, textAlign: 'center' }}>Xem</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredGroups.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="table-empty-cell">
                                            Không có dữ liệu URL & Key.
                                        </td>
                                    </tr>
                                ) : (
                                    filteredGroups.map((group, gi) =>
                                        group.keys.map((keyItem, ki) => {
                                            const cellId = `${gi}-${ki}`
                                            const isFirst = ki === 0
                                            const urlText = keyItem.url || '-'
                                            const keyText = keyItem.key || '-'
                                            const hasUrl = urlText !== '-' && urlText !== '(trong)'
                                            const hasKey = keyText !== '-' && keyText !== '' && keyText !== '(trong)'
                                            const isRevealed = revealedKeys[cellId] ?? false
                                            return (
                                                <tr key={`key-${cellId}`} className={gi % 2 === 0 ? '' : 'row-alt'}>
                                                    {isFirst && (
                                                        <>
                                                            <td rowSpan={group.keys.length} className="table-machine-name merged-cell">
                                                                {group.machineName}
                                                            </td>
                                                            <td rowSpan={group.keys.length} className="mono table-ip merged-cell">
                                                                {group.machineIp}
                                                            </td>
                                                        </>
                                                    )}
                                                    <td style={{ fontWeight: 600 }}>{keyItem.stream || '-'}</td>
                                                    <td>
                                                        <span
                                                            className={`url-key-cell ${hasUrl ? 'url-key-active' : 'url-key-empty'}`}
                                                            title={urlText}
                                                        >
                                                            {urlText}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <span className="key-cell-mask" title={isRevealed ? keyText : undefined}>
                                                            {hasKey
                                                                ? (isRevealed ? keyText : maskKey(keyText))
                                                                : '-'}
                                                        </span>
                                                    </td>
                                                    <td style={{ textAlign: 'center' }}>
                                                        {hasKey && (
                                                            <button
                                                                type="button"
                                                                className={`key-reveal-btn ${isRevealed ? 'key-reveal-btn-active' : ''}`}
                                                                onClick={() => toggleKey(cellId)}
                                                                title={isRevealed ? 'Ẩn key' : 'Xem key'}
                                                            >
                                                                {isRevealed ? <EyeOffIcon /> : <EyeIcon />}
                                                            </button>
                                                        )}
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
