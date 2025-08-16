'use client'

import React, { useState } from 'react'
import { Container, Grid, Paper, Typography, Box, Card, CardContent, Button, Chip, Snackbar, Alert } from '@mui/material'
import { 
  TrendingUp, 
  TrendingDown, 
  AccountBalance, 
  ShowChart,
  PlayArrow,
  Stop,
  Assessment,
  Settings
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'

// APIからデータ取得
const fetchSystemStatus = async () => {
  const response = await fetch('http://localhost:8000/status')
  if (!response.ok) throw new Error('Failed to fetch status')
  return response.json()
}

const fetchHealthCheck = async () => {
  const response = await fetch('http://localhost:8000/health')
  if (!response.ok) throw new Error('Failed to fetch health')
  return response.json()
}

// MT5再接続API
const reconnectMT5 = async () => {
  const response = await fetch('http://localhost:8000/mt5/reconnect', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  })
  if (!response.ok) throw new Error('Failed to reconnect MT5')
  return response.json()
}

// MT5口座情報取得API
const fetchMT5Account = async () => {
  const response = await fetch('http://localhost:8000/mt5/account')
  if (!response.ok) throw new Error('Failed to fetch MT5 account')
  return response.json()
}

export default function Home() {
  const queryClient = useQueryClient()
  const [mounted, setMounted] = useState(false)
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' })

  const { data: status } = useQuery({
    queryKey: ['status'],
    queryFn: fetchSystemStatus,
    refetchInterval: 5000
  })

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealthCheck,
    refetchInterval: 10000
  })

  // useEffectでmountedフラグを設定
  React.useEffect(() => {
    setMounted(true)
  }, [])

  // MT5口座情報を取得
  const { data: mt5Account } = useQuery({
    queryKey: ['mt5-account'],
    queryFn: fetchMT5Account,
    refetchInterval: 30000, // 30秒間隔で更新
    retry: 1 // エラー時は1回だけリトライ
  })

  // MT5再接続用のMutation
  const reconnectMutation = useMutation({
    mutationFn: reconnectMT5,
    onSuccess: (data) => {
      // 再接続成功時にヘルスチェックと口座情報を再実行
      queryClient.invalidateQueries({ queryKey: ['health'] })
      queryClient.invalidateQueries({ queryKey: ['mt5-account'] })
      setSnackbar({ 
        open: true, 
        message: data.success ? 'MT5再接続に成功しました' : 'MT5再接続に失敗しました', 
        severity: data.success ? 'success' : 'error' 
      })
    },
    onError: (error) => {
      console.error('MT5 reconnection failed:', error)
      setSnackbar({ 
        open: true, 
        message: 'MT5再接続中にエラーが発生しました', 
        severity: 'error' 
      })
    }
  })

  const handleMT5Reconnect = () => {
    if (health?.mt5?.status !== 'healthy') {
      reconnectMutation.mutate()
    }
  }

  const handleSnackbarClose = () => {
    setSnackbar({ ...snackbar, open: false })
  }

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Container maxWidth="xl">
        {/* ヘッダー */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h3" component="h1" gutterBottom fontWeight="bold">
            FX Trading System
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            自動売買システム ダッシュボード
          </Typography>
        </Box>

        {/* ステータスカード */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <AccountBalance sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6">口座残高</Typography>
                </Box>
                <Typography variant="h4" fontWeight="bold">
                  {mt5Account?.account_info?.currency === 'JPY' 
                    ? `¥${(mt5Account?.account_info?.balance || 0).toLocaleString()}` 
                    : `$${(mt5Account?.account_info?.balance || 0).toLocaleString()}`
                  }
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {mt5Account?.account_info?.balance 
                    ? `証拠金: ¥${(mt5Account.account_info.equity || 0).toLocaleString()}` 
                    : 'データ取得中...'
                  }
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <TrendingUp sx={{ mr: 1, color: 'success.main' }} />
                  <Typography variant="h6">本日の損益</Typography>
                </Box>
                <Typography variant="h4" fontWeight="bold" color="success.main">
                  +¥0
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  0.00%
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <ShowChart sx={{ mr: 1, color: 'info.main' }} />
                  <Typography variant="h6">オープンポジション</Typography>
                </Box>
                <Typography variant="h4" fontWeight="bold">
                  0
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  アクティブな取引
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Assessment sx={{ mr: 1, color: 'warning.main' }} />
                  <Typography variant="h6">勝率</Typography>
                </Box>
                <Typography variant="h4" fontWeight="bold">
                  --%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  過去30日間
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* システムステータス */}
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom fontWeight="bold">
                システムステータス
              </Typography>
              
              <Box sx={{ mt: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Typography>API サーバー</Typography>
                  <Chip 
                    label={status?.api_status === 'running' ? '稼働中' : '停止中'} 
                    color={status?.api_status === 'running' ? 'success' : 'error'}
                    size="small"
                  />
                </Box>
                
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Typography>データベース</Typography>
                  <Chip 
                    label={health?.database?.status === 'healthy' ? '正常' : 'エラー'} 
                    color={health?.database?.status === 'healthy' ? 'success' : 'error'}
                    size="small"
                  />
                </Box>
                
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Typography>MT5 接続</Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                    <Chip 
                      label={
                        reconnectMutation.isPending 
                          ? '再接続中...' 
                          : (health?.mt5?.status === 'healthy' ? '接続済み' : '未接続')
                      } 
                      color={health?.mt5?.status === 'healthy' ? 'success' : 'warning'}
                      size="small"
                      onClick={handleMT5Reconnect}
                      disabled={reconnectMutation.isPending || health?.mt5?.status === 'healthy'}
                      sx={{ 
                        cursor: health?.mt5?.status !== 'healthy' && !reconnectMutation.isPending ? 'pointer' : 'default',
                        '&:hover': {
                          backgroundColor: health?.mt5?.status !== 'healthy' && !reconnectMutation.isPending ? 'action.hover' : 'transparent'
                        }
                      }}
                    />
                    {health?.mt5?.status !== 'healthy' && (
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                        MT5ターミナルを起動してください
                      </Typography>
                    )}
                  </Box>
                </Box>

                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Typography>自動売買</Typography>
                  <Chip 
                    label="停止中" 
                    color="default"
                    size="small"
                  />
                </Box>
              </Box>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom fontWeight="bold">
                取引制御
              </Typography>
              
              <Box sx={{ mt: 3 }}>
                <Box sx={{ mb: 3 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    自動売買システムの開始・停止を制御します
                  </Typography>
                </Box>
                
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <Link href="/trading" passHref style={{ textDecoration: 'none', flex: 1 }}>
                    <Button 
                      variant="contained" 
                      color="primary"
                      startIcon={<Settings />}
                      size="large"
                      fullWidth
                    >
                      取引制御画面
                    </Button>
                  </Link>
                </Box>

                <Box sx={{ mt: 3 }}>
                  <Typography variant="body2" color="text.secondary">
                    最終更新: {mounted ? new Date().toLocaleString('ja-JP') : '---'}
                  </Typography>
                </Box>
              </Box>
            </Paper>
          </Grid>

          {/* 機能ナビゲーション */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom fontWeight="bold">
                システム機能
              </Typography>
              
              <Grid container spacing={2} sx={{ mt: 2 }}>
                <Grid item xs={12} sm={6} md={3}>
                  <Link href="/trading" style={{ textDecoration: 'none' }}>
                    <Card variant="outlined" sx={{ cursor: 'pointer', '&:hover': { backgroundColor: 'action.hover' } }}>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <TrendingUp sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
                        <Typography variant="h6" fontWeight="bold">
                          自動売買制御
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          取引の開始・停止・監視
                        </Typography>
                      </CardContent>
                    </Card>
                  </Link>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Link href="/backtest" style={{ textDecoration: 'none' }}>
                    <Card variant="outlined" sx={{ cursor: 'pointer', '&:hover': { backgroundColor: 'action.hover' } }}>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Assessment sx={{ fontSize: 40, color: 'secondary.main', mb: 1 }} />
                        <Typography variant="h6" fontWeight="bold">
                          バックテスト
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          過去データでの戦略検証
                        </Typography>
                      </CardContent>
                    </Card>
                  </Link>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Link href="/ml" style={{ textDecoration: 'none' }}>
                    <Card variant="outlined" sx={{ cursor: 'pointer', '&:hover': { backgroundColor: 'action.hover' } }}>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <ShowChart sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
                        <Typography variant="h6" fontWeight="bold">
                          機械学習
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          LightGBMモデル管理
                        </Typography>
                      </CardContent>
                    </Card>
                  </Link>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Link href="/settings" style={{ textDecoration: 'none' }}>
                    <Card variant="outlined" sx={{ cursor: 'pointer', '&:hover': { backgroundColor: 'action.hover' } }}>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Settings sx={{ fontSize: 40, color: 'warning.main', mb: 1 }} />
                        <Typography variant="h6" fontWeight="bold">
                          設定
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          システム設定・管理
                        </Typography>
                      </CardContent>
                    </Card>
                  </Link>
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          {/* 通貨ペア一覧 */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom fontWeight="bold">
                監視通貨ペア
              </Typography>
              
              <Grid container spacing={2} sx={{ mt: 2 }}>
                {['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'CADJPY', 'CHFJPY'].map((pair) => (
                  <Grid item xs={12} sm={6} md={3} key={pair}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="h6" fontWeight="bold">
                          {pair}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          レート: ---
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          スプレッド: ---
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      </Container>

      {/* 通知用Snackbar */}
      <Snackbar 
        open={snackbar.open} 
        autoHideDuration={6000} 
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={handleSnackbarClose} 
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}