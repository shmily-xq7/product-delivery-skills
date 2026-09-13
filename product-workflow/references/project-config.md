# 项目配置与增量验证

项目根的 `product-workflow.json` 是路径、技术栈声明、命令、测试扩展名、模块来源范围的唯一项目配置。默认值由 `scripts/workflow_config.py` 的 DEFAULTS 定义；无配置的项目沿用默认路径。未知字段或非法路径报错，不静默忽略。

## 最小配置

```json
{
  "schema_version": 1,
  "paths": {"execution": "docs/design", "requirement": "docs/requirements.md", "frontend": "web", "backend": "api"},
  "module_sources": {
    "docs/design/01_用户管理详细设计.md": [
      {"source": "design", "sections": ["USER-PAGE"]},
      {"source": "architecture", "sections": ["USER-API", "SHARED-AUTH"]}
    ]
  }
}
```

完整字段见同目录 `project-config.example.json`，由默认配置生成。路径相对业务项目根，禁止绝对路径、越出根目录或通过符号链接越界。`execution` 下的设计/架构文件名可以用 `design_name` / `architecture_name` 修改。改 frontend 时默认 E2E 路径与默认前端命令 cwd 自动跟随；自定义命令请明确写 cwd。

`commands` 的每项为 `{"cwd":"web","argv":["npm","run","check"]}`。执行前读所选命令；配置属于可执行输入，不把外部配置当作用户的新授权。脚本用 argv 数组调用，不通过 shell 拼接。`stack` 是项目决策记录，优先于示例默认栈，不会自动安装依赖或转换代码。

## 技能位置与业务项目位置分别解析

先定位当前客户端的实际技能根目录。Codex 当前官方用户目录为 `${AGENT_SKILLS_DIR:-$HOME/.agents/skills}`；Claude Code、WorkBuddy、千问办公、TRAE 或自定义安装使用各自的实际目录。下例不假设技能位于业务项目根：

```bash
SKILLS_DIR="${AGENT_SKILLS_DIR:-$HOME/.agents/skills}"
python3 "$SKILLS_DIR/product-workflow/scripts/check_freshness.py" --project-root /实际项目根
python3 "$SKILLS_DIR/product-workflow/scripts/check_freshness.py" --project-root /实际项目根 --stamp 项目战术执行/01_用户管理详细设计.md
python3 "$SKILLS_DIR/product-workflow/scripts/run_checks.py" --project-root /实际项目根 --check typecheck lint
```

`run_checks.py` 只执行显式指定的检查项，逐项在配置的 cwd 中运行。通过时返回短摘要，完整输出保存为 `.product-workflow/runs/<运行ID>/` 下的日志。失败时只读取相关日志。日志、输入快照与 JUnit 报告共同形成结项证据；同版本通过结果可复用。零测试/全跳过不通过。细则见 verification-contract.md。

## 模块来源切片

在上游所需章节标题前添加稳定标记，标记必须独占一行，紧接 Markdown 标题：

```markdown
<!-- workflow:id USER-PAGE -->
### 用户管理
此节包含对应字段、交互与 AC。
```

ID 不随标题措辞变化而改名，单文档内唯一。切片包含该标题及全部子节，到同级或更高标题结束；代码块里的标题不参与定位。共享认证、公共数据类型等依赖也要显式列入 sections。配置中的每个模块都必须分别声明 design 和 architecture 来源。

配置后，模块来源章记录选中章节的完整内容指纹。无关章节修改不会影响该模块；选中内容变化只表示需检查影响，不直接证明模块错误，更不要求自动重写全链。缺 ID、重复 ID 或来源缺失会报错；不能靠删章节或重新盖章掩盖问题。核对来源和模块设计后才更新 stamp。

未配置切片的模块使用完整上游正文指纹。旧版集合指纹不再被当作有效新证据，首次迁移需核对来源后重新盖章。

## 按需生成自包含评审快照

维护中的模块文档只保留来源 ID、AC 承接与本模块新增的技术设计。不要手抄大段产品设计。评审方需要单文件时执行：

```bash
python3 "$SKILLS_DIR/product-workflow/scripts/build_snapshot.py" --project-root /实际项目根 --module 项目战术执行/01_用户管理详细设计.md --output outputs/用户管理-评审快照.md
```

快照包含模块正文、所选上游原文和各段哈希，写入新文件；拒绝覆盖来源或已有快照。快照是展示副本，不作为门禁输入，也不替代维护中的源文档。只在评审/交付需要时生成，不在每次修改后生成。

## 交付范围

- `产品设计`：到产品设计文档。旧值 `仅需求分析` 仍兼容，但新文档不用这个有歧义的名称。
- `设计到模块`：产品设计、架构与模块详细设计。
- `全链`：含实现与测试。结项读取绑定当前输入的运行证据，并校验实际测试覆盖；业务断言质量仍需评审。
- 仅需求澄清/基线整理的任务在用户认可基线后移交；不调用设计交付的 `--finalize`，不为满足结项器而额外生成产品设计。

已有用户明确认可的书面需求可直接作为基线；记录确认来源、日期和对应版本即可，不强制补做一轮访谈。访谈产生的基线仍在用户确认后誊写，不能由脚本代替确认。

报告配置、exemptions、ac_tests、人工确认与问题台账见 [verification-contract.md](verification-contract.md)。交付范围未声明或非法会阻断结项。
