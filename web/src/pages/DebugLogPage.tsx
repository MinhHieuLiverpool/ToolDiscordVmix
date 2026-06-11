import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDashboardContext } from '../hooks/useDashboardContext'
import { showToast } from '../components/ui/Toast'

export default function DebugLogPage() {
    const navigate = useNavigate()
    const { debugLogs, clearDebugLogs } = useDashboardContext()
    const [searchTerm, setSearchTerm] = useState('')

    // Fallback if context doesn't have it (e.g. before initial render or in mock environments)
    const logs = debugLogs || []

    const filteredLogs = useMemo(() => {
        if (!searchTerm.trim()) return logs
        const term = searchTerm.toLowerCase()
        return logs.filter((log) => log.toLowerCase().includes(term))
    }, [logs, searchTerm])

    const copyToClipboard = () => {
        if (filteredLogs.length === 0) {
            showToast('Không có log để copy.', 'error')
            return
        }
        const text = filteredLogs.join('\n')
        navigator.clipboard.writeText(text)
            .then(() => showToast('Đã copy logs vào clipboard.', 'success'))
            .catch(() => showToast('Không thể copy logs.', 'error'))
    }

    return (
        <>
            <div className="page-header">
                <h2 className="page-title">Debug Log</h2>
                <p className="page-description">
                    Theo dõi tất cả các thông số phản hồi thời gian thực từ các máy qua kết nối WebSocket.
                </p>
            </div>

            <div className="table-toolbar" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
                <div className="table-search-wrap" style={{ flexGrow: 1, minWidth: '250px' }}>
                    <svg className="table-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                        className="table-search-input"
                        type="text"
                        placeholder="Lọc log theo tên máy, IP, thông số..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    <button
                        className="viewsync-primary-btn"
                        type="button"
                        onClick={() => navigate('/debug-logs/import')}
                        style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                    >
                        Import File Debug
                    </button>
                    <button
                        className="viewsync-outline-btn"
                        type="button"
                        onClick={copyToClipboard}
                        disabled={filteredLogs.length === 0}
                        style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                    >
                        Copy Logs ({filteredLogs.length})
                    </button>
                    <button
                        className="viewsync-outline-btn"
                        type="button"
                        onClick={clearDebugLogs}
                        disabled={logs.length === 0}
                        style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', borderColor: 'rgba(239, 68, 68, 0.4)', color: '#ef4444' }}
                    >
                        Xóa Logs
                    </button>
                </div>
            </div>

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
                    {filteredLogs.length === 0 ? (
                        <div style={{ color: '#52525b', textAlign: 'center', padding: '4rem 0', fontSize: '0.85rem' }}>
                            {searchTerm ? 'Không tìm thấy log phù hợp.' : 'Chưa có log debug nào được ghi nhận.'}
                        </div>
                    ) : (
                        filteredLogs.map((log, index) => {
                            // Find position of the timestamp bracket ending
                            const headerEndIndex = log.indexOf(' ]')
                            const prefix = log.slice(0, headerEndIndex + 2) // [ HH:MM:SS - DD/MM/YYYY ]
                            
                            // Find details
                            const rest = log.slice(headerEndIndex + 2)
                            const parts = rest.split(' - ')
                            
                            if (parts.length >= 4) {
                                const machineName = parts[1]
                                const ip = parts[2]
                                const ipwan = parts[3]
                                const restData = parts.slice(4).join(' - ')
                                
                                return (
                                    <div 
                                        key={`log-${index}`} 
                                        style={{ 
                                            padding: '0.4rem 0', 
                                            borderBottom: '1px solid rgba(255,255,255,0.03)',
                                            wordBreak: 'break-all'
                                        }}
                                    >
                                        <span style={{ color: '#38bdf8', fontWeight: 600 }}>{prefix}</span>
                                        <span style={{ color: '#10b981', marginLeft: '0.5rem', fontWeight: 600 }}>{machineName}</span>
                                        <span style={{ color: '#a78bfa', marginLeft: '0.5rem' }}>({ip} / {ipwan})</span>
                                        <span style={{ color: '#94a3b8', marginLeft: '0.5rem', fontSize: '0.7rem', display: 'inline-block', whiteSpace: 'pre-wrap' }}>{restData}</span>
                                    </div>
                                )
                            }
                            
                            return (
                                <div 
                                    key={`log-${index}`} 
                                    style={{ 
                                        padding: '0.4rem 0', 
                                        borderBottom: '1px solid rgba(255,255,255,0.03)',
                                        wordBreak: 'break-all'
                                    }}
                                >
                                    {log}
                                </div>
                            )
                        })
                    )}
                </div>
            </div>
        </>
    )
}
