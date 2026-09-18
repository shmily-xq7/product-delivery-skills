# Vue 3 + Element Plus Profile

用于新建 Vue 项目，或目标项目已经采用 Vue 3、Vue Router 4、Pinia、Vite、Element Plus。

先读取 `../common-development-contract.md` 和 `../page-patterns/README.md`，再按页面任务读取命中的模式文件。本文件只补充 Vue 3 实现约束。

## 默认技术组合

- Vue 3 + TypeScript + Composition API
- Vite
- Vue Router 4
- Pinia（需要全局客户端状态时）
- Element Plus
- Axios 或项目既有请求层

不因为模板引入第二套组件库或新的状态管理框架。

## 目录与命名

沿用项目既有目录；没有约定时使用：

```text
src/
├── views/<ModuleName>/
├── components/common/
├── api/
├── stores/
└── router/
```

- 页面与组件：`PascalCase.vue`
- composable：`useXxx.ts`
- store：`useXxxStore.ts`
- API 和工具：`camelCase.ts`

## 列表页

- 使用 `assets/templates/vue3/UserManagement.vue`。
- `script setup` 中声明 Props 和 Emits 类型；服务端状态优先由项目既有请求层管理。
- 筛选、分页、排序和导出共享同一查询模型；不得在组件内写演示数据。

## 标签页

- 使用 `assets/templates/vue3/TabsPage.vue`。
- route name 是标签状态的唯一来源；标签切换通过 router push/replace。
- 权限和面包屑使用 route meta 或项目既有路由协议。

## 验证

执行 `vue-tsc`、ESLint、组件测试、构建和 Playwright，具体命令以项目配置为准。至少验证列表查询、分页、表单提交、路由切换、错误态和权限显隐。
