# チケット004: LightGBM機械学習エンジン

## 概要
LightGBMを使用した売買シグナル予測モデルの実装。

## 目的
- 価格データから特徴量を抽出
- LightGBMモデルによる売買シグナル生成
- モデルの学習・評価・予測パイプライン構築

## 要件
- テクニカル指標による特徴量エンジニアリング
- 時間的特徴量（時間帯、曜日）の追加
- LightGBMモデルの学習・予測
- モデルの保存・読み込み機能

## 受け入れ基準
- [ ] 特徴量エンジニアリング機能の実装
- [ ] LightGBMモデルの学習機能
- [ ] モデル評価・検証機能
- [ ] リアルタイム予測機能
- [ ] モデル管理（保存・読み込み）機能

## 技術仕様

### 特徴量エンジニアリング
```python
# backend/ml/features.py
class FeatureEngineering:
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
            'williams_r': 14
        }
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """特徴量作成メイン関数"""
        # テクニカル指標
        df = self._add_technical_indicators(df)
        # 価格変化率
        df = self._add_price_changes(df)
        # 時間的特徴量
        df = self._add_time_features(df)
        # ボラティリティ指標
        df = self._add_volatility_features(df)
        return df
```

### テクニカル指標実装
```python
def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
    """テクニカル指標の追加"""
    
    # 移動平均線
    for period in self.technical_indicators['sma']:
        df[f'sma_{period}'] = talib.SMA(df['close'], timeperiod=period)
        df[f'price_sma_{period}_ratio'] = df['close'] / df[f'sma_{period}']
    
    # 指数移動平均
    for period in self.technical_indicators['ema']:
        df[f'ema_{period}'] = talib.EMA(df['close'], timeperiod=period)
    
    # RSI
    for period in self.technical_indicators['rsi']:
        df[f'rsi_{period}'] = talib.RSI(df['close'], timeperiod=period)
    
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
    
    return df
```

### 時間的特徴量
```python
def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
    """時間的特徴量の追加"""
    df['hour'] = df.index.hour
    df['day_of_week'] = df.index.dayofweek
    df['month'] = df.index.month
    
    # 市場セッション
    df['tokyo_session'] = ((df['hour'] >= 0) & (df['hour'] < 9)).astype(int)
    df['london_session'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)
    df['ny_session'] = ((df['hour'] >= 13) & (df['hour'] < 22)).astype(int)
    
    # 経済指標発表前後フラグ（後で実装）
    df['news_event'] = 0
    
    return df
```

### LightGBMモデル
```python
# backend/ml/models/lightgbm_model.py
class LightGBMPredictor:
    def __init__(self, params: dict = None):
        self.params = params or self._default_params()
        self.model = None
        self.feature_columns = None
        
    def _default_params(self) -> dict:
        return {
            'objective': 'multiclass',
            'num_class': 3,  # 0: HOLD, 1: BUY, 2: SELL
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': 42
        }
    
    def prepare_labels(self, df: pd.DataFrame, 
                      lookforward: int = 24) -> pd.DataFrame:
        """ラベル作成（将来の価格変動から売買シグナルを生成）"""
        df = df.copy()
        
        # 将来の価格変動率を計算
        df['future_return'] = df['close'].shift(-lookforward) / df['close'] - 1
        
        # しきい値設定（ATRベース）
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        df['threshold'] = df['atr'] / df['close'] * 0.5  # ATRの50%をしきい値
        
        # ラベル生成
        conditions = [
            df['future_return'] > df['threshold'],   # BUY: 1
            df['future_return'] < -df['threshold'],  # SELL: 2
        ]
        choices = [1, 2]
        df['label'] = np.select(conditions, choices, default=0)  # HOLD: 0
        
        return df
    
    def train(self, X: pd.DataFrame, y: pd.Series, 
              validation_split: float = 0.2) -> dict:
        """モデル学習"""
        # データ分割
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # LightGBMデータセット作成
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
        
        # モデル学習
        self.model = lgb.train(
            self.params,
            train_data,
            valid_sets=[train_data, val_data],
            num_boost_round=1000,
            callbacks=[
                lgb.early_stopping(stopping_rounds=50),
                lgb.log_evaluation(period=100)
            ]
        )
        
        self.feature_columns = X_train.columns.tolist()
        
        # 評価指標計算
        y_pred = self.model.predict(X_val)
        y_pred_class = np.argmax(y_pred, axis=1)
        
        metrics = {
            'accuracy': accuracy_score(y_val, y_pred_class),
            'precision': precision_score(y_val, y_pred_class, average='weighted'),
            'recall': recall_score(y_val, y_pred_class, average='weighted'),
            'f1': f1_score(y_val, y_pred_class, average='weighted')
        }
        
        return metrics
    
    def predict(self, X: pd.DataFrame) -> tuple:
        """予測実行"""
        if self.model is None:
            raise ValueError("Model not trained yet")
            
        # 特徴量順序の確認
        X = X[self.feature_columns]
        
        # 予測実行
        predictions = self.model.predict(X)
        predicted_classes = np.argmax(predictions, axis=1)
        confidence_scores = np.max(predictions, axis=1)
        
        return predicted_classes, confidence_scores
    
    def save_model(self, filepath: str):
        """モデル保存"""
        model_data = {
            'model': self.model,
            'feature_columns': self.feature_columns,
            'params': self.params
        }
        joblib.dump(model_data, filepath)
    
    def load_model(self, filepath: str):
        """モデル読み込み"""
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.feature_columns = model_data['feature_columns']
        self.params = model_data['params']
```

### モデル管理
```python
# backend/ml/model_manager.py
class ModelManager:
    def __init__(self, db_session):
        self.db = db_session
        
    def save_model(self, model: LightGBMPredictor, 
                   symbol: str, timeframe: str, 
                   version: str, metrics: dict):
        """モデルをDBに保存"""
        file_path = f"models/{symbol}_{timeframe}_{version}.joblib"
        model.save_model(file_path)
        
        # DB記録
        model_record = MLModel(
            model_name=f"lightgbm_{symbol}_{timeframe}",
            model_type="lightgbm",
            symbol=symbol,
            timeframe=timeframe,
            version=version,
            file_path=file_path,
            validation_score=metrics.get('f1', 0),
            parameters=model.params
        )
        self.db.add(model_record)
        self.db.commit()
    
    def load_latest_model(self, symbol: str, timeframe: str):
        """最新モデルの読み込み"""
        model_record = self.db.query(MLModel).filter(
            MLModel.symbol == symbol,
            MLModel.timeframe == timeframe,
            MLModel.is_active == True
        ).order_by(MLModel.created_at.desc()).first()
        
        if model_record:
            model = LightGBMPredictor()
            model.load_model(model_record.file_path)
            return model
        return None
```

## パフォーマンス目標
- 学習時間: 1時間以内（1年分データ）
- 予測時間: 100ms以内
- モデル精度: F1スコア 0.6以上

## 見積もり
**5日**

## 依存関係
- チケット002: MT5データ取得機能
- チケット003: データベース設計実装

## 完了条件
- [ ] 特徴量エンジニアリングが正常に動作する
- [ ] LightGBMモデルの学習が完了する
- [ ] 予測精度が目標値を上回る
- [ ] モデルの保存・読み込みが動作する
- [ ] リアルタイム予測APIが動作する