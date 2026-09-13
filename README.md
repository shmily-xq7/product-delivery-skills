# Product Delivery Skills

一套可安装到多种 AI 编程/办公智能体的产品交付 Skills。它把需求澄清、产品设计、功能架构、模块详细设计、代码开发、E2E 测试、问题诊断和结项检查串成一条可追溯的工作流。

本项目采用开放的 Agent Skills 目录结构，不绑定单一客户端。目前安装器支持 Claude Code、Codex、WorkBuddy、千问办公、TRAE Work、TraeCode CLI 和 DSH，也支持任意自定义 Skills 目录。

## 目录

- [项目解决什么问题](#项目解决什么问题)
- [工作流与 Skill 清单](#工作流与-skill-清单)
- [快速安装](#快速安装)
- [支持的客户端与安装目录](#支持的客户端与安装目录)
- [其他安装方式](#其他安装方式)
- [如何使用](#如何使用)
- [产物目录](#产物目录)
- [项目配置](#项目配置)
- [检查与结项](#检查与结项)
- [仓库结构](#仓库结构)
- [开发与维护](#开发与维护)

## 项目解决什么问题

产品需求进入开发后，经常出现这些问题：需求没有形成确认基线、设计与代码脱节、验收标准没有对应测试、上游修改后下游文档已经过期、测试命令执行过但没有留下可信证据。

本项目通过以下机制处理这些问题：

- **阶段化交付**：每个阶段有明确的输入、输出和完成条件。
- **AC 全链追溯**：产品设计定义 AC，模块设计承接 AC，测试用例引用 AC。
- **阶段检查**：脚本检查文档结构、引用关系和必要产物是否完整。它相当于进入下一阶段前的自动核对，不能代替业务评审。
- **来源指纹**：记录产物依赖的上游内容；上游发生变化时提示哪些下游产物需要复核。
- **运行证据**：保存类型检查、Lint、后端测试和 E2E 测试的日志与报告。
- **交付范围**：支持只交付产品设计、交付到模块设计或完成整条开发测试链路。

默认开发基线是 React 18 + TypeScript + Ant Design、FastAPI + SQLAlchemy + PostgreSQL。已有项目可以通过 `product-workflow.json` 声明自己的路径、技术栈和检查命令，工作流不会为了符合默认示例而强制迁移项目。

## 工作流与 Skill 清单

```text
需求沟通与确认
      │
      ▼
原始需求 → 产品设计 → 功能架构 → 模块详细设计 → 代码开发 → E2E 测试 → 结项清单
                              │
                              └─ 遇到问题 → 只读诊断 → 回到对应阶段修复

横向能力：UI 规范 · 页面原型 · 文档格式转换
```

仓库共包含 11 个 Skill：

| 类型 | Skill | 主要职责 | 主要产物或能力 |
|---|---|---|---|
| 阶段 ⓪ | `product-requirement` | 需求访谈、澄清、分歧对齐和用户确认 | `需求澄清报告.md`、确认后的 `原始需求.md` |
| 阶段 ① | `product-design` | 业务流程、页面、字段、交互和 AC 验收标准 | `00_产品设计文档.md` |
| 阶段 ② | `product-architecture` | 技术选型、系统分层、模块、表定义、ER 图和组件树 | `00_功能架构设计文档.md` |
| 阶段 ③ | `product-module-design` | 单模块前后端、DDL、API 契约和测试详细设计 | `<序号>_<模块名>详细设计.md` |
| 阶段 ④ | `product-development` | 按详细设计实现前端与后端代码 | `frontend/`、`backend/` 中的代码 |
| 阶段 ⑤ | `product-e2e-test` | 编写 Playwright 用例并核对 AC 覆盖 | `frontend/tests/e2e/*.spec.ts` |
| 阶段 ⑥ | `product-diagnosis` | 只读定位流程断点和失败根因 | `90_诊断报告_<主题>.md` |
| 阶段 ⑦ | `product-workflow` | 路由、编排、来源检查和结项判断 | `99_交付清单.md` |
| 横向 | `product-ui-spec` | B 端界面、双主题 Token 和组件规范 | UI 设计规范 |
| 横向 | `product-prototype` | ASCII 线框、单文件 HTML 原型和页面复刻 | 线框图或静态原型 |
| 横向 | `product-doc-convert` | DOCX、Markdown 和 Excel 格式转换 | 本地转换脚本 |

## 快速安装

### 1. 环境要求

- Git
- Python 3.9 或更高版本
- Node.js 20 或更高版本
- npm
- 安装时能够访问 npm registry

仓库不提交 Mermaid 解析器或 `node_modules`。每次安装时，安装器会在目标目录的暂存区运行 `npm ci`，下载 `package-lock.json` 锁定的 Mermaid 语法解析器并完成自检。npm 本地缓存可能减少重复下载量，但不能作为离线安装保证。

### 2. 获取仓库

```bash
git clone https://github.com/shmily-xq7/product-delivery-skills.git
cd product-delivery-skills
```

### 3. 查看可安装客户端

```bash
bash install.sh --list-apps
```

该命令只显示客户端、实际目标目录和检测状态，不会安装任何文件。通常必须通过 `--app`、`--target` 或 `--all-detected` 明确选择目标；只有预先设置了 `AGENT_SKILLS_DIR`、`SKILLS_DIR` 或旧版 `WORKBUDDY_SKILLS_DIR` 时，无参数运行才会把该变量视为用户选择。

### 4. 预览并安装

以 Codex 为例：

```bash
bash install.sh --app codex --dry-run
bash install.sh --app codex
```

把 `codex` 换成下一节中的客户端标识即可。安装完成后，重新打开相应智能体的会话，让客户端重新发现 Skills。

## 支持的客户端与安装目录

以下路径是安装器的默认用户级目标。环境变量的值优先于默认路径。

| 客户端 | `--app` 标识 | 默认目录 | 目录覆盖变量 |
|---|---|---|---|
| Claude Code | `claude-code` | `~/.claude/skills` | `CLAUDE_SKILLS_DIR` |
| Codex | `codex` | `~/.agents/skills` | `AGENT_SKILLS_DIR` |
| WorkBuddy | `workbuddy` | `~/.workbuddy/skills` | `WORKBUDDY_SKILLS_DIR` |
| 千问办公 / QwenWork | `qwen-office` | `~/.qwenwork/skills` | `QWENWORK_SKILLS_DIR` |
| TRAE Work / TRAE CN | `trae-work` | `~/.trae-cn/skills` | `TRAE_SKILLS_DIR` |
| TraeCode CLI | `trae-cli` | `~/.traecli/skills` | `TRAECLI_SKILLS_DIR` |
| DeepSeek Harness / DSH | `dsh` | `${DSH_HOME:-~/.dsh}/skills` | `DSH_SKILLS_DIR`，或通过 `DSH_HOME` 修改根目录 |
| Codex 旧目录 | `codex-legacy` | `${CODEX_HOME:-~/.codex}/skills` | `CODEX_SKILLS_DIR`，或通过 `CODEX_HOME` 修改根目录 |

常用命令示例：

```bash
# 安装到 Claude Code
bash install.sh --app claude-code

# 安装到千问办公
bash install.sh --app qwen-office

# 同时安装到多个客户端
bash install.sh \
  --app claude-code \
  --app codex \
  --app workbuddy \
  --app qwen-office \
  --app trae-work \
  --app trae-cli \
  --app dsh
```

可用别名：`claude`、`qwen`、`qwenwork`、`trae`、`trae-cn`、`traework`、`traecode`、`deepseek-harness`。

`codex-legacy` 仅用于升级仍安装在旧目录中的 Codex Skills，不会被 `--all-detected` 自动选择。

## 其他安装方式

### 安装到本机检测到的全部客户端

先预览，再执行安装：

```bash
bash install.sh --all-detected --dry-run
bash install.sh --all-detected
```

安装器只选择检测到客户端标记目录或配置了对应环境变量的客户端，并按实际路径去重。

### 安装到自定义目录

任何兼容 `<skill-name>/SKILL.md` 结构的客户端或项目都可以指定目标目录：

```bash
bash install.sh --target /path/to/skills
```

`--target` 和 `--app` 都可以重复，也可以组合使用：

```bash
bash install.sh --app codex --target /path/to/project/.agents/skills
```

### 生成客户端界面导入包

部分客户端通过界面导入 ZIP。可以显式生成 11 个独立包：

```bash
bash install.sh --export-packages ./dist/client-import
```

每个 ZIP 的根目录都有 `SKILL.md`。`product-workflow.zip` 会包含安装并自检过的 Mermaid 运行时。导入包只在用户指定的目录中生成，默认不生成，也不纳入源码仓库。

### 没有 Bash 的环境

`install.sh` 只是 Python 安装器的入口。可以直接运行：

```bash
python3 scripts/install.py --list-apps
python3 scripts/install.py --app codex
```

Windows 用户需要确保 `python3`、`node` 和 `npm` 可在当前终端中执行；也可以在 Git Bash 或 WSL 中使用 `install.sh`。

### 更新已安装版本

拉取仓库更新后，对原目标重新运行安装命令：

```bash
git pull
bash install.sh --app codex
```

安装器会先暂存并核验完整 Skill 集合，再替换目标目录。旧版本保存在：

```text
<Skills 根目录>/.product-delivery/backups/<安装运行 ID>/
```

当前安装版本、来源和逐文件 SHA-256 记录在：

```text
<Skills 根目录>/.product-delivery/manifest.json
```

单个目标的替换失败时会尝试回滚。多个目标按顺序分别安装；后一个目标失败不会撤销前面已经成功的目标。

## 如何使用

安装完成并重新打开智能体会话后，直接用自然语言说明任务。智能体会根据 Skill 的描述选择完整工作流或单个阶段。

### 启动完整交付流程

```text
请为这个项目走完整的产品交付流程。
```

如果需求仍然模糊，工作流先进入需求澄清。需求澄清报告必须由用户确认，确认后的基线才会写入 `原始需求.md` 并进入产品设计。

### 只执行一个阶段

```text
根据原始需求写产品设计文档。
根据产品设计文档完成功能架构设计。
为用户管理模块编写详细设计。
按照模块详细设计实现代码。
为这些 AC 编写 Playwright E2E 用例。
```

已有完整且经用户认可的书面需求时，可以直接进入产品设计，不必为了形式重新做需求访谈。

### 使用横向能力

```text
为这个后台页面制定浅色和深色主题规范。
把产品设计中的页面画成 ASCII 线框图。
生成一个单文件 HTML 静态原型。
把这份 DOCX 转成 Markdown。
```

### 诊断与结项

```text
诊断为什么产品设计阶段检查没有通过。
检查上游修改后哪些产物已经过期。
检查这个项目是否具备交付条件并生成交付清单。
```

`product-diagnosis` 是只读诊断角色，只生成或追加诊断报告。实际修复由对应阶段的 Skill 完成。

### 声明交付范围

在 `原始需求.md` 顶部声明本次范围：

```text
交付范围：产品设计
```

可选值：

- `产品设计`：只交付产品设计文档。
- `设计到模块`：交付产品设计、功能架构和模块详细设计。
- `全链`：包含代码实现、测试证据和结项清单。

未声明时按 `全链` 处理。

## 产物目录

默认情况下，工作流在业务项目中使用以下结构：

```text
<业务项目根>/
├── product-workflow.json                    # 可选：项目级配置
├── 项目战略规划/
│   ├── 需求澄清报告.md                      # 阶段 ⓪
│   └── 原始需求.md                          # 用户确认后的需求基线
├── 项目战术执行/
│   ├── 00_产品设计文档.md                   # 阶段 ①
│   ├── 00_功能架构设计文档.md               # 阶段 ②
│   ├── 01_<模块名>详细设计.md               # 阶段 ③，可有多份
│   ├── 90_诊断报告_<主题>.md                 # 阶段 ⑥，按需生成
│   └── 99_交付清单.md                        # 阶段 ⑦，由脚本生成
├── frontend/
│   ├── src/views/<ModuleName>/              # 阶段 ④
│   └── tests/e2e/<page-name>.spec.ts        # 阶段 ⑤
├── backend/app/                              # 阶段 ④
└── .product-workflow/                        # 问题台账和运行证据
```

设计文档集中在 `项目战术执行/`；来源指纹写入对应设计文档的自动元信息块；源代码仍写入业务工程的 `frontend/` 和 `backend/`。不要把实际代码放进设计文档目录。

## 项目配置

业务项目根目录可以创建 `product-workflow.json`，集中覆盖默认路径、技术栈、检查命令、测试扩展名和模块来源范围。不要分别修改各 Skill 中的路径示例。

最小示例：

```json
{
  "schema_version": 1,
  "paths": {
    "requirement": "docs/requirements.md",
    "execution": "docs/design",
    "frontend": "web",
    "backend": "api"
  },
  "commands": {
    "typecheck": {
      "cwd": "web",
      "argv": ["npm", "run", "typecheck"]
    },
    "e2e": {
      "cwd": "web",
      "argv": ["npx", "playwright", "test", "--reporter=junit"],
      "report": "junit"
    }
  }
}
```

完整字段和模块来源切片规则见：

- [`project-config.md`](product-workflow/references/project-config.md)
- [`project-config.example.json`](product-workflow/references/project-config.example.json)
- [`verification-contract.md`](product-workflow/references/verification-contract.md)

## 检查与结项

以下示例假设 Skills 安装在 Codex 的默认目录。其他客户端请把 `SKILLS_DIR` 改成实际安装目录。

```bash
SKILLS_DIR="${AGENT_SKILLS_DIR:-$HOME/.agents/skills}"
PROJECT_ROOT="/path/to/business-project"
```

### 检查产物是否陈旧

```bash
python3 "$SKILLS_DIR/product-workflow/scripts/check_freshness.py" \
  --project-root "$PROJECT_ROOT"
```

### 在复核后记录来源指纹

```bash
python3 "$SKILLS_DIR/product-workflow/scripts/check_freshness.py" \
  --project-root "$PROJECT_ROOT" \
  --stamp 项目战术执行/00_功能架构设计文档.md
```

`--stamp` 表示已经根据当前上游内容复核该产物。它不能代替复核，也不应被用来掩盖未处理的变化。

### 执行项目检查并保存证据

```bash
python3 "$SKILLS_DIR/product-workflow/scripts/run_checks.py" \
  --project-root "$PROJECT_ROOT" \
  --check typecheck lint backend e2e
```

脚本只执行显式指定的检查项。完整日志和报告写入业务项目的 `.product-workflow/runs/`；同版本的成功证据可以复用，使用 `--force` 可以主动重跑。

### 生成结项清单

```bash
python3 "$SKILLS_DIR/product-workflow/scripts/check_freshness.py" \
  --project-root "$PROJECT_ROOT" \
  --finalize
```

该命令读取现有产物与运行证据，生成 `99_交付清单.md`。它不会隐式执行类型检查、测试或 E2E。结构检查通过只说明文件和引用关系满足规则，不等同于业务正确或真实测试通过。

## 仓库结构

```text
product-delivery-skills/
├── install.sh                              # 通用安装入口
├── scripts/
│   └── install.py                          # 客户端识别、暂存、校验、备份和安装
├── release.json                            # 发行版本与来源信息
├── product-workflow/                       # 全流程编排器
│   ├── SKILL.md
│   ├── references/                         # 项目配置、验证契约、命令模板和 Mermaid 规范
│   ├── scripts/                            # 陈旧检查、结项、运行证据和快照工具
│   └── validators/                         # Mermaid 解析入口与锁定依赖清单
├── product-requirement/                    # 阶段 ⓪：需求沟通与确认
├── product-design/                         # 阶段 ①：产品设计与结构检查器
├── product-architecture/                   # 阶段 ②：功能架构与结构检查器
├── product-module-design/                  # 阶段 ③：模块详细设计与结构检查器
├── product-development/                    # 阶段 ④：开发规范、模板和参考工程
├── product-e2e-test/                       # 阶段 ⑤：E2E 规范、模板和静态检查器
├── product-diagnosis/                      # 阶段 ⑥：只读诊断
├── product-ui-spec/                        # 横向：UI 设计规范
├── product-prototype/                      # 横向：线框、原型和页面复刻
├── product-doc-convert/                    # 横向：文档格式转换
└── tests/                                  # 安装器与工作流工具测试
```

每个 Skill 目录都以 `SKILL.md` 为入口，可包含：

- `references/`：规范、模板和说明资料。
- `scripts/`：校验或辅助脚本。
- `assets/`：代码模板或参考工程。

安装器要求发行包中恰好包含这 11 个 Skill，并校验每个目录的 YAML frontmatter、Skill 名称和描述。

## 开发与维护

### 验证仓库

```bash
npm ci --ignore-scripts --prefix product-workflow/validators
python3 -B -m unittest discover -s tests -v
```

### 验证参考前端

```bash
cd product-development/assets/reference-app
npm ci
npm run build
npx playwright install chromium
npm test
```

也可以使用本机 Chrome：

```bash
PLAYWRIGHT_CHANNEL=chrome npm test
```

参考工程使用明确标识的内存演示服务，只用于验证模板。生产项目必须实现真实服务与数据访问逻辑。

### 安装器边界

- `install.sh` 必须与 `scripts/install.py`、`release.json` 和 11 个 Skill 目录一起分发，不能只复制一个脚本完成安装。
- 安装时会忽略源码仓库中的 `node_modules`、`dist`、测试报告、Python 缓存和 `.DS_Store`。
- 文档转换 Skill 的可选 Python 依赖不会随整体安装自动下载，应按其 [`SKILL.md`](product-doc-convert/SKILL.md) 在隔离环境中安装。
- 目录规则可能随客户端版本、企业版、Profile 或沙箱环境变化；实际目录不一致时，使用对应环境变量或 `--target`，不必修改安装器源码。

## 许可证

本仓库未附开源许可证。除非仓库所有者另行授权，默认不授予复制、修改、分发或再许可权利。
