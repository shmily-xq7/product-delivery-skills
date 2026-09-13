# product-delivery-skills

版本：`1.2.0-local.1`（基于 a7f066c8，包含 F1–F9 工作流修复；保留已验证发行包的版本编号）。

产品交付链 skill 族：一条从**需求沟通**到**结项交付**的端到端工作流，含阶段门禁、AC 验收标准追溯、陈旧检测与结项判定。

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

| 阶段 | skill | 职责 | 门禁 |
|---|---|---|---|
| ⓪ | `product-requirement` | 需求访谈、澄清、口径对齐，产出《需求澄清报告》，**用户确认后**基线才生效 | 人工确认门禁 |
| ① | `product-design` | 产品设计文档（页面清单 / ASCII 布局 / 字段字典 / 交互矩阵 / AC 验收标准） | `validate_design_doc.py`（C1–C19） |
| ② | `product-architecture` | 功能架构文档（技术方案 / Mermaid 架构图 / 表定义+ER / 组件树） | `validate_arch_doc.py`（A1–A9） |
| ③ | `product-module-design` | 单模块详细设计（承接 AC / API 契约 / DDL / 测试用例表） | `validate_module_doc.py`（M1–M8） |
| ④ | `product-development` | 按设计写代码；**全族技术栈基线单一事实源**（React18+TS+AntD / FastAPI） | 项目工具链（tsc / eslint / pytest） |
| ⑤ | `product-e2e-test` | Playwright 端到端测试；用例按 AC 编号引用 | `validate_e2e_spec.py`（静态引用检查，执行覆盖另核报告） |
| ⑥ | `product-diagnosis` | 只读问题诊断，产出 `90_诊断报告_<主题>.md` | —（只读角色） |
| ⑦ | `product-workflow` | **编排器**：产物目录契约、阶段门禁、失败回流、来源指纹（陈旧检测）、交付范围声明、结项判定 | `check_freshness.py` |

横向支撑：`product-ui-spec`（双主题 token + 组件规格）、`product-prototype`（ASCII 线框 / HTML 原型 / 页面复刻）、`product-doc-convert`（docx↔Markdown↔Excel 互转脚本）。


## 核心设计

- **AC 编号贯穿全链**：① 定义 `AC-<模块缩写>-<两位序号>` → ③ 列「本模块覆盖的 AC」→ ⑤ 用例按编号标注；三段可对账，门禁双向校验覆盖与悬空
- **结构检查**：4 个阶段校验器 + 1 个陈旧检测/结项脚本。结项核验必需产物、真实确认记录、来源、运行证据与遗留问题；结构通过不能替代业务评审。
- **模块增量检查**：配置模块来源章节后，只核验所选章节完整内容。未配置章节时核验完整正文；旧集合指纹须复核迁移；来源变化先判断影响，不自动重做全链。
- **交付范围声明**：`原始需求.md` 声明 `产品设计 / 设计到模块 / 全链`，结项按范围裁剪判定
- **产物编号体系**：`00_` 全局文档 ｜ `01_` 模块详细设计 ｜ `90_` 诊断报告 ｜ `99_` 交付清单（终点）

## 安装

**安装到 Codex（默认）**，要求 Python 3.9+、Node.js 20+ 和 npm；首次安装需联网下载固定版本 Mermaid 语法解析器：

```bash
git clone https://github.com/shmily-xq7/product-delivery-skills
cd product-delivery-skills
bash install.sh
```

上述安装命令安装当前仓库版本；也可以使用同版本的完整发行包。

```bash
bash install.sh --app workbuddy
bash install.sh --target /自定义/skills
```

`--target` 优先，其次 `SKILLS_DIR`、旧变量 `WORKBUDDY_SKILLS_DIR`，最后应用默认目录。Codex 默认采用 `${CODEX_HOME:-$HOME/.codex}/skills`。

安装先暂存并核验全部文件，再逐目录替换；替换期间出现可捕获异常会回滚。不是跨 11 个目录的操作系统级原子事务，断电/强杀应检查备份恢复。备份位于技能根的 `.product-delivery/backups/<唯一运行ID>/`，避免把旧版备份当作活动技能。`.product-delivery/manifest.json` 保存版本、基准 commit、来源与逐文件 SHA-256；不复制源目录的依赖缓存或构建产物；Mermaid 运行时依照 package-lock 在暂存目录重建并自检。若进程异常退出留下 install.lock，先核对其中 pid 已不再运行，再移走锁并检查备份。

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
