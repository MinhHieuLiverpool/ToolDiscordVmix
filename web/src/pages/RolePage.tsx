import Role from './Role'

type RoleItem = {
    id: string
    name: string
    description?: string
    permissions?: string[]
    members?: number
    status?: 'active' | 'disabled'
}

const EMPTY_ROLES: RoleItem[] = []

export default function RolePage() {
    return (
        <>
            <div className="page-header">
                <h2 className="page-title">Phân quyền</h2>
                <p className="page-description">Quản lý vai trò và quyền hạn hệ thống.</p>
            </div>

            <Role roles={EMPTY_ROLES} />
        </>
    )
}
