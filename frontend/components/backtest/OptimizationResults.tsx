/**
 * パラメータ最適化結果表示コンポーネント
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
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material'
import {
  ExpandMore,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  Warning,
  Settings,
  Analytics,
  Timeline
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
  ScatterChart,
  Scatter
} from 'recharts'
import { OptimizationResult } from '@/types/backtest'
import { 
  formatNumber, 
  formatPercentage,
  formatDateTime 
} from '@/lib/utils'

interface OptimizationResultsProps {
  result: OptimizationResult
  onClose?: () => void
}

export function OptimizationResults({ result, onClose }: OptimizationResultsProps) {
  const [activeTab, setActiveTab] = useState(0)

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

  // 収束チャートデータ（模擬）
  const convergenceData = Array.from({ length: result.totalIterations || 10 }, (_, i) => ({
    iteration: i + 1,
    score: result.bestScore * (0.7 + Math.random() * 0.3 * (i + 1) / (result.totalIterations || 10))
  }))

  // パラメータ感度チャートデータ
  const sensitivityData = result.parameterSensitivity?.map(param => ({
    parameter: param.parameter,
    sensitivity: param.sensitivity * 100,
    impact: param.impact
  })) || []

  return (
    <Box>
      {/* ヘッダー */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title={
            <Box display="flex" alignItems="center" gap={2}>
              <Typography variant="h5" fontWeight={600}>
                パラメータ最適化結果
              </Typography>
              <Chip
                label={`${result.symbol} ${result.timeframe}`}
                color="primary"
                variant="outlined"
              />
              <Chip
                label={result.convergenceAnalysis?.converged ? '収束済み' : '未収束'}
                color={result.convergenceAnalysis?.converged ? 'success' : 'warning'}
                icon={result.convergenceAnalysis?.converged ? <CheckCircle /> : <Warning />}
              />
            </Box>
          }
        />
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                最適化期間
              </Typography>
              <Typography variant="body2">
                {formatDateTime(result.period?.start_date, 'yyyy/MM/dd')} - {formatDateTime(result.period?.end_date, 'yyyy/MM/dd')}
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                総イテレーション数
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {result.totalIterations || result.convergenceAnalysis?.iterations}回
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                最適化指標
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {result.optimizationMetric || result.optimization_metric}
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="caption" color="text.secondary">
                最高スコア
              </Typography>
              <Typography 
                variant="h6" 
                fontWeight={600}
                color="success.main"
              >
                {formatNumber(result.bestScore || result.best_score, 3)}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* タブ */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
            <Tab label="最適パラメータ" />
            <Tab label="収束分析" />
            <Tab label="パラメータ感度" />
            <Tab label="推奨事項" />
          </Tabs>
        </Box>

        {/* 最適パラメータタブ */}
        {activeTab === 0 && (
          <CardContent>
            <Grid container spacing={3}>
              {/* 最適パラメータ */}
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  <Settings sx={{ mr: 1, verticalAlign: 'middle' }} />
                  最適パラメータ
                </Typography>
                <Paper sx={{ p: 2 }}>
                  <Grid container spacing={2}>
                    {Object.entries(result.bestParameters || result.best_parameters || {}).map(([key, value]) => (
                      <Grid item xs={6} key={key}>
                        <Typography variant="caption" color="text.secondary">
                          {key}
                        </Typography>
                        <Typography variant="h6" fontWeight={600}>
                          {typeof value === 'number' ? formatNumber(value, 2) : String(value)}
                        </Typography>
                      </Grid>
                    ))}
                  </Grid>
                </Paper>
              </Grid>

              {/* パフォーマンス指標 */}
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  <Analytics sx={{ mr: 1, verticalAlign: 'middle' }} />
                  パフォーマンス指標
                </Typography>
                <Paper sx={{ p: 2 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        最高スコア
                      </Typography>
                      <Typography variant="h6" fontWeight={600} color="success.main">
                        {formatNumber(result.bestScore || result.best_score, 3)}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        改善率
                      </Typography>
                      <Typography variant="h6" fontWeight={600}>
                        {formatPercentage((result.convergenceAnalysis?.improvement_rate || 0) * 100)}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        有効結果数
                      </Typography>
                      <Typography variant="h6" fontWeight={600}>
                        {result.validResults || result.valid_results || 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        安定性スコア
                      </Typography>
                      <Typography variant="h6" fontWeight={600}>
                        {formatNumber((result.convergenceAnalysis?.stability_score || 0) * 100, 1)}%
                      </Typography>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>

              {/* 最適化方法 */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  最適化詳細
                </Typography>
                <Paper sx={{ p: 2 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={4}>
                      <Typography variant="caption" color="text.secondary">
                        最適化方法
                      </Typography>
                      <Typography variant="body1">
                        {result.optimizationMethod || result.optimization_method || 'ランダムサーチ'}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Typography variant="caption" color="text.secondary">
                        最適化指標
                      </Typography>
                      <Typography variant="body1">
                        {result.optimizationMetric || result.optimization_metric}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Typography variant="caption" color="text.secondary">
                        ベストテストID
                      </Typography>
                      <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
                        {result.bestTestId || result.best_test_id}
                      </Typography>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>
            </Grid>
          </CardContent>
        )}

        {/* 収束分析タブ */}
        {activeTab === 1 && (
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <Timeline sx={{ mr: 1, verticalAlign: 'middle' }} />
              収束分析
            </Typography>
            
            {/* 収束状態 */}
            <Alert 
              severity={result.convergenceAnalysis?.converged ? "success" : "warning"}
              sx={{ mb: 3 }}
            >
              {result.convergenceAnalysis?.converged 
                ? `最適化は${result.convergenceAnalysis.iterations}回のイテレーションで収束しました。`
                : `最適化は未収束です。より多くのイテレーションが必要な可能性があります。`
              }
            </Alert>

            {/* 収束チャート */}
            <Paper sx={{ p: 2, height: 400, mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>スコア収束グラフ</Typography>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={convergenceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="iteration" />
                  <YAxis />
                  <Tooltip formatter={(value) => formatNumber(value as number, 3)} />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="score" 
                    stroke="#1976d2" 
                    name="スコア" 
                    strokeWidth={2}
                    dot={{ fill: '#1976d2', strokeWidth: 2, r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Paper>

            {/* 収束統計 */}
            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    収束状態
                  </Typography>
                  <Typography variant="h6" fontWeight={600}>
                    {result.convergenceAnalysis?.converged ? '収束済み' : '未収束'}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    改善率
                  </Typography>
                  <Typography variant="h6" fontWeight={600}>
                    {formatPercentage((result.convergenceAnalysis?.improvement_rate || 0) * 100)}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    安定性スコア
                  </Typography>
                  <Typography variant="h6" fontWeight={600}>
                    {formatNumber((result.convergenceAnalysis?.stability_score || 0) * 100, 1)}%
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </CardContent>
        )}

        {/* パラメータ感度タブ */}
        {activeTab === 2 && (
          <CardContent>
            <Typography variant="h6" gutterBottom>
              パラメータ感度分析
            </Typography>
            
            {/* 感度チャート */}
            <Paper sx={{ p: 2, height: 400, mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>パラメータ感度</Typography>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sensitivityData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="parameter" />
                  <YAxis />
                  <Tooltip formatter={(value) => `${formatNumber(value as number, 1)}%`} />
                  <Bar dataKey="sensitivity" fill="#1976d2" />
                </BarChart>
              </ResponsiveContainer>
            </Paper>

            {/* 感度テーブル */}
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>パラメータ</TableCell>
                    <TableCell align="right">感度</TableCell>
                    <TableCell align="center">影響度</TableCell>
                    <TableCell align="right">最適値</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {result.parameterSensitivity?.map((param) => (
                    <TableRow key={param.parameter}>
                      <TableCell>{param.parameter}</TableCell>
                      <TableCell align="right">
                        {formatPercentage(param.sensitivity * 100)}
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={param.impact}
                          color={
                            param.impact === 'HIGH' ? 'error' :
                            param.impact === 'MEDIUM' ? 'warning' : 'success'
                          }
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="right">
                        {formatNumber(param.optimalValue || param.optimal_value, 2)}
                      </TableCell>
                    </TableRow>
                  )) || []}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        )}

        {/* 推奨事項タブ */}
        {activeTab === 3 && (
          <CardContent>
            <Typography variant="h6" gutterBottom>
              推奨事項
            </Typography>
            
            <Grid container spacing={3}>
              {/* 最適化に関する推奨事項 */}
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    最適化について
                  </Typography>
                  <List dense>
                    {result.convergenceAnalysis?.converged ? (
                      <ListItem>
                        <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                        <ListItemText primary="最適化は正常に収束しました" />
                      </ListItem>
                    ) : (
                      <ListItem>
                        <ListItemIcon><Warning color="warning" /></ListItemIcon>
                        <ListItemText primary="最適化が収束していません。イテレーション数を増やすことを検討してください" />
                      </ListItem>
                    )}
                    
                    {(result.convergenceAnalysis?.improvement_rate || 0) < 0.1 && (
                      <ListItem>
                        <ListItemIcon><Warning color="warning" /></ListItemIcon>
                        <ListItemText primary="改善率が低いです。パラメータ範囲を見直すことを検討してください" />
                      </ListItem>
                    )}
                  </List>
                </Paper>
              </Grid>

              {/* パラメータに関する推奨事項 */}
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    パラメータについて
                  </Typography>
                  <List dense>
                    {result.parameterSensitivity?.filter(param => param.impact === 'HIGH').map(param => (
                      <ListItem key={param.parameter}>
                        <ListItemIcon><TrendingUp color="error" /></ListItemIcon>
                        <ListItemText 
                          primary={`${param.parameter}は結果に大きく影響します`}
                          secondary={`最適値: ${formatNumber(param.optimalValue || param.optimal_value, 2)}`}
                        />
                      </ListItem>
                    )) || []}
                    
                    {result.parameterSensitivity?.filter(param => param.impact === 'LOW').map(param => (
                      <ListItem key={param.parameter}>
                        <ListItemIcon><TrendingDown color="success" /></ListItemIcon>
                        <ListItemText 
                          primary={`${param.parameter}の影響は限定的です`}
                          secondary="固定値として扱うことを検討できます"
                        />
                      </ListItem>
                    )) || []}
                  </List>
                </Paper>
              </Grid>

              {/* 次のステップ */}
              <Grid item xs={12}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    次のステップ
                  </Typography>
                  <List dense>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="info" /></ListItemIcon>
                      <ListItemText primary="最適パラメータでバックテストを実行して詳細な結果を確認" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="info" /></ListItemIcon>
                      <ListItemText primary="異なる期間でパラメータの安定性を検証" />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><CheckCircle color="info" /></ListItemIcon>
                      <ListItemText primary="フォワードテストでリアルタイムパフォーマンスを評価" />
                    </ListItem>
                  </List>
                </Paper>
              </Grid>
            </Grid>
          </CardContent>
        )}
      </Card>
    </Box>
  )
}

export default OptimizationResults