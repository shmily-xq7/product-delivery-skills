---
name: product-development
description: "按模块详细设计写代码——产品交付链路第四阶段。先识别目标项目技术栈，再按需加载 React + AntD、Vue 2 + Element UI（既有项目兼容）或 Vue 3 + Element Plus profile；提供基础模板与后台页面模式目录，并覆盖前后端命名一致性、枚举单一事实源和 FastAPI 后端实现。触发词：按设计写代码、生成页面组件、React/Vue 后台页面、列表页、标签页、权限矩阵、导入导出、对接 API。不负责写设计文档。"
metadata:
  version: "1.5.0"
  agent_created: true
---

# 代码开发（技术栈适配）

> 定位：详细设计 → **可运行代码**。
> 本 skill 同时承担**全族技术栈基线与适配规则的唯一事实源**。共享交付约束见 `references/common-development-contract.md`；框架细节只读取当前项目对应的 profile，不得把多套框架规则混用。

## 0. 先选择一个技术栈 Profile

优先级：`product-workflow.json` 的 `stack.frontend` 明确声明 → 目标前端 `package.json` 依赖识别 → 新项目默认 React。可运行：

```bash
python3 "$SKILLS_DIR/product-development/scripts/detect_stack.py" --project-root /实际项目根
```

| 识别结果 | 读取 | 使用模板 |
|---|---|---|
| `react-antd` | `references/profiles/react-antd.md` | `assets/templates/` 现有 React 模板 |
| `vue2-element` | `references/profiles/vue2-element.md` | `assets/templates/vue2/` |
| `vue3-element-plus` | `references/profiles/vue3-element-plus.md` | `assets/templates/vue3/` |

检测冲突或无法识别时先核对配置，不猜测框架。Vue 2 profile 只用于维护已有 Vue 2 项目；新建 Vue 项目使用 Vue 3 profile。无论选择哪一套，先遵守 `references/common-development-contract.md`。

## 1. 默认技术栈基线（React Profile）

项目根 `product-workflow.json` 的 paths / stack / commands 配置优先；默认值与执行方法见 `product-workflow/references/project-config.md`。复用已有项目技术栈，不能仅为符合示例而迁移项目。下表与紧随其后的目录树只描述默认 React profile；Vue 项目以对应 profile 为准。

| 层 | 选型 | 备注 |
|---|---|---|
| 框架 / 语言 | React 18 + TypeScript | 严格模式；函数组件 + hooks |
| 构建 | Vite | |
| 路由 | React Router v6 | 嵌套路由 + 懒加载 |
| **UI 组件库** | **Ant Design（主线）** | 表格/表单/弹窗/下拉优先直接用 AntD；**不引入 Tailwind，不引入第二套组件库** |
| 可选 UI 替代 | shadcn/ui + Tailwind | 仅在团队明确指定时使用（原 `agent-frontend` 默认写的是 shadcn，此处已统一为 AntD 主线） |
| 样式 | AntD + CSS Modules / SCSS | 间距遵 8pt；视觉 token 取 `product-ui-spec` |
| 状态管理 | Zustand（模块级） / Redux Toolkit（全局） | 服务端状态用 TanStack Query |
| HTTP | Axios（统一拦截器） | |
| 图表 | ECharts（如需要） | Mermaid 仅用于文档，不进代码 |
| 后端 | FastAPI + SQLAlchemy + PostgreSQL | 工程根 `backend/`，源码根 `app/`；服务在 `app/services/<module>/`，API 在 `app/api/v1/` |

**目录约定（单一事实源，其他 skill 一律引用此处）**

```
<项目根>/
├── 项目战略规划/原始需求.md
├── 项目战术执行/                       ← 只放设计文档，不放代码
│   ├── 00_产品设计文档.md
│   ├── 00_功能架构设计文档.md
│   └── <序号>_<模块名>详细设计.md
├── frontend/                           ← 前端工程根
│   └── src/
│       ├── views/<ModuleName>/         ← 业务域目录（PascalCase）
│       │   ├── <Component>.tsx         ← 组件 / 页面文件（PascalCase）
│       │   └── <component>.scss        ← 样式文件（kebab-case）
│       ├── components/  api/  stores/  router/
│   └── tests/e2e/<page-name>.spec.ts   ← E2E 用例（kebab-case）
└── backend/                            ← 后端工程根
    └── app/                            ← 唯一源码根
        ├── api/v1/  core/  models/  schemas/  services/
        └── tests/{unit,integration}/
```

**路径基准**（两者不冲突，是同一路径在不同基准下的写法）：
- **仓库视角**（编排层、产物树用）：`frontend/src/views/…`、`backend/app/…`
- **工程内视角**（前端 / 后端规范正文用）：`src/views/…`、`app/…`

**代码产物落目标工程**：`项目战术执行/` **只放设计文档**，不放任何代码。

**命名约定（硬规则）**

| 对象 | 规范 |
|---|---|
| 对外 API 字段 | `camelCase`（**强制**） |
| DB 列 / 表 | `snake_case` |
| 页面 / 组件文件 | `PascalCase` | `UserManagement.tsx`、`ProjectList.tsx` |
| 业务域目录 | `PascalCase` | `views/UserManagement/` |
| 样式文件 | `kebab-case` | `data-list-page.scss` |
| 工具函数 | `camelCase` | `dateUtils.ts` |
| E2E 用例 | `kebab-case` | `user-management.spec.ts` |
| 后端 Python | Pydantic / SQLAlchemy 蛇形 |

转换只发生在后端序列化层；前端不得反向改写后端命名。

**枚举单一事实源**：枚举与字典值由后端集中定义（如 `app/core/enums.py`）并通过接口下发，前端动态加载后存入全局状态。**禁止前端硬编码枚举**。思路详见 `references/backend-frontend-consistency.md`（该文为参考思路，非强制规范）。

## 1.1 ④ 阶段检查：跑项目自身的工具链，不另造检查器

代码阶段的语言级检查**由项目自己的工具链承担**，本族**不为它写脚本** —— 再写一个 Python 脚本去 grep TS 代码，只会又慢又误报（它读不懂 import、类型标注与 JSX）。选择本次改动受影响的检查；正式交付核对范围内证据。下面命令独立从项目根执行，自定义路径通过 `product-workflow/scripts/run_checks.py` 按配置运行：

```bash
(cd frontend && npx tsc --noEmit)                      # 类型检查：0 error 才算过
(cd frontend && npx eslint src --max-warnings 0)       # lint
(cd frontend && npx playwright test)                   # E2E（规范见 product-e2e-test）
(cd backend && python -m pytest -q)                   # 后端单测 / 集成测试
```

**各检查项对应的承担者**（不要靠人眼目检）：

| 检查项 | 由谁承担 |
|---|---|
| 类型检查 | `tsc --noEmit` |
| lint | `eslint` |
| 命名符合基线（页面/组件 PascalCase、API camelCase、DB snake_case） | eslint `@typescript-eslint/naming-convention` |
| 无硬编码枚举 | eslint 自定义规则；后端由 `app/core/enums.py` 单一事实源约束 |
| 三层验证（前端 / API / DB） | Playwright 用例（见 `product-e2e-test`） |

> **为什么这里没有 `validate_*.py`**：把「命名是否符合 PascalCase」这类**语言级**规则交给 Python 正则，是在错误的地方造轮子。请把规则落到 eslint 配置里一次配好、长期生效。

## 2. 何时使用

- 用户要"按详细设计写代码""生成页面组件""对接 API"。
- 开发 React 或 Vue 列表页（筛选 + 表格 + 分页 + 增删改查 + 弹窗）或标签页（多 Tab 路由布局）。
- 实现 FastAPI 后端接口、SQLAlchemy 模型与迁移。
- 需要判断某个技术选型或命名是否符合基线。

## 2.1 先匹配后台页面模式

普通列表和标签页之外，树表联动、权限矩阵、审计记录、导入导出、动态列、批量处理、详情编辑、嵌入内容等页面存在不同的状态与失败路径。开发前读取 `references/page-patterns/README.md`，按详细设计选择一个或多个模式；只加载命中的参考文件，不能因为页面外观相似而跳过模式契约。

模式选择必须写入本次实现说明，并把所选模式的 `requiredConcerns` 映射到代码与 AC/E2E。机器可读目录位于 `references/page-patterns/catalog.json`，可运行：

```bash
python3 scripts/page_patterns.py list
python3 scripts/page_patterns.py show import-export
python3 scripts/page_patterns.py validate
```

## 3. React 列表页开发流程

参考 `references/react-datalist-page.md`（**完整分步规范**）。核心约定：

**架构原则**：**布局组件中心化，页面组件只专注业务**。通过 Props / 事件 / Render Props 解耦。

| 步 | 动作 |
|---|---|
| 1 | 确定页面结构：筛选区 + 操作按钮区 + 表格 + 分页（+ 弹窗） |
| 2 | 复用布局组件（筛选+表格的整页布局），只在 Props 中声明列定义与按钮 |
| 3 | 配置表格列：**列宽配置有硬规范**（见规范 3.2.1，属 CRITICAL 项），操作按钮配置见 3.2.2 |
| 4 | 绑定事件：查询 / 重置 / 新增 / 编辑 / 删除 / 批量操作 |
| 5 | 自定义渲染：需要非默认单元格时用 Render Props（3.4） |
| 6 | 数据与业务逻辑：请求、分页、loading、错误、空态（3.5） |
| 7 | 弹窗/表单：新增与编辑复用同一弹窗，字段按设计文档的字段字典 |
| 8 | 检查清单：按钮配置、组件最佳实践、TS 类型、性能（第 9 章） |

**可直接复制的骨架**：`assets/templates/UserManagement.tsx` + `UserListLayout.tsx` + `data-list-page.scss`。布局组件随模板提供，仅依赖 React 与 AntD；传入稳定的 `UserService` 实例连接真实 API。部门/状态来自 dictionaries，保存和删除等待真实 Promise 成功后刷新，失败保留错误与输入。按项目契约修改类型和字段，模板中无生产默认模拟数据。

**可运行参考工程**：`assets/reference-app/`。它通过独立的 demo-service 注入明确标识的内存演示数据，只证明 README 中列出的模板挂载、构建与交互行为，不证明真实后端、鉴权或部署可用。以 package-lock.json 固定依赖；进入该目录执行 `npm ci`、`npm run verify`。浏览器测试需要本机 Playwright Chromium。复制生产模板时不要复制 demo-service；应用入口引入 `product-ui-spec/references/tokens.css` 并映射 AntD theme。

## 4. React 标签页开发流程

参考 `references/react-tabs-page.md`（**完整分步规范**）。核心约定：

- 采用**容器 + 子页**模式：容器组件负责 Tab 布局与路由出口，子页面各自独立。
- 路由用嵌套路由（父路由渲染容器，子路由渲染子页面）。
- 图标与菜单项有接口定义（`VerticalIconMenuItem`），配置项与标准值见规范 3.x。
- 文件命名见规范 4.2；模块目录结构见 4.1 的完整步骤。

**可直接复制的模板**：`assets/templates/TabsPage/index.tsx`（容器）、`routes.tsx`（路由工厂，显式传入 service）、`TabContent.tsx`（复用列表子页面）。三者按 templates 原目录结构复制，不再引用未提供的私有布局组件。

> 另注：列表页规范第 11 章还提供了**扁平化多 Tab** 方案（用路由配置实现多 Tab 而非容器组件）。两方案对比见 11.6，选择时优先看目标项目既有约定。

## 5. 后端开发

参考 `references/agent-backend.md`（FastAPI + SQLAlchemy + PostgreSQL 角色定义，含问题排查流程）。

- 目录：`app/services/<module>/`，API 放 `app/api/v1/`（工程根 `backend/`，源码根 `app/`）
- 每个接口对应详细设计里的 API 契约，**不得改字段名**
- 模型层 snake_case，序列化层输出 camelCase
- 迁移与 Docker / Celery / Redis 相关约定见角色文件

## 6. 完成前自检清单

- [ ] 页面结构复用布局组件，未内联铺布局
- [ ] 表格列宽符合规范 3.2.1（CRITICAL）
- [ ] 已确定且只加载一个技术栈 profile；没有把 React、Vue 2、Vue 3 规则混用
- [ ] 已从页面模式目录选择适用模式，并落实其必备状态、失败路径和验证点
- [ ] TypeScript 项目的 props / API 响应 / store 有明确类型；既有 JavaScript 项目有等价契约说明
- [ ] 对外 API 字段 camelCase、DB 列 snake_case，无混用
- [ ] 前端无硬编码枚举（改为后端下发）
- [ ] 样式 token 取自 `product-ui-spec`，未自造色值
- [ ] 未引入 Tailwind 或第二套组件库
- [ ] 类型检查与 lint 通过
- [ ] 空态 / loading / 错误态齐全

## 7. references 与 assets 索引

| 文件 | 内容 |
|---|---|
| `references/react-datalist-page.md` | **列表页开发规范**（布局组件、Props、列宽规范、事件、Render Props、快速开发流程、检查清单、多 Tab 扁平化方案） |
| `references/react-tabs-page.md` | **标签页开发规范**（容器+子页、路由、接口定义、开发步骤、故障排查、检查清单） |
| `references/common-development-contract.md` | 全技术栈共用的设计承接、数据、错误态、权限和验证契约 |
| `references/profiles/react-antd.md` | React + AntD 路由页；索引现有规范、模板和检查命令 |
| `references/profiles/vue2-element.md` | 既有 Vue 2 + Element UI 项目的兼容开发规范 |
| `references/profiles/vue3-element-plus.md` | Vue 3 + TypeScript + Element Plus 开发规范 |
| `references/page-patterns/README.md` | 后台页面模式入口与选择规则 |
| `references/page-patterns/catalog.json` | 10 类后台页面模式的机器可读索引 |
| `references/page-patterns/*.md` | 列表批量、树表权限、审计导入导出、导航嵌入、详情编辑契约 |
| `references/agent-frontend.md` | React 前端工程师角色定义（AntD 主线） |
| `references/agent-backend.md` | 后端工程师角色定义（FastAPI + SQLAlchemy + PG） |
| `references/backend-frontend-consistency.md` | 前后端枚举一致性策略（**参考思路，非强制规范**） |
| `assets/templates/UserManagement.tsx` | 注入真实 service 的列表页骨架 |
| `assets/templates/UserListLayout.tsx` | 随模板提供的 AntD 布局组件 |
| `assets/reference-app/` | 说明验证范围与能力边界的可运行参考工程 |
| `assets/templates/data-list-page.scss` | 列表页配套样式 |
| `assets/templates/TabsPage/index.tsx` | 标签页容器组件模板 |
| `assets/templates/TabsPage/routes.tsx` | 标签页路由配置模板 |
| `assets/templates/TabsPage/TabContent.tsx` | 标签页子页面模板 |
| `assets/templates/vue2/` | Vue 2 列表页与标签页模板（无模拟数据） |
| `assets/templates/vue3/` | Vue 3 列表页与标签页模板（无模拟数据） |
| `scripts/detect_stack.py` | 从项目配置与 package.json 选择唯一 profile |
| `scripts/page_patterns.py` | 列出、查询并校验后台页面模式目录 |

**外部依赖**（同族 skill）
- `product-module-design` —— 上游输入（模块详细设计）
- `product-ui-spec` —— 所有视觉 token
- `product-e2e-test` —— 下游验证
