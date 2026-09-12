# product-delivery-skills

WorkBuddy 产品交付链 skill 族：一条从**需求沟通**到**结项交付**的端到端工作流，含阶段门禁、AC 验收标准追溯、陈旧检测与结项判定。

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
| ① | `product-design` | 产品设计文档（页面清单 / ASCII 布局 / 字段字典 / 交互矩阵 / AC 验收标准） | `validate_design_doc.py`（C1–C15） |
| ② | `product-architecture` | 功能架构文档（技术方案 / Mermaid 架构图 / 表定义+ER / 组件树） | `validate_arch_doc.py`（A1–A6） |
| ③ | `product-module-design` | 单模块详细设计（承接 AC / API 契约 / DDL / 测试用例表） | `validate_module_doc.py`（M1–M6） |
| ④ | `product-development` | 按设计写代码；**全族技术栈基线单一事实源**（React18+TS+AntD / FastAPI） | 项目工具链（tsc / eslint / pytest） |
| ⑤ | `product-e2e-test` | Playwright 端到端测试；用例按 AC 编号引用 | `validate_e2e_spec.py`（E1–E4 双向覆盖校验） |
| ⑥ | `product-diagnosis` | 只读问题诊断，产出 `90_诊断报告_<主题>.md` | —（只读角色） |
| ⑦ | `product-workflow` | **编排器**：产物目录契约、阶段门禁、失败回流、来源指纹（陈旧检测）、交付范围声明、结项判定 | `check_freshness.py` |

横向支撑：`product-ui-spec`（双主题 token + 组件规格）、`product-prototype`（ASCII 线框 / HTML 原型 / 页面复刻）、`product-doc-convert`（docx↔Markdown↔Excel 互转脚本）。

元技能：`prompt-kit-to-skills`（这套 skill 族本身的整理方法论，含实测陷阱清单）。

## 核心设计

- **AC 编号贯穿全链**：① 定义 `AC-<模块缩写>-<两位序号>` → ③ 列「本模块覆盖的 AC」→ ⑤ 用例按编号标注；三段可对账，门禁双向校验覆盖与悬空
- **门禁可判定**：5 个校验器 + 1 个陈旧检测器，规则与实现对账（规范自己的样例必须过自家门禁）
- **来源指纹（陈旧检测）分层**：人写需求用整文件哈希（改一个字就该重审全链）；结构化产物之间用契约指纹（AC / 页面名 / 表名 / 接口路径的集合哈希）——改错别字不告警，实质变更才告警
- **交付范围声明**：`原始需求.md` 声明 `仅需求分析 / 设计到模块 / 全链`，结项按范围裁剪判定
- **产物编号体系**：`00_` 全局文档 ｜ `01_` 模块详细设计 ｜ `90_` 诊断报告 ｜ `99_` 交付清单（终点）

## 安装

把各 skill 目录复制到 WorkBuddy 的用户级技能目录：

```bash
cp -R product-* prompt-kit-to-skills ~/.workbuddy/skills/
```

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
prompt-kit-to-skills/   # 元技能：提示词工具包 → skill 族的整理方法论
```

> 本仓库内容为私有方法论沉淀，未附开源许可证。
