# React + Ant Design Profile

用于新项目默认路线，或目标项目依赖中存在 React 且配置未指定其他框架时。

## 读取顺序

1. `../common-development-contract.md`
2. `../page-patterns/README.md`，再按页面任务读取命中的模式文件
3. `../react-datalist-page.md` 或 `../react-tabs-page.md`
4. `../agent-frontend.md`（需要完整前端角色约束时）

## 资产

- 列表页：`../../assets/templates/UserManagement.tsx`、`UserListLayout.tsx`、`data-list-page.scss`
- 标签页：`../../assets/templates/TabsPage/`
- 可运行示例：`../../assets/reference-app/`

## 推荐检查

以项目自身脚本为准，通常至少包含 TypeScript、ESLint、构建和 Playwright。不要因为本 profile 提供了示例命令而覆盖项目已有命令。
