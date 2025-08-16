/**
 * 包括的バックテスト結果表示コンポーネント
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
  Alert,
  Tab,
  Tabs,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material'
import {
  ExpandMore,
  TrendingUp,
  TrendingDown,
  Analytics,
  Assessment,
  Timeline,
  CheckCircle,
  Warning
} from '@mui/icons-material'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ScatterChart,
  Scatter,
  Cell,
  PieChart,
  Pie
} from 'recharts'
import { ComprehensiveBacktestResponse } from '@/types/backtest'
import { 
  formatCurrency, 
  formatPercentage,
  formatNumber,
  formatDateTime 
} from '@/lib/utils'

interface ComprehensiveBacktestResultsProps {
  result: ComprehensiveBacktestResponse
  onClose?: () => void
}

export function ComprehensiveBacktestResults({ result, onClose }: ComprehensiveBacktestResultsProps) {
  const [activeTab, setActiveTab] = useState(0)

  console.log('ComprehensiveBacktestResults received:', {
    hasResult: !!result,
    resultKeys: result ? Object.keys(result) : [],
    fullResult: result
  })

  // 個別結果をテーブル形式に変換（snake_caseからcamelCaseへ変換）
  const individualResults = result?.individual_results || result?.individualResults || {}
  
  console.log('Individual results:', {
    hasIndividualResults: !!individualResults,
    individualResultsKeys: Object.keys(individualResults)
  })
  
  const flattenedResults = Object.entries(individualResults).flatMap(([symbol, timeframes]) =>
    Object.entries(timeframes || {}).map(([timeframe, data]: [string, any]) => ({
      symbol,
      timeframe,
      ...data,
      bestScore: data?.best_score || data?.bestScore,
      totalIterations: data?.total_iterations || data?.totalIterations,
      validResults: data?.valid_results || data?.validResults
    }))
  )

  // パフォーマンスサマリーデータ
  const performanceData = flattenedResults.map(result => ({
    name: `${result.symbol}-${result.timeframe}`,
    score: result.bestScore || 0,
    symbol: result.symbol,
    timeframe: result.timeframe
  }))

  // 通貨ペア別集計
  const symbolData = Object.keys(individualResults).map(symbol => {
    const symbolResults = flattenedResults.filter(r => r.symbol === symbol)
    const avgScore = symbolResults.reduce((sum, r) => sum + (r.bestScore || 0), 0) / symbolResults.length
    return {
      symbol,
      avgScore,
      count: symbolResults.length
    }
  })

  // 時間軸別集計
  const timeframeData = ['M15', 'M30', 'H1', 'H4'].map(timeframe => {
    const timeframeResults = flattenedResults.filter(r => r.timeframe === timeframe)
    const avgScore = timeframeResults.reduce((sum, r) => sum + (r.bestScore || 0), 0) / timeframeResults.length
    return {
      timeframe,
      avgScore,
      count: timeframeResults.length
    }
  })

  // カラーパレット
  const colors = ['#1976d2', '#dc004e', '#388e3c', '#f57c00', '#7b1fa2', '#616161', '#0288d1', '#d32f2f']

  return (
    <Box>
      {/* ヘッダー */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title={
            <Box display="flex" alignItems="center" gap={2}>
              <Typography variant="h5" fontWeight={600}>
                包括的バックテスト結果
              </Typography>
              <Chip
                label={`${Object.keys(individualResults).length}通貨ペア × ${Object.keys(Object.values(individualResults)[0] || {}).length}時間軸`}
                color="primary"
                variant="outlined"
              />
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
                {formatDateTime(result.test_period?.start_date || result.testPeriod?.start_date, 'yyyy/MM/dd')} - {formatDateTime(result.test_period?.end_date || result.testPeriod?.end_date, 'yyyy/MM/dd')}
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                総組み合わせ数
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {flattenedResults.length}組み合わせ
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                最適化指標
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {result.optimization_settings?.metric || result.optimizationSettings?.metric || 'N/A'}
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                平均スコア
              </Typography>
              <Typography variant="h6" fontWeight={600} color="primary.main">
                {formatNumber(performanceData.reduce((sum, d) => sum + d.score, 0) / performanceData.length || 0, 3)}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* タブ */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
            <Tab label="個別結果" />
            <Tab label="通貨ペア別分析" />
            <Tab label="時間軸別分析" />
            <Tab label="設定・推奨事項" />
          </Tabs>
        </Box>

        {/* 個別結果タブ */}
        {activeTab === 0 && (
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <Assessment sx={{ mr: 1, verticalAlign: 'middle' }} />
              全組み合わせ結果
            </Typography>
            
            <TableContainer component={Paper} sx={{ mb: 3 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>通貨ペア</TableCell>
                    <TableCell>時間軸</TableCell>
                    <TableCell align="right">最高スコア</TableCell>
                    <TableCell align="right">総イテレーション</TableCell>
                    <TableCell align="right">有効結果</TableCell>
                    <TableCell align="center">状態</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {flattenedResults.map((result, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <Chip label={result.symbol} size="small" variant="outlined" />
                      </TableCell>
                      <TableCell>
                        <Chip label={result.timeframe} size="small" />
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          color={result.bestScore && result.bestScore > 0 ? 'success.main' : 'text.secondary'}
                          fontWeight={600}
                        >
                          {result.bestScore ? formatNumber(result.bestScore, 3) : 'N/A'}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {result.totalIterations || 0}
                      </TableCell>
                      <TableCell align="right">
                        {result.validResults || 0}
                      </TableCell>
                      <TableCell align="center">
                        {result.validResults && result.validResults > 0 ? (
                          <CheckCircle color="success" fontSize="small" />
                        ) : (
                          <Warning color="warning" fontSize="small" />
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {/* パフォーマンス散布図 */}
            <Paper sx={{ p: 2, height: 400 }}>
              <Typography variant="subtitle1" gutterBottom>パフォーマンス散布図</Typography>
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip formatter={(value) => formatNumber(value as number, 3)} />
                  <Scatter dataKey="score" fill="#1976d2" />
                </ScatterChart>
              </ResponsiveContainer>
            </Paper>
          </CardContent>
        )}

        {/* 通貨ペア別分析タブ */}
        {activeTab === 1 && (
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <TrendingUp sx={{ mr: 1, verticalAlign: 'middle' }} />
              通貨ペア別パフォーマンス
            </Typography>
            
            <Grid container spacing={3}>
              {/* 通貨ペア別パフォーマンスチャート */}
              <Grid item xs={12} md={8}>
                <Paper sx={{ p: 2, height: 400 }}>
                  <Typography variant="subtitle1" gutterBottom>平均スコア比較</Typography>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={symbolData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="symbol" />
                      <YAxis />
                      <Tooltip formatter={(value) => formatNumber(value as number, 3)} />
                      <Bar dataKey="avgScore" fill="#1976d2" />
                    </BarChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>

              {/* 通貨ペア別統計 */}
              <Grid item xs={12} md={4}>
                <Paper sx={{ p: 2, height: 400 }}>
                  <Typography variant="subtitle1" gutterBottom>通貨ペア別統計</Typography>
                  <List dense>
                    {symbolData.map((data, index) => (
                      <ListItem key={data.symbol}>
                        <ListItemIcon>
                          <Box
                            sx={{
                              width: 16,
                              height: 16,
                              backgroundColor: colors[index % colors.length],
                              borderRadius: '50%'
                            }}
                          />
                        </ListItemIcon>
                        <ListItemText
                          primary={data.symbol}
                          secondary={`平均スコア: ${formatNumber(data.avgScore, 3)}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Grid>
            </Grid>
          </CardContent>
        )}

        {/* 時間軸別分析タブ */}
        {activeTab === 2 && (
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <Timeline sx={{ mr: 1, verticalAlign: 'middle' }} />
              時間軸別パフォーマンス
            </Typography>
            
            <Grid container spacing={3}>
              {/* 時間軸別パフォーマンスチャート */}
              <Grid item xs={12} md={8}>
                <Paper sx={{ p: 2, height: 400 }}>
                  <Typography variant="subtitle1" gutterBottom>時間軸別平均スコア</Typography>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={timeframeData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="timeframe" />
                      <YAxis />
                      <Tooltip formatter={(value) => formatNumber(value as number, 3)} />
                      <Bar dataKey="avgScore" fill="#4caf50" />
                    </BarChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>

              {/* 時間軸別統計 */}
              <Grid item xs={12} md={4}>
                <Paper sx={{ p: 2, height: 400 }}>
                  <Typography variant="subtitle1" gutterBottom>時間軸別統計</Typography>
                  <List dense>
                    {timeframeData.map((data, index) => (
                      <ListItem key={data.timeframe}>
                        <ListItemIcon>
                          <Box
                            sx={{
                              width: 16,
                              height: 16,
                              backgroundColor: colors[index % colors.length],
                              borderRadius: '50%'
                            }}
                          />
                        </ListItemIcon>
                        <ListItemText
                          primary={data.timeframe}
                          secondary={`平均スコア: ${formatNumber(data.avgScore, 3)}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Grid>
            </Grid>
          </CardContent>
        )}

        {/* 設定・推奨事項タブ */}
        {activeTab === 3 && (
          <CardContent>
            <Typography variant="h6" gutterBottom>
              設定と推奨事項
            </Typography>
            
            <Grid container spacing={3}>
              {/* 最適化設定 */}
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    最適化設定
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        最適化指標
                      </Typography>
                      <Typography variant="body1">
                        {result.optimization_settings?.metric || result.optimizationSettings?.metric || 'N/A'}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        テスト期間
                      </Typography>
                      <Typography variant="body1">
                        {result.test_period?.months || result.testPeriod?.months || 12}ヶ月
                      </Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="caption" color="text.secondary">
                        対象通貨ペア
                      </Typography>
                      <Box mt={1}>
                        {(result.optimization_settings?.symbols || result.optimizationSettings?.symbols)?.map(symbol => (
                          <Chip key={symbol} label={symbol} size="small" sx={{ mr: 1, mb: 1 }} />
                        ))}
                      </Box>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="caption" color="text.secondary">
                        対象時間軸
                      </Typography>
                      <Box mt={1}>
                        {(result.optimization_settings?.timeframes || result.optimizationSettings?.timeframes)?.map(tf => (
                          <Chip key={tf} label={tf} size="small" sx={{ mr: 1, mb: 1 }} />
                        ))}
                      </Box>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>

              {/* 推奨事項 */}
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    推奨事項
                  </Typography>
                  <List dense>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="info" /></ListItemIcon>
                      <ListItemText primary="最もパフォーマンスの良い組み合わせを詳細検証" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="info" /></ListItemIcon>
                      <ListItemText primary="低パフォーマンス組み合わせの原因分析" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="info" /></ListItemIcon>
                      <ListItemText primary="異なる市場条件での追加検証" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="info" /></ListItemIcon>
                      <ListItemText primary="リスク管理パラメータの最適化" />
                    </ListItem>
                  </List>
                </Paper>
              </Grid>

              {/* サマリー統計 */}
              <Grid item xs={12}>
                <Alert severity="info">
                  <Typography variant="body2">
                    <strong>分析完了:</strong> {flattenedResults.length}組み合わせの包括的分析が完了しました。
                    上位パフォーマンスの組み合わせについて、より詳細なバックテストを実行することを推奨します。
                  </Typography>
                </Alert>
              </Grid>
            </Grid>
          </CardContent>
        )}
      </Card>
    </Box>
  )
}

export default ComprehensiveBacktestResults