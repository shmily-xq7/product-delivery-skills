import { createRoot } from 'react-dom/client'
import { ConfigProvider } from 'antd'
import { RouterProvider } from 'react-router-dom'
import { createUserRouter } from '../../templates/TabsPage/routes'
import { demoService } from './demo-service'
import '../../../../product-ui-spec/references/tokens.css'
const router = createUserRouter(demoService)
const token = getComputedStyle(document.documentElement)
createRoot(document.getElementById('root')!).render(<ConfigProvider theme={{ token: { colorPrimary: token.getPropertyValue('--color-primary').trim() } }}>
  <p>演示模式：数据仅存于当前浏览器内存，刷新后重置。</p><RouterProvider router={router} />
</ConfigProvider>)
