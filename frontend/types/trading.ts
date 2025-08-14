/**
 * 取引関連の型定義
 */

export interface Position {
  id: string
  symbol: string
  type: 'BUY' | 'SELL'
  volume: number
  openPrice: number
  currentPrice: number
  profit: number
  openTime: Date
  stopLoss?: number
  takeProfit?: number
  comment?: string
}

export interface Trade {
  id: string
  orderId: string
  symbol: string
  orderType: 'BUY' | 'SELL'
  entryTime: Date
  entryPrice: number
  exitTime?: Date
  exitPrice?: number
  volume: number
  profitLoss?: number
  commission?: number
  comment?: string
  duration?: number
}

export interface TradingStatus {
  isActive: boolean
  currentSymbol?: string
  currentTimeframe?: string
  lastUpdate: Date
  accountBalance?: number
  equity?: number
  freeMargin?: number
  marginLevel?: number
}

export interface RiskSettings {
  maxRiskPerTrade: number
  maxDrawdown: number
  useNanpin: boolean
  nanpinMaxCount: number
  nanpinInterval: number
  stopLossPips: number
  takeProfitPips: number
  maxPositions: number
}

export interface TradingSettings {
  activeSymbol: string
  activeTimeframe: string
  tradingHours: {
    start: string
    end: string
  }
  enableAutoTrading: boolean
  riskPerTrade: number
  useEconomicCalendar: boolean
}

export interface Settings {
  risk: RiskSettings
  trading: TradingSettings
  notification: {
    enableEmail: boolean
    enableSlack: boolean
    emailAddress?: string
    slackWebhook?: string
  }
}

export interface RiskStatus {
  currentDrawdown: number
  maxDrawdownPercent: number
  isRiskLimitExceeded: boolean
  activePositionsCount: number
  totalExposure: number
  marginUtilization: number
  alerts: RiskAlert[]
}

export interface RiskAlert {
  id: string
  type: 'DRAWDOWN' | 'EXPOSURE' | 'MARGIN' | 'ERROR'
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  message: string
  timestamp: Date
  acknowledged: boolean
}

// Market Data Types
export interface PriceData {
  symbol: string
  timeframe: string
  time: Date
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface MarketSession {
  name: string
  startTime: string
  endTime: string
  isActive: boolean
  timezone: string
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'PRICE_UPDATE' | 'TRADE_UPDATE' | 'POSITION_UPDATE' | 'STATUS_UPDATE' | 'RISK_ALERT'
  data: any
  timestamp: Date
}

export interface PriceUpdate {
  symbol: string
  bid: number
  ask: number
  timestamp: Date
}

// Chart Types
export interface ChartDataPoint {
  timestamp: Date
  value: number
  label?: string
}

export interface EquityPoint {
  timestamp: string
  equity: number
  balance: number
  unrealizedPnl?: number
}

// API Response Types
export interface ApiResponse<T> {
  status: 'success' | 'error' | 'warning'
  message: string
  data?: T
  errors?: string[]
  timestamp: Date
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasNext: boolean
}

// Form Types
export interface TradingFormData {
  symbol: string
  timeframe: string
  riskPerTrade: number
  stopLoss: number
  takeProfit: number
  enableAutoTrading: boolean
}

export interface RiskSettingsFormData {
  maxRiskPerTrade: number
  maxDrawdown: number
  useNanpin: boolean
  nanpinMaxCount: number
  nanpinInterval: number
  stopLossPips: number
  takeProfitPips: number
  maxPositions: number
}

// Constants
export const CURRENCY_PAIRS = [
  'USDJPY',
  'EURJPY', 
  'GBPJPY',
  'AUDJPY',
  'NZDJPY',
  'CADJPY',
  'CHFJPY'
] as const

export const TIMEFRAMES = [
  'M1',
  'M5',
  'M15',
  'M30',
  'H1',
  'H4',
  'D1'
] as const

export type CurrencyPair = typeof CURRENCY_PAIRS[number]
export type Timeframe = typeof TIMEFRAMES[number]

export const TIMEFRAME_LABELS: Record<Timeframe, string> = {
  'M1': '1分',
  'M5': '5分',
  'M15': '15分',
  'M30': '30分',
  'H1': '1時間',
  'H4': '4時間',
  'D1': '1日'
}

export const CURRENCY_PAIR_LABELS: Record<CurrencyPair, string> = {
  'USDJPY': 'USD/JPY',
  'EURJPY': 'EUR/JPY',
  'GBPJPY': 'GBP/JPY',
  'AUDJPY': 'AUD/JPY',
  'NZDJPY': 'NZD/JPY',
  'CADJPY': 'CAD/JPY',
  'CHFJPY': 'CHF/JPY'
}