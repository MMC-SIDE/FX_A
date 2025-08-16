/**
 * バックテスト結果表示コンポーネント
 */
'use client'

import React, { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  Grid,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Menu,
  MenuItem,
  Button,
  Alert,
  Tab,
  Tabs,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material'
import {
  MoreVert,
  Download,
  Compare,
  Delete,
  ExpandMore,
  TrendingUp,
  TrendingDown,
  Info,
  Warning
} from '@mui/icons-material'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import { useBacktestResult, useDeleteBacktestResults, useExportBacktestResult } from '@/hooks/useBacktest'
import { BacktestResult } from '@/types/backtest'
import { 
  formatCurrency, 
  formatPercentage, 
  formatDateTime, 
  formatNumber,
  getProfitColor 
} from '@/lib/utils'
import { TableLoading } from '@/components/ui/Loading'

interface BacktestResultsProps {
  testId: string
  onCompare?: (testId: string) => void
  onDelete?: (testId: string) => void
}

export function BacktestResults({ testId, onCompare, onDelete }: BacktestResultsProps) {
  const { data: result, isLoading, error } = useBacktestResult(testId)
  const deleteBacktest = useDeleteBacktestResults()
  const exportBacktest = useExportBacktestResult()
  
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [activeTab, setActiveTab] = useState(0)

  if (isLoading) {
    return <TableLoading rows={10} columns={6} />
  }

  if (error) {
    return (
      <Alert severity="error">
        バックテスト結果の取得に失敗しました: {error.message}
      </Alert>
    )
  }

  if (!result) {
    return (
      <Alert severity="info">
        バックテスト結果が見つかりません
      </Alert>
    )
  }

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const handleExport = async (format: 'JSON' | 'CSV' | 'EXCEL') => {
    try {
      await exportBacktest.mutateAsync({
        testId,
        format,
        filename: `backtest_${result.symbol}_${result.timeframe}_${testId}`
      })
    } catch (error) {
      console.error('Export failed:', error)
    }
    handleMenuClose()
  }

  const handleDelete = async () => {
    try {
      await deleteBacktest.mutateAsync([testId])
      onDelete?.(testId)
    } catch (error) {
      console.error('Delete failed:', error)
    }
    handleMenuClose()
  }

  const { statistics } = result

  // パフォーマンス指標のカラー決定
  const getPerformanceColor = (value: number, type: 'profit' | 'drawdown' | 'ratio') => {
    switch (type) {
      case 'profit':
        return value >= 0 ? 'success.main' : 'error.main'
      case 'drawdown':
        return value <= 10 ? 'success.main' : value <= 20 ? 'warning.main' : 'error.main'
      case 'ratio':
        return value >= 1.5 ? 'success.main' : value >= 1.0 ? 'warning.main' : 'error.main'
      default:
        return 'text.primary'
    }
  }

  // エクイティカーブデータ
  const equityData = result.equityCurve?.map((point, index) => ({
    time: new Date(point.timestamp).toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' }),
    equity: point.equity,
    balance: point.balance,
    drawdown: 0 // 計算要実装
  })) || []

  // 月別パフォーマンスデータ
  const monthlyData = result.trades?.reduce((acc, trade) => {
    const month = new Date(trade.entryTime).toLocaleDateString('ja-JP', { year: 'numeric', month: 'short' })
    if (!acc[month]) {
      acc[month] = { month, profit: 0, trades: 0 }
    }
    acc[month].profit += trade.profitLoss || 0
    acc[month].trades += 1
    return acc
  }, {} as Record<string, { month: string; profit: number; trades: number }>) || {}

  const monthlyChartData = Object.values(monthlyData)

  // 取引分布データ
  const profitDistribution = [
    { name: '利益取引', value: statistics.winningTrades, color: '#4caf50' },
    { name: '損失取引', value: statistics.losingTrades, color: '#f44336' }
  ]

  return (
    <Box>
      {/* ヘッダー */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title={
            <Box display="flex" alignItems="center" gap={2}>
              <Typography variant="h5" fontWeight={600}>
                バックテスト結果
              </Typography>
              <Chip
                label={`${result.symbol} ${result.timeframe}`}
                color="primary"
                variant="outlined"
              />
            </Box>
          }
          action={
            <Box display="flex" alignItems="center" gap={1}>
              <Button
                variant="outlined"
                size="small"
                onClick={() => onCompare?.(testId)}
                startIcon={<Compare />}
              >
                比較
              </Button>
              <IconButton onClick={handleMenuClick}>
                <MoreVert />
              </IconButton>
            </Box>
          }
        />
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                テスト期間
              </Typography>
              <Typography variant="body2">
                {formatDateTime(result.period.startDate, 'yyyy/MM/dd')} - {formatDateTime(result.period.endDate, 'yyyy/MM/dd')}
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                総取引数
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {statistics.totalTrades}回
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                純利益
              </Typography>
              <Typography 
                variant="h6" 
                fontWeight={600}
                color={getPerformanceColor(statistics.netProfit, 'profit')}
              >
                {formatCurrency(statistics.netProfit)}
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                勝率
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {formatPercentage(statistics.winRate)}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* タブ */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
            <Tab label="サマリー" />
            <Tab label="チャート" />
            <Tab label="取引詳細" />
            <Tab label="統計" />
          </Tabs>
        </Box>

        {/* サマリータブ */}
        {activeTab === 0 && (
          <CardContent>
            <Grid container spacing={3}>
              {/* 主要指標 */}
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>主要パフォーマンス指標</Typography>
                <Paper sx={{ p: 2 }}>
                  <Grid container spacing={2}>
                    {[
                      { label: '総利益', value: formatCurrency(statistics.totalProfit), color: 'success.main' },
                      { label: '総損失', value: formatCurrency(statistics.totalLoss), color: 'error.main' },
                      { label: 'プロフィットファクター', value: formatNumber(statistics.profitFactor, 2), color: getPerformanceColor(statistics.profitFactor, 'ratio') },
                      { label: '最大ドローダウン', value: formatPercentage(statistics.maxDrawdownPercent), color: getPerformanceColor(statistics.maxDrawdownPercent, 'drawdown') },
                      { label: 'シャープレシオ', value: formatNumber(statistics.sharpeRatio, 2), color: getPerformanceColor(statistics.sharpeRatio, 'ratio') },
                      { label: 'リターン率', value: formatPercentage(statistics.returnPercent), color: getPerformanceColor(statistics.returnPercent, 'profit') }
                    ].map((metric, index) => (
                      <Grid item xs={6} key={index}>
                        <Typography variant="caption" color="text.secondary">
                          {metric.label}
                        </Typography>
                        <Typography variant="h6" fontWeight={600} color={metric.color}>
                          {metric.value}
                        </Typography>
                      </Grid>
                    ))}
                  </Grid>
                </Paper>
              </Grid>

              {/* 取引統計 */}
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>取引統計</Typography>
                <Paper sx={{ p: 2 }}>
                  <Grid container spacing={2}>
                    {[
                      { label: '勝利取引', value: `${statistics.winningTrades}回`, color: 'success.main' },
                      { label: '敗北取引', value: `${statistics.losingTrades}回`, color: 'error.main' },
                      { label: '平均利益', value: formatCurrency(statistics.avgWin), color: 'success.main' },
                      { label: '平均損失', value: formatCurrency(statistics.avgLoss), color: 'error.main' },
                      { label: '最大利益', value: formatCurrency(statistics.largestWin), color: 'success.main' },
                      { label: '最大損失', value: formatCurrency(statistics.largestLoss), color: 'error.main' }
                    ].map((metric, index) => (
                      <Grid item xs={6} key={index}>
                        <Typography variant="caption" color="text.secondary">
                          {metric.label}
                        </Typography>
                        <Typography variant="h6" fontWeight={600} color={metric.color}>
                          {metric.value}
                        </Typography>
                      </Grid>
                    ))}
                  </Grid>
                </Paper>
              </Grid>

              {/* 勝敗分布 */}
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>勝敗分布</Typography>
                <Paper sx={{ p: 2, height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={profitDistribution}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {profitDistribution.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>

              {/* 月別パフォーマンス */}
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>月別パフォーマンス</Typography>
                <Paper sx={{ p: 2, height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={monthlyChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis />
                      <Tooltip formatter={(value) => formatCurrency(value as number)} />
                      <Bar dataKey="profit" fill="#1976d2" />
                    </BarChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>
            </Grid>
          </CardContent>
        )}

        {/* チャートタブ */}
        {activeTab === 1 && (
          <CardContent>
            <Typography variant="h6" gutterBottom>エクイティカーブ</Typography>
            <Paper sx={{ p: 2, height: 400 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={equityData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip formatter={(value) => formatCurrency(value as number)} />
                  <Legend />
                  <Line type="monotone" dataKey="equity" stroke="#1976d2" name="エクイティ" strokeWidth={2} />
                  <Line type="monotone" dataKey="balance" stroke="#4caf50" name="残高" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </Paper>
          </CardContent>
        )}

        {/* 取引詳細タブ */}
        {activeTab === 2 && (
          <CardContent>
            <Typography variant="h6" gutterBottom>
              取引履歴 ({result.trades?.length || 0}件)
            </Typography>
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>エントリー時刻</TableCell>
                    <TableCell>イグジット時刻</TableCell>
                    <TableCell align="center">タイプ</TableCell>
                    <TableCell align="right">ロット</TableCell>
                    <TableCell align="right">エントリー価格</TableCell>
                    <TableCell align="right">イグジット価格</TableCell>
                    <TableCell align="right">損益</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {result.trades?.slice(0, 100).map((trade, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        {formatDateTime(trade.entryTime, 'MM/dd HH:mm')}
                      </TableCell>
                      <TableCell>
                        {trade.exitTime ? formatDateTime(trade.exitTime, 'MM/dd HH:mm') : '-'}
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={trade.orderType}
                          color={trade.orderType === 'BUY' ? 'success' : 'error'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="right">
                        {formatNumber(trade.volume, 2)}
                      </TableCell>
                      <TableCell align="right">
                        {formatNumber(trade.entryPrice, 3)}
                      </TableCell>
                      <TableCell align="right">
                        {trade.exitPrice ? formatNumber(trade.exitPrice, 3) : '-'}
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          color={getProfitColor(trade.profitLoss || 0)}
                          fontWeight={600}
                        >
                          {formatCurrency(trade.profitLoss || 0)}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        )}

        {/* 統計タブ */}
        {activeTab === 3 && (
          <CardContent>
            <Typography variant="h6" gutterBottom>詳細統計</Typography>
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography>リスク指標</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="text.secondary">最大ドローダウン</Typography>
                    <Typography variant="h6">{formatPercentage(statistics.maxDrawdownPercent)}</Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="text.secondary">シャープレシオ</Typography>
                    <Typography variant="h6">{formatNumber(statistics.sharpeRatio, 2)}</Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="text.secondary">ソルティノレシオ</Typography>
                    <Typography variant="h6">{formatNumber(statistics.sortinoRatio, 2)}</Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="text.secondary">カルマーレシオ</Typography>
                    <Typography variant="h6">{formatNumber(statistics.calmarRatio, 2)}</Typography>
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>
          </CardContent>
        )}
      </Card>

      {/* アクションメニュー */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => handleExport('JSON')}>
          <Download sx={{ mr: 1 }} />
          JSON形式でエクスポート
        </MenuItem>
        <MenuItem onClick={() => handleExport('CSV')}>
          <Download sx={{ mr: 1 }} />
          CSV形式でエクスポート
        </MenuItem>
        <MenuItem onClick={() => handleExport('EXCEL')}>
          <Download sx={{ mr: 1 }} />
          Excel形式でエクスポート
        </MenuItem>
        <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
          <Delete sx={{ mr: 1 }} />
          削除
        </MenuItem>
      </Menu>
    </Box>
  )
}

export default BacktestResults