import { useMemo, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { showToast } from '../components/ui/Toast'
import Dialog from '../components/ui/Dialog'
import { fetchDbDebugLogs } from '../services/api'
import { useDashboardContext } from '../hooks/useDashboardContext'

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
    const location = useLocation()
    const state = location.state as { logs?: ParsedLogLine[]; fileName?: string } | null
    const { gameAssignments } = useDashboardContext()
    const [logLines, setLogLines] = useState<ParsedLogLine[]>(state?.logs || [])
    const [fileName, setFileName] = useState(state?.fileName || '')
    const [loadingDb, setLoadingDb] = useState(false)
    const [filterGame, setFilterGame] = useState('__all__')

    const handleLoadDbLogs = async () => {
        try {
            setLoadingDb(true)
            const dbDocs = await fetchDbDebugLogs()
            if (!dbDocs || dbDocs.length === 0) {
                showToast('Không có dữ liệu log debug trong database.', 'warning')
                return
            }

            const parsed = dbDocs.map((doc: any) => {
                const d = new Date(doc.debug_logged_at || doc.timestamp)
                const hh = String(d.getHours()).padStart(2, '0')
                const mm = String(d.getMinutes()).padStart(2, '0')
                const ss = String(d.getSeconds()).padStart(2, '0')
                const day = String(d.getDate()).padStart(2, '0')
                const month = String(d.getMonth() + 1).padStart(2, '0')
                const year = d.getFullYear()
                
                const formattedTimestamp = `[ ${hh}:${mm}:${ss} - ${day}/${month}/${year} ]`
                const timeOnly = `${hh}:${mm}:${ss}`
                const dateOnly = `${day}/${month}/${year}`
                
                // Clean document from metadata for rawJson
                const { _id, debug_logged_at, ...rawDoc } = doc
                
                return {
                    timestamp: formattedTimestamp,
                    timeOnly,
                    dateOnly,
                    machineName: doc.name || 'Unknown',
                    ip: doc.ip || '',
                    ipwan: doc.ipwan || '',
                    rawJson: JSON.stringify(rawDoc)
                }
            })

            setLogLines(parsed)
            setFileName('Database Logs')
            showToast(`Đã tải thành công ${parsed.length} dòng log từ database.`, 'success')
        } catch (err) {
            console.error(err)
            showToast('Lỗi khi tải log từ database.', 'error')
        } finally {
            setLoadingDb(false)
        }
    }
    
    // Filters
    const [filterName, setFilterName] = useState('')
    const [filterIp, setFilterIp] = useState('')
    const [filterIpwan, setFilterIpwan] = useState('')
    const [filterHour, setFilterHour] = useState('') // e.g. "19" or "19:05"
    const [filterTimeStart, setFilterTimeStart] = useState('') // e.g. "12:00:00" or "12:00"
    const [filterTimeEnd, setFilterTimeEnd] = useState('') // e.g. "13:30:00" or "13:30"
    const initialFieldFilters: Record<string, boolean> = {
        name: false,
        ip: false,
        ipwan: false,
        statusapp: false,
        ping: false,
        ping_timeouts: false,
        temperature: false,
        memory: false,
        gpu: false,
        sender_mbps: false,
        receiver_mbps: false,
        mac_address: false,
        network_speed: false,
        vmixsend: false,
        vmixreceive: false,
        PIDVMIX: false,
        vmix_recording: false,
        vmix_streaming: false,
        vmix_external: false,
        resolution: false,
        SRT: false,
        'SRT.nameSRT': false,
        'SRT.port': false,
        'SRT.quality': false,
        'SRT.status': false,
        'SRT.type': false,
        'SRT.hostname': false,
        'SRT.stream_id': false,
        'SRT.title': false,
        stream: false,
        stream_keys: false,
        stream_quality: false,
        generated_at: false,
        config_source: false,
        config_error: false,
        log_error: false,
        streams: false,
        ffmpeg: false,
    }

    const [isFilterModalOpen, setIsFilterModalOpen] = useState(false)
    const [activeFields, setActiveFields] = useState<Record<string, boolean>>(initialFieldFilters)
    const [draftFields, setDraftFields] = useState<Record<string, boolean>>(initialFieldFilters)

    const openFilterModal = () => {
        setDraftFields({ ...activeFields })
        setIsFilterModalOpen(true)
    }

    const applyFilters = () => {
        setActiveFields({ ...draftFields })
        setIsFilterModalOpen(false)
    }

    const clearAdvancedFilters = () => {
        setActiveFields(initialFieldFilters)
    }

    const hasActiveFilters = useMemo(() => {
        return Object.values(activeFields).some(v => v)
    }, [activeFields])

    const filterJson = (rawJsonStr: string, fields: Record<string, boolean>): string => {
        try {
            const hasAnyActive = Object.values(fields).some(v => v)
            if (!hasAnyActive) return rawJsonStr

            const obj = JSON.parse(rawJsonStr)
            const filtered: any = {}

            Object.entries(fields).forEach(([fieldPath, isChecked]) => {
                if (!isChecked) return

                if (fieldPath.startsWith('SRT.')) {
                    const sub = fieldPath.split('.')[1]
                    if (Array.isArray(obj.SRT)) {
                        if (!filtered.SRT) {
                            filtered.SRT = obj.SRT.map(() => ({}))
                        }
                        obj.SRT.forEach((srtItem: any, index: number) => {
                            if (srtItem && srtItem[sub] !== undefined) {
                                filtered.SRT[index][sub] = srtItem[sub]
                            }
                        })
                    }
                    return
                }

                if (obj[fieldPath] !== undefined) {
                    if (fieldPath === 'SRT') {
                        if (!Object.keys(fields).some(k => k.startsWith('SRT.') && fields[k])) {
                            filtered.SRT = obj.SRT
                        }
                    } else {
                        filtered[fieldPath] = obj[fieldPath]
                    }
                }
            })

            return JSON.stringify(filtered)
        } catch (e) {
            return rawJsonStr
        }
    }



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

        // Find machines list for selected game (excluding hidden)
        const assignment = filterGame !== '__all__'
            ? gameAssignments?.find(g => g.game === filterGame)
            : null
        const assignedMachines = assignment?.machines || []
        const hiddenMachines = assignment?.hidden_machines || []
        const visibleMachines = assignedMachines.filter(m => !hiddenMachines.includes(m))

        return logLines.filter((line) => {
            if (filterGame !== '__all__') {
                const isMatch = visibleMachines.some(
                    m => m.toLowerCase() === line.machineName.toLowerCase()
                )
                if (!isMatch) return false
            }
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
    }, [logLines, filterName, filterIp, filterIpwan, filterHour, filterTimeStart, filterTimeEnd, filterGame, gameAssignments])

    const copyFilteredLogs = () => {
        if (filteredLines.length === 0) {
            showToast('Không có log để copy.', 'error')
            return
        }
        const text = filteredLines.map(l => {
            const filteredJson = filterJson(l.rawJson, activeFields)
            return `${l.timestamp} - ${l.machineName} - ${l.ip} - ${l.ipwan} - ${filteredJson}`
        }).join('\n')
        navigator.clipboard.writeText(text)
            .then(() => showToast('Đã copy logs đã lọc.', 'success'))
            .catch(() => showToast('Không thể copy logs.', 'error'))
    }

    const handleViewCharts = () => {
        if (filteredLines.length === 0) {
            showToast('Không có log để vẽ biểu đồ.', 'error')
            return
        }

        const chartData = filteredLines.map(line => {
            try {
                const obj = JSON.parse(line.rawJson)
                const minimalObj: any = {}
                if (obj.cpu !== undefined) minimalObj.cpu = obj.cpu
                if (obj.temperature !== undefined) minimalObj.temperature = obj.temperature
                if (obj.ram !== undefined) minimalObj.ram = obj.ram
                if (obj.memory !== undefined) minimalObj.memory = obj.memory
                if (obj.gpu !== undefined) minimalObj.gpu = obj.gpu
                if (obj.ping !== undefined) minimalObj.ping = obj.ping
                if (obj.sender_mbps !== undefined) minimalObj.sender_mbps = obj.sender_mbps
                if (obj.receiver_mbps !== undefined) minimalObj.receiver_mbps = obj.receiver_mbps
                
                return {
                    machineName: line.machineName,
                    timeOnly: line.timeOnly,
                    rawJson: JSON.stringify(minimalObj)
                }
            } catch (e) {
                return {
                    machineName: line.machineName,
                    timeOnly: line.timeOnly,
                    rawJson: '{}'
                }
            }
        })

        sessionStorage.setItem('debug_chart_data', JSON.stringify({ logs: chartData, fileName }))
        window.open('/debug-logs/import/charts', '_blank')
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
            <div className="card-light" style={{ padding: '1.5rem', marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap', flexGrow: 1 }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569' }}>Chọn file debug (.txt)</div>
                        <label
                            htmlFor="debug-file-upload"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                padding: '0.55rem 1rem',
                                border: '1.5px dashed #cbd5e1',
                                borderRadius: '10px',
                                cursor: 'pointer',
                                backgroundColor: '#f8fafc',
                                transition: 'all 0.25s ease',
                                width: 'fit-content',
                                minWidth: '320px',
                                boxSizing: 'border-box'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = '#6366f1';
                                e.currentTarget.style.backgroundColor = '#f5f3ff';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = '#cbd5e1';
                                e.currentTarget.style.backgroundColor = '#f8fafc';
                            }}
                        >
                            <svg style={{ width: '18px', height: '18px', color: '#6366f1', flexShrink: 0 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                <polyline points="17 8 12 3 7 8" />
                                <line x1="12" y1="3" x2="12" y2="15" />
                            </svg>
                            <span style={{ fontSize: '0.8rem', fontWeight: 500, color: '#475569', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '240px' }}>
                                {fileName && fileName !== 'Database Logs' ? fileName : 'Chọn tệp debug .txt từ máy...'}
                            </span>
                            <input
                                id="debug-file-upload"
                                type="file"
                                accept=".txt"
                                onChange={handleFileUpload}
                                style={{ display: 'none' }}
                            />
                        </label>
                    </div>

                    {fileName && (
                        <div style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: '0.5rem', 
                            padding: '0.5rem 0.85rem', 
                            background: '#ecfdf5', 
                            border: '1px solid #a7f3d0', 
                            borderRadius: '8px',
                            color: '#065f46',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            marginTop: '1.25rem'
                        }}>
                            <span style={{ display: 'inline-block', width: '8px', height: '8px', background: '#10b981', borderRadius: '50%' }}></span>
                            Đang xem: <span style={{ textDecoration: 'underline' }}>{fileName}</span> ({logLines.length} dòng)
                        </div>
                    )}
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    {logLines.length > 0 && (
                        <button
                            className="viewsync-primary-btn"
                            type="button"
                            onClick={handleViewCharts}
                            style={{ 
                                padding: '0.55rem 1.25rem', 
                                fontSize: '0.85rem', 
                                height: '40px',
                                backgroundColor: '#8b5cf6',
                                borderColor: '#8b5cf6',
                                color: '#ffffff',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.4rem',
                                transition: 'all 0.2s ease'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.backgroundColor = '#7c3aed';
                                e.currentTarget.style.borderColor = '#7c3aed';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.backgroundColor = '#8b5cf6';
                                e.currentTarget.style.borderColor = '#8b5cf6';
                            }}
                        >
                            <span>📊</span> Xem Biểu Đồ Phân Tích
                        </button>
                    )}
                    <button
                        className="viewsync-primary-btn"
                        type="button"
                        onClick={handleLoadDbLogs}
                        disabled={loadingDb}
                        style={{ padding: '0.55rem 1.25rem', fontSize: '0.85rem', height: '40px' }}
                    >
                        {loadingDb ? 'Đang tải...' : 'Tải Logs từ Database'}
                    </button>
                </div>
            </div>

            {/* Filters */}
            <div className="card-light" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#1e293b', marginBottom: '1rem' }}>Bộ lọc log</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>Kênh Game / Thiết bị</label>
                        <select
                            value={filterGame}
                            onChange={(e) => setFilterGame(e.target.value)}
                            style={{ 
                                border: '1px solid #e2e8f0', 
                                borderRadius: '8px', 
                                padding: '0.4rem 0.75rem', 
                                width: '100%', 
                                fontSize: '0.8rem',
                                height: '34px',
                                backgroundColor: '#fff',
                                color: '#1e293b',
                                outline: 'none',
                                cursor: 'pointer'
                            }}
                        >
                            <option value="__all__">Tất cả Kênh</option>
                            {gameAssignments?.filter((a: any) => a.visible_status !== 'OFF').map((assignment: any) => (
                                <option key={assignment.game} value={assignment.game}>
                                    {assignment.game}
                                </option>
                            ))}
                        </select>
                    </div>
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

                <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        <button
                            className="viewsync-primary-btn"
                            type="button"
                            onClick={openFilterModal}
                            style={{ padding: '0.45rem 1rem', fontSize: '0.85rem' }}
                        >
                            ⚙ Lọc Nâng Cao SRT & Máy
                        </button>
                        {hasActiveFilters && (
                            <button
                                className="viewsync-outline-btn"
                                type="button"
                                onClick={clearAdvancedFilters}
                                style={{ padding: '0.45rem 1rem', fontSize: '0.85rem', borderColor: 'rgba(239, 68, 68, 0.4)', color: '#ef4444' }}
                            >
                                Xóa bộ lọc nâng cao
                            </button>
                        )}
                        {hasActiveFilters && (
                            <span style={{ fontSize: '0.8rem', color: '#10b981', fontWeight: 600 }}>
                                Đã lọc: {Object.entries(activeFields)
                                    .filter(([_, isChecked]) => isChecked)
                                    .map(([fieldName]) => fieldName)
                                    .join(', ')}
                            </span>
                        )}
                    </div>
                    {logLines.length > 0 && (
                        <button
                            className="viewsync-outline-btn"
                            type="button"
                            onClick={copyFilteredLogs}
                            disabled={filteredLines.length === 0}
                            style={{ padding: '0.45rem 1.25rem', fontSize: '0.85rem' }}
                        >
                            Copy Logs Đã Lọc
                        </button>
                    )}
                </div>
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
                                <span style={{ color: '#94a3b8', marginLeft: '0.5rem', fontSize: '0.7rem', display: 'inline-block', whiteSpace: 'pre-wrap' }}>
                                    {filterJson(line.rawJson, activeFields)}
                                </span>
                            </div>
                        ))
                    )}
                </div>
            </div>

            <Dialog
                open={isFilterModalOpen}
                onClose={() => setIsFilterModalOpen(false)}
                title="Chọn các trường dữ liệu cần trích xuất (MongoDB Fields)"
            >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', maxHeight: '450px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                    {[
                        {
                            title: "Thông số Thiết bị (Device Info)",
                            color: "#6366f1",
                            fields: [
                                { id: "name", label: "name" },
                                { id: "ip", label: "ip" },
                                { id: "ipwan", label: "ipwan" },
                                { id: "statusapp", label: "statusapp" },
                                { id: "mac_address", label: "mac_address" },
                                { id: "network_speed", label: "network_speed" },
                                { id: "PIDVMIX", label: "PIDVMIX" },
                            ]
                        },
                        {
                            title: "Hiệu năng PC (PC Performance)",
                            color: "#3b82f6",
                            fields: [
                                { id: "ping", label: "ping" },
                                { id: "ping_timeouts", label: "ping_timeouts" },
                                { id: "temperature", label: "temperature" },
                                { id: "memory", label: "memory" },
                                { id: "gpu", label: "gpu" },
                            ]
                        },
                        {
                            title: "Thông số vMix (vMix Status)",
                            color: "#10b981",
                            fields: [
                                { id: "vmix_recording", label: "vmix_recording" },
                                { id: "vmix_streaming", label: "vmix_streaming" },
                                { id: "vmix_external", label: "vmix_external" },
                                { id: "resolution", label: "resolution" },
                                { id: "vmixsend", label: "vmixsend" },
                                { id: "vmixreceive", label: "vmixreceive" },
                            ]
                        },
                        {
                            title: "Luồng & Kết nối (SRT, Streams, Ffmpeg)",
                            color: "#0ea5e9",
                            fields: [
                                { id: "SRT", label: "SRT (Full Array)" },
                                { id: "SRT.title", label: "SRT.title" },
                                { id: "SRT.nameSRT", label: "SRT.nameSRT" },
                                { id: "SRT.port", label: "SRT.port" },
                                { id: "SRT.quality", label: "SRT.quality" },
                                { id: "SRT.status", label: "SRT.status" },
                                { id: "SRT.type", label: "SRT.type" },
                                { id: "SRT.hostname", label: "SRT.hostname" },
                                { id: "SRT.stream_id", label: "SRT.stream_id" },
                                { id: "stream", label: "stream" },
                                { id: "stream_keys", label: "stream_keys" },
                                { id: "stream_quality", label: "stream_quality" },
                                { id: "streams", label: "streams" },
                                { id: "ffmpeg", label: "ffmpeg" },
                            ]
                        },
                        {
                            title: "Metadata & Diagnostics",
                            color: "#8b5cf6",
                            fields: [
                                { id: "generated_at", label: "generated_at" },
                                { id: "config_source", label: "config_source" },
                                { id: "config_error", label: "config_error" },
                                { id: "log_error", label: "log_error" },
                            ]
                        }
                    ].map((group) => (
                        <div key={group.title} style={{ borderLeft: `3px solid ${group.color}`, paddingLeft: '0.75rem', marginBottom: '0.5rem' }}>
                            <h4 style={{ fontSize: '0.82rem', fontWeight: 800, color: '#0f172a', marginBottom: '0.6rem' }}>
                                {group.title}
                            </h4>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '0.5rem' }}>
                                {group.fields.map((f) => {
                                    const isChecked = draftFields[f.id] || false
                                    return (
                                        <label 
                                            key={`chk-field-${f.id}`} 
                                            style={{ 
                                                display: 'flex', 
                                                alignItems: 'center', 
                                                gap: '0.45rem', 
                                                fontSize: '0.78rem', 
                                                color: isChecked ? '#6366f1' : '#334155', 
                                                cursor: 'pointer',
                                                fontWeight: isChecked ? 600 : 500,
                                                transition: 'color 0.15s ease'
                                            }}
                                        >
                                            <input 
                                                type="checkbox" 
                                                checked={isChecked} 
                                                onChange={(e) => setDraftFields(prev => ({ ...prev, [f.id]: e.target.checked }))}
                                                style={{ width: '14px', height: '14px', accentColor: '#6366f1', cursor: 'pointer' }}
                                            />
                                            <span>{f.label}</span>
                                        </label>
                                    )
                                })}
                            </div>
                        </div>
                    ))}
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem', borderTop: '1px solid rgba(0,0,0,0.1)', paddingTop: '1rem' }}>
                    <button
                        className="viewsync-outline-btn"
                        type="button"
                        onClick={() => setIsFilterModalOpen(false)}
                        style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
                    >
                        Hủy
                    </button>
                    <button
                        className="viewsync-primary-btn"
                        type="button"
                        onClick={applyFilters}
                        style={{ padding: '0.4rem 1.25rem', fontSize: '0.85rem' }}
                    >
                        OK
                    </button>
                </div>
            </Dialog>
        </>
    )
}
