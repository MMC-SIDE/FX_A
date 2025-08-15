'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { 
  PlayCircle, 
  StopCircle, 
  AlertTriangle, 
  RefreshCw, 
  Activity,
  Shield,
  TrendingUp,
  Clock,
  DollarSign
} from 'lucide-react'

interface TradingStatus {
  is_active: boolean
  symbol: string | null
  timeframe: string | null
  model_loaded: boolean
  current_positions: number
  positions: any[]
  risk_status: {
    emergency_stop: boolean
    current_drawdown: number
    max_allowed_drawdown: number
    current_positions: number
    max_positions: number
    daily_pnl: number
    risk_settings: any
  }
  last_update: string
}

interface AccountInfo {
  login: number
  balance: number
  equity: number
  margin: number
  margin_free: number
  margin_level: number
  profit: number
  currency: string
  server: string
}

export default function TradingPage() {
  const [tradingStatus, setTradingStatus] = useState<TradingStatus | null>(null)
  const [accountInfo, setAccountInfo] = useState<AccountInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Settings
  const [selectedSymbol, setSelectedSymbol] = useState('USDJPY')
  const [selectedTimeframe, setSelectedTimeframe] = useState('H1')

  const symbols = ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'CADJPY', 'CHFJPY']
  const timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']

  const fetchTradingStatus = async () => {
    try {
      const response = await fetch('/api/backend/trading/status')
      const data = await response.json()
      if (data.status === 'success') {
        setTradingStatus(data.data)
      }
    } catch (err) {
      console.error('Failed to fetch trading status:', err)
    }
  }

  const fetchAccountInfo = async () => {
    try {
      const response = await fetch('/api/backend/trading/account-info')
      const data = await response.json()
      if (data.status === 'success') {
        setAccountInfo(data.data)
      }
    } catch (err) {
      console.error('Failed to fetch account info:', err)
    }
  }

  const startTrading = async () => {
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch('/api/backend/trading/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: selectedSymbol,
          timeframe: selectedTimeframe
        })
      })

      const data = await response.json()
      
      if (response.ok && data.status === 'success') {
        setSuccess(`取引開始: ${selectedSymbol} ${selectedTimeframe}`)
        await fetchTradingStatus()
      } else {
        setError(data.message || '取引開始に失敗しました')
      }
    } catch (err) {
      setError('取引開始中にエラーが発生しました')
    } finally {
      setLoading(false)
    }
  }

  const stopTrading = async (closePositions = false) => {
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch('/api/backend/trading/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ close_positions: closePositions })
      })

      const data = await response.json()
      
      if (response.ok && data.status === 'success') {
        setSuccess(`取引停止${closePositions ? '（ポジションクローズ）' : ''}`)
        await fetchTradingStatus()
      } else {
        setError(data.message || '取引停止に失敗しました')
      }
    } catch (err) {
      setError('取引停止中にエラーが発生しました')
    } finally {
      setLoading(false)
    }
  }

  const emergencyStop = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/backend/trading/emergency-stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      const data = await response.json()
      
      if (response.ok && data.status === 'success') {
        setSuccess('緊急停止が実行されました')
        await fetchTradingStatus()
      } else {
        setError(data.message || '緊急停止に失敗しました')
      }
    } catch (err) {
      setError('緊急停止中にエラーが発生しました')
    } finally {
      setLoading(false)
    }
  }

  const resetEmergencyStop = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/backend/trading/emergency-stop/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      const data = await response.json()
      
      if (response.ok && data.status === 'success') {
        setSuccess('緊急停止が解除されました')
        await fetchTradingStatus()
      } else {
        setError(data.message || '緊急停止解除に失敗しました')
      }
    } catch (err) {
      setError('緊急停止解除中にエラーが発生しました')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTradingStatus()
    fetchAccountInfo()

    // 5秒間隔で状態を更新
    const interval = setInterval(() => {
      fetchTradingStatus()
      fetchAccountInfo()
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">自動売買制御</h1>
        <p className="text-gray-600">
          MT5自動売買システムの開始・停止・監視を行います
        </p>
      </div>

      {error && (
        <Alert className="mb-4 border-red-200 bg-red-50">
          <AlertTriangle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="mb-4 border-green-200 bg-green-50">
          <Activity className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* 取引状態 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              取引状態
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {tradingStatus ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">ステータス</span>
                  <Badge 
                    variant={tradingStatus.is_active ? "default" : "secondary"}
                    className={tradingStatus.is_active ? "bg-green-500" : ""}
                  >
                    {tradingStatus.is_active ? '稼働中' : '停止中'}
                  </Badge>
                </div>
                
                {tradingStatus.symbol && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">通貨ペア</span>
                    <span className="text-sm">{tradingStatus.symbol}</span>
                  </div>
                )}
                
                {tradingStatus.timeframe && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">時間軸</span>
                    <span className="text-sm">{tradingStatus.timeframe}</span>
                  </div>
                )}
                
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">モデル読み込み</span>
                  <Badge variant={tradingStatus.model_loaded ? "default" : "destructive"}>
                    {tradingStatus.model_loaded ? '済み' : '未完了'}
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">現在のポジション</span>
                  <span className="text-sm font-bold">{tradingStatus.current_positions}件</span>
                </div>
              </>
            ) : (
              <div className="text-center py-4">
                <RefreshCw className="h-8 w-8 mx-auto mb-2 animate-spin text-gray-400" />
                <p className="text-sm text-gray-500">状態を取得中...</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 口座情報 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              口座情報
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {accountInfo ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">残高</span>
                  <span className="text-sm font-bold">¥{accountInfo.balance.toLocaleString()}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">有効証拠金</span>
                  <span className="text-sm font-bold">¥{accountInfo.equity.toLocaleString()}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">余剰証拠金</span>
                  <span className="text-sm">¥{accountInfo.margin_free.toLocaleString()}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">損益</span>
                  <span className={`text-sm font-bold ${accountInfo.profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {accountInfo.profit >= 0 ? '+' : ''}¥{accountInfo.profit.toLocaleString()}
                  </span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">ログイン</span>
                  <span className="text-sm">{accountInfo.login}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">サーバー</span>
                  <span className="text-sm">{accountInfo.server}</span>
                </div>
              </>
            ) : (
              <div className="text-center py-4">
                <RefreshCw className="h-8 w-8 mx-auto mb-2 animate-spin text-gray-400" />
                <p className="text-sm text-gray-500">口座情報を取得中...</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* リスク状態 */}
      {tradingStatus?.risk_status && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              リスク管理状態
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <p className="text-sm text-gray-500">緊急停止</p>
                <Badge variant={tradingStatus.risk_status.emergency_stop ? "destructive" : "default"}>
                  {tradingStatus.risk_status.emergency_stop ? '有効' : '無効'}
                </Badge>
              </div>
              
              <div className="text-center">
                <p className="text-sm text-gray-500">ドローダウン</p>
                <p className="text-lg font-bold">
                  {(tradingStatus.risk_status.current_drawdown * 100).toFixed(1)}%
                </p>
              </div>
              
              <div className="text-center">
                <p className="text-sm text-gray-500">ポジション数</p>
                <p className="text-lg font-bold">
                  {tradingStatus.risk_status.current_positions}/{tradingStatus.risk_status.max_positions}
                </p>
              </div>
              
              <div className="text-center">
                <p className="text-sm text-gray-500">日次損益</p>
                <p className={`text-lg font-bold ${tradingStatus.risk_status.daily_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {tradingStatus.risk_status.daily_pnl >= 0 ? '+' : ''}¥{tradingStatus.risk_status.daily_pnl.toFixed(0)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 取引制御 */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            取引制御
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* 設定 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">通貨ペア</label>
              <select 
                value={selectedSymbol} 
                onChange={(e) => setSelectedSymbol(e.target.value)}
                className="w-full p-2 border rounded-md"
                disabled={tradingStatus?.is_active}
              >
                {symbols.map(symbol => (
                  <option key={symbol} value={symbol}>{symbol}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">時間軸</label>
              <select 
                value={selectedTimeframe} 
                onChange={(e) => setSelectedTimeframe(e.target.value)}
                className="w-full p-2 border rounded-md"
                disabled={tradingStatus?.is_active}
              >
                {timeframes.map(tf => (
                  <option key={tf} value={tf}>{tf}</option>
                ))}
              </select>
            </div>
          </div>

          <Separator />

          {/* 制御ボタン */}
          <div className="flex flex-wrap gap-4">
            {!tradingStatus?.is_active ? (
              <Button 
                onClick={startTrading}
                disabled={loading}
                className="flex items-center gap-2"
              >
                <PlayCircle className="h-4 w-4" />
                {loading ? '開始中...' : '取引開始'}
              </Button>
            ) : (
              <>
                <Button 
                  onClick={() => stopTrading(false)}
                  disabled={loading}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <StopCircle className="h-4 w-4" />
                  {loading ? '停止中...' : '取引停止'}
                </Button>
                
                <Button 
                  onClick={() => stopTrading(true)}
                  disabled={loading}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <StopCircle className="h-4 w-4" />
                  {loading ? '停止中...' : '停止＆決済'}
                </Button>
              </>
            )}

            <Button 
              onClick={emergencyStop}
              disabled={loading}
              variant="destructive"
              className="flex items-center gap-2"
            >
              <AlertTriangle className="h-4 w-4" />
              {loading ? '停止中...' : '緊急停止'}
            </Button>

            {tradingStatus?.risk_status?.emergency_stop && (
              <Button 
                onClick={resetEmergencyStop}
                disabled={loading}
                variant="outline"
                className="flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                {loading ? '解除中...' : '緊急停止解除'}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 最終更新時刻 */}
      {tradingStatus && (
        <div className="text-center text-sm text-gray-500">
          <Clock className="inline h-4 w-4 mr-1" />
          最終更新: {new Date(tradingStatus.last_update).toLocaleString('ja-JP')}
        </div>
      )}
    </div>
  )
}