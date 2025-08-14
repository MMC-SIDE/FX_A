// テストユーティリティ
import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'

// テスト用のテーマ
const testTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
})

// テスト用の QueryClient を作成
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      gcTime: 0,
    },
    mutations: {
      retry: false,
    },
  },
})

interface AllTheProvidersProps {
  children: React.ReactNode
}

// すべてのプロバイダーを含むラッパーコンポーネント
const AllTheProviders: React.FC<AllTheProvidersProps> = ({ children }) => {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={testTheme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  )
}

// カスタムレンダー関数
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options })

// ユーティリティ関数をエクスポート
export * from '@testing-library/react'
export { customRender as render }

// モックデータジェネレーター
export const mockTradingData = {
  // モックポジションデータ
  positions: [
    {
      id: '1',
      symbol: 'USDJPY',
      type: 'BUY',
      volume: 0.1,
      openPrice: 130.00,
      currentPrice: 130.25,
      profit: 250,
      openTime: '2023-01-01T09:00:00Z',
    },
    {
      id: '2',
      symbol: 'EURJPY',
      type: 'SELL',
      volume: 0.05,
      openPrice: 145.50,
      currentPrice: 145.30,
      profit: 100,
      openTime: '2023-01-01T10:00:00Z',
    },
  ],

  // モック取引履歴データ
  trades: [
    {
      id: '1',
      symbol: 'USDJPY',
      orderType: 'BUY',
      entryTime: '2023-01-01T09:00:00Z',
      entryPrice: 130.00,
      exitTime: '2023-01-01T10:00:00Z',
      exitPrice: 130.25,
      volume: 0.1,
      profitLoss: 250,
    },
    {
      id: '2',
      symbol: 'EURJPY',
      orderType: 'SELL',
      entryTime: '2023-01-01T11:00:00Z',
      entryPrice: 145.50,
      exitTime: '2023-01-01T12:00:00Z',
      exitPrice: 145.30,
      volume: 0.05,
      profitLoss: 100,
    },
  ],

  // モックバックテスト結果
  backtestResult: {
    testId: 'test_123',
    symbol: 'USDJPY',
    timeframe: 'H1',
    totalTrades: 50,
    winningTrades: 30,
    profitFactor: 1.5,
    maxDrawdown: 12.5,
    totalProfit: 5000,
    winRate: 60.0,
  },

  // モックシステム統計
  systemStats: {
    cpuUsage: 45.2,
    memoryUsage: 68.7,
    diskUsage: 23.1,
    networkIO: {
      received: 1024000,
      sent: 512000,
    },
    mt5Connection: true,
    databaseConnection: true,
  },

  // モックアラート
  alerts: [
    {
      id: 'alert_1',
      level: 'WARNING',
      alertType: 'SYSTEM',
      message: 'High CPU usage detected',
      createdAt: '2023-01-01T12:00:00Z',
      acknowledged: false,
    },
    {
      id: 'alert_2',
      level: 'ERROR',
      alertType: 'TRADING',
      message: 'MT5 connection lost',
      createdAt: '2023-01-01T12:05:00Z',
      acknowledged: true,
    },
  ],
}

// モックAPIレスポンス
export const mockApiResponses = {
  // 成功レスポンス
  success: (data: any) => ({
    json: jest.fn().mockResolvedValue(data),
    ok: true,
    status: 200,
    statusText: 'OK',
  }),

  // エラーレスポンス
  error: (status: number, message: string) => ({
    json: jest.fn().mockResolvedValue({ error: message }),
    ok: false,
    status,
    statusText: message,
  }),

  // ネットワークエラー
  networkError: () => Promise.reject(new Error('Network Error')),
}

// ユーザーイベントのヘルパー
export const userEvents = {
  clickButton: async (buttonText: string) => {
    const { user } = await import('@testing-library/user-event')
    const button = await import('@testing-library/react').then(lib =>
      lib.screen.getByRole('button', { name: buttonText })
    )
    await user.click(button)
  },

  typeInput: async (labelText: string, value: string) => {
    const { user } = await import('@testing-library/user-event')
    const input = await import('@testing-library/react').then(lib =>
      lib.screen.getByLabelText(labelText)
    )
    await user.clear(input)
    await user.type(input, value)
  },

  selectOption: async (labelText: string, option: string) => {
    const { user } = await import('@testing-library/user-event')
    const select = await import('@testing-library/react').then(lib =>
      lib.screen.getByLabelText(labelText)
    )
    await user.selectOptions(select, option)
  },
}

// WebSocket モックヘルパー
export const createMockWebSocket = () => {
  const mockWS = {
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    readyState: WebSocket.OPEN,
    onopen: null,
    onmessage: null,
    onerror: null,
    onclose: null,
  }

  // メッセージ送信のシミュレーション
  const simulateMessage = (data: any) => {
    if (mockWS.onmessage) {
      mockWS.onmessage({ data: JSON.stringify(data) } as MessageEvent)
    }
  }

  // 接続確立のシミュレーション
  const simulateOpen = () => {
    if (mockWS.onopen) {
      mockWS.onopen({} as Event)
    }
  }

  // エラーのシミュレーション
  const simulateError = (error: Error) => {
    if (mockWS.onerror) {
      mockWS.onerror({ error } as ErrorEvent)
    }
  }

  // 切断のシミュレーション
  const simulateClose = () => {
    if (mockWS.onclose) {
      mockWS.onclose({} as CloseEvent)
    }
  }

  return {
    mockWS,
    simulateMessage,
    simulateOpen,
    simulateError,
    simulateClose,
  }
}

// ローカルストレージのモック
export const mockLocalStorage = {
  store: {} as { [key: string]: string },
  
  getItem: jest.fn((key: string) => mockLocalStorage.store[key] || null),
  setItem: jest.fn((key: string, value: string) => {
    mockLocalStorage.store[key] = value
  }),
  removeItem: jest.fn((key: string) => {
    delete mockLocalStorage.store[key]
  }),
  clear: jest.fn(() => {
    mockLocalStorage.store = {}
  }),
}

// テスト用のカスタムマッチャー
expect.extend({
  toBeVisibleAndEnabled(received) {
    const pass = received.style.display !== 'none' && !received.disabled
    return {
      message: () =>
        `expected element to be ${pass ? 'not ' : ''}visible and enabled`,
      pass,
    }
  },
})