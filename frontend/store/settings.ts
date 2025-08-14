/**
 * 設定関連のZustandストア
 */
import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { Settings, RiskSettings, TradingSettings } from '@/types/trading'
import { DEFAULT_RISK_SETTINGS, DEFAULT_TRADING_SETTINGS } from '@/lib/constants'

interface SettingsState {
  // 設定データ
  riskSettings: RiskSettings
  tradingSettings: TradingSettings
  uiSettings: {
    theme: 'light' | 'dark' | 'system'
    language: 'ja' | 'en'
    sidebarCollapsed: boolean
    chartType: 'candlestick' | 'line' | 'area'
    autoRefresh: boolean
    soundEnabled: boolean
    notificationsEnabled: boolean
  }
  
  // 状態
  isLoading: boolean
  error: string | null
  lastSaved: Date | null
  isDirty: boolean // 未保存の変更があるかどうか
  
  // Actions
  updateRiskSettings: (settings: Partial<RiskSettings>) => void
  updateTradingSettings: (settings: Partial<TradingSettings>) => void
  updateUISettings: (settings: Partial<SettingsState['uiSettings']>) => void
  
  setSettings: (settings: Settings) => void
  resetSettings: () => void
  resetRiskSettings: () => void
  resetTradingSettings: () => void
  
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setSaved: (date: Date) => void
  setDirty: (dirty: boolean) => void
  
  // バリデーション
  validateRiskSettings: (settings: Partial<RiskSettings>) => string[]
  validateTradingSettings: (settings: Partial<TradingSettings>) => string[]
  
  // エクスポート/インポート
  exportSettings: () => string
  importSettings: (data: string) => boolean
}

const defaultUISettings = {
  theme: 'light' as const,
  language: 'ja' as const,
  sidebarCollapsed: false,
  chartType: 'candlestick' as const,
  autoRefresh: true,
  soundEnabled: true,
  notificationsEnabled: true
}

const initialState = {
  riskSettings: DEFAULT_RISK_SETTINGS,
  tradingSettings: DEFAULT_TRADING_SETTINGS,
  uiSettings: defaultUISettings,
  isLoading: false,
  error: null,
  lastSaved: null,
  isDirty: false
}

export const useSettingsStore = create<SettingsState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,
        
        updateRiskSettings: (updates) => {
          const current = get().riskSettings
          const newSettings = { ...current, ...updates }
          
          // バリデーション
          const errors = get().validateRiskSettings(newSettings)
          if (errors.length > 0) {
            set({ error: errors.join(', ') }, false, 'updateRiskSettings:validation-error')
            return
          }
          
          set({
            riskSettings: newSettings,
            isDirty: true,
            error: null
          }, false, 'updateRiskSettings')
        },
        
        updateTradingSettings: (updates) => {
          const current = get().tradingSettings
          const newSettings = { ...current, ...updates }
          
          // バリデーション
          const errors = get().validateTradingSettings(newSettings)
          if (errors.length > 0) {
            set({ error: errors.join(', ') }, false, 'updateTradingSettings:validation-error')
            return
          }
          
          set({
            tradingSettings: newSettings,
            isDirty: true,
            error: null
          }, false, 'updateTradingSettings')
        },
        
        updateUISettings: (updates) => 
          set((state) => ({
            uiSettings: { ...state.uiSettings, ...updates }
          }), false, 'updateUISettings'),
        
        setSettings: (settings) => 
          set({
            riskSettings: settings.risk,
            tradingSettings: settings.trading,
            isDirty: false,
            lastSaved: new Date(),
            error: null
          }, false, 'setSettings'),
        
        resetSettings: () => 
          set({
            ...initialState,
            uiSettings: get().uiSettings // UI設定は保持
          }, false, 'resetSettings'),
        
        resetRiskSettings: () => 
          set({
            riskSettings: DEFAULT_RISK_SETTINGS,
            isDirty: true
          }, false, 'resetRiskSettings'),
        
        resetTradingSettings: () => 
          set({
            tradingSettings: DEFAULT_TRADING_SETTINGS,
            isDirty: true
          }, false, 'resetTradingSettings'),
        
        setLoading: (loading) => 
          set({ isLoading: loading }, false, 'setLoading'),
        
        setError: (error) => 
          set({ error }, false, 'setError'),
        
        setSaved: (date) => 
          set({ lastSaved: date, isDirty: false }, false, 'setSaved'),
        
        setDirty: (dirty) => 
          set({ isDirty: dirty }, false, 'setDirty'),
        
        validateRiskSettings: (settings) => {
          const errors: string[] = []
          
          if (settings.maxRiskPerTrade !== undefined) {
            if (settings.maxRiskPerTrade < 0.1 || settings.maxRiskPerTrade > 50) {
              errors.push('取引あたり最大リスクは0.1%〜50%の範囲で入力してください')
            }
          }
          
          if (settings.maxDrawdown !== undefined) {
            if (settings.maxDrawdown < 1 || settings.maxDrawdown > 80) {
              errors.push('最大ドローダウンは1%〜80%の範囲で入力してください')
            }
          }
          
          if (settings.nanpinMaxCount !== undefined) {
            if (settings.nanpinMaxCount < 1 || settings.nanpinMaxCount > 10) {
              errors.push('ナンピン最大回数は1〜10回の範囲で入力してください')
            }
          }
          
          if (settings.nanpinInterval !== undefined) {
            if (settings.nanpinInterval < 1 || settings.nanpinInterval > 100) {
              errors.push('ナンピン間隔は1〜100pipsの範囲で入力してください')
            }
          }
          
          if (settings.stopLossPips !== undefined) {
            if (settings.stopLossPips < 1 || settings.stopLossPips > 1000) {
              errors.push('ストップロスは1〜1000pipsの範囲で入力してください')
            }
          }
          
          if (settings.takeProfitPips !== undefined) {
            if (settings.takeProfitPips < 1 || settings.takeProfitPips > 1000) {
              errors.push('テイクプロフィットは1〜1000pipsの範囲で入力してください')
            }
          }
          
          if (settings.maxPositions !== undefined) {
            if (settings.maxPositions < 1 || settings.maxPositions > 20) {
              errors.push('最大ポジション数は1〜20の範囲で入力してください')
            }
          }
          
          return errors
        },
        
        validateTradingSettings: (settings) => {
          const errors: string[] = []
          
          if (settings.riskPerTrade !== undefined) {
            if (settings.riskPerTrade < 0.1 || settings.riskPerTrade > 10) {
              errors.push('取引リスクは0.1%〜10%の範囲で入力してください')
            }
          }
          
          if (settings.tradingHours) {
            const { start, end } = settings.tradingHours
            if (start && end) {
              const startTime = new Date(`2000-01-01 ${start}`)
              const endTime = new Date(`2000-01-01 ${end}`)
              
              if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) {
                errors.push('取引時間の形式が正しくありません（HH:MM）')
              }
            }
          }
          
          return errors
        },
        
        exportSettings: () => {
          const state = get()
          const exportData = {
            riskSettings: state.riskSettings,
            tradingSettings: state.tradingSettings,
            uiSettings: state.uiSettings,
            exportedAt: new Date().toISOString(),
            version: '1.0'
          }
          return JSON.stringify(exportData, null, 2)
        },
        
        importSettings: (data) => {
          try {
            const parsed = JSON.parse(data)
            
            // バージョンチェック
            if (parsed.version !== '1.0') {
              set({ error: 'サポートされていない設定ファイルのバージョンです' }, false, 'importSettings:version-error')
              return false
            }
            
            // データ検証
            if (!parsed.riskSettings || !parsed.tradingSettings) {
              set({ error: '設定ファイルの形式が正しくありません' }, false, 'importSettings:format-error')
              return false
            }
            
            // バリデーション
            const riskErrors = get().validateRiskSettings(parsed.riskSettings)
            const tradingErrors = get().validateTradingSettings(parsed.tradingSettings)
            
            if (riskErrors.length > 0 || tradingErrors.length > 0) {
              const allErrors = [...riskErrors, ...tradingErrors]
              set({ error: `設定値が正しくありません: ${allErrors.join(', ')}` }, false, 'importSettings:validation-error')
              return false
            }
            
            // 設定を適用
            set({
              riskSettings: parsed.riskSettings,
              tradingSettings: parsed.tradingSettings,
              uiSettings: parsed.uiSettings || get().uiSettings,
              isDirty: true,
              error: null
            }, false, 'importSettings:success')
            
            return true
          } catch (error) {
            set({ error: '設定ファイルの読み込みに失敗しました' }, false, 'importSettings:parse-error')
            return false
          }
        }
      }),
      {
        name: 'settings-store',
        partialize: (state) => ({
          riskSettings: state.riskSettings,
          tradingSettings: state.tradingSettings,
          uiSettings: state.uiSettings
        })
      }
    ),
    {
      name: 'settings-store'
    }
  )
)

// セレクター
export const useSettingsSelectors = () => {
  const store = useSettingsStore()
  
  return {
    riskSettings: store.riskSettings,
    tradingSettings: store.tradingSettings,
    uiSettings: store.uiSettings,
    isLoading: store.isLoading,
    error: store.error,
    lastSaved: store.lastSaved,
    isDirty: store.isDirty,
    
    // 計算されたプロパティ
    isHighRisk: store.riskSettings.maxRiskPerTrade > 10,
    isTradingActive: store.tradingSettings.enableAutoTrading,
    isDarkMode: store.uiSettings.theme === 'dark',
    
    // 設定の組み合わせ
    combinedSettings: {
      risk: store.riskSettings,
      trading: store.tradingSettings
    } as Settings
  }
}

// アクションフック
export const useSettingsActions = () => {
  const store = useSettingsStore()
  
  return {
    updateRiskSettings: store.updateRiskSettings,
    updateTradingSettings: store.updateTradingSettings,
    updateUISettings: store.updateUISettings,
    setSettings: store.setSettings,
    resetSettings: store.resetSettings,
    resetRiskSettings: store.resetRiskSettings,
    resetTradingSettings: store.resetTradingSettings,
    setLoading: store.setLoading,
    setError: store.setError,
    setSaved: store.setSaved,
    setDirty: store.setDirty,
    validateRiskSettings: store.validateRiskSettings,
    validateTradingSettings: store.validateTradingSettings,
    exportSettings: store.exportSettings,
    importSettings: store.importSettings
  }
}