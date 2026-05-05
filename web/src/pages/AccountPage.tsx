import { useEffect, useState } from 'react'
import { fetchAccounts, type BackendAccountItem } from '../services/api'

type AccountItem = {
    id: string
    username: string
    displayName: string
    password: string
    role: string
    status?: 'active' | 'disabled'
    lastActive?: string
}

export default function AccountPage() {
    const [accounts, setAccounts] = useState<AccountItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [revealed, setRevealed] = useState<Record<string, boolean>>({})

    useEffect(() => {
        let active = true
        const loadAccounts = async () => {
            try {
                setError('')
                setLoading(true)
                const data = await fetchAccounts()
                if (!active) return
                const mapped = (data || []).map((item: BackendAccountItem, index: number) => {
                    const username = String(item.username || '').trim() || `user-${index + 1}`
                    const password = String(item.password || '').trim()
                    const createdAt = String(item.created_at || '').trim()
                    return {
                        id: `${username}:${index}`,
                        username,
                        displayName: username,
                        password,
                        role: '—',
                        status: 'active' as const,
                        lastActive: createdAt || '-',
                    }
                })
                setAccounts(mapped)
            } catch (err) {
                console.error(err)
                if (active) setError('Không thể tải dữ liệu tài khoản từ backend.')
            } finally {
                if (active) setLoading(false)
            }
        }
        void loadAccounts()
        return () => {
            active = false
        }
    }, [])

    return (
        <>
            <div className="page-header">
                <h2 className="page-title">Người dùng</h2>
                <p className="page-description">Quản lý tài khoản và phân quyền hệ thống.</p>
            </div>

            <section className="card-light account-card">
                <div className="account-card-header">
                    <div>
                        <h3 className="account-card-title">Tài khoản</h3>
                        <p className="account-card-subtitle">Danh sách người dùng đang truy cập hệ thống.</p>
                    </div>
                    <button className="account-action-btn" type="button">Thêm tài khoản</button>
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
                                <col style={{ width: '30%' }} />
                                <col style={{ width: '14%' }} />
                                <col style={{ width: '14%' }} />
                                <col style={{ width: '22%' }} />
                                <col style={{ width: '20%' }} />
                            </colgroup>
                            <thead>
                                <tr>
                                    <th>Tài khoản</th>
                                    <th>Vai trò</th>
                                    <th>Trạng thái</th>
                                    <th>Hoạt động gần nhất</th>
                                    <th>Mật khẩu</th>
                                </tr>
                            </thead>
                            <tbody>
                                {accounts.map((account) => (
                                    <tr key={account.id}>
                                        <td>
                                            <div className="account-user">
                                                <div className="account-user-name">{account.displayName}</div>
                                                <div className="account-user-sub">@{account.username}</div>
                                            </div>
                                        </td>
                                        <td>
                                            <span className="account-role">{account.role}</span>
                                        </td>
                                        <td>
                                            <span className={`account-status ${account.status === 'disabled' ? 'account-status-off' : 'account-status-on'}`}>
                                                {account.status === 'disabled' ? 'DISABLED' : 'ACTIVE'}
                                            </span>
                                        </td>
                                        <td>{account.lastActive || '-'}</td>
                                        <td className="account-password-cell">
                                            <span className="account-password-text">
                                                {account.password
                                                    ? (revealed[account.id] ? account.password : '******')
                                                    : '-'}
                                            </span>
                                            <button
                                                type="button"
                                                className="account-password-btn"
                                                onClick={() =>
                                                    setRevealed((prev) => ({
                                                        ...prev,
                                                        [account.id]: !prev[account.id],
                                                    }))
                                                }
                                                disabled={!account.password}
                                            >
                                                {revealed[account.id] ? 'Ẩn' : 'Xem'}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>
        </>
    )
}
