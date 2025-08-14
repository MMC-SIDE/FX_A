import { test, expect } from '@playwright/test'

test.describe('Backtest System E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/backtest')
    await page.waitForLoadState('networkidle')
  })

  test('can run a basic backtest', async ({ page }) => {
    // バックテスト設定画面が表示されることを確認
    await expect(page.locator('h4:has-text("バックテスト")')).toBeVisible()
    
    // 通貨ペアを選択
    const symbolSelect = page.locator('[data-testid=symbol-select]')
    await expect(symbolSelect).toBeVisible()
    await symbolSelect.selectOption('USDJPY')
    
    // 時間軸を選択
    const timeframeSelect = page.locator('[data-testid=timeframe-select]')
    await expect(timeframeSelect).toBeVisible()
    await timeframeSelect.selectOption('H1')
    
    // 開始日を設定
    const startDate = page.locator('[data-testid=start-date]')
    await expect(startDate).toBeVisible()
    await startDate.fill('2023-01-01')
    
    // 終了日を設定
    const endDate = page.locator('[data-testid=end-date]')
    await expect(endDate).toBeVisible()
    await endDate.fill('2023-12-31')
    
    // 初期残高を設定
    const initialBalance = page.locator('[data-testid=initial-balance]')
    await expect(initialBalance).toBeVisible()
    await initialBalance.clear()
    await initialBalance.fill('100000')
    
    // パラメータ設定
    const rsiPeriod = page.locator('[data-testid=rsi-period]')
    if (await rsiPeriod.isVisible()) {
      await rsiPeriod.clear()
      await rsiPeriod.fill('14')
    }
    
    const stopLoss = page.locator('[data-testid=stop-loss-percent]')
    if (await stopLoss.isVisible()) {
      await stopLoss.clear()
      await stopLoss.fill('2.0')
    }
    
    const takeProfit = page.locator('[data-testid=take-profit-percent]')
    if (await takeProfit.isVisible()) {
      await takeProfit.clear()
      await takeProfit.fill('4.0')
    }
    
    // バックテスト実行ボタンをクリック
    const runButton = page.locator('button:has-text("バックテスト実行")')
    await expect(runButton).toBeVisible()
    await runButton.click()
    
    // 実行中表示が出ることを確認
    await expect(page.locator('text=バックテスト実行中')).toBeVisible({ timeout: 5000 })
    
    // プログレスバーが表示されることを確認
    const progressBar = page.locator('[data-testid=progress-bar]')
    await expect(progressBar).toBeVisible()
    
    // 結果表示を待機（タイムアウトを長めに設定）
    const resultsContainer = page.locator('[data-testid=backtest-results]')
    await expect(resultsContainer).toBeVisible({ timeout: 60000 })
    
    // 統計データが表示されることを確認
    await expect(page.locator('text=総取引回数')).toBeVisible()
    await expect(page.locator('text=勝率')).toBeVisible()
    await expect(page.locator('text=プロフィットファクター')).toBeVisible()
    await expect(page.locator('text=最大ドローダウン')).toBeVisible()
    
    // チャートが表示されることを確認
    const equityChart = page.locator('[data-testid=equity-chart]')
    await expect(equityChart).toBeVisible()
  })

  test('can view detailed backtest results', async ({ page }) => {
    // バックテスト実行（簡略版）
    await page.selectOption('[data-testid=symbol-select]', 'USDJPY')
    await page.selectOption('[data-testid=timeframe-select]', 'H1')
    await page.fill('[data-testid=start-date]', '2023-01-01')
    await page.fill('[data-testid=end-date]', '2023-03-31')
    await page.fill('[data-testid=initial-balance]', '100000')
    
    await page.click('button:has-text("バックテスト実行")')
    
    // 結果表示を待機
    await expect(page.locator('[data-testid=backtest-results]')).toBeVisible({ timeout: 60000 })
    
    // 詳細結果タブをクリック
    const detailsTab = page.locator('text=詳細結果')
    if (await detailsTab.isVisible()) {
      await detailsTab.click()
    }
    
    // 取引履歴テーブルが表示されることを確認
    const tradesTable = page.locator('[data-testid=trades-table]')
    await expect(tradesTable).toBeVisible()
    
    // 取引データが存在する場合、詳細を確認
    const tradeRows = page.locator('[data-testid=trade-row]')
    const tradeCount = await tradeRows.count()
    
    if (tradeCount > 0) {
      const firstTrade = tradeRows.first()
      
      // 取引詳細が表示されることを確認
      await expect(firstTrade.locator('[data-testid=entry-time]')).toBeVisible()
      await expect(firstTrade.locator('[data-testid=exit-time]')).toBeVisible()
      await expect(firstTrade.locator('[data-testid=profit-loss]')).toBeVisible()
      
      // 取引詳細をクリックして展開
      await firstTrade.click()
      
      // 詳細情報が表示されることを確認
      const tradeDetails = page.locator('[data-testid=trade-details]')
      if (await tradeDetails.isVisible()) {
        await expect(tradeDetails.locator('text=エントリー理由')).toBeVisible()
        await expect(tradeDetails.locator('text=エグジット理由')).toBeVisible()
      }
    }
    
    // 統計タブをクリック
    const statsTab = page.locator('text=統計')
    if (await statsTab.isVisible()) {
      await statsTab.click()
      
      // 詳細統計が表示されることを確認
      await expect(page.locator('text=月別パフォーマンス')).toBeVisible()
      await expect(page.locator('text=曜日別分析')).toBeVisible()
      await expect(page.locator('text=時間帯別分析')).toBeVisible()
    }
  })

  test('can compare multiple backtest results', async ({ page }) => {
    // 最初のバックテストを実行
    await page.selectOption('[data-testid=symbol-select]', 'USDJPY')
    await page.selectOption('[data-testid=timeframe-select]', 'H1')
    await page.fill('[data-testid=start-date]', '2023-01-01')
    await page.fill('[data-testid=end-date]', '2023-06-30')
    await page.fill('[data-testid=initial-balance]', '100000')
    await page.fill('[data-testid=rsi-period]', '14')
    
    await page.click('button:has-text("バックテスト実行")')
    await expect(page.locator('[data-testid=backtest-results]')).toBeVisible({ timeout: 60000 })
    
    // 結果を保存
    const saveButton = page.locator('button:has-text("結果を保存")')
    if (await saveButton.isVisible()) {
      await saveButton.click()
      
      // 保存名を入力
      const saveNameInput = page.locator('[data-testid=save-name-input]')
      if (await saveNameInput.isVisible()) {
        await saveNameInput.fill('RSI_14_Test')
        await page.click('button:has-text("保存")')
      }
    }
    
    // 新しいバックテストを実行（パラメータ変更）
    await page.fill('[data-testid=rsi-period]', '21')
    await page.click('button:has-text("バックテスト実行")')
    await expect(page.locator('[data-testid=backtest-results]')).toBeVisible({ timeout: 60000 })
    
    // 比較機能を使用
    const compareButton = page.locator('button:has-text("比較")')
    if (await compareButton.isVisible()) {
      await compareButton.click()
      
      // 比較対象選択ダイアログが表示されることを確認
      const compareDialog = page.locator('[data-testid=compare-dialog]')
      await expect(compareDialog).toBeVisible()
      
      // 保存済み結果を選択
      const savedResult = page.locator('text=RSI_14_Test')
      if (await savedResult.isVisible()) {
        await savedResult.click()
        await page.click('button:has-text("比較実行")')
        
        // 比較結果が表示されることを確認
        const comparisonTable = page.locator('[data-testid=comparison-table]')
        await expect(comparisonTable).toBeVisible()
        
        // 比較項目が表示されることを確認
        await expect(page.locator('text=勝率比較')).toBeVisible()
        await expect(page.locator('text=プロフィットファクター比較')).toBeVisible()
        await expect(page.locator('text=最大ドローダウン比較')).toBeVisible()
      }
    }
  })

  test('can run parameter optimization', async ({ page }) => {
    // 最適化タブをクリック
    const optimizationTab = page.locator('text=パラメータ最適化')
    await optimizationTab.click()
    
    // 最適化画面が表示されることを確認
    await expect(page.locator('h5:has-text("パラメータ最適化")')).toBeVisible()
    
    // 基本設定
    await page.selectOption('[data-testid=symbol-select]', 'USDJPY')
    await page.selectOption('[data-testid=timeframe-select]', 'H1')
    await page.fill('[data-testid=start-date]', '2023-01-01')
    await page.fill('[data-testid=end-date]', '2023-03-31')
    await page.fill('[data-testid=initial-balance]', '100000')
    
    // 最適化パラメータ設定
    const rsiMinInput = page.locator('[data-testid=rsi-min]')
    if (await rsiMinInput.isVisible()) {
      await rsiMinInput.fill('10')
    }
    
    const rsiMaxInput = page.locator('[data-testid=rsi-max]')
    if (await rsiMaxInput.isVisible()) {
      await rsiMaxInput.fill('20')
    }
    
    const rsiStepInput = page.locator('[data-testid=rsi-step]')
    if (await rsiStepInput.isVisible()) {
      await rsiStepInput.fill('2')
    }
    
    // 最適化目標を選択
    const optimizationTarget = page.locator('[data-testid=optimization-target]')
    if (await optimizationTarget.isVisible()) {
      await optimizationTarget.selectOption('profit_factor')
    }
    
    // 最適化実行
    const optimizeButton = page.locator('button:has-text("最適化実行")')
    await expect(optimizeButton).toBeVisible()
    await optimizeButton.click()
    
    // 最適化進行状況が表示されることを確認
    await expect(page.locator('text=最適化実行中')).toBeVisible({ timeout: 5000 })
    
    const optimizationProgress = page.locator('[data-testid=optimization-progress]')
    await expect(optimizationProgress).toBeVisible()
    
    // 最適化結果を待機（タイムアウトを長めに設定）
    const optimizationResults = page.locator('[data-testid=optimization-results]')
    await expect(optimizationResults).toBeVisible({ timeout: 120000 })
    
    // 最適化結果テーブルが表示されることを確認
    const resultsTable = page.locator('[data-testid=optimization-results-table]')
    await expect(resultsTable).toBeVisible()
    
    // 最適パラメータが表示されることを確認
    await expect(page.locator('text=最適パラメータ')).toBeVisible()
    
    // 3D表面プロットが表示されることを確認
    const surfacePlot = page.locator('[data-testid=surface-plot]')
    if (await surfacePlot.isVisible()) {
      await expect(surfacePlot).toBeVisible()
    }
  })

  test('can export backtest results', async ({ page }) => {
    // バックテスト実行
    await page.selectOption('[data-testid=symbol-select]', 'USDJPY')
    await page.selectOption('[data-testid=timeframe-select]', 'H1')
    await page.fill('[data-testid=start-date]', '2023-01-01')
    await page.fill('[data-testid=end-date]', '2023-03-31')
    await page.fill('[data-testid=initial-balance]', '100000')
    
    await page.click('button:has-text("バックテスト実行")')
    await expect(page.locator('[data-testid=backtest-results]')).toBeVisible({ timeout: 60000 })
    
    // エクスポートボタンをクリック
    const exportButton = page.locator('button:has-text("エクスポート")')
    await expect(exportButton).toBeVisible()
    await exportButton.click()
    
    // エクスポート形式選択ダイアログが表示されることを確認
    const exportDialog = page.locator('[data-testid=export-dialog]')
    await expect(exportDialog).toBeVisible()
    
    // CSV形式を選択
    const csvOption = page.locator('input[value="csv"]')
    if (await csvOption.isVisible()) {
      await csvOption.check()
    }
    
    // エクスポート実行
    const downloadPromise = page.waitForEvent('download')
    await page.click('button:has-text("ダウンロード")')
    
    // ファイルダウンロードが開始されることを確認
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain('.csv')
    
    // Excel形式もテスト
    await page.click('button:has-text("エクスポート")')
    await expect(exportDialog).toBeVisible()
    
    const excelOption = page.locator('input[value="excel"]')
    if (await excelOption.isVisible()) {
      await excelOption.check()
      
      const downloadPromise2 = page.waitForEvent('download')
      await page.click('button:has-text("ダウンロード")')
      
      const download2 = await downloadPromise2
      expect(download2.suggestedFilename()).toContain('.xlsx')
    }
  })

  test('can handle large dataset backtest', async ({ page }) => {
    // 大量データでのバックテスト
    await page.selectOption('[data-testid=symbol-select]', 'USDJPY')
    await page.selectOption('[data-testid=timeframe-select]', 'M1') // 1分足で大量データ
    await page.fill('[data-testid=start-date]', '2023-01-01')
    await page.fill('[data-testid=end-date]', '2023-12-31') // 1年間
    await page.fill('[data-testid=initial-balance]', '100000')
    
    // 詳細ログを有効にする
    const detailedLogging = page.locator('[data-testid=detailed-logging]')
    if (await detailedLogging.isVisible()) {
      await detailedLogging.check()
    }
    
    await page.click('button:has-text("バックテスト実行")')
    
    // 大量データ処理の警告が表示される可能性
    const warningDialog = page.locator('text=大量のデータを処理します')
    if (await warningDialog.isVisible()) {
      await page.click('button:has-text("続行")')
    }
    
    // 進行状況が適切に表示されることを確認
    const progressBar = page.locator('[data-testid=progress-bar]')
    await expect(progressBar).toBeVisible()
    
    // 処理時間の表示を確認
    const elapsedTime = page.locator('[data-testid=elapsed-time]')
    if (await elapsedTime.isVisible()) {
      await expect(elapsedTime).toBeVisible()
    }
    
    // メモリ使用量の警告が表示される可能性
    const memoryWarning = page.locator('text=メモリ使用量が高くなっています')
    if (await memoryWarning.isVisible()) {
      // 警告を確認
      await expect(memoryWarning).toBeVisible()
    }
    
    // 結果表示（タイムアウトを非常に長く設定）
    const results = page.locator('[data-testid=backtest-results]')
    await expect(results).toBeVisible({ timeout: 300000 }) // 5分
    
    // パフォーマンス統計が表示されることを確認
    const performanceStats = page.locator('[data-testid=performance-stats]')
    if (await performanceStats.isVisible()) {
      await expect(performanceStats.locator('text=処理時間')).toBeVisible()
      await expect(performanceStats.locator('text=処理速度')).toBeVisible()
    }
  })

  test('can cancel running backtest', async ({ page }) => {
    // バックテスト開始
    await page.selectOption('[data-testid=symbol-select]', 'USDJPY')
    await page.selectOption('[data-testid=timeframe-select]', 'H1')
    await page.fill('[data-testid=start-date]', '2023-01-01')
    await page.fill('[data-testid=end-date]', '2023-12-31')
    await page.fill('[data-testid=initial-balance]', '100000')
    
    await page.click('button:has-text("バックテスト実行")')
    
    // 実行中表示が出ることを確認
    await expect(page.locator('text=バックテスト実行中')).toBeVisible()
    
    // キャンセルボタンが表示されることを確認
    const cancelButton = page.locator('button:has-text("キャンセル")')
    await expect(cancelButton).toBeVisible()
    
    // 少し待ってからキャンセル
    await page.waitForTimeout(3000)
    await cancelButton.click()
    
    // キャンセル確認ダイアログが表示されることを確認
    const confirmDialog = page.locator('text=バックテストをキャンセルしますか？')
    if (await confirmDialog.isVisible()) {
      await page.click('button:has-text("はい")')
    }
    
    // キャンセル完了メッセージが表示されることを確認
    await expect(page.locator('text=バックテストがキャンセルされました')).toBeVisible({ timeout: 10000 })
    
    // 初期状態に戻ることを確認
    const runButton = page.locator('button:has-text("バックテスト実行")')
    await expect(runButton).toBeVisible()
    await expect(runButton).toBeEnabled()
  })

  test('handles validation errors properly', async ({ page }) => {
    // 無効な日付範囲でテスト
    await page.selectOption('[data-testid=symbol-select]', 'USDJPY')
    await page.fill('[data-testid=start-date]', '2023-12-31')
    await page.fill('[data-testid=end-date]', '2023-01-01') // 開始日より前の終了日
    
    await page.click('button:has-text("バックテスト実行")')
    
    // バリデーションエラーが表示されることを確認
    await expect(page.locator('text=終了日は開始日より後に設定してください')).toBeVisible()
    
    // 無効な初期残高でテスト
    await page.fill('[data-testid=start-date]', '2023-01-01')
    await page.fill('[data-testid=end-date]', '2023-12-31')
    await page.fill('[data-testid=initial-balance]', '0')
    
    await page.click('button:has-text("バックテスト実行")')
    
    // バリデーションエラーが表示されることを確認
    await expect(page.locator('text=初期残高は1以上である必要があります')).toBeVisible()
    
    // 無効なパラメータでテスト
    await page.fill('[data-testid=initial-balance]', '100000')
    await page.fill('[data-testid=rsi-period]', '0')
    
    await page.click('button:has-text("バックテスト実行")')
    
    // バリデーションエラーが表示されることを確認
    await expect(page.locator('text=RSI期間は1以上である必要があります')).toBeVisible()
  })
})