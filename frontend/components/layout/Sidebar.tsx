/**
 * サイドバーコンポーネント
 */
'use client'

import React from 'react'
import { usePathname, useRouter } from 'next/navigation'
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Divider,
  IconButton,
  Typography,
  Box,
  Collapse,
  Chip
} from '@mui/material'
import {
  Dashboard,
  TrendingUp,
  Settings,
  Assessment,
  Timeline,
  Security,
  ExpandLess,
  ExpandMore,
  ChevronLeft,
  ChevronRight,
  ShowChart,
  AccountBalance,
  Notifications,
  Help
} from '@mui/icons-material'
import { useUISelectors, useUIActions } from '@/store/ui'
import { useTradingSelectors } from '@/store/trading'
import { SIDEBAR_WIDTH } from '@/lib/constants'

interface MenuItem {
  id: string
  label: string
  icon: React.ReactNode
  path?: string
  children?: MenuItem[]
  badge?: string | number
  disabled?: boolean
}

const menuItems: MenuItem[] = [
  {
    id: 'dashboard',
    label: 'ダッシュボード',
    icon: <Dashboard />,
    path: '/dashboard'
  },
  {
    id: 'backtest',
    label: 'バックテスト',
    icon: <Assessment />,
    path: '/backtest'
  },
  {
    id: 'monitoring',
    label: 'リアルタイム監視',
    icon: <Security />,
    path: '/monitoring'
  },
  {
    id: 'settings',
    label: '設定',
    icon: <Settings />,
    path: '/settings'
  }
]

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { sidebarOpen, sidebarCollapsed } = useUISelectors()
  const { setSidebarOpen, toggleSidebarCollapsed } = useUIActions()
  const { isActive, totalPositions } = useTradingSelectors()
  
  const [expandedItems, setExpandedItems] = React.useState<string[]>(['trading'])

  const handleItemClick = (item: MenuItem) => {
    if (item.path) {
      router.push(item.path)
    } else if (item.children) {
      toggleExpanded(item.id)
    }
  }

  const toggleExpanded = (itemId: string) => {
    setExpandedItems(prev =>
      prev.includes(itemId)
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    )
  }

  const renderMenuItem = (item: MenuItem, depth = 0) => {
    const isSelected = pathname === item.path
    const isExpanded = expandedItems.includes(item.id)
    const hasChildren = item.children && item.children.length > 0

    let badge = item.badge
    if (item.id === 'positions' && totalPositions > 0) {
      badge = totalPositions
    }

    return (
      <React.Fragment key={item.id}>
        <ListItem disablePadding>
          <ListItemButton
            selected={isSelected}
            onClick={() => handleItemClick(item)}
            disabled={item.disabled}
            sx={{
              pl: 2 + depth * 2,
              minHeight: 48,
              borderRadius: 1,
              mx: 1,
              '&.Mui-selected': {
                backgroundColor: 'primary.main',
                color: 'primary.contrastText',
                '&:hover': {
                  backgroundColor: 'primary.dark'
                },
                '& .MuiListItemIcon-root': {
                  color: 'primary.contrastText'
                }
              }
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: sidebarCollapsed ? 0 : 40,
                mr: sidebarCollapsed ? 0 : 1
              }}
            >
              {item.icon}
            </ListItemIcon>
            
            {!sidebarCollapsed && (
              <>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{
                    fontSize: '0.875rem',
                    fontWeight: isSelected ? 600 : 400
                  }}
                />
                
                {badge && (
                  <Chip
                    label={badge}
                    size="small"
                    color={isSelected ? 'secondary' : 'default'}
                    sx={{ ml: 1, height: 20, fontSize: '0.75rem' }}
                  />
                )}
                
                {hasChildren && (
                  <IconButton size="small" edge="end">
                    {isExpanded ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                )}
              </>
            )}
          </ListItemButton>
        </ListItem>

        {hasChildren && !sidebarCollapsed && (
          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {item.children!.map(child => renderMenuItem(child, depth + 1))}
            </List>
          </Collapse>
        )}
      </React.Fragment>
    )
  }

  const drawerContent = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* ヘッダー */}
      <Toolbar
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: sidebarCollapsed ? 'center' : 'space-between',
          px: 2
        }}
      >
        {!sidebarCollapsed && (
          <Typography variant="h6" noWrap component="div" fontWeight={600}>
            FX Trading
          </Typography>
        )}
        <IconButton onClick={toggleSidebarCollapsed} size="small">
          {sidebarCollapsed ? <ChevronRight /> : <ChevronLeft />}
        </IconButton>
      </Toolbar>

      <Divider />

      {/* ステータス表示 */}
      {!sidebarCollapsed && (
        <Box sx={{ px: 2, py: 1 }}>
          <Chip
            label={isActive ? '取引中' : '停止中'}
            color={isActive ? 'success' : 'default'}
            size="small"
            sx={{ width: '100%' }}
          />
        </Box>
      )}

      <Divider />

      {/* メニュー項目 */}
      <Box sx={{ flex: 1, overflow: 'auto', py: 1 }}>
        <List>
          {menuItems.map(item => renderMenuItem(item))}
        </List>
      </Box>

      <Divider />

      {/* フッター */}
      <Box sx={{ p: 2 }}>
        {!sidebarCollapsed ? (
          <ListItemButton
            onClick={() => router.push('/help')}
            sx={{ borderRadius: 1 }}
          >
            <ListItemIcon>
              <Help />
            </ListItemIcon>
            <ListItemText
              primary="ヘルプ"
              primaryTypographyProps={{ fontSize: '0.875rem' }}
            />
          </ListItemButton>
        ) : (
          <IconButton onClick={() => router.push('/help')} size="small">
            <Help />
          </IconButton>
        )}
      </Box>
    </Box>
  )

  return (
    <Drawer
      variant="persistent"
      anchor="left"
      open={sidebarOpen}
      sx={{
        width: sidebarCollapsed ? 64 : SIDEBAR_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: sidebarCollapsed ? 64 : SIDEBAR_WIDTH,
          boxSizing: 'border-box',
          transition: theme => theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen
          })
        }
      }}
    >
      {drawerContent}
    </Drawer>
  )
}

export default Sidebar