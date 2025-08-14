/**
 * ポジション一覧コンポーネント
 */
'use client'

import React, { useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Alert
} from '@mui/material'
import {
  MoreVert,
  TrendingUp,
  TrendingDown,
  Close,
  Edit,
  Info
} from '@mui/icons-material'
import { usePositions } from '@/hooks/useTrades'
import { useTradingSelectors } from '@/store/trading'
import { useNotifications } from '@/store/ui'
import { Position } from '@/types/trading'
import {
  formatCurrency,
  formatDateTime,
  formatNumber,
  getProfitColor,
  translateOrderType,
  formatCurrencyPair
} from '@/lib/utils'
import { TableLoading } from '@/components/ui/Loading'

interface PositionsListProps {
  positions?: Position[]
  loading?: boolean
  onPositionClose?: (positionId: string) => void
  onPositionModify?: (positionId: string, updates: Partial<Position>) => void
}

export function PositionsList({
  positions: propPositions,
  loading: propLoading,
  onPositionClose,
  onPositionModify
}: PositionsListProps) {
  const { data: queryPositions, isLoading: queryLoading } = usePositions()
  const { currentPositions } = useTradingSelectors()
  const { showSuccess, showError } = useNotifications()

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null)
  const [modifyDialogOpen, setModifyDialogOpen] = useState(false)
  const [closeDialogOpen, setCloseDialogOpen] = useState(false)
  const [modifyValues, setModifyValues] = useState({ stopLoss: '', takeProfit: '' })

  // propsがあればそれを使用、なければクエリ結果またはストアの値を使用
  const positions = propPositions || queryPositions || currentPositions
  const loading = propLoading ?? queryLoading

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, position: Position) => {
    setAnchorEl(event.currentTarget)
    setSelectedPosition(position)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
    setSelectedPosition(null)
  }

  const handleModifyOpen = () => {
    if (selectedPosition) {
      setModifyValues({
        stopLoss: selectedPosition.stopLoss?.toString() || '',
        takeProfit: selectedPosition.takeProfit?.toString() || ''
      })
      setModifyDialogOpen(true)
      handleMenuClose()
    }
  }

  const handleCloseOpen = () => {
    setCloseDialogOpen(true)
    handleMenuClose()
  }

  const handleModifySubmit = async () => {
    if (!selectedPosition || !onPositionModify) return

    try {
      const updates: Partial<Position> = {}
      if (modifyValues.stopLoss) updates.stopLoss = parseFloat(modifyValues.stopLoss)
      if (modifyValues.takeProfit) updates.takeProfit = parseFloat(modifyValues.takeProfit)

      await onPositionModify(selectedPosition.id, updates)
      showSuccess('ポジション更新', 'ポジションが正常に更新されました')
      setModifyDialogOpen(false)
    } catch (error) {
      showError('更新エラー', 'ポジションの更新に失敗しました')
    }
  }

  const handleCloseSubmit = async () => {
    if (!selectedPosition || !onPositionClose) return

    try {
      await onPositionClose(selectedPosition.id)
      showSuccess('ポジション決済', 'ポジションが正常に決済されました')
      setCloseDialogOpen(false)
    } catch (error) {
      showError('決済エラー', 'ポジションの決済に失敗しました')
    }
  }

  const getTotalProfit = () => {
    return positions?.reduce((sum, pos) => sum + pos.profit, 0) || 0
  }

  const getProfitableCount = () => {
    return positions?.filter(pos => pos.profit > 0).length || 0
  }

  if (loading) {
    return <TableLoading rows={5} columns={8} />
  }

  if (!positions || positions.length === 0) {
    return (
      <Box display="flex" flexDirection="column" alignItems="center" py={4}>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          保有ポジションはありません
        </Typography>
        <Typography variant="body2" color="text.secondary">
          自動取引を開始するとポジションが表示されます
        </Typography>
      </Box>
    )
  }

  const totalProfit = getTotalProfit()
  const profitableCount = getProfitableCount()

  return (
    <Box>
      {/* サマリー情報 */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">
          保有ポジション ({positions.length}件)
        </Typography>
        <Box display="flex" gap={1}>
          <Chip
            label={`利益: ${profitableCount}件`}
            color="success"
            size="small"
          />
          <Chip
            label={`損失: ${positions.length - profitableCount}件`}
            color="error"
            size="small"
          />
          <Chip
            label={`合計: ${formatCurrency(totalProfit)}`}
            color={totalProfit >= 0 ? 'success' : 'error'}
            size="small"
            variant="outlined"
          />
        </Box>
      </Box>

      {/* ポジション一覧テーブル */}
      <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>通貨ペア</TableCell>
              <TableCell align="center">タイプ</TableCell>
              <TableCell align="right">ロット</TableCell>
              <TableCell align="right">建値</TableCell>
              <TableCell align="right">現在価格</TableCell>
              <TableCell align="right">損益</TableCell>
              <TableCell align="center">保有時間</TableCell>
              <TableCell align="center">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {positions.map((position) => (
              <TableRow key={position.id} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight={600}>
                    {formatCurrencyPair(position.symbol)}
                  </Typography>
                  {position.comment && (
                    <Typography variant="caption" color="text.secondary">
                      {position.comment}
                    </Typography>
                  )}
                </TableCell>
                
                <TableCell align="center">
                  <Box display="flex" alignItems="center" justifyContent="center" gap={0.5}>
                    {position.type === 'BUY' ? (
                      <TrendingUp color="success" fontSize="small" />
                    ) : (
                      <TrendingDown color="error" fontSize="small" />
                    )}
                    <Typography variant="body2" fontWeight={600}>
                      {translateOrderType(position.type)}
                    </Typography>
                  </Box>
                </TableCell>
                
                <TableCell align="right">
                  <Typography variant="body2">
                    {formatNumber(position.volume, 2)}
                  </Typography>
                </TableCell>
                
                <TableCell align="right">
                  <Typography variant="body2">
                    {formatNumber(position.openPrice, 3)}
                  </Typography>
                </TableCell>
                
                <TableCell align="right">
                  <Typography variant="body2">
                    {formatNumber(position.currentPrice, 3)}
                  </Typography>
                </TableCell>
                
                <TableCell align="right">
                  <Typography
                    variant="body2"
                    fontWeight={600}
                    className={getProfitColor(position.profit)}
                  >
                    {formatCurrency(position.profit)}
                  </Typography>
                  {(position.stopLoss || position.takeProfit) && (
                    <Box>
                      {position.stopLoss && (
                        <Typography variant="caption" color="error" display="block">
                          SL: {formatNumber(position.stopLoss, 3)}
                        </Typography>
                      )}
                      {position.takeProfit && (
                        <Typography variant="caption" color="success" display="block">
                          TP: {formatNumber(position.takeProfit, 3)}
                        </Typography>
                      )}
                    </Box>
                  )}
                </TableCell>
                
                <TableCell align="center">
                  <Typography variant="body2">
                    {formatDateTime(position.openTime, 'MM/dd HH:mm')}
                  </Typography>
                </TableCell>
                
                <TableCell align="center">
                  <IconButton
                    size="small"
                    onClick={(e) => handleMenuClick(e, position)}
                  >
                    <MoreVert />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* アクションメニュー */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleModifyOpen}>
          <Edit fontSize="small" sx={{ mr: 1 }} />
          修正
        </MenuItem>
        <MenuItem onClick={handleCloseOpen}>
          <Close fontSize="small" sx={{ mr: 1 }} />
          決済
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <Info fontSize="small" sx={{ mr: 1 }} />
          詳細
        </MenuItem>
      </Menu>

      {/* ポジション修正ダイアログ */}
      <Dialog open={modifyDialogOpen} onClose={() => setModifyDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>ポジション修正</DialogTitle>
        <DialogContent>
          {selectedPosition && (
            <Box display="flex" flexDirection="column" gap={2} mt={1}>
              <Alert severity="info">
                {formatCurrencyPair(selectedPosition.symbol)} {translateOrderType(selectedPosition.type)} 
                {formatNumber(selectedPosition.volume, 2)}ロット
              </Alert>
              
              <TextField
                label="ストップロス"
                type="number"
                value={modifyValues.stopLoss}
                onChange={(e) => setModifyValues(prev => ({ ...prev, stopLoss: e.target.value }))}
                inputProps={{ step: "0.001" }}
                fullWidth
                helperText="空欄の場合は設定しません"
              />
              
              <TextField
                label="テイクプロフィット"
                type="number"
                value={modifyValues.takeProfit}
                onChange={(e) => setModifyValues(prev => ({ ...prev, takeProfit: e.target.value }))}
                inputProps={{ step: "0.001" }}
                fullWidth
                helperText="空欄の場合は設定しません"
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModifyDialogOpen(false)}>
            キャンセル
          </Button>
          <Button onClick={handleModifySubmit} variant="contained">
            更新
          </Button>
        </DialogActions>
      </Dialog>

      {/* ポジション決済ダイアログ */}
      <Dialog open={closeDialogOpen} onClose={() => setCloseDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>ポジション決済</DialogTitle>
        <DialogContent>
          {selectedPosition && (
            <Box>
              <Alert severity="warning" sx={{ mb: 2 }}>
                以下のポジションを決済しますか？この操作は取り消せません。
              </Alert>
              
              <Box display="flex" flexDirection="column" gap={1}>
                <Typography>
                  <strong>通貨ペア:</strong> {formatCurrencyPair(selectedPosition.symbol)}
                </Typography>
                <Typography>
                  <strong>タイプ:</strong> {translateOrderType(selectedPosition.type)}
                </Typography>
                <Typography>
                  <strong>ロット:</strong> {formatNumber(selectedPosition.volume, 2)}
                </Typography>
                <Typography>
                  <strong>建値:</strong> {formatNumber(selectedPosition.openPrice, 3)}
                </Typography>
                <Typography>
                  <strong>現在価格:</strong> {formatNumber(selectedPosition.currentPrice, 3)}
                </Typography>
                <Typography className={getProfitColor(selectedPosition.profit)}>
                  <strong>評価損益:</strong> {formatCurrency(selectedPosition.profit)}
                </Typography>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCloseDialogOpen(false)}>
            キャンセル
          </Button>
          <Button onClick={handleCloseSubmit} variant="contained" color="error">
            決済する
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default PositionsList