# Product Delivery Skills

一套面向 AI 编程与办公智能体的产品交付 Skill 集合。覆盖需求确认、产品设计、技术架构、模块设计、开发、E2E 测试、问题诊断和结项，并通过 AC、来源指纹和运行证据保持各阶段可追溯。

支持 Claude Code、Codex、WorkBuddy、千问办公、TRAE Work、TraeCode CLI、DSH，以及任意兼容 `<skill-name>/SKILL.md` 的目录。

## 核心能力

- **阶段化交付**：每个阶段有明确的输入、产物和完成条件。
- **AC 追溯**：产品设计定义 AC，模块设计承接 AC，测试结果验证 AC。
- **来源检查**：上游变化后识别需要复核的下游产物。
- **运行证据**：保存类型检查、Lint、后端测试和 E2E 报告。
- **按范围结项**：支持只交付产品设计、交付到模块或完成全链。

默认开发基线为 React 18 + TypeScript + Ant Design、FastAPI + SQLAlchemy + PostgreSQL。已有项目可通过 `product-workflow.json` 使用自己的路径、技术栈和检查命令。

## 工作流

```text
需求沟通与确认
      │
      ▼
原始需求 → 产品设计 → 功能架构 → 模块设计 → 代码开发 → E2E 测试 → 结项
                              │
                              └─ 失败 → 只读诊断 → 回到对应阶段修复

横向能力：UI 规范 · 页面原型 · 交付图表 · 文档转换
```

## Skill 清单

| 类型 | Skill | 职责 |
|---|---|---|
| 阶段 ⓪ | `product-requirement` | 需求访谈、澄清、确认并形成需求基线 |
| 阶段 ① | `product-design` | 业务流程、页面、字段、交互和 AC |
| 阶段 ② | `product-architecture` | 技术选型、系统架构、数据模型和组件树 |
| 阶段 ③ | `product-module-design` | 模块前后端、DDL、API 和测试详细设计 |
| 阶段 ④ | `product-development` | 按详细设计实现前后端代码 |
| 阶段 ⑤ | `product-e2e-test` | 编写 Playwright 用例并验证 AC |
| 阶段 ⑥ | `product-diagnosis` | 只读定位流程断点和失败根因 |
| 阶段 ⑦ | `product-workflow` | 流程编排、来源检查和结项判断 |
| 横向 | `product-ui-spec` | B 端 UI、双主题 Token 和组件规范 |
| 横向 | `product-prototype` | ASCII 线框、HTML 原型和页面复刻 |
| 横向 | `product-diagram` | Mermaid 绘图、SVG/HTML 导出和陈旧检查 |
| 横向 | `product-doc-convert` | DOCX、Markdown 和 Excel 格式转换 |

## 安装

### 环境要求

- Git
- Python 3.9+
- Node.js 20+
- npm
- 首次安装可访问 npm registry

### 获取项目

```bash
git clone https://github.com/shmily-xq7/product-delivery-skills.git
cd product-delivery-skills
```

### 选择客户端

```bash
# 查看客户端、目标目录和检测状态
bash install.sh --list-apps

# 预览安装位置
bash install.sh --app codex --dry-run

# 执行安装
bash install.sh --app codex
```

安装完成后，重新打开对应智能体的会话。

### 支持的客户端

| 客户端 | `--app` | 默认目录 | 覆盖变量 |
|---|---|---|---|
| Claude Code | `claude-code` | `~/.claude/skills` | `CLAUDE_SKILLS_DIR` |
| Codex | `codex` | `~/.agents/skills` | `AGENT_SKILLS_DIR` |
| WorkBuddy | `workbuddy` | `~/.workbuddy/skills` | `WORKBUDDY_SKILLS_DIR` |
| 千问办公 / QwenWork | `qwen-office` | `~/.qwenwork/skills` | `QWENWORK_SKILLS_DIR` |
| TRAE Work / TRAE CN | `trae-work` | `~/.trae-cn/skills` | `TRAE_SKILLS_DIR` |
| TraeCode CLI | `trae-cli` | `~/.traecli/skills` | `TRAECLI_SKILLS_DIR` |
| DeepSeek Harness / DSH | `dsh` | `${DSH_HOME:-~/.dsh}/skills` | `DSH_SKILLS_DIR` |
| Codex（`.codex` 目录） | `codex-legacy` | `${CODEX_HOME:-~/.codex}/skills` | `CODEX_SKILLS_DIR` |

`codex-legacy` 用于明确安装到 `~/.codex/skills`。为避免与 `codex` 对应的目录重复安装，`--all-detected` 不会自动选择它；需要使用该目录时，请手动指定 `--app codex-legacy`。

### 其他安装方式

```bash
# 安装到多个客户端
bash install.sh --app claude-code --app codex --app workbuddy

# 安装到检测到的全部客户端
bash install.sh --all-detected --dry-run
bash install.sh --all-detected

# 安装到自定义目录
bash install.sh --target /path/to/skills

# 生成 12 个可单独导入的 ZIP
bash install.sh --export-packages ./dist/client-import
```

每个 ZIP 均可单独导入。更新时拉取新代码并重新执行原安装命令。

## 使用

安装后直接用自然语言描述任务。

```text
# 完整流程
请为这个项目走完整的产品交付流程。

# 单个阶段
根据原始需求写产品设计文档。
根据产品设计文档完成功能架构设计。
为用户管理模块编写详细设计。
按照模块详细设计实现代码。
为这些 AC 编写 Playwright E2E 用例。

# 横向能力
为这个后台页面制定深浅主题规范。
把产品设计中的页面画成 ASCII 线框图。
把架构图导出为 SVG 和本地 HTML。
检查上游修改后哪些图表需要重新生成。
把这份 DOCX 转成 Markdown。

# 诊断与结项
诊断为什么产品设计阶段检查没有通过。
检查哪些产物已经过期。
生成项目交付清单。
```

需求澄清报告需要用户确认，确认后的需求基线才进入产品设计。已有完整且经认可的书面需求时，可以直接进入产品设计。

### 交付范围

在 `原始需求.md` 顶部声明：

```text
交付范围：产品设计
```

可选值：`产品设计`、`设计到模块`、`全链`。未声明时按 `全链` 处理。

### 检查与结项

工作流可以检查上下游产物是否一致、记录当前测试证据，并按交付范围生成结项清单。结构检查只能证明文件和引用关系符合规则，不能代替业务评审或真实测试。

具体命令与判断规则见 [`product-workflow/SKILL.md`](product-workflow/SKILL.md) 和 [`verification-contract.md`](product-workflow/references/verification-contract.md)。

## 许可证

本项目采用 [MIT License](LICENSE)。
