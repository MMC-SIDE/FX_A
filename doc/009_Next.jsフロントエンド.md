# チケット009: Next.jsフロントエンド

## 概要
Next.js 14 + TypeScriptを使用したWebフロントエンドの実装。

## 目的
- ダッシュボード画面の実装
- バックテスト実行・結果表示画面
- 設定管理画面
- リアルタイム監視機能
- レスポンシブデザイン対応

## 要件
- App Router使用（Next.js 13+）
- TypeScript による型安全性
- Material-UI によるモダンなUI
- TanStack Query によるデータ管理
- Zustand による状態管理

## 受け入れ基準
- [ ] プロジェクト初期化とセットアップ
- [ ] 共通コンポーネントの実装
- [ ] ダッシュボード画面
- [ ] バックテスト画面
- [ ] 設定画面
- [ ] レスポンシブ対応

## 技術仕様

### プロジェクト初期化
```bash
# Next.js プロジェクト作成
npx create-next-app@latest frontend --typescript --tailwind --app

cd frontend

# 依存関係インストール
npm install @mui/material @emotion/react @emotion/styled
npm install @tanstack/react-query zustand
npm install @mui/icons-material @mui/x-date-pickers
npm install recharts date-fns
npm install @hookform/resolvers react-hook-form zod
npm install axios
```

### ディレクトリ構造
```
frontend/
├── app/
│   ├── api/                 # API Routes
│   ├── dashboard/           # ダッシュボードページ
│   ├── backtest/           # バックテストページ
│   ├── settings/           # 設定ページ
│   ├── layout.tsx          # ルートレイアウト
│   ├── page.tsx            # ホームページ
│   └── globals.css         # グローバルCSS
├── components/
│   ├── ui/                 # 基本UIコンポーネント
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   └── Loading.tsx
│   ├── charts/             # チャートコンポーネント
│   │   ├── EquityCurveChart.tsx
│   │   ├── PriceChart.tsx
│   │   └── PerformanceChart.tsx
│   ├── forms/              # フォームコンポーネント
│   │   ├── BacktestForm.tsx
│   │   └── SettingsForm.tsx
│   ├── layout/             # レイアウトコンポーネント
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── Footer.tsx
│   └── trading/            # 取引関連コンポーネント
│       ├── TradingPanel.tsx
│       ├── PositionsList.tsx
│       └── TradeHistory.tsx
├── hooks/                  # カスタムフック
│   ├── useTrades.ts
│   ├── useBacktest.ts
│   └── useSettings.ts
├── lib/                    # ユーティリティ
│   ├── api.ts
│   ├── utils.ts
│   └── constants.ts
├── store/                  # Zustand ストア
│   ├── trading.ts
│   ├── settings.ts
│   └── ui.ts
├── types/                  # TypeScript型定義
│   ├── trading.ts
│   ├── backtest.ts
│   └── api.ts
└── styles/                 # スタイル
    └── globals.css
```

### 型定義
```typescript
// types/trading.ts
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
}

export interface TradingStatus {
  isActive: boolean
  currentSymbol?: string
  currentTimeframe?: string
  lastUpdate: Date
}

// types/backtest.ts
export interface BacktestRequest {
  symbol: string
  timeframe: string
  startDate: string
  endDate: string
  parameters: Record<string, any>
  initialBalance: number
}

export interface BacktestResult {
  testId: string
  symbol: string
  timeframe: string
  statistics: BacktestStatistics
  equityCurve: EquityPoint[]
  trades: Trade[]
}

export interface BacktestStatistics {
  totalTrades: number
  winningTrades: number
  losingTrades: number
  winRate: number
  profitFactor: number
  maxDrawdown: number
  sharpeRatio: number
  finalBalance: number
  returnPercent: number
}

export interface EquityPoint {
  timestamp: string
  equity: number
  balance: number
  unrealizedPnl?: number
}
```

### Zustand ストア
```typescript
// store/trading.ts
import { create } from 'zustand'

interface TradingState {
  isActive: boolean
  currentPositions: Position[]
  recentTrades: Trade[]
  tradingStatus: TradingStatus | null
  
  // Actions
  setIsActive: (active: boolean) => void
  setPositions: (positions: Position[]) => void
  addTrade: (trade: Trade) => void
  setTradingStatus: (status: TradingStatus) => void
  clearData: () => void
}

export const useTradingStore = create<TradingState>((set) => ({
  isActive: false,
  currentPositions: [],
  recentTrades: [],
  tradingStatus: null,
  
  setIsActive: (active) => set({ isActive: active }),
  
  setPositions: (positions) => set({ currentPositions: positions }),
  
  addTrade: (trade) => 
    set((state) => ({ 
      recentTrades: [trade, ...state.recentTrades].slice(0, 100) 
    })),
  
  setTradingStatus: (status) => set({ tradingStatus: status }),
  
  clearData: () => set({
    currentPositions: [],
    recentTrades: [],
    tradingStatus: null
  })
}))

// store/settings.ts
interface SettingsState {
  riskSettings: RiskSettings
  tradingSettings: TradingSettings
  
  updateRiskSettings: (settings: Partial<RiskSettings>) => void
  updateTradingSettings: (settings: Partial<TradingSettings>) => void
}

export const useSettingsStore = create<SettingsState>((set) => ({
  riskSettings: {
    maxRiskPerTrade: 20,
    maxDrawdown: 20,
    useNanpin: true,
    nanpinMaxCount: 3,
    stopLossPips: 50,
    takeProfitPips: 100
  },
  
  tradingSettings: {
    activeSymbol: 'USDJPY',
    activeTimeframe: 'H1',
    tradingHours: {
      start: '09:00',
      end: '17:00'
    }
  },
  
  updateRiskSettings: (settings) =>
    set((state) => ({
      riskSettings: { ...state.riskSettings, ...settings }
    })),
  
  updateTradingSettings: (settings) =>
    set((state) => ({
      tradingSettings: { ...state.tradingSettings, ...settings }
    }))
}))
```

### API クライアント
```typescript
// lib/api.ts
import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Trading API
export const tradingApi = {
  start: (symbol: string, timeframe: string) =>
    api.post('/trading/start', { symbol, timeframe }),
  
  stop: () => api.post('/trading/stop'),
  
  getStatus: () => api.get<TradingStatus>('/trading/status'),
  
  getPositions: () => api.get<Position[]>('/positions'),
  
  getTrades: (limit?: number) => 
    api.get<Trade[]>('/trades', { params: { limit } })
}

// Backtest API
export const backtestApi = {
  run: (request: BacktestRequest) =>
    api.post<BacktestResult>('/backtest/run', request),
  
  getResult: (testId: string) =>
    api.get<BacktestResult>(`/backtest/results/${testId}`),
  
  optimize: (request: OptimizationRequest) =>
    api.post<OptimizationResult>('/backtest/optimize', request)
}

// Settings API
export const settingsApi = {
  get: () => api.get<Settings>('/settings'),
  
  update: (settings: Partial<Settings>) =>
    api.put<Settings>('/settings', settings),
  
  getRiskStatus: () => api.get<RiskStatus>('/risk/status')
}
```

### カスタムフック
```typescript
// hooks/useTrades.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tradingApi } from '@/lib/api'

export function useTrades(limit?: number) {
  return useQuery({
    queryKey: ['trades', limit],
    queryFn: () => tradingApi.getTrades(limit),
    refetchInterval: 5000 // 5秒間隔で更新
  })
}

export function usePositions() {
  return useQuery({
    queryKey: ['positions'],
    queryFn: () => tradingApi.getPositions(),
    refetchInterval: 2000 // 2秒間隔で更新
  })
}

export function useStartTrading() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ symbol, timeframe }: { symbol: string, timeframe: string }) =>
      tradingApi.start(symbol, timeframe),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trading-status'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
    }
  })
}

export function useStopTrading() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => tradingApi.stop(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trading-status'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
    }
  })
}

// hooks/useBacktest.ts
export function useBacktest() {
  return useMutation({
    mutationFn: (request: BacktestRequest) => backtestApi.run(request)
  })
}

export function useBacktestResult(testId: string) {
  return useQuery({
    queryKey: ['backtest-result', testId],
    queryFn: () => backtestApi.getResult(testId),
    enabled: !!testId
  })
}
```

### コンポーネント実装例

#### ダッシュボード
```typescript
// app/dashboard/page.tsx
'use client'

import { Grid, Paper, Typography, Box } from '@mui/material'
import TradingPanel from '@/components/trading/TradingPanel'
import PositionsList from '@/components/trading/PositionsList'
import TradeHistory from '@/components/trading/TradeHistory'
import PerformanceChart from '@/components/charts/PerformanceChart'
import { useTrades, usePositions } from '@/hooks/useTrades'

export default function DashboardPage() {
  const { data: trades, isLoading: tradesLoading } = useTrades(50)
  const { data: positions, isLoading: positionsLoading } = usePositions()

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        ダッシュボード
      </Typography>
      
      <Grid container spacing={3}>
        {/* 取引制御パネル */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <TradingPanel />
          </Paper>
        </Grid>
        
        {/* パフォーマンスチャート */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              損益推移
            </Typography>
            <PerformanceChart data={trades} />
          </Paper>
        </Grid>
        
        {/* 現在のポジション */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              現在のポジション
            </Typography>
            <PositionsList 
              positions={positions} 
              loading={positionsLoading} 
            />
          </Paper>
        </Grid>
        
        {/* 取引履歴 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              最近の取引
            </Typography>
            <TradeHistory 
              trades={trades} 
              loading={tradesLoading} 
            />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}
```

#### 取引制御パネル
```typescript
// components/trading/TradingPanel.tsx
'use client'

import { useState } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box,
  Chip,
  Alert
} from '@mui/material'
import { PlayArrow, Stop } from '@mui/icons-material'
import { useStartTrading, useStopTrading } from '@/hooks/useTrades'
import { useTradingStore } from '@/store/trading'

export default function TradingPanel() {
  const { isActive, setIsActive } = useTradingStore()
  const [symbol, setSymbol] = useState('USDJPY')
  const [timeframe, setTimeframe] = useState('H1')
  
  const startTradingMutation = useStartTrading()
  const stopTradingMutation = useStopTrading()

  const handleStart = async () => {
    try {
      await startTradingMutation.mutateAsync({ symbol, timeframe })
      setIsActive(true)
    } catch (error) {
      console.error('Failed to start trading:', error)
    }
  }

  const handleStop = async () => {
    try {
      await stopTradingMutation.mutateAsync()
      setIsActive(false)
    } catch (error) {
      console.error('Failed to stop trading:', error)
    }
  }

  return (
    <Card>
      <CardHeader 
        title="取引制御"
        action={
          <Chip 
            label={isActive ? '稼働中' : '停止中'}
            color={isActive ? 'success' : 'default'}
          />
        }
      />
      <CardContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <FormControl fullWidth>
            <InputLabel>通貨ペア</InputLabel>
            <Select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              disabled={isActive}
            >
              <MenuItem value="USDJPY">USD/JPY</MenuItem>
              <MenuItem value="EURJPY">EUR/JPY</MenuItem>
              <MenuItem value="GBPJPY">GBP/JPY</MenuItem>
              <MenuItem value="AUDJPY">AUD/JPY</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>時間軸</InputLabel>
            <Select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              disabled={isActive}
            >
              <MenuItem value="M5">5分</MenuItem>
              <MenuItem value="M15">15分</MenuItem>
              <MenuItem value="M30">30分</MenuItem>
              <MenuItem value="H1">1時間</MenuItem>
              <MenuItem value="H4">4時間</MenuItem>
            </Select>
          </FormControl>

          {!isActive ? (
            <Button
              variant="contained"
              color="primary"
              startIcon={<PlayArrow />}
              onClick={handleStart}
              disabled={startTradingMutation.isPending}
              fullWidth
            >
              取引開始
            </Button>
          ) : (
            <Button
              variant="contained"
              color="error"
              startIcon={<Stop />}
              onClick={handleStop}
              disabled={stopTradingMutation.isPending}
              fullWidth
            >
              取引停止
            </Button>
          )}

          {(startTradingMutation.error || stopTradingMutation.error) && (
            <Alert severity="error">
              操作に失敗しました。再試行してください。
            </Alert>
          )}
        </Box>
      </CardContent>
    </Card>
  )
}
```

## パフォーマンス最適化
- React.memo の適切な使用
- 動的インポートによるコード分割
- 画像最適化
- Service Worker による キャッシュ

## レスポンシブ対応
- Material-UI Grid システム
- ブレークポイント: xs, sm, md, lg, xl
- モバイルファーストデザイン

## 見積もり
**5日**

## 依存関係
- チケット001: 環境構築

## 完了条件
- [ ] プロジェクトセットアップが完了
- [ ] ダッシュボード画面が動作する
- [ ] バックテスト画面が動作する
- [ ] 設定画面が動作する
- [ ] レスポンシブデザインが適用される
- [ ] APIとの連携が正常に動作する