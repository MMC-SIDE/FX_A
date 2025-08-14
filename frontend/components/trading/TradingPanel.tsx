/**
 * 取引制御パネルコンポーネント
 */
'use client'

import React, { useState } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box,
  Chip,
  Alert,
  Typography,
  Grid,
  Switch,
  FormControlLabel,
  TextField
} from '@mui/material'
import {
  PlayArrow,
  Stop,
  TrendingUp,
  TrendingDown,
  Warning,
  CheckCircle,
  Error as ErrorIcon
} from '@mui/icons-material'
import { useStartTrading, useStopTrading, useTradingStatus } from '@/hooks/useTrades'
import { useTradingSelectors, useTradingActions } from '@/store/trading'
import { useSettingsSelectors } from '@/store/settings'
import { useNotifications } from '@/store/ui'
import { formatCurrency, formatDateTime } from '@/lib/utils'
import { CURRENCY_PAIRS, TIMEFRAMES, CURRENCY_PAIR_LABELS, TIMEFRAME_LABELS } from '@/lib/constants'

export function TradingPanel() {
  const {
    isActive,
    isConnected,
    selectedSymbol,
    selectedTimeframe,
    tradingStatus,
    error
  } = useTradingSelectors()
  
  const {
    setSelectedSymbol,
    setSelectedTimeframe,
    setError
  } = useTradingActions()
  
  const { tradingSettings } = useSettingsSelectors()
  const { showWarning } = useNotifications()
  
  const [symbol, setSymbol] = useState(selectedSymbol)
  const [timeframe, setTimeframe] = useState(selectedTimeframe)
  const [enableAutoTrading, setEnableAutoTrading] = useState(tradingSettings.enableAutoTrading)
  
  const startTradingMutation = useStartTrading()
  const stopTradingMutation = useStopTrading()
  const { data: status, isLoading: statusLoading } = useTradingStatus()

  const handleStart = async () => {
    if (!isConnected) {
      showWarning('接続エラー', 'MT5に接続されていません。接続を確認してください。')
      return
    }

    if (!enableAutoTrading) {
      showWarning('自動取引無効', '自動取引が無効になっています。設定を確認してください。')
      return
    }

    try {
      await startTradingMutation.mutateAsync({ symbol, timeframe })
      setSelectedSymbol(symbol)
      setSelectedTimeframe(timeframe)
      setError(null)
    } catch (error) {
      console.error('Failed to start trading:', error)
    }
  }

  const handleStop = async () => {
    try {
      await stopTradingMutation.mutateAsync()
      setError(null)
    } catch (error) {
      console.error('Failed to stop trading:', error)
    }
  }

  const getConnectionStatus = () => {
    if (!isConnected) return { color: 'error', text: '未接続', icon: <ErrorIcon /> }
    if (isActive) return { color: 'success', text: '取引中', icon: <CheckCircle /> }
    return { color: 'warning', text: '待機中', icon: <Warning /> }
  }

  const connectionStatus = getConnectionStatus()

  return (
    <Card>
      <CardHeader
        title="取引制御"
        action={
          <Chip
            label={connectionStatus.text}
            color={connectionStatus.color}
            icon={connectionStatus.icon}
            size="small"
          />
        }
      />
      <CardContent>
        <Box display="flex" flexDirection="column" gap={3}>
          {/* 接続状態とバランス情報 */}
          {status && (
            <Box>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    口座残高
                  </Typography>
                  <Typography variant="h6" fontWeight={600}>
                    {formatCurrency(status.accountBalance || 0)}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    有効証拠金
                  </Typography>
                  <Typography variant="h6" fontWeight={600}>
                    {formatCurrency(status.equity || 0)}
                  </Typography>
                </Grid>
              </Grid>
            </Box>
          )}

          {/* 取引設定 */}
          <Box>
            <FormControl fullWidth margin="normal">
              <InputLabel>通貨ペア</InputLabel>
              <Select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                disabled={isActive}
                label="通貨ペア"
              >
                {CURRENCY_PAIRS.map((pair) => (
                  <MenuItem key={pair} value={pair}>
                    {CURRENCY_PAIR_LABELS[pair]}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth margin="normal">
              <InputLabel>時間軸</InputLabel>
              <Select
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                disabled={isActive}
                label="時間軸"
              >
                {TIMEFRAMES.map((tf) => (
                  <MenuItem key={tf} value={tf}>
                    {TIMEFRAME_LABELS[tf]}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControlLabel
              control={
                <Switch
                  checked={enableAutoTrading}
                  onChange={(e) => setEnableAutoTrading(e.target.checked)}
                  disabled={isActive}
                />
              }
              label="自動取引を有効にする"
              sx={{ mt: 1 }}
            />
          </Box>

          {/* リスク設定表示 */}
          <Box sx={{ bgcolor: 'background.paper', p: 2, borderRadius: 1, border: '1px solid', borderColor: 'divider' }}>
            <Typography variant="subtitle2" gutterBottom>
              リスク設定
            </Typography>
            <Grid container spacing={1}>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">
                  取引リスク
                </Typography>
                <Typography variant="body2">
                  {tradingSettings.riskPerTrade}%
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">
                  最大ポジション
                </Typography>
                <Typography variant="body2">
                  制限なし
                </Typography>
              </Grid>
            </Grid>
          </Box>

          {/* エラー表示 */}
          {error && (
            <Alert severity="error" onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* 取引制御ボタン */}
          <Box display="flex" gap={2}>
            {!isActive ? (
              <Button
                variant="contained"
                color="primary"
                size="large"
                startIcon={<PlayArrow />}
                onClick={handleStart}
                disabled={
                  startTradingMutation.isPending || 
                  !isConnected || 
                  !enableAutoTrading ||
                  statusLoading
                }
                fullWidth
              >
                {startTradingMutation.isPending ? '開始中...' : '取引開始'}
              </Button>
            ) : (
              <Button
                variant="contained"
                color="error"
                size="large"
                startIcon={<Stop />}
                onClick={handleStop}
                disabled={stopTradingMutation.isPending || statusLoading}
                fullWidth
              >
                {stopTradingMutation.isPending ? '停止中...' : '取引停止'}
              </Button>
            )}
          </Box>

          {/* 取引状態詳細 */}
          {isActive && status && (
            <Box sx={{ bgcolor: 'success.light', p: 2, borderRadius: 1, color: 'success.contrastText' }}>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <TrendingUp />
                <Typography variant="subtitle2" fontWeight={600}>
                  自動取引実行中
                </Typography>
              </Box>
              <Typography variant="body2">
                通貨ペア: {CURRENCY_PAIR_LABELS[status.currentSymbol || selectedSymbol]}
              </Typography>
              <Typography variant="body2">
                時間軸: {TIMEFRAME_LABELS[status.currentTimeframe || selectedTimeframe]}
              </Typography>
              {status.lastUpdate && (
                <Typography variant="caption">
                  最終更新: {formatDateTime(status.lastUpdate)}
                </Typography>
              )}
            </Box>
          )}

          {/* 接続エラー時の警告 */}
          {!isConnected && (
            <Alert severity="warning">
              MT5に接続されていません。システム設定を確認してください。
            </Alert>
          )}
        </Box>
      </CardContent>
    </Card>
  )
}

export default TradingPanel