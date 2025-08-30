/**
 * バックテスト進捗ダイアログコンポーネント
 */
'use client'

import React from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Loader2, CheckCircle, XCircle, Activity } from 'lucide-react'
import { BacktestProgress } from '@/lib/api'

interface BacktestProgressDialogProps {
  isOpen: boolean
  onClose: () => void
  progress: BacktestProgress | null
  isLoading: boolean
  error: string | null
}

export function BacktestProgressDialog({
  isOpen,
  onClose,
  progress,
  isLoading,
  error
}: BacktestProgressDialogProps) {
  const getStatusIcon = () => {
    if (error) return <XCircle className="h-5 w-5 text-red-500" />
    if (progress?.status === 'completed') return <CheckCircle className="h-5 w-5 text-green-500" />
    if (progress?.status === 'error') return <XCircle className="h-5 w-5 text-red-500" />
    if (isLoading || progress?.status === 'running') return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
    return <Activity className="h-5 w-5 text-gray-500" />
  }

  const getStatusBadge = () => {
    if (error) return <Badge variant="destructive">エラー</Badge>
    if (progress?.status === 'completed') return <Badge variant="success">完了</Badge>
    if (progress?.status === 'error') return <Badge variant="destructive">エラー</Badge>
    if (progress?.status === 'running') return <Badge variant="default">実行中</Badge>
    return <Badge variant="secondary">待機中</Badge>
  }

  const formatTime = (timestamp?: string) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    return date.toLocaleTimeString('ja-JP', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    })
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {getStatusIcon()}
            バックテスト進捗
            {getStatusBadge()}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* 基本情報 */}
          <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm text-gray-600">テストID</p>
              <p className="font-mono text-sm">{progress?.test_id || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">開始時刻</p>
              <p className="text-sm">{formatTime(progress?.start_time) || 'N/A'}</p>
            </div>
          </div>

          {/* 進捗バー */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">
                進捗: {progress?.progress_percent?.toFixed(1) || 0}%
              </span>
              <span className="text-sm text-gray-600">
                {progress?.completed_configurations || 0} / {progress?.total_configurations || 0} 設定
              </span>
            </div>
            <Progress 
              value={progress?.progress_percent || 0} 
              className="w-full"
            />
          </div>

          {/* 現在の状態 */}
          <div className="p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-4 w-4 text-blue-500" />
              <span className="font-medium text-blue-900">現在の処理</span>
            </div>
            <p className="text-sm text-blue-800">
              {progress?.current_step || 'バックテスト準備中...'}
            </p>
            {progress?.current_symbol && progress?.current_timeframe && (
              <div className="flex gap-2 mt-2">
                <Badge variant="outline">{progress.current_symbol}</Badge>
                <Badge variant="outline">{progress.current_timeframe}</Badge>
              </div>
            )}
          </div>

          {/* ログ */}
          {progress?.logs && progress.logs.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium">実行ログ</h4>
              <ScrollArea className="h-32 w-full border rounded-md p-3">
                <div className="space-y-1">
                  {progress.logs.map((log, index) => (
                    <div key={index} className="text-xs font-mono text-gray-600">
                      {log}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}

          {/* エラーメッセージ */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="h-4 w-4 text-red-500" />
                <span className="font-medium text-red-900">エラー</span>
              </div>
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* 完了メッセージ */}
          {progress?.status === 'completed' && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span className="font-medium text-green-900">バックテスト完了</span>
              </div>
              <p className="text-sm text-green-800 mt-1">
                すべての設定でバックテストが正常に完了しました。
              </p>
              <div className="mt-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                >
                  結果を確認する
                </button>
              </div>
            </div>
          )}

          {/* 実行中メッセージ */}
          {progress?.status === 'running' && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                  <span className="font-medium text-blue-900">実行中...</span>
                </div>
                <button
                  onClick={onClose}
                  className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                >
                  バックグラウンドで実行
                </button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}