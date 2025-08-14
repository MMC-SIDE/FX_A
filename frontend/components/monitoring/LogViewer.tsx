/**
 * ログビューアコンポーネント
 */
'use client'

import React, { useState, useEffect } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box,
  Paper,
  List,
  ListItem,
  Button,
  Chip,
  Switch,
  FormControlLabel,
  Toolbar,
  IconButton,
  Tooltip
} from '@mui/material'
import {
  Search,
  FilterList,
  Refresh,
  Download,
  PlayArrow,
  Pause,
  Clear
} from '@mui/icons-material'
import { useWebSocket, LogEntry } from '@/hooks/useWebSocket'
import { formatDateTime } from '@/lib/utils'

interface LogViewerProps {
  websocketUrl?: string
  autoRefresh?: boolean
  maxLogEntries?: number
}

export function LogViewer({ 
  websocketUrl = 'ws://localhost:8000/ws/monitoring',
  autoRefresh = true,
  maxLogEntries = 500 
}: LogViewerProps) {
  const { logs, isConnected, requestLogs, searchLogs } = useWebSocket(websocketUrl)
  
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedLogType, setSelectedLogType] = useState('all')
  const [selectedLevel, setSelectedLevel] = useState('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const [isLiveMode, setIsLiveMode] = useState(autoRefresh)
  const [displayLogs, setDisplayLogs] = useState<LogEntry[]>([])

  const logTypes = [
    { value: 'all', label: 'すべて' },
    { value: 'trading', label: '取引ログ' },
    { value: 'system', label: 'システムログ' },
    { value: 'error', label: 'エラーログ' },
    { value: 'mt5', label: 'MT5ログ' },
    { value: 'backtest', label: 'バックテストログ' }
  ]

  const logLevels = [
    { value: 'all', label: 'すべて' },
    { value: 'DEBUG', label: 'デバッグ' },
    { value: 'INFO', label: '情報' },
    { value: 'WARNING', label: '警告' },
    { value: 'ERROR', label: 'エラー' },
    { value: 'CRITICAL', label: '緊急' }
  ]

  // ログフィルタリング
  useEffect(() => {
    let filtered = [...logs]

    // レベルフィルタ
    if (selectedLevel !== 'all') {
      filtered = filtered.filter(log => log.level === selectedLevel)
    }

    // ログタイプフィルタ（ファイル名ベース）
    if (selectedLogType !== 'all') {
      filtered = filtered.filter(log => 
        log.log_file.includes(selectedLogType) || 
        log.logger_name.toLowerCase().includes(selectedLogType.toLowerCase())
      )
    }

    // 検索語句フィルタ
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      filtered = filtered.filter(log =>
        log.message.toLowerCase().includes(term) ||
        log.logger_name.toLowerCase().includes(term)
      )
    }

    // 最大件数制限
    filtered = filtered.slice(0, maxLogEntries)

    setDisplayLogs(filtered)
  }, [logs, selectedLevel, selectedLogType, searchTerm, maxLogEntries])

  // 自動スクロール
  useEffect(() => {
    if (autoScroll && displayLogs.length > 0) {
      const logContainer = document.getElementById('log-container')
      if (logContainer) {
        logContainer.scrollTop = logContainer.scrollHeight
      }
    }
  }, [displayLogs, autoScroll])

  const handleRefresh = () => {
    requestLogs(selectedLogType === 'all' ? 'trading' : selectedLogType, 100)
  }

  const handleSearch = () => {
    if (searchTerm) {
      searchLogs(searchTerm, selectedLogType === 'all' ? undefined : selectedLogType)
    }
  }

  const handleClear = () => {
    setSearchTerm('')
    setSelectedLevel('all')
    setSelectedLogType('all')
  }

  const getLogLevelColor = (level: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (level) {
      case 'CRITICAL':
      case 'ERROR':
        return 'error'
      case 'WARNING':
        return 'warning'
      case 'INFO':
        return 'info'
      case 'DEBUG':
        return 'secondary'
      default:
        return 'default'
    }
  }

  const formatLogMessage = (log: LogEntry) => {
    // ログメッセージの長さ制限
    const maxLength = 200
    if (log.message.length > maxLength) {
      return log.message.substring(0, maxLength) + '...'
    }
    return log.message
  }

  const exportLogs = () => {
    const csvContent = displayLogs.map(log => 
      `"${log.timestamp}","${log.level}","${log.logger_name}","${log.message.replace(/"/g, '""')}"`
    ).join('\n')
    
    const header = 'Timestamp,Level,Logger,Message\n'
    const blob = new Blob([header + csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    
    const a = document.createElement('a')
    a.href = url
    a.download = `logs_${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (!isConnected) {
    return (
      <Card>
        <CardHeader title="ログビューア" />
        <CardContent>
          <Typography color="text.secondary">
            WebSocketに接続されていません
          </Typography>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader
        title="ログビューア"
        action={
          <Box display="flex" gap={1} alignItems="center">
            <FormControlLabel
              control={
                <Switch
                  checked={isLiveMode}
                  onChange={(e) => setIsLiveMode(e.target.checked)}
                  size="small"
                />
              }
              label="ライブ"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                  size="small"
                />
              }
              label="自動スクロール"
            />
          </Box>
        }
      />
      
      <CardContent>
        {/* フィルターツールバー */}
        <Toolbar sx={{ px: 0, mb: 2 }}>
          <Box display="flex" gap={2} alignItems="center" flexWrap="wrap" sx={{ width: '100%' }}>
            <TextField
              size="small"
              placeholder="検索..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              InputProps={{
                startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
              }}
              sx={{ minWidth: 200 }}
            />
            
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>ログタイプ</InputLabel>
              <Select
                value={selectedLogType}
                onChange={(e) => setSelectedLogType(e.target.value)}
                label="ログタイプ"
              >
                {logTypes.map((type) => (
                  <MenuItem key={type.value} value={type.value}>
                    {type.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>レベル</InputLabel>
              <Select
                value={selectedLevel}
                onChange={(e) => setSelectedLevel(e.target.value)}
                label="レベル"
              >
                {logLevels.map((level) => (
                  <MenuItem key={level.value} value={level.value}>
                    {level.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <Box display="flex" gap={1}>
              <Tooltip title="検索">
                <IconButton size="small" onClick={handleSearch}>
                  <Search />
                </IconButton>
              </Tooltip>
              <Tooltip title="更新">
                <IconButton size="small" onClick={handleRefresh}>
                  <Refresh />
                </IconButton>
              </Tooltip>
              <Tooltip title="クリア">
                <IconButton size="small" onClick={handleClear}>
                  <Clear />
                </IconButton>
              </Tooltip>
              <Tooltip title="エクスポート">
                <IconButton size="small" onClick={exportLogs}>
                  <Download />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
        </Toolbar>

        {/* ログリスト */}
        <Paper 
          id="log-container"
          sx={{ 
            height: 400, 
            overflow: 'auto', 
            border: '1px solid',
            borderColor: 'divider'
          }}
        >
          <List dense>
            {displayLogs.length === 0 ? (
              <Box textAlign="center" py={4}>
                <Typography color="text.secondary">
                  表示するログがありません
                </Typography>
              </Box>
            ) : (
              displayLogs.map((log, index) => (
                <ListItem
                  key={`${log.timestamp}-${index}`}
                  sx={{
                    borderBottom: '1px solid',
                    borderColor: 'divider',
                    '&:hover': {
                      bgcolor: 'action.hover'
                    }
                  }}
                >
                  <Box sx={{ width: '100%' }}>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <Typography variant="caption" color="text.secondary" sx={{ minWidth: 140 }}>
                        {formatDateTime(log.timestamp, 'MM/dd HH:mm:ss.SSS')}
                      </Typography>
                      <Chip
                        label={log.level}
                        size="small"
                        color={getLogLevelColor(log.level)}
                        sx={{ minWidth: 60 }}
                      />
                      <Typography variant="caption" color="text.secondary" sx={{ minWidth: 100 }}>
                        {log.logger_name}
                      </Typography>
                    </Box>
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        fontFamily: 'monospace',
                        wordBreak: 'break-word',
                        whiteSpace: 'pre-wrap'
                      }}
                    >
                      {formatLogMessage(log)}
                    </Typography>
                    {!log.parsed && (
                      <Typography variant="caption" color="warning.main">
                        パース失敗
                      </Typography>
                    )}
                  </Box>
                </ListItem>
              ))
            )}
          </List>
        </Paper>

        {/* 統計情報 */}
        <Box mt={2} display="flex" justifyContent="between" alignItems="center">
          <Typography variant="caption" color="text.secondary">
            表示中: {displayLogs.length}件 / 総ログ: {logs.length}件
          </Typography>
          <Box display="flex" gap={1}>
            <Chip
              label={`エラー: ${displayLogs.filter(log => log.level === 'ERROR').length}`}
              size="small"
              color="error"
              variant="outlined"
            />
            <Chip
              label={`警告: ${displayLogs.filter(log => log.level === 'WARNING').length}`}
              size="small"
              color="warning"
              variant="outlined"
            />
            <Chip
              label={`情報: ${displayLogs.filter(log => log.level === 'INFO').length}`}
              size="small"
              color="info"
              variant="outlined"
            />
          </Box>
        </Box>
      </CardContent>
    </Card>
  )
}

export default LogViewer