# 可运行参考工程

该工程用于验证 `product-development` 的 React + Ant Design 生产模板能被真实挂载，并能完成列表查询、新增、编辑、删除及失败反馈。数据适配器位于 `src/demo-service.ts`，仅在本参考工程中使用；生产模板不会导入它。

## 已验证范围

- TypeScript 类型检查与 Vite 生产构建
- 直接访问嵌套路由后正常显示列表页
- 查询条件能过滤并恢复列表
- 新增、编辑、删除成功后界面与内存数据一致
- 保存失败时保留弹窗和输入，且不显示伪成功数据
- E2E 执行期间无页面异常、浏览器错误日志和失败请求

执行完整验证：

```bash
npm ci
npm run verify
```

首次运行 Playwright 时，如本机没有 Chromium，执行 `npx playwright install chromium`。
macOS/Linux 已安装 Google Chrome 时，也可执行 `PLAYWRIGHT_CHANNEL=chrome npm run verify`，无需另行下载 Playwright Chromium。

## 能力边界

该工程不证明真实后端、数据库事务、登录鉴权、RBAC、审计记录、文件导入导出或生产部署可用。这些能力必须在目标项目中接入真实服务，并使用项目自己的单元测试、集成测试和 E2E 验证。
