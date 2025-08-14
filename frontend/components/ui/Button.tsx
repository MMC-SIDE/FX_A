/**
 * 再利用可能なButtonコンポーネント
 */
import React from 'react'
import { Button as MuiButton, ButtonProps as MuiButtonProps, CircularProgress } from '@mui/material'
import { cn } from '@/lib/utils'

interface ButtonProps extends Omit<MuiButtonProps, 'variant'> {
  variant?: 'contained' | 'outlined' | 'text'
  size?: 'small' | 'medium' | 'large'
  loading?: boolean
  loadingText?: string
  fullWidth?: boolean
  startIcon?: React.ReactNode
  endIcon?: React.ReactNode
}

export function Button({
  children,
  variant = 'contained',
  size = 'medium',
  loading = false,
  loadingText,
  disabled,
  startIcon,
  endIcon,
  className,
  ...props
}: ButtonProps) {
  return (
    <MuiButton
      variant={variant}
      size={size}
      disabled={disabled || loading}
      startIcon={loading ? <CircularProgress size={16} /> : startIcon}
      endIcon={!loading ? endIcon : undefined}
      className={cn(className)}
      {...props}
    >
      {loading && loadingText ? loadingText : children}
    </MuiButton>
  )
}

export default Button