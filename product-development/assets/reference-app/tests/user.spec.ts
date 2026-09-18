import { test, expect } from '@playwright/test'
let pageErrors: string[] = []
let consoleErrors: string[] = []
let failedRequests: string[] = []
let httpErrors: string[] = []
test.beforeEach(async ({ page }) => {
  pageErrors = []
  consoleErrors = []
  failedRequests = []
  httpErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()) })
  page.on('requestfailed', request => failedRequests.push(`${request.method()} ${request.url()}`))
  page.on('response', response => { if (response.status() >= 400) httpErrors.push(`${response.status()} ${response.url()}`) })
})
test.afterEach(() => {
  expect(pageErrors, '页面不应抛出未处理异常').toEqual([])
  expect(consoleErrors, '浏览器控制台不应出现 error').toEqual([])
  expect(failedRequests, '浏览器请求不应失败').toEqual([])
  expect(httpErrors, '浏览器请求不应返回 4xx/5xx').toEqual([])
})

test('直接访问嵌套路由并按查询条件过滤列表', async ({ page }) => {
  await page.goto('/user-management/user')
  const search = page.getByLabel('用户名或邮箱')
  await expect(page.getByRole('cell', { name: '示例用户', exact: true })).toBeVisible()
  await search.fill('不存在的用户')
  await search.press('Enter')
  await expect(page.getByRole('cell', { name: '示例用户', exact: true })).toHaveCount(0)
  await search.fill('demo@example.com')
  await search.press('Enter')
  await expect(page.getByRole('cell', { name: '示例用户', exact: true })).toBeVisible()
})

test('真实组件：新增成功后显示，删除成功后消失', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('cell', { name: '示例用户', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '新增用户' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('用户名').fill('测试新增')
  await dialog.getByLabel('邮箱').fill('test@example.com')
  await dialog.getByRole('button', { name: 'OK' }).click()
  await expect(dialog).not.toBeVisible()
  const row = page.getByRole('row').filter({ hasText: '测试新增' })
  await expect(row).toBeVisible()
  await row.getByRole('button', { name: /删\s*除/ }).click()
  await page.getByRole('button', { name: 'OK', exact: true }).click()
  await expect(row).toHaveCount(0)
})

test('编辑成功后重新查询并显示服务返回的数据', async ({ page }) => {
  await page.goto('/')
  const row = page.getByRole('row').filter({ hasText: '示例用户' })
  await row.getByRole('button', { name: /编\s*辑/ }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('邮箱').fill('updated@example.com')
  await dialog.getByRole('button', { name: 'OK' }).click()
  await expect(dialog).not.toBeVisible()
  await expect(page.getByRole('cell', { name: 'updated@example.com', exact: true })).toBeVisible()
})

test('保存失败时保留弹窗与输入，不伪装成功', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '新增用户' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('用户名').fill('失败用户')
  await dialog.getByLabel('邮箱').fill('fail@example.com')
  await dialog.getByRole('button', { name: 'OK' }).click()
  await expect(dialog).toBeVisible()
  await expect(dialog.getByLabel('邮箱')).toHaveValue('fail@example.com')
  await expect(page.getByRole('alert')).toContainText('演示保存失败')
  await expect(page.getByRole('cell', { name: '失败用户', exact: true })).toHaveCount(0)
})
