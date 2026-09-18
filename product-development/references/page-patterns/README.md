# 后台页面模式目录

本目录补充普通 CRUD 列表和单层标签页之外的高频后台页面。它定义业务与交互契约，不绑定 React、Vue 或组件库；实现时仍以已选技术栈 profile 和目标项目现有组件为准。

## 使用方法

1. 从模块详细设计确认页面承担的任务与风险。
2. 在下表选择必要模式；一个页面可组合多个模式。
3. 只读取命中的参考文件，将其中的必备状态、失败路径和验证点写入实现与 AC/E2E 映射。
4. 若模式与详细设计冲突，回到详细设计确认，不能用目录内容擅自改业务口径。

| 模式 ID | 适用场景 | 参考文件 |
|---|---|---|
| `standard-list` | 查询、分页、增删改查 | `list-and-batch.md` |
| `batch-processing` | 勾选多条数据后批量执行 | `list-and-batch.md` |
| `dynamic-columns` | 列显隐、顺序或宽度可配置 | `list-and-batch.md` |
| `tree-table` | 树形层级与表格联动 | `tree-and-rbac.md` |
| `rbac-matrix` | 角色、资源、动作授权 | `tree-and-rbac.md` |
| `audit-log` | 操作记录、条件检索、详情取证 | `audit-and-transfer.md` |
| `import-export` | 文件上传、校验、异步导入导出 | `audit-and-transfer.md` |
| `nested-tabs` | 路由驱动的多层标签页 | `navigation-and-embedded.md` |
| `embedded-content` | iframe 或第三方页面嵌入 | `navigation-and-embedded.md` |
| `detail-editor` | 详情查看与编辑状态切换 | `detail-editor.md` |

`catalog.json` 是机器可读索引。可运行以下命令检查目录或查看单个模式：

```bash
python3 scripts/page_patterns.py validate
python3 scripts/page_patterns.py list
python3 scripts/page_patterns.py show rbac-matrix
```

## 共同约束

- URL、筛选条件、选中项、编辑草稿和服务端数据必须区分来源，避免出现两份互相漂移的状态。
- 权限由服务端最终判定；前端隐藏或禁用仅用于交互提示。
- 批量操作、导入导出和长耗时任务必须使用真实任务状态，不用固定延时伪造完成。
- 错误提示要说明失败对象、原因和可恢复动作；部分成功不得显示成全部成功。
- E2E 至少验证正常路径、失败路径和权限拒绝；涉及数据写入时还要核对 API 与持久化结果。
