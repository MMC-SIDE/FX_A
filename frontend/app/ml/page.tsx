'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card-simple'
import { Button } from '@/components/ui/Button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Brain,
  TrendingUp,
  Target,
  Activity,
  Play,
  StopCircle,
  Home,
  RefreshCw,
  Settings,
  Eye,
  BarChart3,
  Clock,
  Zap
} from 'lucide-react'
import Link from 'next/link'

interface MLModel {
  model_id: string
  symbol: string
  timeframe: string
  model_type: string
  status: string
  accuracy: number
  precision: number
  recall: number
  f1_score: number
  created_at: string
  last_trained: string
  is_active: boolean
}

interface Prediction {
  symbol: string
  timeframe: string
  prediction: number
  confidence: number
  timestamp: string
  signal: 'BUY' | 'SELL' | 'HOLD'
}

interface TrainingRequest {
  symbol: string
  timeframe: string
  lookback_days: number
  model_params: {
    num_leaves: number
    learning_rate: number
    max_depth: number
    min_data_in_leaf: number
  }
}

export default function MLPage() {
  const [mounted, setMounted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [models, setModels] = useState<MLModel[]>([])
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [selectedModel, setSelectedModel] = useState<MLModel | null>(null)
  const [predictionStatus, setPredictionStatus] = useState<string>('stopped')

  // フォーム設定
  const [formData, setFormData] = useState<TrainingRequest>({
    symbol: 'USDJPY',
    timeframe: 'H1',
    lookback_days: 365,
    model_params: {
      num_leaves: 31,
      learning_rate: 0.05,
      max_depth: -1,
      min_data_in_leaf: 20
    }
  })

  const symbols = ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'CADJPY', 'CHFJPY']
  const timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']

  useEffect(() => {
    setMounted(true)
    fetchModels()
    fetchPredictions()
    fetchPredictionStatus()

    // 5秒間隔で予測データを更新
    const interval = setInterval(() => {
      fetchPredictions()
      fetchPredictionStatus()
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/backend/ml/models')
      if (response.ok) {
        const data = await response.json()
        setModels(data.models || [])
      }
    } catch (err) {
      console.error('Failed to fetch models:', err)
    }
  }

  const fetchPredictions = async () => {
    try {
      const response = await fetch('/api/backend/ml/predictions/multiple/H1')
      if (response.ok) {
        const data = await response.json()
        setPredictions(data.predictions || [])
      }
    } catch (err) {
      console.error('Failed to fetch predictions:', err)
    }
  }

  const fetchPredictionStatus = async () => {
    try {
      const response = await fetch('/api/backend/ml/predictions/status')
      if (response.ok) {
        const data = await response.json()
        setPredictionStatus(data.status || 'stopped')
      }
    } catch (err) {
      console.error('Failed to fetch prediction status:', err)
    }
  }

  const trainModel = async () => {
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch('/api/backend/ml/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      const data = await response.json()

      if (response.ok && data.status === 'success') {
        setSuccess(`モデル学習開始 (ID: ${data.model_id})`)
        setTimeout(() => {
          fetchModels()
        }, 2000)
      } else {
        setError(data.message || 'モデル学習に失敗しました')
      }
    } catch (err) {
      setError('モデル学習中にエラーが発生しました')
    } finally {
      setLoading(false)
    }
  }

  const startPredictions = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/backend/ml/predictions/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      const data = await response.json()

      if (response.ok && data.status === 'success') {
        setSuccess('予測システムを開始しました')
        fetchPredictionStatus()
      } else {
        setError(data.message || '予測システム開始に失敗しました')
      }
    } catch (err) {
      setError('予測システム開始中にエラーが発生しました')
    } finally {
      setLoading(false)
    }
  }

  const stopPredictions = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/backend/ml/predictions/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      const data = await response.json()

      if (response.ok && data.status === 'success') {
        setSuccess('予測システムを停止しました')
        fetchPredictionStatus()
      } else {
        setError(data.message || '予測システム停止に失敗しました')
      }
    } catch (err) {
      setError('予測システム停止中にエラーが発生しました')
    } finally {
      setLoading(false)
    }
  }

  const activateModel = async (modelId: string) => {
    try {
      const response = await fetch(`/api/backend/ml/models/${modelId}/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      if (response.ok) {
        setSuccess('モデルを有効化しました')
        fetchModels()
      } else {
        setError('モデル有効化に失敗しました')
      }
    } catch (err) {
      setError('モデル有効化中にエラーが発生しました')
    }
  }

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'BUY': return 'text-green-600'
      case 'SELL': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const getSignalBadgeVariant = (signal: string) => {
    switch (signal) {
      case 'BUY': return 'default'
      case 'SELL': return 'destructive'
      default: return 'secondary'
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">機械学習</h1>
            <p className="text-gray-600">
              LightGBMモデルの学習・予測・管理を行います
            </p>
          </div>
          <Link href="/">
            <Button 
              variant="outlined" 
              startIcon={<Home className="h-4 w-4" />}
            >
              メインページへ
            </Button>
          </Link>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert variant="success" className="mb-6">
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* モデル学習設定 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              モデル学習設定
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  通貨ペア
                </label>
                <select
                  value={formData.symbol}
                  onChange={(e) => setFormData({...formData, symbol: e.target.value})}
                  className="w-full p-2 border border-gray-300 rounded-md"
                >
                  {symbols.map(symbol => (
                    <option key={symbol} value={symbol}>{symbol}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  時間軸
                </label>
                <select
                  value={formData.timeframe}
                  onChange={(e) => setFormData({...formData, timeframe: e.target.value})}
                  className="w-full p-2 border border-gray-300 rounded-md"
                >
                  {timeframes.map(tf => (
                    <option key={tf} value={tf}>{tf}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                学習期間（日）
              </label>
              <input
                type="number"
                value={formData.lookback_days}
                onChange={(e) => setFormData({...formData, lookback_days: Number(e.target.value)})}
                className="w-full p-2 border border-gray-300 rounded-md"
              />
            </div>

            <Separator />

            <div className="space-y-3">
              <h4 className="font-medium text-gray-900">LightGBMパラメータ</h4>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Num Leaves
                  </label>
                  <input
                    type="number"
                    value={formData.model_params.num_leaves}
                    onChange={(e) => setFormData({
                      ...formData, 
                      model_params: {...formData.model_params, num_leaves: Number(e.target.value)}
                    })}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Learning Rate
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.model_params.learning_rate}
                    onChange={(e) => setFormData({
                      ...formData, 
                      model_params: {...formData.model_params, learning_rate: Number(e.target.value)}
                    })}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Depth
                  </label>
                  <input
                    type="number"
                    value={formData.model_params.max_depth}
                    onChange={(e) => setFormData({
                      ...formData, 
                      model_params: {...formData.model_params, max_depth: Number(e.target.value)}
                    })}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Min Data in Leaf
                  </label>
                  <input
                    type="number"
                    value={formData.model_params.min_data_in_leaf}
                    onChange={(e) => setFormData({
                      ...formData, 
                      model_params: {...formData.model_params, min_data_in_leaf: Number(e.target.value)}
                    })}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  />
                </div>
              </div>
            </div>

            <Separator />

            <Button
              onClick={trainModel}
              disabled={loading}
              startIcon={loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4" />}
              className="w-full"
            >
              {loading ? 'モデル学習中...' : 'モデル学習開始'}
            </Button>
          </CardContent>
        </Card>

        {/* 予測システム制御 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              予測システム制御
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">システム状態</span>
              <Badge variant={predictionStatus === 'running' ? 'default' : 'secondary'}>
                {predictionStatus === 'running' ? '稼働中' : '停止中'}
              </Badge>
            </div>

            <Separator />

            <div className="space-y-3">
              <Button
                onClick={startPredictions}
                disabled={loading || predictionStatus === 'running'}
                startIcon={<Play className="h-4 w-4" />}
                className="w-full"
              >
                予測システム開始
              </Button>

              <Button
                onClick={stopPredictions}
                disabled={loading || predictionStatus === 'stopped'}
                variant="outlined"
                startIcon={<StopCircle className="h-4 w-4" />}
                className="w-full"
              >
                予測システム停止
              </Button>
            </div>

            <Separator />

            <div className="space-y-2">
              <h4 className="font-medium text-gray-900">リアルタイム予測</h4>
              {predictions.length === 0 ? (
                <p className="text-gray-500 text-sm">予測データがありません</p>
              ) : (
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {predictions.map((pred, index) => (
                    <div key={index} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                      <div>
                        <span className="text-sm font-medium">{pred.symbol}</span>
                        <span className="text-xs text-gray-500 ml-2">{pred.timeframe}</span>
                      </div>
                      <div className="text-right">
                        <Badge variant={getSignalBadgeVariant(pred.signal)}>
                          {pred.signal}
                        </Badge>
                        <p className="text-xs text-gray-500">{(pred.confidence * 100).toFixed(1)}%</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* モデル一覧 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              学習済みモデル
            </CardTitle>
          </CardHeader>
          <CardContent>
            {models.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                まだ学習済みモデルがありません
              </p>
            ) : (
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {models.map((model) => (
                  <div
                    key={model.model_id}
                    className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                      selectedModel?.model_id === model.model_id 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => setSelectedModel(model)}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h4 className="font-medium">{model.symbol} - {model.timeframe}</h4>
                        <p className="text-sm text-gray-500">
                          {mounted ? new Date(model.created_at).toLocaleString('ja-JP') : model.created_at}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Badge variant={model.is_active ? 'default' : 'secondary'}>
                          {model.is_active ? '有効' : '無効'}
                        </Badge>
                        <Badge variant={model.status === 'trained' ? 'default' : 'secondary'}>
                          {model.status}
                        </Badge>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="text-center">
                        <p className="text-gray-500">精度</p>
                        <p className="font-medium">{(model.accuracy * 100).toFixed(1)}%</p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-500">F1スコア</p>
                        <p className="font-medium">{model.f1_score?.toFixed(3)}</p>
                      </div>
                    </div>

                    {!model.is_active && model.status === 'trained' && (
                      <Button
                        onClick={(e) => {
                          e.stopPropagation()
                          activateModel(model.model_id)
                        }}
                        size="small"
                        variant="outlined"
                        startIcon={<Zap className="h-3 w-3" />}
                        className="mt-2 w-full"
                      >
                        有効化
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 選択されたモデルの詳細 */}
      {selectedModel && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              モデル詳細: {selectedModel.symbol} - {selectedModel.timeframe}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center">
                <Target className="h-8 w-8 mx-auto mb-2 text-blue-600" />
                <p className="text-sm text-gray-500">精度</p>
                <p className="text-lg font-bold">{(selectedModel.accuracy * 100).toFixed(2)}%</p>
              </div>
              
              <div className="text-center">
                <BarChart3 className="h-8 w-8 mx-auto mb-2 text-green-600" />
                <p className="text-sm text-gray-500">適合率</p>
                <p className="text-lg font-bold">{(selectedModel.precision * 100).toFixed(2)}%</p>
              </div>
              
              <div className="text-center">
                <TrendingUp className="h-8 w-8 mx-auto mb-2 text-purple-600" />
                <p className="text-sm text-gray-500">再現率</p>
                <p className="text-lg font-bold">{(selectedModel.recall * 100).toFixed(2)}%</p>
              </div>
              
              <div className="text-center">
                <Activity className="h-8 w-8 mx-auto mb-2 text-orange-600" />
                <p className="text-sm text-gray-500">F1スコア</p>
                <p className="text-lg font-bold">{selectedModel.f1_score?.toFixed(3)}</p>
              </div>
            </div>

            <Separator className="my-6" />

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-gray-500">モデルタイプ</p>
                <p className="font-medium">{selectedModel.model_type}</p>
              </div>
              <div>
                <p className="text-gray-500">作成日時</p>
                <p className="font-medium">
                  {mounted ? new Date(selectedModel.created_at).toLocaleString('ja-JP') : selectedModel.created_at}
                </p>
              </div>
              <div>
                <p className="text-gray-500">最終学習</p>
                <p className="font-medium">
                  {mounted ? new Date(selectedModel.last_trained).toLocaleString('ja-JP') : selectedModel.last_trained}
                </p>
              </div>
              <div>
                <p className="text-gray-500">状態</p>
                <p className="font-medium">{selectedModel.status}</p>
              </div>
              <div>
                <p className="text-gray-500">有効性</p>
                <p className={`font-medium ${selectedModel.is_active ? 'text-green-600' : 'text-gray-600'}`}>
                  {selectedModel.is_active ? '有効' : '無効'}
                </p>
              </div>
              <div>
                <p className="text-gray-500">モデルID</p>
                <p className="font-medium text-xs">{selectedModel.model_id.substring(0, 8)}...</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 最終更新時刻 */}
      <div className="text-center text-sm text-gray-500 mt-8">
        <Clock className="inline h-4 w-4 mr-1" />
        最終更新: {mounted ? new Date().toLocaleString('ja-JP') : '---'}
      </div>
    </div>
  )
}