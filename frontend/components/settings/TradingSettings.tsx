/**
 * 取引設定コンポーネント
 */
'use client'

import React, { useState } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Button,
  Box,
  Slider,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip
} from '@mui/material'
import {
  ExpandMore,
  Save,
  RestoreRounded,
  Security,
  TrendingUp,
  Schedule
} from '@mui/icons-material'
import { useSettingsSelectors, useSettingsActions } from '@/store/settings'
import { useNotifications } from '@/store/ui'
import { CURRENCY_PAIRS, TIMEFRAMES, CURRENCY_PAIR_LABELS, TIMEFRAME_LABELS } from '@/lib/constants'

export function TradingSettings() {
  const { tradingSettings } = useSettingsSelectors()
  const { updateTradingSettings } = useSettingsActions()
  const { showSuccess, showError } = useNotifications()
  
  const [localSettings, setLocalSettings] = useState(tradingSettings)
  const [hasChanges, setHasChanges] = useState(false)

  const handleChange = (field: string, value: any) => {
    setLocalSettings(prev => ({ ...prev, [field]: value }))
    setHasChanges(true)
  }

  const handleSave = async () => {
    try {
      updateTradingSettings(localSettings)
      setHasChanges(false)
      showSuccess('設定保存', '取引設定が保存されました')
    } catch (error) {
      showError('保存エラー', '設定の保存に失敗しました')
    }
  }

  const handleReset = () => {
    setLocalSettings(tradingSettings)
    setHasChanges(false)
  }

  const handleResetToDefaults = () => {
    const defaultSettings = {
      enableAutoTrading: false,
      riskPerTrade: 2.0,
      maxDrawdown: 20.0,
      enableNanpin: true,
      nanpinMaxCount: 3,
      nanpinInterval: 10,
      lotAllocation: 'equal' as const,
      maxConcurrentPositions: 5,
      defaultStopLoss: 2.0,
      defaultTakeProfit: 4.0,
      slippageLimit: 2,
      tradingTimeframes: ['H1'],
      preferredCurrencies: ['USDJPY', 'EURJPY'],
      enableWeekendClose: true,
      enableNewsFilter: false,
      emergencyStopLoss: 10.0
    }
    setLocalSettings(defaultSettings)
    setHasChanges(true)
  }

  return (
    <Box display="flex" flexDirection="column" gap={3}>
      {/* アクションボタン */}
      <Box display="flex" justifyContent="space-between" alignItems="center">
        <Typography variant="h6">取引設定</Typography>
        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            onClick={handleResetToDefaults}
            startIcon={<RestoreRounded />}
          >
            デフォルトに戻す
          </Button>
          <Button
            variant="outlined"
            onClick={handleReset}
            disabled={!hasChanges}
          >
            リセット
          </Button>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={!hasChanges}
            startIcon={<Save />}
          >
            保存
          </Button>
        </Box>
      </Box>

      {hasChanges && (
        <Alert severity="warning">
          未保存の変更があります。保存ボタンをクリックして設定を保存してください。
        </Alert>
      )}

      {/* 基本設定 */}
      <Card>
        <CardHeader
          title={
            <Box display="flex" alignItems="center" gap={1}>
              <TrendingUp />
              <Typography variant="h6">基本取引設定</Typography>
            </Box>
          }
        />
        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={localSettings.enableAutoTrading}
                    onChange={(e) => handleChange('enableAutoTrading', e.target.checked)}
                  />
                }
                label="自動取引を有効にする"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                1取引あたりのリスク: {localSettings.riskPerTrade}%
              </Typography>
              <Slider
                value={localSettings.riskPerTrade}
                onChange={(_, value) => handleChange('riskPerTrade', value)}
                min={0.1}
                max={10}
                step={0.1}
                marks={[
                  { value: 1, label: '1%' },
                  { value: 2, label: '2%' },
                  { value: 5, label: '5%' },
                  { value: 10, label: '10%' }
                ]}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                最大ドローダウン: {localSettings.maxDrawdown}%
              </Typography>
              <Slider
                value={localSettings.maxDrawdown}
                onChange={(_, value) => handleChange('maxDrawdown', value)}
                min={5}
                max={50}
                step={1}
                marks={[
                  { value: 10, label: '10%' },
                  { value: 20, label: '20%' },
                  { value: 30, label: '30%' },
                  { value: 50, label: '50%' }
                ]}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                label="最大同時ポジション数"
                type="number"
                value={localSettings.maxConcurrentPositions}
                onChange={(e) => handleChange('maxConcurrentPositions', Number(e.target.value))}
                inputProps={{ min: 1, max: 20 }}
                fullWidth
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                label="スリッページ許容値 (pips)"
                type="number"
                value={localSettings.slippageLimit}
                onChange={(e) => handleChange('slippageLimit', Number(e.target.value))}
                inputProps={{ min: 0, max: 10, step: 0.1 }}
                fullWidth
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* リスク管理設定 */}
      <Card>
        <CardHeader
          title={
            <Box display="flex" alignItems="center" gap={1}>
              <Security />
              <Typography variant="h6">リスク管理</Typography>
            </Box>
          }
        />
        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                デフォルトストップロス: {localSettings.defaultStopLoss}%
              </Typography>
              <Slider
                value={localSettings.defaultStopLoss}
                onChange={(_, value) => handleChange('defaultStopLoss', value)}
                min={0.5}
                max={10}
                step={0.1}
                marks={[
                  { value: 1, label: '1%' },
                  { value: 2, label: '2%' },
                  { value: 5, label: '5%' },
                  { value: 10, label: '10%' }
                ]}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                デフォルトテイクプロフィット: {localSettings.defaultTakeProfit}%
              </Typography>
              <Slider
                value={localSettings.defaultTakeProfit}
                onChange={(_, value) => handleChange('defaultTakeProfit', value)}
                min={1}
                max={20}
                step={0.1}
                marks={[
                  { value: 2, label: '2%' },
                  { value: 4, label: '4%' },
                  { value: 10, label: '10%' },
                  { value: 20, label: '20%' }
                ]}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                緊急停止ロス: {localSettings.emergencyStopLoss}%
              </Typography>
              <Slider
                value={localSettings.emergencyStopLoss}
                onChange={(_, value) => handleChange('emergencyStopLoss', value)}
                min={5}
                max={30}
                step={1}
                marks={[
                  { value: 10, label: '10%' },
                  { value: 15, label: '15%' },
                  { value: 20, label: '20%' },
                  { value: 30, label: '30%' }
                ]}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <Box display="flex" flexDirection="column" gap={2}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={localSettings.enableWeekendClose}
                      onChange={(e) => handleChange('enableWeekendClose', e.target.checked)}
                    />
                  }
                  label="週末前ポジション自動決済"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={localSettings.enableNewsFilter}
                      onChange={(e) => handleChange('enableNewsFilter', e.target.checked)}
                    />
                  }
                  label="重要経済指標時の取引停止"
                />
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* ナンピン設定 */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="h6">ナンピン設定</Typography>
            <Chip
              label={localSettings.enableNanpin ? '有効' : '無効'}
              color={localSettings.enableNanpin ? 'success' : 'default'}
              size="small"
            />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={localSettings.enableNanpin}
                    onChange={(e) => handleChange('enableNanpin', e.target.checked)}
                  />
                }
                label="ナンピン機能を有効にする"
              />
            </Grid>

            {localSettings.enableNanpin && (
              <>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="最大ナンピン回数"
                    type="number"
                    value={localSettings.nanpinMaxCount}
                    onChange={(e) => handleChange('nanpinMaxCount', Number(e.target.value))}
                    inputProps={{ min: 1, max: 10 }}
                    fullWidth
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    label="ナンピン間隔 (pips)"
                    type="number"
                    value={localSettings.nanpinInterval}
                    onChange={(e) => handleChange('nanpinInterval', Number(e.target.value))}
                    inputProps={{ min: 5, max: 100 }}
                    fullWidth
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <FormControl fullWidth>
                    <InputLabel>ロット配分方式</InputLabel>
                    <Select
                      value={localSettings.lotAllocation}
                      onChange={(e) => handleChange('lotAllocation', e.target.value)}
                      label="ロット配分方式"
                    >
                      <MenuItem value="equal">等倍</MenuItem>
                      <MenuItem value="martingale">マーチンゲール法</MenuItem>
                      <MenuItem value="anti_martingale">逆マーチンゲール法</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </>
            )}
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* 取引対象設定 */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box display="flex" alignItems="center" gap={1}>
            <Schedule />
            <Typography variant="h6">取引対象・時間設定</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                優先通貨ペア
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={1}>
                {CURRENCY_PAIRS.map((pair) => (
                  <Chip
                    key={pair}
                    label={CURRENCY_PAIR_LABELS[pair]}
                    color={localSettings.preferredCurrencies.includes(pair) ? 'primary' : 'default'}
                    onClick={() => {
                      const updated = localSettings.preferredCurrencies.includes(pair)
                        ? localSettings.preferredCurrencies.filter(p => p !== pair)
                        : [...localSettings.preferredCurrencies, pair]
                      handleChange('preferredCurrencies', updated)
                    }}
                    variant={localSettings.preferredCurrencies.includes(pair) ? 'filled' : 'outlined'}
                  />
                ))}
              </Box>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                取引時間軸
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={1}>
                {TIMEFRAMES.map((tf) => (
                  <Chip
                    key={tf}
                    label={TIMEFRAME_LABELS[tf]}
                    color={localSettings.tradingTimeframes.includes(tf) ? 'primary' : 'default'}
                    onClick={() => {
                      const updated = localSettings.tradingTimeframes.includes(tf)
                        ? localSettings.tradingTimeframes.filter(t => t !== tf)
                        : [...localSettings.tradingTimeframes, tf]
                      handleChange('tradingTimeframes', updated)
                    }}
                    variant={localSettings.tradingTimeframes.includes(tf) ? 'filled' : 'outlined'}
                  />
                ))}
              </Box>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>
    </Box>
  )
}

export default TradingSettings