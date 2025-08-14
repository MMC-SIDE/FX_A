/**
 * バックテスト関連のカスタムフック
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { backtestApi } from '@/lib/api'
import { useNotifications } from '@/store/ui'
import {
  BacktestRequest,
  BacktestResult,
  OptimizationRequest,
  OptimizationResult,
  ComprehensiveBacktestRequest,
  ComprehensiveBacktestResponse,
  BacktestListResponse
} from '@/types/backtest'
import { useMemo, useState } from 'react'

// ============= バックテスト実行 =============

/**
 * バックテスト実行フック
 */
export function useBacktest() {
  const { showSuccess, showError } = useNotifications()
  const [progress, setProgress] = useState(0)

  return useMutation({
    mutationFn: async (request: BacktestRequest) => {
      setProgress(0)
      
      // プログレス更新のシミュレーション
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90))
      }, 500)

      try {
        const result = await backtestApi.run(request)
        clearInterval(progressInterval)
        setProgress(100)
        return result
      } catch (error) {
        clearInterval(progressInterval)
        setProgress(0)
        throw error
      }
    },
    
    onSuccess: (result, request) => {
      showSuccess(
        'バックテスト完了',
        `${request.symbol} ${request.timeframe}のバックテストが完了しました`
      )
    },
    
    onError: (error: any) => {
      const message = error.response?.data?.message || 'バックテストに失敗しました'
      showError('バックテストエラー', message)
    },

    onSettled: () => {
      setProgress(0)
    }
  })
}

/**
 * パラメータ最適化実行フック
 */
export function useOptimization() {
  const { showSuccess, showError } = useNotifications()
  const [progress, setProgress] = useState(0)

  return useMutation({
    mutationFn: async (request: OptimizationRequest) => {
      setProgress(0)
      
      // プログレス更新のシミュレーション
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 5, 90))
      }, 1000)

      try {
        const result = await backtestApi.optimize(request)
        clearInterval(progressInterval)
        setProgress(100)
        return result
      } catch (error) {
        clearInterval(progressInterval)
        setProgress(0)
        throw error
      }
    },
    
    onSuccess: (result, request) => {
      showSuccess(
        '最適化完了',
        `${request.symbol} ${request.timeframe}のパラメータ最適化が完了しました`
      )
    },
    
    onError: (error: any) => {
      const message = error.response?.data?.message || 'パラメータ最適化に失敗しました'
      showError('最適化エラー', message)
    },

    onSettled: () => {
      setProgress(0)
    }
  })
}

/**
 * 包括的バックテスト実行フック
 */
export function useComprehensiveBacktest() {
  const { showSuccess, showError } = useNotifications()
  const [progress, setProgress] = useState(0)

  return useMutation({
    mutationFn: async (request: ComprehensiveBacktestRequest) => {
      setProgress(0)
      
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 2, 90))
      }, 2000)

      try {
        const result = await backtestApi.comprehensive(request)
        clearInterval(progressInterval)
        setProgress(100)
        return result
      } catch (error) {
        clearInterval(progressInterval)
        setProgress(0)
        throw error
      }
    },
    
    onSuccess: (result) => {
      showSuccess(
        '包括的テスト完了',
        '全通貨ペア・全時間軸のバックテストが完了しました'
      )
    },
    
    onError: (error: any) => {
      const message = error.response?.data?.message || '包括的バックテストに失敗しました'
      showError('包括的テストエラー', message)
    },

    onSettled: () => {
      setProgress(0)
    }
  })
}

// ============= バックテスト結果取得 =============

/**
 * バックテスト結果取得フック
 */
export function useBacktestResult(testId: string) {
  return useQuery({
    queryKey: ['backtest-result', testId],
    queryFn: () => backtestApi.getResult(testId),
    enabled: !!testId,
    staleTime: 300000, // 5分間はキャッシュを使用
    retry: 3
  })
}

/**
 * バックテスト結果一覧取得フック
 */
export function useBacktestResults(params?: {
  page?: number
  pageSize?: number
  symbol?: string
  timeframe?: string
  startDate?: string
  endDate?: string
}) {
  return useQuery({
    queryKey: ['backtest-results', params],
    queryFn: () => backtestApi.getResults(params),
    staleTime: 60000, // 1分間はキャッシュを使用
    refetchOnWindowFocus: false
  })
}

// ============= バックテスト結果操作 =============

/**
 * バックテスト結果削除フック
 */
export function useDeleteBacktestResults() {
  const queryClient = useQueryClient()
  const { showSuccess, showError } = useNotifications()

  return useMutation({
    mutationFn: (testIds: string[]) => backtestApi.deleteResults(testIds),
    
    onSuccess: (result, testIds) => {
      // キャッシュ無効化
      queryClient.invalidateQueries({ queryKey: ['backtest-results'] })
      
      showSuccess(
        '削除完了',
        `${testIds.length}件のバックテスト結果を削除しました`
      )
    },
    
    onError: (error: any) => {
      const message = error.response?.data?.message || 'バックテスト結果の削除に失敗しました'
      showError('削除エラー', message)
    }
  })
}

/**
 * バックテスト結果比較フック
 */
export function useCompareBacktestResults() {
  const { showSuccess, showError } = useNotifications()

  return useMutation({
    mutationFn: (testIds: string[]) => backtestApi.compare(testIds),
    
    onSuccess: () => {
      showSuccess('比較完了', 'バックテスト結果の比較が完了しました')
    },
    
    onError: (error: any) => {
      const message = error.response?.data?.message || 'バックテスト結果の比較に失敗しました'
      showError('比較エラー', message)
    }
  })
}

/**
 * バックテスト結果エクスポートフック
 */
export function useExportBacktestResult() {
  const { showSuccess, showError } = useNotifications()

  return useMutation({
    mutationFn: async (params: {
      testId: string
      format: 'JSON' | 'CSV' | 'EXCEL'
      filename?: string
    }) => {
      const { testId, format, filename } = params
      const result = await backtestApi.export(testId, format)
      
      // ダウンロード処理
      if (result.downloadUrl) {
        const link = document.createElement('a')
        link.href = result.downloadUrl
        link.download = filename || `backtest_${testId}.${format.toLowerCase()}`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }
      
      return result
    },
    
    onSuccess: () => {
      showSuccess('エクスポート完了', 'バックテスト結果のエクスポートが完了しました')
    },
    
    onError: (error: any) => {
      const message = error.response?.data?.message || 'エクスポートに失敗しました'
      showError('エクスポートエラー', message)
    }
  })
}

// ============= データ分析・統計 =============

/**
 * バックテスト結果分析フック
 */
export function useBacktestAnalysis(result?: BacktestResult) {
  return useMemo(() => {
    if (!result) {
      return {
        performance: null,
        riskMetrics: null,
        tradeAnalysis: null,
        timeAnalysis: null
      }
    }

    const { statistics, trades, equityCurve } = result

    // パフォーマンス指標
    const performance = {
      totalReturn: statistics.returnPercent,
      annualizedReturn: statistics.returnPercent, // 簡略化
      maxDrawdown: statistics.maxDrawdownPercent,
      sharpeRatio: statistics.sharpeRatio,
      sortinoRatio: statistics.sortinoRatio,
      profitFactor: statistics.profitFactor,
      winRate: statistics.winRate
    }

    // リスク指標
    const riskMetrics = {
      volatility: 0, // 実装要
      var95: 0, // Value at Risk
      expectedShortfall: 0,
      maxConsecutiveLosses: 0, // 実装要
      avgDrawdownDuration: 0 // 実装要
    }

    // 取引分析
    const profitableTrades = trades?.filter(trade => trade.profitLoss && trade.profitLoss > 0) || []
    const losingTrades = trades?.filter(trade => trade.profitLoss && trade.profitLoss < 0) || []

    const tradeAnalysis = {
      totalTrades: statistics.totalTrades,
      avgTradeReturn: statistics.netProfit / statistics.totalTrades,
      avgWinningTrade: profitableTrades.length > 0 
        ? profitableTrades.reduce((sum, trade) => sum + (trade.profitLoss || 0), 0) / profitableTrades.length
        : 0,
      avgLosingTrade: losingTrades.length > 0
        ? losingTrades.reduce((sum, trade) => sum + (trade.profitLoss || 0), 0) / losingTrades.length
        : 0,
      largestWin: statistics.largestWin,
      largestLoss: statistics.largestLoss,
      avgHoldingTime: 0 // 実装要
    }

    // 時間分析
    const timeAnalysis = {
      tradingPeriod: {
        start: result.period.startDate,
        end: result.period.endDate
      },
      activeTradinDays: 0, // 実装要
      tradesPerMonth: 0, // 実装要
      bestMonth: null, // 実装要
      worstMonth: null // 実装要
    }

    return {
      performance,
      riskMetrics,
      tradeAnalysis,
      timeAnalysis
    }
  }, [result])
}

/**
 * 最適化結果分析フック
 */
export function useOptimizationAnalysis(result?: OptimizationResult) {
  return useMemo(() => {
    if (!result) {
      return {
        convergence: null,
        sensitivity: null,
        recommendations: []
      }
    }

    // 収束分析
    const convergence = {
      converged: result.convergenceAnalysis.converged,
      iterations: result.convergenceAnalysis.iterations,
      bestScore: result.bestScore,
      improvementRate: 0 // 実装要
    }

    // パラメータ感度分析
    const sensitivity = result.parameterSensitivity.map(param => ({
      parameter: param.parameter,
      sensitivity: param.sensitivity,
      impact: param.impact,
      optimalValue: param.optimalValue,
      range: param.valueRange
    }))

    // 推奨事項
    const recommendations = [
      ...(result.convergenceAnalysis.converged 
        ? ['最適化は収束しました'] 
        : ['最適化が収束していません。イテレーション数を増やすことを検討してください']
      ),
      ...result.parameterSensitivity
        .filter(param => param.impact === 'HIGH')
        .map(param => `${param.parameter}は結果に大きく影響します`)
    ]

    return {
      convergence,
      sensitivity,
      recommendations
    }
  }, [result])
}

// ============= フィルタリング・検索 =============

/**
 * バックテスト結果フィルタリングフック
 */
export function useFilteredBacktestResults(
  results: BacktestListResponse | undefined,
  filters: {
    symbol?: string
    timeframe?: string
    dateRange?: { start: string; end: string }
    performanceRange?: { min: number; max: number }
    search?: string
  }
) {
  return useMemo(() => {
    if (!results || !results.tests) return []

    return results.tests.filter(test => {
      // 通貨ペアフィルタ
      if (filters.symbol && test.symbol !== filters.symbol) {
        return false
      }

      // 時間軸フィルタ
      if (filters.timeframe && test.timeframe !== filters.timeframe) {
        return false
      }

      // 日付範囲フィルタ
      if (filters.dateRange) {
        const testDate = new Date(test.createdAt)
        const startDate = new Date(filters.dateRange.start)
        const endDate = new Date(filters.dateRange.end)
        
        if (testDate < startDate || testDate > endDate) {
          return false
        }
      }

      // パフォーマンス範囲フィルタ
      if (filters.performanceRange) {
        const returnPercent = test.returnPercent
        if (returnPercent < filters.performanceRange.min || returnPercent > filters.performanceRange.max) {
          return false
        }
      }

      // 検索フィルタ
      if (filters.search) {
        const searchTerm = filters.search.toLowerCase()
        const searchableText = [
          test.symbol,
          test.timeframe,
          test.testId
        ].join(' ').toLowerCase()
        
        if (!searchableText.includes(searchTerm)) {
          return false
        }
      }

      return true
    })
  }, [results, filters])
}

// ============= チャートデータ変換 =============

/**
 * エクイティカーブチャートデータ変換フック
 */
export function useEquityCurveChartData(result?: BacktestResult) {
  return useMemo(() => {
    if (!result || !result.equityCurve) return []

    return result.equityCurve.map(point => ({
      timestamp: new Date(point.timestamp),
      equity: point.equity,
      balance: point.balance,
      drawdown: 0, // 実装要: peak からの下落率計算
      profit: point.equity - result.initialBalance
    }))
  }, [result])
}

/**
 * 取引分布チャートデータ変換フック
 */
export function useTradeDistributionChartData(result?: BacktestResult) {
  return useMemo(() => {
    if (!result || !result.trades) return []

    // 損益を範囲別に分類
    const ranges = [
      { min: -Infinity, max: -1000, label: '-1000円以下' },
      { min: -1000, max: -500, label: '-1000~-500円' },
      { min: -500, max: -100, label: '-500~-100円' },
      { min: -100, max: 0, label: '-100~0円' },
      { min: 0, max: 100, label: '0~100円' },
      { min: 100, max: 500, label: '100~500円' },
      { min: 500, max: 1000, label: '500~1000円' },
      { min: 1000, max: Infinity, label: '1000円以上' }
    ]

    return ranges.map(range => {
      const count = result.trades!.filter(trade => 
        trade.profitLoss !== undefined &&
        trade.profitLoss > range.min && 
        trade.profitLoss <= range.max
      ).length

      return {
        range: range.label,
        count,
        percentage: (count / result.trades!.length) * 100
      }
    })
  }, [result])
}