// ============================================================================
// React 标签页模板 —— 路由配置（React Router v6 嵌套路由）
//
// 用途：为标签页容器与各子页面注册嵌套路由。
// 配套：同目录 index.tsx（容器组件）、TabContent.tsx（子页面内容）
// 注意：下方 import 的布局组件路径需指向目标项目实际的布局组件位置。
// ============================================================================

import { createBrowserRouter, Navigate } from 'react-router-dom'
import NavigationLayout from '../components/layouts/NavigationLayout'
import UserManagementTabs from '../views/UserManagement/UserManagementTabs'
import UserManagementUser from '../views/UserManagement/UserManagement-User'
import UserManagementRole from '../views/UserManagement/UserManagement-Role'
import UserManagementPermission from '../views/UserManagement/UserManagement-Permission'

const router = createBrowserRouter([
  {
    path: '/',
    element: <NavigationLayout pageName="企业数据管理平台" breadcrumbs={[]} />,
    children: [
      // 用户管理垂直标签页模块
      {
        path: 'user-management',
        element: <UserManagementTabs />,
        children: [
          {
            index: true,
            element: <Navigate to="/user-management/user" replace />
          },
          {
            path: 'user',
            element: <UserManagementUser />,
            handle: { 
              title: '用户管理', 
              breadcrumb: ['系统管理', '用户权限管理', '用户管理'] 
            }
          },
          {
            path: 'role',
            element: <UserManagementRole />,
            handle: { 
              title: '角色管理', 
              breadcrumb: ['系统管理', '用户权限管理', '角色管理'] 
            }
          },
          {
            path: 'permission',
            element: <UserManagementPermission />,
            handle: { 
              title: '权限管理', 
              breadcrumb: ['系统管理', '用户权限管理', '权限管理'] 
            }
          }
        ]
      }
    ]
  }
])
