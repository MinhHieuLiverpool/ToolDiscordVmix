import { useState } from 'react'
import { toNumber } from '../types'
import {
    normalizeSrtList,
    normalizeStreamList,
    normalizeStreamKeysList,
    normalizeRecordList,
    normalizeMultiRecordList,
    updateNameEdit,
    deleteMachine,
    type BackendLogItem,
} from '../services/api'
import Dialog from './ui/Dialog'
import { renderSrtCard, renderStreamCard, renderRecordCard, renderMultiRecordCard } from './DialogHelpers'
import { hasActionPermission } from '../services/auth'
import { showToast } from './ui/Toast'


export default function MachineStatusCard({
    item,
    index,
    isEditMode = false,
}: {
    item: BackendLogItem
    index: number
    isEditMode?: boolean
}) {
    const canEditName = hasActionPermission('Tổng quan', 'edit')
    const isOn = (value: unknown): boolean => ['ONLINE', 'ON', '1', 'TRUE', 'RUNNING', 'LIVE', 'ACTIVE'].includes(String(value || '').toUpperCase())

    const srtList = normalizeSrtList(item.data.SRT)
    const streamList = normalizeStreamList(item.data.stream)
    const streamKeysList = normalizeStreamKeysList(item.data.stream_keys)
    const recordList = normalizeRecordList(item.data.List_REcord)
    const multiRecordList = normalizeMultiRecordList(item.data.ListMultiREcord || (item.data as any).ListMultiRecord)


    const appOn = Number(item.data.statusapp) === 1
    const srtOnlineCount = srtList.filter((s) => isOn(s.status)).length
    const streamActiveCount = streamList.filter((s) => isOn(s.runtime)).length

    const srtOnline = appOn || srtOnlineCount > 0
    const cpuVal = toNumber(item.data.temperature ?? item.data.cpu)
    const ramVal = toNumber(item.data.memory ?? item.data.ram)
    const gpuVal = toNumber(item.data.gpu)
    const senderVal = toNumber(item.data.sender_mbps)
    const receiverVal = toNumber(item.data.receiver_mbps)
    const cpuHigh = cpuVal !== null && cpuVal > 50
    const ramHigh = ramVal !== null && ramVal > 50
    const hasHighUsage = cpuHigh || ramHigh
    const recOn = Boolean(item.data.vmix_recording)
    const liveOn = Boolean(item.data.vmix_streaming)
    const extOn = Boolean(item.data.vmix_external)
    const multiRecOn = Boolean(item.data.vmix_multicorder || item.data.MultirecordingStatus)
    const pidVmix = String(item.data.PIDVMIX ?? '').trim() || '-'


    const timeText = (() => {
        const raw = item.timestamp || ''
        const d = new Date(raw)
        if (Number.isNaN(d.getTime())) return raw || '-'
        return d.toLocaleString('vi-VN', { hour12: false })
    })()

    const onOff = (v: boolean) => (v ? 'ON' : 'OFF')
    const fmtMbps = (value: number | null) => (value !== null ? `${value.toFixed(2)}` : '-')
    const [streamOpen, setStreamOpen] = useState(false)
    const [srtOpen, setSrtOpen] = useState(false)
    const [recordOpen, setRecordOpen] = useState(false)
    const [isEditing, setIsEditing] = useState(false)
    const [editedName, setEditedName] = useState(item.data.name_edit || '')
    const [isSaving, setIsSaving] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)


    const handleStartEdit = () => {
        setEditedName(item.data.name_edit || '')
        setIsEditing(true)
    }

    const handleCancelEdit = () => {
        setIsEditing(false)
    }

    const handleSaveEdit = async () => {
        const trimmed = editedName.trim()
        if (trimmed === (item.data.name_edit || '')) {
            setIsEditing(false)
            return
        }
        setIsSaving(true)
        try {
            const res = await updateNameEdit(item.data.name, trimmed)
            if (res.success) {
                setIsEditing(false)
            } else {
                alert(res.message || 'Lỗi khi cập nhật tên')
            }
        } catch (err: any) {
            console.error('Update name_edit error:', err)
            alert('Lỗi kết nối đến server: ' + (err.message || err))
        } finally {
            setIsSaving(false)
        }
    }

    const handleDeleteMachine = async () => {
        setIsDeleting(true)
        try {
            const res = await deleteMachine(item.data.name)
            if (res.success) {
                showToast(res.message || `Đã xóa thiết bị ${item.data.name}`, 'success')
            } else {
                showToast((res as any).error || 'Lỗi khi xóa thiết bị', 'error')
            }
        } catch (err: any) {
            console.error('Delete machine error:', err)
            showToast('Lỗi kết nối đến server: ' + (err.message || err), 'error')
        } finally {
            setIsDeleting(false)
            setShowDeleteConfirm(false)
        }
    }

    return (
        <div
            className={`glass-card card-animate machine-card ${srtOnline ? 'card-online' : 'card-offline'} ${hasHighUsage ? 'card-overload' : ''}`}
            style={{
                animationDelay: `${index * 40}ms`,
                position: 'relative',
                ...(isEditMode ? { animation: `card-shake 0.4s ease-in-out infinite alternate` } : {}),
            }}
        >
            {/* Delete button - visible in edit mode */}
            {isEditMode && (
                <button
                    type="button"
                    onClick={() => setShowDeleteConfirm(true)}
                    className="machine-card-delete-btn"
                    title={`Xóa thiết bị ${item.data.name}`}
                    style={{
                        position: 'absolute',
                        top: '-8px',
                        right: '-8px',
                        zIndex: 20,
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                        border: '2px solid rgba(255,255,255,0.3)',
                        color: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        boxShadow: '0 2px 8px rgba(239, 68, 68, 0.5)',
                        transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'scale(1.15)'
                        e.currentTarget.style.boxShadow = '0 4px 14px rgba(239, 68, 68, 0.7)'
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'scale(1)'
                        e.currentTarget.style.boxShadow = '0 2px 8px rgba(239, 68, 68, 0.5)'
                    }}
                >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            )}
            {/* Header */}
            <div className="card-header flex justify-between items-center w-full gap-2">
                {isEditing ? (
                    <div className="flex items-center gap-1.5 flex-1 min-w-0">
                        <input
                            type="text"
                            value={editedName}
                            onChange={(e) => setEditedName(e.target.value)}
                            disabled={isSaving}
                            className="bg-white text-rose-600 border border-rose-500 rounded px-2.5 py-1 text-xs font-bold uppercase w-full focus:outline-none focus:ring-2 focus:ring-rose-500/20 transition-all placeholder:text-rose-500/40"
                            placeholder="TÊN HIỂN THỊ..."
                            autoFocus
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSaveEdit()
                                if (e.key === 'Escape') handleCancelEdit()
                            }}
                        />
                        <button
                            onClick={handleSaveEdit}
                            disabled={isSaving}
                            className="text-emerald-400 hover:text-emerald-300 p-1.5 rounded-md hover:bg-emerald-500/10 disabled:opacity-50 transition-colors shrink-0"
                            title="Lưu"
                        >
                            {isSaving ? (
                                <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                            ) : (
                                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                </svg>
                            )}
                        </button>
                        <button
                            onClick={handleCancelEdit}
                            disabled={isSaving}
                            className="text-rose-400 hover:text-rose-300 p-1.5 rounded-md hover:bg-rose-500/10 disabled:opacity-50 transition-colors shrink-0"
                            title="Hủy"
                        >
                            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                ) : (
                    <div className="flex flex-col min-w-0 flex-1 group">
                        {item.data.name_edit ? (
                            <div className="flex items-center gap-1.5 h-4 mb-0.5">
                                <span className="text-[11px] font-black text-rose-600 dark:text-rose-400 uppercase tracking-wider break-all">
                                    {item.data.name_edit}
                                </span>
                                {canEditName && (
                                    <button
                                        onClick={handleStartEdit}
                                        className="opacity-0 group-hover:opacity-100 focus:opacity-100 text-gray-400 hover:text-white transition-opacity p-0.5 rounded hover:bg-white/10 shrink-0"
                                        title="Sửa tên hiển thị"
                                    >
                                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                        </svg>
                                    </button>
                                )}
                            </div>
                        ) : (
                            canEditName && (
                                <div className="flex items-center h-4 mb-0.5">
                                    <button
                                        onClick={handleStartEdit}
                                        className="opacity-0 group-hover:opacity-60 focus:opacity-60 text-slate-400 hover:text-rose-400 text-[9px] font-bold uppercase tracking-wider flex items-center gap-1 transition-all"
                                        title="Đặt tên hiển thị"
                                    >
                                        <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                        </svg>
                                        Đặt tên hiển thị
                                    </button>
                                </div>
                            )
                        )}
                        <h3 className="card-name truncate" title={item.data.name}>
                            {item.data.name || 'Unknown'}
                        </h3>
                    </div>
                )}
                <span className={`status-badge shrink-0 ${srtOnline ? 'badge-online' : 'badge-offline'}`}>
                    <span className={`status-dot ${srtOnline ? 'dot-online' : 'dot-offline'}`} />
                    {onOff(srtOnline)}
                </span>
            </div>

            {/* IP info */}
            <div className="card-info">
                <div className="info-row">
                    <span className="info-label">IP</span>
                    <span className="info-value mono">{item.data.ip || '-'}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">WAN</span>
                    <span className="info-value mono">{item.data.ipwan || '-'}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">REC | LIVE | MULTI | EXT</span>
                    <span className="info-value">{onOff(recOn)} | {onOff(liveOn)} | {onOff(multiRecOn)} | {onOff(extOn)}</span>
                </div>
            </div>

            <div className="card-divider" />

            {/* Metrics */}
            <div className="card-metrics">
                <div className={`metric-box ${cpuHigh ? 'metric-box-danger' : ''}`}>
                    <div className="metric-label metric-label-cpu">CPU</div>
                    <div className={`metric-value ${cpuHigh ? 'metric-danger' : 'metric-cpu'}`}>
                        {cpuVal !== null ? `${cpuVal.toFixed(0)}%` : '-'}
                    </div>
                </div>
                <div className={`metric-box ${ramHigh ? 'metric-box-danger' : ''}`}>
                    <div className="metric-label metric-label-ram">RAM</div>
                    <div className={`metric-value ${ramHigh ? 'metric-danger' : 'metric-ram'}`}>
                        {ramVal !== null ? `${ramVal.toFixed(0)}%` : '-'}
                    </div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">Ping</div>
                    <div className="metric-value metric-ping">{item.data.ping ?? '-'}</div>
                </div>
            </div>

            <div className="card-metrics">
                <div className="metric-box">
                    <div className="metric-label">APP</div>
                    <div className={`metric-value ${appOn ? 'metric-ping' : 'metric-warn'}`}>{onOff(appOn)}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">Timeout</div>
                    <div className="metric-value metric-cpu">{item.data.ping_timeouts ?? 0}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">Ping ISP</div>
                    <div className="metric-value metric-ping">{item.data.ping_isp ?? '-'}</div>
                </div>
            </div>

            <div className="card-metrics">
                <div className="metric-box">
                    <div className="metric-label metric-label-gpu">GPU</div>
                    <div className="metric-value metric-warn">{gpuVal !== null ? `${gpuVal.toFixed(0)}%` : '-'}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">Sender</div>
                    <div className="metric-value metric-ping">{fmtMbps(senderVal)} Mbps</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">Receiver</div>
                    <div className="metric-value metric-ping">{fmtMbps(receiverVal)} Mbps</div>
                </div>
            </div>

            <div className="card-metrics">
                <div className="metric-box">
                    <div className="metric-label">REC</div>
                    <div className={`metric-value ${recOn ? 'metric-ping' : 'metric-warn'}`}>{onOff(recOn)}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">MULTI</div>
                    <div className={`metric-value ${multiRecOn ? 'metric-ping' : 'metric-warn'}`}>{onOff(multiRecOn)}</div>
                </div>
                <div className="metric-box">
                    <div className="metric-label">LIVE</div>
                    <div className={`metric-value ${liveOn ? 'metric-ping' : 'metric-warn'}`}>{onOff(liveOn)}</div>
                </div>
            </div>

            {/* Extra info */}
            <div className="card-extra">
                <div className="info-row">
                    <span className="info-label">Resolution</span>
                    <span className="info-value">{item.data.resolution || '-'}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">PID VMIX</span>
                    <span className="info-value mono">{pidVmix}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">MAC Address</span>
                    <span className="info-value mono">{item.data.mac_address || '-'}</span>
                </div>
                <div className="info-row">
                    <span className="info-label">Network Speed</span>
                    <span className="info-value">{item.data.network_speed || '-'}</span>
                </div>
            </div>

            <div className="card-footer" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '0.25rem' }}>
                <div className="card-footer-actions">
                    <button
                        type="button"
                        className="card-footer-btn"
                        onClick={() => setSrtOpen(true)}
                        disabled={srtList.length === 0}
                    >
                        SRT ({srtOnlineCount}/{srtList.length})
                    </button>
                    <button
                        type="button"
                        className="card-footer-btn"
                        onClick={() => setRecordOpen(true)}
                        disabled={recordList.length === 0 && multiRecordList.length === 0}
                    >
                        Record ({recordList.length + multiRecordList.length})
                    </button>
                    <button
                        type="button"
                        className="card-footer-btn"
                        onClick={() => setStreamOpen(true)}
                        disabled={streamList.length === 0}
                    >
                        Stream ({streamActiveCount}/{streamList.length})
                    </button>
                </div>
                <span className="card-timestamp" style={{ textAlign: 'right', display: 'block', marginTop: '0.15rem' }}>{timeText}</span>
            </div>

            <Dialog
                open={srtOpen}
                onClose={() => setSrtOpen(false)}
                title={`SRT · ${item.data.name || 'Unknown'}`}
            >
                {srtList.length > 0 ? (
                    <div className="dialog-detail-grid">
                        {srtList.map(renderSrtCard)}
                    </div>
                ) : (
                    <div className="dialog-empty-state">Không có dữ liệu SRT.</div>
                )}
            </Dialog>

            <Dialog
                open={streamOpen}
                onClose={() => setStreamOpen(false)}
                title={`Stream · ${item.data.name || 'Unknown'}`}
            >
                {streamList.length > 0 ? (
                    <div className="dialog-detail-grid">
                        {streamList.map((stream, idx) => {
                            const matchedKey = streamKeysList.find((sk) => sk.stream === stream.stream)
                            return renderStreamCard(stream, idx, matchedKey)
                        })}
                    </div>
                ) : (
                    <div className="dialog-empty-state">Không có dữ liệu stream.</div>
                )}
            </Dialog>

            <Dialog
                open={recordOpen}
                onClose={() => setRecordOpen(false)}
                title={`Record & MultiCorder · ${item.data.name || 'Unknown'}`}
            >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <div>
                        <h4 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.5rem', textTransform: 'uppercase', color: '#94a3b8', borderBottom: '1px solid rgba(148, 163, 184, 0.1)', paddingBottom: '0.25rem' }}>
                            Standard Record ({recordList.length})
                        </h4>
                        {recordList.length > 0 ? (
                            <div className="dialog-detail-grid">
                                {recordList.map(renderRecordCard)}
                            </div>
                        ) : (
                            <div className="dialog-empty-state">Không có dữ liệu Standard Record.</div>
                        )}
                    </div>
                    <div>
                        <h4 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.5rem', textTransform: 'uppercase', color: '#94a3b8', borderBottom: '1px solid rgba(148, 163, 184, 0.1)', paddingBottom: '0.25rem' }}>
                            MultiCorder ({multiRecordList.length})
                        </h4>
                        {multiRecordList.length > 0 ? (
                            <div className="dialog-detail-grid">
                                {multiRecordList.map(renderMultiRecordCard)}
                            </div>
                        ) : (
                            <div className="dialog-empty-state">Không có dữ liệu MultiCorder.</div>
                        )}
                    </div>
                </div>
            </Dialog>

            {/* Delete confirmation dialog */}
            <Dialog
                open={showDeleteConfirm}
                onClose={() => setShowDeleteConfirm(false)}
                title="Xác nhận xóa thiết bị"
            >
                <div className="flex flex-col gap-4 text-slate-800 dark:text-slate-100">
                    <div className="text-sm">
                        <p className="mb-2">
                            Bạn có chắc chắn muốn xóa thiết bị <strong className="text-red-500">{item.data.name_edit || item.data.name}</strong>?
                        </p>
                        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-xs text-red-400">
                            <p className="font-bold mb-1">⚠ Hành động này sẽ:</p>
                            <ul className="list-disc list-inside space-y-0.5">
                                <li>Xóa toàn bộ logs của thiết bị</li>
                                <li>Xóa thống kê CPU/RAM/GPU</li>
                                <li>Xóa debug logs liên quan</li>
                                <li>Loại trừ khỏi tất cả kênh game</li>
                            </ul>
                            <p className="mt-2 font-bold">Không thể hoàn tác!</p>
                        </div>
                    </div>
                    <div className="flex justify-end gap-2">
                        <button
                            onClick={() => setShowDeleteConfirm(false)}
                            disabled={isDeleting}
                            className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
                        >
                            Hủy
                        </button>
                        <button
                            onClick={handleDeleteMachine}
                            disabled={isDeleting}
                            className="bg-red-600 hover:bg-red-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
                        >
                            {isDeleting ? (
                                <>
                                    <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Đang xóa...
                                </>
                            ) : (
                                <>
                                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                    Xóa thiết bị
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </Dialog>

        </div>
    )
}
