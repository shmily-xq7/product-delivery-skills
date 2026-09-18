---
name: product-doc-convert
description: "本地文档格式互转工具（可运行 Python 脚本，跨阶段横向能力）。支持 docx/doc/docm → Markdown（保留表格与标题层级）、Markdown → docx（可指定中文字体）、表格型 docx → 结构化 docx、docx 标题层级 → Excel、三级列 Excel → 分级标题 Markdown。触发词：文档转 md、Word 转 Markdown、Markdown 转 Word、把表格做成 docx、docx 导出 excel、excel 转 md、格式转换。不负责文档内容撰写。"
metadata:
  version: "1.5.0"
  agent_created: true
---

# 文档格式互转

> 定位：**可执行的本地转换工具**，用于把需求材料在 Word / Excel / Markdown 之间搬运，打通「别人的文档」与「我们的单源 Markdown 工作流」。

## 1. 何时使用

- 拿到 `.docx` 需求说明书，要变成 Markdown 进入产品设计流程。
- 产品设计文档（Markdown）要交付给不使用 Markdown 的同事 → 转 `.docx`。
- 需要把 Word 里的标题层级导出成 Excel 做清单核对。
- 需要把整理了层级的 Excel 反向变成结构清晰的 Markdown。
- 需要把一份"纯表格"的 docx 拆成「标题 + 正文」的可读文档。

## 2. 转换矩阵

| 方向 | 脚本 | 说明 |
|---|---|---|
| docx / docm / doc → Markdown | `scripts/convert_docx_to_markdown.py` | 保留表格与标题层级；`.doc` 需系统有 `textutil`（macOS）或 LibreOffice |
| Markdown → docx | `scripts/markdown_to_docx.py` | 支持指定字体（`-f`，默认宋体）；保留标题层级与格式 |
| 表格型 docx → 结构化 docx | `scripts/convert_table_to_structured_docx.py` | 表格内容 → 标题 + 正文，便于阅读 |
| docx 标题层级 → Excel | `scripts/docx_to_excel.py` | 输出「1级标题 … N级标题 / 正文内容」共 N+1 列，N 取文档最大标题层级 |
| 三级列 Excel → Markdown | `scripts/excel_to_markdown.py` | 只读取前三列为一级/二级/三级标题；忽略其余列，且不保留正文 |

**格式边界**：两支 Excel 工具不是通用往返转换。DOCX 导出的 N+1 列不能直接当作固定三列标题输入：层级少于三层时正文可能占据第三列；超过三层时第四层及正文会被忽略。进入 Excel → Markdown 前应明确整理为「一级/二级/三级标题」三列，正文另行处理。

## 3. 运行方式

**依赖**（须在隔离 venv 内安装，勿污染全局环境；若你的运行平台提供托管的隔离环境，直接用它即可）

```bash
python3 -m venv .venv
.venv/bin/pip install python-docx openpyxl
# 之后用 .venv/bin/python 运行各脚本
```

| 脚本 | 需要的包 |
|---|---|
| `convert_docx_to_markdown.py` | `python-docx` |
| `markdown_to_docx.py` | `python-docx` |
| `convert_table_to_structured_docx.py` | `python-docx` |
| `docx_to_excel.py` | `python-docx`、`openpyxl` |
| `excel_to_markdown.py` | `openpyxl` |

**命令**

```bash
# docx → markdown（默认输出同名 .md）
<venv>/bin/python scripts/convert_docx_to_markdown.py 需求说明书.docx
<venv>/bin/python scripts/convert_docx_to_markdown.py 需求说明书.docx -o 原始需求.md

# markdown → docx（可指定字体）
<venv>/bin/python scripts/markdown_to_docx.py 00_产品设计文档.md
<venv>/bin/python scripts/markdown_to_docx.py 00_产品设计文档.md -f 思源宋体

# 表格型 docx → 结构化 docx
<venv>/bin/python scripts/convert_table_to_structured_docx.py 表格文档.docx

# docx 标题层级 → excel
<venv>/bin/python scripts/docx_to_excel.py 需求说明书.docx

# 三级列 excel → markdown
<venv>/bin/python scripts/excel_to_markdown.py 功能清单.xlsx
```

**全部脚本均接受位置参数指定输入文件，可选 `-o/--output` 指定输出路径**；未指定时按「与输入同目录同名、仅换扩展名」生成。

## 4. 注意事项

- **`.doc`（旧版二进制）转换依赖外部工具**（macOS `textutil` 或 LibreOffice）。若无，请先另存为 `.docx`。
- **转换是单向近似**：Markdown 无「表格样式」「页眉页脚」「批注」概念，往返转换会丢失这些信息。**不要用往返转换来"编辑"文档**，只用于搬运。
- **编码**：输出统一 UTF-8。若下游工具出现乱码，先确认其编码设置，而不是改脚本。
- **路径**：脚本已改为标准命令行入参，**不再包含任何硬编码路径**（原版本内含他人机器的绝对路径，已清除）。
- 生成的文件属于交付物，请放到目标项目目录内并遵守 `product-workflow` 的产物命名约定。

## 5. 完成前自检清单

- [ ] 在隔离 venv 中安装了所需包，未使用全局 pip
- [ ] 输入文件存在且格式与脚本匹配
- [ ] 输出路径符合目标项目的产物命名约定
- [ ] 抽查转换结果：标题层级、表格、列表是否完整
- [ ] 已知的不可转换内容（批注、页眉、样式）已向使用者说明

## 6. references 与 scripts 索引

| 文件 | 内容 |
|---|---|
| `scripts/convert_docx_to_markdown.py` | docx/docm/doc → Markdown |
| `scripts/markdown_to_docx.py` | Markdown → docx（可指定字体） |
| `scripts/convert_table_to_structured_docx.py` | 表格型 docx → 结构化 docx |
| `scripts/docx_to_excel.py` | docx 标题层级 → Excel |
| `scripts/excel_to_markdown.py` | 三级列 Excel → 分级标题 Markdown |
