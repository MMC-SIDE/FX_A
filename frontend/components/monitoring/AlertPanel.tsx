/**
 * アラートパネルコンポーネント
 */
'use client'

import React, { useState } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Chip,
  Box,
  Button,
  Alert as MUIAlert,
  Tabs,
  Tab,
  Badge,
  Tooltip,
  Collapse,
  Paper
} from '@mui/material'
import {
  Warning,
  Error,
  Info,
  NotificationImportant,
  Check,
  Clear,
  ExpandMore,
  ExpandLess,
  ClearAll,
  Refresh
} from '@mui/icons-material'
import { useWebSocket, Alert } from '@/hooks/useWebSocket'
import { formatDateTime } from '@/lib/utils'

interface AlertPanelProps {
  websocketUrl?: string
  maxDisplayAlerts?: number
}

export function AlertPanel({ 
  websocketUrl = 'ws://localhost:8000/ws/monitoring',
  maxDisplayAlerts = 50 
}: AlertPanelProps) {
  const { alerts, isConnected, acknowledgeAlert, dismissAlert } = useWebSocket(websocketUrl)
  const [activeTab, setActiveTab] = useState(0)
  const [expandedAlert, setExpandedAlert] = useState<string | null>(null)

  const getAlertIcon = (level: string) => {
    switch (level) {
      case 'critical':
        return <NotificationImportant color="error" />
      case 'error':
        return <Error color="error" />
      case 'warning':
        return <Warning color="warning" />
      case 'info':
      default:
        return <Info color="info" />
    }
  }

  const getAlertColor = (level: string): 'error' | 'warning' | 'info' | 'success' => {
    switch (level) {
      case 'critical':
      case 'error':
        return 'error'
      case 'warning':
        return 'warning'
      case 'info':
        return 'info'
      default:
        return 'info'
    }
  }

  const getAlertSeverityOrder = (level: string): number => {
    switch (level) {
      case 'critical': return 4
      case 'error': return 3
      case 'warning': return 2
      case 'info': return 1
      default: return 0
    }
  }

  // フィルタリング
  const activeAlerts = alerts.filter(alert => !alert.acknowledged)
  const acknowledgedAlerts = alerts.filter(alert => alert.acknowledged)
  const criticalAlerts = activeAlerts.filter(alert => alert.level === 'critical')
  const errorAlerts = activeAlerts.filter(alert => alert.level === 'error')
  const warningAlerts = activeAlerts.filter(alert => alert.level === 'warning')

  // ソート（重要度順、時間順）
  const sortedActiveAlerts = [...activeAlerts]
    .sort((a, b) => {
      const severityDiff = getAlertSeverityOrder(b.level) - getAlertSeverityOrder(a.level)
      if (severityDiff !== 0) return severityDiff
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    })
    .slice(0, maxDisplayAlerts)

  const handleAcknowledge = async (alertId: string) => {
    await acknowledgeAlert(alertId)
  }

  const handleDismiss = async (alertId: string) => {
    await dismissAlert(alertId)
  }

  const handleExpandAlert = (alertId: string) => {
    setExpandedAlert(expandedAlert === alertId ? null : alertId)
  }

  const renderAlert = (alert: Alert) => (
    <ListItem
      key={alert.id}
      sx={{
        border: '1px solid',
        borderColor: `${getAlertColor(alert.level)}.light`,
        borderRadius: 1,
        mb: 1,
        bgcolor: alert.acknowledged ? 'grey.50' : 'background.paper'
      }}
    >
      <ListItemIcon>
        {getAlertIcon(alert.level)}
      </ListItemIcon>
      
      <ListItemText
        primary={
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="body2" fontWeight={600}>
              {alert.message}
            </Typography>
            <Chip
              label={alert.level.toUpperCase()}
              size="small"
              color={getAlertColor(alert.level)}
            />
            {alert.acknowledged && (
              <Chip
                label="確認済み"
                size="small"
                color="success"
                variant="outlined"
              />
            )}
          </Box>
        }
        secondary={
          <Box>
            <Typography variant="caption" color="text.secondary">
              {formatDateTime(alert.timestamp, 'MM/dd HH:mm:ss')} - {alert.source}
            </Typography>
            {alert.value !== undefined && alert.threshold !== undefined && (
              <Typography variant="caption" display="block">
                現在値: {alert.value} / 閾値: {alert.threshold}
              </Typography>
            )}
            
            {/* 詳細情報の展開 */}
            {alert.details && Object.keys(alert.details).length > 0 && (
              <Collapse in={expandedAlert === alert.id}>
                <Paper sx={{ mt: 1, p: 1, bgcolor: 'grey.50' }}>
                  <Typography variant="caption" fontWeight={600}>
                    詳細情報:
                  </Typography>
                  <pre style={{ 
                    fontSize: '0.75rem', 
                    margin: 0, 
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}>
                    {JSON.stringify(alert.details, null, 2)}
                  </pre>
                </Paper>
              </Collapse>
            )}
          </Box>
        }
      />
      
      <Box display="flex" flexDirection="column" gap={0.5}>
        {!alert.acknowledged && (
          <Tooltip title="確認済みにマーク">
            <IconButton 
              size="small"
              onClick={() => handleAcknowledge(alert.id)}
              color="success"
            >
              <Check />
            </IconButton>
          </Tooltip>
        )}
        
        <Tooltip title="削除">
          <IconButton 
            size="small"
            onClick={() => handleDismiss(alert.id)}
            color="error"
          >
            <Clear />
          </IconButton>
        </Tooltip>
        
        {alert.details && Object.keys(alert.details).length > 0 && (
          <Tooltip title="詳細を表示">
            <IconButton 
              size="small"
              onClick={() => handleExpandAlert(alert.id)}
            >
              {expandedAlert === alert.id ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </Tooltip>
        )}
      </Box>
    </ListItem>
  )

  if (!isConnected) {
    return (
      <Card>
        <CardHeader title="アラート" />
        <CardContent>
          <MUIAlert severity="warning">
            WebSocketに接続されていません
          </MUIAlert>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader
        title={
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Typography variant="h6">アラート</Typography>
            <Box display="flex" gap={1}>
              <Badge badgeContent={criticalAlerts.length} color="error">
                <Chip
                  label={`緊急: ${criticalAlerts.length}`}
                  size="small"
                  color="error"
                />
              </Badge>
              <Badge badgeContent={errorAlerts.length} color="error">
                <Chip
                  label={`エラー: ${errorAlerts.length}`}
                  size="small"
                  color="error"
                  variant="outlined"
                />
              </Badge>
              <Badge badgeContent={warningAlerts.length} color="warning">
                <Chip
                  label={`警告: ${warningAlerts.length}`}
                  size="small"
                  color="warning"
                  variant="outlined"
                />
              </Badge>
            </Box>
          </Box>
        }
        action={
          <Box display="flex" gap={1}>
            <Tooltip title="全て確認済みにマーク">
              <IconButton 
                size="small" 
                disabled={activeAlerts.length === 0}
                onClick={() => {
                  activeAlerts.forEach(alert => handleAcknowledge(alert.id))
                }}
              >
                <ClearAll />
              </IconButton>
            </Tooltip>
            <Tooltip title="更新">
              <IconButton size="small">
                <Refresh />
              </IconButton>
            </Tooltip>
          </Box>
        }
      />
      
      <CardContent>
        {/* タブ */}
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)} sx={{ mb: 2 }}>
          <Tab 
            label={
              <Badge badgeContent={activeAlerts.length} color="error">
                アクティブ
              </Badge>
            } 
          />
          <Tab 
            label={
              <Badge badgeContent={acknowledgedAlerts.length} color="success">
                確認済み
              </Badge>
            } 
          />
        </Tabs>

        {/* アラート一覧 */}
        <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
          {activeTab === 0 && (
            <List>
              {sortedActiveAlerts.length === 0 ? (
                <Box textAlign="center" py={4}>
                  <Typography color="text.secondary">
                    アクティブなアラートはありません
                  </Typography>
                </Box>
              ) : (
                sortedActiveAlerts.map(renderAlert)
              )}
            </List>
          )}

          {activeTab === 1 && (
            <List>
              {acknowledgedAlerts.length === 0 ? (
                <Box textAlign="center" py={4}>
                  <Typography color="text.secondary">
                    確認済みアラートはありません
                  </Typography>
                </Box>
              ) : (
                acknowledgedAlerts
                  .slice(0, maxDisplayAlerts)
                  .map(renderAlert)
              )}
            </List>
          )}
        </Box>

        {/* 統計情報 */}
        <Box mt={2} pt={2} borderTop="1px solid" borderColor="divider">
          <Typography variant="caption" color="text.secondary">
            合計: {alerts.length}件 | 
            アクティブ: {activeAlerts.length}件 | 
            確認済み: {acknowledgedAlerts.length}件
          </Typography>
        </Box>
      </CardContent>
    </Card>
  )
}

export default AlertPanel