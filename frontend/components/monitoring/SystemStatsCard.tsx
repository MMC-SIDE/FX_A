/**
 * システム統計表示カード
 */
'use client'

import React from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Grid,
  Paper,
  Box,
  LinearProgress,
  Chip
} from '@mui/material'
import {
  Computer,
  Memory,
  Storage,
  NetworkCheck,
  Speed
} from '@mui/icons-material'
import { useWebSocket, SystemStats } from '@/hooks/useWebSocket'
import { formatNumber } from '@/lib/utils'

interface SystemStatsCardProps {
  websocketUrl?: string
}

export function SystemStatsCard({ websocketUrl = 'ws://localhost:8000/ws/monitoring' }: SystemStatsCardProps) {
  const { systemStats, isConnected } = useWebSocket(websocketUrl)

  if (!isConnected) {
    return (
      <Card>
        <CardHeader title="システム状況" />
        <CardContent>
          <Box display="flex" justifyContent="center" alignItems="center" py={4}>
            <Typography color="text.secondary">
              WebSocketに接続中...
            </Typography>
          </Box>
        </CardContent>
      </Card>
    )
  }

  if (!systemStats) {
    return (
      <Card>
        <CardHeader title="システム状況" />
        <CardContent>
          <Box display="flex" justifyContent="center" alignItems="center" py={4}>
            <Typography color="text.secondary">
              データ読み込み中...
            </Typography>
          </Box>
        </CardContent>
      </Card>
    )
  }

  const getColorForPercentage = (percentage: number) => {
    if (percentage >= 90) return 'error'
    if (percentage >= 80) return 'warning'
    if (percentage >= 60) return 'info'
    return 'success'
  }

  const getTextColorForPercentage = (percentage: number) => {
    if (percentage >= 90) return 'error.main'
    if (percentage >= 80) return 'warning.main'
    return 'primary.main'
  }

  return (
    <Card>
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={1}>
            <Computer />
            <Typography variant="h6">システム状況</Typography>
            <Chip
              label={`稼働: ${systemStats.uptime_human}`}
              size="small"
              color="success"
              variant="outlined"
            />
          </Box>
        }
      />
      <CardContent>
        <Grid container spacing={3}>
          {/* CPU使用率 */}
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center', height: '100%' }}>
              <Box display="flex" flexDirection="column" alignItems="center" gap={1}>
                <Speed color="primary" />
                <Typography variant="h6">CPU</Typography>
                <Typography 
                  variant="h4" 
                  fontWeight={600}
                  color={getTextColorForPercentage(systemStats.cpu_percent)}
                >
                  {systemStats.cpu_percent}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={systemStats.cpu_percent}
                  color={getColorForPercentage(systemStats.cpu_percent)}
                  sx={{ width: '100%', height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary">
                  {systemStats.cpu_count}コア
                </Typography>
              </Box>
            </Paper>
          </Grid>
          
          {/* メモリ使用率 */}
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center', height: '100%' }}>
              <Box display="flex" flexDirection="column" alignItems="center" gap={1}>
                <Memory color="primary" />
                <Typography variant="h6">メモリ</Typography>
                <Typography 
                  variant="h4"
                  fontWeight={600}
                  color={getTextColorForPercentage(systemStats.memory_percent)}
                >
                  {systemStats.memory_percent}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={systemStats.memory_percent}
                  color={getColorForPercentage(systemStats.memory_percent)}
                  sx={{ width: '100%', height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary">
                  {formatNumber(systemStats.memory_used_gb, 1)}GB / {formatNumber(systemStats.memory_total_gb, 1)}GB
                </Typography>
              </Box>
            </Paper>
          </Grid>
          
          {/* ディスク使用率 */}
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center', height: '100%' }}>
              <Box display="flex" flexDirection="column" alignItems="center" gap={1}>
                <Storage color="primary" />
                <Typography variant="h6">ディスク</Typography>
                <Typography 
                  variant="h4"
                  fontWeight={600}
                  color={getTextColorForPercentage(systemStats.disk_percent)}
                >
                  {systemStats.disk_percent}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={systemStats.disk_percent}
                  color={getColorForPercentage(systemStats.disk_percent)}
                  sx={{ width: '100%', height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary">
                  {formatNumber(systemStats.disk_free_gb, 1)}GB 空き
                </Typography>
              </Box>
            </Paper>
          </Grid>
          
          {/* ネットワーク */}
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center', height: '100%' }}>
              <Box display="flex" flexDirection="column" alignItems="center" gap={1}>
                <NetworkCheck color="primary" />
                <Typography variant="h6">ネットワーク</Typography>
                <Box>
                  <Typography variant="body2" color="success.main">
                    ↑ {formatNumber(systemStats.network_sent_mb, 1)}MB
                  </Typography>
                  <Typography variant="body2" color="info.main">
                    ↓ {formatNumber(systemStats.network_recv_mb, 1)}MB
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  WebSocket: {systemStats.websocket_connections}接続
                </Typography>
              </Box>
            </Paper>
          </Grid>

          {/* 詳細情報 */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                詳細情報
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    プロセスメモリ
                  </Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {formatNumber(systemStats.process_memory_mb, 1)}MB
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    仮想メモリ
                  </Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {formatNumber(systemStats.process_memory_vms_mb, 1)}MB
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    ネットワークパケット送信
                  </Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {systemStats.network_packets_sent.toLocaleString()}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    ネットワークパケット受信
                  </Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {systemStats.network_packets_recv.toLocaleString()}
                  </Typography>
                </Grid>
              </Grid>
              
              <Box mt={2}>
                <Typography variant="caption" color="text.secondary">
                  最終更新: {new Date(systemStats.timestamp).toLocaleString('ja-JP')}
                </Typography>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  )
}

export default SystemStatsCard