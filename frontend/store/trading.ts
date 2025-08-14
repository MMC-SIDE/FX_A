/**
 * 取引関連のZustandストア
 */
import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { Position, Trade, TradingStatus, RiskStatus } from '@/types/trading'

interface TradingState {
  // 状態
  isActive: boolean
  currentPositions: Position[]
  recentTrades: Trade[]
  tradingStatus: TradingStatus | null
  riskStatus: RiskStatus | null
  selectedSymbol: string
  selectedTimeframe: string
  
  // WebSocket接続状態
  isConnected: boolean
  lastUpdate: Date | null
  
  // エラー状態
  error: string | null
  isLoading: boolean
  
  // Actions
  setIsActive: (active: boolean) => void
  setPositions: (positions: Position[]) => void
  addPosition: (position: Position) => void
  updatePosition: (positionId: string, updates: Partial<Position>) => void
  removePosition: (positionId: string) => void
  
  addTrade: (trade: Trade) => void
  setTrades: (trades: Trade[]) => void
  updateTrade: (tradeId: string, updates: Partial<Trade>) => void
  
  setTradingStatus: (status: TradingStatus) => void
  setRiskStatus: (status: RiskStatus) => void
  
  setSelectedSymbol: (symbol: string) => void
  setSelectedTimeframe: (timeframe: string) => void
  
  setConnected: (connected: boolean) => void
  setLastUpdate: (date: Date) => void
  
  setError: (error: string | null) => void
  setLoading: (loading: boolean) => void
  
  clearData: () => void
  reset: () => void
}

const initialState = {
  isActive: false,
  currentPositions: [],
  recentTrades: [],
  tradingStatus: null,
  riskStatus: null,
  selectedSymbol: 'USDJPY',
  selectedTimeframe: 'H1',
  isConnected: false,
  lastUpdate: null,
  error: null,
  isLoading: false
}

export const useTradingStore = create<TradingState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,
        
        setIsActive: (active) => 
          set({ isActive: active }, false, 'setIsActive'),
        
        setPositions: (positions) => 
          set({ currentPositions: positions, lastUpdate: new Date() }, false, 'setPositions'),
        
        addPosition: (position) => 
          set((state) => ({
            currentPositions: [...state.currentPositions, position],
            lastUpdate: new Date()
          }), false, 'addPosition'),
        
        updatePosition: (positionId, updates) => 
          set((state) => ({
            currentPositions: state.currentPositions.map(pos =>
              pos.id === positionId ? { ...pos, ...updates } : pos
            ),
            lastUpdate: new Date()
          }), false, 'updatePosition'),
        
        removePosition: (positionId) => 
          set((state) => ({
            currentPositions: state.currentPositions.filter(pos => pos.id !== positionId),
            lastUpdate: new Date()
          }), false, 'removePosition'),
        
        addTrade: (trade) => 
          set((state) => ({
            recentTrades: [trade, ...state.recentTrades].slice(0, 100), // 最新100件を保持
            lastUpdate: new Date()
          }), false, 'addTrade'),
        
        setTrades: (trades) => 
          set({ recentTrades: trades, lastUpdate: new Date() }, false, 'setTrades'),
        
        updateTrade: (tradeId, updates) => 
          set((state) => ({
            recentTrades: state.recentTrades.map(trade =>
              trade.id === tradeId ? { ...trade, ...updates } : trade
            ),
            lastUpdate: new Date()
          }), false, 'updateTrade'),
        
        setTradingStatus: (status) => 
          set({ tradingStatus: status, lastUpdate: new Date() }, false, 'setTradingStatus'),
        
        setRiskStatus: (status) => 
          set({ riskStatus: status, lastUpdate: new Date() }, false, 'setRiskStatus'),
        
        setSelectedSymbol: (symbol) => 
          set({ selectedSymbol: symbol }, false, 'setSelectedSymbol'),
        
        setSelectedTimeframe: (timeframe) => 
          set({ selectedTimeframe: timeframe }, false, 'setSelectedTimeframe'),
        
        setConnected: (connected) => 
          set({ isConnected: connected }, false, 'setConnected'),
        
        setLastUpdate: (date) => 
          set({ lastUpdate: date }, false, 'setLastUpdate'),
        
        setError: (error) => 
          set({ error }, false, 'setError'),
        
        setLoading: (loading) => 
          set({ isLoading: loading }, false, 'setLoading'),
        
        clearData: () => 
          set({
            currentPositions: [],
            recentTrades: [],
            tradingStatus: null,
            lastUpdate: new Date()
          }, false, 'clearData'),
        
        reset: () => 
          set(initialState, false, 'reset')
      }),
      {
        name: 'trading-store',
        partialize: (state) => ({
          selectedSymbol: state.selectedSymbol,
          selectedTimeframe: state.selectedTimeframe
        })
      }
    ),
    {
      name: 'trading-store'
    }
  )
)

// セレクター（パフォーマンス最適化）
export const useTradingSelectors = () => {
  const store = useTradingStore()
  
  return {
    // 基本状態
    isActive: store.isActive,
    isLoading: store.isLoading,
    error: store.error,
    isConnected: store.isConnected,
    
    // データ
    positions: store.currentPositions,
    trades: store.recentTrades,
    status: store.tradingStatus,
    riskStatus: store.riskStatus,
    
    // 選択中の設定
    selectedSymbol: store.selectedSymbol,
    selectedTimeframe: store.selectedTimeframe,
    
    // 計算されたプロパティ
    totalPositions: store.currentPositions.length,
    totalProfit: store.currentPositions.reduce((sum, pos) => sum + pos.profit, 0),
    hasActivePositions: store.currentPositions.length > 0,
    
    recentTradesCount: store.recentTrades.length,
    todaysTrades: store.recentTrades.filter(trade => {
      const today = new Date()
      const tradeDate = new Date(trade.entryTime)
      return tradeDate.toDateString() === today.toDateString()
    }),
    
    profitableTrades: store.recentTrades.filter(trade => 
      trade.profitLoss && trade.profitLoss > 0
    ).length,
    
    lastUpdate: store.lastUpdate
  }
}

// アクションフック
export const useTradingActions = () => {
  const store = useTradingStore()
  
  return {
    setIsActive: store.setIsActive,
    setPositions: store.setPositions,
    addPosition: store.addPosition,
    updatePosition: store.updatePosition,
    removePosition: store.removePosition,
    addTrade: store.addTrade,
    setTrades: store.setTrades,
    updateTrade: store.updateTrade,
    setTradingStatus: store.setTradingStatus,
    setRiskStatus: store.setRiskStatus,
    setSelectedSymbol: store.setSelectedSymbol,
    setSelectedTimeframe: store.setSelectedTimeframe,
    setConnected: store.setConnected,
    setLastUpdate: store.setLastUpdate,
    setError: store.setError,
    setLoading: store.setLoading,
    clearData: store.clearData,
    reset: store.reset
  }
}

// WebSocket更新用のヘルパー
export const updateFromWebSocket = (message: any) => {
  const { setPositions, addTrade, setTradingStatus, setRiskStatus, setLastUpdate } = useTradingStore.getState()
  
  switch (message.type) {
    case 'POSITION_UPDATE':
      if (Array.isArray(message.data)) {
        setPositions(message.data)
      }
      break
      
    case 'TRADE_UPDATE':
      if (message.data) {
        addTrade(message.data)
      }
      break
      
    case 'STATUS_UPDATE':
      if (message.data) {
        setTradingStatus(message.data)
      }
      break
      
    case 'RISK_UPDATE':
      if (message.data) {
        setRiskStatus(message.data)
      }
      break
  }
  
  setLastUpdate(new Date())
}