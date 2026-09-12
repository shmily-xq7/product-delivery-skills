// ============================================================================
// React 列表页整页骨架模板（Ant Design + TypeScript）
//
// 用途：复制到目标项目后，替换列定义 / 接口调用 / 表单字段即可跑通。
// 配套：同目录 data-list-page.scss
// 前提：目标项目需有「筛选栏 + 表格」的布局组件层——即下方 import 的
//       @/components/layouts/* 、@/components/common/* 必须指向其实际位置。
//       若目标项目尚无该层，先按《列表页开发规范》第 2 章补齐，
//       不要在页面组件里内联铺布局。
// ============================================================================

// UserManagement.tsx
import React, { useState, useEffect, useCallback, useMemo } from 'react'
import FilterBarTablePageLayout from '@/components/layouts/FilterBarTablePageLayout'
import DialogWrapper from '@/components/common/DialogWrapper'
import FilterFields from '@/components/common/FilterFields'
import type { SearchItem, ActionButton as ActionButtonType, TableColumn } from '@/types'
import './UserManagement.scss'

const UserManagement: React.FC = () => {
  // 状态管理
  const [loading, setLoading] = useState(false)
  const [tableData, setTableData] = useState<any[]>([])
  const [filters, setFilters] = useState({
    searchText: '',
    selectedUserType: null,
    department: ''
  })
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  })
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [dialogState, setDialogState] = useState({
    visible: false,
    title: '',
    loading: false,
    formData: {} as any,
    currentRow: null as any
  })

  // 页面配置
  const pageTitle = '用户管理'
  
  const searchConfig: SearchItem[] = useMemo(() => [
    { type: 'input', label: '关键字', prop: 'searchText', placeholder: '输入用户名或邮箱' },
    { 
      type: 'select', 
      label: '部门', 
      prop: 'department', 
      placeholder: '请选择部门',
      options: [
        { label: '技术部', value: 'tech' },
        { label: '市场部', value: 'marketing' },
        { label: '人事部', value: 'hr' }
      ]
    }
  ], [])

  const actionButtons: ActionButtonType[] = useMemo(() => [
    { text: '新增用户', action: 'add', type: 'primary' },
    { text: '批量删除', action: 'batchDelete', type: 'danger' },
    { text: '导出', action: 'export', type: 'default' }
  ], [])

  const tableColumns: TableColumn[] = useMemo(() => [
    { prop: 'userName', label: '用户名', minWidth: 120 },
    { prop: 'email', label: '邮箱', minWidth: 200 },
    { prop: 'department', label: '部门', width: 120 },
    { prop: 'status', label: '状态', width: 100, render: 'status' },
    { prop: 'createTime', label: '创建时间', minWidth: 180 }
  ], [])

  const filterFieldsConfig = useMemo(() => ({
    treeData: [
      {
        label: '用户类型',
        value: 'userType',
        children: [
          { label: '管理员', value: 'admin' },
          { label: '普通用户', value: 'user' },
          { label: '访客', value: 'guest' }
        ]
      }
    ]
  }), [])

  // 数据获取
  const fetchData = useCallback(async (params = {}) => {
    setLoading(true)
    try {
      const requestParams = {
        ...filters,
        ...params,
        page: pagination.current,
        pageSize: pagination.pageSize
      }
      
      // const response = await getUserList(requestParams)
      // setTableData(response.data.list)
      // setPagination(prev => ({ ...prev, total: response.data.total }))

      // 模拟数据
      await new Promise(resolve => setTimeout(resolve, 500)) // 模拟加载延迟
      const mockData = Array.from({ length: requestParams.pageSize }, (_, i) => {
        const index = (requestParams.page - 1) * requestParams.pageSize + i + 1
        return {
          id: index,
          userName: `用户${index}`,
          email: `user${index}@example.com`,
          department: ['技术部', '市场部', '人事部'][i % 3],
          status: Math.random() > 0.5 ? 'active' : 'inactive',
          createTime: new Date(Date.now() - Math.random() * 10000000000).toLocaleString(),
          canDelete: Math.random() > 0.7
        }
      })
      
      setTableData(mockData)
      setPagination(prev => ({ ...prev, total: 100 }))
      
    } catch (error) {
      console.error('Failed to load data:', error)
      // 这里应该显示错误消息，实际项目中可使用 message 组件
    } finally {
      setLoading(false)
    }
  }, [filters, pagination.current, pagination.pageSize])

  // 事件处理
  const handleSearch = useCallback((formData: Record<string, any>) => {
    setFilters(prev => ({ ...prev, ...formData }))
    setPagination(prev => ({ ...prev, current: 1 }))
    // fetchData 会在 useEffect 中被调用
  }, [])

  const handleReset = useCallback(() => {
    const resetFilters = {
      searchText: '',
      selectedUserType: null,
      department: ''
    }
    setFilters(resetFilters)
    setPagination(prev => ({ ...prev, current: 1 }))
  }, [])

  const handleFilterChange = useCallback((selectedFilterValues: any) => {
    setFilters(prev => ({ 
      ...prev, 
      selectedUserType: selectedFilterValues.userType 
    }))
    setPagination(prev => ({ ...prev, current: 1 }))
  }, [])

  const handleAction = useCallback((action: string) => {
    console.log('Page action:', action)
    
    switch (action) {
      case 'add':
        setDialogState({
          visible: true,
          title: '新增用户',
          loading: false,
          formData: {},
          currentRow: null
        })
        break
      case 'export':
        exportData()
        break
      case 'batchDelete':
        if (selectedRowKeys.length === 0) {
          alert('请至少选择一项进行批量删除')
          return
        }
        batchDeleteUsers()
        break
      default:
        console.warn('Unknown action:', action)
    }
  }, [selectedRowKeys])

  const handleTableAction = useCallback((action: string, row: any) => {
    console.log('Table action:', action, row)
    // 通过 renderActions 自定义时，通常不会用到此回调
  }, [])

  const handlePagination = useCallback((page: number, size: number) => {
    setPagination(prev => ({ ...prev, current: page, pageSize: size }))
  }, [])

  const handleSelectionChange = useCallback((selectedKeys: React.Key[]) => {
    setSelectedRowKeys(selectedKeys)
  }, [])

  // 业务操作
  const handleEdit = useCallback((row: any) => {
    setDialogState({
      visible: true,
      title: '编辑用户',
      loading: false,
      formData: { ...row },
      currentRow: row
    })
  }, [])

  const handleDelete = useCallback((row: any) => {
    if (window.confirm(`确认删除用户 "${row.userName}"?`)) {
      console.log('Delete user:', row.id)
      // await deleteUser(row.id)
      // 重新加载数据
      fetchData()
    }
  }, [fetchData])

  const exportData = useCallback(() => {
    console.log('Export data with filters:', filters)
    alert('导出功能执行中...')
  }, [filters])

  const batchDeleteUsers = useCallback(() => {
    console.log('Batch delete users:', selectedRowKeys)
    alert(`批量删除 ${selectedRowKeys.length} 个用户`)
  }, [selectedRowKeys])

  const handleDialogConfirm = useCallback(async () => {
    setDialogState(prev => ({ ...prev, loading: true }))
    try {
      // 表单验证和提交逻辑
      console.log('Save user data:', dialogState.formData)
      // await saveUser(dialogState.formData)
      
      setDialogState(prev => ({ ...prev, visible: false, loading: false }))
      fetchData() // 重新加载数据
    } catch (error) {
      console.error('Save failed:', error)
    } finally {
      setDialogState(prev => ({ ...prev, loading: false }))
    }
  }, [dialogState.formData, fetchData])

  const handleDialogCancel = useCallback(() => {
    setDialogState(prev => ({ ...prev, visible: false }))
  }, [])

  // 副作用
  useEffect(() => {
    fetchData()
  }, [filters, pagination.current, pagination.pageSize])

  return (
    <div className="user-management-page">
      <FilterBarTablePageLayout
        title={pageTitle}
        searchItems={searchConfig}
        initialFormData={filters}
        actionButtons={actionButtons}
        tableColumns={tableColumns}
        tableData={tableData}
        loading={loading}
        total={pagination.total}
        current={pagination.current}
        pageSize={pagination.pageSize}
        showSelection={true}
        showIndex={true}
        showTableAction={true}
        actionWidth={120}
        onSearch={handleSearch}
        onReset={handleReset}
        onAction={handleAction}
        onTableAction={handleTableAction}
        onPagination={handlePagination}
        onSelectionChange={handleSelectionChange}
        filterContent={
          <FilterFields 
            fields={filterFieldsConfig}
            value={filters}
            onChange={handleFilterChange}
          />
        }
        renderColumns={{
          status: (value: string, row: any) => (
            <span className={`status-tag ${value === 'active' ? 'status-active' : 'status-inactive'}`}>
              {value === 'active' ? '启用' : '禁用'}
            </span>
          )
        }}
        renderActions={(row: any) => (
          <>
            <button className="action-btn" onClick={() => handleEdit(row)}>
              编辑
            </button>
            {row.canDelete && (
              <button className="action-btn danger" onClick={() => handleDelete(row)}>
                删除
              </button>
            )}
          </>
        )}
      />

      {/* 弹窗组件 */}
      <DialogWrapper
        visible={dialogState.visible}
        title={dialogState.title}
        loading={dialogState.loading}
        onConfirm={handleDialogConfirm}
        onCancel={handleDialogCancel}
      >
        <div className="user-form">
          <div className="form-item">
            <label>用户名：</label>
            <input 
              type="text" 
              value={dialogState.formData.userName || ''} 
              onChange={(e) => setDialogState(prev => ({
                ...prev,
                formData: { ...prev.formData, userName: e.target.value }
              }))}
            />
          </div>
          <div className="form-item">
            <label>邮箱：</label>
            <input 
              type="email" 
              value={dialogState.formData.email || ''} 
              onChange={(e) => setDialogState(prev => ({
                ...prev,
                formData: { ...prev.formData, email: e.target.value }
              }))}
            />
          </div>
        </div>
      </DialogWrapper>
    </div>
  )
}

export default UserManagement
