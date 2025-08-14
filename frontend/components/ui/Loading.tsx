/**
 * 再利用可能なLoadingコンポーネント
 */
import React from 'react'
import { Box, CircularProgress, Typography, Skeleton } from '@mui/material'
import { cn } from '@/lib/utils'

interface LoadingProps {
  size?: number | 'small' | 'medium' | 'large'
  message?: string
  variant?: 'circular' | 'linear' | 'skeleton'
  fullHeight?: boolean
  className?: string
}

export function Loading({
  size = 'medium',
  message = '読み込み中...',
  variant = 'circular',
  fullHeight = false,
  className
}: LoadingProps) {
  const containerClass = cn(
    'flex flex-col items-center justify-center gap-2',
    fullHeight ? 'min-h-screen' : 'min-h-[200px]',
    className
  )

  if (variant === 'skeleton') {
    return (
      <Box className={containerClass}>
        <Skeleton variant="rectangular" width="100%" height={200} />
        <Skeleton variant="text" width="60%" />
        <Skeleton variant="text" width="40%" />
      </Box>
    )
  }

  const sizeMap = {
    small: 24,
    medium: 40,
    large: 60
  }

  const actualSize = typeof size === 'string' ? sizeMap[size] : size

  return (
    <Box className={containerClass}>
      <CircularProgress size={actualSize} />
      {message && (
        <Typography variant="body2" color="text.secondary">
          {message}
        </Typography>
      )}
    </Box>
  )
}

interface LoadingOverlayProps {
  loading: boolean
  children: React.ReactNode
  message?: string
}

export function LoadingOverlay({
  loading,
  children,
  message = '読み込み中...'
}: LoadingOverlayProps) {
  return (
    <Box position="relative">
      {children}
      {loading && (
        <Box
          position="absolute"
          top={0}
          left={0}
          right={0}
          bottom={0}
          display="flex"
          alignItems="center"
          justifyContent="center"
          bgcolor="rgba(255, 255, 255, 0.8)"
          zIndex={1000}
        >
          <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
            <CircularProgress />
            <Typography variant="body2" color="text.secondary">
              {message}
            </Typography>
          </Box>
        </Box>
      )}
    </Box>
  )
}

interface ProgressLoadingProps {
  progress: number
  message?: string
  showPercentage?: boolean
}

export function ProgressLoading({
  progress,
  message = '処理中...',
  showPercentage = true
}: ProgressLoadingProps) {
  return (
    <Box display="flex" flexDirection="column" alignItems="center" gap={2} p={3}>
      <Box position="relative" display="inline-flex">
        <CircularProgress
          variant="determinate"
          value={progress}
          size={60}
          thickness={4}
        />
        {showPercentage && (
          <Box
            position="absolute"
            top={0}
            left={0}
            bottom={0}
            right={0}
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <Typography variant="caption" component="div" color="text.secondary">
              {`${Math.round(progress)}%`}
            </Typography>
          </Box>
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" textAlign="center">
        {message}
      </Typography>
    </Box>
  )
}

interface TableLoadingProps {
  rows?: number
  columns?: number
}

export function TableLoading({ rows = 5, columns = 4 }: TableLoadingProps) {
  return (
    <Box>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <Box key={rowIndex} display="flex" gap={2} mb={1}>
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton
              key={colIndex}
              variant="text"
              height={40}
              sx={{ flex: 1 }}
            />
          ))}
        </Box>
      ))}
    </Box>
  )
}

interface ChartLoadingProps {
  height?: number
}

export function ChartLoading({ height = 300 }: ChartLoadingProps) {
  return (
    <Box display="flex" flexDirection="column" gap={2}>
      <Skeleton variant="rectangular" width="100%" height={height} />
      <Box display="flex" gap={2} justifyContent="center">
        <Skeleton variant="text" width={60} />
        <Skeleton variant="text" width={60} />
        <Skeleton variant="text" width={60} />
      </Box>
    </Box>
  )
}

export default Loading