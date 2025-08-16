/**
 * バックテストページ
 */
'use client'

import React, { useState } from 'react'
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Button,
  Chip,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Checkbox,
  Pagination,
  Alert,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material'
import {
  Add,
  Refresh,
  FilterList,
  Compare,
  Delete,
  Visibility,
  Download,
  Search,
  Close
} from '@mui/icons-material'
// DatePickerを削除してHTML input[type="date"]を使用
import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import BacktestForm from '@/components/backtest/BacktestForm'
import BacktestResults from '@/components/backtest/BacktestResults'
import { useUISelectors } from '@/store/ui'
import { useBacktestResults, useDeleteBacktestResults } from '@/hooks/useBacktest'
import { BacktestListResponse } from '@/types/backtest'
import {
  formatCurrency,
  formatPercentage,
  formatDateTime,
  getProfitColor
} from '@/lib/utils'
import { SIDEBAR_WIDTH, HEADER_HEIGHT, CURRENCY_PAIRS, TIMEFRAMES, CURRENCY_PAIR_LABELS, TIMEFRAME_LABELS } from '@/lib/constants'
import { TableLoading } from '@/components/ui/Loading'

export default function BacktestPage() {
  const { sidebarOpen, sidebarCollapsed } = useUISelectors()
  
  const [selectedTests, setSelectedTests] = useState<string[]>([])
  const [showForm, setShowForm] = useState(false)
  const [showResults, setShowResults] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [filters, setFilters] = useState({
    symbol: '',
    timeframe: '',
    startDate: '',
    endDate: '',
    search: ''
  })

  const pageSize = 20
  const { data: backtestData, isLoading, refetch } = useBacktestResults({
    page: currentPage,
    pageSize,
    symbol: filters.symbol || undefined,
    timeframe: filters.timeframe || undefined,
    startDate: filters.startDate || undefined,
    endDate: filters.endDate || undefined
  })

  const deleteBacktests = useDeleteBacktestResults()

  const sidebarWidth = sidebarOpen ? (sidebarCollapsed ? 64 : SIDEBAR_WIDTH) : 0

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelectedTests(backtestData?.tests?.map(test => test.testId) || [])
    } else {
      setSelectedTests([])
    }
  }

  const handleSelectTest = (testId: string) => {
    setSelectedTests(prev => 
      prev.includes(testId) 
        ? prev.filter(id => id !== testId)
        : [...prev, testId]
    )
  }

  const handleDeleteSelected = async () => {
    if (selectedTests.length === 0) return
    
    try {
      await deleteBacktests.mutateAsync(selectedTests)
      setSelectedTests([])
      refetch()
    } catch (error) {
      console.error('Delete failed:', error)
    }
  }

  const handleFormResult = (testId: string) => {
    setShowForm(false)
    setShowResults(testId)
    refetch()
  }

  const handleViewResults = (testId: string) => {
    setShowResults(testId)
  }

  const handleResultsClose = () => {
    setShowResults(null)
  }

  const handleResultsDelete = (testId: string) => {
    setShowResults(null)
    refetch()
  }

  const filteredTests = backtestData?.tests?.filter(test => {
    if (!filters.search) return true
    const searchTerm = filters.search.toLowerCase()
    return (
      test.symbol.toLowerCase().includes(searchTerm) ||
      test.timeframe.toLowerCase().includes(searchTerm) ||
      test.testId.toLowerCase().includes(searchTerm)
    )
  }) || []

  const isAllSelected = selectedTests.length > 0 && selectedTests.length === filteredTests.length
  const isPartiallySelected = selectedTests.length > 0 && selectedTests.length < filteredTests.length

  return (
    <div>
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
                バックテスト
              </Typography>
              <Typography variant="body1" color="text.secondary">
                戦略の検証と最適化
              </Typography>
            </Box>

            {/* フィルター・アクション */}
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} md={2}>
                    <FormControl fullWidth size="small">
                      <InputLabel>通貨ペア</InputLabel>
                      <Select
                        value={filters.symbol}
                        onChange={(e) => setFilters(prev => ({ ...prev, symbol: e.target.value }))}
                        label="通貨ペア"
                      >
                        <MenuItem value="">すべて</MenuItem>
                        {CURRENCY_PAIRS.map((pair) => (
                          <MenuItem key={pair} value={pair}>
                            {CURRENCY_PAIR_LABELS[pair]}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  
                  <Grid item xs={12} md={2}>
                    <FormControl fullWidth size="small">
                      <InputLabel>時間軸</InputLabel>
                      <Select
                        value={filters.timeframe}
                        onChange={(e) => setFilters(prev => ({ ...prev, timeframe: e.target.value }))}
                        label="時間軸"
                      >
                        <MenuItem value="">すべて</MenuItem>
                        {TIMEFRAMES.map((tf) => (
                          <MenuItem key={tf} value={tf}>
                            {TIMEFRAME_LABELS[tf]}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12} md={2}>
                    <TextField
                      label="開始日"
                      type="date"
                      value={filters.startDate || ''}
                      onChange={(e) => setFilters(prev => ({ 
                        ...prev, 
                        startDate: e.target.value
                      }))}
                      size="small"
                      fullWidth
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>

                  <Grid item xs={12} md={2}>
                    <TextField
                      label="終了日"
                      type="date"
                      value={filters.endDate || ''}
                      onChange={(e) => setFilters(prev => ({ 
                        ...prev, 
                        endDate: e.target.value
                      }))}
                      size="small"
                      fullWidth
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>

                  <Grid item xs={12} md={3}>
                    <TextField
                      fullWidth
                      size="small"
                      placeholder="検索..."
                      value={filters.search}
                      onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                      InputProps={{
                        startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
                      }}
                    />
                  </Grid>

                  <Grid item xs={12} md={1}>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => refetch()}
                      startIcon={<Refresh />}
                      fullWidth
                    >
                      更新
                    </Button>
                  </Grid>
                </Grid>

                {/* 選択アクション */}
                {selectedTests.length > 0 && (
                  <Box mt={2} display="flex" gap={1} alignItems="center">
                    <Typography variant="body2" color="text.secondary">
                      {selectedTests.length}件選択中
                    </Typography>
                    <Button
                      size="small"
                      color="error"
                      startIcon={<Delete />}
                      onClick={handleDeleteSelected}
                      disabled={deleteBacktests.isPending}
                    >
                      削除
                    </Button>
                    {selectedTests.length >= 2 && (
                      <Button
                        size="small"
                        startIcon={<Compare />}
                        // onClick={handleCompareSelected}
                      >
                        比較
                      </Button>
                    )}
                  </Box>
                )}
              </CardContent>
            </Card>

            {/* バックテスト結果一覧 */}
            <Card>
              <CardHeader
                title={`バックテスト結果 (${backtestData?.total || 0}件)`}
                action={
                  <Button
                    variant="contained"
                    startIcon={<Add />}
                    onClick={() => setShowForm(true)}
                  >
                    新規バックテスト
                  </Button>
                }
              />
              <CardContent>
                {isLoading ? (
                  <TableLoading rows={10} columns={8} />
                ) : filteredTests.length === 0 ? (
                  <Alert severity="info">
                    バックテスト結果がありません。新規バックテストを実行してください。
                  </Alert>
                ) : (
                  <>
                    <TableContainer component={Paper} elevation={0}>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell padding="checkbox">
                              <Checkbox
                                checked={isAllSelected}
                                indeterminate={isPartiallySelected}
                                onChange={handleSelectAll}
                              />
                            </TableCell>
                            <TableCell>通貨ペア</TableCell>
                            <TableCell>時間軸</TableCell>
                            <TableCell>期間</TableCell>
                            <TableCell align="right">取引数</TableCell>
                            <TableCell align="right">純利益</TableCell>
                            <TableCell align="right">勝率</TableCell>
                            <TableCell align="right">PF</TableCell>
                            <TableCell align="center">実行日時</TableCell>
                            <TableCell align="center">操作</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {filteredTests.map((test) => (
                            <TableRow key={test.testId} hover>
                              <TableCell padding="checkbox">
                                <Checkbox
                                  checked={selectedTests.includes(test.testId)}
                                  onChange={() => handleSelectTest(test.testId)}
                                />
                              </TableCell>
                              
                              <TableCell>
                                <Chip
                                  label={CURRENCY_PAIR_LABELS[test.symbol]}
                                  size="small"
                                  variant="outlined"
                                />
                              </TableCell>
                              
                              <TableCell>
                                <Chip
                                  label={TIMEFRAME_LABELS[test.timeframe]}
                                  size="small"
                                />
                              </TableCell>
                              
                              <TableCell>
                                <Typography variant="body2">
                                  {formatDateTime(test.period.startDate, 'MM/dd')} - {formatDateTime(test.period.endDate, 'MM/dd')}
                                </Typography>
                              </TableCell>
                              
                              <TableCell align="right">
                                <Typography variant="body2">
                                  {test.totalTrades}
                                </Typography>
                              </TableCell>
                              
                              <TableCell align="right">
                                <Typography
                                  variant="body2"
                                  fontWeight={600}
                                  color={getProfitColor(test.netProfit)}
                                >
                                  {formatCurrency(test.netProfit)}
                                </Typography>
                              </TableCell>
                              
                              <TableCell align="right">
                                <Typography variant="body2">
                                  {formatPercentage(test.winRate)}
                                </Typography>
                              </TableCell>
                              
                              <TableCell align="right">
                                <Typography variant="body2">
                                  {test.profitFactor?.toFixed(2) || '-'}
                                </Typography>
                              </TableCell>
                              
                              <TableCell align="center">
                                <Typography variant="body2">
                                  {formatDateTime(test.createdAt, 'MM/dd HH:mm')}
                                </Typography>
                              </TableCell>
                              
                              <TableCell align="center">
                                <IconButton
                                  size="small"
                                  onClick={() => handleViewResults(test.testId)}
                                >
                                  <Visibility />
                                </IconButton>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>

                    {/* ページネーション */}
                    {backtestData && backtestData.total > pageSize && (
                      <Box display="flex" justifyContent="center" mt={2}>
                        <Pagination
                          count={Math.ceil(backtestData.total / pageSize)}
                          page={currentPage}
                          onChange={(_, page) => setCurrentPage(page)}
                          color="primary"
                        />
                      </Box>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </Container>

          {/* FAB */}
          <Fab
            color="primary"
            sx={{ position: 'fixed', bottom: 24, right: 24 }}
            onClick={() => setShowForm(true)}
          >
            <Add />
          </Fab>
        </Box>
      </Box>

      {/* バックテスト実行フォームダイアログ */}
      <Dialog
        open={showForm}
        onClose={() => setShowForm(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            新規バックテスト
            <IconButton onClick={() => setShowForm(false)}>
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <BacktestForm
            onResult={handleFormResult}
          />
        </DialogContent>
      </Dialog>

      {/* バックテスト結果表示ダイアログ */}
      <Dialog
        open={!!showResults}
        onClose={handleResultsClose}
        maxWidth="xl"
        fullWidth
        sx={{ '& .MuiDialog-paper': { height: '90vh' } }}
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            バックテスト結果
            <IconButton onClick={handleResultsClose}>
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent sx={{ p: 0 }}>
          {showResults && (
            <BacktestResults
              testId={showResults}
              onDelete={handleResultsDelete}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}