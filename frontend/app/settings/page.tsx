/**
 * 設定ページ
 */
'use client'

import React, { useState } from 'react'
import {
  Box,
  Container,
  Typography,
  Tab,
  Tabs,
  Card,
  Alert
} from '@mui/material'
import {
  TrendingUp,
  Computer,
  Security,
  Notifications,
  Palette
} from '@mui/icons-material'
import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import TradingSettings from '@/components/settings/TradingSettings'
import SystemSettings from '@/components/settings/SystemSettings'
import { useUISelectors } from '@/store/ui'
import { SIDEBAR_WIDTH, HEADER_HEIGHT } from '@/lib/constants'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
    >
      {value === index && (
        <Box sx={{ py: 3 }}>
          {children}
        </Box>
      )}
    </div>
  )
}

function a11yProps(index: number) {
  return {
    id: `settings-tab-${index}`,
    'aria-controls': `settings-tabpanel-${index}`,
  }
}

export default function SettingsPage() {
  const { sidebarOpen, sidebarCollapsed } = useUISelectors()
  const [activeTab, setActiveTab] = useState(0)

  const sidebarWidth = sidebarOpen ? (sidebarCollapsed ? 64 : SIDEBAR_WIDTH) : 0

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue)
  }

  const tabs = [
    {
      label: '取引設定',
      icon: <TrendingUp />,
      component: <TradingSettings />
    },
    {
      label: 'システム設定',
      icon: <Computer />,
      component: <SystemSettings />
    }
  ]

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
              設定
            </Typography>
            <Typography variant="body1" color="text.secondary">
              取引設定とシステム設定の管理
            </Typography>
          </Box>

          {/* 注意事項 */}
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2">
              設定を変更した場合は、必ず「保存」ボタンをクリックして設定を保存してください。
              一部の設定はシステムの再起動が必要な場合があります。
            </Typography>
          </Alert>

          {/* タブ付き設定画面 */}
          <Card>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs 
                value={activeTab} 
                onChange={handleTabChange} 
                variant="scrollable"
                scrollButtons="auto"
              >
                {tabs.map((tab, index) => (
                  <Tab
                    key={index}
                    label={tab.label}
                    icon={tab.icon}
                    iconPosition="start"
                    {...a11yProps(index)}
                    sx={{
                      minHeight: 64,
                      textTransform: 'none',
                      fontSize: '1rem',
                      fontWeight: 500
                    }}
                  />
                ))}
              </Tabs>
            </Box>

            {/* タブパネル */}
            {tabs.map((tab, index) => (
              <TabPanel key={index} value={activeTab} index={index}>
                <Container maxWidth="lg" sx={{ px: 3 }}>
                  {tab.component}
                </Container>
              </TabPanel>
            ))}
          </Card>
        </Container>
      </Box>
    </Box>
  )
}