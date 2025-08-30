/**
 * バックテスト進捗追跡フック
 */
import { useState, useEffect, useRef } from 'react'
import { BacktestProgress, backtestApi } from '@/lib/api'

interface UseBacktestProgressOptions {
  testId?: string
  pollingInterval?: number
  onComplete?: (progress: BacktestProgress) => void
  onError?: (error: Error) => void
}

export function useBacktestProgress({
  testId,
  pollingInterval = 1000, // 1秒間隔
  onComplete,
  onError
}: UseBacktestProgressOptions = {}) {
  const [progress, setProgress] = useState<BacktestProgress | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [startTime, setStartTime] = useState<Date | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const errorCountRef = useRef(0)
  const maxRetries = 3
  const maxPollingTimeMs = 120000 // 2 minutes

  const startPolling = (newTestId: string) => {
    console.log(`Starting progress polling for test ID: ${newTestId}`)
    setIsLoading(true)
    setError(null)
    setProgress(null)
    setStartTime(new Date())
    errorCountRef.current = 0

    // 既存のポーリングを停止
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }

    // 新しいポーリングを開始（1秒間隔で詳細な進捗表示）
    intervalRef.current = setInterval(async () => {
      // 時間制限チェック
      if (startTime && Date.now() - startTime.getTime() > maxPollingTimeMs) {
        console.warn('Progress polling timeout - stopping after 2 minutes')
        stopPolling()
        setError('Progress polling timed out')
        if (onError) {
          onError(new Error('Progress polling timed out'))
        }
        return
      }

      try {
        const progressData = await backtestApi.getProgress(newTestId)
        console.log('Progress update:', progressData)
        errorCountRef.current = 0 // Reset error count on success
        
        setProgress(progressData)
        setIsLoading(false)

        // バックテストが完了またはエラーの場合、ポーリングを停止
        if (progressData.status === 'completed' || progressData.status === 'error') {
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
          
          // 最小表示時間（5秒）を確保
          const minDisplayTime = 5000 // 5秒
          const elapsedTime = startTime ? Date.now() - startTime.getTime() : 0
          const remainingTime = Math.max(0, minDisplayTime - elapsedTime)
          
          setTimeout(() => {
            if (progressData.status === 'completed' && onComplete) {
              onComplete(progressData)
            } else if (progressData.status === 'error' && onError) {
              onError(new Error(progressData.current_step))
            }
          }, remainingTime)
        }
      } catch (err: any) {
        errorCountRef.current++
        
        // 404エラーの場合は、まだテストが開始されていない可能性があるため継続
        if (err?.response?.status === 404) {
          if (errorCountRef.current <= maxRetries) {
            console.log(`Backtest progress not found (404) - attempt ${errorCountRef.current}/${maxRetries}:`, newTestId)
            return
          } else {
            console.warn(`Backtest progress not found after ${maxRetries} attempts - stopping polling for:`, newTestId)
          }
        }
        
        // タイムアウトエラーの場合は、短時間継続してからリトライ
        if (err?.code === 'ECONNABORTED' || err?.message?.includes('timeout')) {
          if (errorCountRef.current <= maxRetries) {
            console.log(`Progress polling timeout - attempt ${errorCountRef.current}/${maxRetries}:`, newTestId)
            return // エラーカウントはインクリメントするが、継続
          } else {
            console.warn(`Progress polling timeout after ${maxRetries} attempts - stopping polling for:`, newTestId)
          }
        }
        
        console.error('Progress polling error:', err)
        
        // 最大試行回数に達した場合、ポーリングを停止
        const errorMessage = err instanceof Error ? err.message : 'Progress fetch failed'
        setError(errorMessage)
        setIsLoading(false)
        
        if (onError) {
          onError(err instanceof Error ? err : new Error(errorMessage))
        }
        
        // エラーが発生した場合もポーリングを停止
        stopPolling()
      }
    }, 1000) // 1秒間隔で詳細な進捗チェック
  }

  const stopPolling = () => {
    console.log('Stopping progress polling')
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setIsLoading(false)
  }

  // testIdが変更された時の処理
  useEffect(() => {
    if (testId) {
      startPolling(testId)
    } else {
      stopPolling()
    }

    // クリーンアップ
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [testId, pollingInterval])

  return {
    progress,
    isLoading,
    error,
    startPolling,
    stopPolling,
    isPolling: intervalRef.current !== null
  }
}