/**
 * バックテスト実行フォームコンポーネント
 */
'use client'

import React, { useState } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Box,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControlLabel,
  Switch,
  Slider,
  Alert,
  LinearProgress
} from '@mui/material'
import {
  ExpandMore,
  PlayArrow,
  TuneRounded,
  Analytics
} from '@mui/icons-material'
// DatePickerを削除してHTML input[type="date"]を使用
import { 
  useBacktest, 
  useOptimization, 
  useComprehensiveBacktest 
} from '@/hooks/useBacktest'
import { BacktestRequest, OptimizationRequest, ComprehensiveBacktestRequest } from '@/types/backtest'
import { CURRENCY_PAIRS, TIMEFRAMES, CURRENCY_PAIR_LABELS, TIMEFRAME_LABELS } from '@/lib/constants'

interface BacktestFormProps {
  onResult?: (testId: string, mode?: 'single' | 'optimization' | 'comprehensive') => void
  onOptimizationResult?: (result: any) => void
  onComprehensiveResult?: (result: any) => void
  defaultValues?: Partial<BacktestRequest>
}

export function BacktestForm({ onResult, onOptimizationResult, onComprehensiveResult, defaultValues }: BacktestFormProps) {
  const [mode, setMode] = useState<'single' | 'optimization' | 'comprehensive'>('single')
  
  // Use fixed dates to avoid hydration mismatch
  const getDefaultStartDate = () => {
    if (defaultValues?.startDate) return defaultValues.startDate
    // Use a fixed date (1 year ago from 2024-12-31)
    return '2023-12-31'
  }
  
  const getDefaultEndDate = () => {
    if (defaultValues?.endDate) return defaultValues.endDate
    // Use a fixed date
    return '2024-12-31'
  }
  
  const [formData, setFormData] = useState<BacktestRequest>({
    symbol: defaultValues?.symbol || 'USDJPY',
    timeframe: defaultValues?.timeframe || 'H1',
    startDate: getDefaultStartDate(),
    endDate: getDefaultEndDate(),
    initialBalance: defaultValues?.initialBalance || 100000,
    parameters: {
      rsiPeriod: 14,
      rsiOverbought: 70,
      rsiOversold: 30,
      macdFast: 12,
      macdSlow: 26,
      macdSignal: 9,
      bollingerPeriod: 20,
      bollingerStdDev: 2,
      stopLossPercent: 2.0,
      takeProfitPercent: 4.0,
      maxPositions: 1,
      ...defaultValues?.parameters
    }
  })

  const [optimizationParams, setOptimizationParams] = useState({
    target: 'profit_factor' as 'profit_factor' | 'max_drawdown' | 'sharpe_ratio',
    iterations: 100,
    populationSize: 50
  })

  const singleBacktest = useBacktest()
  const optimization = useOptimization()
  const comprehensiveBacktest = useComprehensiveBacktest()

  const getCurrentMutation = () => {
    switch (mode) {
      case 'optimization': return optimization
      case 'comprehensive': return comprehensiveBacktest
      default: return singleBacktest
    }
  }

  const handleSubmit = async () => {
    const currentMutation = getCurrentMutation()

    try {
      if (mode === 'single') {
        const result = await singleBacktest.mutateAsync(formData)
        onResult?.(result.testId, 'single')
      } else if (mode === 'optimization') {
        const request: OptimizationRequest = {
          symbol: formData.symbol,
          timeframe: formData.timeframe,
          startDate: formData.startDate,
          endDate: formData.endDate,
          initialBalance: formData.initialBalance,
          optimizationMetric: optimizationParams.target,
          maxIterations: optimizationParams.iterations,
          optimizationMethod: 'random_search' as any,
          parameterRanges: {
            rsiPeriod: { min: 10, max: 20, step: 1 },
            rsiOverbought: { min: 65, max: 80, step: 1 },
            rsiOversold: { min: 15, max: 35, step: 1 },
            stopLossPercent: { min: 1.0, max: 5.0, step: 0.1 },
            takeProfitPercent: { min: 2.0, max: 8.0, step: 0.1 }
          }
        }
        const result = await optimization.mutateAsync(request)
        console.log('Optimization result:', result)
        
        // 最適化結果は別のハンドラーで処理
        if (onOptimizationResult) {
          onOptimizationResult(result)
        } else {
          // フォールバック: bestTestIdがあればそれを使用
          const testId = (result as any).bestTestId || (result as any).best_test_id
          if (testId) {
            onResult?.(testId, 'optimization')
          }
        }
      } else {
        const request: ComprehensiveBacktestRequest = {
          startDate: formData.startDate,
          endDate: formData.endDate,
          initialBalance: formData.initialBalance,
          parameters: formData.parameters
        }
        const result = await comprehensiveBacktest.mutateAsync(request)
        console.log('Comprehensive result received:', {
          hasResult: !!result,
          resultKeys: result ? Object.keys(result) : [],
          fullResult: result
        })
        
        // 包括的結果は別のハンドラーで処理
        if (onComprehensiveResult) {
          console.log('Calling onComprehensiveResult with:', result)
          onComprehensiveResult(result)
        } else {
          // フォールバック: batchIdがあればそれを使用
          const batchId = (result as any).batchId
          if (batchId) {
            onResult?.(batchId, 'comprehensive')
          }
        }
      }
    } catch (error) {
      console.error('Backtest error:', error)
    }
  }

  const updateFormData = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const updateParameters = (param: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      parameters: { ...prev.parameters, [param]: value }
    }))
  }

  const isLoading = singleBacktest.isPending || optimization.isPending || comprehensiveBacktest.isPending
  const currentMutation = getCurrentMutation()

  return (
    <div>
      <Card>
        <CardHeader
          title="バックテスト実行"
          action={
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>モード</InputLabel>
              <Select
                value={mode}
                onChange={(e) => setMode(e.target.value as any)}
                label="モード"
                disabled={isLoading}
              >
                <MenuItem value="single">単体テスト</MenuItem>
                <MenuItem value="optimization">パラメータ最適化</MenuItem>
                <MenuItem value="comprehensive">包括的テスト</MenuItem>
              </Select>
            </FormControl>
          }
        />
        <CardContent>
          <Box display="flex" flexDirection="column" gap={3}>
            {/* 基本設定 */}
            <Box>
              <Typography variant="h6" gutterBottom>
                基本設定
              </Typography>
              <Grid container spacing={2}>
                {mode !== 'comprehensive' && (
                  <>
                    <Grid item xs={12} md={6}>
                      <FormControl fullWidth>
                        <InputLabel>通貨ペア</InputLabel>
                        <Select
                          value={formData.symbol}
                          onChange={(e) => updateFormData('symbol', e.target.value)}
                          label="通貨ペア"
                          disabled={isLoading}
                        >
                          {CURRENCY_PAIRS.map((pair) => (
                            <MenuItem key={pair} value={pair}>
                              {CURRENCY_PAIR_LABELS[pair]}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <FormControl fullWidth>
                        <InputLabel>時間軸</InputLabel>
                        <Select
                          value={formData.timeframe}
                          onChange={(e) => updateFormData('timeframe', e.target.value)}
                          label="時間軸"
                          disabled={isLoading}
                        >
                          {TIMEFRAMES.map((tf) => (
                            <MenuItem key={tf} value={tf}>
                              {TIMEFRAME_LABELS[tf]}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Grid>
                  </>
                )}
                
                <Grid item xs={12} md={4}>
                  <TextField
                    label="開始日"
                    type="date"
                    value={formData.startDate}
                    onChange={(e) => updateFormData('startDate', e.target.value)}
                    disabled={isLoading}
                    fullWidth
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    label="終了日"
                    type="date"
                    value={formData.endDate}
                    onChange={(e) => updateFormData('endDate', e.target.value)}
                    disabled={isLoading}
                    fullWidth
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    label="初期資金"
                    type="number"
                    value={formData.initialBalance}
                    onChange={(e) => updateFormData('initialBalance', Number(e.target.value))}
                    disabled={isLoading}
                    fullWidth
                    InputProps={{ endAdornment: '円' }}
                  />
                </Grid>
              </Grid>
            </Box>

            {/* 最適化設定 */}
            {mode === 'optimization' && (
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <TuneRounded />
                    <Typography variant="h6">最適化設定</Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={4}>
                      <FormControl fullWidth>
                        <InputLabel>最適化目標</InputLabel>
                        <Select
                          value={optimizationParams.target}
                          onChange={(e) => setOptimizationParams(prev => ({ 
                            ...prev, 
                            target: e.target.value as any 
                          }))}
                          label="最適化目標"
                          disabled={isLoading}
                        >
                          <MenuItem value="profit_factor">プロフィットファクター</MenuItem>
                          <MenuItem value="max_drawdown">最大ドローダウン</MenuItem>
                          <MenuItem value="sharpe_ratio">シャープレシオ</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <TextField
                        label="イテレーション数"
                        type="number"
                        value={optimizationParams.iterations}
                        onChange={(e) => setOptimizationParams(prev => ({ 
                          ...prev, 
                          iterations: Number(e.target.value) 
                        }))}
                        disabled={isLoading}
                        fullWidth
                      />
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <TextField
                        label="集団サイズ"
                        type="number"
                        value={optimizationParams.populationSize}
                        onChange={(e) => setOptimizationParams(prev => ({ 
                          ...prev, 
                          populationSize: Number(e.target.value) 
                        }))}
                        disabled={isLoading}
                        fullWidth
                      />
                    </Grid>
                  </Grid>
                </AccordionDetails>
              </Accordion>
            )}

            {/* パラメータ設定 */}
            {mode !== 'optimization' && (
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Analytics />
                    <Typography variant="h6">テクニカル分析パラメータ</Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={3}>
                    {/* RSI設定 */}
                    <Grid item xs={12}>
                      <Typography variant="subtitle2" gutterBottom>RSI設定</Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={12} md={4}>
                          <Typography gutterBottom>期間: {formData.parameters.rsiPeriod}</Typography>
                          <Slider
                            value={formData.parameters.rsiPeriod}
                            onChange={(_, value) => updateParameters('rsiPeriod', value)}
                            min={5}
                            max={30}
                            disabled={isLoading}
                          />
                        </Grid>
                        <Grid item xs={12} md={4}>
                          <Typography gutterBottom>買われすぎ: {formData.parameters.rsiOverbought}</Typography>
                          <Slider
                            value={formData.parameters.rsiOverbought}
                            onChange={(_, value) => updateParameters('rsiOverbought', value)}
                            min={60}
                            max={90}
                            disabled={isLoading}
                          />
                        </Grid>
                        <Grid item xs={12} md={4}>
                          <Typography gutterBottom>売られすぎ: {formData.parameters.rsiOversold}</Typography>
                          <Slider
                            value={formData.parameters.rsiOversold}
                            onChange={(_, value) => updateParameters('rsiOversold', value)}
                            min={10}
                            max={40}
                            disabled={isLoading}
                          />
                        </Grid>
                      </Grid>
                    </Grid>

                    {/* リスク管理設定 */}
                    <Grid item xs={12}>
                      <Typography variant="subtitle2" gutterBottom>リスク管理</Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                          <Typography gutterBottom>ストップロス: {formData.parameters.stopLossPercent}%</Typography>
                          <Slider
                            value={formData.parameters.stopLossPercent}
                            onChange={(_, value) => updateParameters('stopLossPercent', value)}
                            min={0.5}
                            max={10}
                            step={0.1}
                            disabled={isLoading}
                          />
                        </Grid>
                        <Grid item xs={12} md={6}>
                          <Typography gutterBottom>テイクプロフィット: {formData.parameters.takeProfitPercent}%</Typography>
                          <Slider
                            value={formData.parameters.takeProfitPercent}
                            onChange={(_, value) => updateParameters('takeProfitPercent', value)}
                            min={1}
                            max={20}
                            step={0.1}
                            disabled={isLoading}
                          />
                        </Grid>
                      </Grid>
                    </Grid>
                  </Grid>
                </AccordionDetails>
              </Accordion>
            )}

            {/* 実行進行状況 */}
            {isLoading && (
              <Alert severity="info">
                <Box>
                  <Typography variant="body2" gutterBottom>
                    {mode === 'single' && 'バックテストを実行中...'}
                    {mode === 'optimization' && 'パラメータ最適化を実行中...'}
                    {mode === 'comprehensive' && '包括的バックテストを実行中...'}
                  </Typography>
                  {mode === 'comprehensive' && (
                    <Typography variant="caption" color="text.secondary" gutterBottom>
                      まず高速モード（2通貨ペア×2時間軸）で実行し、失敗した場合は完全モードにフォールバックします。
                    </Typography>
                  )}
                  <LinearProgress variant="determinate" value={currentMutation.progress || 0} />
                  <Typography variant="caption" color="text.secondary">
                    {Math.round(currentMutation.progress || 0)}% 完了
                    {mode === 'comprehensive' && ' - 高速モードで実行中'}
                  </Typography>
                </Box>
              </Alert>
            )}

            {/* 実行ボタン */}
            <Button
              variant="contained"
              size="large"
              startIcon={<PlayArrow />}
              onClick={handleSubmit}
              disabled={isLoading}
              fullWidth
            >
              {isLoading ? '実行中...' : 
               mode === 'single' ? 'バックテスト実行' :
               mode === 'optimization' ? 'パラメータ最適化実行' :
               '包括的バックテスト実行'}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </div>
  )
}

export default BacktestForm