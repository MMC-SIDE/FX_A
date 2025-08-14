import { test, expect } from '@playwright/test'

test.describe('Monitoring System E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/monitoring')
    await page.waitForLoadState('networkidle')
  })

  test('can view system monitoring dashboard', async ({ page }) => {
    // 監視ダッシュボードが表示されることを確認
    await expect(page.locator('h4:has-text("システム監視")')).toBeVisible()
    
    // システム統計カードが表示されることを確認
    const systemStatsCards = [
      'cpu-usage-card',
      'memory-usage-card', 
      'disk-usage-card',
      'network-io-card'
    ]
    
    for (const cardId of systemStatsCards) {
      const card = page.locator(`[data-testid=${cardId}]`)
      await expect(card).toBeVisible()
      
      // 使用率の値が表示されることを確認
      const usageValue = card.locator('[data-testid=usage-value]')
      await expect(usageValue).toBeVisible()
      
      // プログレスバーが表示されることを確認
      const progressBar = card.locator('[data-testid=usage-progress]')
      await expect(progressBar).toBeVisible()
    }
    
    // 接続状態インジケーター
    const connectionStatus = page.locator('[data-testid=connection-status]')
    await expect(connectionStatus).toBeVisible()
    
    // MT5接続状態
    const mt5Status = page.locator('[data-testid=mt5-connection-status]')
    await expect(mt5Status).toBeVisible()
    
    // データベース接続状態
    const dbStatus = page.locator('[data-testid=database-connection-status]')
    await expect(dbStatus).toBeVisible()
  })

  test('can view and manage alerts', async ({ page }) => {
    // アラートパネルが表示されることを確認
    const alertPanel = page.locator('[data-testid=alert-panel]')
    await expect(alertPanel).toBeVisible()
    
    // アラートタブが表示されることを確認
    const alertTabs = ['アクティブ', '履歴', 'すべて']
    for (const tab of alertTabs) {
      const tabElement = page.locator(`text=${tab}`)
      await expect(tabElement).toBeVisible()
    }
    
    // アクティブアラートを表示
    await page.click('text=アクティブ')
    
    // アラート一覧が表示されることを確認
    const alertList = page.locator('[data-testid=alert-list]')
    await expect(alertList).toBeVisible()
    
    // アラートフィルター機能をテスト
    const levelFilter = page.locator('[data-testid=alert-level-filter]')
    if (await levelFilter.isVisible()) {
      await levelFilter.selectOption('ERROR')
      await page.waitForTimeout(1000)
      
      // フィルター結果の確認
      const filteredAlerts = page.locator('[data-testid=alert-item]')
      if (await filteredAlerts.count() > 0) {
        await expect(filteredAlerts.first().locator('text=ERROR')).toBeVisible()
      }
      
      // フィルターをリセット
      await levelFilter.selectOption('ALL')
    }
    
    // アラートアクションをテスト
    const alertItems = page.locator('[data-testid=alert-item]')
    const alertCount = await alertItems.count()
    
    if (alertCount > 0) {
      const firstAlert = alertItems.first()
      
      // アラート詳細の展開
      const expandButton = firstAlert.locator('[data-testid=alert-expand]')
      if (await expandButton.isVisible()) {
        await expandButton.click()
        
        // 詳細情報が表示されることを確認
        const alertDetails = firstAlert.locator('[data-testid=alert-details]')
        await expect(alertDetails).toBeVisible()
      }
      
      // アラート確認
      const acknowledgeButton = firstAlert.locator('button:has-text("確認")')
      if (await acknowledgeButton.isVisible()) {
        await acknowledgeButton.click()
        
        // 確認済みマークが表示されることを確認
        const acknowledgedMark = firstAlert.locator('[data-testid=acknowledged-mark]')
        await expect(acknowledgedMark).toBeVisible({ timeout: 5000 })
      }
    }
  })

  test('can view system logs', async ({ page }) => {
    // ログビューアーが表示されることを確認
    const logViewer = page.locator('[data-testid=log-viewer]')
    await expect(logViewer).toBeVisible()
    
    // ログタイプ選択が表示されることを確認
    const logTypeSelect = page.locator('[data-testid=log-type-select]')
    await expect(logTypeSelect).toBeVisible()
    
    // 異なるログタイプをテスト
    const logTypes = ['system', 'trading', 'error', 'api']
    for (const logType of logTypes) {
      await logTypeSelect.selectOption(logType)
      await page.waitForTimeout(2000)
      
      // ログエントリが表示されることを確認
      const logEntries = page.locator('[data-testid=log-entry]')
      if (await logEntries.count() > 0) {
        // ログエントリの構造確認
        const firstEntry = logEntries.first()
        await expect(firstEntry.locator('[data-testid=log-timestamp]')).toBeVisible()
        await expect(firstEntry.locator('[data-testid=log-level]')).toBeVisible()
        await expect(firstEntry.locator('[data-testid=log-message]')).toBeVisible()
      }
    }
    
    // ログレベルフィルター
    const logLevelFilter = page.locator('[data-testid=log-level-filter]')
    if (await logLevelFilter.isVisible()) {
      await logLevelFilter.selectOption('ERROR')
      await page.waitForTimeout(1000)
      
      // エラーレベルのログのみ表示されることを確認
      const errorLogs = page.locator('[data-testid=log-entry]')
      if (await errorLogs.count() > 0) {
        await expect(errorLogs.first().locator('text=ERROR')).toBeVisible()
      }
    }
    
    // ログ検索機能
    const logSearchInput = page.locator('[data-testid=log-search-input]')
    if (await logSearchInput.isVisible()) {
      await logSearchInput.fill('connection')
      await page.click('button:has-text("検索")')
      await page.waitForTimeout(2000)
      
      // 検索結果が表示されることを確認
      const searchResults = page.locator('[data-testid=log-search-results]')
      if (await searchResults.isVisible()) {
        await expect(searchResults).toBeVisible()
      }
    }
    
    // ログの自動更新確認
    const autoRefreshToggle = page.locator('[data-testid=auto-refresh-toggle]')
    if (await autoRefreshToggle.isVisible()) {
      await autoRefreshToggle.check()
      
      // 自動更新が有効になったことを確認
      await expect(autoRefreshToggle).toBeChecked()
    }
  })

  test('can view real-time performance metrics', async ({ page }) => {
    // パフォーマンスメトリクス画面に移動
    const metricsTab = page.locator('text=パフォーマンス')
    if (await metricsTab.isVisible()) {
      await metricsTab.click()
    }
    
    // リアルタイムチャートが表示されることを確認
    const realtimeCharts = [
      'cpu-usage-chart',
      'memory-usage-chart',
      'network-io-chart',
      'disk-io-chart'
    ]
    
    for (const chartId of realtimeCharts) {
      const chart = page.locator(`[data-testid=${chartId}]`)
      await expect(chart).toBeVisible()
    }
    
    // データの更新間隔設定
    const updateInterval = page.locator('[data-testid=update-interval-select]')
    if (await updateInterval.isVisible()) {
      await updateInterval.selectOption('5') // 5秒間隔
      
      // 間隔が適用されることを確認
      await page.waitForTimeout(6000)
      
      // チャートが更新されることを確認
      const lastUpdate = page.locator('[data-testid=last-update-time]')
      await expect(lastUpdate).toBeVisible()
    }
    
    // 時間範囲の変更
    const timeRange = page.locator('[data-testid=time-range-select]')
    if (await timeRange.isVisible()) {
      await timeRange.selectOption('1hour')
      await page.waitForTimeout(2000)
      
      // チャートが更新されることを確認
      const chartContainer = page.locator('[data-testid=metrics-chart-container]')
      await expect(chartContainer).toBeVisible()
    }
    
    // パフォーマンス統計サマリー
    const performanceStats = page.locator('[data-testid=performance-stats]')
    await expect(performanceStats).toBeVisible()
    
    // 平均値、最大値、最小値の表示確認
    await expect(performanceStats.locator('text=平均')).toBeVisible()
    await expect(performanceStats.locator('text=最大')).toBeVisible()
    await expect(performanceStats.locator('text=最小')).toBeVisible()
  })

  test('can configure alert settings', async ({ page }) => {
    // アラート設定ボタンをクリック
    const alertSettingsButton = page.locator('button:has-text("アラート設定")')
    if (await alertSettingsButton.isVisible()) {
      await alertSettingsButton.click()
      
      // アラート設定ダイアログが表示されることを確認
      const alertSettingsDialog = page.locator('[data-testid=alert-settings-dialog]')
      await expect(alertSettingsDialog).toBeVisible()
      
      // システムリソースアラート設定
      const cpuThreshold = page.locator('[data-testid=cpu-alert-threshold]')
      if (await cpuThreshold.isVisible()) {
        await cpuThreshold.clear()
        await cpuThreshold.fill('85')
      }
      
      const memoryThreshold = page.locator('[data-testid=memory-alert-threshold]')
      if (await memoryThreshold.isVisible()) {
        await memoryThreshold.clear()
        await memoryThreshold.fill('90')
      }
      
      const diskThreshold = page.locator('[data-testid=disk-alert-threshold]')
      if (await diskThreshold.isVisible()) {
        await diskThreshold.clear()
        await diskThreshold.fill('95')
      }
      
      // 通知設定
      const emailNotification = page.locator('[data-testid=email-notification-enabled]')
      if (await emailNotification.isVisible()) {
        await emailNotification.check()
        
        // メール設定
        const emailAddress = page.locator('[data-testid=alert-email-address]')
        if (await emailAddress.isVisible()) {
          await emailAddress.fill('admin@example.com')
        }
      }
      
      const webhookNotification = page.locator('[data-testid=webhook-notification-enabled]')
      if (await webhookNotification.isVisible()) {
        await webhookNotification.check()
        
        // Webhook URL設定
        const webhookUrl = page.locator('[data-testid=webhook-url]')
        if (await webhookUrl.isVisible()) {
          await webhookUrl.fill('https://hooks.slack.com/services/...')
        }
      }
      
      // 設定保存
      await page.click('button:has-text("設定保存")')
      
      // 保存成功メッセージ
      await expect(page.locator('text=アラート設定が保存されました')).toBeVisible({ timeout: 5000 })
    }
  })

  test('can export monitoring data', async ({ page }) => {
    // エクスポートボタンをクリック
    const exportButton = page.locator('button:has-text("データエクスポート")')
    if (await exportButton.isVisible()) {
      await exportButton.click()
      
      // エクスポート設定ダイアログが表示されることを確認
      const exportDialog = page.locator('[data-testid=export-monitoring-dialog]')
      await expect(exportDialog).toBeVisible()
      
      // エクスポート対象の選択
      const exportTargets = [
        'system-metrics',
        'alert-history',
        'log-data',
        'performance-stats'
      ]
      
      for (const target of exportTargets) {
        const checkbox = page.locator(`[data-testid=export-${target}]`)
        if (await checkbox.isVisible()) {
          await checkbox.check()
        }
      }
      
      // エクスポート期間設定
      const exportPeriod = page.locator('[data-testid=export-period]')
      if (await exportPeriod.isVisible()) {
        await exportPeriod.selectOption('7days')
      }
      
      // エクスポート形式選択
      const exportFormat = page.locator('[data-testid=export-format]')
      if (await exportFormat.isVisible()) {
        await exportFormat.selectOption('csv')
      }
      
      // エクスポート実行
      const downloadPromise = page.waitForEvent('download')
      await page.click('button:has-text("エクスポート実行")')
      
      // ファイルダウンロードの確認
      const download = await downloadPromise
      expect(download.suggestedFilename()).toContain('.csv')
    }
  })

  test('can view WebSocket connection status', async ({ page }) => {
    // WebSocket接続状態が表示されることを確認
    const wsStatus = page.locator('[data-testid=websocket-status]')
    await expect(wsStatus).toBeVisible()
    
    // 接続状態の詳細表示
    const connectionDetails = page.locator('[data-testid=connection-details]')
    if (await connectionDetails.isVisible()) {
      await connectionDetails.click()
      
      // 接続詳細情報が表示されることを確認
      const detailsPanel = page.locator('[data-testid=connection-details-panel]')
      await expect(detailsPanel).toBeVisible()
      
      // 接続時間、データ転送量などの表示確認
      await expect(detailsPanel.locator('text=接続時間')).toBeVisible()
      await expect(detailsPanel.locator('text=受信データ')).toBeVisible()
      await expect(detailsPanel.locator('text=送信データ')).toBeVisible()
    }
    
    // 接続テストボタン
    const connectionTestButton = page.locator('button:has-text("接続テスト")')
    if (await connectionTestButton.isVisible()) {
      await connectionTestButton.click()
      
      // 接続テスト結果が表示されることを確認
      const testResult = page.locator('[data-testid=connection-test-result]')
      await expect(testResult).toBeVisible({ timeout: 10000 })
    }
    
    // 再接続ボタン
    const reconnectButton = page.locator('button:has-text("再接続")')
    if (await reconnectButton.isVisible()) {
      await reconnectButton.click()
      
      // 再接続プロセスが開始されることを確認
      await expect(page.locator('text=再接続中')).toBeVisible({ timeout: 5000 })
      
      // 再接続完了の確認
      await expect(page.locator('text=接続中')).toBeVisible({ timeout: 15000 })
    }
  })

  test('can handle monitoring system errors', async ({ page }) => {
    // ネットワークエラーをシミュレート
    await page.route('**/api/v1/monitoring/**', route => {
      route.abort('connectionrefused')
    })
    
    // ページを再読み込み
    await page.reload()
    await page.waitForTimeout(3000)
    
    // エラー状態が表示されることを確認
    const errorMessage = page.locator('[data-testid=monitoring-error-message]')
    if (await errorMessage.isVisible()) {
      await expect(errorMessage).toBeVisible()
      await expect(errorMessage).toContainText('接続エラー')
    }
    
    // 再試行ボタンが表示されることを確認
    const retryButton = page.locator('button:has-text("再試行")')
    if (await retryButton.isVisible()) {
      // ネットワークエラーのルーティングを解除
      await page.unroute('**/api/v1/monitoring/**')
      
      // 再試行をクリック
      await retryButton.click()
      
      // 正常状態に戻ることを確認
      await expect(page.locator('[data-testid=system-stats-cards]')).toBeVisible({ timeout: 10000 })
    }
  })

  test('can view monitoring history', async ({ page }) => {
    // 履歴タブをクリック
    const historyTab = page.locator('text=監視履歴')
    if (await historyTab.isVisible()) {
      await historyTab.click()
      
      // 履歴画面が表示されることを確認
      await expect(page.locator('h5:has-text("監視履歴")')).toBeVisible()
      
      // 期間選択
      const periodSelect = page.locator('[data-testid=history-period-select]')
      if (await periodSelect.isVisible()) {
        await periodSelect.selectOption('24hours')
        await page.waitForTimeout(2000)
      }
      
      // 履歴チャートが表示されることを確認
      const historyChart = page.locator('[data-testid=monitoring-history-chart]')
      await expect(historyChart).toBeVisible()
      
      // 統計サマリーが表示されることを確認
      const historySummary = page.locator('[data-testid=history-summary]')
      await expect(historySummary).toBeVisible()
      
      // イベントタイムラインが表示されることを確認
      const eventTimeline = page.locator('[data-testid=event-timeline]')
      await expect(eventTimeline).toBeVisible()
      
      // 特定の時間範囲にズーム
      const zoomControls = page.locator('[data-testid=chart-zoom-controls]')
      if (await zoomControls.isVisible()) {
        const zoomInButton = zoomControls.locator('button:has-text("拡大")')
        await zoomInButton.click()
        
        // チャートが更新されることを確認
        await page.waitForTimeout(1000)
        await expect(historyChart).toBeVisible()
      }
    }
  })

  test('responsive design works on mobile devices', async ({ page }) => {
    // モバイルビューポートに設定
    await page.setViewportSize({ width: 375, height: 812 })
    
    // 監視画面が適切に表示されることを確認
    await expect(page.locator('h4:has-text("システム監視")')).toBeVisible()
    
    // モバイル用のコンパクトビューが表示されることを確認
    const mobileStatsGrid = page.locator('[data-testid=mobile-stats-grid]')
    if (await mobileStatsGrid.isVisible()) {
      await expect(mobileStatsGrid).toBeVisible()
    } else {
      // 通常のグリッドがモバイル対応していることを確認
      const statsCards = page.locator('[data-testid*=usage-card]')
      const cardCount = await statsCards.count()
      expect(cardCount).toBeGreaterThan(0)
    }
    
    // モバイルナビゲーションの確認
    const mobileMenu = page.locator('[data-testid=mobile-monitoring-menu]')
    if (await mobileMenu.isVisible()) {
      await mobileMenu.click()
      
      // メニューアイテムが表示されることを確認
      await expect(page.locator('[data-testid=mobile-menu-items]')).toBeVisible()
    }
    
    // スワイプ操作でタブ切り替え（可能であれば）
    const tabContainer = page.locator('[data-testid=monitoring-tabs]')
    if (await tabContainer.isVisible()) {
      // タブが表示されることを確認
      await expect(tabContainer).toBeVisible()
    }
    
    // 縦向きスクロールの確認
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await page.waitForTimeout(500)
    await page.evaluate(() => window.scrollTo(0, 0))
  })
})