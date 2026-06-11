import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { showToast } from '../components/ui/Toast'

type ParsedLogLine = {
    timestamp: string
    timeOnly: string
    dateOnly: string
    machineName: string
    ip: string
    ipwan: string
    rawJson: string
}

export default function ImportDebugPage() {
    const navigate = useNavigate()
    const [logLines, setLogLines] = useState<ParsedLogLine[]>([])
    const [fileName, setFileName] = useState('')
    
    // Filters
    const [filterName, setFilterName] = useState('')
    const [filterIp, setFilterIp] = useState('')
    const [filterIpwan, setFilterIpwan] = useState('')
    const [filterHour, setFilterHour] = useState('') // e.g. "19" or "19:05"
    const [filterTimeStart, setFilterTimeStart] = useState('') // e.g. "12:00:00" or "12:00"
    const [filterTimeEnd, setFilterTimeEnd] = useState('') // e.g. "13:30:00" or "13:30"

    const parseTimeToSeconds = (timeStr: string): number | null => {
        const trimmed = timeStr.trim()
        if (!trimmed) return null
        const parts = trimmed.split(':')
        const hrs = parseInt(parts[0], 10)
        if (isNaN(hrs)) return null
        const mins = parts[1] ? parseInt(parts[1], 10) : 0
        const secs = parts[2] ? parseInt(parts[2], 10) : 0
        return hrs * 3600 + (isNaN(mins) ? 0 : mins) * 60 + (isNaN(secs) ? 0 : secs)
    }

    const parseLogLine = (line: string): ParsedLogLine | null => {
        const trimmed = line.trim()
        if (!trimmed) return null
        
        // Find closing bracket of timestamp
        const bracketIndex = trimmed.indexOf(' ]')
        if (bracketIndex === -1) return null
        
        const timestamp = trimmed.substring(0, bracketIndex + 2) // [ HH:MM:SS - DD/MM/YYYY ]
        const headerParts = timestamp.replace('[', '').replace(']', '').split(' - ')
        const timeOnly = headerParts[0]?.trim() || ''
        const dateOnly = headerParts[1]?.trim() || ''
        
        const rest = trimmed.substring(bracketIndex + 2).trim()
        if (!rest.startsWith('-')) return null
        
        const restClean = rest.substring(1).trim() // Remove leading "-"
        
        // Split rest by " - " up to 3 times to extract machineName, ip, ipwan, and JSON
        const parts: string[] = []
        let currentStr = restClean
        for (let i = 0; i < 3; i++) {
            const idx = currentStr.indexOf(' - ')
            if (idx === -1) break
            parts.push(currentStr.substring(0, idx).trim())
            currentStr = currentStr.substring(idx + 3).trim()
        }
        
        if (parts.length < 3) return null
        
        return {
            timestamp,
            timeOnly,
            dateOnly,
            machineName: parts[0],
            ip: parts[1],
            ipwan: parts[2],
            rawJson: currentStr,
        }
    }

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (!file) return
        
        setFileName(file.name)
        const reader = new FileReader()
        reader.onload = (e) => {
            const text = e.target?.result as string
            if (!text) {
                showToast('File trống hoặc không hợp lệ.', 'error')
                return
            }
            
            const lines = text.split(/\r?\n/)
            const parsed: ParsedLogLine[] = []
            
            lines.forEach((line) => {
                const item = parseLogLine(line)
                if (item) {
                    parsed.push(item)
                }
            })
            
            setLogLines(parsed)
            showToast(`Đã import thành công ${parsed.length} dòng log.`, 'success')
        }
        
        reader.onerror = () => {
            showToast('Lỗi khi đọc file.', 'error')
        }
        
        reader.readAsText(file, 'utf-8')
    }

    const filteredLines = useMemo(() => {
        const startSecs = parseTimeToSeconds(filterTimeStart)
        const endSecs = parseTimeToSeconds(filterTimeEnd)

        return logLines.filter((line) => {
            if (filterName.trim() && !line.machineName.toLowerCase().includes(filterName.toLowerCase())) {
                return false
            }
            if (filterIp.trim() && !line.ip.toLowerCase().includes(filterIp.toLowerCase())) {
                return false
            }
            if (filterIpwan.trim() && !line.ipwan.toLowerCase().includes(filterIpwan.toLowerCase())) {
                return false
            }
            if (filterHour.trim()) {
                // Hour filter: prefix match on timeOnly (e.g. "19" matches "19:05:40")
                const cleanHour = filterHour.trim()
                if (!line.timeOnly.startsWith(cleanHour)) {
                    return false
                }
            }
            const lineSecs = parseTimeToSeconds(line.timeOnly)
            if (lineSecs !== null) {
                if (startSecs !== null && lineSecs < startSecs) {
                    return false
                }
                if (endSecs !== null && lineSecs > endSecs) {
                    return false
                }
            }
            return true
        })
    }, [logLines, filterName, filterIp, filterIpwan, filterHour, filterTimeStart, filterTimeEnd])

    const copyFilteredLogs = () => {
        if (filteredLines.length === 0) {
            showToast('Không có log để copy.', 'error')
            return
        }
        const text = filteredLines.map(l => `${l.timestamp} - ${l.machineName} - ${l.ip} - ${l.ipwan} - ${l.rawJson}`).join('\n')
        navigator.clipboard.writeText(text)
            .then(() => showToast('Đã copy logs đã lọc.', 'success'))
            .catch(() => showToast('Không thể copy logs.', 'error'))
    }

    return (
        <>
            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                    <h2 className="page-title">Import File Debug</h2>
                    <p className="page-description">
                        Tải lên file log `.txt` từ máy của bạn (được lưu tại C:\VmixMonitor\debugger) để xem và phân tích.
                    </p>
                </div>
                <button
                    className="viewsync-outline-btn"
                    type="button"
                    onClick={() => navigate('/debug-logs')}
                    style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                >
                    &larr; Quay lại Live Logs
                </button>
            </div>

            {/* Uploader section */}
            <div className="card-light" style={{ padding: '1.5rem', marginBottom: '1.5rem', display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <div style={{ flexGrow: 1 }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569', marginBottom: '0.4rem' }}>Chọn file debug (.txt)</div>
                    <input
                        type="file"
                        accept=".txt"
                        onChange={handleFileUpload}
                        style={{ fontSize: '0.85rem', color: '#64748b' }}
                    />
                </div>
                {fileName && (
                    <div style={{ fontSize: '0.85rem', color: '#10b981', fontWeight: 600 }}>
                        Active file: {fileName} ({logLines.length} dòng)
                    </div>
                )}
            </div>

            {/* Filters */}
            <div className="card-light" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#1e293b', marginBottom: '1rem' }}>Bộ lọc log</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>Giờ (ví dụ: 19 hoặc 19:05)</label>
                        <input
                            className="table-search-input"
                            type="text"
                            placeholder="Lọc theo giờ..."
                            value={filterHour}
                            onChange={(e) => setFilterHour(e.target.value)}
                            style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '0.4rem 0.75rem', width: '100%', fontSize: '0.8rem' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>Tên thiết bị</label>
                        <input
                            className="table-search-input"
                            type="text"
                            placeholder="Lọc theo tên..."
                            value={filterName}
                            onChange={(e) => setFilterName(e.target.value)}
                            style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '0.4rem 0.75rem', width: '100%', fontSize: '0.8rem' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>IP</label>
                        <input
                            className="table-search-input"
                            type="text"
                            placeholder="Lọc theo IP..."
                            value={filterIp}
                            onChange={(e) => setFilterIp(e.target.value)}
                            style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '0.4rem 0.75rem', width: '100%', fontSize: '0.8rem' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>IPWAN</label>
                        <input
                            className="table-search-input"
                            type="text"
                            placeholder="Lọc theo IPWAN..."
                            value={filterIpwan}
                            onChange={(e) => setFilterIpwan(e.target.value)}
                            style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '0.4rem 0.75rem', width: '100%', fontSize: '0.8rem' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>Từ giờ (ví dụ: 19:00:00)</label>
                        <input
                            className="table-search-input"
                            type="text"
                            placeholder="Từ giờ (timestart)..."
                            value={filterTimeStart}
                            onChange={(e) => setFilterTimeStart(e.target.value)}
                            style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '0.4rem 0.75rem', width: '100%', fontSize: '0.8rem' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>Đến giờ (ví dụ: 20:00:00)</label>
                        <input
                            className="table-search-input"
                            type="text"
                            placeholder="Đến giờ (timeend)..."
                            value={filterTimeEnd}
                            onChange={(e) => setFilterTimeEnd(e.target.value)}
                            style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '0.4rem 0.75rem', width: '100%', fontSize: '0.8rem' }}
                        />
                    </div>
                </div>

                {logLines.length > 0 && (
                    <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                        <button
                            className="viewsync-outline-btn"
                            type="button"
                            onClick={copyFilteredLogs}
                            disabled={filteredLines.length === 0}
                            style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                        >
                            Copy Logs Đã Lọc ({filteredLines.length})
                        </button>
                    </div>
                )}
            </div>

            {/* Terminal console render */}
            <div className="card-light" style={{ padding: '1.25rem', background: '#0b0f19', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px' }}>
                <div 
                    style={{ 
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                        fontSize: '0.74rem',
                        lineHeight: '1.6',
                        color: '#a1a1aa',
                        height: '520px',
                        overflowY: 'auto',
                        paddingRight: '0.5rem'
                    }}
                >
                    {filteredLines.length === 0 ? (
                        <div style={{ color: '#52525b', textAlign: 'center', padding: '4rem 0', fontSize: '0.85rem' }}>
                            {logLines.length === 0 ? 'Hãy chọn file debug log để bắt đầu phân tích.' : 'Không có log phù hợp với bộ lọc hiện tại.'}
                        </div>
                    ) : (
                        filteredLines.map((line, index) => (
                            <div 
                                key={`imported-log-${index}`} 
                                style={{ 
                                    padding: '0.4rem 0', 
                                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                                    wordBreak: 'break-all'
                                }}
                            >
                                <span style={{ color: '#38bdf8', fontWeight: 600 }}>{line.timestamp}</span>
                                <span style={{ color: '#10b981', marginLeft: '0.5rem', fontWeight: 600 }}>{line.machineName}</span>
                                <span style={{ color: '#a78bfa', marginLeft: '0.5rem' }}>({line.ip} / {line.ipwan})</span>
                                <span style={{ color: '#94a3b8', marginLeft: '0.5rem', fontSize: '0.7rem', display: 'inline-block', whiteSpace: 'pre-wrap' }}>{line.rawJson}</span>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </>
    )
}
