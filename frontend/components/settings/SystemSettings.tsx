/**
 * システム設定コンポーネント
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
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton
} from '@mui/material'
import {
  ExpandMore,
  Save,
  RestoreRounded,
  Computer,
  Storage,
  Notifications,
  Security,
  Delete,
  Add,
  Visibility,
  VisibilityOff
} from '@mui/icons-material'
import { useSettingsSelectors, useSettingsActions } from '@/store/settings'
import { useUISelectors, useUIActions } from '@/store/ui'
import { useNotifications } from '@/store/ui'

export function SystemSettings() {
  const { systemSettings } = useSettingsSelectors()
  const { theme } = useUISelectors()
  const { updateSystemSettings } = useSettingsActions()
  const { setTheme } = useUIActions()
  const { showSuccess, showError } = useNotifications()
  
  const [localSettings, setLocalSettings] = useState(systemSettings)
  const [showApiKey, setShowApiKey] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  const handleChange = (field: string, value: any) => {
    setLocalSettings(prev => ({ ...prev, [field]: value }))
    setHasChanges(true)
  }

  const handleSave = async () => {
    try {
      updateSystemSettings(localSettings)
      setHasChanges(false)
      showSuccess('設定保存', 'システム設定が保存されました')
    } catch (error) {
      showError('保存エラー', '設定の保存に失敗しました')
    }
  }

  const handleReset = () => {
    setLocalSettings(systemSettings)
    setHasChanges(false)
  }

  const handleResetToDefaults = () => {
    const defaultSettings = {
      mt5Server: '',
      mt5Login: '',
      mt5Password: '',
      apiBaseUrl: 'http://localhost:8000',
      apiTimeout: 30000,
      websocketUrl: 'ws://localhost:8000/ws',
      enableWebSocket: true,
      enableLogging: true,
      logLevel: 'INFO' as const,
      logRetentionDays: 90,
      enableNotifications: true,
      notificationEmail: '',
      enableEmailAlerts: false,
      dataRefreshInterval: 5000,
      enableAutoReconnect: true,
      maxReconnectAttempts: 5,
      reconnectInterval: 10000
    }
    setLocalSettings(defaultSettings)
    setHasChanges(true)
  }

  const connectionStatus = {
    mt5: localSettings.mt5Server && localSettings.mt5Login ? 'configured' : 'not_configured',
    api: localSettings.apiBaseUrl ? 'configured' : 'not_configured',
    websocket: localSettings.enableWebSocket && localSettings.websocketUrl ? 'enabled' : 'disabled'
  }

  return (
    <Box display="flex" flexDirection="column" gap={3}>
      {/* アクションボタン */}
      <Box display="flex" justifyContent="space-between" alignItems="center">
        <Typography variant="h6">システム設定</Typography>
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

      {/* 接続状態サマリー */}
      <Card>
        <CardHeader title="接続状態" />
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  MT5接続
                </Typography>
                <Box display="flex" justifyContent="center" mt={1}>
                  <Chip
                    label={connectionStatus.mt5 === 'configured' ? '設定済み' : '未設定'}
                    color={connectionStatus.mt5 === 'configured' ? 'success' : 'error'}
                    size="small"
                  />
                </Box>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  API接続
                </Typography>
                <Box display="flex" justifyContent="center" mt={1}>
                  <Chip
                    label={connectionStatus.api === 'configured' ? '設定済み' : '未設定'}
                    color={connectionStatus.api === 'configured' ? 'success' : 'error'}
                    size="small"
                  />
                </Box>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  WebSocket
                </Typography>
                <Box display="flex" justifyContent="center" mt={1}>
                  <Chip
                    label={connectionStatus.websocket === 'enabled' ? '有効' : '無効'}
                    color={connectionStatus.websocket === 'enabled' ? 'success' : 'default'}
                    size="small"
                  />
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* MT5接続設定 */}
      <Card>
        <CardHeader
          title={
            <Box display="flex" alignItems="center" gap={1}>
              <Computer />
              <Typography variant="h6">MT5接続設定</Typography>
            </Box>
          }
        />
        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                label="サーバー名"
                value={localSettings.mt5Server}
                onChange={(e) => handleChange('mt5Server', e.target.value)}
                placeholder="XMTrading-Real 52"
                fullWidth
                helperText="ブローカーのサーバー名を入力してください"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="ログインID"
                value={localSettings.mt5Login}
                onChange={(e) => handleChange('mt5Login', e.target.value)}
                placeholder="12345678"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="パスワード"
                type={showApiKey ? 'text' : 'password'}
                value={localSettings.mt5Password}
                onChange={(e) => handleChange('mt5Password', e.target.value)}
                placeholder="••••••••"
                fullWidth
                InputProps={{
                  endAdornment: (
                    <IconButton
                      onClick={() => setShowApiKey(!showApiKey)}
                      edge="end"
                    >
                      {showApiKey ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  )
                }}
              />
            </Grid>
          </Grid>
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="body2">
              <strong>注意:</strong> MT5の認証情報は暗号化されて保存されます。
              本番環境では必ず強固なパスワードを使用してください。
            </Typography>
          </Alert>
        </CardContent>
      </Card>

      {/* API・通信設定 */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box display="flex" alignItems="center" gap={1}>
            <Storage />
            <Typography variant="h6">API・通信設定</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                label="APIベースURL"
                value={localSettings.apiBaseUrl}
                onChange={(e) => handleChange('apiBaseUrl', e.target.value)}
                placeholder="http://localhost:8000"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="APIタイムアウト (ms)"
                type="number"
                value={localSettings.apiTimeout}
                onChange={(e) => handleChange('apiTimeout', Number(e.target.value))}
                inputProps={{ min: 5000, max: 120000 }}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="WebSocket URL"
                value={localSettings.websocketUrl}
                onChange={(e) => handleChange('websocketUrl', e.target.value)}
                placeholder="ws://localhost:8000/ws"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="データ更新間隔 (ms)"
                type="number"
                value={localSettings.dataRefreshInterval}
                onChange={(e) => handleChange('dataRefreshInterval', Number(e.target.value))}
                inputProps={{ min: 1000, max: 60000 }}
                fullWidth
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={localSettings.enableWebSocket}
                    onChange={(e) => handleChange('enableWebSocket', e.target.checked)}
                  />
                }
                label="WebSocketによるリアルタイム通信を有効にする"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={localSettings.enableAutoReconnect}
                    onChange={(e) => handleChange('enableAutoReconnect', e.target.checked)}
                  />
                }
                label="自動再接続を有効にする"
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* ログ・監視設定 */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box display="flex" alignItems="center" gap={1}>
            <Security />
            <Typography variant="h6">ログ・監視設定</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={localSettings.enableLogging}
                    onChange={(e) => handleChange('enableLogging', e.target.checked)}
                  />
                }
                label="ログ出力を有効にする"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>ログレベル</InputLabel>
                <Select
                  value={localSettings.logLevel}
                  onChange={(e) => handleChange('logLevel', e.target.value)}
                  label="ログレベル"
                  disabled={!localSettings.enableLogging}
                >
                  <MenuItem value="DEBUG">DEBUG</MenuItem>
                  <MenuItem value="INFO">INFO</MenuItem>
                  <MenuItem value="WARNING">WARNING</MenuItem>
                  <MenuItem value="ERROR">ERROR</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="ログ保存期間 (日)"
                type="number"
                value={localSettings.logRetentionDays}
                onChange={(e) => handleChange('logRetentionDays', Number(e.target.value))}
                inputProps={{ min: 7, max: 365 }}
                disabled={!localSettings.enableLogging}
                fullWidth
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* 通知設定 */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box display="flex" alignItems="center" gap={1}>
            <Notifications />
            <Typography variant="h6">通知設定</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={localSettings.enableNotifications}
                    onChange={(e) => handleChange('enableNotifications', e.target.checked)}
                  />
                }
                label="プッシュ通知を有効にする"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={localSettings.enableEmailAlerts}
                    onChange={(e) => handleChange('enableEmailAlerts', e.target.checked)}
                  />
                }
                label="Eメール通知を有効にする"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="通知用メールアドレス"
                type="email"
                value={localSettings.notificationEmail}
                onChange={(e) => handleChange('notificationEmail', e.target.value)}
                disabled={!localSettings.enableEmailAlerts}
                placeholder="your-email@example.com"
                fullWidth
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* UI設定 */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">UI設定</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>テーマ</InputLabel>
                <Select
                  value={theme}
                  onChange={(e) => setTheme(e.target.value as any)}
                  label="テーマ"
                >
                  <MenuItem value="light">ライト</MenuItem>
                  <MenuItem value="dark">ダーク</MenuItem>
                  <MenuItem value="system">システム設定に従う</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>
    </Box>
  )
}

export default SystemSettings