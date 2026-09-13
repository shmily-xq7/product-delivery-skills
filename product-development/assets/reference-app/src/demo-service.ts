// Explicitly isolated demonstration data. Never imported by production templates.
import type { UserRow, UserService } from '../../templates/UserManagement'
let rows: UserRow[] = [{ id: '1', userName: '示例用户', email: 'demo@example.com', department: '演示部门', status: 'enabled', createdAt: '2026-01-01', canDelete: true }]
let sequence = 1
export const demoService: UserService = {
  async dictionaries() { return { departments: [{ value: '演示部门', label: '演示部门' }], statuses: [{ value: 'enabled', label: '可用' }] } },
  async list(query) { const matches = rows.filter(row => (!query.searchText || `${row.userName} ${row.email}`.includes(query.searchText)) && (!query.department || row.department === query.department) && (!query.status || row.status === query.status)); return { items: matches.slice((query.page - 1) * query.pageSize, query.page * query.pageSize), total: matches.length } },
  async save(draft, id) {
    if (draft.email === 'fail@example.com') throw new Error('演示保存失败：请修改邮箱后重试')
    if (id) rows = rows.map(row => row.id === id ? { ...row, ...draft } : row)
    else rows = [...rows, { ...draft, id: String(++sequence), department: '演示部门', status: 'enabled', createdAt: '2026-01-01', canDelete: true }]
  },
  async remove(ids) { rows = rows.filter(row => !ids.includes(row.id)) },
}
