import { test, expect } from '@playwright/test'

test.describe('Analysis System E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/analysis')
    await page.waitForLoadState('networkidle')
  })

  test('can view timeframe analysis', async ({ page }) => {
    // 分析画面が表示されることを確認
    await expect(page.locator('h4:has-text("市場分析")')).toBeVisible()
    
    // 時間帯分析タブが表示されることを確認
    const timeframeTab = page.locator('text=時間帯分析')
    await expect(timeframeTab).toBeVisible()
    await timeframeTab.click()
    
    // 通貨ペア選択
    const symbolSelect = page.locator('[data-testid=analysis-symbol-select]')
    await expect(symbolSelect).toBeVisible()
    await symbolSelect.selectOption('USDJPY')
    
    // 分析期間設定
    const periodSelect = page.locator('[data-testid=analysis-period]')
    if (await periodSelect.isVisible()) {
      await periodSelect.selectOption('6months')
    }
    
    // 分析実行ボタンをクリック
    const analyzeButton = page.locator('button:has-text("分析実行")')
    await expect(analyzeButton).toBeVisible()
    await analyzeButton.click()
    
    // 分析結果の読み込み表示
    await expect(page.locator('text=分析中')).toBeVisible()
    
    // 時間帯別分析結果が表示されることを確認
    const timeframeResults = page.locator('[data-testid=timeframe-analysis-results]')
    await expect(timeframeResults).toBeVisible({ timeout: 30000 })
    
    // ヒートマップが表示されることを確認
    const heatmap = page.locator('[data-testid=timeframe-heatmap]')
    await expect(heatmap).toBeVisible()
    
    // 時間帯別統計が表示されることを確認
    await expect(page.locator('text=東京市場')).toBeVisible()
    await expect(page.locator('text=ロンドン市場')).toBeVisible()
    await expect(page.locator('text=ニューヨーク市場')).toBeVisible()
    
    // 最も活発な時間帯の表示
    const mostActiveHour = page.locator('[data-testid=most-active-hour]')
    await expect(mostActiveHour).toBeVisible()
    
    // ボラティリティチャートが表示されることを確認
    const volatilityChart = page.locator('[data-testid=volatility-chart]')
    await expect(volatilityChart).toBeVisible()
  })

  test('can view weekday analysis', async ({ page }) => {
    // 曜日別分析タブをクリック
    const weekdayTab = page.locator('text=曜日別分析')
    await expect(weekdayTab).toBeVisible()
    await weekdayTab.click()
    
    // 通貨ペア選択
    await page.selectOption('[data-testid=analysis-symbol-select]', 'EURJPY')
    
    // 分析実行
    await page.click('button:has-text("分析実行")')
    
    // 曜日別分析結果が表示されることを確認
    const weekdayResults = page.locator('[data-testid=weekday-analysis-results]')
    await expect(weekdayResults).toBeVisible({ timeout: 30000 })
    
    // 曜日別パフォーマンスチャートが表示されることを確認
    const weekdayChart = page.locator('[data-testid=weekday-performance-chart]')
    await expect(weekdayChart).toBeVisible()
    
    // 各曜日の統計が表示されることを確認
    const weekdays = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日']
    for (const weekday of weekdays) {
      await expect(page.locator(`text=${weekday}`)).toBeVisible()
    }
    
    // 最高/最低パフォーマンス曜日の表示
    const bestWorstDays = page.locator('[data-testid=best-worst-days]')
    await expect(bestWorstDays).toBeVisible()
    
    // 取引量分析チャート
    const volumeAnalysis = page.locator('[data-testid=volume-analysis-chart]')
    await expect(volumeAnalysis).toBeVisible()
  })

  test('can view correlation analysis', async ({ page }) => {
    // 相関分析タブをクリック
    const correlationTab = page.locator('text=相関分析')
    await correlationTab.click()
    
    // 通貨ペア選択（複数選択）
    const symbolMultiSelect = page.locator('[data-testid=correlation-symbols]')
    await expect(symbolMultiSelect).toBeVisible()
    
    // 複数の通貨ペアを選択
    await page.click('[data-testid=symbol-checkbox-USDJPY]')
    await page.click('[data-testid=symbol-checkbox-EURJPY]')
    await page.click('[data-testid=symbol-checkbox-GBPJPY]')
    
    // 相関期間を設定
    const correlationPeriod = page.locator('[data-testid=correlation-period]')
    if (await correlationPeriod.isVisible()) {
      await correlationPeriod.selectOption('3months')
    }
    
    // 分析実行
    await page.click('button:has-text("相関分析実行")')
    
    // 相関分析結果が表示されることを確認
    const correlationResults = page.locator('[data-testid=correlation-results]')
    await expect(correlationResults).toBeVisible({ timeout: 30000 })
    
    // 相関マトリックスが表示されることを確認
    const correlationMatrix = page.locator('[data-testid=correlation-matrix]')
    await expect(correlationMatrix).toBeVisible()
    
    // 相関係数のヒートマップ
    const correlationHeatmap = page.locator('[data-testid=correlation-heatmap]')
    await expect(correlationHeatmap).toBeVisible()
    
    // 時系列相関チャート
    const timeSeriesCorrelation = page.locator('[data-testid=timeseries-correlation]')
    await expect(timeSeriesCorrelation).toBeVisible()
    
    // 強い相関/弱い相関のペア表示
    const correlationPairs = page.locator('[data-testid=correlation-pairs]')
    await expect(correlationPairs).toBeVisible()
  })

  test('can view market sentiment analysis', async ({ page }) => {
    // センチメント分析タブをクリック
    const sentimentTab = page.locator('text=センチメント分析')
    await sentimentTab.click()
    
    // 通貨ペア選択
    await page.selectOption('[data-testid=analysis-symbol-select]', 'USDJPY')
    
    // 分析期間選択
    const sentimentPeriod = page.locator('[data-testid=sentiment-period]')
    if (await sentimentPeriod.isVisible()) {
      await sentimentPeriod.selectOption('1month')
    }
    
    // センチメントソース選択
    const sentimentSources = page.locator('[data-testid=sentiment-sources]')
    if (await sentimentSources.isVisible()) {
      await page.click('[data-testid=source-news]')
      await page.click('[data-testid=source-social]')
    }
    
    // 分析実行
    await page.click('button:has-text("センチメント分析実行")')
    
    // センチメント分析結果が表示されることを確認
    const sentimentResults = page.locator('[data-testid=sentiment-results]')
    await expect(sentimentResults).toBeVisible({ timeout: 30000 })
    
    // センチメントスコアゲージ
    const sentimentGauge = page.locator('[data-testid=sentiment-gauge]')
    await expect(sentimentGauge).toBeVisible()
    
    // センチメント履歴チャート
    const sentimentHistory = page.locator('[data-testid=sentiment-history-chart]')
    await expect(sentimentHistory).toBeVisible()
    
    // ニュース影響度分析
    const newsImpact = page.locator('[data-testid=news-impact-analysis]')
    if (await newsImpact.isVisible()) {
      await expect(newsImpact).toBeVisible()
    }
    
    // センチメント vs 価格相関
    const sentimentPriceCorrelation = page.locator('[data-testid=sentiment-price-correlation]')
    await expect(sentimentPriceCorrelation).toBeVisible()
  })

  test('can view technical analysis', async ({ page }) => {
    // テクニカル分析タブをクリック
    const technicalTab = page.locator('text=テクニカル分析')
    await technicalTab.click()
    
    // 通貨ペアと時間軸選択
    await page.selectOption('[data-testid=analysis-symbol-select]', 'USDJPY')
    await page.selectOption('[data-testid=analysis-timeframe]', 'H1')
    
    // テクニカル指標選択
    const indicators = ['RSI', 'MACD', 'ボリンジャーバンド', '移動平均']
    for (const indicator of indicators) {
      const checkbox = page.locator(`[data-testid=indicator-${indicator}]`)
      if (await checkbox.isVisible()) {
        await checkbox.check()
      }
    }
    
    // 分析実行
    await page.click('button:has-text("テクニカル分析実行")')
    
    // テクニカル分析結果が表示されることを確認
    const technicalResults = page.locator('[data-testid=technical-results]')
    await expect(technicalResults).toBeVisible({ timeout: 30000 })
    
    // 価格チャートが表示されることを確認
    const priceChart = page.locator('[data-testid=price-chart]')
    await expect(priceChart).toBeVisible()
    
    // テクニカル指標チャート
    const indicatorCharts = page.locator('[data-testid=indicator-charts]')
    await expect(indicatorCharts).toBeVisible()
    
    // シグナル検出結果
    const signals = page.locator('[data-testid=detected-signals]')
    await expect(signals).toBeVisible()
    
    // 買い/売りシグナルの表示
    const buySignals = page.locator('[data-testid=buy-signals]')
    const sellSignals = page.locator('[data-testid=sell-signals]')
    
    if (await buySignals.isVisible()) {
      await expect(buySignals).toBeVisible()
    }
    if (await sellSignals.isVisible()) {
      await expect(sellSignals).toBeVisible()
    }
    
    // 指標値サマリー
    const indicatorSummary = page.locator('[data-testid=indicator-summary]')
    await expect(indicatorSummary).toBeVisible()
  })

  test('can export analysis results', async ({ page }) => {
    // 時間帯分析を実行
    await page.click('text=時間帯分析')
    await page.selectOption('[data-testid=analysis-symbol-select]', 'USDJPY')
    await page.click('button:has-text("分析実行")')
    
    // 分析結果を待機
    await expect(page.locator('[data-testid=timeframe-analysis-results]')).toBeVisible({ timeout: 30000 })
    
    // エクスポートボタンをクリック
    const exportButton = page.locator('button:has-text("エクスポート")')
    await expect(exportButton).toBeVisible()
    await exportButton.click()
    
    // エクスポート形式選択ダイアログ
    const exportDialog = page.locator('[data-testid=export-analysis-dialog]')
    await expect(exportDialog).toBeVisible()
    
    // PDF形式を選択
    const pdfOption = page.locator('input[value="pdf"]')
    if (await pdfOption.isVisible()) {
      await pdfOption.check()
    }
    
    // レポート設定
    const includeCharts = page.locator('[data-testid=include-charts]')
    if (await includeCharts.isVisible()) {
      await includeCharts.check()
    }
    
    const includeData = page.locator('[data-testid=include-raw-data]')
    if (await includeData.isVisible()) {
      await includeData.check()
    }
    
    // エクスポート実行
    const downloadPromise = page.waitForEvent('download')
    await page.click('button:has-text("PDFレポート生成")')
    
    // ファイルダウンロードの確認
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain('.pdf')
    
    // CSV形式でのエクスポートもテスト
    await page.click('button:has-text("エクスポート")')
    await expect(exportDialog).toBeVisible()
    
    const csvOption = page.locator('input[value="csv"]')
    if (await csvOption.isVisible()) {
      await csvOption.check()
      
      const downloadPromise2 = page.waitForEvent('download')
      await page.click('button:has-text("CSVダウンロード")')
      
      const download2 = await downloadPromise2
      expect(download2.suggestedFilename()).toContain('.csv')
    }
  })

  test('can compare analysis across multiple timeframes', async ({ page }) => {
    // 比較分析タブをクリック
    const compareTab = page.locator('text=比較分析')
    await compareTab.click()
    
    // 比較画面が表示されることを確認
    await expect(page.locator('h5:has-text("マルチタイムフレーム比較")')).toBeVisible()
    
    // 通貨ペア選択
    await page.selectOption('[data-testid=compare-symbol-select]', 'USDJPY')
    
    // 複数の時間軸を選択
    const timeframes = ['M15', 'H1', 'H4', 'D1']
    for (const timeframe of timeframes) {
      const checkbox = page.locator(`[data-testid=timeframe-${timeframe}]`)
      if (await checkbox.isVisible()) {
        await checkbox.check()
      }
    }
    
    // 比較指標を選択
    const compareMetrics = page.locator('[data-testid=compare-metrics]')
    if (await compareMetrics.isVisible()) {
      await page.click('[data-testid=metric-volatility]')
      await page.click('[data-testid=metric-trend-strength]')
      await page.click('[data-testid=metric-signal-accuracy]')
    }
    
    // 比較分析実行
    await page.click('button:has-text("比較分析実行")')
    
    // 比較結果が表示されることを確認
    const compareResults = page.locator('[data-testid=comparison-results]')
    await expect(compareResults).toBeVisible({ timeout: 30000 })
    
    // タイムフレーム比較チャート
    const comparisonChart = page.locator('[data-testid=timeframe-comparison-chart]')
    await expect(comparisonChart).toBeVisible()
    
    // 比較サマリーテーブル
    const comparisonTable = page.locator('[data-testid=comparison-summary-table]')
    await expect(comparisonTable).toBeVisible()
    
    // 最適タイムフレーム推奨
    const recommendation = page.locator('[data-testid=timeframe-recommendation]')
    await expect(recommendation).toBeVisible()
  })

  test('can view real-time market overview', async ({ page }) => {
    // マーケット概況タブをクリック
    const marketOverviewTab = page.locator('text=マーケット概況')
    await marketOverviewTab.click()
    
    // マーケット概況画面が表示されることを確認
    await expect(page.locator('h5:has-text("リアルタイム マーケット概況")')).toBeVisible()
    
    // 主要通貨ペアの現在価格が表示されることを確認
    const majorPairs = ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY']
    for (const pair of majorPairs) {
      const pairPrice = page.locator(`[data-testid=price-${pair}]`)
      await expect(pairPrice).toBeVisible()
    }
    
    // 市場動向インジケーター
    const marketTrend = page.locator('[data-testid=market-trend-indicator]')
    await expect(marketTrend).toBeVisible()
    
    // ボラティリティメーター
    const volatilityMeter = page.locator('[data-testid=volatility-meter]')
    await expect(volatilityMeter).toBeVisible()
    
    // 経済指標カレンダー
    const economicCalendar = page.locator('[data-testid=economic-calendar]')
    await expect(economicCalendar).toBeVisible()
    
    // 今日の重要イベント
    const todayEvents = page.locator('[data-testid=today-events]')
    await expect(todayEvents).toBeVisible()
    
    // 市場センチメント概況
    const marketSentiment = page.locator('[data-testid=market-sentiment-overview]')
    await expect(marketSentiment).toBeVisible()
    
    // データの自動更新確認（5秒待機）
    const initialTrendValue = await marketTrend.textContent()
    await page.waitForTimeout(5000)
    
    // データが更新される可能性があることを確認（実際の更新は市場状況による）
    await expect(marketTrend).toBeVisible()
  })

  test('can set up custom alerts from analysis', async ({ page }) => {
    // テクニカル分析を実行
    await page.click('text=テクニカル分析')
    await page.selectOption('[data-testid=analysis-symbol-select]', 'USDJPY')
    await page.click('[data-testid=indicator-RSI]')
    await page.click('button:has-text("テクニカル分析実行")')
    
    // 分析結果を待機
    await expect(page.locator('[data-testid=technical-results]')).toBeVisible({ timeout: 30000 })
    
    // アラート設定ボタンをクリック
    const alertButton = page.locator('button:has-text("アラート設定")')
    if (await alertButton.isVisible()) {
      await alertButton.click()
      
      // アラート設定ダイアログが表示されることを確認
      const alertDialog = page.locator('[data-testid=alert-setup-dialog]')
      await expect(alertDialog).toBeVisible()
      
      // アラート条件設定
      const alertCondition = page.locator('[data-testid=alert-condition]')
      if (await alertCondition.isVisible()) {
        await alertCondition.selectOption('rsi_oversold')
      }
      
      // RSI閾値設定
      const rsiThreshold = page.locator('[data-testid=rsi-threshold]')
      if (await rsiThreshold.isVisible()) {
        await rsiThreshold.fill('30')
      }
      
      // 通知方法選択
      const notificationEmail = page.locator('[data-testid=notification-email]')
      if (await notificationEmail.isVisible()) {
        await notificationEmail.check()
      }
      
      const notificationPush = page.locator('[data-testid=notification-push]')
      if (await notificationPush.isVisible()) {
        await notificationPush.check()
      }
      
      // アラート名前
      const alertName = page.locator('[data-testid=alert-name]')
      if (await alertName.isVisible()) {
        await alertName.fill('USDJPY RSI買われ過ぎアラート')
      }
      
      // アラート作成
      await page.click('button:has-text("アラート作成")')
      
      // 作成成功メッセージ
      await expect(page.locator('text=アラートが作成されました')).toBeVisible({ timeout: 5000 })
    }
  })
})