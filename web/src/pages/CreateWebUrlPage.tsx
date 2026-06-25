import { useState, useEffect, useMemo } from 'react'
import { useDashboardContext } from '../hooks/useDashboardContext'
import { 
    createSharedWebConfig, 
    updateSharedWebConfig,
    listSharedWebConfigs, 
    deleteSharedWebConfig, 
    type SharedWebConfig 
} from '../services/api'
import { showToast } from '../components/ui/Toast'
import Dialog from '../components/ui/Dialog'

const AVAILABLE_FEATURES = [
    { id: 'Tổng quan', label: 'Tổng quan' },
    { id: 'SRT', label: 'SRT' },
    { id: 'Thông số Stream', label: 'Thông số Stream' },
    { id: 'URL & Key', label: 'URL & Key' },
    { id: 'FFmpeg', label: 'FFmpeg' },
    { id: 'Thống kê', label: 'Thống kê' },
    { id: 'Vmix Monitor', label: 'Vmix Monitor' },
    { id: 'Mobile Monitor', label: 'Mobile Monitor' },
    { id: 'Speedtest', label: 'Speedtest' },
    { id: 'Debug Log', label: 'Debug Log' },
]

const AVAILABLE_GAMES = [
    { id: '__all__', label: 'Tất cả Game' },
    { id: 'Liên Quân Mobile', label: 'Liên Quân Mobile' },
    { id: 'Free Fire', label: 'Free Fire' },
    { id: 'FC Online', label: 'FC Online' },
    { id: 'FC Mobile', label: 'FC Mobile' },
    { id: 'Delta Force', label: 'Delta Force' },
]

export default function CreateWebUrlPage() {
    const { allRows } = useDashboardContext()
    
    // Config Dialog states
    const [isDialogOpen, setIsDialogOpen] = useState(false)
    const [editingUuid, setEditingUuid] = useState<string | null>(null)
    const [selectedFeatures, setSelectedFeatures] = useState<string[]>(['Tổng quan'])
    const [selectedMachines, setSelectedMachines] = useState<string[]>([])
    const [selectedGame, setSelectedGame] = useState('__all__')
    const [saving, setSaving] = useState(false)
    const [generatedUrl, setGeneratedUrl] = useState('')
    
    // Shared links list state
    const [links, setLinks] = useState<SharedWebConfig[]>([])
    const [loadingLinks, setLoadingLinks] = useState(false)

    // Unique machine names from backend logs
    const uniqueMachines = useMemo(() => {
        const names = new Set<string>()
        allRows.forEach((row) => {
            if (row.data.name) {
                names.add(row.data.name)
            }
        })
        return Array.from(names).sort()
    }, [allRows])

    // Load existing links
    const loadLinks = async () => {
        setLoadingLinks(true)
        try {
            const data = await listSharedWebConfigs()
            setLinks(data)
        } catch (err) {
            console.error('Error fetching links:', err)
            showToast('Lỗi khi tải danh sách liên kết chia sẻ', 'error')
        } finally {
            setLoadingLinks(false)
        }
    }

    useEffect(() => {
        loadLinks()
    }, [])

    const handleOpenCreateDialog = () => {
        setEditingUuid(null)
        setSelectedFeatures(['Tổng quan'])
        setSelectedMachines([])
        setSelectedGame('__all__')
        setGeneratedUrl('')
        setIsDialogOpen(true)
    }

    const handleOpenEditDialog = (link: SharedWebConfig) => {
        setEditingUuid(link.uuid)
        setSelectedFeatures(link.allowed_features || [])
        setSelectedMachines(link.allowed_machines || [])
        setSelectedGame(link.selected_game || '__all__')
        setGeneratedUrl('')
        setIsDialogOpen(true)
    }

    const handleSelectAllMachines = () => {
        if (selectedMachines.length === uniqueMachines.length) {
            setSelectedMachines([])
        } else {
            setSelectedMachines([...uniqueMachines])
        }
    }

    const handleToggleMachine = (name: string) => {
        if (selectedMachines.includes(name)) {
            setSelectedMachines(selectedMachines.filter((m) => m !== name))
        } else {
            setSelectedMachines([...selectedMachines, name])
        }
    }

    const handleToggleFeature = (id: string) => {
        if (selectedFeatures.includes(id)) {
            setSelectedFeatures(selectedFeatures.filter((f) => f !== id))
        } else {
            setSelectedFeatures([...selectedFeatures, id])
        }
    }

    const handleSaveConfig = async () => {
        if (selectedFeatures.length === 0) {
            showToast('Vui lòng chọn ít nhất 1 chức năng hiển thị!', 'warning')
            return
        }
        if (selectedMachines.length === 0) {
            showToast('Vui lòng chọn ít nhất 1 máy được xem log!', 'warning')
            return
        }

        setSaving(true)
        try {
            if (editingUuid) {
                // Update
                const res = await updateSharedWebConfig(editingUuid, selectedFeatures, selectedMachines, selectedGame)
                if (res.success) {
                    showToast('Cập nhật liên kết chia sẻ thành công!', 'success')
                    setIsDialogOpen(false)
                    await loadLinks()
                } else {
                    showToast(res.message || 'Lỗi khi cập nhật cấu hình', 'error')
                }
            } else {
                // Create
                const res = await createSharedWebConfig(selectedFeatures, selectedMachines, selectedGame)
                if (res.success && res.uuid) {
                    const url = `${window.location.origin}/shared/${res.uuid}`
                    setGeneratedUrl(url)
                    showToast('Tạo liên kết chia sẻ thành công!', 'success')
                    await loadLinks()
                } else {
                    showToast(res.message || 'Lỗi khi tạo liên kết', 'error')
                }
            }
        } catch (err: any) {
            console.error('Error saving config:', err)
            showToast('Lỗi máy chủ: ' + (err.message || err), 'error')
        } finally {
            setSaving(false)
        }
    }

    const handleCopyUrl = (url: string) => {
        navigator.clipboard.writeText(url)
        showToast('Đã copy liên kết vào clipboard!', 'success')
    }

    const handleDeleteLink = async (uuid: string) => {
        if (!confirm('Bạn có chắc chắn muốn thu hồi (xóa) liên kết chia sẻ này không? Người dùng truy cập bằng liên kết này sẽ không xem được nữa.')) {
            return
        }
        try {
            const res = await deleteSharedWebConfig(uuid)
            if (res.success) {
                showToast('Đã thu hồi liên kết thành công!', 'success')
                await loadLinks()
            } else {
                showToast(res.message || 'Lỗi khi thu hồi liên kết', 'error')
            }
        } catch (err: any) {
            console.error('Error deleting link:', err)
            showToast('Lỗi máy chủ: ' + (err.message || err), 'error')
        }
    }

    return (
        <div className="p-6 text-slate-800 dark:text-slate-100 flex flex-col gap-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h2 className="page-title text-2xl font-black text-slate-800 dark:text-slate-100">Cấu hình URL Web Chia Sẻ (CreateWebURL)</h2>
                    <p className="page-description text-slate-500 text-sm">Tạo hoặc sửa đổi các liên kết xem trực tiếp không cần tài khoản đăng nhập và ẩn Sidebar bên trái.</p>
                </div>
                <button
                    onClick={handleOpenCreateDialog}
                    className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl flex items-center gap-1.5 transition-colors shrink-0 shadow-md shadow-purple-500/10"
                >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                    </svg>
                    Tạo URL Mới
                </button>
            </div>

            {/* List of existing links */}
            <div className="bg-white dark:bg-slate-900/45 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800/80">
                <h3 className="text-sm font-black text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-4">Danh sách liên kết đang hoạt động</h3>

                {loadingLinks ? (
                    <div className="py-8 text-center text-xs text-slate-400 font-bold">
                        Đang tải danh sách liên kết...
                    </div>
                ) : links.length === 0 ? (
                    <div className="py-8 text-center text-xs text-slate-400 font-bold">
                        Chưa có liên kết chia sẻ nào được tạo. Nhấp vào "Tạo URL Mới" để bắt đầu.
                    </div>
                ) : (
                    <div className="table-scroll-shell">
                        <div className="table-scroll">
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Ngày tạo</th>
                                        <th>Chức năng hiển thị</th>
                                        <th>Kênh Game</th>
                                        <th>Thiết bị được xem</th>
                                        <th>Liên kết chia sẻ</th>
                                        <th>Hành động</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {links.map((link) => {
                                        const url = `${window.location.origin}/shared/${link.uuid}`
                                        const createdDate = new Date(link.created_at).toLocaleString('vi-VN', { hour12: false })
                                        return (
                                            <tr key={link.uuid}>
                                                <td className="text-xs text-slate-500 font-semibold">{createdDate}</td>
                                                <td>
                                                    <div className="flex flex-wrap gap-1 max-w-xs">
                                                        {link.allowed_features.map((feat) => (
                                                            <span key={feat} className="px-2 py-0.5 text-[9px] font-bold bg-purple-50 dark:bg-purple-950/20 text-purple-600 dark:text-purple-400 rounded-md">
                                                                {feat}
                                                            </span>
                                                        ))}
                                                    </div>
                                                </td>
                                                <td>
                                                    <span className={`px-2 py-0.5 text-[9px] font-bold rounded-md ${
                                                        link.selected_game && link.selected_game !== '__all__'
                                                            ? 'bg-amber-50 dark:bg-amber-950/20 text-amber-600 dark:text-amber-400'
                                                            : 'bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                                                    }`}>
                                                        {AVAILABLE_GAMES.find(g => g.id === link.selected_game)?.label || link.selected_game || 'Tất cả Game'}
                                                    </span>
                                                </td>
                                                <td>
                                                    <span className="px-2 py-0.5 text-[9px] font-bold bg-indigo-50 dark:bg-indigo-950/20 text-indigo-600 dark:text-indigo-400 rounded-md">
                                                        {link.allowed_machines.length} máy
                                                    </span>
                                                </td>
                                                <td className="mono text-xs max-w-sm truncate select-all">{url}</td>
                                                <td>
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            onClick={() => handleCopyUrl(url)}
                                                            className="px-2 py-1 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-[10px] font-bold rounded-lg transition-colors"
                                                            title="Copy liên kết"
                                                        >
                                                            Copy
                                                        </button>
                                                        <button
                                                            onClick={() => handleOpenEditDialog(link)}
                                                            className="px-2 py-1 bg-amber-500 hover:bg-amber-600 text-white text-[10px] font-bold rounded-lg transition-colors"
                                                            title="Sửa cấu hình"
                                                        >
                                                            Sửa
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteLink(link.uuid)}
                                                            className="px-2 py-1 bg-rose-500 hover:bg-rose-600 text-white text-[10px] font-bold rounded-lg transition-colors"
                                                            title="Thu hồi liên kết"
                                                        >
                                                            Thu hồi
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>

            {/* Dialog Form for Create / Edit */}
            <Dialog
                open={isDialogOpen}
                onClose={() => setIsDialogOpen(false)}
                title={editingUuid ? "Sửa Cấu Hình Liên Kết Chia Sẻ" : "Tạo Liên Kết Chia Sẻ Mới"}
            >
                <div className="flex flex-col gap-5 text-slate-800 dark:text-slate-100 max-h-[80vh] overflow-y-auto pr-1">
                    
                    {/* Render URL if generated successfully */}
                    {generatedUrl ? (
                        <div className="flex flex-col gap-4 py-4">
                            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/15 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 rounded-xl text-xs font-semibold flex items-center gap-2">
                                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                    <polyline points="20 6 9 17 4 12" />
                                </svg>
                                Liên kết chia sẻ đã được tạo thành công!
                            </div>
                            
                            <div className="flex flex-col gap-1.5">
                                <label className="text-[10px] font-bold text-slate-400 uppercase">Liên kết truy cập:</label>
                                <div className="p-3 bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800 rounded-xl font-mono text-xs text-slate-800 dark:text-slate-200 break-all select-all leading-normal">
                                    {generatedUrl}
                                </div>
                            </div>
                            
                            <div className="flex gap-2 mt-2">
                                <button
                                    onClick={() => handleCopyUrl(generatedUrl)}
                                    className="flex-1 bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold py-2.5 rounded-xl transition-all flex items-center justify-center gap-1.5 shadow-md shadow-purple-500/10"
                                >
                                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                                    </svg>
                                    Copy Liên Kết
                                </button>
                                <button
                                    onClick={() => setIsDialogOpen(false)}
                                    className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-200 text-xs font-bold rounded-xl transition-all"
                                >
                                    Đóng
                                </button>
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* Section 1: Features */}
                            <div>
                                <h3 className="text-xs font-black text-slate-400 uppercase tracking-wider mb-2.5">1. Chọn chức năng hiển thị</h3>
                                <div className="grid grid-cols-2 gap-2.5">
                                    {AVAILABLE_FEATURES.map((feature) => {
                                        const isChecked = selectedFeatures.includes(feature.id)
                                        return (
                                            <label 
                                                key={feature.id} 
                                                className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-semibold cursor-pointer select-none transition-all ${
                                                    isChecked 
                                                        ? 'bg-purple-50/70 dark:bg-purple-950/20 border-purple-500 text-purple-600 dark:text-purple-400'
                                                        : 'bg-slate-50/50 dark:bg-slate-900/30 border-slate-200 dark:border-slate-800/60 hover:bg-slate-100/50 dark:hover:bg-slate-800/40 text-slate-600 dark:text-slate-400'
                                                }`}
                                            >
                                                <input 
                                                    type="checkbox"
                                                    checked={isChecked}
                                                    onChange={() => handleToggleFeature(feature.id)}
                                                    className="sr-only"
                                                />
                                                <span className={`w-3.5 h-3.5 rounded flex items-center justify-center border transition-all ${
                                                    isChecked ? 'border-purple-500 bg-purple-500 text-white' : 'border-slate-300 dark:border-slate-700'
                                                }`}>
                                                    {isChecked && (
                                                        <svg className="w-2 h-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="4">
                                                            <polyline points="20 6 9 17 4 12" />
                                                        </svg>
                                                    )}
                                                </span>
                                                {feature.label}
                                            </label>
                                        )
                                    })}
                                </div>
                            </div>

                            <hr className="border-slate-100 dark:border-slate-800/70" />

                            {/* Section 2: Game Channel */}
                            <div>
                                <h3 className="text-xs font-black text-slate-400 uppercase tracking-wider mb-2.5">2. Chọn kênh game mặc định</h3>
                                <div className="relative">
                                    <select
                                        value={selectedGame}
                                        onChange={(e) => setSelectedGame(e.target.value)}
                                        className="w-full bg-slate-50/50 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800/60 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 focus:outline-none focus:border-purple-500 transition-all cursor-pointer appearance-none"
                                    >
                                        {AVAILABLE_GAMES.map((game) => (
                                            <option key={game.id} value={game.id} className="dark:bg-slate-900">
                                                {game.label}
                                            </option>
                                        ))}
                                    </select>
                                    <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none text-slate-400">
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                                        </svg>
                                    </div>
                                </div>
                            </div>

                            <hr className="border-slate-100 dark:border-slate-800/70" />

                            {/* Section 3: Machines */}
                            <div>
                                <div className="flex justify-between items-center mb-2.5">
                                    <h3 className="text-xs font-black text-slate-400 uppercase tracking-wider">3. Chọn máy được phép xem log</h3>
                                    <button 
                                        onClick={handleSelectAllMachines}
                                        className="text-[9px] font-black text-purple-600 dark:text-purple-400 hover:underline uppercase"
                                    >
                                        {selectedMachines.length === uniqueMachines.length ? 'Bỏ chọn tất cả' : 'Chọn tất cả'}
                                    </button>
                                </div>

                                <div className="max-h-60 overflow-y-auto border border-slate-100 dark:border-slate-800/80 rounded-xl p-2.5 bg-slate-50/50 dark:bg-slate-950/30 grid grid-cols-1 sm:grid-cols-2 gap-2">
                                    {uniqueMachines.map((name) => {
                                        const isChecked = selectedMachines.includes(name)
                                        const machineRow = allRows.find(r => r.data.name === name)
                                        const displayName = machineRow?.data.name_edit
                                            ? `${machineRow.data.name_edit} (${name})`
                                            : name
                                        return (
                                            <label 
                                                key={name}
                                                className={`flex items-center gap-2.5 px-3 py-1.5 rounded-lg border text-xs cursor-pointer select-none transition-all ${
                                                    isChecked 
                                                        ? 'bg-indigo-50/50 dark:bg-indigo-950/15 border-indigo-500/80 text-indigo-600 dark:text-indigo-400 font-semibold'
                                                        : 'bg-white dark:bg-slate-900/30 border-slate-200 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30 text-slate-600 dark:text-slate-400'
                                                }`}
                                            >
                                                <input 
                                                    type="checkbox"
                                                    checked={isChecked}
                                                    onChange={() => handleToggleMachine(name)}
                                                    className="sr-only"
                                                />
                                                <span className={`w-3.5 h-3.5 rounded flex items-center justify-center border transition-all ${
                                                    isChecked ? 'border-indigo-500 bg-indigo-500 text-white' : 'border-slate-300 dark:border-slate-700'
                                                }`}>
                                                    {isChecked && (
                                                        <svg className="w-2 h-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="4">
                                                            <polyline points="20 6 9 17 4 12" />
                                                        </svg>
                                                    )}
                                                </span>
                                                <span className="truncate">{displayName}</span>
                                            </label>
                                        )
                                    })}
                                    {uniqueMachines.length === 0 && (
                                        <div className="col-span-2 text-center text-slate-400 py-6 text-xs font-semibold">
                                            Không tìm thấy dữ liệu máy từ logs hệ thống.
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Dialog Footer Actions */}
                            <div className="flex justify-end gap-2.5 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/70">
                                <button
                                    onClick={() => setIsDialogOpen(false)}
                                    type="button"
                                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                                >
                                    Hủy
                                </button>
                                <button
                                    onClick={handleSaveConfig}
                                    disabled={saving}
                                    className="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-bold px-4 py-2 rounded-xl transition-all flex items-center gap-1.5"
                                >
                                    {saving ? 'Đang lưu...' : editingUuid ? 'Lưu Thay Đổi' : 'Tạo Liên Kết'}
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </Dialog>
        </div>
    )
}
