<template>
  <section class="user-management">
    <el-form :inline="true" :model="filters" @submit.prevent="submitQuery">
      <el-form-item label="用户名"><el-input v-model.trim="filters.username" clearable /></el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" clearable>
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit">查询</el-button>
        <el-button @click="resetQuery">重置</el-button>
        <el-button v-if="canWrite" type="primary" @click="emit('create')">新增用户</el-button>
      </el-form-item>
    </el-form>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <el-table v-loading="loading" :data="rows" row-key="id" empty-text="暂无数据">
      <el-table-column prop="username" label="用户名" min-width="160" />
      <el-table-column prop="displayName" label="姓名" min-width="140" />
      <el-table-column prop="statusLabel" label="状态" width="120" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button link @click="emit('view', scope.row)">查看</el-button>
          <el-button v-if="canWrite" link @click="emit('edit', scope.row)">编辑</el-button>
          <el-button v-if="canWrite" link type="danger" @click="emit('delete', scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      :current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next, sizes"
      @current-change="emit('page-change', $event)"
      @size-change="emit('page-size-change', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

type Option = { label: string; value: string }
type UserRow = { id: string; username: string; displayName: string; statusLabel: string }

defineProps<{
  rows: UserRow[]
  statusOptions: Option[]
  loading?: boolean
  error?: string
  page: number
  pageSize: number
  total: number
  canWrite?: boolean
}>()

const emit = defineEmits<{
  (event: 'query', filters: { username: string; status: string }): void
  (event: 'create'): void
  (event: 'view' | 'edit' | 'delete', row: UserRow): void
  (event: 'page-change' | 'page-size-change', value: number): void
}>()

const filters = reactive({ username: '', status: '' })
const submitQuery = () => emit('query', { ...filters })
const resetQuery = () => {
  filters.username = ''
  filters.status = ''
  submitQuery()
}
</script>

<style scoped>
.el-pagination { margin-top: 16px; justify-content: flex-end; }
</style>
