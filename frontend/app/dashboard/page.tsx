/**
 * ダッシュボードページ
 */
'use client'

import React from 'react'
import {
  Box,
  Grid,
  Typography,
  Paper,
  Container
} from '@mui/material'
import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import TradingPanel from '@/components/trading/TradingPanel'
import PositionsList from '@/components/trading/PositionsList'
import { useUISelectors } from '@/store/ui'
import { useTradingSelectors } from '@/store/trading'
import { useTrades, usePositions } from '@/hooks/useTrades'
import { formatCurrency, formatPercentage } from '@/lib/utils'
import { SIDEBAR_WIDTH, HEADER_HEIGHT } from '@/lib/constants'

export default function DashboardPage() {
  const { sidebarOpen, sidebarCollapsed } = useUISelectors()
  const { 
    isActive, 
    totalProfit, 
    totalPositions, 
    tradingStatus 
  } = useTradingSelectors()
  
  const { data: trades, isLoading: tradesLoading } = useTrades({ limit: 20 })
  const { data: positions, isLoading: positionsLoading } = usePositions()

  const sidebarWidth = sidebarOpen ? (sidebarCollapsed ? 64 : SIDEBAR_WIDTH) : 0

  // 統計データの計算
  const todaysTrades = trades?.filter(trade => {
    const today = new Date()
    const tradeDate = new Date(trade.entryTime)
    return tradeDate.toDateString() === today.toDateString()
  }) || []

  const todaysProfit = todaysTrades.reduce((sum, trade) => 
    sum + (trade.profitLoss || 0), 0
  )

  const winningTrades = todaysTrades.filter(trade => 
    trade.profitLoss && trade.profitLoss > 0
  ).length

  const todaysWinRate = todaysTrades.length > 0 
    ? (winningTrades / todaysTrades.length) * 100 
    : 0

  return (
    <Box sx={{ display: 'flex' }}>
      {/* サイドバー */}
      <Sidebar />
      
      {/* メインコンテンツ */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: `calc(100% - ${sidebarWidth}px)`,
          ml: `${sidebarWidth}px`,
          transition: theme => theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen
          })
        }}
      >
        {/* ヘッダー */}
        <Header />
        
        {/* ページコンテンツ */}
        <Container 
          maxWidth={false} 
          sx={{ 
            mt: `${HEADER_HEIGHT + 16}px`, 
            mb: 3,
            px: 3
          }}
        >
          {/* ページタイトル */}
          <Box mb={3}>
            <Typography variant="h4" fontWeight={600} gutterBottom>
              ダッシュボード
            </Typography>
            <Typography variant="body1" color="text.secondary">
              取引状況とポートフォリオの概要
            </Typography>
          </Box>

          <Grid container spacing={3}>
            {/* サマリーカード */}
            <Grid item xs={12}>
              <Grid container spacing={2}>
                {/* 取引状態 */}
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h6" color="primary" gutterBottom>
                      取引状態
                    </Typography>
                    <Typography variant="h4" fontWeight={600}>
                      {isActive ? '稼働中' : '停止中'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {isActive ? '自動取引実行中' : '待機中'}
                    </Typography>
                  </Paper>
                </Grid>

                {/* 保有ポジション */}
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h6" color="primary" gutterBottom>
                      保有ポジション
                    </Typography>
                    <Typography variant="h4" fontWeight={600}>
                      {totalPositions}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      件
                    </Typography>
                  </Paper>
                </Grid>

                {/* 評価損益 */}
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h6" color="primary" gutterBottom>
                      評価損益
                    </Typography>
                    <Typography 
                      variant="h4" 
                      fontWeight={600}
                      color={totalProfit >= 0 ? 'success.main' : 'error.main'}
                    >
                      {formatCurrency(totalProfit)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      未実現損益
                    </Typography>
                  </Paper>
                </Grid>

                {/* 本日の損益 */}
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h6" color="primary" gutterBottom>
                      本日の損益
                    </Typography>
                    <Typography 
                      variant="h4" 
                      fontWeight={600}
                      color={todaysProfit >= 0 ? 'success.main' : 'error.main'}
                    >
                      {formatCurrency(todaysProfit)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      勝率: {formatPercentage(todaysWinRate)}
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>
            </Grid>

            {/* 取引制御パネル */}
            <Grid item xs={12} md={4}>
              <TradingPanel />
            </Grid>

            {/* アカウント情報 */}
            <Grid item xs={12} md={8}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  アカウント情報
                </Typography>
                
                {tradingStatus ? (
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          口座残高
                        </Typography>
                        <Typography variant="h5" fontWeight={600}>
                          {formatCurrency(tradingStatus.accountBalance || 0)}
                        </Typography>
                      </Box>
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          有効証拠金
                        </Typography>
                        <Typography variant="h5" fontWeight={600}>
                          {formatCurrency(tradingStatus.equity || 0)}
                        </Typography>
                      </Box>
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          余剰証拠金
                        </Typography>
                        <Typography variant="h5" fontWeight={600}>
                          {formatCurrency(tradingStatus.freeMargin || 0)}
                        </Typography>
                      </Box>
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          証拠金維持率
                        </Typography>
                        <Typography 
                          variant="h5" 
                          fontWeight={600}
                          color={
                            !tradingStatus.marginLevel ? 'text.primary' :
                            tradingStatus.marginLevel > 200 ? 'success.main' :
                            tradingStatus.marginLevel > 100 ? 'warning.main' : 'error.main'
                          }
                        >
                          {tradingStatus.marginLevel ? formatPercentage(tradingStatus.marginLevel) : 'N/A'}
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                ) : (
                  <Typography color="text.secondary">
                    取引状態を取得中...
                  </Typography>
                )}
              </Paper>
            </Grid>

            {/* ポジション一覧 */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  保有ポジション
                </Typography>
                <PositionsList 
                  positions={positions}
                  loading={positionsLoading}
                />
              </Paper>
            </Grid>

            {/* 最近の取引 */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  最近の取引履歴
                </Typography>
                
                {tradesLoading ? (
                  <Typography color="text.secondary">
                    取引履歴を読み込み中...
                  </Typography>
                ) : trades && trades.length > 0 ? (
                  <Box>
                    {/* 簡易的な取引リスト */}
                    {trades.slice(0, 5).map((trade) => (
                      <Box 
                        key={trade.id}
                        display="flex" 
                        justifyContent="space-between" 
                        alignItems="center"
                        py={1}
                        borderBottom="1px solid"
                        borderColor="divider"
                      >
                        <Box>
                          <Typography variant="body2" fontWeight={600}>
                            {trade.symbol} {trade.orderType}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(trade.entryTime).toLocaleString('ja-JP')}
                          </Typography>
                        </Box>
                        <Box textAlign="right">
                          <Typography 
                            variant="body2" 
                            fontWeight={600}
                            color={
                              !trade.profitLoss ? 'text.primary' :
                              trade.profitLoss >= 0 ? 'success.main' : 'error.main'
                            }
                          >
                            {trade.profitLoss ? formatCurrency(trade.profitLoss) : '決済待ち'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {trade.volume}ロット
                          </Typography>
                        </Box>
                      </Box>
                    ))}
                  </Box>
                ) : (
                  <Typography color="text.secondary">
                    取引履歴がありません
                  </Typography>
                )}
              </Paper>
            </Grid>
          </Grid>
        </Container>
      </Box>
    </Box>
  )
}