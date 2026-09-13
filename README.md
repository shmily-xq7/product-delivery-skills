# product-delivery-skills

版本：`1.3.1`（包含 F1–F9 工作流修复、跨 Agent 安装支持及用户用语优化）。

产品交付链 skill 族：一条从**需求沟通**到**结项交付**的端到端工作流，含阶段检查（原称“阶段门禁”）、AC 验收标准追溯、陈旧检测与结项判定。

## 交付链

```
需求沟通⓪（访谈/澄清/用户确认）
   │  产出《需求澄清报告》→ 用户确认 → 确认基线誊为 原始需求.md
   ▼
原始需求 ──①──▶ 产品设计文档 ──②──▶ 功能架构设计文档 ──③──▶ 模块详细设计
                                                              │
                                                              ▼
                                                    ④ 代码开发 ──⑤──▶ E2E 测试 ──⑦──▶ 99_交付清单
                                                              │
                     任一环节卡住 ──⑥ 诊断──▶ 诊断报告 ──▶ 回对应阶段

横向支撑（任一阶段可调用）：
  产品视觉口径 product-ui-spec   ·   线框/原型 product-prototype   ·   格式转换 product-doc-convert
```

## Skill 清单

| 阶段 | skill | 职责 | 检查方式 |
|---|---|---|---|
| ⓪ | `product-requirement` | 需求访谈、澄清、口径对齐，产出《需求澄清报告》，**用户确认后**基线才生效 | 用户人工确认 |
| ① | `product-design` | 产品设计文档（页面清单 / ASCII 布局 / 字段字典 / 交互矩阵 / AC 验收标准） | `validate_design_doc.py`（C1–C19） |
| ② | `product-architecture` | 功能架构文档（技术方案 / Mermaid 架构图 / 表定义+ER / 组件树） | `validate_arch_doc.py`（A1–A9） |
| ③ | `product-module-design` | 单模块详细设计（承接 AC / API 契约 / DDL / 测试用例表） | `validate_module_doc.py`（M1–M8） |
| ④ | `product-development` | 按设计写代码；**全族技术栈基线单一事实源**（React18+TS+AntD / FastAPI） | 项目工具链（tsc / eslint / pytest） |
| ⑤ | `product-e2e-test` | Playwright 端到端测试；用例按 AC 编号引用 | `validate_e2e_spec.py`（静态引用检查，执行覆盖另核报告） |
| ⑥ | `product-diagnosis` | 只读问题诊断，产出 `90_诊断报告_<主题>.md` | —（只读角色） |
| ⑦ | `product-workflow` | **编排器**：产物目录契约、阶段检查、失败回流、来源指纹（陈旧检测）、交付范围声明、结项判定 | `check_freshness.py` |

横向支撑：`product-ui-spec`（双主题 token + 组件规格）、`product-prototype`（ASCII 线框 / HTML 原型 / 页面复刻）、`product-doc-convert`（docx↔Markdown↔Excel 互转脚本）。


## 核心设计

- **AC 编号贯穿全链**：① 定义 `AC-<模块缩写>-<两位序号>` → ③ 列「本模块覆盖的 AC」→ ⑤ 用例按编号标注；三段可对账，阶段检查会双向校验覆盖与悬空
- **结构检查**：4 个阶段校验器 + 1 个陈旧检测/结项脚本。结项核验必需产物、真实确认记录、来源、运行证据与遗留问题；结构通过不能替代业务评审。
- **模块增量检查**：配置模块来源章节后，只核验所选章节完整内容。未配置章节时核验完整正文；旧集合指纹须复核迁移；来源变化先判断影响，不自动重做全链。
- **交付范围声明**：`原始需求.md` 声明 `产品设计 / 设计到模块 / 全链`，结项按范围裁剪判定
- **产物编号体系**：`00_` 全局文档 ｜ `01_` 模块详细设计 ｜ `90_` 诊断报告 ｜ `99_` 交付清单（终点）

## 安装

安装器采用开放的 Agent Skills 目录结构，不把工作流绑定到某一个智能体。要求 Python 3.9+、Node.js 20+ 和 npm。仓库不打包 Mermaid 解析器及其 `node_modules`；每次安装时，安装器会在暂存目录运行 `npm ci`，从 npm registry 下载 `package-lock.json` 锁定的版本并完成自检，因此安装时需要网络可访问 npm registry：

```bash
git clone https://github.com/shmily-xq7/product-delivery-skills
cd product-delivery-skills
bash install.sh --list-apps
```

该命令只列出支持的客户端和实际路径。再由用户明确选择安装目标；无参数不会替用户默认选择某一个客户端。

以下客户端可直接指定，也可以一次安装到多个客户端：

```bash
bash install.sh --app claude-code
bash install.sh --app codex
bash install.sh --app workbuddy
bash install.sh --app qwen-office
bash install.sh --app trae-work
bash install.sh --app trae-cli
bash install.sh --app dsh
bash install.sh --app claude-code --app codex --app workbuddy --app qwen-office --app trae-work --app dsh
```

客户端配置如下。别名 `claude`、`qwenwork`、`traework`、`traecode`、`deepseek-harness` 也可使用。

| 客户端标识 | 默认用户级目录 | 单客户端覆盖变量 | 依据与限制 |
|---|---|---|---|
| `claude-code` | `~/.claude/skills` | `CLAUDE_SKILLS_DIR` | [Claude Code 官方 Skills 文档](https://code.claude.com/docs/en/skills) |
| `codex` | `~/.agents/skills` | `AGENT_SKILLS_DIR` | [Codex 官方 Skills 文档](https://developers.openai.com/codex/skills) |
| `codex-legacy` | `${CODEX_HOME:-~/.codex}/skills` | `CODEX_SKILLS_DIR` | 只用于升级旧安装，避免旧目录用户被静默迁移 |
| `workbuddy` | `~/.workbuddy/skills` | `WORKBUDDY_SKILLS_DIR` | WorkBuddy 客户端兼容目录；格式见[官方技能文档](https://open.workbuddy.cn/docs/skill) |
| `qwen-office` | `~/.qwenwork/skills` | `QWENWORK_SKILLS_DIR` | [千问办公官方 Skills 文档](https://www.alibabacloud.com/help/zh/qwenwork/skills) |
| `trae-work` | `~/.trae-cn/skills` | `TRAE_SKILLS_DIR` | [TRAE Work 官方 Skills 文档](https://docs.trae.cn/work_skills) |
| `trae-cli` | `~/.traecli/skills` | `TRAECLI_SKILLS_DIR` | [TraeCode CLI 官方 Skills 文档](https://docs.trae.cn/cli_skills) |
| `dsh` | `${DSH_HOME:-~/.dsh}/skills` | `DSH_SKILLS_DIR` | [DSH 官方 Skills 文档](https://dsh.fish/docs/publish/skill)；目录保持 `<name>/SKILL.md` 一层结构 |

先检查本机检测结果与实际写入位置，再执行批量安装：

```bash
bash install.sh --list-apps
bash install.sh --all-detected --dry-run
bash install.sh --all-detected
```

`--all-detected` 是用户主动选择“全部已检测客户端”时的便利选项，只选择存在客户端标记目录的配置，并按真实路径去重。它不会自动选择 `codex-legacy`。多个目标逐个事务化安装；若后一个目标失败，前面已成功的目标保持新版本，终端会列出失败目标。

对于支持客户端界面导入的场景，可以显式生成 11 个独立包。每个 ZIP 的根目录都有 `SKILL.md`，`product-workflow.zip` 还包含安装并自检过的 Mermaid 运行时；这些是写入用户指定目录的临时交付物，默认不生成，也不纳入源码仓库：

```bash
bash install.sh --export-packages ./dist/client-import
```

也可以重复 `--target` 支持任何兼容 Agent Skills 的客户端或项目级目录：

```bash
bash install.sh --target /自定义/skills --target /另一个项目/.agents/skills
```

显式 `--app` 使用该客户端的覆盖变量；显式 `--target` 直接加入安装目标。没有命令行目标时，只有已经设置的通用变量 `AGENT_SKILLS_DIR`、`SKILLS_DIR` 或旧变量 `WORKBUDDY_SKILLS_DIR` 才会被视为用户选择；否则安装器停止并提示选择目标。目录和导入能力会随客户端版本变化，遇到企业版、国际版、多用户 Profile 或沙箱安装时，应以 `--list-apps` 和客户端实际目录为准，用对应环境变量或 `--target` 修正，而不是修改安装器源码。

每个目标都先暂存并核验全部文件，再逐目录替换；替换期间出现可捕获异常会回滚。不是跨 11 个目录的操作系统级原子事务，断电/强杀应检查备份恢复。备份位于技能根的 `.product-delivery/backups/<唯一运行ID>/`，避免把旧版备份当作活动技能。`.product-delivery/manifest.json` 保存版本、客户端、目标、基准 commit、来源与逐文件 SHA-256；源仓库中的依赖缓存和构建产物不会被复制，Mermaid 运行时会按照 package-lock 在暂存目录重新安装并自检。npm 缓存可能减少实际下载量，但不能作为离线安装保证。若进程异常退出留下 install.lock，先核对其中 pid 已不再运行，再移走锁并检查备份。

`install.sh` 是 Python 安装器的入口，需与 scripts/install.py、release.json 和 11 个技能目录一起分发，不能单独复制它完成安装。可选文档转换依赖仍在隔离环境安装，不在安装技能时自动下载。

## 项目配置与验证

验证契约：`product-workflow/references/verification-contract.md`。配置说明：`product-workflow/references/project-config.md`；可复制同目录 project-config.example.json 到业务项目根并按需修改。维护中的模块引用稳定来源 ID；需要评审单文件时才生成快照。

```bash
npm ci --ignore-scripts --prefix product-workflow/validators
python3 -B -m unittest discover -s tests -v
```

参考页面：进入 `product-development/assets/reference-app` 后执行：

```bash
npm ci
npm run build
npx playwright install chromium
npm test
```

也可使用已安装的 Chrome：`PLAYWRIGHT_CHANNEL=chrome npm test`。参考工程使用独立、明确标识的内存演示服务，验证模板本身；生产项目必须提供实际 UserService，不包含演示数据。依赖以 package-lock.json 固定，测试产物不打包。

使用时直接说触发词即可（如「写产品设计文档」「模块详细设计」「需求访谈」「项目能不能交付」）；不知道从哪开始就说「走完整产品交付流程」，由编排器 `product-workflow` 路由。

## 目录结构

```
product-workflow/       # 编排器（含 scripts/check_freshness.py、commands/、产物母版）
product-requirement/    # ⓪ 需求沟通（访谈清单、澄清报告模板、表达原则）
product-design/         # ① 产品设计（规范、范例、scripts/validate_design_doc.py）
product-architecture/   # ② 功能架构（规范、scripts/validate_arch_doc.py）
product-module-design/  # ③ 模块详细设计（规范、scripts/validate_module_doc.py）
product-development/    # ④ 代码开发（技术栈基线、React 整页模板 assets/templates/）
product-e2e-test/       # ⑤ E2E（规范、模板、scripts/validate_e2e_spec.py）
product-diagnosis/      # ⑥ 诊断
product-ui-spec/        # 横向：界面设计规范（tokens.css 双主题 token）
product-prototype/      # 横向：原型（ASCII 规范 / HTML / 复刻）
product-doc-convert/    # 横向：文档格式转换（scripts/*.py）
```

> 本仓库内容为私有方法论沉淀，未附开源许可证。
