# Vue 2 + Element UI Profile

只用于维护既有 Vue 2 项目。新建 Vue 项目使用 Vue 3 profile；不要为了套用模板把既有 Vue 2 项目强制迁移。

先读取 `../common-development-contract.md` 和 `../page-patterns/README.md`，再按页面任务读取命中的模式文件。本文件只补充 Vue 2 实现约束。

## 识别与版本约束

- `package.json` 含 Vue 2、Vue Router 3、Vuex 3 或 Element UI。
- `vue` 与 `vue-template-compiler` 必须使用完全一致的版本。
- 不混入 Vue 3 的 `@vue/compiler-sfc`、Vue Router 4、Pinia 或 Element Plus，除非正在执行一项明确的迁移任务。

## 目录与命名

沿用项目既有目录；没有约定时使用：

```text
src/
├── views/<ModuleName>/
├── components/common/
├── api/
├── store/modules/
└── router/
```

- 页面与组件：`PascalCase.vue`
- API/工具模块：`camelCase.js` 或项目既有 TypeScript 约定
- 路由 name：稳定 PascalCase；权限点和后端资源保持一一对应

## 列表页

- 使用 `assets/templates/vue2/UserManagement.vue` 作为无模拟数据骨架。
- Props 承接真实 rows、loading、total 和分页；查询、翻页、增删改通过事件交给容器或 service。
- 自定义单元格使用 scoped slot；不要复制一套新的表格布局组件。

## 标签页

- 使用 `assets/templates/vue2/TabsPage.vue`。
- 标签选择由路由驱动，避免同时维护 route 和本地选中状态。
- 子页面通过嵌套路由或现有项目约定装载；面包屑读取 route meta。

## 验证

执行项目已有的 lint、单元测试、构建和 Playwright。至少验证列表查询、分页、弹窗提交、路由切换和权限显隐。构建成功不能代替业务 AC 验证。
