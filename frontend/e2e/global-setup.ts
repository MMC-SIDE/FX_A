// Playwright グローバルセットアップ
import { chromium, FullConfig } from '@playwright/test'

async function globalSetup(config: FullConfig) {
  console.log('Starting global setup...')

  // ブラウザとページを起動
  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()

  try {
    // バックエンドサーバーの起動確認
    console.log('Checking backend server availability...')
    const maxRetries = 30
    let retries = 0
    
    while (retries < maxRetries) {
      try {
        const response = await page.request.get('http://localhost:8000/health')
        if (response.ok()) {
          console.log('Backend server is ready')
          break
        }
      } catch (error) {
        console.log(`Backend server not ready, retry ${retries + 1}/${maxRetries}`)
        await new Promise(resolve => setTimeout(resolve, 2000))
        retries++
      }
    }

    if (retries >= maxRetries) {
      console.warn('Backend server is not available, some tests may fail')
    }

    // フロントエンドサーバーの起動確認
    console.log('Checking frontend server availability...')
    retries = 0
    
    while (retries < maxRetries) {
      try {
        const response = await page.request.get('http://localhost:3000/')
        if (response.ok()) {
          console.log('Frontend server is ready')
          break
        }
      } catch (error) {
        console.log(`Frontend server not ready, retry ${retries + 1}/${maxRetries}`)
        await new Promise(resolve => setTimeout(resolve, 2000))
        retries++
      }
    }

    if (retries >= maxRetries) {
      throw new Error('Frontend server is not available')
    }

    // テスト用データの準備（必要に応じて）
    console.log('Setting up test data...')
    
    // 認証やセッションの設定（将来的に必要になる場合）
    // await setupAuthentication(page)
    
    // テスト用の設定データ保存
    await page.evaluate(() => {
      localStorage.setItem('test-mode', 'true')
      localStorage.setItem('backend-url', 'http://localhost:8000')
    })

    console.log('Global setup completed successfully')

  } catch (error) {
    console.error('Global setup failed:', error)
    throw error
  } finally {
    await context.close()
    await browser.close()
  }
}

export default globalSetup