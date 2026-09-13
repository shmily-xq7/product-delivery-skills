---
name: product-ui-spec
description: "B 端后台 / 工作台 / 管理端界面设计规范（可独立于产品设计流程使用）。提供浅色/深色双主题 token 全表（色板、语义色、间距 8pt、圆角、字号字重、层级、阴影、字体栈）、布局骨架（侧栏+顶栏+内容区）、组件视觉与交互规格（表格/表单/弹窗/抽屉/标签/分页/反馈）、五态交互约定、命名约定与 RBAC 权限内建规则。触发词：设计后台界面、后台设计系统、双主题、深色浅色、配色 token、数据表格规范、弹窗表单规范、RBAC 权限矩阵、视觉规格。不负责业务流程与字段设计（那是产品设计）。"
metadata:
  version: "1.3.0"
  agent_created: true
---

# B 端后台界面设计规范

> 定位：**视觉与交互口径的唯一事实源**。产品设计文档、模块详细设计、前端代码在涉及配色/间距/组件形态时都引用此处，不得各自另立一套。
> 技术栈对齐：React + **Ant Design** 主线（本规范可映射到 AntD 的 ConfigProvider theme token）。

## 1. 何时使用

- 设计/规范一个后台管理界面、运营工作台、管理端控制台。
- 要定配色 token、双主题（浅/深）方案。
- 要规范数据表格、筛选栏、表单、弹窗、标签、分页、反馈组件的视觉与交互。
- 要设计 RBAC 权限在界面上的呈现方式。
- 产品设计文档/详细设计里需要写"视觉规格"章节时。

**不适用**：营销落地页、移动端 C 端应用（布局与信息密度规则完全不同）。

## 2. Token 体系（单一事实源）

完整可运行版本见 `references/tokens.css`（直接 `<link>` 或用 Vite 引入即可）。两套主题**共用同一组变量名**，只在取值上不同。

### 2.1 语义色

| Token | 浅色 | 深色 | 用途 |
|---|---|---|---|
| `--color-primary` | `#2b5cd9` | `#5b83f0` | 主色（品牌蓝） |
| `--color-primary-hover` | `#1f4cc0` | `#7495f3` | 主色 hover |
| `--color-primary-subtle` | `#eef2fd` | `rgba(91,131,240,.14)` | 主色浅底 |
| `--color-success` | `#1f9d55` | `#34b364` | 成功 |
| `--color-warning` | `#b8791a` | `#d9a03a` | 警告 |
| `--color-error` | `#d64545` | `#e2646a` | 危险 / 错误 |
| `--color-info` | **= 主色** | **= 主色** | 信息（写作 `var(--color-primary)`，是主色的**别名**） |
| `--color-neutral` | `#646a73` | `#a1a7b3` | 中性 / 次要 |

语义色每组三支成对出现：**前景**（`--color-x`）、**浅底**（`--color-x-subtle`）、**描边**（`--color-x-border`）。做状态标签、提示条、告警卡片时三支一起用，不要只取前景色去调透明度。

> **`--color-info` 是主色的别名**：它的三支写作 `var(--color-primary)` / `var(--color-primary-subtle)` / `var(--color-primary-border)`。这样换品牌色时 info 自动跟随，**不需要单独维护**；若某天确实需要信息色独立于品牌色，把这三支的 `var()` 换回字面色值即可。

### 2.2 背景与表面

| Token | 浅色 | 深色 | 用途 |
|---|---|---|---|
| `--color-bg` | `#f6f7f9` | `#16181d` | 页面背景 |
| `--color-bg-sunken` | `#eef0f3` | `#111317` | 凹陷区（代码块、只读区） |
| `--color-surface` | `#ffffff` | `#1e2126` | 卡片 / 面板 |
| `--color-surface-hover` | `#fafbfc` | `#242830` | 表面 hover |
| `--color-border` | `#e3e6ea` | `#333740` | 常规描边 |
| `--color-border-strong` | `#cfd4db` | `#454a55` | 强调描边（输入框 hover） |

### 2.3 文字

| Token | 浅色 | 深色 | 用途 |
|---|---|---|---|
| `--color-text-primary` | `#1f2329` | `#e8eaed` | 主文字 |
| `--color-text-secondary` | `#646a73` | `#a1a7b3` | 次要文字 / 表格辅助列 |
| `--color-text-tertiary` | `#8f959e` | `#737a86` | 辅助 / 占位 |
| `--color-text-disabled` | `#bbbfc4` | `#4d525b` | 禁用 |

### 2.4 间距（4px 基准，布局节奏取 8 的倍数）

`--space-2/4/8/12/16/20/24/32/40/48/64` = `2/4/8/12/16/20/24/32/40/48/64px`

**常用语义**：卡片内边距 16–24；表格单元格垂直 12、水平 16；表单控件间距 16；按钮组间距 8；区块之间 24–32。

### 2.5 圆角 / 字号 / 层级 / 阴影

- 圆角：`--radius-sm:4` `--radius-md:6` `--radius-lg:10` `--radius-xl:16` `--radius-pill:999`
  - 控件（按钮/输入框）6；卡片 10；弹窗 16；标签用 pill。
- 字号：12 / 13 / 14(正文) / 16 / 20 / 24 / 32；标题用 600，正文 400。
- 层级：`--z-sticky:10` `--z-topbar:20` `--z-dropdown:100` `--z-modal:1000` `--z-toast:1100` `--z-tooltip:1200`
- 阴影：`--shadow-sm`（卡片）/ `--shadow-md`（下拉）/ `--shadow-lg`（弹窗）；`--shadow-focus` 用于聚焦环。

### 2.6 字体栈

- 中文 `--font-cn`：`PingFang SC → Microsoft YaHei → Hiragino Sans GB → sans-serif`
- 西文 `--font-en`：`Inter → system-ui`
- 等宽 `--font-mono`：`JetBrains Mono → ui-monospace`（编号、代码、ID）

### 2.7 改品牌色

只覆盖 **5 支**：`--color-primary` / `-hover` / `-active` / `-subtle` / `-border`（浅深主题各一份，共 10 处取值）。

- `--color-info*` **不用改** —— 它已是 `var(--color-primary*)` 的别名，会自动跟随。
- **不要**去改语义色的结构（增删语义色会让组件规格与状态映射失配）。

## 3. 布局骨架（三段式）

```
+--------------+-----------------------------------------------------+
|              | 顶栏 56px: 面包屑 / 搜索 / 用户 / 主题切换          |
|              +-----------------------------------------------------+
| 侧边导航     |                                                     |
| 232px        | 内容区 padding 24px                                 |
| (可折叠      | 56px)                                               |
|              |  +-----------------------------------------------+  |
|              |  | 页头 48px: 标题 + 操作按钮                    |  |
|              |  +-----------------------------------------------+  |
|              |  | 筛选栏(可选)                                  |  |
|              |  +-----------------------------------------------+  |
|              |  | 数据表格 / 表单                               |  |
|              |  +-----------------------------------------------+  |
|              |  | 分页                                          |  |
|              |  +-----------------------------------------------+  |
|              |                                                     |
+--------------+-----------------------------------------------------+
```

> 本图是页面线框图，故用 ASCII 字符绘制（见 `product-prototype/references/ascii-ui-generator.md`）；文件树/流程示意才允许用 `│ ├ └`。

| Token | 值 | 说明 |
|---|---|---|
| `--shell-side-width` | 232px | 侧栏展开 |
| `--shell-side-collapsed` | 56px | 侧栏折叠（仅图标） |
| `--shell-top-height` | 56px | 顶栏 |
| `--content-padding` | 24px | 内容区内边距 |
| `--page-header-height` | 48px | 页头 |
| `--row-height` | 48px | 表格行高（紧凑 36px） |

**侧栏**：业务域分组、当前项高亮、可折叠、支持二级展开。底部放折叠按钮。
**顶栏**：面包屑（反映当前层级）+ 全局搜索 + 主题切换 + 用户菜单。
**路由组织**：按业务域分组；列表页懒加载；详情/编辑用路由参数 `:id`。

## 4. 组件规格

统一命名：`<type>-<variant>`（如 `btn-primary`、`tag-success`、`modal-lg`）。

**基础**：Button（primary / secondary / ghost / danger；高 32 常规 / 40 强调）、Input、Select、Tag（success / warning / error / info / neutral，可带圆点）、Card、Switch、Avatar、Tooltip。

**数据展示**
- **Table**：吸顶表头、多列排序、行选 / 全选、行操作列、密度切换（常规 48 / 紧凑 36）、空态、骨架屏、列宽遵循内容与固定列策略
- **Filter Bar**：筛选条件一行内收拢，超过 3 项用「展开更多」；已选条件可单独清除；有「查询」「重置」
- **Pagination**：页大小可切、显示总数、支持跳页
- **Status Tag**：状态 → 语义色固定映射，同一状态全局同色

**数据录入**
- **Form**：两列栅格（窄屏单列）、必填星标、失焦即时校验、错误态在控件下方、提交按钮 loading、禁用/只读区分
- 控件：Input、Select、DatePicker、Textarea、Radio/Segmented、Upload

**反馈浮层**
- **Modal**：sm 480 / md 640 / lg 880；关闭方式 × / 取消 / 点遮罩 / Esc（危险操作**禁止**点遮罩关闭）
- **Drawer**：右侧 480–720，用于详情与编辑，避免长表单塞进 Modal
- **Toast**：success / info / warning / error，自动消失（error 停留更久）
- **Dropdown**：外部点击 / Esc 关闭
- **Empty / Skeleton**：列表与图表的默认空态与加载态

## 5. 交互与五态

**每个可交互组件必须支持五态**：`default / hover / active / disabled / loading`。

- 聚焦环：`box-shadow: var(--shadow-focus)`（不要用 outline 硬画）
- 按钮 active 需有位移或色深反馈
- **图标系统**：统一线性图标，24px viewBox，`stroke-width: 1.8`，`stroke: currentColor`（自动继承语义色、天然主题安全）；小尺寸 18px / 14px。**禁止用 emoji 充当图标**。

## 6. 命名约定

| 对象 | 规范 | 示例 |
|---|---|---|
| Design token | kebab-case CSS 变量 | `--color-primary-hover` |
| 组件 class | `<type>-<variant>` | `btn-primary`、`modal-lg` |
| 权限点 | `<域>/<资源>:<动作>` | `license/cert:read`、`audit/log:export` |
| 路由 | 同上，与权限点一一对应 | `user/role:write` |

**跨主题约束**：变量名在两套主题中必须**完全一致**，只允许取值不同。

## 7. RBAC 权限的界面呈现

权限矩阵示例（`●` 已授予，空白未授予）：

| 角色 | 读 | 写 | 审 | 管 |
|---|---|---|---|---|
| 超级管理员 | ● | ● | ● | ● |
| 管理员 | ● | ● | ● | — |
| 运营 | ● | ● | — | — |
| 访客 | ● | — | — | — |

**内建规则**：无写权限 → 隐藏「新建 / 编辑 / 删除」；无审权限 → 隐藏「审核」。**隐藏而非置灰**（置灰会暴露功能存在性，视安全要求而定，需与产品明确）。

## 8. 完成前自检清单

- [ ] 所有颜色都来自 token，无硬编码色值
- [ ] 浅/深两套主题下都实际看过一遍，文字对比度可读
- [ ] 间距取值来自间距刻度，无随手魔法数字
- [ ] 每个可交互组件五态齐全
- [ ] 图标统一线性风格，无 emoji
- [ ] 表格列宽、行高符合规格；空态与骨架屏已实现
- [ ] 弹窗关闭方式符合危险操作例外规则
- [ ] 权限点命名与路由一一对应，无权限的操作已按规则处理

## 9. references 索引

| 文件 | 内容 |
|---|---|
| `references/tokens.css` | **可直接使用的双主题 token 全量 CSS**（单一事实源） |
| `references/ui-design-spec.md` | B 端 UI 设计专家提示词原文（设计原则、视觉规范、组件视觉规格、设计流程） |

**关于 token 层的说明**：本规范的双主题 token 为**独立设计**，不依赖任何第三方设计系统的数值，可整体迁移或直接用于新项目。如需更换品牌色，按 §2.7 覆盖品牌变量（含 border，浅深主题分别设置）；**不要改动语义色的结构**——语义色一旦增删，组件规格与状态映射会全部失效。

**外部依赖**（同族 skill）
- `product-design` / `product-module-design` —— 引用本规范写"视觉规格"章节
- `product-development` —— 用 AntD `ConfigProvider` 映射本 token
