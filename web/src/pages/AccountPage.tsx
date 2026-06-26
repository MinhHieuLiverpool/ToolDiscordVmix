import { useEffect, useState } from 'react'
import { fetchAccounts, createAccount, updateAccount, deleteAccount, fetchRoles, fetchGameSelected } from '../services/api'
import type { BackendRoleItem } from '../services/api'
import { showToast } from '../components/ui/Toast'
import Dialog from '../components/ui/Dialog'

interface AccountItem {
    username: string
    password?: string
    created_at?: string
    email?: string
    phone?: string
    is_locked?: boolean
    role?: string
    allowed_channels?: string[]
}

export default function AccountPage() {
    const [accounts, setAccounts] = useState<AccountItem[]>([])
    const [roles, setRoles] = useState<BackendRoleItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [revealed, setRevealed] = useState<Record<string, boolean>>({})

    // Modals visibility
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [showEditModal, setShowEditModal] = useState(false)
    const [selectedAccount, setSelectedAccount] = useState<AccountItem | null>(null)

    // Form fields
    const [newUsername, setNewUsername] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [newEmail, setNewEmail] = useState('')
    const [newPhone, setNewPhone] = useState('')
    const [newRole, setNewRole] = useState('')
    const [gameChannels, setGameChannels] = useState<string[]>([])
    const [newAllowedChannels, setNewAllowedChannels] = useState<string[]>([])

    const [editEmail, setEditEmail] = useState('')
    const [editPhone, setEditPhone] = useState('')
    const [editPassword, setEditPassword] = useState('')
    const [editRole, setEditRole] = useState('')
    const [editAllowedChannels, setEditAllowedChannels] = useState<string[]>([])

    const loadAccounts = async () => {
        try {
            setError('')
            setLoading(true)
            const [accountsData, rolesData, channelsData] = await Promise.all([
                fetchAccounts(),
                fetchRoles(),
                fetchGameSelected()
            ])
            const processedAccounts = (accountsData || []).map(acc => ({
                username: acc.username || '',
                password: acc.password,
                created_at: acc.created_at,
                email: acc.email,
                phone: acc.phone,
                is_locked: acc.is_locked,
                role: acc.role,
                allowed_channels: acc.allowed_channels || []
            }))
            setAccounts(processedAccounts)
            setRoles(rolesData || [])
            setGameChannels((channelsData || []).map(c => c.game))
        } catch (err) {
            console.error(err)
            setError('Không thể tải dữ liệu tài khoản và vai trò từ backend.')
            showToast('Không thể tải dữ liệu tài khoản.', 'error')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        void loadAccounts()
    }, [])

    const getRoleName = (roleKey: string) => {
        if (!roleKey) return <span style={{ color: '#94a3b8', fontStyle: 'italic', fontSize: '0.75rem' }}>chưa gán</span>
        if (roleKey.toLowerCase() === 'admin') {
            return (
                <span
                    style={{
                        fontWeight: 600,
                        color: '#dc2626',
                        background: 'rgba(220, 38, 38, 0.08)',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '6px',
                        fontSize: '0.75rem',
                        display: 'inline-block'
                    }}
                >
                    Admin
                </span>
            )
        }
        const r = roles.find(x => x.role_key === roleKey.toLowerCase())
        const displayName = r ? r.name : roleKey
        return (
            <span
                style={{
                    fontWeight: 600,
                    color: '#2563eb',
                    background: 'rgba(37, 99, 235, 0.08)',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    display: 'inline-block'
                }}
            >
                {displayName}
            </span>
        )
    }

    const handleCreateAccount = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!newUsername.trim() || !newPassword.trim()) {
            showToast('Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.', 'warning')
            return
        }
        if (newPassword.length < 4) {
            showToast('Mật khẩu phải dài từ 4 ký tự trở lên.', 'warning')
            return
        }

        try {
            const res = await createAccount({
                username: newUsername.trim(),
                password: newPassword.trim(),
                email: newEmail.trim(),
                phone: newPhone.trim(),
                role: newRole,
                allowed_channels: newRole.toLowerCase() === 'admin' ? [] : newAllowedChannels
            })

            if (res.success) {
                showToast('Thêm tài khoản mới thành công!', 'success')
                setShowCreateModal(false)
                // Reset form
                setNewUsername('')
                setNewPassword('')
                setNewEmail('')
                setNewPhone('')
                setNewRole('')
                setNewAllowedChannels([])
                // Reload list
                await loadAccounts()
            } else {
                showToast(res.message || 'Thêm tài khoản thất bại.', 'error')
            }
        } catch (err: any) {
            console.error(err)
            showToast(err.response?.data?.message || 'Lỗi khi tạo tài khoản.', 'error')
        }
    }

    const handleEditAccount = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!selectedAccount) return

        if (editPassword && editPassword.length < 4) {
            showToast('Mật khẩu mới phải dài từ 4 ký tự trở lên.', 'warning')
            return
        }

        const isMasterAdmin = selectedAccount.username.toLowerCase() === 'admin'
        if (isMasterAdmin && editRole && editRole.toLowerCase() !== 'admin') {
            showToast('Không thể thay đổi vai trò tài khoản master admin.', 'error')
            return
        }

        try {
            const isTargetAdmin = (isMasterAdmin ? 'admin' : editRole).toLowerCase() === 'admin'
            const updates: any = {
                email: editEmail.trim(),
                phone: editPhone.trim(),
                role: isMasterAdmin ? 'admin' : editRole,
                allowed_channels: isTargetAdmin ? [] : editAllowedChannels
            }
            if (editPassword) {
                updates.password = editPassword.trim()
            }

            const res = await updateAccount({
                username: selectedAccount.username,
                ...updates
            })

            if (res.success) {
                showToast('Cập nhật tài khoản thành công!', 'success')
                setShowEditModal(false)
                setSelectedAccount(null)
                setEditPassword('')
                setEditRole('')
                setEditAllowedChannels([])
                await loadAccounts()
            } else {
                showToast(res.message || 'Cập nhật tài khoản thất bại.', 'error')
            }
        } catch (err: any) {
            console.error(err)
            showToast(err.response?.data?.message || 'Lỗi khi cập nhật tài khoản.', 'error')
        }
    }

    const handleToggleLock = async (account: AccountItem) => {
        if (account.username.toLowerCase() === 'admin') {
            showToast('Không thể khóa tài khoản master admin.', 'error')
            return
        }

        const nextLockState = !account.is_locked
        const confirmMsg = nextLockState
            ? `Bạn có chắc chắn muốn khóa tài khoản "${account.username}" không?`
            : `Bạn có chắc chắn muốn mở khóa tài khoản "${account.username}" không?`

        if (!window.confirm(confirmMsg)) return

        try {
            const res = await updateAccount({
                username: account.username,
                is_locked: nextLockState
            })

            if (res.success) {
                showToast(`${nextLockState ? 'Khóa' : 'Mở khóa'} tài khoản thành công!`, 'success')
                await loadAccounts()
            } else {
                showToast(res.message || 'Thao tác thất bại.', 'error')
            }
        } catch (err: any) {
            console.error(err)
            showToast(err.response?.data?.message || 'Lỗi khi thay đổi trạng thái tài khoản.', 'error')
        }
    }

    const handleDeleteAccount = async (username: string) => {
        if (username.toLowerCase() === 'admin') {
            showToast('Không thể xóa tài khoản master admin.', 'error')
            return
        }

        if (!window.confirm(`Bạn có chắc chắn muốn XÓA vĩnh viễn tài khoản "${username}"?`)) {
            return
        }

        try {
            const res = await deleteAccount(username)
            if (res.success) {
                showToast('Xóa tài khoản thành công!', 'success')
                await loadAccounts()
            } else {
                showToast(res.message || 'Xóa tài khoản thất bại.', 'error')
            }
        } catch (err: any) {
            console.error(err)
            showToast(err.response?.data?.message || 'Lỗi khi xóa tài khoản.', 'error')
        }
    }

    return (
        <>
            <section className="card-light account-card">
                <div className="account-card-header">
                    <div>
                        <h3 className="account-card-title">Tài khoản</h3>
                        <p className="account-card-subtitle">Danh sách người dùng đang truy cập hệ thống.</p>
                    </div>
                    <button
                        className="account-action-btn"
                        type="button"
                        onClick={() => setShowCreateModal(true)}
                    >
                        Thêm tài khoản
                    </button>
                </div>

                {loading ? (
                    <div className="account-empty">Đang tải dữ liệu tài khoản...</div>
                ) : error ? (
                    <div className="account-empty">{error}</div>
                ) : accounts.length === 0 ? (
                    <div className="account-empty">Chưa có dữ liệu tài khoản.</div>
                ) : (
                    <div className="account-table-wrap">
                        <table className="account-table">
                            <colgroup>
                                <col style={{ width: '12%' }} />
                                <col style={{ width: '14%' }} />
                                <col style={{ width: '10%' }} />
                                <col style={{ width: '10%' }} />
                                <col style={{ width: '16%' }} />
                                <col style={{ width: '10%' }} />
                                <col style={{ width: '10%' }} />
                                <col style={{ width: '18%' }} />
                            </colgroup>
                            <thead>
                                <tr>
                                    <th>Tài khoản</th>
                                    <th>Email</th>
                                    <th>Số điện thoại</th>
                                    <th>Vai trò</th>
                                    <th>Kênh truy cập</th>
                                    <th>Trạng thái</th>
                                    <th>Mật khẩu</th>
                                    <th>Hành động</th>
                                </tr>
                            </thead>
                            <tbody>
                                {accounts.map((account) => {
                                    const isMasterAdmin = account.username.toLowerCase() === 'admin'
                                    return (
                                        <tr key={account.username}>
                                            <td>
                                                <div className="account-user">
                                                    <div className="account-user-name">{account.username}</div>
                                                    <div className="account-user-sub">@{account.username}</div>
                                                </div>
                                            </td>
                                            <td>
                                                {account.email ? (
                                                    <span>{account.email}</span>
                                                ) : (
                                                    <span style={{ color: '#94a3b8', fontStyle: 'italic', fontSize: '0.75rem' }}>chưa có</span>
                                                )}
                                            </td>
                                            <td>
                                                {account.phone ? (
                                                    <span style={{ fontFamily: 'monospace' }}>{account.phone}</span>
                                                ) : (
                                                    <span style={{ color: '#94a3b8', fontStyle: 'italic', fontSize: '0.75rem' }}>chưa có</span>
                                                )}
                                            </td>
                                            <td>
                                                {getRoleName(account.role || '')}
                                            </td>
                                            <td>
                                                {isMasterAdmin || account.role?.toLowerCase() === 'admin' ? (
                                                    <span style={{
                                                        fontSize: '0.7rem',
                                                        fontWeight: 500,
                                                        color: '#16a34a',
                                                        background: 'rgba(22, 163, 74, 0.08)',
                                                        padding: '0.15rem 0.35rem',
                                                        borderRadius: '4px'
                                                    }}>
                                                        Tất cả
                                                    </span>
                                                ) : account.allowed_channels && account.allowed_channels.length > 0 ? (
                                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', maxWidth: '200px' }}>
                                                        {account.allowed_channels.map(ch => (
                                                            <span key={ch} style={{
                                                                fontSize: '0.7rem',
                                                                color: '#4f46e5',
                                                                background: 'rgba(99, 102, 241, 0.08)',
                                                                padding: '0.15rem 0.35rem',
                                                                borderRadius: '4px',
                                                                whiteSpace: 'nowrap'
                                                            }}>
                                                                {ch}
                                                            </span>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <span style={{ color: '#94a3b8', fontStyle: 'italic', fontSize: '0.75rem' }}>Chưa gán kênh</span>
                                                )}
                                            </td>
                                            <td>
                                                <span className={`account-status ${account.is_locked ? 'account-status-off' : 'account-status-on'}`}>
                                                    {account.is_locked ? 'LOCKED' : 'ACTIVE'}
                                                </span>
                                            </td>
                                            <td className="account-password-cell">
                                                <span className="account-password-text">
                                                    {account.password
                                                        ? (revealed[account.username] ? account.password : '******')
                                                        : '—'}
                                                </span>
                                                {account.password && (
                                                    <button
                                                        type="button"
                                                        style={{
                                                            border: 'none',
                                                            background: 'transparent',
                                                            padding: 0,
                                                            cursor: 'pointer',
                                                            color: '#64748b',
                                                            display: 'inline-flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'center',
                                                            marginLeft: '0.4rem',
                                                            outline: 'none',
                                                            transition: 'color 0.2s'
                                                        }}
                                                        onMouseEnter={(e) => { e.currentTarget.style.color = '#4f46e5' }}
                                                        onMouseLeave={(e) => { e.currentTarget.style.color = '#64748b' }}
                                                        title={revealed[account.username] ? 'Ẩn mật khẩu' : 'Xem mật khẩu'}
                                                        onClick={() =>
                                                            setRevealed((prev) => ({
                                                                ...prev,
                                                                [account.username]: !prev[account.username],
                                                            }))
                                                        }
                                                    >
                                                        {revealed[account.username] ? (
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                                                                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94m9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                                                                <line x1="1" y1="1" x2="23" y2="23" />
                                                            </svg>
                                                        ) : (
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                                                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                                                                <circle cx="12" cy="12" r="3" />
                                                            </svg>
                                                        )}
                                                    </button>
                                                )}
                                            </td>
                                            <td>
                                                <div style={{ display: 'flex', gap: '0.35rem' }}>
                                                    <button
                                                        type="button"
                                                        className="account-password-btn"
                                                        style={{
                                                            color: '#4f46e5',
                                                            borderColor: 'rgba(99, 102, 241, 0.4)',
                                                            background: 'rgba(99, 102, 241, 0.05)'
                                                        }}
                                                        onClick={() => {
                                                            setSelectedAccount(account)
                                                            setEditEmail(account.email || '')
                                                            setEditPhone(account.phone || '')
                                                            setEditPassword('')
                                                            setEditRole(account.role || '')
                                                            setEditAllowedChannels(account.allowed_channels || [])
                                                            setShowEditModal(true)
                                                        }}
                                                    >
                                                        Sửa
                                                    </button>
                                                    <button
                                                        type="button"
                                                        className="account-password-btn"
                                                        disabled={isMasterAdmin}
                                                        style={isMasterAdmin ? {
                                                            color: '#cbd5e1',
                                                            borderColor: '#e2e8f0',
                                                            background: '#f1f5f9',
                                                            cursor: 'not-allowed',
                                                            opacity: 0.7
                                                        } : (account.is_locked ? {
                                                            color: '#10b981',
                                                            borderColor: 'rgba(16, 185, 129, 0.4)',
                                                            background: 'rgba(16, 185, 129, 0.05)'
                                                        } : {
                                                            color: '#f59e0b',
                                                            borderColor: 'rgba(245, 158, 11, 0.4)',
                                                            background: 'rgba(245, 158, 11, 0.05)'
                                                        })}
                                                        onClick={() => handleToggleLock(account)}
                                                    >
                                                        {account.is_locked ? 'Mở khóa' : 'Khóa'}
                                                    </button>
                                                    <button
                                                        type="button"
                                                        className="account-password-btn"
                                                        disabled={isMasterAdmin}
                                                        style={isMasterAdmin ? {
                                                            color: '#cbd5e1',
                                                            borderColor: '#e2e8f0',
                                                            background: '#f1f5f9',
                                                            cursor: 'not-allowed',
                                                            opacity: 0.7
                                                        } : {
                                                            color: '#ef4444',
                                                            borderColor: 'rgba(239, 68, 68, 0.4)',
                                                            background: 'rgba(239, 68, 68, 0.05)'
                                                        }}
                                                        onClick={() => handleDeleteAccount(account.username)}
                                                    >
                                                        Xóa
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>

            {/* Create Account Modal */}
            <Dialog
                open={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                title="Thêm tài khoản mới"
            >
                <form onSubmit={handleCreateAccount} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                            Tên đăng nhập *
                        </label>
                        <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                            <input
                                type="text"
                                required
                                className="table-search-input"
                                placeholder="Nhập tên tài khoản"
                                value={newUsername}
                                onChange={(e) => setNewUsername(e.target.value)}
                            />
                        </div>
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                            Mật khẩu * (Tối thiểu 4 ký tự)
                        </label>
                        <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                            <input
                                type="password"
                                required
                                className="table-search-input"
                                placeholder="Nhập mật khẩu"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                            />
                        </div>
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                            Email
                        </label>
                        <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                            <input
                                type="email"
                                className="table-search-input"
                                placeholder="user@example.com"
                                value={newEmail}
                                onChange={(e) => setNewEmail(e.target.value)}
                            />
                        </div>
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                            Số điện thoại
                        </label>
                        <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                            <input
                                type="text"
                                className="table-search-input"
                                placeholder="Nhập số điện thoại"
                                value={newPhone}
                                onChange={(e) => setNewPhone(e.target.value)}
                            />
                        </div>
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                            Vai trò
                        </label>
                        <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box', background: '#fff' }}>
                            <select
                                className="table-search-input"
                                style={{ width: '100%', padding: '0.5rem', background: 'transparent', border: 'none', outline: 'none', color: '#1e293b' }}
                                value={newRole}
                                onChange={(e) => setNewRole(e.target.value)}
                            >
                                <option value="">-- Chọn vai trò --</option>
                                {roles.map(r => (
                                    <option key={r.role_key} value={r.role_key}>{r.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                    {newRole.toLowerCase() !== 'admin' && gameChannels.length > 0 && (
                        <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                                Kênh được phép truy cập
                            </label>
                            <div style={{
                                display: 'flex',
                                flexWrap: 'wrap',
                                gap: '0.5rem',
                                padding: '0.75rem',
                                background: '#f8fafc',
                                borderRadius: '8px',
                                border: '1px solid #e2e8f0',
                                maxHeight: '150px',
                                overflowY: 'auto'
                            }}>
                                {gameChannels.map(channel => {
                                    const checked = newAllowedChannels.includes(channel)
                                    return (
                                        <label key={channel} style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.35rem',
                                            background: '#fff',
                                            padding: '0.25rem 0.5rem',
                                            borderRadius: '6px',
                                            border: '1px solid #e2e8f0',
                                            fontSize: '0.75rem',
                                            cursor: 'pointer',
                                            userSelect: 'none'
                                        }}>
                                            <input
                                                type="checkbox"
                                                checked={checked}
                                                onChange={(e) => {
                                                    if (e.target.checked) {
                                                        setNewAllowedChannels(prev => [...prev, channel])
                                                    } else {
                                                        setNewAllowedChannels(prev => prev.filter(c => c !== channel))
                                                    }
                                                }}
                                            />
                                            {channel}
                                        </label>
                                    )
                                })}
                            </div>
                        </div>
                    )}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
                        <button
                            type="button"
                            className="account-password-btn"
                            onClick={() => setShowCreateModal(false)}
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            className="account-action-btn"
                        >
                            Xác nhận
                        </button>
                    </div>
                </form>
            </Dialog>

            {/* Edit Account Modal */}
            {showEditModal && selectedAccount && (
                <Dialog
                    open={showEditModal}
                    onClose={() => {
                        setShowEditModal(false)
                        setSelectedAccount(null)
                    }}
                    title={`Chỉnh sửa tài khoản: ${selectedAccount.username}`}
                >
                    <form onSubmit={handleEditAccount} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                                Tên đăng nhập
                            </label>
                            <div className="table-search-wrap" style={{ maxWidth: '100%', background: '#f8fafc', color: '#64748b', boxSizing: 'border-box' }}>
                                <input
                                    type="text"
                                    className="table-search-input"
                                    style={{ color: '#64748b' }}
                                    value={selectedAccount.username}
                                    disabled
                                />
                            </div>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                                Mật khẩu mới (Bỏ trống nếu giữ nguyên)
                            </label>
                            <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                                <input
                                    type="password"
                                    className="table-search-input"
                                    placeholder="Nhập mật khẩu mới"
                                    value={editPassword}
                                    onChange={(e) => setEditPassword(e.target.value)}
                                />
                            </div>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                                Email
                            </label>
                            <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                                <input
                                    type="email"
                                    className="table-search-input"
                                    placeholder="user@example.com"
                                    value={editEmail}
                                    onChange={(e) => setEditEmail(e.target.value)}
                                />
                            </div>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                                Số điện thoại
                            </label>
                            <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                                <input
                                    type="text"
                                    className="table-search-input"
                                    placeholder="Nhập số điện thoại"
                                    value={editPhone}
                                    onChange={(e) => setEditPhone(e.target.value)}
                                />
                            </div>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                                Vai trò
                            </label>
                            <div
                                className="table-search-wrap"
                                style={{
                                    maxWidth: '100%',
                                    boxSizing: 'border-box',
                                    background: selectedAccount.username.toLowerCase() === 'admin' ? '#f8fafc' : '#fff'
                                }}
                            >
                                <select
                                    className="table-search-input"
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem',
                                        background: 'transparent',
                                        border: 'none',
                                        outline: 'none',
                                        color: selectedAccount.username.toLowerCase() === 'admin' ? '#94a3b8' : '#1e293b',
                                        cursor: selectedAccount.username.toLowerCase() === 'admin' ? 'not-allowed' : 'default'
                                    }}
                                    value={editRole}
                                    disabled={selectedAccount.username.toLowerCase() === 'admin'}
                                    onChange={(e) => setEditRole(e.target.value)}
                                >
                                    <option value="">-- Chọn vai trò --</option>
                                    {roles.map(r => (
                                        <option key={r.role_key} value={r.role_key}>{r.name}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        {editRole.toLowerCase() !== 'admin' && gameChannels.length > 0 && (
                            <div>
                                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                                    Kênh được phép truy cập
                                </label>
                                <div style={{
                                    display: 'flex',
                                    flexWrap: 'wrap',
                                    gap: '0.5rem',
                                    padding: '0.75rem',
                                    background: '#f8fafc',
                                    borderRadius: '8px',
                                    border: '1px solid #e2e8f0',
                                    maxHeight: '150px',
                                    overflowY: 'auto'
                                }}>
                                    {gameChannels.map(channel => {
                                        const checked = editAllowedChannels.includes(channel)
                                        return (
                                            <label key={channel} style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.35rem',
                                                background: '#fff',
                                                padding: '0.25rem 0.5rem',
                                                borderRadius: '6px',
                                                border: '1px solid #e2e8f0',
                                                fontSize: '0.75rem',
                                                cursor: 'pointer',
                                                userSelect: 'none'
                                            }}>
                                                <input
                                                    type="checkbox"
                                                    checked={checked}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setEditAllowedChannels(prev => [...prev, channel])
                                                        } else {
                                                            setEditAllowedChannels(prev => prev.filter(c => c !== channel))
                                                        }
                                                    }}
                                                />
                                                {channel}
                                            </label>
                                        )
                                    })}
                                </div>
                            </div>
                        )}
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
                            <button
                                type="button"
                                className="account-password-btn"
                                onClick={() => {
                                    setShowEditModal(false)
                                    setSelectedAccount(null)
                                }}
                            >
                                Hủy
                            </button>
                            <button
                                type="submit"
                                className="account-action-btn"
                            >
                                Cập nhật
                            </button>
                        </div>
                    </form>
                </Dialog>
            )}
        </>
    )
}
