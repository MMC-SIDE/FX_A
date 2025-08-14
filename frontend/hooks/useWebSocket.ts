/**
 * WebSocket接続カスタムフック
 */
import { useEffect, useRef, useState, useCallback } from 'react'

export interface WebSocketData {
  type: string
  timestamp: string
  data?: any
  alerts?: any[]
  alert?: any
}

export interface SystemStats {
  timestamp: string
  uptime_seconds: number
  uptime_human: string
  cpu_percent: number
  cpu_count: number
  memory_percent: number
  memory_total_gb: number
  memory_available_gb: number
  memory_used_gb: number
  disk_percent: number
  disk_total_gb: number
  disk_free_gb: number
  disk_used_gb: number
  network_sent_mb: number
  network_recv_mb: number
  network_packets_sent: number
  network_packets_recv: number
  process_memory_mb: number
  process_memory_vms_mb: number
  websocket_connections: number
}

export interface TradingStats {
  today_stats: {
    date: string
    total_trades: number
    winning_trades: number
    losing_trades: number
    win_rate: number
    total_pnl: number
    gross_profit: number
    gross_loss: number
    largest_win: number
    largest_loss: number
    average_win: number
    average_loss: number
    profit_factor: number
  }
  current_pnl: {
    total_profit: number
    unrealized_pnl: number
    position_count: number
    updated_at: string
  }
  account_info: {
    login: number
    balance: number
    equity: number
    equity_change: number
    margin: number
    margin_free: number
    margin_level: number
    margin_level_change: number
    profit: number
    currency: string
    server: string
    company: string
    updated_at: string
  }
}

export interface Alert {
  id: string
  level: 'info' | 'warning' | 'error' | 'critical'
  type: string
  message: string
  details?: any
  value?: number
  threshold?: number
  source?: string
  timestamp: string
  acknowledged: boolean
  acknowledged_by?: string
  acknowledged_at?: string
}

export interface LogEntry {
  timestamp: string
  level: string
  logger_name: string
  message: string
  log_file: string
  raw_line: string
  parsed: boolean
}

export function useWebSocket(url: string, options?: {
  autoReconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
}) {
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [lastMessage, setLastMessage] = useState<WebSocketData | null>(null)
  
  // 状態管理
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [tradingStats, setTradingStats] = useState<TradingStats | null>(null)
  const [mt5Status, setMt5Status] = useState<any>(null)
  const [databaseStatus, setDatabaseStatus] = useState<any>(null)
  const [performanceStats, setPerformanceStats] = useState<any>(null)
  const [riskMetrics, setRiskMetrics] = useState<any>(null)
  const [performanceMetrics, setPerformanceMetrics] = useState<any>(null)
  const [positions, setPositions] = useState<any[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([])

  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const {
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10
  } = options || {}

  const connectWebSocket = useCallback(() => {
    try {
      if (ws.current?.readyState === WebSocket.OPEN) {
        return
      }

      ws.current = new WebSocket(url)

      ws.current.onopen = () => {
        setIsConnected(true)
        setConnectionError(null)
        reconnectAttempts.current = 0
        console.log('WebSocket connected')
      }

      ws.current.onmessage = (event) => {
        try {
          const data: WebSocketData = JSON.parse(event.data)
          setLastMessage(data)

          // メッセージタイプ別処理
          switch (data.type) {
            case 'system_stats':
              setSystemStats(data.data)
              break
              
            case 'trading_stats':
              setTradingStats(data.data)
              break
              
            case 'mt5_status':
              setMt5Status(data.data)
              break
              
            case 'database_status':
              setDatabaseStatus(data.data)
              break
              
            case 'performance_stats':
              setPerformanceStats(data.data)
              break
              
            case 'risk_metrics':
              setRiskMetrics(data.data)
              break
              
            case 'performance_metrics':
              setPerformanceMetrics(data.data)
              break
              
            case 'positions_update':
              setPositions(data.data?.positions || [])
              break
              
            case 'system_alert':
            case 'trading_alert':
            case 'new_alert':
              if (data.alert) {
                setAlerts(prev => [data.alert, ...prev].slice(0, 100))
              }
              break
              
            case 'system_alerts':
            case 'trading_alerts':
              if (data.alerts) {
                setAlerts(prev => [...data.alerts, ...prev].slice(0, 100))
              }
              break
              
            case 'alert_acknowledged':
              if (data.data?.alert_id) {
                setAlerts(prev => prev.map(alert => 
                  alert.id === data.data.alert_id 
                    ? { ...alert, acknowledged: true, acknowledged_by: data.data.acknowledged_by }
                    : alert
                ))
              }
              break
              
            case 'alert_dismissed':
              if (data.data?.alert_id) {
                setAlerts(prev => prev.filter(alert => alert.id !== data.data.alert_id))
              }
              break
              
            case 'alerts_cleared':
              setAlerts([])
              break
              
            case 'log_data':
              if (data.data?.entries) {
                setLogs(data.data.entries)
              }
              break
              
            case 'log_update':
              if (data.data?.new_entries) {
                setLogs(prev => [...data.data.new_entries, ...prev].slice(0, 500))
              }
              break
              
            case 'connection_established':
              console.log('WebSocket connection established:', data.data)
              break
              
            case 'heartbeat':
              // ハートビート受信（特に処理不要）
              break
              
            default:
              console.log('Unknown WebSocket message type:', data.type, data)
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error, event.data)
        }
      }

      ws.current.onclose = (event) => {
        setIsConnected(false)
        console.log('WebSocket disconnected', event.code, event.reason)
        
        // 自動再接続
        if (autoReconnect && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++
          console.log(`Attempting to reconnect (${reconnectAttempts.current}/${maxReconnectAttempts})...`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket()
          }, reconnectInterval)
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setConnectionError('Maximum reconnection attempts reached')
        }
      }

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionError('WebSocket connection error')
      }

    } catch (error) {
      console.error('WebSocket connection failed:', error)
      setConnectionError('Failed to connect')
      
      if (autoReconnect && reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current++
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, reconnectInterval)
      }
    }
  }, [url, autoReconnect, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (ws.current) {
      ws.current.close()
    }
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(JSON.stringify(message))
        return true
      } catch (error) {
        console.error('Failed to send WebSocket message:', error)
        return false
      }
    }
    return false
  }, [])

  const acknowledgeAlert = useCallback((alertId: string) => {
    return sendMessage({
      type: 'acknowledge_alert',
      alert_id: alertId
    })
  }, [sendMessage])

  const dismissAlert = useCallback((alertId: string) => {
    return sendMessage({
      type: 'dismiss_alert',
      alert_id: alertId
    })
  }, [sendMessage])

  const requestLogs = useCallback((logType: string = 'trading', lines: number = 100) => {
    return sendMessage({
      type: 'request_logs',
      log_type: logType,
      lines: lines
    })
  }, [sendMessage])

  const searchLogs = useCallback((searchTerm: string, logType?: string) => {
    return sendMessage({
      type: 'search_logs',
      search_term: searchTerm,
      log_type: logType
    })
  }, [sendMessage])

  useEffect(() => {
    connectWebSocket()

    return () => {
      disconnect()
    }
  }, [connectWebSocket, disconnect])

  return {
    // 接続状態
    isConnected,
    connectionError,
    lastMessage,
    
    // データ
    systemStats,
    tradingStats,
    mt5Status,
    databaseStatus,
    performanceStats,
    riskMetrics,
    performanceMetrics,
    positions,
    alerts,
    logs,
    
    // 操作
    sendMessage,
    acknowledgeAlert,
    dismissAlert,
    requestLogs,
    searchLogs,
    reconnect: connectWebSocket,
    disconnect
  }
}