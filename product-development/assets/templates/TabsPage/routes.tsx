import { createBrowserRouter, Navigate } from 'react-router-dom'
import type { UserService } from '../UserManagement'
import UserManagementTabs from './index'
import TabContent from './TabContent'
// Construct once at the application entrypoint; service identity should remain stable.
export function createUserRouter(service: UserService) {
  return createBrowserRouter([
    { path: '/', element: <Navigate to="/user-management/user" replace /> },
    { path: '/user-management', element: <UserManagementTabs />, children: [
      { index: true, element: <Navigate to="user" replace /> },
      { path: 'user', element: <TabContent service={service} /> },
    ] },
  ])
}
