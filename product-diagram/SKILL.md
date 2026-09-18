---
name: product-diagram
description: "产品交付图表设计与交付（跨阶段横向能力）。根据需求、产品设计、架构、模块设计、测试证据或诊断材料选择合适图型，生成和维护 Mermaid 源码、SVG、HTML 与来源清单，并检查图表是否陈旧。适用于业务流程/泳道/状态、系统架构/部署/数据流/ER、接口时序/模块依赖、测试覆盖和问题诊断关系图。触发词：画流程图、泳道图、状态图、架构图、部署图、数据流图、ER 图、时序图、依赖图、测试覆盖图、诊断关系图、导出 SVG、图表过期检查。不负责页面线框或静态页面原型（使用 product-prototype），也不凭空生成没有数据依据的统计图。"
metadata:
  version: "1.5.0"
  agent_created: true
---

# 产品交付图表

> 定位：把各阶段已经确认的业务或技术关系转成可审阅、可追溯、可重新生成的图表。图表负责表达，不替代需求、设计、代码、测试证据或人工评审。

项目路径优先读取项目根 `product-workflow.json`；默认设计文档仍落 `项目战术执行/`，独立图表产物落 `outputs/diagrams/`。

## 1. 何时使用

- 用户明确要求绘制、重绘、导出或检查产品交付图表。
- 一个阶段存在多角色交接、状态迁移、服务调用、部署边界、数据关系或依赖传播，仅靠表格难以看清。
- 文档中的 Mermaid 图需要生成独立 SVG / HTML，供评审、知识库或交付材料引用。
- 上游文档变化后，需要判断既有图表是否陈旧。

以下情况不使用：页面布局和交互原型交给 `product-prototype`；简单清单继续使用表格；没有真实数据时不制造比例、趋势或统计结论。

## 2. 工作原则

1. **来源先于图形**：先确定权威来源文件和具体 Mermaid 块，再生成派生产物。不得从旧 PNG 反推并覆盖当前设计。
2. **语义完整**：保留关键角色、正常路径、异常路径、终态、关系方向和约束。图太密时拆成总览与细节，不静默删除规则。
3. **阶段归属明确**：业务含义由对应阶段 skill 决定；本 skill 只负责选择图型、绘制、导出和检查。
4. **默认静态交付**：维护 Mermaid 源码，生成无外部脚本和远程资源的 SVG / HTML。需要动画或统计图时另行明确需求。
5. **检查边界清楚**：渲染成功只证明语法与基本输出有效，不证明业务正确、测试通过或架构合理。

## 3. 工作流程

1. 读取对应阶段产物，确认图表目的、读者和权威来源。
2. 按 [references/diagram-spec.md](references/diagram-spec.md) 选择阶段、图型和必须表达的内容。
3. 在来源 Markdown 中维护 fenced `mermaid` 块，遵守 [references/diagram-spec.md](references/diagram-spec.md) 的语法与语义规则。
4. 复杂图先拆分；每张图使用稳定 ID，例如 `USER-LIFECYCLE`、`PAYMENT-SEQUENCE`。
5. 用脚本生成独立产物并登记来源：

```bash
python3 "$SKILLS_DIR/product-diagram/scripts/diagram_tool.py" render \
  --project-root /实际项目根 \
  --source 项目战术执行/00_产品设计文档.md \
  --diagram-index 0 \
  --id USER-FLOW \
  --stage design \
  --type business-flow \
  --title 用户管理业务流程 \
  --description 用户从进入页面到完成查询和异常重试的业务流程
```

6. 打开生成的 HTML 或 SVG 做人工目视检查：文字无截断、节点不重叠、连线方向明确、异常路径可识别。
7. 交付或结项前检查全部登记图表：

```bash
python3 "$SKILLS_DIR/product-diagram/scripts/diagram_tool.py" check \
  --project-root /实际项目根
```

## 4. 输出契约

默认输出：

```text
outputs/diagrams/
├── manifest.json
└── USER-FLOW/
    ├── source.mmd
    ├── USER-FLOW.svg
    └── USER-FLOW.html
```

- `source.mmd` 是来源 Mermaid 块的可独立读取副本；权威来源仍是清单记录的阶段文档。
- `manifest.json` 记录图表 ID、阶段、图型、来源路径、块序号、来源哈希和产物哈希。
- 同一 ID 再次生成会更新该图和清单；其他图不受影响。
- 不手工修改 SVG / HTML。需要变化时修改权威来源并重新生成。

## 5. 与阶段 Skill 的边界

| 阶段 | 内容责任 | 本 skill 可提供 |
|---|---|---|
| 需求沟通 | 用户、范围和确认口径 | 现状/目标流程、用户旅程关系图 |
| 产品设计 | 业务规则、页面、交互、AC | 业务流程、泳道、状态、页面导航关系图 |
| 功能架构 | 服务、数据、部署和安全边界 | 系统架构、部署、数据流、ER 图 |
| 模块详细设计 | API、状态、DDL、组件与测试设计 | 时序、状态、依赖、模块 ER 图 |
| 开发与测试 | 真实实现和运行结果 | 实现依赖图、AC 测试覆盖关系图 |
| 问题诊断 | 根因、影响和证据 | 故障时序、原因树、影响关系图 |
| 结项 | 当前交付范围与有效证据 | 图表目录与陈旧检查结果 |

图表类型、触发条件和语义自检详见 [references/diagram-spec.md](references/diagram-spec.md)。

## 6. 自检

- [ ] 图表有明确权威来源，而不是从旧截图复制。
- [ ] 使用正确图型，表格能讲清楚的内容没有强行绘图。
- [ ] 正常、异常、取消、重试、权限拒绝等适用分支没有因版面被省略。
- [ ] Mermaid 语法通过，并已打开最终产物做目视检查。
- [ ] SVG 含可访问的标题和描述；HTML 不依赖远程字体、脚本或图片。
- [ ] 清单中的来源与产物哈希通过 `check`。
- [ ] 图表检查结果未被当成业务评审或测试通过证明。

## 7. references / scripts

| 文件 | 用途 |
|---|---|
| `references/diagram-spec.md` | 阶段与图型选择、内容要求、拆图和审阅规则 |
| `scripts/diagram_tool.py` | 从 Markdown Mermaid 块生成 SVG / HTML，登记来源并检查陈旧状态 |
| `validators/mermaid.mjs` | 本 skill 的本地 SVG 渲染入口；依赖由安装器按锁定版本装入，不依赖其他 skill 运行 |
