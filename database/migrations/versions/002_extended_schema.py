"""Extended schema for ML and advanced features

Revision ID: 002
Revises: 001
Create Date: 2025-01-14 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add extended tables for ML and advanced features"""
    
    # MLモデル管理テーブル
    op.create_table('ml_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_name', sa.VARCHAR(length=100), nullable=False),
        sa.Column('model_type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('symbol', sa.VARCHAR(length=10), nullable=False),
        sa.Column('timeframe', sa.VARCHAR(length=5), nullable=False),
        sa.Column('version', sa.VARCHAR(length=20), nullable=False),
        sa.Column('file_path', sa.VARCHAR(length=255), nullable=False),
        sa.Column('training_period_start', sa.Date(), nullable=False),
        sa.Column('training_period_end', sa.Date(), nullable=False),
        sa.Column('validation_score', sa.DECIMAL(precision=8, scale=4)),
        sa.Column('test_score', sa.DECIMAL(precision=8, scale=4)),
        sa.Column('parameters', postgresql.JSONB()),
        sa.Column('feature_importance', postgresql.JSONB()),
        sa.Column('feature_list', postgresql.JSONB()),
        sa.Column('metrics', postgresql.JSONB()),
        sa.Column('is_active', sa.Boolean(), server_default='false'),
        sa.Column('notes', sa.Text()),
        sa.Column('created_by', sa.VARCHAR(length=100)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_name', 'symbol', 'timeframe', 'version')
    )
    
    # MLモデルインデックス
    op.create_index('idx_ml_models_active', 'ml_models', ['is_active', 'symbol', 'timeframe'])
    op.create_index('idx_ml_models_symbol_timeframe', 'ml_models', ['symbol', 'timeframe'])
    op.create_index('idx_ml_models_created_at', 'ml_models', [sa.text('created_at DESC')])
    
    # 戦略実行履歴テーブル
    op.create_table('strategy_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('execution_id', postgresql.UUID(), nullable=False),
        sa.Column('strategy_name', sa.VARCHAR(length=100), nullable=False),
        sa.Column('symbol', sa.VARCHAR(length=10), nullable=False),
        sa.Column('timeframe', sa.VARCHAR(length=5), nullable=False),
        sa.Column('model_id', sa.Integer()),
        sa.Column('start_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('end_time', sa.TIMESTAMP(timezone=True)),
        sa.Column('status', sa.VARCHAR(length=20), server_default='running'),
        sa.Column('total_trades', sa.Integer(), server_default='0'),
        sa.Column('winning_trades', sa.Integer(), server_default='0'),
        sa.Column('total_profit', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('max_drawdown', sa.DECIMAL(precision=5, scale=2), server_default='0'),
        sa.Column('parameters', postgresql.JSONB()),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['model_id'], ['ml_models.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 戦略実行履歴インデックス
    op.create_index('idx_strategy_executions_strategy', 'strategy_executions', ['strategy_name', sa.text('start_time DESC')])
    op.create_index('idx_strategy_executions_symbol', 'strategy_executions', ['symbol', sa.text('start_time DESC')])
    op.create_index('idx_strategy_executions_status', 'strategy_executions', ['status'])
    
    # リスク管理ログテーブル
    op.create_table('risk_management_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('symbol', sa.VARCHAR(length=10)),
        sa.Column('trigger_value', sa.DECIMAL(precision=10, scale=4)),
        sa.Column('threshold_value', sa.DECIMAL(precision=10, scale=4)),
        sa.Column('action_taken', sa.VARCHAR(length=100)),
        sa.Column('description', sa.Text()),
        sa.Column('severity', sa.VARCHAR(length=10), server_default='INFO'),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # リスク管理ログインデックス
    op.create_index('idx_risk_logs_event_type', 'risk_management_logs', ['event_type', sa.text('created_at DESC')])
    op.create_index('idx_risk_logs_severity', 'risk_management_logs', ['severity', sa.text('created_at DESC')])
    
    # 特徴量履歴テーブル
    op.create_table('feature_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.VARCHAR(length=10), nullable=False),
        sa.Column('timeframe', sa.VARCHAR(length=5), nullable=False),
        sa.Column('time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('features', postgresql.JSONB(), nullable=False),
        sa.Column('target', sa.DECIMAL(precision=10, scale=5)),
        sa.Column('is_training_data', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'timeframe', 'time')
    )
    
    # 特徴量データをハイパーテーブル化
    op.execute("SELECT create_hypertable('feature_data', 'time', if_not_exists => TRUE)")
    
    # 特徴量履歴インデックス
    op.create_index('idx_feature_data_symbol_timeframe', 'feature_data', ['symbol', 'timeframe', sa.text('time DESC')])
    op.create_index('idx_feature_data_training', 'feature_data', ['is_training_data', 'symbol', 'timeframe'])
    
    # 予測結果テーブル
    op.create_table('predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.VARCHAR(length=10), nullable=False),
        sa.Column('timeframe', sa.VARCHAR(length=5), nullable=False),
        sa.Column('prediction_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('target_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('predicted_direction', sa.VARCHAR(length=10)),
        sa.Column('predicted_price', sa.DECIMAL(precision=10, scale=5)),
        sa.Column('confidence_score', sa.DECIMAL(precision=5, scale=4)),
        sa.Column('actual_price', sa.DECIMAL(precision=10, scale=5)),
        sa.Column('accuracy', sa.DECIMAL(precision=5, scale=4)),
        sa.Column('features_used', postgresql.JSONB()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['model_id'], ['ml_models.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 予測結果をハイパーテーブル化
    op.execute("SELECT create_hypertable('predictions', 'prediction_time', if_not_exists => TRUE)")
    
    # 予測結果インデックス
    op.create_index('idx_predictions_model_symbol', 'predictions', ['model_id', 'symbol', sa.text('prediction_time DESC')])
    op.create_index('idx_predictions_accuracy', 'predictions', ['accuracy', 'model_id'])
    
    # アラート・通知テーブル
    op.create_table('alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('priority', sa.VARCHAR(length=10), server_default='MEDIUM'),
        sa.Column('title', sa.VARCHAR(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('symbol', sa.VARCHAR(length=10)),
        sa.Column('trade_id', sa.BigInteger()),
        sa.Column('strategy_name', sa.VARCHAR(length=100)),
        sa.Column('triggered_value', sa.DECIMAL(precision=10, scale=4)),
        sa.Column('threshold_value', sa.DECIMAL(precision=10, scale=4)),
        sa.Column('is_sent', sa.Boolean(), server_default='false'),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('is_acknowledged', sa.Boolean(), server_default='false'),
        sa.Column('acknowledged_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('acknowledged_by', sa.VARCHAR(length=100)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # アラートインデックス
    op.create_index('idx_alerts_type_priority', 'alerts', ['alert_type', 'priority', sa.text('created_at DESC')])
    op.create_index('idx_alerts_unacknowledged', 'alerts', ['is_acknowledged', 'priority', sa.text('created_at DESC')])
    
    # パフォーマンス統計テーブル
    op.create_table('performance_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period_type', sa.VARCHAR(length=20), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('symbol', sa.VARCHAR(length=10)),
        sa.Column('strategy_name', sa.VARCHAR(length=100)),
        sa.Column('total_trades', sa.Integer(), server_default='0'),
        sa.Column('winning_trades', sa.Integer(), server_default='0'),
        sa.Column('losing_trades', sa.Integer(), server_default='0'),
        sa.Column('win_rate', sa.DECIMAL(precision=5, scale=2), server_default='0'),
        sa.Column('total_profit', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('total_loss', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('net_profit', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('profit_factor', sa.DECIMAL(precision=8, scale=4), server_default='0'),
        sa.Column('max_drawdown', sa.DECIMAL(precision=5, scale=2), server_default='0'),
        sa.Column('max_drawdown_amount', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('avg_trade_duration', sa.Interval()),
        sa.Column('sharpe_ratio', sa.DECIMAL(precision=8, scale=4)),
        sa.Column('sortino_ratio', sa.DECIMAL(precision=8, scale=4)),
        sa.Column('calmar_ratio', sa.DECIMAL(precision=8, scale=4)),
        sa.Column('recovery_factor', sa.DECIMAL(precision=8, scale=4)),
        sa.Column('commission_paid', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('swap_paid', sa.DECIMAL(precision=10, scale=2), server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('period_type', 'period_start', 'symbol', 'strategy_name')
    )
    
    # パフォーマンス統計インデックス
    op.create_index('idx_performance_stats_period', 'performance_stats', ['period_type', sa.text('period_start DESC')])
    op.create_index('idx_performance_stats_symbol', 'performance_stats', ['symbol', sa.text('period_start DESC')])
    op.create_index('idx_performance_stats_strategy', 'performance_stats', ['strategy_name', sa.text('period_start DESC')])
    
    # ユーザー認証テーブル
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.VARCHAR(length=50), nullable=False),
        sa.Column('email', sa.VARCHAR(length=255), nullable=False),
        sa.Column('password_hash', sa.VARCHAR(length=255), nullable=False),
        sa.Column('full_name', sa.VARCHAR(length=100)),
        sa.Column('role', sa.VARCHAR(length=20), server_default='user'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_login', sa.TIMESTAMP(timezone=True)),
        sa.Column('failed_login_attempts', sa.Integer(), server_default='0'),
        sa.Column('locked_until', sa.TIMESTAMP(timezone=True)),
        sa.Column('password_reset_token', sa.VARCHAR(length=255)),
        sa.Column('password_reset_expires', sa.TIMESTAMP(timezone=True)),
        sa.Column('preferences', postgresql.JSONB()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    
    # ユーザーインデックス
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_active', 'users', ['is_active'])
    
    # セッション管理テーブル
    op.create_table('user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.VARCHAR(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ip_address', postgresql.INET()),
        sa.Column('user_agent', sa.Text()),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    
    # セッションインデックス
    op.create_index('idx_user_sessions_session_id', 'user_sessions', ['session_id'])
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id', 'is_active'])
    op.create_index('idx_user_sessions_expires', 'user_sessions', ['expires_at'])
    
    # 設定変更履歴テーブル
    op.create_table('settings_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('setting_key', sa.VARCHAR(length=100), nullable=False),
        sa.Column('old_value', postgresql.JSONB()),
        sa.Column('new_value', postgresql.JSONB()),
        sa.Column('changed_by', sa.Integer()),
        sa.Column('change_reason', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 設定履歴インデックス
    op.create_index('idx_settings_history_key', 'settings_history', ['setting_key', sa.text('created_at DESC')])
    op.create_index('idx_settings_history_user', 'settings_history', ['changed_by', sa.text('created_at DESC')])


def downgrade() -> None:
    """Drop extended tables"""
    op.drop_table('settings_history')
    op.drop_table('user_sessions')
    op.drop_table('users')
    op.drop_table('performance_stats')
    op.drop_table('alerts')
    op.drop_table('predictions')
    op.drop_table('feature_data')
    op.drop_table('risk_management_logs')
    op.drop_table('strategy_executions')
    op.drop_table('ml_models')