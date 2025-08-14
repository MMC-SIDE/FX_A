/**
 * ヘッダーコンポーネント
 */
'use client'

import React from 'react'
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Badge,
  Menu,
  MenuItem,
  Box,
  Chip,
  Avatar,
  Divider,
  ListItemIcon,
  ListItemText
} from '@mui/material'
import {
  Menu as MenuIcon,
  Notifications,
  AccountCircle,
  Settings,
  Logout,
  DarkMode,
  LightMode,
  Refresh,
  Warning,
  CheckCircle,
  Error
} from '@mui/icons-material'
import { useUISelectors, useUIActions } from '@/store/ui'
import { useTradingSelectors } from '@/store/trading'
import { useNotifications } from '@/store/ui'
import { formatCurrency, formatDateTime } from '@/lib/utils'
import { HEADER_HEIGHT, SIDEBAR_WIDTH } from '@/lib/constants'

export function Header() {
  const { sidebarOpen, sidebarCollapsed, theme } = useUISelectors()
  const { setSidebarOpen, setTheme } = useUIActions()
  const { 
    isActive, 
    isConnected, 
    totalProfit, 
    totalPositions, 
    lastUpdate,
    tradingStatus 
  } = useTradingSelectors()
  const { notifications } = useNotifications()

  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null)
  const [notificationAnchor, setNotificationAnchor] = React.useState<null | HTMLElement>(null)

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleNotificationMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setNotificationAnchor(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
    setNotificationAnchor(null)
  }

  const handleThemeToggle = () => {
    setTheme(theme === 'light' ? 'dark' : 'light')
    handleMenuClose()
  }

  const unreadNotifications = notifications.filter(n => !n.persistent).length

  const getStatusColor = () => {
    if (!isConnected) return 'error'
    if (isActive) return 'success'
    return 'default'
  }

  const getStatusText = () => {
    if (!isConnected) return '接続エラー'
    if (isActive) return '取引中'
    return '停止中'
  }

  const sidebarWidth = sidebarOpen ? (sidebarCollapsed ? 64 : SIDEBAR_WIDTH) : 0

  return (
    <AppBar
      position="fixed"
      sx={{
        width: `calc(100% - ${sidebarWidth}px)`,
        ml: `${sidebarWidth}px`,
        transition: theme => theme.transitions.create(['width', 'margin'], {
          easing: theme.transitions.easing.sharp,
          duration: theme.transitions.duration.leavingScreen
        }),
        height: HEADER_HEIGHT
      }}
    >
      <Toolbar>
        {/* サイドバートグル */}
        <IconButton
          color="inherit"
          aria-label="サイドバーを開く"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          edge="start"
        >
          <MenuIcon />
        </IconButton>

        {/* タイトル */}
        <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
          FX 自動売買システム
        </Typography>

        {/* ステータス情報 */}
        <Box display="flex" alignItems="center" gap={2} mr={2}>
          {/* 接続・取引状態 */}
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={getStatusText()}
              color={getStatusColor()}
              size="small"
              icon={
                !isConnected ? <Error /> : 
                isActive ? <CheckCircle /> : 
                <Warning />
              }
            />
            {isActive && totalPositions > 0 && (
              <Chip
                label={`${totalPositions}ポジション`}
                size="small"
                variant="outlined"
                color="primary"
              />
            )}
          </Box>

          {/* 損益表示 */}
          {tradingStatus && (
            <Box display="flex" alignItems="center" gap={1}>
              <Typography variant="body2" color="inherit">
                損益:
              </Typography>
              <Typography
                variant="body2"
                color={totalProfit >= 0 ? 'success.light' : 'error.light'}
                fontWeight={600}
              >
                {formatCurrency(totalProfit)}
              </Typography>
            </Box>
          )}

          {/* 最終更新時刻 */}
          {lastUpdate && (
            <Typography variant="caption" color="inherit" sx={{ opacity: 0.8 }}>
              最終更新: {formatDateTime(lastUpdate, 'HH:mm:ss')}
            </Typography>
          )}
        </Box>

        {/* 通知アイコン */}
        <IconButton
          size="large"
          aria-label={`${unreadNotifications}件の新しい通知`}
          color="inherit"
          onClick={handleNotificationMenuOpen}
        >
          <Badge badgeContent={unreadNotifications} color="error">
            <Notifications />
          </Badge>
        </IconButton>

        {/* プロフィールメニュー */}
        <IconButton
          size="large"
          edge="end"
          aria-label="アカウントメニュー"
          aria-controls="primary-search-account-menu"
          aria-haspopup="true"
          onClick={handleProfileMenuOpen}
          color="inherit"
        >
          <AccountCircle />
        </IconButton>

        {/* プロフィールメニュー */}
        <Menu
          id="primary-search-account-menu"
          anchorEl={anchorEl}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'right'
          }}
          keepMounted
          transformOrigin={{
            vertical: 'top',
            horizontal: 'right'
          }}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
        >
          <MenuItem disabled>
            <Avatar sx={{ width: 32, height: 32, mr: 2 }}>
              U
            </Avatar>
            <Box>
              <Typography variant="body2" fontWeight={600}>
                ユーザー
              </Typography>
              <Typography variant="caption" color="text.secondary">
                user@example.com
              </Typography>
            </Box>
          </MenuItem>
          
          <Divider />
          
          <MenuItem onClick={() => { /* 設定ページに移動 */ handleMenuClose() }}>
            <ListItemIcon>
              <Settings fontSize="small" />
            </ListItemIcon>
            <ListItemText>設定</ListItemText>
          </MenuItem>
          
          <MenuItem onClick={handleThemeToggle}>
            <ListItemIcon>
              {theme === 'light' ? <DarkMode fontSize="small" /> : <LightMode fontSize="small" />}
            </ListItemIcon>
            <ListItemText>
              {theme === 'light' ? 'ダークモード' : 'ライトモード'}
            </ListItemText>
          </MenuItem>
          
          <MenuItem onClick={() => { /* データ更新 */ handleMenuClose() }}>
            <ListItemIcon>
              <Refresh fontSize="small" />
            </ListItemIcon>
            <ListItemText>データ更新</ListItemText>
          </MenuItem>
          
          <Divider />
          
          <MenuItem onClick={() => { /* ログアウト */ handleMenuClose() }}>
            <ListItemIcon>
              <Logout fontSize="small" />
            </ListItemIcon>
            <ListItemText>ログアウト</ListItemText>
          </MenuItem>
        </Menu>

        {/* 通知メニュー */}
        <Menu
          id="notification-menu"
          anchorEl={notificationAnchor}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'right'
          }}
          keepMounted
          transformOrigin={{
            vertical: 'top',
            horizontal: 'right'
          }}
          open={Boolean(notificationAnchor)}
          onClose={handleMenuClose}
          PaperProps={{
            sx: { width: 320, maxHeight: 400 }
          }}
        >
          <Box sx={{ px: 2, py: 1 }}>
            <Typography variant="h6" fontWeight={600}>
              通知
            </Typography>
          </Box>
          
          <Divider />
          
          {notifications.length === 0 ? (
            <MenuItem disabled>
              <Typography variant="body2" color="text.secondary">
                新しい通知はありません
              </Typography>
            </MenuItem>
          ) : (
            notifications.slice(0, 5).map((notification) => (
              <MenuItem key={notification.id} onClick={handleMenuClose}>
                <Box sx={{ width: '100%' }}>
                  <Box display="flex" alignItems="center" justifyContent="space-between">
                    <Typography variant="body2" fontWeight={600}>
                      {notification.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatDateTime(notification.timestamp, 'HH:mm')}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {notification.message}
                  </Typography>
                </Box>
              </MenuItem>
            ))
          )}
          
          {notifications.length > 5 && (
            <>
              <Divider />
              <MenuItem onClick={handleMenuClose}>
                <Typography variant="body2" color="primary">
                  すべての通知を表示
                </Typography>
              </MenuItem>
            </>
          )}
        </Menu>
      </Toolbar>
    </AppBar>
  )
}

export default Header