import type { ReactNode } from 'react'
import { Table, Typography } from 'antd'
import type { TableProps } from 'antd'
import type { UserRow } from './UserManagement'
interface Props {
  title: string; rows: UserRow[]; columns: TableProps<UserRow>['columns']; loading: boolean
  filters: ReactNode; actions: ReactNode; error?: ReactNode; pagination: TableProps<UserRow>['pagination']
}
export default function UserListLayout(props: Props) {
  return <section className="user-management-page">
    <header className="page-header"><Typography.Title level={2}>{props.title}</Typography.Title>{props.actions}</header>
    {props.error}<div className="filter-bar">{props.filters}</div>
    <Table<UserRow> rowKey="id" dataSource={props.rows} columns={props.columns} loading={props.loading} pagination={props.pagination} />
  </section>
}
