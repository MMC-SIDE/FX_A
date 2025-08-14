/**
 * バックテスト関連の型定義
 */

import { CurrencyPair, Timeframe, Trade, EquityPoint } from './trading'

export interface BacktestRequest {
  symbol: CurrencyPair
  timeframe: Timeframe
  startDate: string
  endDate: string
  parameters: BacktestParameters
  initialBalance: number
}

export interface BacktestParameters {
  riskPerTrade?: number
  riskRewardRatio?: number
  useNanpin?: boolean
  nanpinMaxCount?: number
  nanpinInterval?: number
  minConfidence?: number
  stopLossPips?: number
  takeProfitPips?: number
  maxPositions?: number
  tradingHours?: {
    start: string
    end: string
  }
  enableEconomicFilter?: boolean
  [key: string]: any
}

export interface BacktestResult {
  testId: string
  symbol: CurrencyPair
  timeframe: Timeframe
  period: {
    startDate: string
    endDate: string
  }
  initialBalance: number
  parameters: BacktestParameters
  statistics: BacktestStatistics
  equityCurve: EquityPoint[]
  trades: BacktestTrade[]
  createdAt: string
}

export interface BacktestStatistics {
  totalTrades: number
  winningTrades: number
  losingTrades: number
  winRate: number
  totalProfit: number
  totalLoss: number
  netProfit: number
  profitFactor: number
  avgWin: number
  avgLoss: number
  largestWin: number
  largestLoss: number
  maxDrawdown: number
  maxDrawdownPercent: number
  sharpeRatio: number
  sortinoRatio: number
  calmarRatio: number
  finalBalance: number
  returnPercent: number
  tradingDays?: number
  avgTradesPerDay?: number
}

export interface BacktestTrade extends Trade {
  testId: string
  entryReason?: string
  exitReason?: string
  durationHours?: number
  maxRunup?: number
  maxDrawdownTrade?: number
}

export interface OptimizationRequest {
  symbol: CurrencyPair
  timeframe: Timeframe
  startDate: string
  endDate: string
  parameterRanges: ParameterRanges
  optimizationMetric: OptimizationMetric
  maxIterations: number
  optimizationMethod: OptimizationMethod
}

export interface ParameterRanges {
  riskPerTrade?: {
    min: number
    max: number
    step: number
  }
  riskRewardRatio?: {
    min: number
    max: number
    step: number
  }
  minConfidence?: {
    min: number
    max: number
    step: number
  }
  stopLossPips?: {
    min: number
    max: number
    step: number
  }
  takeProfitPips?: {
    min: number
    max: number
    step: number
  }
  [key: string]: {
    min: number
    max: number
    step: number
  } | undefined
}

export interface OptimizationResult {
  bestParameters: BacktestParameters
  bestScore: number
  allResults: OptimizationIteration[]
  optimizationMetric: OptimizationMetric
  convergenceAnalysis: {
    converged: boolean
    iterations: number
    improvementThreshold: number
  }
  parameterSensitivity: ParameterSensitivity[]
}

export interface OptimizationIteration {
  parameters: BacktestParameters
  score: number
  statistics: BacktestStatistics
  iteration: number
}

export interface ParameterSensitivity {
  parameter: string
  sensitivity: number
  impact: 'HIGH' | 'MEDIUM' | 'LOW'
  optimalValue: number
  valueRange: {
    min: number
    max: number
  }
}

export interface ComprehensiveBacktestRequest {
  symbols?: CurrencyPair[]
  timeframes?: Timeframe[]
  testPeriodMonths: number
  parameterRanges: ParameterRanges
  optimizationMetric: OptimizationMetric
}

export interface ComprehensiveBacktestResponse {
  individualResults: Record<string, Record<string, BacktestStatistics>>
  summary: {
    totalTests: number
    successfulTests: number
    bestPerformingSymbol: string
    bestPerformingTimeframe: string
    avgPerformanceMetrics: BacktestStatistics
  }
  testPeriod: {
    startDate: string
    endDate: string
  }
  recommendations: string[]
}

export interface BacktestListItem {
  testId: string
  symbol: CurrencyPair
  timeframe: Timeframe
  createdAt: Date
  period: {
    startDate: string
    endDate: string
  }
  finalBalance: number
  returnPercent: number
  totalTrades: number
  winRate: number
  profitFactor: number
  maxDrawdownPercent: number
  sharpeRatio: number
}

export interface BacktestListResponse {
  tests: BacktestListItem[]
  totalCount: number
  page: number
  pageSize: number
  hasNext: boolean
}

export interface BacktestCompareRequest {
  testIds: string[]
  comparisonMetrics: string[]
}

export interface BacktestCompareResponse {
  testIds: string[]
  comparisonMetrics: ComparisonMetric[]
  summary: {
    bestTest: string
    worstTest: string
    avgMetrics: Record<string, number>
  }
  recommendations: string[]
}

export interface ComparisonMetric {
  metric: string
  values: Record<string, number>
  winner: string
  analysis: string
}

export interface BacktestExportRequest {
  testId: string
  format: 'JSON' | 'CSV' | 'EXCEL'
  includeStatistics: boolean
  includeTrades: boolean
  includeEquityCurve: boolean
}

export interface BacktestValidationResult {
  isValid: boolean
  warnings: string[]
  errors: string[]
  dataQualityScore: number
  recommendedAdjustments: string[]
}

export interface BacktestMetrics {
  totalTests: number
  avgReturnPercent: number
  avgWinRate: number
  avgProfitFactor: number
  avgSharpeRatio: number
  bestPerformingSymbol: string
  bestPerformingTimeframe: string
  totalProfit: number
  totalTrades: number
}

// Enums
export type OptimizationMetric = 
  | 'return_percent'
  | 'profit_factor'
  | 'sharpe_ratio'
  | 'sortino_ratio'
  | 'calmar_ratio'
  | 'win_rate'
  | 'net_profit'

export type OptimizationMethod = 
  | 'grid_search'
  | 'random_search'
  | 'bayesian'
  | 'genetic'

// Constants
export const OPTIMIZATION_METRICS: Record<OptimizationMetric, string> = {
  'return_percent': '総利益率',
  'profit_factor': 'プロフィットファクター',
  'sharpe_ratio': 'シャープレシオ',
  'sortino_ratio': 'ソルティノレシオ',
  'calmar_ratio': 'カルマーレシオ',
  'win_rate': '勝率',
  'net_profit': '純利益'
}

export const OPTIMIZATION_METHODS: Record<OptimizationMethod, string> = {
  'grid_search': 'グリッドサーチ',
  'random_search': 'ランダムサーチ',
  'bayesian': 'ベイズ最適化',
  'genetic': '遺伝的アルゴリズム'
}

export const DEFAULT_PARAMETER_RANGES: ParameterRanges = {
  riskPerTrade: { min: 1, max: 10, step: 1 },
  riskRewardRatio: { min: 1, max: 3, step: 0.2 },
  minConfidence: { min: 0.5, max: 0.9, step: 0.05 },
  stopLossPips: { min: 20, max: 100, step: 10 },
  takeProfitPips: { min: 30, max: 200, step: 20 }
}

// Chart Data Types
export interface EquityCurveData {
  timestamp: Date
  equity: number
  balance: number
  drawdown: number
}

export interface ParameterOptimizationChart {
  parameter: string
  values: number[]
  scores: number[]
  bestValue: number
}

export interface BacktestComparisonChart {
  metric: string
  tests: {
    testId: string
    label: string
    value: number
    color: string
  }[]
}

// Form Types
export interface BacktestFormData {
  symbol: CurrencyPair
  timeframe: Timeframe
  startDate: string
  endDate: string
  initialBalance: number
  riskPerTrade: number
  riskRewardRatio: number
  useNanpin: boolean
  nanpinMaxCount: number
  nanpinInterval: number
  minConfidence: number
  stopLossPips: number
  takeProfitPips: number
  maxPositions: number
  enableEconomicFilter: boolean
}

export interface OptimizationFormData {
  symbol: CurrencyPair
  timeframe: Timeframe
  startDate: string
  endDate: string
  optimizationMetric: OptimizationMetric
  optimizationMethod: OptimizationMethod
  maxIterations: number
  parameterRanges: ParameterRanges
}