type RoleItem = {
    id: string
    name: string
    description?: string
    permissions?: string[]
    members?: number
    status?: 'active' | 'disabled'
}

export default function Role({ roles = [] }: { roles?: RoleItem[] }) {
    return (
        <section className="card-light account-card">
            <div className="account-card-header">
                <div>
                    <h3 className="account-card-title">Phân quyền</h3>
                    <p className="account-card-subtitle">Nhóm vai trò và quyền hạn trong hệ thống.</p>
                </div>
                <button className="account-action-btn" type="button">Thêm role</button>
            </div>

            {roles.length === 0 ? (
                <div className="account-empty">Chưa có dữ liệu phân quyền.</div>
            ) : (
                <div className="role-list">
                    {roles.map((role) => (
                        <div key={role.id} className="role-item">
                            <div className="role-item-header">
                                <div>
                                    <div className="role-name">{role.name}</div>
                                    {role.description && <div className="role-meta">{role.description}</div>}
                                </div>
                                <span className={`role-status ${role.status === 'disabled' ? 'role-status-off' : 'role-status-on'}`}>
                                    {role.status === 'disabled' ? 'DISABLED' : 'ACTIVE'}
                                </span>
                            </div>
                            <div className="role-meta">Thành viên: {role.members ?? 0}</div>
                            {role.permissions && role.permissions.length > 0 && (
                                <div className="role-perms">
                                    {role.permissions.map((perm) => (
                                        <span key={`${role.id}:${perm}`} className="role-perm-chip">{perm}</span>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </section>
    )
}
