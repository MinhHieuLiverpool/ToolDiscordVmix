import { useEffect, useState } from 'react'
import { fetchRoles, createRole, updateRole, deleteRole } from '../services/api'
import type { BackendRoleItem } from '../services/api'
import { showToast } from '../components/ui/Toast'
import Dialog from '../components/ui/Dialog'
import { MODULE_PERMISSIONS, ACTION_LABELS, actionPermissionKey } from '../config/permissions'
import type { PermissionAction } from '../config/permissions'
import { hasActionPermission } from '../services/auth'

const MODULE_KEY = 'Phân quyền'

// Toggle module access. Turning access OFF also strips all of its action keys.
function toggleAccess(perms: string[], moduleKey: string): string[] {
    const mod = MODULE_PERMISSIONS.find(m => m.key === moduleKey)
    if (perms.includes(moduleKey)) {
        const actionKeys = mod ? mod.actions.map(a => actionPermissionKey(moduleKey, a)) : []
        return perms.filter(p => p !== moduleKey && !actionKeys.includes(p))
    }
    return [...perms, moduleKey]
}

// Toggle an action. Turning an action ON also ensures module access is granted.
function toggleAction(perms: string[], moduleKey: string, action: PermissionAction): string[] {
    const key = actionPermissionKey(moduleKey, action)
    if (perms.includes(key)) {
        return perms.filter(p => p !== key)
    }
    const withAccess = perms.includes(moduleKey) ? [...perms] : [...perms, moduleKey]
    return [...withAccess, key]
}

function PermissionMatrix({
    permissions,
    onToggleAccess,
    onToggleAction,
}: {
    permissions: string[]
    onToggleAccess: (moduleKey: string) => void
    onToggleAction: (moduleKey: string, action: PermissionAction) => void
}) {
    return (
        <div
            style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.4rem',
                padding: '0.75rem',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                maxHeight: '340px',
                overflowY: 'auto',
            }}
        >
            {MODULE_PERMISSIONS.map(m => {
                const hasAccess = permissions.includes(m.key)
                return (
                    <div
                        key={m.key}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            gap: '0.75rem',
                            padding: '0.4rem 0.6rem',
                            background: '#ffffff',
                            borderRadius: '6px',
                            border: '1px solid #e2e8f0',
                        }}
                    >
                        <label
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.4rem',
                                minWidth: '180px',
                                cursor: 'pointer',
                                fontSize: '0.82rem',
                                fontWeight: 600,
                                color: '#334155',
                                userSelect: 'none',
                            }}
                        >
                            <input
                                type="checkbox"
                                checked={hasAccess}
                                onChange={() => onToggleAccess(m.key)}
                                style={{ accentColor: '#4f46e5' }}
                            />
                            {m.label}
                        </label>
                        {m.actions.length > 0 && (
                            <div style={{ display: 'flex', gap: '0.85rem', flexWrap: 'wrap' }}>
                                {m.actions.map(a => {
                                    const key = actionPermissionKey(m.key, a)
                                    return (
                                        <label
                                            key={a}
                                            style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.3rem',
                                                cursor: 'pointer',
                                                fontSize: '0.78rem',
                                                color: hasAccess ? '#475569' : '#94a3b8',
                                                userSelect: 'none',
                                            }}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={permissions.includes(key)}
                                                onChange={() => onToggleAction(m.key, a)}
                                                style={{ accentColor: '#4f46e5' }}
                                            />
                                            {ACTION_LABELS[a]}
                                        </label>
                                    )
                                })}
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}

export default function RolePage() {
    const [roles, setRoles] = useState<BackendRoleItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')

    const canAdd = hasActionPermission(MODULE_KEY, 'add')
    const canEdit = hasActionPermission(MODULE_KEY, 'edit')
    const canDelete = hasActionPermission(MODULE_KEY, 'delete')

    // Modals
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [showEditModal, setShowEditModal] = useState(false)
    const [selectedRole, setSelectedRole] = useState<BackendRoleItem | null>(null)

    // Forms
    const [newRoleKey, setNewRoleKey] = useState('')
    const [newName, setNewName] = useState('')
    const [newDescription, setNewDescription] = useState('')
    const [newPermissions, setNewPermissions] = useState<string[]>([])

    const [editName, setEditName] = useState('')
    const [editDescription, setEditDescription] = useState('')
    const [editPermissions, setEditPermissions] = useState<string[]>([])

    const loadRoles = async () => {
        try {
            setError('')
            setLoading(true)
            const data = await fetchRoles()
            setRoles(data || [])
        } catch (err) {
            console.error(err)
            setError('Không thể tải danh sách vai trò từ backend.')
            showToast('Không thể tải danh sách vai trò.', 'error')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        void loadRoles()
    }, [])

    const handleCreateRole = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!newRoleKey.trim() || !newName.trim()) {
            showToast('Vui lòng nhập đầy đủ mã vai trò và tên vai trò.', 'warning')
            return
        }

        try {
            const res = await createRole({
                role_key: newRoleKey.trim().toLowerCase(),
                name: newName.trim(),
                description: newDescription.trim(),
                permissions: newPermissions
            })

            if (res.success) {
                showToast('Thêm vai trò mới thành công!', 'success')
                setShowCreateModal(false)
                setNewRoleKey('')
                setNewName('')
                setNewDescription('')
                setNewPermissions([])
                await loadRoles()
            } else {
                showToast(res.message || 'Thêm vai trò thất bại.', 'error')
            }
        } catch (err: any) {
            console.error(err)
            showToast(err.response?.data?.message || 'Lỗi khi tạo vai trò.', 'error')
        }
    }

    const handleEditRole = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!selectedRole) return

        if (selectedRole.role_key.toLowerCase() === 'admin') {
            showToast('Không thể chỉnh sửa vai trò default admin.', 'error')
            return
        }

        try {
            const res = await updateRole({
                role_key: selectedRole.role_key,
                name: editName.trim(),
                description: editDescription.trim(),
                permissions: editPermissions
            })

            if (res.success) {
                showToast('Cập nhật vai trò thành công!', 'success')
                setShowEditModal(false)
                setSelectedRole(null)
                setEditName('')
                setEditDescription('')
                setEditPermissions([])
                await loadRoles()
            } else {
                showToast(res.message || 'Cập nhật vai trò thất bại.', 'error')
            }
        } catch (err: any) {
            console.error(err)
            showToast(err.response?.data?.message || 'Lỗi khi cập nhật vai trò.', 'error')
        }
    }

    const handleDeleteRole = async (roleKey: string) => {
        if (roleKey.toLowerCase() === 'admin') {
            showToast('Không thể xóa vai trò default admin.', 'error')
            return
        }

        if (!window.confirm(`Bạn có chắc chắn muốn XÓA vai trò "${roleKey}" không?`)) {
            return
        }

        try {
            const res = await deleteRole(roleKey)
            if (res.success) {
                showToast('Xóa vai trò thành công!', 'success')
                await loadRoles()
            } else {
                showToast(res.message || 'Xóa vai trò thất bại.', 'error')
            }
        } catch (err: any) {
            console.error(err)
            showToast(err.response?.data?.message || 'Lỗi khi xóa vai trò.', 'error')
        }
    }

    return (
        <>
            <div className="page-header" style={{ marginBottom: '1.5rem' }}>
                <h2 className="page-title">Phân quyền</h2>
                <p className="page-description">Quản lý vai trò và quyền hạn truy cập hệ thống.</p>
            </div>

            <section className="card-light account-card">
                <div className="account-card-header">
                    <div>
                        <h3 className="account-card-title">Vai trò</h3>
                        <p className="account-card-subtitle">Nhóm các quyền truy cập menu được phân bổ cho tài khoản.</p>
                    </div>
                    {canAdd && (
                        <button
                            className="account-action-btn"
                            type="button"
                            onClick={() => setShowCreateModal(true)}
                        >
                            Thêm vai trò
                        </button>
                    )}
                </div>

                {loading ? (
                    <div className="account-empty">Đang tải danh sách vai trò...</div>
                ) : error ? (
                    <div className="account-empty">{error}</div>
                ) : roles.length === 0 ? (
                    <div className="account-empty">Chưa có vai trò nào được định nghĩa.</div>
                ) : (
                    <div className="account-table-wrap">
                        <table className="account-table">
                            <colgroup>
                                <col style={{ width: '15%' }} />
                                <col style={{ width: '20%' }} />
                                <col style={{ width: '45%' }} />
                                <col style={{ width: '20%' }} />
                            </colgroup>
                            <thead>
                                <tr>
                                    <th>Mã vai trò</th>
                                    <th>Tên vai trò</th>
                                    <th>Quyền truy cập</th>
                                    <th>Hành động</th>
                                </tr>
                            </thead>
                            <tbody>
                                {roles.map((role) => {
                                    const isAdminRole = role.role_key.toLowerCase() === 'admin'
                                    return (
                                        <tr key={role.role_key}>
                                            <td>
                                                <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#334155' }}>
                                                    {role.role_key}
                                                </span>
                                            </td>
                                            <td>
                                                <div style={{ fontWeight: 600, color: isAdminRole ? '#dc2626' : '#2563eb' }}>
                                                    {role.name}
                                                </div>
                                                {role.description && (
                                                    <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.1rem' }}>
                                                        {role.description}
                                                    </div>
                                                )}
                                            </td>
                                            <td>
                                                <div className="role-perms">
                                                    {role.permissions && role.permissions.length > 0 ? (
                                                        role.permissions.map((perm) => (
                                                            <span
                                                                key={`${role.role_key}:${perm}`}
                                                                className="role-perm-chip"
                                                                style={{
                                                                    fontSize: '10px',
                                                                    textTransform: 'none',
                                                                    fontWeight: 500,
                                                                    padding: '0.12rem 0.35rem',
                                                                    ...(isAdminRole
                                                                        ? { background: 'rgba(220, 38, 38, 0.08)', color: '#dc2626' }
                                                                        : { background: 'rgba(37, 99, 235, 0.08)', color: '#2563eb' }
                                                                    )
                                                                }}
                                                            >
                                                                {perm}
                                                            </span>
                                                        ))
                                                    ) : (
                                                        <span style={{ color: '#94a3b8', fontStyle: 'italic', fontSize: '0.75rem' }}>không có quyền</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td>
                                                <div style={{ display: 'flex', gap: '0.35rem' }}>
                                                    {canEdit && (
                                                        <button
                                                            type="button"
                                                            className="account-password-btn"
                                                            disabled={isAdminRole}
                                                            style={isAdminRole ? {
                                                                color: '#cbd5e1',
                                                                borderColor: '#e2e8f0',
                                                                background: '#f1f5f9',
                                                                cursor: 'not-allowed',
                                                                opacity: 0.7
                                                            } : {
                                                                color: '#4f46e5',
                                                                borderColor: 'rgba(99, 102, 241, 0.4)',
                                                                background: 'rgba(99, 102, 241, 0.05)'
                                                            }}
                                                            onClick={() => {
                                                                setSelectedRole(role)
                                                                setEditName(role.name)
                                                                setEditDescription(role.description || '')
                                                                setEditPermissions(role.permissions || [])
                                                                setShowEditModal(true)
                                                            }}
                                                        >
                                                            Sửa
                                                        </button>
                                                    )}
                                                    {canDelete && (
                                                        <button
                                                            type="button"
                                                            className="account-password-btn"
                                                            disabled={isAdminRole}
                                                            style={isAdminRole ? {
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
                                                            onClick={() => handleDeleteRole(role.role_key)}
                                                        >
                                                            Xóa
                                                        </button>
                                                    )}
                                                    {!canEdit && !canDelete && (
                                                        <span style={{ color: '#94a3b8', fontSize: '0.75rem', fontStyle: 'italic' }}>—</span>
                                                    )}
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

            {/* Create Role Modal */}
            <Dialog
                open={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                title="Thêm vai trò mới"
            >
                <form onSubmit={handleCreateRole} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                            Mã vai trò * (Ví dụ: viewer, editor)
                        </label>
                        <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                            <input
                                type="text"
                                required
                                className="table-search-input"
                                placeholder="Nhập mã vai trò"
                                value={newRoleKey}
                                onChange={(e) => setNewRoleKey(e.target.value)}
                            />
                        </div>
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                            Tên vai trò * (Ví dụ: Người xem, Quản lý)
                        </label>
                        <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                            <input
                                type="text"
                                required
                                className="table-search-input"
                                placeholder="Nhập tên hiển thị vai trò"
                                value={newName}
                                onChange={(e) => setNewName(e.target.value)}
                            />
                        </div>
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                            Mô tả vai trò
                        </label>
                        <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                            <input
                                type="text"
                                className="table-search-input"
                                placeholder="Nhập mô tả vai trò"
                                value={newDescription}
                                onChange={(e) => setNewDescription(e.target.value)}
                            />
                        </div>
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                            Quyền truy cập & hành động
                        </label>
                        <PermissionMatrix
                            permissions={newPermissions}
                            onToggleAccess={(k) => setNewPermissions(prev => toggleAccess(prev, k))}
                            onToggleAction={(k, a) => setNewPermissions(prev => toggleAction(prev, k, a))}
                        />
                    </div>
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

            {/* Edit Role Modal */}
            {showEditModal && selectedRole && (
                <Dialog
                    open={showEditModal}
                    onClose={() => {
                        setShowEditModal(false)
                        setSelectedRole(null)
                    }}
                    title={`Chỉnh sửa vai trò: ${selectedRole.role_key}`}
                >
                    <form onSubmit={handleEditRole} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                                Mã vai trò
                            </label>
                            <div className="table-search-wrap" style={{ maxWidth: '100%', background: '#f8fafc', color: '#64748b', boxSizing: 'border-box' }}>
                                <input
                                    type="text"
                                    className="table-search-input"
                                    style={{ color: '#64748b' }}
                                    value={selectedRole.role_key}
                                    disabled
                                />
                            </div>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                                Tên vai trò *
                            </label>
                            <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                                <input
                                    type="text"
                                    required
                                    className="table-search-input"
                                    placeholder="Nhập tên hiển thị vai trò"
                                    value={editName}
                                    onChange={(e) => setEditName(e.target.value)}
                                />
                            </div>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                                Mô tả vai trò
                            </label>
                            <div className="table-search-wrap" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                                <input
                                    type="text"
                                    className="table-search-input"
                                    placeholder="Nhập mô tả vai trò"
                                    value={editDescription}
                                    onChange={(e) => setEditDescription(e.target.value)}
                                />
                            </div>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '0.35rem' }}>
                                Quyền truy cập & hành động
                            </label>
                            <PermissionMatrix
                                permissions={editPermissions}
                                onToggleAccess={(k) => setEditPermissions(prev => toggleAccess(prev, k))}
                                onToggleAction={(k, a) => setEditPermissions(prev => toggleAction(prev, k, a))}
                            />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
                            <button
                                type="button"
                                className="account-password-btn"
                                onClick={() => {
                                    setShowEditModal(false)
                                    setSelectedRole(null)
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
