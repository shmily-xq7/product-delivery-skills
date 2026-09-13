import { Tabs } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
export default function UserManagementTabs() {
  const location = useLocation()
  const navigate = useNavigate()
  return <section style={{ padding: 'var(--content-padding)', background: 'var(--color-surface)' }}>
    <Tabs activeKey={location.pathname} items={[{ key: '/user-management/user', label: '用户管理' }]} onChange={key => navigate(key)} />
    <Outlet />
  </section>
}
