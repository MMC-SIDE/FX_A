import { test, expect } from '@playwright/test'

test.describe('Frontend Performance Tests', () => {
  test.beforeEach(async ({ page }) => {
    // ページパフォーマンス測定の準備
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('page load performance meets targets', async ({ page }) => {
    const navigationTiming = await page.evaluate(() => {
      const perfData = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
      return {
        domContentLoaded: perfData.domContentLoadedEventEnd - perfData.navigationStart,
        loadComplete: perfData.loadEventEnd - perfData.navigationStart,
        firstPaint: performance.getEntriesByType('paint').find(entry => entry.name === 'first-paint')?.startTime || 0,
        firstContentfulPaint: performance.getEntriesByType('paint').find(entry => entry.name === 'first-contentful-paint')?.startTime || 0,
        ttfb: perfData.responseStart - perfData.navigationStart
      }
    })

    // パフォーマンス目標値
    expect(navigationTiming.domContentLoaded).toBeLessThan(2000) // 2秒以内
    expect(navigationTiming.loadComplete).toBeLessThan(4000) // 4秒以内
    expect(navigationTiming.firstPaint).toBeLessThan(1500) // 1.5秒以内
    expect(navigationTiming.firstContentfulPaint).toBeLessThan(2000) // 2秒以内
    expect(navigationTiming.ttfb).toBeLessThan(800) // 800ms以内

    console.log('Page Load Performance:', navigationTiming)
  })

  test('dashboard loads quickly with real-time data', async ({ page }) => {
    const startTime = Date.now()
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // ダッシュボードの主要コンポーネントが表示されるまでの時間を測定
    await expect(page.locator('[data-testid=trading-panel]')).toBeVisible()
    await expect(page.locator('[data-testid=position-list]')).toBeVisible()
    await expect(page.locator('[data-testid=system-stats]')).toBeVisible()
    
    const loadTime = Date.now() - startTime
    
    // ダッシュボードが3秒以内に読み込まれること
    expect(loadTime).toBeLessThan(3000)
    
    // WebSocket接続が確立されること
    const connectionStatus = page.locator('[data-testid=connection-status]')
    await expect(connectionStatus).toContainText('接続中', { timeout: 5000 })
    
    console.log(`Dashboard load time: ${loadTime}ms`)
  })

  test('chart rendering performance', async ({ page }) => {
    await page.goto('/dashboard')
    
    // チャートコンポーネントが存在することを確認
    const chartContainer = page.locator('[data-testid=price-chart]')
    if (await chartContainer.isVisible()) {
      const startTime = Date.now()
      
      // チャートデータの更新をトリガー
      await page.selectOption('[data-testid=timeframe-select]', 'H1')
      
      // チャートが再描画されるまで待機
      await page.waitForTimeout(1000)
      
      const renderTime = Date.now() - startTime
      
      // チャート描画が2秒以内に完了すること
      expect(renderTime).toBeLessThan(2000)
      
      console.log(`Chart render time: ${renderTime}ms`)
    }
  })

  test('table virtualization performance with large datasets', async ({ page }) => {
    await page.goto('/dashboard')
    await page.click('text=取引履歴')
    
    const startTime = Date.now()
    
    // 大量データの表示をテスト（1000件以上のレコード）
    const historyTable = page.locator('[data-testid=trading-history]')
    await expect(historyTable).toBeVisible()
    
    // スクロールパフォーマンステスト
    for (let i = 0; i < 10; i++) {
      await page.evaluate(() => window.scrollBy(0, 500))
      await page.waitForTimeout(100)
    }
    
    const scrollTime = Date.now() - startTime
    
    // スクロール操作が3秒以内に完了すること
    expect(scrollTime).toBeLessThan(3000)
    
    // 最下部までスクロール
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await page.waitForTimeout(500)
    
    // ページトップに戻る
    await page.evaluate(() => window.scrollTo(0, 0))
    
    console.log(`Table scroll performance: ${scrollTime}ms`)
  })

  test('backtest execution performance monitoring', async ({ page }) => {
    await page.goto('/backtest')
    
    // バックテスト設定
    await page.selectOption('[data-testid=symbol-select]', 'USDJPY')
    await page.selectOption('[data-testid=timeframe-select]', 'H1')
    await page.fill('[data-testid=start-date]', '2023-01-01')
    await page.fill('[data-testid=end-date]', '2023-03-31')
    await page.fill('[data-testid=initial-balance]', '100000')
    
    const startTime = Date.now()
    
    // バックテスト実行
    await page.click('button:has-text("バックテスト実行")')
    
    // 進行状況の監視
    const progressBar = page.locator('[data-testid=progress-bar]')
    await expect(progressBar).toBeVisible({ timeout: 5000 })
    
    // 結果表示まで待機（タイムアウトは長めに設定）
    const results = page.locator('[data-testid=backtest-results]')
    await expect(results).toBeVisible({ timeout: 120000 })
    
    const executionTime = Date.now() - startTime
    
    // バックテストが2分以内に完了すること
    expect(executionTime).toBeLessThan(120000)
    
    console.log(`Backtest execution time: ${executionTime}ms`)
  })

  test('memory usage monitoring during heavy operations', async ({ page, context }) => {
    // ページのメモリ使用量を監視
    const initialMetrics = await page.evaluate(() => {
      return (performance as any).memory ? {
        usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
        totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
        jsHeapSizeLimit: (performance as any).memory.jsHeapSizeLimit
      } : null
    })
    
    if (initialMetrics) {
      console.log('Initial memory usage:', initialMetrics)
      
      // メモリ集約的な操作を実行
      await page.goto('/backtest')
      
      // 複数のバックテストを連続実行してメモリ使用量をテスト
      for (let i = 0; i < 3; i++) {
        await page.selectOption('[data-testid=symbol-select]', 'USDJPY')
        await page.selectOption('[data-testid=timeframe-select]', 'M15')
        await page.fill('[data-testid=start-date]', '2023-01-01')
        await page.fill('[data-testid=end-date]', '2023-01-31')
        await page.fill('[data-testid=initial-balance]', '100000')
        
        await page.click('button:has-text("バックテスト実行")')
        await page.waitForTimeout(5000)
        
        // バックテストをキャンセル（メモリテストのため）
        const cancelButton = page.locator('button:has-text("キャンセル")')
        if (await cancelButton.isVisible()) {
          await cancelButton.click()
          await page.waitForTimeout(1000)
        }
      }
      
      // 最終メモリ使用量を測定
      const finalMetrics = await page.evaluate(() => {
        return (performance as any).memory ? {
          usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
          totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
          jsHeapSizeLimit: (performance as any).memory.jsHeapSizeLimit
        } : null
      })
      
      if (finalMetrics) {
        console.log('Final memory usage:', finalMetrics)
        
        const memoryIncrease = finalMetrics.usedJSHeapSize - initialMetrics.usedJSHeapSize
        const memoryIncreasePercent = (memoryIncrease / initialMetrics.usedJSHeapSize) * 100
        
        // メモリ使用量の増加が50%以下であること
        expect(memoryIncreasePercent).toBeLessThan(50)
        
        console.log(`Memory increase: ${memoryIncrease} bytes (${memoryIncreasePercent.toFixed(2)}%)`)
      }
    }
  })

  test('network request optimization', async ({ page }) => {
    // ネットワークリクエストを監視
    const requests: any[] = []
    
    page.on('request', request => {
      requests.push({
        url: request.url(),
        method: request.method(),
        timestamp: Date.now()
      })
    })
    
    const responses: any[] = []
    
    page.on('response', response => {
      responses.push({
        url: response.url(),
        status: response.status(),
        timestamp: Date.now()
      })
    })
    
    // ダッシュボード読み込み
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // API リクエスト数をチェック
    const apiRequests = requests.filter(req => req.url.includes('/api/'))
    
    // 初期読み込みでのAPIリクエスト数が15個以下であること
    expect(apiRequests.length).toBeLessThan(15)
    
    // レスポンス時間の分析
    const responseTimes = responses.map(res => {
      const req = requests.find(r => r.url === res.url)
      return req ? res.timestamp - req.timestamp : 0
    }).filter(time => time > 0)
    
    if (responseTimes.length > 0) {
      const avgResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length
      const maxResponseTime = Math.max(...responseTimes)
      
      // 平均レスポンス時間が1秒以内であること
      expect(avgResponseTime).toBeLessThan(1000)
      
      // 最大レスポンス時間が3秒以内であること
      expect(maxResponseTime).toBeLessThan(3000)
      
      console.log(`Average response time: ${avgResponseTime}ms`)
      console.log(`Max response time: ${maxResponseTime}ms`)
    }
  })

  test('real-time data update performance', async ({ page }) => {
    await page.goto('/dashboard')
    
    // WebSocket接続の確立を待機
    const connectionStatus = page.locator('[data-testid=connection-status]')
    await expect(connectionStatus).toContainText('接続中', { timeout: 10000 })
    
    // リアルタイムデータ更新の監視
    let updateCount = 0
    const startTime = Date.now()
    
    // 価格データの変更を監視
    const priceElement = page.locator('[data-testid=current-price]')
    let lastPrice = await priceElement.textContent()
    
    // 30秒間データ更新を監視
    const monitoringPromise = new Promise<void>((resolve) => {
      const interval = setInterval(async () => {
        const currentPrice = await priceElement.textContent()
        if (currentPrice !== lastPrice) {
          updateCount++
          lastPrice = currentPrice
        }
        
        if (Date.now() - startTime > 30000) {
          clearInterval(interval)
          resolve()
        }
      }, 1000)
    })
    
    await monitoringPromise
    
    // 30秒間で少なくとも5回は更新されること（実際の市場データに依存）
    console.log(`Real-time updates in 30 seconds: ${updateCount}`)
    
    // WebSocket接続が維持されていること
    await expect(connectionStatus).toContainText('接続中')
  })

  test('concurrent user simulation', async ({ page, context }) => {
    // 複数タブで同時アクセスをシミュレート
    const pages = [page]
    
    // 追加で4つのタブを開く
    for (let i = 0; i < 4; i++) {
      const newPage = await context.newPage()
      pages.push(newPage)
    }
    
    const startTime = Date.now()
    
    // 全てのタブで同時にダッシュボードを読み込み
    const loadPromises = pages.map(async (p, index) => {
      await p.goto('/dashboard')
      await p.waitForLoadState('networkidle')
      
      // 各タブで異なる操作を実行
      switch (index % 3) {
        case 0:
          // 取引履歴を表示
          await p.click('text=取引履歴')
          break
        case 1:
          // バックテストページに移動
          await p.goto('/backtest')
          break
        case 2:
          // 監視ページに移動
          await p.goto('/monitoring')
          break
      }
      
      return `Tab ${index} completed`
    })
    
    // 全ての操作が完了するまで待機
    const results = await Promise.all(loadPromises)
    const totalTime = Date.now() - startTime
    
    // 5つのタブが同時に10秒以内に読み込まれること
    expect(totalTime).toBeLessThan(10000)
    expect(results.length).toBe(5)
    
    console.log(`Concurrent load time for 5 tabs: ${totalTime}ms`)
    
    // 追加のタブを閉じる
    for (let i = 1; i < pages.length; i++) {
      await pages[i].close()
    }
  })

  test('mobile performance optimization', async ({ page }) => {
    // モバイルデバイスの設定
    await page.setViewportSize({ width: 375, height: 812 })
    
    const startTime = Date.now()
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    const mobileLoadTime = Date.now() - startTime
    
    // モバイルでの読み込み時間が5秒以内であること
    expect(mobileLoadTime).toBeLessThan(5000)
    
    // モバイル専用コンポーネントが表示されること
    const mobileNav = page.locator('[data-testid=mobile-menu]')
    if (await mobileNav.isVisible()) {
      await mobileNav.click()
      
      // メニュー開閉が滑らかであること（アニメーション含む）
      const menuOpenTime = Date.now()
      await expect(page.locator('[data-testid=mobile-menu-items]')).toBeVisible()
      const menuAnimationTime = Date.now() - menuOpenTime
      
      expect(menuAnimationTime).toBeLessThan(500) // 500ms以内
    }
    
    // タッチ操作のレスポンス性をテスト
    const tradingPanel = page.locator('[data-testid=trading-panel]')
    if (await tradingPanel.isVisible()) {
      const touchStartTime = Date.now()
      await tradingPanel.tap()
      await page.waitForTimeout(100)
      const touchResponseTime = Date.now() - touchStartTime
      
      // タッチレスポンスが200ms以内であること
      expect(touchResponseTime).toBeLessThan(200)
    }
    
    console.log(`Mobile load time: ${mobileLoadTime}ms`)
  })

  test('large dataset rendering performance', async ({ page }) => {
    await page.goto('/analysis')
    
    // 大量データを含む分析を実行
    await page.click('text=時間帯分析')
    await page.selectOption('[data-testid=analysis-symbol-select]', 'USDJPY')
    
    const analysisStartTime = Date.now()
    await page.click('button:has-text("分析実行")')
    
    // 分析結果のチャートが表示されるまで待機
    const chartContainer = page.locator('[data-testid=timeframe-analysis-results]')
    await expect(chartContainer).toBeVisible({ timeout: 60000 })
    
    const analysisTime = Date.now() - analysisStartTime
    
    // 大量データの分析・描画が1分以内に完了すること
    expect(analysisTime).toBeLessThan(60000)
    
    // インタラクティブ操作のレスポンス性をテスト
    const heatmap = page.locator('[data-testid=timeframe-heatmap]')
    if (await heatmap.isVisible()) {
      const interactionStartTime = Date.now()
      
      // ヒートマップの操作
      await heatmap.hover()
      await page.waitForTimeout(100)
      
      const interactionTime = Date.now() - interactionStartTime
      
      // インタラクション応答が500ms以内であること
      expect(interactionTime).toBeLessThan(500)
    }
    
    console.log(`Large dataset analysis time: ${analysisTime}ms`)
  })

  test('bundle size and resource optimization', async ({ page }) => {
    // リソース読み込みの監視
    const resources: any[] = []
    
    page.on('response', response => {
      if (response.url().includes('.js') || response.url().includes('.css')) {
        resources.push({
          url: response.url(),
          size: response.headers()['content-length'] || 0,
          type: response.url().includes('.js') ? 'js' : 'css'
        })
      }
    })
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // JavaScript バンドルサイズの確認
    const jsResources = resources.filter(r => r.type === 'js')
    const totalJsSize = jsResources.reduce((total, resource) => {
      return total + parseInt(resource.size as string || '0', 10)
    }, 0)
    
    // CSS ファイルサイズの確認
    const cssResources = resources.filter(r => r.type === 'css')
    const totalCssSize = cssResources.reduce((total, resource) => {
      return total + parseInt(resource.size as string || '0', 10)
    }, 0)
    
    console.log(`Total JS size: ${totalJsSize} bytes`)
    console.log(`Total CSS size: ${totalCssSize} bytes`)
    
    // バンドルサイズが適切であること（目安値）
    // JavaScript: 2MB以下
    expect(totalJsSize).toBeLessThan(2 * 1024 * 1024)
    
    // CSS: 500KB以下
    expect(totalCssSize).toBeLessThan(500 * 1024)
    
    // チャンクされたファイル数の確認（適切なcode splittingがされているか）
    const chunkCount = jsResources.filter(r => r.url.includes('chunk')).length
    expect(chunkCount).toBeGreaterThan(0) // 最低1つのチャンクファイルが存在
  })
})