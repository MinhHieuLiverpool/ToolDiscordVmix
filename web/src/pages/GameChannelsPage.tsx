import { useState, useMemo, useEffect } from 'react'
import { useDashboardContext } from '../hooks/useDashboardContext'
import { saveGameSelected, deleteGameSelected, toggleVisibleStatus, toggleMachineVisibility } from '../services/api'
import { showToast } from '../components/ui/Toast'
import Dialog from '../components/ui/Dialog'
import axios from 'axios'

export default function GameChannelsPage() {
    const { allRows, gameAssignments, loadAssignments } = useDashboardContext()
    
    const [loading, setLoading] = useState(false)
    const [mobileDevices, setMobileDevices] = useState<string[]>([])

    useEffect(() => {
        axios.get('https://mobile-monitor.onrender.com/api/mobile-logs?limit=100')
            .then(res => {
                if (res.data && res.data.status === 'success') {
                    const rawData = res.data.data || []
                    const names = rawData.map((item: any) => item.name_device || item.deviceName || item.deviceId).filter(Boolean)
                    setMobileDevices(Array.from(new Set(names)).sort() as string[])
                }
            })
            .catch(err => {
                console.error('Error fetching mobile devices:', err)
            })
    }, [])

    // Modal state
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [showEditModal, setShowEditModal] = useState(false)
    const [editingGame, setEditingGame] = useState<string | null>(null)

    // Form inputs state
    const [gameName, setGameName] = useState('')
    const [selectedMachines, setSelectedMachines] = useState<string[]>([])

    // List of unique machine names from backend logs
    const allMachineNames = useMemo(() => {
        const names = allRows.map(r => r.data.name).filter(Boolean)
        return Array.from(new Set(names)).sort()
    }, [allRows])

    // Toggle machine selection for checklist
    const handleToggleMachineSelection = (name: string) => {
        setSelectedMachines(prev =>
            prev.includes(name) ? prev.filter(m => m !== name) : [...prev, name]
        )
    }

    const handleSelectAll = () => {
        setSelectedMachines([...allMachineNames, ...mobileDevices])
    }

    const handleDeselectAll = () => {
        setSelectedMachines([])
    }

    // Handlers
    const handleCreateChannel = async (e: React.FormEvent) => {
        e.preventDefault()
        const trimmedName = gameName.trim()
        if (!trimmedName) {
            showToast('Vui lòng nhập tên kênh.', 'warning')
            return
        }

        // Check duplicate name
        const exists = gameAssignments.some(a => a.game.toLowerCase() === trimmedName.toLowerCase())
        if (exists) {
            showToast('Tên kênh này đã tồn tại.', 'warning')
            return
        }

        try {
            setLoading(true)
            const res = await saveGameSelected(trimmedName, selectedMachines)
            if (res.success) {
                showToast('Tạo kênh mới thành công!', 'success')
                setShowCreateModal(false)
                setGameName('')
                setSelectedMachines([])
                await loadAssignments()
            } else {
                showToast(res.message || 'Lưu kênh thất bại.', 'error')
            }
        } catch (err: any) {
            console.error(err)
            showToast('Lỗi khi tạo kênh game.', 'error')
        } finally {
            setLoading(false)
        }
    }

    const handleOpenEdit = (game: string, machines: string[]) => {
        setEditingGame(game)
        setGameName(game)
        setSelectedMachines(machines || [])
        setShowEditModal(true)
    }

    const handleEditChannel = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!editingGame) return

        try {
            setLoading(true)
            const res = await saveGameSelected(editingGame, selectedMachines)
            if (res.success) {
                showToast('Cập nhật kênh thành công!', 'success')
                setShowEditModal(false)
                setEditingGame(null)
                setGameName('')
                setSelectedMachines([])
                await loadAssignments()
            } else {
                showToast(res.message || 'Cập nhật kênh thất bại.', 'error')
            }
        } catch (err) {
            console.error(err)
            showToast('Lỗi khi cập nhật kênh game.', 'error')
        } finally {
            setLoading(false)
        }
    }

    const handleDeleteChannel = async (game: string) => {
        if (!window.confirm(`Bạn có chắc muốn xóa kênh "${game}" không?`)) {
            return
        }

        try {
            setLoading(true)
            const res = await deleteGameSelected(game)
            if (res.success) {
                showToast(`Đã xóa kênh "${game}" thành công.`, 'success')
                await loadAssignments()
            } else {
                showToast(res.message || 'Xóa kênh thất bại.', 'error')
            }
        } catch (err) {
            console.error(err)
            showToast('Lỗi khi xóa kênh game.', 'error')
        } finally {
            setLoading(false)
        }
    }

    const handleToggleVisible = async (game: string, currentStatus: string) => {
        const newStatus = currentStatus === 'ON' ? 'OFF' : 'ON'
        try {
            const res = await toggleVisibleStatus(game, newStatus)
            if (res.success) {
                showToast(`Kênh "${game}" đã ${newStatus === 'ON' ? 'hiển thị' : 'ẩn'}.`, 'success')
                await loadAssignments()
            } else {
                showToast(res.message || 'Lỗi cập nhật trạng thái.', 'error')
            }
        } catch (err) {
            console.error(err)
            showToast('Lỗi khi cập nhật trạng thái hiển thị.', 'error')
        }
    }

    const handleToggleMachine = async (game: string, machine: string, isCurrentlyHidden: boolean) => {
        try {
            const res = await toggleMachineVisibility(game, machine, !isCurrentlyHidden)
            if (res.success) {
                showToast(`Máy "${machine}" đã ${!isCurrentlyHidden ? 'ẩn' : 'hiện'} trong kênh "${game}".`, 'success')
                await loadAssignments()
            } else {
                showToast(res.message || 'Lỗi cập nhật.', 'error')
            }
        } catch (err) {
            console.error(err)
            showToast('Lỗi khi cập nhật trạng thái máy.', 'error')
        }
    }

    return (
        <>
            <style>{`
                .account-table-compact {
                    font-size: 0.725rem !important;
                }
                .account-table-compact th {
                    padding: 0.4rem 0.6rem !important;
                    font-size: 0.7rem !important;
                }
                .account-table-compact td {
                    padding: 0.4rem 0.6rem !important;
                }
                .account-card-title-compact {
                    font-size: 0.8rem !important;
                }
                .account-card-subtitle-compact {
                    font-size: 0.7rem !important;
                }
                .page-title-compact {
                    font-size: 1.25rem !important;
                }
                .page-description-compact {
                    font-size: 0.75rem !important;
                }
            `}</style>
            <div className="page-header" style={{ marginBottom: '1.5rem' }}>
                <h2 className="page-title page-title-compact">Quản lý Kênh</h2>
                <p className="page-description page-description-compact">Quản lý danh sách các kênh game và chỉ định máy trực thuộc mỗi kênh.</p>
            </div>

            <section className="card-light account-card">
                <div className="account-card-header">
                    <div>
                        <h3 className="account-card-title account-card-title-compact">Kênh Game</h3>
                        <p className="account-card-subtitle account-card-subtitle-compact">Danh sách các kênh game đang hoạt động trong hệ thống.</p>
                    </div>
                    <button
                        className="account-action-btn"
                        type="button"
                        onClick={() => {
                            setGameName('')
                            setSelectedMachines([])
                            setShowCreateModal(true)
                        }}
                    >
                        Thêm kênh mới
                    </button>
                </div>

                {gameAssignments.length === 0 ? (
                    <div className="account-empty">Chưa có kênh game nào được tạo. Nhấp "Thêm kênh mới" để bắt đầu.</div>
                ) : (
                    <div className="account-table-wrap">
                        <table className="account-table account-table-compact">
                            <colgroup>
                                <col style={{ width: '20%' }} />
                                <col style={{ width: '10%' }} />
                                <col style={{ width: '50%' }} />
                                <col style={{ width: '20%' }} />
                            </colgroup>
                            <thead>
                                <tr>
                                    <th>Tên Kênh</th>
                                    <th>Hiển Thị</th>
                                    <th>Các Máy Thuộc Kênh</th>
                                    <th>Hành Động</th>
                                </tr>
                            </thead>
                            <tbody>
                                {gameAssignments.map((assignment) => (
                                    <tr key={assignment.game} style={{ opacity: assignment.visible_status === 'OFF' ? 0.5 : 1, transition: 'opacity 0.2s' }}>
                                        <td>
                                            <span style={{ fontWeight: 700, color: assignment.visible_status === 'OFF' ? '#94a3b8' : '#4f46e5', fontSize: '0.8rem' }}>
                                                {assignment.game}
                                            </span>
                                        </td>
                                        <td>
                                            <button
                                                type="button"
                                                onClick={() => handleToggleVisible(assignment.game, assignment.visible_status || 'ON')}
                                                style={{
                                                    display: 'inline-flex',
                                                    alignItems: 'center',
                                                    gap: '0.35rem',
                                                    padding: '0.25rem 0.6rem',
                                                    borderRadius: '6px',
                                                    border: '1px solid',
                                                    fontSize: '0.7rem',
                                                    fontWeight: 700,
                                                    cursor: 'pointer',
                                                    transition: 'all 0.2s',
                                                    ...(assignment.visible_status === 'OFF'
                                                        ? { color: '#94a3b8', borderColor: '#e2e8f0', background: '#f8fafc' }
                                                        : { color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.4)', background: 'rgba(16, 185, 129, 0.05)' }
                                                    )
                                                }}
                                            >
                                                {assignment.visible_status === 'OFF' ? 'OFF' : 'ON'}
                                            </button>
                                        </td>
                                        <td>
                                            <div className="role-perms" style={{ flexWrap: 'wrap', gap: '0.35rem' }}>
                                                {assignment.machines && assignment.machines.length > 0 ? (
                                                    assignment.machines.map((machine) => {
                                                        const isHidden = (assignment.hidden_machines || []).includes(machine)
                                                        return (
                                                            <span
                                                                key={machine}
                                                                className="role-perm-chip"
                                                                onClick={() => handleToggleMachine(assignment.game, machine, isHidden)}
                                                                style={{
                                                                    fontSize: '9.5px',
                                                                    textTransform: 'none',
                                                                    fontWeight: 600,
                                                                    cursor: 'pointer',
                                                                    transition: 'all 0.2s',
                                                                    padding: '0.2rem 0.5rem',
                                                                    borderRadius: '6px',
                                                                    userSelect: 'none',
                                                                    ...(isHidden
                                                                        ? { background: '#ef4444', color: '#fff', border: '1px solid #dc2626' }
                                                                        : { background: 'rgba(99, 102, 241, 0.08)', color: '#4f46e5', border: '1px solid rgba(99, 102, 241, 0.15)' }
                                                                    )
                                                                }}
                                                                title={isHidden ? `Click để hiện máy "${machine}"` : `Click để ẩn máy "${machine}"`}
                                                            >
                                                                {machine}
                                                            </span>
                                                        )
                                                    })
                                                ) : (
                                                    <span style={{ color: '#94a3b8', fontStyle: 'italic', fontSize: '0.75rem' }}>
                                                        (Chưa chọn máy nào)
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                <button
                                                    type="button"
                                                    className="account-password-btn"
                                                    style={{
                                                        color: '#4f46e5',
                                                        borderColor: 'rgba(99, 102, 241, 0.4)',
                                                        background: 'rgba(99, 102, 241, 0.05)'
                                                    }}
                                                    onClick={() => handleOpenEdit(assignment.game, assignment.machines)}
                                                >
                                                    Sửa
                                                </button>
                                                <button
                                                    type="button"
                                                    className="account-password-btn"
                                                    style={{
                                                        color: '#ef4444',
                                                        borderColor: 'rgba(239, 68, 68, 0.4)',
                                                        background: 'rgba(239, 68, 68, 0.05)'
                                                    }}
                                                    onClick={() => handleDeleteChannel(assignment.game)}
                                                >
                                                    Xóa
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>

            {/* Create Channel Modal */}
            <Dialog
                open={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                title="Tạo Kênh Mới"
            >
                <form onSubmit={handleCreateChannel} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.5rem' }}>
                            Tên Kênh Mới * (Không dùng dropdown, nhập tự do)
                        </label>
                        <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                            <input
                                type="text"
                                required
                                className="table-search-input"
                                placeholder="Nhập tên kênh (ví dụ: Kênh Game A)"
                                value={gameName}
                                onChange={(e) => setGameName(e.target.value)}
                            />
                        </div>
                    </div>

                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <label style={{ flex: 1, fontSize: '0.8rem', fontWeight: 600, color: '#475569' }}>
                                Chọn các máy trực thuộc kênh này
                            </label>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button
                                    type="button"
                                    onClick={handleSelectAll}
                                    style={{
                                        fontSize: '0.7rem',
                                        background: '#f1f5f9',
                                        border: '1px solid #cbd5e1',
                                        borderRadius: '6px',
                                        padding: '0.2rem 0.5rem',
                                        cursor: 'pointer',
                                        fontWeight: 600,
                                        color: '#475569'
                                    }}
                                >
                                    Chọn tất cả
                                </button>
                                <button
                                    type="button"
                                    onClick={handleDeselectAll}
                                    style={{
                                        fontSize: '0.7rem',
                                        background: '#f1f5f9',
                                        border: '1px solid #cbd5e1',
                                        borderRadius: '6px',
                                        padding: '0.2rem 0.5rem',
                                        cursor: 'pointer',
                                        fontWeight: 600,
                                        color: '#475569'
                                    }}
                                >
                                    Bỏ chọn tất cả
                                </button>
                            </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                                    Máy tính ({allMachineNames.length})
                                </label>
                                {allMachineNames.length === 0 ? (
                                    <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', color: '#94a3b8', fontSize: '0.75rem', fontStyle: 'italic', textAlign: 'center' }}>
                                        Không tìm thấy máy tính nào.
                                    </div>
                                ) : (
                                    <div
                                        style={{
                                            display: 'grid',
                                            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                                            gap: '0.5rem',
                                            padding: '0.75rem',
                                            background: '#f8fafc',
                                            borderRadius: '10px',
                                            border: '1px solid #e2e8f0',
                                            maxHeight: '140px',
                                            overflowY: 'auto'
                                        }}
                                    >
                                        {allMachineNames.map(name => (
                                            <label
                                                key={name}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem',
                                                    cursor: 'pointer',
                                                    fontSize: '0.75rem',
                                                    color: '#334155',
                                                    userSelect: 'none',
                                                    padding: '0.2rem 0.4rem',
                                                    borderRadius: '6px',
                                                    background: selectedMachines.includes(name) ? 'rgba(99, 102, 241, 0.05)' : 'transparent'
                                                }}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selectedMachines.includes(name)}
                                                    onChange={() => handleToggleMachineSelection(name)}
                                                    style={{ accentColor: '#4f46e5', width: '14px', height: '14px', cursor: 'pointer' }}
                                                />
                                                <span style={{ fontWeight: selectedMachines.includes(name) ? 700 : 500 }}>
                                                    {name}
                                                </span>
                                            </label>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div>
                                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                                    Thiết bị Mobile ({mobileDevices.length})
                                </label>
                                {mobileDevices.length === 0 ? (
                                    <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', color: '#94a3b8', fontSize: '0.75rem', fontStyle: 'italic', textAlign: 'center' }}>
                                        Không tìm thấy thiết bị mobile nào.
                                    </div>
                                ) : (
                                    <div
                                        style={{
                                            display: 'grid',
                                            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                                            gap: '0.5rem',
                                            padding: '0.75rem',
                                            background: '#f8fafc',
                                            borderRadius: '10px',
                                            border: '1px solid #e2e8f0',
                                            maxHeight: '140px',
                                            overflowY: 'auto'
                                        }}
                                    >
                                        {mobileDevices.map(name => (
                                            <label
                                                key={name}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem',
                                                    cursor: 'pointer',
                                                    fontSize: '0.75rem',
                                                    color: '#334155',
                                                    userSelect: 'none',
                                                    padding: '0.2rem 0.4rem',
                                                    borderRadius: '6px',
                                                    background: selectedMachines.includes(name) ? 'rgba(99, 102, 241, 0.05)' : 'transparent'
                                                }}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selectedMachines.includes(name)}
                                                    onChange={() => handleToggleMachineSelection(name)}
                                                    style={{ accentColor: '#10b981', width: '14px', height: '14px', cursor: 'pointer' }}
                                                />
                                                <span style={{ fontWeight: selectedMachines.includes(name) ? 700 : 500 }}>
                                                    {name}
                                                </span>
                                            </label>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
                        <button
                            type="button"
                            className="account-password-btn"
                            onClick={() => setShowCreateModal(false)}
                            disabled={loading}
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            className="account-action-btn"
                            disabled={loading}
                        >
                            {loading ? 'Đang lưu...' : 'Lưu cấu hình'}
                        </button>
                    </div>
                </form>
            </Dialog>

            {/* Edit Channel Modal */}
            <Dialog
                open={showEditModal}
                onClose={() => {
                    setShowEditModal(false)
                    setEditingGame(null)
                }}
                title={`Chỉnh sửa kênh: ${editingGame}`}
            >
                <form onSubmit={handleEditChannel} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#64748b', marginBottom: '0.5rem' }}>
                            Tên Kênh (Không thể sửa)
                        </label>
                        <div className="table-search-wrap" style={{ maxWidth: '100%', background: '#f8fafc', color: '#64748b', boxSizing: 'border-box' }}>
                            <input
                                type="text"
                                className="table-search-input"
                                style={{ color: '#64748b', fontWeight: 700 }}
                                value={editingGame || ''}
                                disabled
                            />
                        </div>
                    </div>

                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <label style={{ flex: 1, fontSize: '0.8rem', fontWeight: 600, color: '#475569' }}>
                                Chọn các máy trực thuộc kênh này
                            </label>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button
                                    type="button"
                                    onClick={handleSelectAll}
                                    style={{
                                        fontSize: '0.7rem',
                                        background: '#f1f5f9',
                                        border: '1px solid #cbd5e1',
                                        borderRadius: '6px',
                                        padding: '0.2rem 0.5rem',
                                        cursor: 'pointer',
                                        fontWeight: 600,
                                        color: '#475569'
                                    }}
                                >
                                    Chọn tất cả
                                </button>
                                <button
                                    type="button"
                                    onClick={handleDeselectAll}
                                    style={{
                                        fontSize: '0.7rem',
                                        background: '#f1f5f9',
                                        border: '1px solid #cbd5e1',
                                        borderRadius: '6px',
                                        padding: '0.2rem 0.5rem',
                                        cursor: 'pointer',
                                        fontWeight: 600,
                                        color: '#475569'
                                    }}
                                >
                                    Bỏ chọn tất cả
                                </button>
                            </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                                    Máy tính ({allMachineNames.length})
                                </label>
                                {allMachineNames.length === 0 ? (
                                    <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', color: '#94a3b8', fontSize: '0.75rem', fontStyle: 'italic', textAlign: 'center' }}>
                                        Không tìm thấy máy tính nào.
                                    </div>
                                ) : (
                                    <div
                                        style={{
                                            display: 'grid',
                                            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                                            gap: '0.5rem',
                                            padding: '0.75rem',
                                            background: '#f8fafc',
                                            borderRadius: '10px',
                                            border: '1px solid #e2e8f0',
                                            maxHeight: '140px',
                                            overflowY: 'auto'
                                        }}
                                    >
                                        {allMachineNames.map(name => (
                                            <label
                                                key={name}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem',
                                                    cursor: 'pointer',
                                                    fontSize: '0.75rem',
                                                    color: '#334155',
                                                    userSelect: 'none',
                                                    padding: '0.2rem 0.4rem',
                                                    borderRadius: '6px',
                                                    background: selectedMachines.includes(name) ? 'rgba(99, 102, 241, 0.05)' : 'transparent'
                                                }}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selectedMachines.includes(name)}
                                                    onChange={() => handleToggleMachineSelection(name)}
                                                    style={{ accentColor: '#4f46e5', width: '14px', height: '14px', cursor: 'pointer' }}
                                                />
                                                <span style={{ fontWeight: selectedMachines.includes(name) ? 700 : 500 }}>
                                                    {name}
                                                </span>
                                            </label>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div>
                                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                                    Thiết bị Mobile ({mobileDevices.length})
                                </label>
                                {mobileDevices.length === 0 ? (
                                    <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', color: '#94a3b8', fontSize: '0.75rem', fontStyle: 'italic', textAlign: 'center' }}>
                                        Không tìm thấy thiết bị mobile nào.
                                    </div>
                                ) : (
                                    <div
                                        style={{
                                            display: 'grid',
                                            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                                            gap: '0.5rem',
                                            padding: '0.75rem',
                                            background: '#f8fafc',
                                            borderRadius: '10px',
                                            border: '1px solid #e2e8f0',
                                            maxHeight: '140px',
                                            overflowY: 'auto'
                                        }}
                                    >
                                        {mobileDevices.map(name => (
                                            <label
                                                key={name}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem',
                                                    cursor: 'pointer',
                                                    fontSize: '0.75rem',
                                                    color: '#334155',
                                                    userSelect: 'none',
                                                    padding: '0.2rem 0.4rem',
                                                    borderRadius: '6px',
                                                    background: selectedMachines.includes(name) ? 'rgba(99, 102, 241, 0.05)' : 'transparent'
                                                }}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selectedMachines.includes(name)}
                                                    onChange={() => handleToggleMachineSelection(name)}
                                                    style={{ accentColor: '#10b981', width: '14px', height: '14px', cursor: 'pointer' }}
                                                />
                                                <span style={{ fontWeight: selectedMachines.includes(name) ? 700 : 500 }}>
                                                    {name}
                                                </span>
                                            </label>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
                        <button
                            type="button"
                            className="account-password-btn"
                            onClick={() => {
                                setShowEditModal(false)
                                setEditingGame(null)
                            }}
                            disabled={loading}
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            className="account-action-btn"
                            disabled={loading}
                        >
                            {loading ? 'Đang lưu...' : 'Lưu cấu hình'}
                        </button>
                    </div>
                </form>
            </Dialog>
        </>
    )
}
