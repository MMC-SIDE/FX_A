/**
 * 監視ページ
 */
'use client'

import React from 'react'
import {
  Box,
  Container,
  Typography,
  Grid
} from '@mui/material'
import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import SystemStatsCard from '@/components/monitoring/SystemStatsCard'
import AlertPanel from '@/components/monitoring/AlertPanel'
import LogViewer from '@/components/monitoring/LogViewer'
import { useUISelectors } from '@/store/ui'
import { SIDEBAR_WIDTH, HEADER_HEIGHT } from '@/lib/constants'

export default function MonitoringPage() {
  const { sidebarOpen, sidebarCollapsed } = useUISelectors()

  const sidebarWidth = sidebarOpen ? (sidebarCollapsed ? 64 : SIDEBAR_WIDTH) : 0

  return (
    <Box sx={{ display: 'flex' }}>
      {/* サイドバー */}
      <Sidebar />
      
      {/* メインコンテンツ */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: `calc(100% - ${sidebarWidth}px)`,
          ml: `${sidebarWidth}px`,
          transition: theme => theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen
          })
        }}
      >
        {/* ヘッダー */}
        <Header />
        
        {/* ページコンテンツ */}
        <Container 
          maxWidth={false} 
          sx={{ 
            mt: `${HEADER_HEIGHT + 16}px`, 
            mb: 3,
            px: 3
          }}
        >
          {/* ページタイトル */}
          <Box mb={3}>
            <Typography variant="h4" fontWeight={600} gutterBottom>
              リアルタイム監視
            </Typography>
            <Typography variant="body1" color="text.secondary">
              システム状況とアラートのリアルタイム監視
            </Typography>
          </Box>

          <Grid container spacing={3}>
            {/* システム統計 */}
            <Grid item xs={12}>
              <SystemStatsCard />
            </Grid>

            {/* アラートパネル */}
            <Grid item xs={12} md={6}>
              <AlertPanel />
            </Grid>

            {/* ログビューア */}
            <Grid item xs={12} md={6}>
              <LogViewer />
            </Grid>
          </Grid>
        </Container>
      </Box>
    </Box>
  )
}