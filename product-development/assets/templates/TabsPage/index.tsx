// ============================================================================
// React 标签页模板 —— 容器组件（Ant Design + React Router v6）
//
// 用途：父路由渲染本容器，子路由渲染各标签页内容组件。
// 配套：同目录 routes.tsx（路由配置）、TabContent.tsx（子页面内容）
// ============================================================================
import React from 'react'
import { UserOutlined, SafetyOutlined, KeyOutlined } from '@ant-design/icons'
import VerticalTabsPageLayout from '../../components/layouts/VerticalTabsPageLayout'
import type { VerticalIconMenuItem } from '../../components/common/VerticalIconMenu'

const UserManagementTabs: React.FC = () => {
  // 标签页菜单配置
  const menuItems: VerticalIconMenuItem[] = [
    {
      key: '/user-management/user',
      icon: <UserOutlined />,
      label: '用户管理'
    },
    {
      key: '/user-management/role',
      icon: <SafetyOutlined />,
      label: '角色管理'
    },
    {
      key: '/user-management/permission',
      icon: <KeyOutlined />,
      label: '权限管理'
    }
  ]

  return (
    <VerticalTabsPageLayout 
      menuItems={menuItems}
      menuWidth={60}
      menuBackgroundColor="#fafafa"
      contentPadding="24px"
      contentMargin="16px 16px 16px 0"
      contentBorderRadius="0 6px 6px 0"
      contentBoxShadow="2px 2px 8px rgba(0,0,0,0.06)"
    />
  )
}

export default UserManagementTabs
