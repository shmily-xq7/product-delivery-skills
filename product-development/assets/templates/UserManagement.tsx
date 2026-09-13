// Production skeleton: inject the real API adapter. No fallback mock data or fake success.
// Copy UserListLayout.tsx and data-list-page.scss alongside this file; import shared tokens.css once.
import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Form, Input, Modal, Popconfirm, Select, Space, Tag } from 'antd'
import type { TableProps } from 'antd'
import UserListLayout from './UserListLayout'
import './data-list-page.scss'

export interface UserRow {
  id: string
  userName: string
  email: string
  department: string
  status: string
  createdAt: string
  canDelete: boolean
}
export interface UserDraft { userName: string; email: string }
export interface UserQuery { searchText: string; department?: string; status?: string; page: number; pageSize: number }
export interface DictionaryOption { label: string; value: string }
export interface UserDictionaries { departments: DictionaryOption[]; statuses: DictionaryOption[] }
export interface UserService {
  list(query: UserQuery, signal: AbortSignal): Promise<{ items: UserRow[]; total: number }>
  dictionaries(signal: AbortSignal): Promise<UserDictionaries>
  save(draft: UserDraft, id?: string): Promise<void>
  remove(ids: string[]): Promise<void>
}
export interface UserManagementProps { service: UserService }
const messageOf = (error: unknown) => error instanceof Error ? error.message : '请求失败，请重试'

export default function UserManagement({ service }: UserManagementProps) {
  const [form] = Form.useForm<UserDraft>()
  const [query, setQuery] = useState<UserQuery>({ searchText: '', page: 1, pageSize: 20 })
  const [rows, setRows] = useState<UserRow[]>([])
  const [total, setTotal] = useState(0)
  const [dict, setDict] = useState<UserDictionaries>({ departments: [], statuses: [] })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const [editing, setEditing] = useState<UserRow | null | undefined>(undefined)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    Promise.all([service.list(query, controller.signal), service.dictionaries(controller.signal)])
      .then(([data, dictionaries]) => {
        if (!controller.signal.aborted) { setRows(data.items); setTotal(data.total); setDict(dictionaries) }
      })
      .catch((reason: unknown) => { if (!controller.signal.aborted) { setRows([]); setTotal(0); setError(messageOf(reason)) } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [service, query, revision])
  const statuses = useMemo(() => new Map(dict.statuses.map(item => [item.value, item.label])), [dict.statuses])
  const openEditor = (row: UserRow | null) => { form.resetFields(); form.setFieldsValue(row ?? { userName: '', email: '' }); setEditing(row) }
  const save = async () => {
    let draft: UserDraft
    try { draft = await form.validateFields() } catch { return }
    setSaving(true)
    try { await service.save(draft, editing?.id); setEditing(undefined); setRevision(value => value + 1) }
    catch (reason: unknown) { setError(messageOf(reason)) }
    finally { setSaving(false) }
  }
  const remove = async (id: string) => {
    try { await service.remove([id]); setRevision(value => value + 1) }
    catch (reason: unknown) { setError(messageOf(reason)) }
  }
  const columns: TableProps<UserRow>['columns'] = [
    { title: '用户名', dataIndex: 'userName' },
    { title: '邮箱', dataIndex: 'email' },
    { title: '部门', dataIndex: 'department' },
    { title: '状态', dataIndex: 'status', render: (value: string) => <Tag className="status-tag">{statuses.get(value) ?? value}</Tag> },
    { title: '创建时间', dataIndex: 'createdAt' },
    { title: '操作', key: 'actions', render: (_: unknown, row: UserRow) => <Space>
      <Button onClick={() => openEditor(row)}>编辑</Button>
      {row.canDelete && <Popconfirm title="确认删除该用户？" onConfirm={() => remove(row.id)}><Button danger>删除</Button></Popconfirm>}
    </Space> },
  ]
  return <>
    <UserListLayout title="用户管理" rows={rows} columns={columns} loading={loading}
      error={error ? <Alert type="error" message={error} action={<Button onClick={() => setRevision(value => value + 1)}>重试</Button>} /> : undefined}
      filters={<Space wrap>
        <Input.Search aria-label="用户名或邮箱" placeholder="用户名或邮箱" onSearch={searchText => setQuery(value => ({ ...value, searchText, page: 1 }))} />
        <Select aria-label="部门" placeholder="部门" allowClear options={dict.departments} value={query.department} onChange={(department?: string) => setQuery(value => ({ ...value, department, page: 1 }))} />
        <Select aria-label="状态" placeholder="状态" allowClear options={dict.statuses} value={query.status} onChange={(status?: string) => setQuery(value => ({ ...value, status, page: 1 }))} />
      </Space>}
      actions={<Button type="primary" onClick={() => openEditor(null)}>新增用户</Button>}
      pagination={{ current: query.page, pageSize: query.pageSize, total, onChange: (page, pageSize) => setQuery(value => ({ ...value, page, pageSize })) }} />
    <Modal title={editing ? '编辑用户' : '新增用户'} open={editing !== undefined} confirmLoading={saving} onOk={save} onCancel={() => { if (!saving) setEditing(undefined) }}>
      <Form form={form} layout="vertical">
        <Form.Item name="userName" label="用户名" rules={[{ required: true, whitespace: true }]}><Input /></Form.Item>
        <Form.Item name="email" label="邮箱" rules={[{ required: true }, { type: 'email' }]}><Input /></Form.Item>
      </Form>
    </Modal>
  </>
}
