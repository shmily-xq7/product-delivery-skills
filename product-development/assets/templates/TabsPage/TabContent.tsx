// ============================================================================
// React 标签页模板 —— 子页面内容组件
//
// 用途：单个标签页的内容实现；每个标签页复制一份并按业务改写。
// 配套：同目录 index.tsx（容器组件）、routes.tsx（路由配置）
// ============================================================================
import React, { useState, useCallback } from 'react'
import FilterBarTablePageLayout from '../../components/layouts/FilterBarTablePageLayout'
import type { SearchItem, ActionButton, TableColumn } from '../../types'

const UserManagementUser: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [tableData, setTableData] = useState<any[]>([])

  // 搜索配置
  const searchItems: SearchItem[] = [
    { type: 'input', label: '用户名', prop: 'username', placeholder: '请输入用户名' },
    { 
      type: 'select', 
      label: '状态', 
      prop: 'status', 
      placeholder: '请选择状态',
      options: [
        { label: '启用', value: 'active' },
        { label: '禁用', value: 'inactive' }
      ]
    }
  ]

  // 操作按钮配置
  const actionButtons: ActionButton[] = [
    { name: 'add', label: '新增用户', type: 'primary' },
    { name: 'export', label: '导出数据', type: 'default' }
  ]

  // 表格列配置
  const tableColumns: TableColumn[] = [
    { prop: 'username', label: '用户名', minWidth: 150 },
    { prop: 'realName', label: '真实姓名', width: 120 },
    { prop: 'department', label: '部门', width: 150 },
    { prop: 'role', label: '角色', width: 120 },
    { prop: 'status', label: '状态', width: 100 },
    { prop: 'createTime', label: '创建时间', width: 180 }
  ]

  // 事件处理
  const handleSearch = useCallback((formData: Record<string, any>) => {
    console.log('搜索参数:', formData)
    // 执行搜索逻辑
  }, [])

  const handleAction = useCallback((action: string) => {
    console.log('操作:', action)
    // 执行对应操作
  }, [])

  return (
    <FilterBarTablePageLayout
      searchItems={searchItems}
      actionButtons={actionButtons}
      tableColumns={tableColumns}
      tableData={tableData}
      loading={loading}
      onSearch={handleSearch}
      onAction={handleAction}
      showSelection={true}
      showIndex={true}
      showTableAction={true}
    />
  )
}

export default UserManagementUser
