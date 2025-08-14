import { test, expect } from '@playwright/test'

test.describe('Trading System E2E', () => {
  test.beforeEach(async ({ page }) => {
    // ホームページに移動
    await page.goto('/')
    
    // ページが完全に読み込まれるまで待機
    await page.waitForLoadState('networkidle')
  })

  test('can navigate to dashboard', async ({ page }) => {
    // ダッシュボードリンクをクリック
    await page.click('text=ダッシュボード')
    
    // ダッシュボードページのURLを確認
    await expect(page).toHaveURL('/dashboard')
    
    // ダッシュボードのタイトルが表示されることを確認
    await expect(page.locator('h4')).toContainText('ダッシュボード')
    
    // 主要なダッシュボードコンポーネントが表示されることを確認
    await expect(page.locator('[data-testid=trading-panel]')).toBeVisible()
    await expect(page.locator('[data-testid=position-list]')).toBeVisible()
    await expect(page.locator('[data-testid=system-stats]')).toBeVisible()
  })

  test('can start and stop trading', async ({ page }) => {
    await page.goto('/dashboard')
    
    // 取引開始ボタンが表示されることを確認
    const startButton = page.locator('button:has-text("取引開始")')
    await expect(startButton).toBeVisible()
    
    // 取引開始ボタンをクリック
    await startButton.click()
    
    // 確認ダイアログが表示される場合は確認
    const confirmDialog = page.locator('text=取引を開始しますか？')
    if (await confirmDialog.isVisible()) {
      await page.click('button:has-text("はい")')
    }
    
    // 稼働中ステータスが表示されることを確認
    await expect(page.locator('text=稼働中')).toBeVisible({ timeout: 10000 })
    
    // 取引停止ボタンが表示されることを確認
    const stopButton = page.locator('button:has-text("取引停止")')
    await expect(stopButton).toBeVisible()
    
    // 取引停止ボタンをクリック
    await stopButton.click()
    
    // 停止確認ダイアログが表示される場合は確認
    const stopConfirmDialog = page.locator('text=取引を停止しますか？')
    if (await stopConfirmDialog.isVisible()) {
      await page.click('button:has-text("はい")')
    }
    
    // 停止中ステータスが表示されることを確認
    await expect(page.locator('text=停止中')).toBeVisible({ timeout: 10000 })
  })

  test('can view and manage positions', async ({ page }) => {
    await page.goto('/dashboard')
    
    // ポジション一覧が表示されることを確認
    const positionList = page.locator('[data-testid=position-list]')
    await expect(positionList).toBeVisible()
    
    // ポジションが存在する場合の操作をテスト
    const positionRows = page.locator('[data-testid=position-row]')
    const positionCount = await positionRows.count()
    
    if (positionCount > 0) {
      // 最初のポジションを選択
      const firstPosition = positionRows.first()
      await expect(firstPosition).toBeVisible()
      
      // ポジション詳細情報が表示されることを確認
      await expect(firstPosition.locator('text=USDJPY')).toBeVisible()
      await expect(firstPosition.locator('[data-testid=current-profit]')).toBeVisible()
      
      // ポジション決済ボタンをテスト
      const closeButton = firstPosition.locator('button:has-text("決済")')
      if (await closeButton.isVisible()) {
        await closeButton.click()
        
        // 決済確認ダイアログ
        const confirmDialog = page.locator('text=このポジションを決済しますか？')
        if (await confirmDialog.isVisible()) {
          await page.click('button:has-text("キャンセル")') // テストなのでキャンセル
        }
      }
    }
  })

  test('can view trading history', async ({ page }) => {
    await page.goto('/dashboard')
    
    // 取引履歴タブまたはリンクをクリック
    await page.click('text=取引履歴')
    
    // 取引履歴テーブルが表示されることを確認
    const historyTable = page.locator('[data-testid=trading-history]')
    await expect(historyTable).toBeVisible()
    
    // フィルター機能をテスト
    const symbolFilter = page.locator('[data-testid=symbol-filter]')
    if (await symbolFilter.isVisible()) {
      await symbolFilter.selectOption('USDJPY')
      
      // フィルター結果が表示されることを確認
      await page.waitForTimeout(1000)
      const filteredRows = page.locator('[data-testid=history-row]')
      if (await filteredRows.count() > 0) {
        await expect(filteredRows.first().locator('text=USDJPY')).toBeVisible()
      }
    }
    
    // ページネーション機能をテスト
    const nextPageButton = page.locator('button:has-text("次へ")')
    if (await nextPageButton.isVisible() && await nextPageButton.isEnabled()) {
      await nextPageButton.click()
      await page.waitForTimeout(1000)
    }
  })

  test('can adjust trading settings', async ({ page }) => {
    await page.goto('/dashboard')
    
    // 設定ボタンまたはリンクをクリック
    await page.click('text=設定')
    
    // 設定画面が表示されることを確認
    await expect(page.locator('h4:has-text("取引設定")')).toBeVisible()
    
    // 通貨ペア設定
    const symbolSelect = page.locator('[data-testid=symbol-select]')
    if (await symbolSelect.isVisible()) {
      await symbolSelect.selectOption('EURJPY')
    }
    
    // 時間軸設定
    const timeframeSelect = page.locator('[data-testid=timeframe-select]')
    if (await timeframeSelect.isVisible()) {
      await timeframeSelect.selectOption('M15')
    }
    
    // リスク設定
    const riskInput = page.locator('[data-testid=risk-per-trade]')
    if (await riskInput.isVisible()) {
      await riskInput.clear()
      await riskInput.fill('1.5')
    }
    
    // 信頼度設定
    const confidenceInput = page.locator('[data-testid=min-confidence]')
    if (await confidenceInput.isVisible()) {
      await confidenceInput.clear()
      await confidenceInput.fill('0.8')
    }
    
    // 設定保存ボタンをクリック
    const saveButton = page.locator('button:has-text("保存")')
    await expect(saveButton).toBeVisible()
    await saveButton.click()
    
    // 保存成功メッセージが表示されることを確認
    await expect(page.locator('text=設定が保存されました')).toBeVisible({ timeout: 5000 })
  })

  test('displays real-time market data', async ({ page }) => {
    await page.goto('/dashboard')
    
    // リアルタイムデータ表示エリアが存在することを確認
    const marketDataPanel = page.locator('[data-testid=market-data-panel]')
    await expect(marketDataPanel).toBeVisible()
    
    // WebSocket接続状態の確認
    const connectionStatus = page.locator('[data-testid=connection-status]')
    await expect(connectionStatus).toContainText('接続中')
    
    // 現在価格が表示されることを確認
    const currentPrice = page.locator('[data-testid=current-price]')
    await expect(currentPrice).toBeVisible()
    
    // スプレッド情報が表示されることを確認
    const spread = page.locator('[data-testid=spread]')
    await expect(spread).toBeVisible()
    
    // 価格の更新を確認（5秒待機して値が変化する可能性をチェック）
    const initialPrice = await currentPrice.textContent()
    await page.waitForTimeout(5000)
    
    // 注意: 実際の市場データの更新は市場状況に依存するため、
    // ここでは単純に価格表示が維持されていることを確認
    await expect(currentPrice).toBeVisible()
  })

  test('can view system monitoring', async ({ page }) => {
    await page.goto('/monitoring')
    
    // 監視画面が表示されることを確認
    await expect(page.locator('h4:has-text("システム監視")')).toBeVisible()
    
    // システム統計カードが表示されることを確認
    await expect(page.locator('[data-testid=cpu-usage]')).toBeVisible()
    await expect(page.locator('[data-testid=memory-usage]')).toBeVisible()
    await expect(page.locator('[data-testid=disk-usage]')).toBeVisible()
    
    // アラート一覧が表示されることを確認
    const alertPanel = page.locator('[data-testid=alert-panel]')
    await expect(alertPanel).toBeVisible()
    
    // ログビューアが表示されることを確認
    const logViewer = page.locator('[data-testid=log-viewer]')
    await expect(logViewer).toBeVisible()
    
    // ログタイプ切り替えをテスト
    const logTypeSelect = page.locator('[data-testid=log-type-select]')
    if (await logTypeSelect.isVisible()) {
      await logTypeSelect.selectOption('trading')
      await page.waitForTimeout(1000)
      
      // 取引ログが表示されることを確認
      const logEntries = page.locator('[data-testid=log-entry]')
      if (await logEntries.count() > 0) {
        await expect(logEntries.first()).toBeVisible()
      }
    }
  })

  test('can handle alerts', async ({ page }) => {
    await page.goto('/monitoring')
    
    // アラート一覧が表示されることを確認
    const alertList = page.locator('[data-testid=alert-list]')
    await expect(alertList).toBeVisible()
    
    // アラートが存在する場合の操作をテスト
    const alertItems = page.locator('[data-testid=alert-item]')
    const alertCount = await alertItems.count()
    
    if (alertCount > 0) {
      const firstAlert = alertItems.first()
      
      // アラート確認ボタンをテスト
      const acknowledgeButton = firstAlert.locator('button:has-text("確認")')
      if (await acknowledgeButton.isVisible()) {
        await acknowledgeButton.click()
        
        // 確認済みステータスが表示されることを確認
        await expect(firstAlert.locator('text=確認済み')).toBeVisible({ timeout: 5000 })
      }
      
      // アラート削除ボタンをテスト
      const dismissButton = firstAlert.locator('button:has-text("削除")')
      if (await dismissButton.isVisible()) {
        await dismissButton.click()
        
        // 削除確認ダイアログ
        const confirmDialog = page.locator('text=このアラートを削除しますか？')
        if (await confirmDialog.isVisible()) {
          await page.click('button:has-text("キャンセル")') // テストなのでキャンセル
        }
      }
    }
    
    // アラートフィルター機能をテスト
    const levelFilter = page.locator('[data-testid=alert-level-filter]')
    if (await levelFilter.isVisible()) {
      await levelFilter.selectOption('ERROR')
      await page.waitForTimeout(1000)
      
      // エラーレベルのアラートのみ表示されることを確認
      const filteredAlerts = page.locator('[data-testid=alert-item]')
      if (await filteredAlerts.count() > 0) {
        await expect(filteredAlerts.first().locator('text=ERROR')).toBeVisible()
      }
    }
  })

  test('can navigate between pages', async ({ page }) => {
    await page.goto('/')
    
    // ナビゲーションメニューが表示されることを確認
    const navigation = page.locator('[data-testid=navigation]')
    await expect(navigation).toBeVisible()
    
    // 各ページへのナビゲーションをテスト
    const pages = [
      { name: 'ダッシュボード', url: '/dashboard' },
      { name: 'バックテスト', url: '/backtest' },
      { name: '分析', url: '/analysis' },
      { name: '監視', url: '/monitoring' },
      { name: '設定', url: '/settings' }
    ]
    
    for (const pageInfo of pages) {
      // ページリンクをクリック
      await page.click(`text=${pageInfo.name}`)
      
      // URLが正しいことを確認
      await expect(page).toHaveURL(pageInfo.url)
      
      // ページが読み込まれることを確認
      await page.waitForLoadState('networkidle')
      
      // ページタイトルが表示されることを確認
      await expect(page.locator('h4')).toContainText(pageInfo.name)
    }
  })

  test('handles network errors gracefully', async ({ page }) => {
    await page.goto('/dashboard')
    
    // ネットワークエラーをシミュレート
    await page.route('**/api/**', route => {
      route.abort('connectionrefused')
    })
    
    // 何らかのAPI呼び出しを試行（例：取引開始）
    const startButton = page.locator('button:has-text("取引開始")')
    if (await startButton.isVisible()) {
      await startButton.click()
      
      // エラーメッセージが表示されることを確認
      await expect(page.locator('text=ネットワークエラー')).toBeVisible({ timeout: 10000 })
    }
    
    // ネットワークエラーのルーティングを解除
    await page.unroute('**/api/**')
  })

  test('responsive design works on mobile', async ({ page }) => {
    // モバイルビューポートに設定
    await page.setViewportSize({ width: 375, height: 812 })
    
    await page.goto('/dashboard')
    
    // モバイルナビゲーションメニューが表示されることを確認
    const mobileMenu = page.locator('[data-testid=mobile-menu]')
    if (await mobileMenu.isVisible()) {
      await mobileMenu.click()
      
      // メニューアイテムが表示されることを確認
      await expect(page.locator('[data-testid=mobile-menu-items]')).toBeVisible()
    }
    
    // モバイルレイアウトでコンポーネントが適切に表示されることを確認
    const tradingPanel = page.locator('[data-testid=trading-panel]')
    await expect(tradingPanel).toBeVisible()
    
    // スクロール可能であることを確認
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await page.waitForTimeout(500)
    await page.evaluate(() => window.scrollTo(0, 0))
  })
})