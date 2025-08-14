/**
 * 時間帯分析関連の型定義
 */

import { CurrencyPair } from './trading'

// 基本的な分析結果の型
export interface TradingStatistics {
  totalTrades: number
  winningTrades: number
  losingTrades: number
  winRate: number
  totalProfit: number
  totalLoss: number
  netProfit: number
  profitFactor: number
  avgProfitPerTrade: number
}

export interface SessionStatistics extends TradingStatistics {
  sessionName: string
  avgVolatility?: number
  maxDrawdown?: number
}

export interface HourlyStatistics extends TradingStatistics {
  hour: string
  marketSession: MarketSession
  avgDurationMinutes?: number
  newsEventsCount?: number
}

export interface WeekdayStatistics extends TradingStatistics {
  weekday: number
  weekdayName: string
  isWeekend: boolean
}

// 市場セッション
export type MarketSession = 'tokyo' | 'london' | 'ny' | 'london_ny_overlap' | 'quiet'

export const MARKET_SESSION_LABELS: Record<MarketSession, string> = {
  'tokyo': '東京セッション',
  'london': 'ロンドンセッション', 
  'ny': 'ニューヨークセッション',
  'london_ny_overlap': 'ロンドン・NY重複',
  'quiet': '閑散時間'
}

// 分析リクエスト/レスポンス
export interface TimeframeAnalysisRequest {
  symbol: CurrencyPair
  periodDays: number
  includeWeekends: boolean
  minTradesPerHour: number
}

export interface MarketSessionAnalysisResponse {
  symbol: CurrencyPair
  periodDays: number
  sessionStatistics: Record<string, SessionStatistics>
  bestSession?: string
  recommendations: string[]
  analysisDate: string
}

export interface HourlyAnalysisResponse {
  symbol: CurrencyPair
  periodDays: number
  hourlyStatistics: Record<string, HourlyStatistics>
  bestHours: string[]
  heatmapData?: number[][]
  recommendations: string[]
  analysisDate: string
}

export interface WeekdayAnalysisResponse {
  symbol: CurrencyPair
  periodDays: number
  weekdayStatistics: Record<string, WeekdayStatistics>
  bestWeekdays: string[]
  weekendEffect?: {
    avgWeekdayPerformance: number
    avgWeekendPerformance: number
    weekendEffectPercent: number
    isWeekendBeneficial: boolean
  }
  recommendations: string[]
  analysisDate: string
}

// 経済指標関連
export interface EconomicEvent {
  name: string
  time: string
  currency: string
  impact: ImpactLevel
  actual?: number
  forecast?: number
  previous?: number
}

export interface VolatilityAnalysis {
  beforeVolatility: number
  afterVolatility: number
  volatilityIncreasePercent: number
  priceChange: number
  priceChangePercent: number
  maxRange: number
  maxRangePercent: number
  dataPointsBefore: number
  dataPointsAfter: number
}

export interface NewsImpactAnalysisRequest {
  symbol: CurrencyPair
  impactLevels: ImpactLevel[]
  timeWindowMinutes: number
  periodDays: number
}

export interface NewsImpactAnalysisResponse {
  symbol: CurrencyPair
  analysisPeriod: {
    startDate: string
    endDate: string
  }
  analyzedEvents: number
  results: {
    event: EconomicEvent
    volatilityAnalysis: VolatilityAnalysis
  }[]
  summary: {
    totalEvents: number
    avgVolatilityIncrease: number
    avgPriceChangePercent: number
    maxVolatilityIncrease: number
    maxPriceChangePercent: number
    highImpactEvents: number
    eventsWithSignificantImpact: number
  }
  recommendations: string[]
  analysisDate: string
}

export interface UpcomingEventsRequest {
  symbol: CurrencyPair
  hoursAhead: number
  impactLevels: ImpactLevel[]
}

export interface UpcomingEventsResponse {
  symbol: CurrencyPair
  hoursAhead: number
  events: {
    eventName: string
    currency: string
    impact: ImpactLevel
    eventTime: string
    hoursUntil: number
    forecast?: number
    previous?: number
  }[]
  highImpactCount: number
  nextMajorEvent?: {
    eventName: string
    currency: string
    impact: ImpactLevel
    eventTime: string
    hoursUntil: number
  }
  recommendations: string[]
}

// 最適時間帯検出
export interface OptimalHour {
  hour: string
  statistics: TradingStatistics
  score: number
  newsRiskScore: number
  marketSession: MarketSession
}

export interface TimeWindow {
  startHour: string
  endHour: string
  durationHours: number
  hours: string[]
  qualityScore: number
  statistics: {
    totalTrades: number
    avgWinRate: number
    avgProfitFactor: number
    avgScore: number
  }
  marketSessions: MarketSession[]
}

export interface TradingSchedule {
  activeHours: number[]
  inactiveHours: number[]
  recommendedSessions: {
    session: MarketSession
    window: TimeWindow
    priority: 'high' | 'medium' | 'low'
  }[]
  totalActiveHours: number
  scheduleEfficiency: number
  dailySchedule: Record<string, string>
}

export interface OptimalTimeFindingRequest {
  symbol: CurrencyPair
  minTrades: number
  minWinRate: number
  minProfitFactor: number
  excludeNewsHours: boolean
  analysisPeriodDays: number
}

export interface OptimalTimeFindingResponse {
  symbol: CurrencyPair
  analysisCriteria: {
    minTrades: number
    minWinRate: number
    minProfitFactor: number
    excludeNewsHours: boolean
  }
  optimalHours: OptimalHour[]
  recommendedWindows: TimeWindow[]
  tradingSchedule: TradingSchedule
  marketSessionAnalysis: {
    sessionStatistics: Record<string, any>
    bestSession?: string
    sessionRanking: {
      session: string
      score: number
    }[]
  }
  recommendations: string[]
  analysisDate: string
}

// エントリー・エグジット分析
export interface EntryExitPair {
  entryHour: string
  exitHour: string
  holdingHours: number
  entryScore: number
  exitScore: number
  combinedScore: number
  entryStats: TradingStatistics
  exitStats: TradingStatistics
}

export interface EntryExitAnalysisRequest {
  symbol: CurrencyPair
  positionType: 'buy' | 'sell' | 'both'
  minHoldingHours: number
  maxHoldingHours: number
  analysisPeriodDays: number
}

export interface EntryExitAnalysisResponse {
  symbol: CurrencyPair
  positionType: string
  optimalEntryTimes: {
    hour: string
    score: number
    statistics: TradingStatistics
  }[]
  optimalExitTimes: {
    hour: string
    score: number
    statistics: TradingStatistics
  }[]
  optimalPairs: EntryExitPair[]
  recommendations: string[]
  analysisDate: string
}

// 包括的分析
export interface ComprehensiveAnalysisRequest {
  symbols: CurrencyPair[]
  periodDays: number
  includeMarketSessions: boolean
  includeHourlyAnalysis: boolean
  includeWeekdayAnalysis: boolean
  includeNewsImpact: boolean
  includeOptimalTimes: boolean
}

export interface ComprehensiveAnalysisResponse {
  symbols: CurrencyPair[]
  periodDays: number
  marketSessionResults: Record<string, MarketSessionAnalysisResponse>
  hourlyResults: Record<string, HourlyAnalysisResponse>
  weekdayResults: Record<string, WeekdayAnalysisResponse>
  newsImpactResults: Record<string, NewsImpactAnalysisResponse>
  optimalTimeResults: Record<string, OptimalTimeFindingResponse>
  summary: {
    analyzedSymbols: number
    successfulAnalyses: number
    commonBestSessions: [string, number][]
    overallBestHours: string[]
    performanceMetrics: Record<string, number>
  }
  crossSymbolInsights: string[]
  recommendations: string[]
  analysisDate: string
}

// エラー・警告
export interface AnalysisError {
  errorCode: string
  errorMessage: string
  details?: Record<string, any>
  timestamp: string
}

export interface AnalysisWarning {
  warningCode: string
  warningMessage: string
  severity: 'low' | 'medium' | 'high'
  recommendations: string[]
}

// API共通レスポンス
export interface AnalysisApiResponse<T> {
  status: 'success' | 'warning' | 'error'
  message: string
  data?: T
  warnings: AnalysisWarning[]
  errors: AnalysisError[]
  executionTimeMs?: number
  timestamp: string
}

// Enums and Constants
export type ImpactLevel = 'high' | 'medium' | 'low'

export const IMPACT_LEVEL_LABELS: Record<ImpactLevel, string> = {
  'high': '高インパクト',
  'medium': '中インパクト',
  'low': '低インパクト'
}

export const WEEKDAY_NAMES = [
  '月曜日',
  '火曜日', 
  '水曜日',
  '木曜日',
  '金曜日',
  '土曜日',
  '日曜日'
] as const

export const HOURS_24 = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`)

// Chart data types
export interface HeatmapData {
  hour: number
  day: number
  value: number
  label: string
}

export interface SessionPerformanceChart {
  session: MarketSession
  winRate: number
  profitFactor: number
  totalTrades: number
  avgProfit: number
}

export interface TimeAnalysisChart {
  time: string
  winRate: number
  profitFactor: number
  totalTrades: number
  riskScore?: number
}

export interface NewsImpactChart {
  eventName: string
  currency: string
  impact: ImpactLevel
  volatilityIncrease: number
  priceChangePercent: number
  eventTime: string
}

// Form types
export interface AnalysisFormData {
  symbol: CurrencyPair
  periodDays: number
  includeWeekends: boolean
  analysisTypes: {
    marketSessions: boolean
    hourlyAnalysis: boolean
    weekdayAnalysis: boolean
    newsImpact: boolean
    optimalTimes: boolean
  }
}

export interface OptimalTimeFormData {
  symbol: CurrencyPair
  minTrades: number
  minWinRate: number
  minProfitFactor: number
  excludeNewsHours: boolean
  analysisPeriodDays: number
}

export interface NewsImpactFormData {
  symbol: CurrencyPair
  impactLevels: ImpactLevel[]
  timeWindowMinutes: number
  periodDays: number
}