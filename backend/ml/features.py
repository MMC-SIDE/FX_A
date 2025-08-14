"""
特徴量エンジニアリング
"""
import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FeatureEngineering:
    """特徴量エンジニアリングクラス"""
    
    def __init__(self):
        self.technical_indicators = {
            'sma': [5, 10, 20, 50, 200],
            'ema': [12, 26],
            'rsi': [14, 30],
            'macd': {'fast': 12, 'slow': 26, 'signal': 9},
            'bollinger': {'period': 20, 'std': 2},
            'atr': 14,
            'stoch': {'k': 14, 'd': 3},
            'adx': 14,
            'cci': 20,
            'williams_r': 14,
            'mfi': 14,
            'obv': True,
            'sar': {'acceleration': 0.02, 'maximum': 0.2}
        }
        
        self.feature_columns = []
        
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        特徴量作成メイン関数
        
        Args:
            df: OHLCV価格データのDataFrame
            
        Returns:
            特徴量を追加したDataFrame
        """
        try:
            logger.info("Starting feature engineering...")
            df = df.copy()
            
            # 基本チェック
            if not self._validate_input(df):
                raise ValueError("Invalid input data")
            
            # テクニカル指標
            df = self._add_technical_indicators(df)
            
            # 価格変化率
            df = self._add_price_changes(df)
            
            # 時間的特徴量
            df = self._add_time_features(df)
            
            # ボラティリティ指標
            df = self._add_volatility_features(df)
            
            # 統計的特徴量
            df = self._add_statistical_features(df)
            
            # パターン認識特徴量
            df = self._add_pattern_features(df)
            
            # 特徴量リストを更新
            self._update_feature_columns(df)
            
            # NaN値の処理
            df = self._handle_missing_values(df)
            
            logger.info(f"Feature engineering completed. Created {len(self.feature_columns)} features")
            return df
            
        except Exception as e:
            logger.error(f"Error in feature engineering: {e}")
            raise
    
    def _validate_input(self, df: pd.DataFrame) -> bool:
        """入力データの検証"""
        required_columns = ['open', 'high', 'low', 'close']
        if 'volume' in df.columns:
            required_columns.append('volume')
            
        if not all(col in df.columns for col in required_columns):
            logger.error(f"Missing required columns: {required_columns}")
            return False
            
        if len(df) < 200:  # 最小データ数
            logger.error("Insufficient data for feature engineering")
            return False
            
        return True
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """テクニカル指標の追加"""
        try:
            # 移動平均線
            for period in self.technical_indicators['sma']:
                df[f'sma_{period}'] = talib.SMA(df['close'], timeperiod=period)
                df[f'price_sma_{period}_ratio'] = df['close'] / df[f'sma_{period}']
                
                # 移動平均線の傾き
                df[f'sma_{period}_slope'] = df[f'sma_{period}'].diff(5) / df[f'sma_{period}']
            
            # 指数移動平均
            for period in self.technical_indicators['ema']:
                df[f'ema_{period}'] = talib.EMA(df['close'], timeperiod=period)
                df[f'price_ema_{period}_ratio'] = df['close'] / df[f'ema_{period}']
            
            # RSI
            for period in self.technical_indicators['rsi']:
                df[f'rsi_{period}'] = talib.RSI(df['close'], timeperiod=period)
                # RSIの変化率
                df[f'rsi_{period}_change'] = df[f'rsi_{period}'].diff()
            
            # MACD
            macd_config = self.technical_indicators['macd']
            macd, macdsignal, macdhist = talib.MACD(
                df['close'], 
                fastperiod=macd_config['fast'],
                slowperiod=macd_config['slow'],
                signalperiod=macd_config['signal']
            )
            df['macd'] = macd
            df['macd_signal'] = macdsignal
            df['macd_histogram'] = macdhist
            df['macd_signal_cross'] = np.where(
                (df['macd'] > df['macd_signal']) & 
                (df['macd'].shift(1) <= df['macd_signal'].shift(1)), 1,
                np.where(
                    (df['macd'] < df['macd_signal']) & 
                    (df['macd'].shift(1) >= df['macd_signal'].shift(1)), -1, 0
                )
            )
            
            # ボリンジャーバンド
            bb_config = self.technical_indicators['bollinger']
            upper, middle, lower = talib.BBANDS(
                df['close'], 
                timeperiod=bb_config['period'],
                nbdevup=bb_config['std'],
                nbdevdn=bb_config['std']
            )
            df['bb_upper'] = upper
            df['bb_middle'] = middle
            df['bb_lower'] = lower
            df['bb_width'] = (upper - lower) / middle
            df['bb_position'] = (df['close'] - lower) / (upper - lower)
            df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(20).mean() * 0.8
            
            # ATR (Average True Range)
            atr_period = self.technical_indicators['atr']
            df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=atr_period)
            df['atr_ratio'] = df['atr'] / df['close']
            
            # ストキャスティクス
            stoch_config = self.technical_indicators['stoch']
            slowk, slowd = talib.STOCH(
                df['high'], df['low'], df['close'],
                fastk_period=stoch_config['k'], 
                slowk_period=stoch_config['d'],
                slowd_period=stoch_config['d']
            )
            df['stoch_k'] = slowk
            df['stoch_d'] = slowd
            df['stoch_cross'] = np.where(
                (df['stoch_k'] > df['stoch_d']) & 
                (df['stoch_k'].shift(1) <= df['stoch_d'].shift(1)), 1,
                np.where(
                    (df['stoch_k'] < df['stoch_d']) & 
                    (df['stoch_k'].shift(1) >= df['stoch_d'].shift(1)), -1, 0
                )
            )
            
            # ADX (Average Directional Index)
            adx_period = self.technical_indicators['adx']
            df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=adx_period)
            df['plus_di'] = talib.PLUS_DI(df['high'], df['low'], df['close'], timeperiod=adx_period)
            df['minus_di'] = talib.MINUS_DI(df['high'], df['low'], df['close'], timeperiod=adx_period)
            df['dx'] = talib.DX(df['high'], df['low'], df['close'], timeperiod=adx_period)
            
            # CCI (Commodity Channel Index)
            cci_period = self.technical_indicators['cci']
            df['cci'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=cci_period)
            
            # Williams %R
            willr_period = self.technical_indicators['williams_r']
            df['williams_r'] = talib.WILLR(df['high'], df['low'], df['close'], timeperiod=willr_period)
            
            # MFI (Money Flow Index) - volumeが必要
            if 'volume' in df.columns:
                mfi_period = self.technical_indicators['mfi']
                df['mfi'] = talib.MFI(df['high'], df['low'], df['close'], df['volume'], timeperiod=mfi_period)
                
                # OBV (On Balance Volume)
                df['obv'] = talib.OBV(df['close'], df['volume'])
                df['obv_sma'] = talib.SMA(df['obv'], timeperiod=20)
            
            # Parabolic SAR
            sar_config = self.technical_indicators['sar']
            df['sar'] = talib.SAR(
                df['high'], df['low'], 
                acceleration=sar_config['acceleration'],
                maximum=sar_config['maximum']
            )
            df['sar_signal'] = np.where(df['close'] > df['sar'], 1, -1)
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding technical indicators: {e}")
            raise
    
    def _add_price_changes(self, df: pd.DataFrame) -> pd.DataFrame:
        """価格変化率の追加"""
        try:
            periods = [1, 3, 5, 10, 20]
            
            for period in periods:
                # 価格変化率
                df[f'price_change_{period}'] = df['close'].pct_change(period)
                df[f'high_change_{period}'] = df['high'].pct_change(period)
                df[f'low_change_{period}'] = df['low'].pct_change(period)
                
                # ログリターン
                df[f'log_return_{period}'] = np.log(df['close'] / df['close'].shift(period))
                
                # 価格レンジ
                df[f'hl_ratio_{period}'] = (df['high'] - df['low']) / df['close']
                
            # 日中価格変動
            df['intraday_range'] = (df['high'] - df['low']) / df['open']
            df['open_close_ratio'] = df['close'] / df['open']
            df['high_close_ratio'] = df['high'] / df['close']
            df['low_close_ratio'] = df['low'] / df['close']
            
            # ギャップ
            df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
            df['gap_filled'] = np.where(
                (df['gap'] > 0) & (df['low'] <= df['close'].shift(1)), 1,
                np.where(
                    (df['gap'] < 0) & (df['high'] >= df['close'].shift(1)), 1, 0
                )
            )
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding price changes: {e}")
            raise
    
    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """時間的特徴量の追加"""
        try:
            # 基本的な時間特徴量
            df['hour'] = df.index.hour
            df['day_of_week'] = df.index.dayofweek
            df['month'] = df.index.month
            df['quarter'] = df.index.quarter
            df['day_of_month'] = df.index.day
            df['week_of_year'] = df.index.isocalendar().week
            
            # 循環的エンコーディング
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
            df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
            df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
            df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
            
            # 市場セッション
            df['tokyo_session'] = ((df['hour'] >= 0) & (df['hour'] < 9)).astype(int)
            df['london_session'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)
            df['ny_session'] = ((df['hour'] >= 13) & (df['hour'] < 22)).astype(int)
            df['overlap_london_ny'] = ((df['hour'] >= 13) & (df['hour'] < 16)).astype(int)
            df['overlap_tokyo_london'] = ((df['hour'] >= 8) & (df['hour'] < 9)).astype(int)
            
            # 週末・休日フラグ
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
            df['is_monday'] = (df['day_of_week'] == 0).astype(int)
            df['is_friday'] = (df['day_of_week'] == 4).astype(int)
            
            # 月末・月初フラグ
            df['is_month_end'] = (df['day_of_month'] >= 28).astype(int)
            df['is_month_start'] = (df['day_of_month'] <= 3).astype(int)
            
            # 経済指標発表時間フラグ（一般的な時間）
            df['news_time_jpy'] = ((df['hour'] == 0) | (df['hour'] == 1)).astype(int)  # 日本時間8:30, 9:30
            df['news_time_eur'] = ((df['hour'] == 9) | (df['hour'] == 10)).astype(int)  # 欧州時間10:00
            df['news_time_usd'] = ((df['hour'] == 13) | (df['hour'] == 14) | (df['hour'] == 15)).astype(int)  # 米国時間8:30, 10:00
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding time features: {e}")
            raise
    
    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ボラティリティ特徴量の追加"""
        try:
            periods = [5, 10, 20, 50]
            
            for period in periods:
                # 価格ボラティリティ（標準偏差）
                df[f'volatility_{period}'] = df['close'].rolling(period).std()
                df[f'volatility_{period}_norm'] = df[f'volatility_{period}'] / df['close']
                
                # パーキンソン推定量（高値・安値を使用）
                df[f'parkinson_vol_{period}'] = np.sqrt(
                    0.25 * np.log(df['high'] / df['low']).pow(2).rolling(period).mean()
                )
                
                # ガーマン・クラス推定量
                df[f'gk_vol_{period}'] = np.sqrt(
                    np.log(df['high'] / df['close']) * np.log(df['high'] / df['open']) +
                    np.log(df['low'] / df['close']) * np.log(df['low'] / df['open'])
                ).rolling(period).mean()
                
                # リターンのレンジ
                df[f'return_range_{period}'] = (
                    df['close'].rolling(period).max() - df['close'].rolling(period).min()
                ) / df['close']
                
            # VIXライクな指標（ATRベース）
            df['vix_like'] = df['atr'] / df['close'] * 100
            df['vix_like_ma'] = df['vix_like'].rolling(20).mean()
            df['vix_spike'] = (df['vix_like'] > df['vix_like_ma'] * 1.5).astype(int)
            
            # ボラティリティレジーム
            vol_20 = df['close'].rolling(20).std()
            vol_60 = df['close'].rolling(60).std()
            df['vol_regime'] = np.where(vol_20 > vol_60 * 1.2, 1,  # 高ボラティリティ
                                np.where(vol_20 < vol_60 * 0.8, -1, 0))  # 低ボラティリティ
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding volatility features: {e}")
            raise
    
    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """統計的特徴量の追加"""
        try:
            periods = [10, 20, 50]
            
            for period in periods:
                # 歪度・尖度
                df[f'skewness_{period}'] = df['close'].rolling(period).skew()
                df[f'kurtosis_{period}'] = df['close'].rolling(period).kurt()
                
                # パーセンタイル
                df[f'percentile_10_{period}'] = df['close'].rolling(period).quantile(0.1)
                df[f'percentile_90_{period}'] = df['close'].rolling(period).quantile(0.9)
                df[f'percentile_position_{period}'] = (
                    df['close'] - df[f'percentile_10_{period}']
                ) / (df[f'percentile_90_{period}'] - df[f'percentile_10_{period}'])
                
                # Z-Score
                df[f'zscore_{period}'] = (
                    df['close'] - df['close'].rolling(period).mean()
                ) / df['close'].rolling(period).std()
                
                # 最高値・最安値からの位置
                df[f'high_position_{period}'] = (
                    df['close'] - df['close'].rolling(period).min()
                ) / (df['close'].rolling(period).max() - df['close'].rolling(period).min())
                
            # 自己相関
            for lag in [1, 5, 10]:
                df[f'autocorr_{lag}'] = df['close'].rolling(50).apply(
                    lambda x: x.autocorr(lag=lag), raw=False
                )
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding statistical features: {e}")
            raise
    
    def _add_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """パターン認識特徴量の追加"""
        try:
            # TALIBのパターン認識関数
            pattern_functions = [
                'CDL2CROWS', 'CDL3BLACKCROWS', 'CDL3INSIDE', 'CDL3LINESTRIKE',
                'CDL3OUTSIDE', 'CDL3STARSINSOUTH', 'CDL3WHITESOLDIERS',
                'CDLABANDONEDBABY', 'CDLADVANCEBLOCK', 'CDLBELTHOLD',
                'CDLBREAKAWAY', 'CDLCLOSINGMARUBOZU', 'CDLCONCEALBABYSWALL',
                'CDLCOUNTERATTACK', 'CDLDARKCLOUDCOVER', 'CDLDOJI',
                'CDLDOJISTAR', 'CDLDRAGONFLYDOJI', 'CDLENGULFING',
                'CDLEVENINGDOJISTAR', 'CDLEVENINGSTAR', 'CDLGAPSIDESIDEWHITE',
                'CDLGRAVESTONEDOJI', 'CDLHAMMER', 'CDLHANGINGMAN',
                'CDLHARAMI', 'CDLHARAMICROSS', 'CDLHIGHWAVE', 'CDLHIKKAKE',
                'CDLHIKKAKEMOD', 'CDLHOMINGPIGEON', 'CDLIDENTICAL3CROWS',
                'CDLINNECK', 'CDLINVERTEDHAMMER', 'CDLKICKING',
                'CDLKICKINGBYLENGTH', 'CDLLADDERBOTTOM', 'CDLLONGLEGGEDDOJI',
                'CDLLONGLINE', 'CDLMARUBOZU', 'CDLMATCHINGLOW',
                'CDLMATHOLD', 'CDLMORNINGDOJISTAR', 'CDLMORNINGSTAR',
                'CDLONNECK', 'CDLPIERCING', 'CDLRICKSHAWMAN',
                'CDLRISEFALL3METHODS', 'CDLSEPARATINGLINES', 'CDLSHOOTINGSTAR',
                'CDLSHORTLINE', 'CDLSPINNINGTOP', 'CDLSTALLEDPATTERN',
                'CDLSTICKSANDWICH', 'CDLTAKURI', 'CDLTASUKIGAP',
                'CDLTHRUSTING', 'CDLTRISTAR', 'CDLUNIQUE3RIVER',
                'CDLUPSIDEGAP2CROWS', 'CDLXSIDEGAP3METHODS'
            ]
            
            pattern_scores = []
            for pattern in pattern_functions[:20]:  # 上位20パターンのみ使用（計算量削減）
                try:
                    pattern_func = getattr(talib, pattern)
                    df[f'pattern_{pattern.lower()}'] = pattern_func(
                        df['open'], df['high'], df['low'], df['close']
                    )
                    pattern_scores.append(f'pattern_{pattern.lower()}')
                except:
                    continue
            
            # パターンスコアの合計
            if pattern_scores:
                df['pattern_bull_score'] = df[pattern_scores].apply(
                    lambda x: (x > 0).sum(), axis=1
                )
                df['pattern_bear_score'] = df[pattern_scores].apply(
                    lambda x: (x < 0).sum(), axis=1
                )
                df['pattern_net_score'] = df['pattern_bull_score'] - df['pattern_bear_score']
            
            # 価格パターン
            df['higher_high'] = (
                (df['high'] > df['high'].shift(1)) & 
                (df['high'].shift(1) > df['high'].shift(2))
            ).astype(int)
            
            df['lower_low'] = (
                (df['low'] < df['low'].shift(1)) & 
                (df['low'].shift(1) < df['low'].shift(2))
            ).astype(int)
            
            df['inside_bar'] = (
                (df['high'] <= df['high'].shift(1)) & 
                (df['low'] >= df['low'].shift(1))
            ).astype(int)
            
            df['outside_bar'] = (
                (df['high'] >= df['high'].shift(1)) & 
                (df['low'] <= df['low'].shift(1))
            ).astype(int)
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding pattern features: {e}")
            raise
    
    def _update_feature_columns(self, df: pd.DataFrame):
        """特徴量カラムリストを更新"""
        exclude_columns = ['open', 'high', 'low', 'close', 'volume', 'time', 
                          'symbol', 'timeframe', 'created_at']
        
        self.feature_columns = [col for col in df.columns 
                               if col not in exclude_columns and 
                               not col.startswith('target') and
                               not col.startswith('label')]
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """欠損値の処理"""
        try:
            # 前方補完
            df = df.fillna(method='ffill')
            
            # 残った欠損値は0で補完
            df = df.fillna(0)
            
            # 無限大値の処理
            df = df.replace([np.inf, -np.inf], 0)
            
            return df
            
        except Exception as e:
            logger.error(f"Error handling missing values: {e}")
            raise
    
    def get_feature_columns(self) -> List[str]:
        """特徴量カラム一覧を取得"""
        return self.feature_columns
    
    def get_feature_importance_names(self) -> Dict[str, str]:
        """特徴量の説明を取得"""
        descriptions = {
            'sma_': '単純移動平均',
            'ema_': '指数移動平均',
            'rsi_': 'RSI指標',
            'macd': 'MACD指標',
            'bb_': 'ボリンジャーバンド',
            'atr': 'ATR（平均真の値幅）',
            'stoch_': 'ストキャスティクス',
            'adx': 'ADX（平均方向性指数）',
            'cci': 'CCI（商品チャンネル指数）',
            'williams_r': 'ウィリアムズ%R',
            'volatility_': 'ボラティリティ',
            'price_change_': '価格変化率',
            'hour': '時間',
            'day_of_week': '曜日',
            'session': '市場セッション',
            'pattern_': 'ローソク足パターン'
        }
        return descriptions

if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    # サンプルデータ作成
    dates = pd.date_range('2023-01-01', periods=1000, freq='H')
    np.random.seed(42)
    
    close_prices = 100 + np.cumsum(np.random.randn(1000) * 0.1)
    sample_data = pd.DataFrame({
        'open': close_prices + np.random.randn(1000) * 0.05,
        'high': close_prices + np.abs(np.random.randn(1000) * 0.1),
        'low': close_prices - np.abs(np.random.randn(1000) * 0.1),
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, 1000)
    }, index=dates)
    
    # 特徴量エンジニアリング実行
    fe = FeatureEngineering()
    featured_data = fe.create_features(sample_data)
    
    print(f"Original columns: {len(sample_data.columns)}")
    print(f"Featured columns: {len(featured_data.columns)}")
    print(f"Feature columns: {len(fe.get_feature_columns())}")
    print(f"Sample features: {fe.get_feature_columns()[:10]}")