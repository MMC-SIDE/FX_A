/**
 * API クライアント
 */
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { 
  ApiResponse, 
  PaginatedApiResponse, 
  HealthCheckResponse, 
  SystemStatusResponse 
} from '@/types/api'
import { 
  Position, 
  Trade, 
  TradingStatus, 
  Settings, 
  RiskStatus 
} from '@/types/trading'
import { 
  BacktestRequest, 
  BacktestResult, 
  OptimizationRequest, 
  OptimizationResult, 
  ComprehensiveBacktestRequest, 
  ComprehensiveBacktestResponse,
  BacktestListResponse 
} from '@/types/backtest'
import {
  MarketSessionAnalysisResponse,
  HourlyAnalysisResponse,
  WeekdayAnalysisResponse,
  NewsImpactAnalysisRequest,
  NewsImpactAnalysisResponse,
  OptimalTimeFindingRequest,
  OptimalTimeFindingResponse,
  ComprehensiveAnalysisRequest,
  ComprehensiveAnalysisResponse,
  AnalysisApiResponse
} from '@/types/analysis'

// API クライアント設定
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || '/api/backend',
    timeout: 30000, // Default timeout
    headers: {
      'Content-Type': 'application/json'
    }
  })

  // リクエストインターセプター
  client.interceptors.request.use(
    (config) => {
      // 認証トークンがあれば追加
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth-token') : null
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error) => Promise.reject(error)
  )

  // レスポンスインターセプター
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        // 認証エラーの場合はトークンを削除
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth-token')
          window.location.href = '/login'
        }
      }
      return Promise.reject(error)
    }
  )

  return client
}

const api = createApiClient()
console.log('API Client initialized with base URL:', api.defaults.baseURL)

// ヘルパー関数
const handleApiResponse = <T>(response: AxiosResponse<ApiResponse<T>>): T => {
  if (response.data.status === 'error') {
    throw new Error(response.data.message || 'API error occurred')
  }
  // APIレスポンスのデータ構造を確認
  console.log('API Response structure:', {
    status: response.data.status,
    hasData: !!response.data.data,
    dataKeys: response.data.data ? Object.keys(response.data.data) : []
  })
  
  // dataフィールドが存在しない場合、response.data全体を返す
  if (response.data.data === undefined && response.data.status === 'success') {
    console.log('Using full response.data as result')
    return response.data as any as T
  }
  
  return response.data.data as T
}

// ============= Trading API =============

export const tradingApi = {
  // 取引開始
  start: async (symbol: string, timeframe: string): Promise<ApiResponse> => {
    const response = await api.post('/trading/start', { symbol, timeframe })
    return response.data
  },

  // 取引停止
  stop: async (): Promise<ApiResponse> => {
    const response = await api.post('/trading/stop')
    return response.data
  },

  // 取引状態取得
  getStatus: async (): Promise<TradingStatus> => {
    const response = await api.get<ApiResponse<TradingStatus>>('/trading/status')
    return handleApiResponse(response)
  },

  // ポジション一覧取得
  getPositions: async (): Promise<Position[]> => {
    const response = await api.get<ApiResponse<Position[]>>('/trading/positions')
    return handleApiResponse(response)
  },

  // 取引履歴取得
  getTrades: async (params?: {
    limit?: number
    offset?: number
    symbol?: string
    startDate?: string
    endDate?: string
  }): Promise<Trade[]> => {
    const response = await api.get<ApiResponse<Trade[]>>('/trading/trades', { params })
    return handleApiResponse(response)
  },

  // 個別取引取得
  getTrade: async (tradeId: string): Promise<Trade> => {
    const response = await api.get<ApiResponse<Trade>>(`/trading/trades/${tradeId}`)
    return handleApiResponse(response)
  }
}

// ============= Backtest API =============

// 進捗追跡用の型定義
export interface BacktestProgress {
  test_id: string
  status: 'running' | 'completed' | 'error'
  current_step: string
  progress_percent: number
  total_configurations: number
  completed_configurations: number
  current_symbol?: string
  current_timeframe?: string
  estimated_time_remaining?: number
  start_time?: string
  logs?: string[]
}

export const backtestApi = {
  // バックテスト実行
  run: async (request: BacktestRequest): Promise<BacktestResult> => {
    console.log('=== BACKTEST API CALL START ===')
    console.log('Original request:', request)
    console.log('API base URL:', api.defaults.baseURL)
    
    // 日付をISO形式文字列に変換（バックエンドの期待する形式）
    const transformedRequest = {
      symbol: request.symbol,
      timeframe: request.timeframe,
      start_date: request.startDate + 'T00:00:00',  // YYYY-MM-DDTHH:MM:SS 形式
      end_date: request.endDate + 'T23:59:59',      // YYYY-MM-DDTHH:MM:SS 形式
      initial_balance: request.initialBalance,
      parameters: request.parameters || {}
    }
    
    console.log('Transformed request being sent to backend:', JSON.stringify(transformedRequest, null, 2))
    console.log('Full URL will be:', api.defaults.baseURL + '/backtest/run')
    
    try {
      console.log('Making POST request...')
      const response = await api.post<ApiResponse<BacktestResult>>('/backtest/run', transformedRequest)
      
      console.log('Request succeeded!')
      console.log('Raw API response:', response)
      console.log('Response data:', response.data)
      console.log('Response status:', response.status)
      
      const rawResult = handleApiResponse(response)
      
      console.log('Raw result:', rawResult)
      console.log('Raw result type:', typeof rawResult)
      console.log('Raw result keys:', rawResult ? Object.keys(rawResult) : 'null')
      
      // バックエンドのレスポンスをフロントエンドの型にマッピング（getResultと同じロジック）
      const result: BacktestResult = {
        testId: (rawResult as any)?.test_id || '',
        symbol: (rawResult as any)?.symbol || '',
        timeframe: (rawResult as any)?.timeframe || '',
        period: {
          startDate: (rawResult as any)?.period?.start_date || '',
          endDate: (rawResult as any)?.period?.end_date || ''
        },
        initialBalance: (rawResult as any)?.initial_balance || (rawResult as any)?.initialBalance || 0,
        parameters: (rawResult as any)?.parameters || {},
        statistics: {
          totalTrades: (rawResult as any)?.statistics?.total_trades || 0,
          winningTrades: (rawResult as any)?.statistics?.winning_trades || 0,
          losingTrades: (rawResult as any)?.statistics?.losing_trades || 0,
          winRate: (rawResult as any)?.statistics?.win_rate || 0,
          netProfit: (rawResult as any)?.statistics?.net_profit || 0,
          totalProfit: (rawResult as any)?.statistics?.total_profit || (rawResult as any)?.statistics?.gross_profit || (rawResult as any)?.statistics?.net_profit || 0,
          totalLoss: (rawResult as any)?.statistics?.total_loss || (rawResult as any)?.statistics?.gross_loss || 0,
          profitFactor: (rawResult as any)?.statistics?.profit_factor || 0,
          maxDrawdownPercent: (rawResult as any)?.statistics?.max_drawdown_percent || 0,
          sharpeRatio: (rawResult as any)?.statistics?.sharpe_ratio || 0,
          sortinoRatio: (rawResult as any)?.statistics?.sortino_ratio || 0,
          calmarRatio: (rawResult as any)?.statistics?.calmar_ratio || 0,
          finalBalance: (rawResult as any)?.statistics?.final_balance || 0,
          returnPercent: (rawResult as any)?.statistics?.return_percent || 0,
          avgWin: (rawResult as any)?.statistics?.avg_win || (rawResult as any)?.statistics?.average_win || 0,
          avgLoss: (rawResult as any)?.statistics?.avg_loss || (rawResult as any)?.statistics?.average_loss || 0,
          largestWin: (rawResult as any)?.statistics?.largest_win || 0,
          largestLoss: (rawResult as any)?.statistics?.largest_loss || 0,
          maxDrawdown: (rawResult as any)?.statistics?.max_drawdown || (rawResult as any)?.statistics?.max_drawdown_percent || 0
        },
        equityCurve: (rawResult as any)?.equity_curve || [],
        trades: (rawResult as any)?.trades || [],
        createdAt: (rawResult as any)?.created_at || new Date().toISOString()
      }
      
      console.log('Mapped result:', result)
      console.log('Mapped statistics:', result.statistics)
      
      return result
    } catch (error: any) {
      console.error('=== BACKTEST API ERROR ===')
      console.error('Error type:', error.name)
      console.error('Error message:', error.message)
      console.error('Error code:', error.code)
      console.error('API Error Details:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        headers: error.response?.headers,
        message: error.message,
        stack: error.stack,
        fullError: error
      })
      
      if (error.code === 'ERR_NETWORK') {
        console.error('Network error - backend may not be running or CORS issue')
      }
      
      throw error
    }
  },

  // バックテスト結果取得
  getResult: async (testId: string): Promise<BacktestResult> => {
    const response = await api.get<any>(`/backtest/results/${testId}`)
    const data = response.data.data
    
    console.log('Backend response data:', data)
    console.log('Statistics:', data.statistics)
    console.log('total_profit:', data.statistics.total_profit)
    console.log('total_loss:', data.statistics.total_loss)
    
    // バックエンドのレスポンスをフロントエンドの型にマッピング
    return {
      testId: data.test_id,
      symbol: data.symbol,
      timeframe: data.timeframe,
      period: {
        startDate: data.period.start_date,
        endDate: data.period.end_date
      },
      initialBalance: data.initial_balance || data.initialBalance,
      parameters: data.parameters || {},
      statistics: {
        totalTrades: data.statistics.total_trades,
        winningTrades: data.statistics.winning_trades,
        losingTrades: data.statistics.losing_trades,
        winRate: data.statistics.win_rate,
        netProfit: data.statistics.net_profit,
        totalProfit: data.statistics.total_profit || data.statistics.gross_profit || data.statistics.net_profit,
        totalLoss: data.statistics.total_loss || data.statistics.gross_loss || 0,
        profitFactor: data.statistics.profit_factor,
        maxDrawdownPercent: data.statistics.max_drawdown_percent,
        sharpeRatio: data.statistics.sharpe_ratio,
        sortinoRatio: data.statistics.sortino_ratio || 0,
        calmarRatio: data.statistics.calmar_ratio || 0,
        finalBalance: data.statistics.final_balance,
        returnPercent: data.statistics.return_percent,
        avgWin: data.statistics.avg_win || data.statistics.average_win || 0,
        avgLoss: data.statistics.avg_loss || data.statistics.average_loss || 0,
        largestWin: data.statistics.largest_win || 0,
        largestLoss: data.statistics.largest_loss || 0,
        maxDrawdown: data.statistics.max_drawdown || data.statistics.max_drawdown_percent
      },
      equityCurve: data.equity_curve || [],
      trades: data.trades || [],
      createdAt: data.created_at
    }
  },

  // バックテスト結果一覧取得
  getResultsList: async (params?: {
    page?: number
    pageSize?: number
    symbol?: string
    timeframe?: string
    startDate?: string
    endDate?: string
  }): Promise<BacktestListResponse> => {
    const response = await api.get<any>('/backtest/list', { params })
    const data = response.data
    
    console.log('Raw list response:', data)
    
    // バックエンドからの応答を変換
    const backendResults = data.results || []
    const tests: BacktestListItem[] = backendResults.map((item: any) => ({
      testId: item.test_id,
      symbol: item.symbols?.[0] || 'USDJPY', // 包括的テストの場合は最初の通貨ペア
      timeframe: item.timeframes?.[0] || 'H1', // 包括的テストの場合は最初の時間軸
      createdAt: new Date(item.created_at),
      period: {
        startDate: item.start_date || '2024-01-01',
        endDate: item.end_date || '2024-12-31'
      },
      finalBalance: 10000 + (item.average_profit || 0),
      returnPercent: ((item.average_profit || 0) / 10000) * 100,
      totalTrades: item.total_configurations || 0,
      winRate: 0.5, // デフォルト値
      profitFactor: item.profit_factor || 0,
      maxDrawdownPercent: 0.2, // デフォルト値
      sharpeRatio: 0 // デフォルト値
    }))
    
    return {
      tests,
      totalCount: data.total || 0,
      page: data.page || 1,
      pageSize: data.page_size || 10,
      hasNext: (data.page || 1) * (data.page_size || 10) < (data.total || 0)
    }
  },

  // パラメータ最適化実行
  optimize: async (request: OptimizationRequest): Promise<OptimizationResult> => {
    console.log('Optimization request:', request)
    
    // 簡略化されたリクエスト形式
    const transformedRequest = {
      symbol: request.symbol,
      timeframe: request.timeframe,
      start_date: request.startDate + 'T00:00:00',
      end_date: request.endDate + 'T23:59:59',
      initial_balance: request.initialBalance || 100000,
      target: request.optimizationMetric,
      iterations: request.maxIterations,
      parameter_ranges: request.parameterRanges
    }
    
    console.log('Transformed optimization request:', transformedRequest)
    
    const response = await api.post<ApiResponse<OptimizationResult>>('/backtest/optimize2', transformedRequest)
    const result = handleApiResponse(response)
    
    console.log('Optimization result:', result)
    
    return result
  },

  // 包括的バックテスト実行
  // 進捗取得
  getProgress: async (testId: string): Promise<BacktestProgress> => {
    try {
      console.log(`Fetching progress for test ID: ${testId}`)
      const response = await api.get<ApiResponse<BacktestProgress>>(`/backtest/progress/${testId}`, {
        timeout: 5000 // 5秒のタイムアウト（進捗ポーリング用に短縮）
      })
      console.log('Progress response:', {
        status: response.status,
        statusText: response.statusText,
        data: response.data
      })
      return handleApiResponse(response)
    } catch (error: any) {
      console.error('Progress API error:', {
        message: error.message,
        status: error?.response?.status,
        statusText: error?.response?.statusText,
        data: error?.response?.data,
        code: error?.code
      })
      throw error
    }
  },

  comprehensive: async (request: ComprehensiveBacktestRequest): Promise<{testId: string, message: string, totalConfigurations: number}> => {
    console.log('Comprehensive backtest request:', request)
    
    // 実際の包括的バックテストエンドポイントを呼び出し
    const requestBody = {
      symbols: request.symbols || ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY"],
      timeframes: request.timeframes || ["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
      start_date: (request.startDate || '2024-01-01') + 'T00:00:00',
      end_date: (request.endDate || '2024-12-31') + 'T23:59:59',
      initial_balance: request.initialBalance || 100000,
      risk_levels: request.riskLevels || [0.01, 0.02, 0.05],
      optimization_metric: request.optimizationMetric || 'profit_factor',
      use_ml: request.useMl !== undefined ? request.useMl : true,
      test_period_months: request.testPeriodMonths || 12,
      parameters: request.parameters || {
        rsi_period: 14,
        rsi_overbought: 70,
        rsi_oversold: 30,
        stop_loss_percent: 2.0,
        take_profit_percent: 4.0
      }
    }
    
    console.log('Sending comprehensive backtest request (async):', requestBody)
    
    const response = await api.post('/backtest/comprehensive', requestBody, {
      timeout: 10000 // Short timeout since it returns immediately
    })
    
    console.log('Comprehensive backtest started:', response.data)
    
    // Return the test ID and metadata for progress tracking
    return {
      testId: response.data.test_id,
      message: response.data.message,
      totalConfigurations: response.data.total_configurations
    }
  },

  // 高速包括的バックテスト実行（制限付き）
  comprehensiveFast: async (request: ComprehensiveBacktestRequest): Promise<ComprehensiveBacktestResponse> => {
    console.log('Fast comprehensive backtest request:', request)
    
    // Transform request to match backend model
    const transformedRequest = {
      test_period_months: 6, // Shorter period for speed
      optimization_metric: 'sharpe_ratio', // Default value
      initial_balance: request.initialBalance || 100000,
      ...request,
      // Remove frontend-specific fields and use backend field names
      ...(request.startDate && request.endDate ? {
        start_date: request.startDate + 'T00:00:00',
        end_date: request.endDate + 'T23:59:59'
      } : {}),
      // Remove fields that don't exist in backend model
      startDate: undefined,
      endDate: undefined,
      initialBalance: undefined
    }
    
    // Clean up undefined fields
    Object.keys(transformedRequest).forEach(key => {
      if (transformedRequest[key] === undefined) {
        delete transformedRequest[key]
      }
    })
    
    console.log('Transformed fast comprehensive request:', transformedRequest)
    
    // Use shorter timeout for fast comprehensive
    const response = await api.post<ApiResponse<ComprehensiveBacktestResponse>>('/backtest/comprehensive-fast', transformedRequest, {
      timeout: 120000 // 2 minutes for fast comprehensive
    })
    const result = handleApiResponse(response)
    
    console.log('Fast comprehensive backtest result:', result)
    
    return result
  },

  // バックテスト結果取得
  getResults: async (testId: string): Promise<ComprehensiveBacktestResponse> => {
    const response = await api.get<ApiResponse<ComprehensiveBacktestResponse>>(`/backtest/results/${testId}`)
    return handleApiResponse(response)
  },

  // バックテスト結果削除
  deleteResults: async (testIds: string[]): Promise<ApiResponse> => {
    const response = await api.delete('/backtest/results', { data: { testIds } })
    return response.data
  },

  // バックテスト結果比較
  compare: async (testIds: string[]): Promise<any> => {
    const response = await api.post('/backtest/compare', { testIds })
    return response.data
  },

  // バックテスト結果エクスポート
  export: async (testId: string, format: 'JSON' | 'CSV' | 'EXCEL'): Promise<any> => {
    const response = await api.post(`/backtest/export`, { 
      testId, 
      format,
      includeStatistics: true,
      includeTrades: true,
      includeEquityCurve: true
    })
    return response.data
  }
}

// ============= Analysis API =============

export const analysisApi = {
  // 市場セッション分析
  getMarketSessionAnalysis: async (
    symbol: string, 
    periodDays: number = 365
  ): Promise<MarketSessionAnalysisResponse> => {
    const response = await api.get<AnalysisApiResponse<MarketSessionAnalysisResponse>>(
      `/analysis/market-sessions/${symbol}`,
      { params: { period_days: periodDays } }
    )
    return response.data.data!
  },

  // 時間別分析
  getHourlyAnalysis: async (
    symbol: string, 
    periodDays: number = 365,
    includeHeatmap: boolean = true
  ): Promise<HourlyAnalysisResponse> => {
    const response = await api.get<AnalysisApiResponse<HourlyAnalysisResponse>>(
      `/analysis/hourly/${symbol}`,
      { params: { period_days: periodDays, include_heatmap: includeHeatmap } }
    )
    return response.data.data!
  },

  // 曜日別分析
  getWeekdayAnalysis: async (
    symbol: string, 
    periodDays: number = 365,
    includeWeekendEffect: boolean = true
  ): Promise<WeekdayAnalysisResponse> => {
    const response = await api.get<AnalysisApiResponse<WeekdayAnalysisResponse>>(
      `/analysis/weekday/${symbol}`,
      { params: { period_days: periodDays, include_weekend_effect: includeWeekendEffect } }
    )
    return response.data.data!
  },

  // ニュース影響分析
  analyzeNewsImpact: async (request: NewsImpactAnalysisRequest): Promise<NewsImpactAnalysisResponse> => {
    const response = await api.post<AnalysisApiResponse<NewsImpactAnalysisResponse>>(
      '/analysis/news-impact',
      request
    )
    return response.data.data!
  },

  // 今後のイベント取得
  getUpcomingEvents: async (
    symbol: string, 
    hoursAhead: number = 24
  ): Promise<any> => {
    const response = await api.post('/analysis/upcoming-events', {
      symbol,
      hoursAhead,
      impactLevels: ['high', 'medium']
    })
    return response.data.data
  },

  // 最適時間帯検出
  findOptimalTimes: async (request: OptimalTimeFindingRequest): Promise<OptimalTimeFindingResponse> => {
    const response = await api.post<AnalysisApiResponse<OptimalTimeFindingResponse>>(
      '/analysis/optimal-hours',
      request
    )
    return response.data.data!
  },

  // エントリー・エグジット分析
  analyzeEntryExit: async (request: any): Promise<any> => {
    const response = await api.post('/analysis/entry-exit', request)
    return response.data.data
  },

  // 包括的分析
  comprehensive: async (request: ComprehensiveAnalysisRequest): Promise<ComprehensiveAnalysisResponse> => {
    const response = await api.post<AnalysisApiResponse<ComprehensiveAnalysisResponse>>(
      '/analysis/comprehensive',
      request
    )
    return response.data.data!
  },

  // 経済指標カレンダー更新
  refreshCalendar: async (daysAhead: number = 7): Promise<any> => {
    const response = await api.post('/analysis/refresh-calendar', null, {
      params: { days_ahead: daysAhead }
    })
    return response.data
  }
}

// ============= Risk Management API =============

export const riskApi = {
  // リスク設定取得
  getSettings: async (): Promise<any> => {
    const response = await api.get('/risk/settings')
    return response.data
  },

  // リスク設定更新
  updateSettings: async (settings: any): Promise<any> => {
    const response = await api.put('/risk/settings', settings)
    return response.data
  },

  // リスク状態取得
  getStatus: async (): Promise<RiskStatus> => {
    const response = await api.get<ApiResponse<RiskStatus>>('/risk/status')
    return handleApiResponse(response)
  },

  // アラート一覧取得
  getAlerts: async (): Promise<any[]> => {
    const response = await api.get('/risk/alerts')
    return response.data
  },

  // 緊急停止
  emergencyStop: async (): Promise<ApiResponse> => {
    const response = await api.post('/risk/emergency-stop')
    return response.data
  }
}

// ============= Settings API =============

export const settingsApi = {
  // 設定取得
  get: async (): Promise<Settings> => {
    const response = await api.get<ApiResponse<Settings>>('/settings')
    return handleApiResponse(response)
  },

  // 設定更新
  update: async (settings: Partial<Settings>): Promise<Settings> => {
    const response = await api.put<ApiResponse<Settings>>('/settings', settings)
    return handleApiResponse(response)
  },

  // 設定リセット
  reset: async (): Promise<ApiResponse> => {
    const response = await api.post('/settings/reset')
    return response.data
  }
}

// ============= Market Data API =============

export const marketApi = {
  // 価格データ取得
  getPrices: async (symbol: string, timeframe: string, limit?: number): Promise<any[]> => {
    const response = await api.get('/market/prices', {
      params: { symbol, timeframe, limit }
    })
    return response.data
  },

  // リアルタイム価格取得
  getRealTimePrice: async (symbol: string): Promise<any> => {
    const response = await api.get(`/market/quotes/${symbol}`)
    return response.data
  },

  // 利用可能通貨ペア取得
  getSymbols: async (): Promise<string[]> => {
    const response = await api.get('/market/symbols')
    return response.data
  }
}

// ============= System API =============

export const systemApi = {
  // ヘルスチェック
  health: async (): Promise<HealthCheckResponse> => {
    const response = await api.get<HealthCheckResponse>('/health')
    return response.data
  },

  // システム状態取得
  status: async (): Promise<SystemStatusResponse> => {
    const response = await api.get<SystemStatusResponse>('/status')
    return response.data
  },

  // ログ取得
  getLogs: async (params?: {
    level?: string
    startDate?: string
    endDate?: string
    limit?: number
  }): Promise<any[]> => {
    const response = await api.get('/system/logs', { params })
    return response.data
  }
}

// WebSocket クライアント
export class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectInterval = 5000
  private maxReconnectAttempts = 5
  private reconnectAttempts = 0
  private subscriptions = new Set<string>()

  constructor(private url: string = 'ws://localhost:8001/ws') {}

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          this.reconnectAttempts = 0
          console.log('WebSocket connected')
          resolve()
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          reject(error)
        }

        this.ws.onclose = () => {
          console.log('WebSocket disconnected')
          this.handleReconnect()
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`)
      
      setTimeout(() => {
        this.connect().then(() => {
          // 再接続後に購読を復元
          this.subscriptions.forEach(subscription => {
            this.send(subscription)
          })
        })
      }, this.reconnectInterval)
    }
  }

  private handleMessage(data: string): void {
    try {
      const message = JSON.parse(data)
      // メッセージハンドリングのロジックをここに実装
      window.dispatchEvent(new CustomEvent('websocket-message', { detail: message }))
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }

  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }

  subscribe(channel: string, params?: any): void {
    const subscription = JSON.stringify({ action: 'subscribe', channel, ...params })
    this.subscriptions.add(subscription)
    this.send(subscription)
  }

  unsubscribe(channel: string): void {
    const subscription = JSON.stringify({ action: 'unsubscribe', channel })
    this.send(subscription)
    this.subscriptions.delete(subscription)
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.subscriptions.clear()
  }
}

// API クライアントのデフォルトエクスポート
export default {
  trading: tradingApi,
  backtest: backtestApi,
  analysis: analysisApi,
  risk: riskApi,
  settings: settingsApi,
  market: marketApi,
  system: systemApi,
  websocket: WebSocketClient
}