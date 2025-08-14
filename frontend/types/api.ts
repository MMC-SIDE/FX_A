/**
 * API関連の型定義
 */

// 共通のAPI応答型
export interface ApiResponse<T = any> {
  status: 'success' | 'error' | 'warning'
  message: string
  data?: T
  errors?: string[]
  warnings?: string[]
  timestamp: string
}

export interface PaginatedApiResponse<T> {
  status: 'success' | 'error'
  message: string
  data: {
    items: T[]
    total: number
    page: number
    pageSize: number
    hasNext: boolean
  }
  timestamp: string
}

// エラー型
export interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
  field?: string
}

export interface ValidationError extends ApiError {
  field: string
  value: any
  constraint: string
}

// ヘルスチェック
export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy' | 'error'
  components: {
    database: boolean
    mt5: boolean
    [key: string]: boolean
  }
  timestamp: string
  error?: string
}

// システム状態
export interface SystemStatusResponse {
  apiStatus: string
  timestamp: string
  uptime: string
  services: {
    marketData: 'active' | 'inactive' | 'error'
    websocket: 'active' | 'inactive' | 'error'
    database: 'connected' | 'disconnected' | 'error'
    mt5: 'connected' | 'disconnected' | 'error'
    trading: 'active' | 'inactive' | 'error'
  }
  performance?: {
    cpuUsage: number
    memoryUsage: number
    diskUsage: number
  }
}

// 認証関連
export interface AuthRequest {
  username: string
  password: string
  rememberMe?: boolean
}

export interface AuthResponse {
  token: string
  refreshToken: string
  expiresIn: number
  user: {
    id: string
    username: string
    email: string
    role: string
  }
}

export interface RefreshTokenRequest {
  refreshToken: string
}

// WebSocket関連
export interface WebSocketConfig {
  url: string
  reconnectInterval: number
  maxReconnectAttempts: number
  pingInterval: number
}

export interface WebSocketMessage<T = any> {
  type: string
  data: T
  timestamp: string
  id?: string
}

export interface WebSocketSubscription {
  channel: string
  symbol?: string
  timeframe?: string
  filters?: Record<string, any>
}

// HTTP Client設定
export interface HttpClientConfig {
  baseURL: string
  timeout: number
  headers?: Record<string, string>
  retryConfig?: {
    retries: number
    retryDelay: number
    retryCondition?: (error: any) => boolean
  }
}

// API エンドポイント定義
export interface ApiEndpoints {
  // Authentication
  auth: {
    login: string
    logout: string
    refresh: string
    profile: string
  }
  
  // Trading
  trading: {
    start: string
    stop: string
    status: string
    positions: string
    trades: string
    history: string
  }
  
  // Market Data
  market: {
    prices: string
    symbols: string
    candles: string
    quotes: string
  }
  
  // Backtest
  backtest: {
    run: string
    results: string
    optimize: string
    compare: string
    export: string
    list: string
  }
  
  // Analysis
  analysis: {
    marketSessions: string
    hourly: string
    weekday: string
    newsImpact: string
    optimalTimes: string
    comprehensive: string
    upcomingEvents: string
  }
  
  // Risk Management
  risk: {
    settings: string
    status: string
    alerts: string
    emergency: string
  }
  
  // Settings
  settings: {
    get: string
    update: string
    reset: string
  }
  
  // System
  system: {
    health: string
    status: string
    logs: string
  }
}

// リクエスト/レスポンス インターセプター
export interface RequestInterceptor {
  onRequest: (config: any) => any
  onRequestError: (error: any) => any
}

export interface ResponseInterceptor {
  onResponse: (response: any) => any
  onResponseError: (error: any) => any
}

// API クライアント設定
export interface ApiClientConfig {
  baseURL: string
  timeout: number
  headers: Record<string, string>
  endpoints: ApiEndpoints
  interceptors?: {
    request?: RequestInterceptor[]
    response?: ResponseInterceptor[]
  }
  websocket?: WebSocketConfig
}

// レート制限
export interface RateLimitConfig {
  maxRequests: number
  windowMs: number
  skipSuccessfulRequests?: boolean
  skipFailedRequests?: boolean
}

// キャッシュ設定
export interface CacheConfig {
  enabled: boolean
  defaultTTL: number
  maxSize: number
  keyPrefix: string
}

// ロギング設定
export interface LoggingConfig {
  enabled: boolean
  level: 'debug' | 'info' | 'warn' | 'error'
  includeRequest: boolean
  includeResponse: boolean
  sanitizeHeaders: string[]
  sanitizeBody: string[]
}

// API メトリクス
export interface ApiMetrics {
  totalRequests: number
  successfulRequests: number
  failedRequests: number
  avgResponseTime: number
  errorRate: number
  endpoints: Record<string, {
    count: number
    avgResponseTime: number
    errorCount: number
  }>
}

// バッチ処理
export interface BatchRequest {
  requests: {
    id: string
    method: string
    url: string
    data?: any
    headers?: Record<string, string>
  }[]
}

export interface BatchResponse {
  responses: {
    id: string
    status: number
    data?: any
    error?: ApiError
  }[]
}

// ファイルアップロード
export interface FileUploadRequest {
  file: File
  metadata?: Record<string, any>
}

export interface FileUploadResponse {
  fileId: string
  filename: string
  size: number
  url: string
  uploadedAt: string
}

// エクスポート/インポート
export interface ExportRequest {
  format: 'JSON' | 'CSV' | 'EXCEL'
  filters?: Record<string, any>
  dateRange?: {
    start: string
    end: string
  }
}

export interface ExportResponse {
  downloadUrl: string
  filename: string
  size: number
  expiresAt: string
}

export interface ImportRequest {
  fileId: string
  mapping?: Record<string, string>
  options?: Record<string, any>
}

export interface ImportResponse {
  importId: string
  status: 'processing' | 'completed' | 'failed'
  processedRecords: number
  totalRecords: number
  errors: string[]
}

// 通知設定
export interface NotificationConfig {
  enabled: boolean
  channels: {
    email?: {
      enabled: boolean
      address: string
    }
    slack?: {
      enabled: boolean
      webhook: string
    }
    webhook?: {
      enabled: boolean
      url: string
      secret: string
    }
  }
  events: string[]
}

// 環境設定
export interface EnvironmentConfig {
  name: string
  apiBaseURL: string
  websocketURL: string
  features: {
    trading: boolean
    backtest: boolean
    analysis: boolean
    realTimeData: boolean
    notifications: boolean
  }
  limits: {
    maxPositions: number
    maxRequestsPerMinute: number
    maxFileSize: number
  }
}