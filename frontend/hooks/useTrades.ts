/**
 * 取引関連のカスタムフック
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tradingApi } from '@/lib/api'
import { useTradingActions } from '@/store/trading'
import { useNotifications } from '@/store/ui'
import { Position, Trade, TradingStatus } from '@/types/trading'
import { REFRESH_INTERVALS } from '@/lib/constants'

// ============= 取引データ取得 =============

/**
 * 取引履歴取得フック
 */
export function useTrades(params?: {
  limit?: number
  offset?: number
  symbol?: string
  startDate?: string
  endDate?: string
}) {
  return useQuery({
    queryKey: ['trades', params],
    queryFn: () => tradingApi.getTrades(params),
    refetchInterval: REFRESH_INTERVALS.trades,
    staleTime: 30000, // 30秒間はキャッシュを使用
    refetchOnWindowFocus: true,
    retry: 3
  })
}

/**
 * 個別取引取得フック
 */
export function useTrade(tradeId: string) {
  return useQuery({
    queryKey: ['trade', tradeId],
    queryFn: () => tradingApi.getTrade(tradeId),
    enabled: !!tradeId,
    staleTime: 60000 // 1分間はキャッシュを使用
  })
}

/**
 * ポジション一覧取得フック
 */
export function usePositions() {
  const { setPositions } = useTradingActions()
  
  return useQuery({
    queryKey: ['positions'],
    queryFn: async () => {
      const positions = await tradingApi.getPositions()
      setPositions(positions) // ストアも更新
      return positions
    },
    refetchInterval: REFRESH_INTERVALS.positions,
    staleTime: 10000, // 10秒間はキャッシュを使用
    refetchOnWindowFocus: true,
    retry: 3
  })
}

/**
 * 取引状態取得フック
 */
export function useTradingStatus() {
  const { setTradingStatus } = useTradingActions()
  
  return useQuery({
    queryKey: ['trading-status'],
    queryFn: async () => {
      const status = await tradingApi.getStatus()
      setTradingStatus(status) // ストアも更新
      return status
    },
    refetchInterval: REFRESH_INTERVALS.status,
    staleTime: 5000, // 5秒間はキャッシュを使用
    refetchOnWindowFocus: true,
    retry: 3
  })
}

// ============= 取引操作 =============

/**
 * 取引開始フック
 */
export function useStartTrading() {
  const queryClient = useQueryClient()
  const { setIsActive, setError } = useTradingActions()
  const { showSuccess, showError } = useNotifications()

  return useMutation({
    mutationFn: ({ symbol, timeframe }: { symbol: string; timeframe: string }) =>
      tradingApi.start(symbol, timeframe),
    
    onMutate: () => {
      setError(null)
    },
    
    onSuccess: (response, { symbol, timeframe }) => {
      // ストア更新
      setIsActive(true)
      
      // キャッシュ無効化
      queryClient.invalidateQueries({ queryKey: ['trading-status'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      
      // 成功通知
      showSuccess(
        '取引開始',
        `${symbol} ${timeframe}での自動取引を開始しました`
      )
    },
    
    onError: (error: any) => {
      const message = error.response?.data?.message || '取引開始に失敗しました'
      setError(message)
      showError('取引開始エラー', message)
    }
  })
}

/**
 * 取引停止フック
 */
export function useStopTrading() {
  const queryClient = useQueryClient()
  const { setIsActive, setError } = useTradingActions()
  const { showSuccess, showError } = useNotifications()

  return useMutation({
    mutationFn: () => tradingApi.stop(),
    
    onMutate: () => {
      setError(null)
    },
    
    onSuccess: () => {
      // ストア更新
      setIsActive(false)
      
      // キャッシュ無効化
      queryClient.invalidateQueries({ queryKey: ['trading-status'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      
      // 成功通知
      showSuccess('取引停止', '自動取引を停止しました')
    },
    
    onError: (error: any) => {
      const message = error.response?.data?.message || '取引停止に失敗しました'
      setError(message)
      showError('取引停止エラー', message)
    }
  })
}

// ============= データ分析・統計 =============

/**
 * 取引統計計算フック
 */
export function useTradeStatistics(trades?: Trade[]) {
  return useMemo(() => {
    if (!trades || trades.length === 0) {
      return {
        totalTrades: 0,
        winningTrades: 0,
        losingTrades: 0,
        winRate: 0,
        totalProfit: 0,
        totalLoss: 0,
        netProfit: 0,
        profitFactor: 0,
        avgProfit: 0,
        largestWin: 0,
        largestLoss: 0
      }
    }

    const closedTrades = trades.filter(trade => trade.profitLoss !== undefined)
    const totalTrades = closedTrades.length
    
    if (totalTrades === 0) {
      return {
        totalTrades: 0,
        winningTrades: 0,
        losingTrades: 0,
        winRate: 0,
        totalProfit: 0,
        totalLoss: 0,
        netProfit: 0,
        profitFactor: 0,
        avgProfit: 0,
        largestWin: 0,
        largestLoss: 0
      }
    }

    const profits = closedTrades.filter(trade => trade.profitLoss! > 0)
    const losses = closedTrades.filter(trade => trade.profitLoss! < 0)
    
    const winningTrades = profits.length
    const losingTrades = losses.length
    const winRate = (winningTrades / totalTrades) * 100
    
    const totalProfit = profits.reduce((sum, trade) => sum + trade.profitLoss!, 0)
    const totalLoss = Math.abs(losses.reduce((sum, trade) => sum + trade.profitLoss!, 0))
    const netProfit = totalProfit - totalLoss
    
    const profitFactor = totalLoss > 0 ? totalProfit / totalLoss : (totalProfit > 0 ? Infinity : 0)
    const avgProfit = netProfit / totalTrades
    
    const largestWin = profits.length > 0 ? Math.max(...profits.map(t => t.profitLoss!)) : 0
    const largestLoss = losses.length > 0 ? Math.abs(Math.min(...losses.map(t => t.profitLoss!))) : 0

    return {
      totalTrades,
      winningTrades,
      losingTrades,
      winRate: Number(winRate.toFixed(2)),
      totalProfit: Number(totalProfit.toFixed(2)),
      totalLoss: Number(totalLoss.toFixed(2)),
      netProfit: Number(netProfit.toFixed(2)),
      profitFactor: Number(profitFactor.toFixed(4)),
      avgProfit: Number(avgProfit.toFixed(2)),
      largestWin: Number(largestWin.toFixed(2)),
      largestLoss: Number(largestLoss.toFixed(2))
    }
  }, [trades])
}

/**
 * ポジション統計計算フック
 */
export function usePositionStatistics(positions?: Position[]) {
  return useMemo(() => {
    if (!positions || positions.length === 0) {
      return {
        totalPositions: 0,
        buyPositions: 0,
        sellPositions: 0,
        totalProfit: 0,
        totalVolume: 0,
        avgProfit: 0,
        profitablePositions: 0
      }
    }

    const totalPositions = positions.length
    const buyPositions = positions.filter(pos => pos.type === 'BUY').length
    const sellPositions = positions.filter(pos => pos.type === 'SELL').length
    
    const totalProfit = positions.reduce((sum, pos) => sum + pos.profit, 0)
    const totalVolume = positions.reduce((sum, pos) => sum + pos.volume, 0)
    const avgProfit = totalProfit / totalPositions
    const profitablePositions = positions.filter(pos => pos.profit > 0).length

    return {
      totalPositions,
      buyPositions,
      sellPositions,
      totalProfit: Number(totalProfit.toFixed(2)),
      totalVolume: Number(totalVolume.toFixed(2)),
      avgProfit: Number(avgProfit.toFixed(2)),
      profitablePositions
    }
  }, [positions])
}

// ============= リアルタイム更新 =============

/**
 * リアルタイム取引データ監視フック
 */
export function useRealtimeTradingData() {
  const queryClient = useQueryClient()
  const { setPositions, addTrade, setTradingStatus } = useTradingActions()

  useEffect(() => {
    // WebSocketメッセージのリスナー
    const handleWebSocketMessage = (event: CustomEvent) => {
      const { type, data } = event.detail

      switch (type) {
        case 'POSITION_UPDATE':
          setPositions(data)
          queryClient.setQueryData(['positions'], data)
          break
          
        case 'TRADE_UPDATE':
          addTrade(data)
          queryClient.invalidateQueries({ queryKey: ['trades'] })
          break
          
        case 'STATUS_UPDATE':
          setTradingStatus(data)
          queryClient.setQueryData(['trading-status'], data)
          break
      }
    }

    // イベントリスナー登録
    window.addEventListener('websocket-message', handleWebSocketMessage as EventListener)

    return () => {
      window.removeEventListener('websocket-message', handleWebSocketMessage as EventListener)
    }
  }, [queryClient, setPositions, addTrade, setTradingStatus])
}

// ============= フィルタリング・検索 =============

/**
 * 取引データフィルタリングフック
 */
export function useFilteredTrades(
  trades: Trade[] | undefined,
  filters: {
    symbol?: string
    type?: 'BUY' | 'SELL'
    dateRange?: { start: string; end: string }
    profitRange?: { min: number; max: number }
    search?: string
  }
) {
  return useMemo(() => {
    if (!trades) return []

    return trades.filter(trade => {
      // 通貨ペアフィルタ
      if (filters.symbol && trade.symbol !== filters.symbol) {
        return false
      }

      // 取引タイプフィルタ
      if (filters.type && trade.orderType !== filters.type) {
        return false
      }

      // 日付範囲フィルタ
      if (filters.dateRange) {
        const tradeDate = new Date(trade.entryTime)
        const startDate = new Date(filters.dateRange.start)
        const endDate = new Date(filters.dateRange.end)
        
        if (tradeDate < startDate || tradeDate > endDate) {
          return false
        }
      }

      // 損益範囲フィルタ
      if (filters.profitRange && trade.profitLoss !== undefined) {
        if (trade.profitLoss < filters.profitRange.min || trade.profitLoss > filters.profitRange.max) {
          return false
        }
      }

      // 検索フィルタ
      if (filters.search) {
        const searchTerm = filters.search.toLowerCase()
        const searchableText = [
          trade.symbol,
          trade.orderType,
          trade.comment || ''
        ].join(' ').toLowerCase()
        
        if (!searchableText.includes(searchTerm)) {
          return false
        }
      }

      return true
    })
  }, [trades, filters])
}

// ============= エクスポート・分析 =============

/**
 * 取引データエクスポートフック
 */
export function useExportTrades() {
  const { showSuccess, showError } = useNotifications()

  return useMutation({
    mutationFn: async (params: {
      trades: Trade[]
      format: 'CSV' | 'JSON'
      filename?: string
    }) => {
      const { trades, format, filename = `trades_${new Date().toISOString().split('T')[0]}` } = params

      if (format === 'CSV') {
        const headers = [
          'Symbol', 'Type', 'Entry Time', 'Entry Price', 'Exit Time', 
          'Exit Price', 'Volume', 'Profit/Loss', 'Commission', 'Comment'
        ]
        
        const csvData = trades.map(trade => [
          trade.symbol,
          trade.orderType,
          trade.entryTime,
          trade.entryPrice,
          trade.exitTime || '',
          trade.exitPrice || '',
          trade.volume,
          trade.profitLoss || '',
          trade.commission || '',
          trade.comment || ''
        ])

        const csvContent = [headers, ...csvData]
          .map(row => row.map(field => `"${field}"`).join(','))
          .join('\n')

        // ファイルダウンロード
        const blob = new Blob([csvContent], { type: 'text/csv' })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${filename}.csv`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
      } else {
        // JSON形式
        const jsonContent = JSON.stringify(trades, null, 2)
        const blob = new Blob([jsonContent], { type: 'application/json' })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${filename}.json`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
      }
    },
    
    onSuccess: () => {
      showSuccess('エクスポート完了', '取引データのエクスポートが完了しました')
    },
    
    onError: () => {
      showError('エクスポートエラー', 'エクスポートに失敗しました')
    }
  })
}

import { useMemo, useEffect } from 'react'