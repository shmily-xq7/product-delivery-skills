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

源码仓库不提交 `node_modules`。安装器会执行 `npm ci`，按 `package-lock.json` 下载并验证 Mermaid 运行依赖。

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
| Codex 旧目录 | `codex-legacy` | `${CODEX_HOME:-~/.codex}/skills` | `CODEX_SKILLS_DIR` |

`codex-legacy` 只用于升级旧安装，不参与自动检测。

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

`product-workflow.zip` 和 `product-diagram.zip` 包含各自的 Mermaid 运行时，可单独导入。更新时拉取新代码并重新执行原安装命令；安装器会备份旧版本并在单个目标失败时回滚。

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

## 默认产物结构

```text
<项目根>/
├── product-workflow.json                    # 可选项目配置
├── 项目战略规划/
│   ├── 需求澄清报告.md
│   └── 原始需求.md
├── 项目战术执行/
│   ├── 00_产品设计文档.md
│   ├── 00_功能架构设计文档.md
│   ├── 01_<模块名>详细设计.md
│   ├── 90_诊断报告_<主题>.md
│   └── 99_交付清单.md
├── frontend/
├── backend/
├── outputs/diagrams/                         # Mermaid、SVG、HTML 和来源清单
└── .product-workflow/                        # 问题台账和运行证据
```

项目配置说明：

- [`project-config.md`](product-workflow/references/project-config.md)
- [`project-config.example.json`](product-workflow/references/project-config.example.json)
- [`verification-contract.md`](product-workflow/references/verification-contract.md)

## 检查与结项

以下示例使用 Codex 默认目录；其他客户端请修改 `SKILLS_DIR`。

```bash
SKILLS_DIR="${AGENT_SKILLS_DIR:-$HOME/.agents/skills}"
PROJECT_ROOT="/path/to/project"

# 检查产物是否陈旧
python3 "$SKILLS_DIR/product-workflow/scripts/check_freshness.py" \
  --project-root "$PROJECT_ROOT"

# 复核后记录来源指纹
python3 "$SKILLS_DIR/product-workflow/scripts/check_freshness.py" \
  --project-root "$PROJECT_ROOT" \
  --stamp 项目战术执行/00_功能架构设计文档.md

# 执行项目检查并保存证据
python3 "$SKILLS_DIR/product-workflow/scripts/run_checks.py" \
  --project-root "$PROJECT_ROOT" \
  --check typecheck lint backend e2e

# 生成结项清单
python3 "$SKILLS_DIR/product-workflow/scripts/check_freshness.py" \
  --project-root "$PROJECT_ROOT" \
  --finalize
```

结构检查只验证文件、格式和引用关系，不能代替业务评审或真实测试。结项命令读取已有证据，不会隐式运行测试。

## 仓库结构

```text
product-delivery-skills/
├── install.sh
├── scripts/install.py
├── release.json
├── product-workflow/
├── product-requirement/
├── product-design/
├── product-architecture/
├── product-module-design/
├── product-development/
├── product-e2e-test/
├── product-diagnosis/
├── product-ui-spec/
├── product-prototype/
├── product-diagram/
├── product-doc-convert/
└── tests/
```

每个 Skill 以 `SKILL.md` 为入口，可包含 `references/`、`scripts/` 和 `assets/`。

## 开发验证

```bash
npm ci --ignore-scripts --prefix product-workflow/validators
python3 -B -m unittest discover -s tests -v
```

参考前端另见 [`product-development/assets/reference-app`](product-development/assets/reference-app)。文档转换的可选依赖见 [`product-doc-convert/SKILL.md`](product-doc-convert/SKILL.md)。

## 许可证

本项目采用 [MIT License](LICENSE)。
