"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2025-01-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Initial schema creation"""
    
    # TimescaleDB拡張を有効化
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    
    # 価格データテーブル
    op.create_table('price_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.VARCHAR(length=10), nullable=False),
        sa.Column('timeframe', sa.VARCHAR(length=5), nullable=False),
        sa.Column('time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('open', sa.DECIMAL(precision=10, scale=5), nullable=False),
        sa.Column('high', sa.DECIMAL(precision=10, scale=5), nullable=False),
        sa.Column('low', sa.DECIMAL(precision=10, scale=5), nullable=False),
        sa.Column('close', sa.DECIMAL(precision=10, scale=5), nullable=False),
        sa.Column('tick_volume', sa.BigInteger(), server_default='0'),
        sa.Column('spread', sa.Integer(), server_default='0'),
        sa.Column('real_volume', sa.BigInteger(), server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'timeframe', 'time')
    )
    
    # TimescaleDBハイパーテーブル化
    op.execute("SELECT create_hypertable('price_data', 'time', if_not_exists => TRUE)")
    
    # 価格データインデックス
    op.create_index('idx_price_data_symbol_timeframe', 'price_data', ['symbol', 'timeframe'])
    op.create_index('idx_price_data_time', 'price_data', [sa.text('time DESC')])
    op.create_index('idx_price_data_symbol_time', 'price_data', ['symbol', sa.text('time DESC')])
    
    # 取引履歴テーブル
    op.create_table('trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_id', sa.BigInteger(), nullable=False),
        sa.Column('symbol', sa.VARCHAR(length=10), nullable=False),
        sa.Column('order_type', sa.VARCHAR(length=10), nullable=False),
        sa.Column('order_id', sa.BigInteger()),
        sa.Column('position_id', sa.BigInteger()),
        sa.Column('entry_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('entry_price', sa.DECIMAL(precision=10, scale=5), nullable=False),
        sa.Column('exit_time', sa.TIMESTAMP(timezone=True)),
        sa.Column('exit_price', sa.DECIMAL(precision=10, scale=5)),
        sa.Column('volume', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('profit_loss', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('swap', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('commission', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('comment', sa.VARCHAR(length=255)),
        sa.Column('magic_number', sa.Integer(), server_default='0'),
        sa.Column('reason', sa.VARCHAR(length=50)),
        sa.Column('is_closed', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_id')
    )
    
    # 取引履歴インデックス
    op.create_index('idx_trades_symbol', 'trades', ['symbol'])
    op.create_index('idx_trades_entry_time', 'trades', [sa.text('entry_time DESC')])
    op.create_index('idx_trades_is_closed', 'trades', ['is_closed'])
    op.create_index('idx_trades_magic_number', 'trades', ['magic_number'])
    
    # ポジション情報テーブル
    op.create_table('positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('position_id', sa.BigInteger(), nullable=False),
        sa.Column('symbol', sa.VARCHAR(length=10), nullable=False),
        sa.Column('type', sa.VARCHAR(length=10), nullable=False),
        sa.Column('volume', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('price_open', sa.DECIMAL(precision=10, scale=5), nullable=False),
        sa.Column('price_current', sa.DECIMAL(precision=10, scale=5)),
        sa.Column('stop_loss', sa.DECIMAL(precision=10, scale=5)),
        sa.Column('take_profit', sa.DECIMAL(precision=10, scale=5)),
        sa.Column('profit', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('swap', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('commission', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('magic_number', sa.Integer(), server_default='0'),
        sa.Column('comment', sa.VARCHAR(length=255)),
        sa.Column('time_create', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('time_update', sa.TIMESTAMP(timezone=True)),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('position_id')
    )
    
    # ポジションインデックス
    op.create_index('idx_positions_symbol', 'positions', ['symbol'])
    op.create_index('idx_positions_is_active', 'positions', ['is_active'])
    op.create_index('idx_positions_magic_number', 'positions', ['magic_number'])
    
    # バックテスト結果テーブル
    op.create_table('backtest_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_id', postgresql.UUID(), nullable=False),
        sa.Column('test_name', sa.VARCHAR(length=255), nullable=False),
        sa.Column('symbol', sa.VARCHAR(length=10), nullable=False),
        sa.Column('timeframe', sa.VARCHAR(length=5), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('total_trades', sa.Integer(), server_default='0'),
        sa.Column('winning_trades', sa.Integer(), server_default='0'),
        sa.Column('losing_trades', sa.Integer(), server_default='0'),
        sa.Column('win_rate', sa.DECIMAL(precision=5, scale=2), server_default='0'),
        sa.Column('profit_factor', sa.DECIMAL(precision=10, scale=4), server_default='0'),
        sa.Column('max_drawdown', sa.DECIMAL(precision=5, scale=2), server_default='0'),
        sa.Column('total_profit', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('avg_profit', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('avg_loss', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('largest_profit', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('largest_loss', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('parameters', postgresql.JSONB()),
        sa.Column('metrics', postgresql.JSONB()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # バックテストインデックス
    op.create_index('idx_backtest_test_id', 'backtest_results', ['test_id'])
    op.create_index('idx_backtest_symbol', 'backtest_results', ['symbol'])
    op.create_index('idx_backtest_created_at', 'backtest_results', [sa.text('created_at DESC')])
    
    # 経済指標テーブル
    op.create_table('economic_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.VARCHAR(length=50)),
        sa.Column('title', sa.VARCHAR(length=255), nullable=False),
        sa.Column('country', sa.VARCHAR(length=10), nullable=False),
        sa.Column('currency', sa.VARCHAR(length=5), nullable=False),
        sa.Column('impact', sa.VARCHAR(length=10)),
        sa.Column('event_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('forecast', sa.VARCHAR(length=50)),
        sa.Column('previous', sa.VARCHAR(length=50)),
        sa.Column('actual', sa.VARCHAR(length=50)),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )
    
    # 経済指標インデックス
    op.create_index('idx_economic_events_time', 'economic_events', ['event_time'])
    op.create_index('idx_economic_events_currency', 'economic_events', ['currency'])
    op.create_index('idx_economic_events_impact', 'economic_events', ['impact'])
    
    # システム設定テーブル
    op.create_table('system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.VARCHAR(length=100), nullable=False),
        sa.Column('value', sa.Text()),
        sa.Column('value_type', sa.VARCHAR(length=20), server_default='string'),
        sa.Column('description', sa.Text()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    
    # システムログテーブル
    op.create_table('system_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('level', sa.VARCHAR(length=10), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('module', sa.VARCHAR(length=100)),
        sa.Column('function_name', sa.VARCHAR(length=100)),
        sa.Column('line_number', sa.Integer()),
        sa.Column('extra_data', postgresql.JSONB()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # システムログインデックス
    op.create_index('idx_system_logs_level', 'system_logs', ['level'])
    op.create_index('idx_system_logs_created_at', 'system_logs', [sa.text('created_at DESC')])
    op.create_index('idx_system_logs_module', 'system_logs', ['module'])


def downgrade() -> None:
    """Drop all tables"""
    op.drop_table('system_logs')
    op.drop_table('system_settings')
    op.drop_table('economic_events')
    op.drop_table('backtest_results')
    op.drop_table('positions')
    op.drop_table('trades')
    op.drop_table('price_data')