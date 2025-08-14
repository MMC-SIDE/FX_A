// Playwright グローバルティアダウン
import { chromium, FullConfig } from '@playwright/test'

async function globalTeardown(config: FullConfig) {
  console.log('Starting global teardown...')

  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()

  try {
    // テストデータのクリーンアップ（必要に応じて）
    console.log('Cleaning up test data...')
    
    // データベースのテストデータクリアなど
    // await cleanupTestData(page)
    
    // ローカルストレージのクリア
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })

    console.log('Global teardown completed successfully')

  } catch (error) {
    console.error('Global teardown failed:', error)
    // ティアダウンのエラーはテストの失敗にしない
  } finally {
    await context.close()
    await browser.close()
  }
}

export default globalTeardown