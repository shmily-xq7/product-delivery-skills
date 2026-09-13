# 验证与证据契约（1.2.0）

## 结项条件

`--finalize` 只运行轻量结构检查、指纹检查和已保存证据核验，不自动执行项目命令。必需文件缺失、空文件、无来源标记、陈旧来源、异常退出、未知/损坏证据均阻断。

- 所有范围：明确的交付范围、原始需求、绑定当前需求的人工确认、产品设计、有效来源链、对应结构检查、当前问题台账。
- 设计到模块：再要求架构、至少一份模块详细设计和完整模块 AC 承接。
- 全链：再要求实际源码、配置中的全部必需命令通过，以及设计 AC 被实际执行通过的测试覆盖。默认检查为 typecheck、lint、backend、e2e；添加的自定义命令也计入必需检查。

`exemptions` 可对 frontend/backend 代码端或 typecheck/lint/e2e 检查写明具体范围理由（至少 8 字，不能含 TODO/待补充）。backend 豁免同时作用于后端源码和 backend 检查。不可豁免全部源码；豁免 E2E 不豁免 AC 的实际执行覆盖。此声明必须符合已经确认的交付范围，不能为绕过失败临时改口径。

## 需求确认

`.product-workflow/approval.json`：

```json
{
  "schema_version": 1,
  "requirement_sha256": "原始需求文件的完整 SHA256",
  "confirmed_by": "真实确认人",
  "confirmed_at": "实际确认时间",
  "confirmation_reference": "已有会话消息、批准记录或文档版本的可追溯位置"
}
```

已有明确授权可直接记录，不重复询问。模型不得编造确认人、时间或确认来源。脚本只能检查记录结构和版本绑定，不能认证是谁写入的。

## 执行与复用

读取配置中的命令后，用实际技能路径执行：

```bash
python3 "$SKILLS_DIR/product-workflow/scripts/run_checks.py" --project-root /实际项目根 --check typecheck lint backend e2e
```

脚本使用 argv、独立 cwd 和 600 秒超时，不拼接 shell。日志、独立 JUnit 报告和输入哈希落 `.product-workflow/runs/`；latest.json 指向各检查的最近一次尝试。启动新尝试前即使旧 PASS 失效，失败或中断后不能退回旧 PASS。

当前配置、需求、设计、模块、源码、测试和常见根目录构建配置/锁文件共同生成输入快照。忽略依赖缓存、构建结果和生成报告。前后快照必须一致；修改源码、文档、测试、命令、日志或报告会使相应证据失效。相同输入的通过记录默认复用；`--force` 强制重跑。当前采用保守的项目级运行快照，输入有变化可能需要重跑多项检查，但哈希和日志保存在本地，不需要把全文送给模型。文档来源检查支持模块章节切片。

环境变量、数据库内容、远端 API、浏览器以及工具链升级不保证都能由文件快照发现；这些输入变化时必须 `--force`，并在运行说明中记录环境。哈希验证用于防止意外误用旧证据，不是防伪签名，也不证明断言充分。

## 测试覆盖

测试命令配置 `"report":"junit"`。pytest 默认使用 `--junitxml={report}`，Playwright 默认使用 `--reporter=junit`，脚本设置 `PLAYWRIGHT_JUNIT_OUTPUT_FILE` 到本次独立报告。自定义命令通过 `{report}` 接收报告绝对路径。不得复用手工准备的报告。

读取真实 testcase：失败/错误报告、零测试或全部跳过都失败；跳过条目不提供覆盖。只要同一报告出现失败，即使随后有重试通过，仍保守要求检查重试原因。

把 AC 写在实际测试名称中，例如 `test('AC-USER-01 查询用户', ...)`；也可在配置中显式映射 JUnit 的准确身份：

```json
{
  "ac_tests": {
    "AC-USER-01": [
      {"check":"backend", "classname":"tests.test_users.TestUsers", "name":"test_query"}
    ]
  }
}
```

同一 AC 映射的全部测试都必须执行通过。适合单元/API测试的 AC 不强制重复写 E2E；界面关键路径仍应有 E2E。`validate_e2e_spec.py` 只查静态引用、悬空编号和是否识别到测试声明，不证明实际执行，也不能判断断言业务质量。可执行但空断言的测试仍需针对验收标准进行评审。

## 指纹与复核

来源默认使用规范化完整正文 SHA256，仅去掉流程生成的元信息块、统一换行及行尾空白。编号不变但阈值、字段类型、权限规则变化也会失效。显式 `module_sources` 仅核验选定章节；共享依赖必须列全。旧 fp/短哈希首次迁移会失效，应复核后重新盖章。

缺失需求不会删除依赖边。完整文档边传播上游未复核状态；章节切片隔离无关正文变化，但需求基线缺失/变化、来源未标记等链路问题仍向下游传播。全链结项仍要求架构等范围内文档完成复核。

STALE 表示需要复核，不自动要求重写。`--stamp` 仅在核对相关来源后记录新版本，不能替代评审。运行证据独立绑定文档和代码；只给文档盖章不会制造测试通过记录。

## 文档结构与图语法

产品设计要求非空页面清单，与详情名称一一对应，每页有 AC、字段字典和交互矩阵实际表格，以及全局检查。架构要求核心章节、数据库定义、前端组件树；模块要求产品/前端/后端/测试四部分、非空 AC 声明及对应测试表、API 契约和数据库设计。

确无数据库或接口时可写独立行 `N/A[database]: 本模块读取外部接口且不持久化数据`、`N/A[api]: 本模块全部逻辑在本地执行且不调用后端`。架构没有前端时可用 `N/A[frontend]: 具体理由`。空白、TODO 或“待补充”不构成理由。保留核心章节，并在相关章节说明适用边界；这些理由仍需与需求一致。

实际 Mermaid 11.12.2 解析器检查语法，原有兼容性风格规则另外保留。解析成功不等于图语义或布局正确，也不等于已经在旧版 Mermaid 8 渲染器实测。安装器在暂存目录安装并自检锁定依赖；缺依赖时阶段检查阻断，不能降级成 PASS。

## 问题台账

`.product-workflow/issues.json`：

```json
{
  "schema_version":1,
  "reviewed_by":"实际复核者（可为执行诊断的代理）",
  "reviewed_at":"实际复核时间",
  "input_sha256":"delivery_evidence.input_digest(root, load_config(root)) 的结果",
  "issues":[
    {"id":"ISSUE-001","title":"权限拒绝尚未验证","owner":"负责人","severity":"high","blocking":true,"status":"open"}
  ]
}
```

检查后确认没有问题可写 `issues: []`，不可未经检查自动填空。台账不存在、输入版本过期、字段不合法、任何 open 阻断项都会阻断结项。severity 为 critical/high/medium/low；status 为 open/resolved/accepted。

resolved 必须有 `resolution: {"summary":"解决说明", "evidence":[{"path":"项目相对证据文件", "sha256":"该文件完整哈希"}]}`。accepted 还需 `acceptance: {"confirmed_by":"真实确认人", "confirmation_reference":"真实确认位置"}`，不能由模型自行接受风险。

旧报告会扫描全部“未确认/待处理/未解决”章节，空白和“待补充”均阻断。同一报告可在文末追加复核，不删历史内容。已迁移并解决的旧章节可在对应关闭问题的 `legacy_sources` 中登记 `{"path":"旧报告相对路径", "body_sha256":"该章节正文 strip 后的 SHA256"}`。脚本 `issue_ledger.legacy_sections` 返回精确 path、hash、body，避免人工猜哈希；报告内容再次变化会重新触发未确认项。
