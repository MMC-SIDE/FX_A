/**
 * 再利用可能なCardコンポーネント
 */
import React from 'react'
import { 
  Card as MuiCard, 
  CardContent, 
  CardHeader, 
  CardActions,
  Typography,
  IconButton,
  Box
} from '@mui/material'
import { MoreVert } from '@mui/icons-material'
import { cn } from '@/lib/utils'

interface CardProps {
  children: React.ReactNode
  title?: string
  subtitle?: string
  action?: React.ReactNode
  onMenuClick?: () => void
  className?: string
  elevation?: number
  loading?: boolean
}

export function Card({
  children,
  title,
  subtitle,
  action,
  onMenuClick,
  className,
  elevation = 1,
  loading = false
}: CardProps) {
  return (
    <MuiCard 
      elevation={elevation} 
      className={cn('relative', className)}
    >
      {(title || subtitle || action || onMenuClick) && (
        <CardHeader
          title={title && (
            <Typography variant="h6" component="h2">
              {title}
            </Typography>
          )}
          subheader={subtitle && (
            <Typography variant="body2" color="text.secondary">
              {subtitle}
            </Typography>
          )}
          action={
            <Box display="flex" alignItems="center" gap={1}>
              {action}
              {onMenuClick && (
                <IconButton
                  size="small"
                  onClick={onMenuClick}
                  aria-label="メニュー"
                >
                  <MoreVert />
                </IconButton>
              )}
            </Box>
          }
        />
      )}
      <CardContent>
        {loading ? (
          <Box 
            display="flex" 
            justifyContent="center" 
            alignItems="center" 
            minHeight={100}
          >
            <div className="animate-pulse">読み込み中...</div>
          </Box>
        ) : (
          children
        )}
      </CardContent>
    </MuiCard>
  )
}

interface CardWithActionsProps extends CardProps {
  actions?: React.ReactNode
}

export function CardWithActions({
  actions,
  children,
  ...props
}: CardWithActionsProps) {
  return (
    <Card {...props}>
      {children}
      {actions && (
        <CardActions>
          {actions}
        </CardActions>
      )}
    </Card>
  )
}

export default Card