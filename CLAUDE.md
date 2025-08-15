# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

XMTradingのMT5とPython、LightGBM機械学習モデルを統合したFX自動売買システムです。

## 重要: Windows バッチファイルの文字コード問題と対処法

### 問題
Windowsのバッチファイル（.bat）で日本語を使用すると、文字化けエラーが発生することがあります：
```
'繝ｧ繝ｳ繧貞ｮ御ｺ・＠縺ｾ縺励◆' は、内部コマンドまたは外部コマンド、
操作可能なプログラムまたはバッチ ファイルとして認識されていません。
```

### 原因
- Windowsのコマンドプロンプトとバッチファイルの文字エンコーディングの不一致
- `chcp 65001`（UTF-8設定）を使用しても完全には解決しない
- 特にPython 3.12環境では問題が発生しやすい

### 解決方法

#### 1. バッチファイルは英語のみで作成
```batch
@echo off
REM 日本語コメントは避ける - Avoid Japanese comments
echo Starting system...  REM "システムを起動中..." ではなく英語を使用
```

#### 2. シンプルなバッチファイルを使用
複雑な処理を避け、基本的なコマンドのみを使用：
```batch
@echo off
title Simple Start
python -m uvicorn backend.main:app
```

#### 3. 推奨バッチファイル
以下のシンプルなバッチファイルを使用することを推奨：
- `install_backend_simple.bat` - バックエンドパッケージのインストール
- `start_all.bat` - システム全体の起動
- `start_simple_backend.bat` - バックエンドのみ起動
- `start_simple_frontend.bat` - フロントエンドのみ起動

### Python 3.12での追加の注意事項

#### distutilsエラーの対処
Python 3.12では`distutils`が削除されたため、以下の対処が必要：

1. **UV (uv) を使用**（推奨）
```bash
pip install uv
python -m uv pip install [package]
```

2. **setuptoolsを先にインストール**
```bash
pip install --upgrade setuptools wheel
pip install [other-packages]
```

3. **互換性のあるパッケージバージョンを使用**
- `psycopg2-binary`の代わりに`psycopg[binary]`を使用
- 最新の安定版パッケージを使用

## 要件定義

### システム基本情報
- **ブローカー**: XMTrading
- **取引プラットフォーム**: MetaTrader 5 (MT5)
- **初期資金**: 10万円
- **口座タイプ**: 本番口座
- **認証情報管理**: JSONファイル（config/mt5_config.json）
- **運用形態**: 特定時間帯での自動売買
- **開発環境**: Windows / ローカル環境（将来的にクラウド移行）

### 第1段階実装機能（必須）

#### 1. 自動売買機能
- MT5 APIを通じた自動注文執行
- リアルタイム価格データ取得
- 同時監視: 1通貨ペアのみ
- 注文執行時間: 1分以内

#### 2. LightGBM機械学習エンジン
- **使用する特徴量**:
  - テクニカル指標（RSI, MACD, ボリンジャーバンド等）
  - 価格パターン認識
  - 市場ボラティリティ
  - 時間的特徴（時間帯、曜日）

#### 3. バックテスト機能
- 検証期間: 過去1年
- 全通貨ペア・全時間軸の自動検証
- 対象通貨: USD/JPY, EUR/JPY, GBP/JPY, AUD/JPY, NZD/JPY, CAD/JPY, CHF/JPY
- 時間軸: M1, M5, M15, M30, H1, H4, D1

#### 4. 時間帯分析機能
- 市場別分析（東京、ロンドン、ニューヨーク）
- 曜日別パフォーマンス分析
- 経済指標カレンダー連携
- 勝率の高い時間帯の自動検出

#### 5. リスク管理（すべて設定可能）
```json
{
  "1取引あたり最大リスク": "デフォルト20%（設定可能）",
  "最大ドローダウン": "デフォルト20%（設定可能）",
  "ナンピン機能": "デフォルトON（設定可能）",
  "ナンピン最大回数": 3,
  "ナンピン間隔": "10pips",
  "ロット配分": "等倍"
}
```

#### 6. Web管理画面
- ダッシュボード（リアルタイム損益、ポジション状況）
- 設定画面（リスクパラメータ、取引時間帯）
- バックテスト実行・結果表示

#### 7. リアルタイム監視
- アラート機能（損失、エラー、ドローダウン）
- ログ表示（取引、システム、エラー）
- ログ保存期間: 3ヶ月

### 技術スタック

```yaml
Backend:
  - Python 3.9+
  - FastAPI
  - MetaTrader5 Python Package
  - LightGBM
  - PostgreSQL + TimescaleDB
  - Redis
  - Celery

Frontend:
  - Next.js 14+ (App Router)
  - TypeScript
  - Material-UI or Ant Design
  - Chart.js or Recharts
  - TanStack Query (React Query)
  - Zustand (状態管理)
```

## プロジェクト構造

```
FX_A/
├── backend/
│   ├── api/                 # FastAPI エンドポイント
│   ├── core/                # コア機能
│   │   ├── mt5_client.py   # MT5接続
│   │   ├── trading_engine.py
│   │   └── risk_manager.py
│   ├── ml/                  # 機械学習
│   │   ├── models/
│   │   ├── features.py
│   │   └── predictor.py
│   ├── backtest/            # バックテスト
│   ├── analysis/            # 分析機能
│   └── config/              # 設定
├── frontend/                # Next.js アプリ
│   ├── app/                 # App Router (Next.js 13+)
│   │   ├── api/            # API Routes
│   │   ├── dashboard/      # ダッシュボードページ
│   │   ├── backtest/       # バックテストページ
│   │   ├── settings/       # 設定ページ
│   │   ├── layout.tsx      # ルートレイアウト
│   │   └── page.tsx        # ホームページ
│   ├── components/         # 再利用可能コンポーネント
│   │   ├── ui/            # 基本UIコンポーネント
│   │   ├── charts/        # チャートコンポーネント
│   │   ├── forms/         # フォームコンポーネント
│   │   └── layout/        # レイアウトコンポーネント
│   ├── hooks/             # カスタムフック
│   ├── lib/               # ユーティリティ関数
│   ├── store/             # Zustand ストア
│   ├── types/             # TypeScript型定義
│   └── styles/            # CSS/Tailwind設定
├── database/               # DB スキーマ
├── config/
│   └── mt5_config.json     # MT5認証情報
├── logs/                   # ログファイル
├── data/                   # データ保存
└── tests/                  # テスト
```

## 開発コマンド

### Python環境セットアップ
```bash
# 仮想環境作成
python -m venv venv

# 仮想環境有効化（Windows）
venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt
```

### バックエンド起動
```bash
# FastAPIサーバー起動
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Celeryワーカー起動
celery -A backend.tasks worker --loglevel=info

# データベースマイグレーション
alembic upgrade head
```

### フロントエンド起動
```bash
cd frontend

# 依存関係インストール
npm install

# 開発サーバー起動
npm run dev

# 本番ビルド
npm run build

# 本番サーバー起動
npm run start

# ESLint実行
npm run lint

# Prisma（使用する場合）
npx prisma generate
npx prisma db push
```

### テスト実行
```bash
# 単体テスト
pytest tests/unit

# 統合テスト
pytest tests/integration

# カバレッジ付きテスト
pytest --cov=backend tests/
```

## API仕様

### 主要エンドポイント

```yaml
# 取引制御
POST   /api/v1/trading/start      # 自動売買開始
POST   /api/v1/trading/stop       # 自動売買停止
GET    /api/v1/trading/status     # 稼働状態取得

# ポジション管理
GET    /api/v1/positions          # 現在のポジション
GET    /api/v1/trades            # 取引履歴

# バックテスト
POST   /api/v1/backtest/run       # バックテスト実行
GET    /api/v1/backtest/results/{id}  # 結果取得

# 分析
GET    /api/v1/analysis/timeframe # 時間帯別分析
GET    /api/v1/analysis/weekday   # 曜日別分析

# 設定
GET    /api/v1/settings          # 設定取得
PUT    /api/v1/settings          # 設定更新
```

## データベース設計

### 主要テーブル

```sql
-- 取引履歴
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    order_type VARCHAR(10),
    entry_time TIMESTAMP,
    entry_price DECIMAL(10,5),
    exit_time TIMESTAMP,
    exit_price DECIMAL(10,5),
    volume DECIMAL(10,2),
    profit_loss DECIMAL(10,2)
);

-- 価格データ
CREATE TABLE price_data (
    symbol VARCHAR(10),
    timeframe VARCHAR(5),
    time TIMESTAMP,
    open DECIMAL(10,5),
    high DECIMAL(10,5),
    low DECIMAL(10,5),
    close DECIMAL(10,5),
    tick_volume BIGINT
);

-- バックテスト結果
CREATE TABLE backtest_results (
    test_id UUID,
    symbol VARCHAR(10),
    timeframe VARCHAR(5),
    period_start DATE,
    period_end DATE,
    total_trades INT,
    winning_trades INT,
    profit_factor DECIMAL(5,2),
    max_drawdown DECIMAL(5,2),
    parameters JSONB
);
```

## 開発スケジュール

1. **基盤構築**（2週間）
   - 開発環境セットアップ
   - MT5接続テスト
   - データベース構築

2. **コア機能実装**（3週間）
   - MT5データ取得
   - LightGBMモデル実装
   - 売買ロジック
   - リスク管理

3. **バックテスト機能**（2週間）
   - バックテストエンジン
   - パラメータ最適化

4. **分析機能**（1週間）
   - 時間帯分析
   - 経済指標連携

5. **Web UI実装**（2週間）
   - ダッシュボード
   - 設定画面
   - バックテスト画面

6. **テスト・調整**（2週間）
   - 統合テスト
   - デモ環境検証

## 重要な注意事項

### リスク管理
- デフォルトのリスク設定（20%）は高リスクのため、実運用前に適切な値に調整すること
- 初期はデモ口座で十分なテストを実施
- システムエラー時の自動停止機能を必ず実装

### セキュリティ
- MT5認証情報は必ず暗号化して保存
- config/mt5_config.jsonはGitにコミットしない（.gitignoreに追加）
- Web画面はJWT認証で保護

### 運用
- バックアップは起動時に自動実行
- ログは3ヶ月保存
- 定期的なモデルの再学習が必要

### パフォーマンス目標
- 注文執行: 1分以内
- 稼働率: 99%以上
- 月間プロフィットファクター: 1.5以上
- 最大ドローダウン: 20%以内

## TODO管理ルール

このプロジェクトでは各チケットファイル（/doc配下）でタスクの進捗を管理します。

### チェックボックス記法
- `- [ ]` : 未完了タスク
- `- [×]` : 完了タスク

### 完了の記録方法
タスクを完了したら、以下のように記録してください：

```markdown
## 受け入れ基準
- [×] MT5接続クライアントクラスの実装
- [×] 価格データ取得APIの実装  
- [ ] データベース保存機能
- [ ] WebSocket経由のリアルタイム配信
- [ ] エラー処理と自動再接続機能
```

### 進捗確認
各チケットの進捗は以下で確認できます：
- 受け入れ基準のチェックボックス状況
- 完了条件のチェックボックス状況

### チケット一覧
1. **001_環境構築.md** - 開発環境のセットアップ
2. **002_MT5データ取得機能.md** - MT5からのデータ取得
3. **003_データベース設計実装.md** - DB設計と実装
4. **004_LightGBM機械学習エンジン.md** - ML予測モデル
5. **005_自動売買エンジン.md** - 取引実行エンジン
6. **006_リスク管理機能.md** - リスク制御システム
7. **007_バックテスト機能.md** - 戦略検証システム
8. **008_時間帯分析機能.md** - 時間帯別分析
9. **009_Next.jsフロントエンド.md** - Web UI実装
10. **010_リアルタイム監視機能.md** - 監視システム
11. **011_テスト実装.md** - テストスイート
12. **012_本番環境構築.md** - 本番デプロイ

### 開発順序
依存関係に基づく推奨実装順序：
1. 001 → 003 → 002
2. 004 → 006 → 005  
3. 007 → 008
4. 009 → 010
5. 011 → 012

総開発期間：約12週間（3ヶ月）

## Next.jsベストプラクティス

### 1. アーキテクチャパターン

#### App Router使用
```typescript
// app/layout.tsx - ルートレイアウト
import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'FX Trading System',
  description: 'Automated FX Trading with ML'
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  )
}

// app/dashboard/page.tsx - ページコンポーネント
export default function DashboardPage() {
  return <DashboardContent />
}
```

#### Server/Client Components分離
```typescript
// Server Component（デフォルト）
async function TradingData() {
  const data = await fetch('http://localhost:8000/api/v1/trades')
  return <TradesList trades={data} />
}

// Client Component
'use client'
import { useState } from 'react'

function InteractiveChart() {
  const [timeframe, setTimeframe] = useState('H1')
  // インタラクティブな機能
}
```

### 2. 状態管理（Zustand）

```typescript
// store/trading.ts
import { create } from 'zustand'

interface TradingState {
  isActive: boolean
  currentPositions: Position[]
  setIsActive: (active: boolean) => void
  addPosition: (position: Position) => void
}

export const useTradingStore = create<TradingState>((set) => ({
  isActive: false,
  currentPositions: [],
  setIsActive: (active) => set({ isActive: active }),
  addPosition: (position) => 
    set((state) => ({ 
      currentPositions: [...state.currentPositions, position] 
    })),
}))
```

### 3. データフェッチング（TanStack Query）

```typescript
// hooks/useTrades.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

export function useTrades() {
  return useQuery({
    queryKey: ['trades'],
    queryFn: async () => {
      const response = await fetch('/api/trades')
      return response.json()
    },
    refetchInterval: 5000, // 5秒間隔で更新
  })
}

export function useStartTrading() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async () => {
      return fetch('/api/trading/start', { method: 'POST' })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trading-status'] })
    },
  })
}
```

### 4. コンポーネント設計

#### 再利用可能なUIコンポーネント
```typescript
// components/ui/Button.tsx
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

export function Button({ 
  variant = 'primary', 
  size = 'md', 
  className,
  ...props 
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-md font-medium',
        {
          'bg-blue-600 text-white hover:bg-blue-700': variant === 'primary',
          'bg-red-600 text-white hover:bg-red-700': variant === 'danger',
        },
        className
      )}
      {...props}
    />
  )
}
```

#### ビジネスロジックコンポーネント
```typescript
// components/trading/TradingPanel.tsx
'use client'

export function TradingPanel() {
  const { isActive } = useTradingStore()
  const startTradingMutation = useStartTrading()
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>取引制御</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2">
          <Button 
            onClick={() => startTradingMutation.mutate()}
            disabled={isActive}
          >
            取引開始
          </Button>
          <TradingStatus status={isActive ? 'active' : 'stopped'} />
        </div>
      </CardContent>
    </Card>
  )
}
```

### 5. API Routes

```typescript
// app/api/trading/start/route.ts
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    // バックエンドAPIへのプロキシ
    const response = await fetch('http://localhost:8000/api/v1/trading/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken(request)}`,
      },
    })
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    )
  }
}
```

### 6. 型安全性

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
}

export interface BacktestResult {
  testId: string
  symbol: string
  timeframe: string
  totalTrades: number
  winningTrades: number
  profitFactor: number
  maxDrawdown: number
  parameters: Record<string, any>
}

export interface TradingSettings {
  maxRiskPerTrade: number
  maxDrawdown: number
  useNanpin: boolean
  nanpinMaxCount: number
  tradingHours: {
    start: string
    end: string
  }
}
```

### 7. パフォーマンス最適化

#### 動的インポート
```typescript
// 重いチャートコンポーネントの遅延読み込み
import dynamic from 'next/dynamic'

const TradingChart = dynamic(() => import('./TradingChart'), {
  loading: () => <ChartSkeleton />,
  ssr: false, // サーバーサイドレンダリング無効
})
```

#### メモ化
```typescript
'use client'
import { memo, useMemo } from 'react'

export const TradesList = memo(function TradesList({ trades }: { trades: Trade[] }) {
  const sortedTrades = useMemo(() => 
    trades.sort((a, b) => new Date(b.openTime).getTime() - new Date(a.openTime).getTime()),
    [trades]
  )
  
  return (
    <div>
      {sortedTrades.map(trade => (
        <TradeItem key={trade.id} trade={trade} />
      ))}
    </div>
  )
})
```

### 8. エラーハンドリング

```typescript
// app/error.tsx - エラーバウンダリ
'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h2 className="text-2xl font-bold mb-4">エラーが発生しました</h2>
      <p className="text-gray-600 mb-4">{error.message}</p>
      <Button onClick={reset}>再試行</Button>
    </div>
  )
}

// app/loading.tsx - ローディング画面
export default function Loading() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
    </div>
  )
}
```

### 9. 環境設定

```typescript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // Dockerでの最適化
  experimental: {
    serverComponentsExternalPackages: ['@prisma/client'], // Prisma使用時
  },
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: 'http://localhost:8000/api/v1/:path*', // バックエンドAPI
      },
    ]
  },
}

module.exports = nextConfig
```

### 10. 開発・デバッグ

```typescript
// lib/logger.ts - クライアントサイドログ
export const logger = {
  info: (message: string, data?: any) => {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[INFO] ${message}`, data)
    }
  },
  error: (message: string, error?: any) => {
    console.error(`[ERROR] ${message}`, error)
    // 本番環境では外部ログサービスに送信
  },
}

// React DevTools用のカスタムフック
export function useDebugValue(value: any, formatter?: (value: any) => any) {
  if (process.env.NODE_ENV === 'development') {
    React.useDebugValue(value, formatter)
  }
}
```

### 11. 推奨パッケージ構成

```json
{
  "dependencies": {
    "next": "^14.0.0",
    "@tanstack/react-query": "^4.29.0",
    "zustand": "^4.3.0",
    "@mui/material": "^5.14.0",
    "recharts": "^2.7.0",
    "date-fns": "^2.30.0",
    "zod": "^3.21.0",
    "react-hook-form": "^7.45.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0",
    "@types/react": "^18.0.0",
    "eslint": "^8.44.0",
    "eslint-config-next": "^14.0.0",
    "tailwindcss": "^3.3.0"
  }
}
```