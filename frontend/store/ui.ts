/**
 * UI関連のZustandストア
 */
import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  duration?: number
  persistent?: boolean
  timestamp: Date
}

interface Modal {
  id: string
  component: string
  props?: Record<string, any>
  onClose?: () => void
}

interface UIState {
  // サイドバー
  sidebarOpen: boolean
  sidebarCollapsed: boolean
  
  // モーダル
  modals: Modal[]
  
  // 通知
  notifications: Notification[]
  
  // ローディング
  globalLoading: boolean
  loadingMessage: string
  
  // テーマ
  theme: 'light' | 'dark' | 'system'
  
  // チャート設定
  chartSettings: {
    type: 'candlestick' | 'line' | 'area'
    indicators: string[]
    timeframe: string
    autoScale: boolean
    showVolume: boolean
    showGrid: boolean
  }
  
  // テーブル設定
  tableSettings: {
    density: 'comfortable' | 'standard' | 'compact'
    pageSize: number
    sortOrder: 'asc' | 'desc'
    sortField: string
  }
  
  // フィルター・検索
  filters: Record<string, any>
  searchQuery: string
  
  // ページ状態
  currentPage: string
  breadcrumbs: { label: string; path: string }[]
  
  // エラー状態
  error: string | null
  
  // Actions
  setSidebarOpen: (open: boolean) => void
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void
  toggleSidebarCollapsed: () => void
  
  addModal: (modal: Omit<Modal, 'id'>) => string
  removeModal: (id: string) => void
  removeAllModals: () => void
  
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => string
  removeNotification: (id: string) => void
  removeAllNotifications: () => void
  
  setGlobalLoading: (loading: boolean, message?: string) => void
  
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  
  updateChartSettings: (settings: Partial<UIState['chartSettings']>) => void
  resetChartSettings: () => void
  
  updateTableSettings: (settings: Partial<UIState['tableSettings']>) => void
  resetTableSettings: () => void
  
  setFilters: (filters: Record<string, any>) => void
  updateFilter: (key: string, value: any) => void
  removeFilter: (key: string) => void
  clearFilters: () => void
  
  setSearchQuery: (query: string) => void
  
  setCurrentPage: (page: string) => void
  setBreadcrumbs: (breadcrumbs: { label: string; path: string }[]) => void
  
  setError: (error: string | null) => void
  
  // ヘルパー関数
  showSuccess: (title: string, message: string) => void
  showError: (title: string, message: string) => void
  showWarning: (title: string, message: string) => void
  showInfo: (title: string, message: string) => void
  
  openConfirmDialog: (options: {
    title: string
    message: string
    onConfirm: () => void
    onCancel?: () => void
  }) => void
}

const defaultChartSettings = {
  type: 'candlestick' as const,
  indicators: [] as string[],
  timeframe: 'H1',
  autoScale: true,
  showVolume: true,
  showGrid: true
}

const defaultTableSettings = {
  density: 'standard' as const,
  pageSize: 20,
  sortOrder: 'desc' as const,
  sortField: 'timestamp'
}

const initialState = {
  sidebarOpen: true,
  sidebarCollapsed: false,
  modals: [],
  notifications: [],
  globalLoading: false,
  loadingMessage: '',
  theme: 'light' as const,
  chartSettings: defaultChartSettings,
  tableSettings: defaultTableSettings,
  filters: {},
  searchQuery: '',
  currentPage: '',
  breadcrumbs: [],
  error: null
}

export const useUIStore = create<UIState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,
        
        setSidebarOpen: (open) => 
          set({ sidebarOpen: open }, false, 'setSidebarOpen'),
        
        setSidebarCollapsed: (collapsed) => 
          set({ sidebarCollapsed: collapsed }, false, 'setSidebarCollapsed'),
        
        toggleSidebar: () => 
          set((state) => ({ sidebarOpen: !state.sidebarOpen }), false, 'toggleSidebar'),
        
        toggleSidebarCollapsed: () => 
          set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }), false, 'toggleSidebarCollapsed'),
        
        addModal: (modal) => {
          const id = `modal-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
          const newModal = { ...modal, id }
          
          set((state) => ({
            modals: [...state.modals, newModal]
          }), false, 'addModal')
          
          return id
        },
        
        removeModal: (id) => 
          set((state) => ({
            modals: state.modals.filter(modal => modal.id !== id)
          }), false, 'removeModal'),
        
        removeAllModals: () => 
          set({ modals: [] }, false, 'removeAllModals'),
        
        addNotification: (notification) => {
          const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
          const newNotification = {
            ...notification,
            id,
            timestamp: new Date()
          }
          
          set((state) => ({
            notifications: [...state.notifications, newNotification]
          }), false, 'addNotification')
          
          // 自動削除（persistentでない場合）
          if (!notification.persistent) {
            const duration = notification.duration || 5000
            setTimeout(() => {
              get().removeNotification(id)
            }, duration)
          }
          
          return id
        },
        
        removeNotification: (id) => 
          set((state) => ({
            notifications: state.notifications.filter(notif => notif.id !== id)
          }), false, 'removeNotification'),
        
        removeAllNotifications: () => 
          set({ notifications: [] }, false, 'removeAllNotifications'),
        
        setGlobalLoading: (loading, message = '') => 
          set({ globalLoading: loading, loadingMessage: message }, false, 'setGlobalLoading'),
        
        setTheme: (theme) => 
          set({ theme }, false, 'setTheme'),
        
        updateChartSettings: (settings) => 
          set((state) => ({
            chartSettings: { ...state.chartSettings, ...settings }
          }), false, 'updateChartSettings'),
        
        resetChartSettings: () => 
          set({ chartSettings: defaultChartSettings }, false, 'resetChartSettings'),
        
        updateTableSettings: (settings) => 
          set((state) => ({
            tableSettings: { ...state.tableSettings, ...settings }
          }), false, 'updateTableSettings'),
        
        resetTableSettings: () => 
          set({ tableSettings: defaultTableSettings }, false, 'resetTableSettings'),
        
        setFilters: (filters) => 
          set({ filters }, false, 'setFilters'),
        
        updateFilter: (key, value) => 
          set((state) => ({
            filters: { ...state.filters, [key]: value }
          }), false, 'updateFilter'),
        
        removeFilter: (key) => 
          set((state) => {
            const { [key]: removed, ...rest } = state.filters
            return { filters: rest }
          }, false, 'removeFilter'),
        
        clearFilters: () => 
          set({ filters: {} }, false, 'clearFilters'),
        
        setSearchQuery: (query) => 
          set({ searchQuery: query }, false, 'setSearchQuery'),
        
        setCurrentPage: (page) => 
          set({ currentPage: page }, false, 'setCurrentPage'),
        
        setBreadcrumbs: (breadcrumbs) => 
          set({ breadcrumbs }, false, 'setBreadcrumbs'),
        
        setError: (error) => 
          set({ error }, false, 'setError'),
        
        // ヘルパー関数
        showSuccess: (title, message) => {
          get().addNotification({
            type: 'success',
            title,
            message,
            duration: 4000
          })
        },
        
        showError: (title, message) => {
          get().addNotification({
            type: 'error',
            title,
            message,
            duration: 6000
          })
        },
        
        showWarning: (title, message) => {
          get().addNotification({
            type: 'warning',
            title,
            message,
            duration: 5000
          })
        },
        
        showInfo: (title, message) => {
          get().addNotification({
            type: 'info',
            title,
            message,
            duration: 4000
          })
        },
        
        openConfirmDialog: (options) => {
          get().addModal({
            component: 'ConfirmDialog',
            props: options
          })
        }
      }),
      {
        name: 'ui-store',
        partialize: (state) => ({
          sidebarCollapsed: state.sidebarCollapsed,
          theme: state.theme,
          chartSettings: state.chartSettings,
          tableSettings: state.tableSettings
        })
      }
    ),
    {
      name: 'ui-store'
    }
  )
)

// セレクター
export const useUISelectors = () => {
  const store = useUIStore()
  
  return {
    sidebarOpen: store.sidebarOpen,
    sidebarCollapsed: store.sidebarCollapsed,
    modals: store.modals,
    notifications: store.notifications,
    globalLoading: store.globalLoading,
    loadingMessage: store.loadingMessage,
    theme: store.theme,
    chartSettings: store.chartSettings,
    tableSettings: store.tableSettings,
    filters: store.filters,
    searchQuery: store.searchQuery,
    currentPage: store.currentPage,
    breadcrumbs: store.breadcrumbs,
    error: store.error,
    
    // 計算されたプロパティ
    hasModals: store.modals.length > 0,
    hasNotifications: store.notifications.length > 0,
    hasFilters: Object.keys(store.filters).length > 0,
    isDarkMode: store.theme === 'dark',
    isSystemTheme: store.theme === 'system'
  }
}

// アクションフック
export const useUIActions = () => {
  const store = useUIStore()
  
  return {
    setSidebarOpen: store.setSidebarOpen,
    setSidebarCollapsed: store.setSidebarCollapsed,
    toggleSidebar: store.toggleSidebar,
    toggleSidebarCollapsed: store.toggleSidebarCollapsed,
    addModal: store.addModal,
    removeModal: store.removeModal,
    removeAllModals: store.removeAllModals,
    addNotification: store.addNotification,
    removeNotification: store.removeNotification,
    removeAllNotifications: store.removeAllNotifications,
    setGlobalLoading: store.setGlobalLoading,
    setTheme: store.setTheme,
    updateChartSettings: store.updateChartSettings,
    resetChartSettings: store.resetChartSettings,
    updateTableSettings: store.updateTableSettings,
    resetTableSettings: store.resetTableSettings,
    setFilters: store.setFilters,
    updateFilter: store.updateFilter,
    removeFilter: store.removeFilter,
    clearFilters: store.clearFilters,
    setSearchQuery: store.setSearchQuery,
    setCurrentPage: store.setCurrentPage,
    setBreadcrumbs: store.setBreadcrumbs,
    setError: store.setError,
    showSuccess: store.showSuccess,
    showError: store.showError,
    showWarning: store.showWarning,
    showInfo: store.showInfo,
    openConfirmDialog: store.openConfirmDialog
  }
}

// 通知関連のヘルパーフック
export const useNotifications = () => {
  const { notifications } = useUISelectors()
  const { addNotification, removeNotification, removeAllNotifications, showSuccess, showError, showWarning, showInfo } = useUIActions()
  
  return {
    notifications,
    addNotification,
    removeNotification,
    removeAllNotifications,
    showSuccess,
    showError,
    showWarning,
    showInfo
  }
}

// モーダル関連のヘルパーフック
export const useModals = () => {
  const { modals } = useUISelectors()
  const { addModal, removeModal, removeAllModals, openConfirmDialog } = useUIActions()
  
  return {
    modals,
    addModal,
    removeModal,
    removeAllModals,
    openConfirmDialog
  }
}