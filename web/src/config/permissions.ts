// Central definition of module-level permissions and the actions each module supports.
// Permission keys are stored as strings:
//   - Module access:  the module label itself (e.g. "Notification")
//   - Module action:  "<label>:<action>" (e.g. "Notification:add")
// This keeps backward compatibility with the sidebar gating which checks the plain label.

export type PermissionAction = 'add' | 'edit' | 'delete' | 'lock' | 'toggle'

export interface ModulePermission {
  key: string // module label (matches sidebar NAV_ITEMS label)
  label: string // display name in the permission matrix
  actions: PermissionAction[] // actions this module actually supports
}

export const ACTION_LABELS: Record<PermissionAction, string> = {
  add: 'Thêm',
  edit: 'Sửa',
  delete: 'Xóa',
  lock: 'Khóa',
  toggle: 'Bật/Tắt',
}

// Order mirrors the sidebar. Only list actions a module truly supports.
export const MODULE_PERMISSIONS: ModulePermission[] = [
  { key: 'Tổng quan', label: 'Tổng quan', actions: ['edit'] },
  { key: 'SRT', label: 'SRT', actions: [] },
  { key: 'Thông số Stream', label: 'Thông số Stream', actions: [] },
  { key: 'URL & Key', label: 'URL & Key', actions: [] },
  { key: 'Thống kê', label: 'Thống kê', actions: [] },
  { key: 'Vmix Monitor', label: 'Vmix Monitor', actions: [] },
  { key: 'Record & MultiCorder', label: 'Record & MultiCorder', actions: [] },
  { key: 'Mobile Monitor', label: 'Mobile Monitor', actions: ['edit'] },
  { key: 'ViewSync', label: 'ViewSync', actions: ['add', 'delete'] },
  { key: 'Speedtest', label: 'Speedtest', actions: [] },
  { key: 'Debug Log', label: 'Debug Log', actions: ['add', 'delete'] },
  { key: 'CreateWebURL', label: 'CreateWebURL', actions: ['add', 'edit', 'delete'] },
  { key: 'Quản lý Kênh', label: 'Quản lý Kênh', actions: ['add', 'edit', 'delete'] },
  { key: 'Notification', label: 'Notification', actions: ['add', 'edit', 'delete', 'toggle'] },
  { key: 'Tài khoản', label: 'Tài khoản', actions: ['add', 'edit', 'delete', 'lock'] },
  { key: 'Phân quyền', label: 'Phân quyền', actions: ['add', 'edit', 'delete'] },
]

export function actionPermissionKey(moduleKey: string, action: PermissionAction): string {
  return `${moduleKey}:${action}`
}

// Full flat list of every assignable permission key (access + actions).
export function getAllPermissionKeys(): string[] {
  const keys: string[] = []
  for (const m of MODULE_PERMISSIONS) {
    keys.push(m.key)
    for (const a of m.actions) keys.push(actionPermissionKey(m.key, a))
  }
  return keys
}
