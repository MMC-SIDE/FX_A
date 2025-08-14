"""
LightGBMPredictor単体テスト
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from backend.ml.lightgbm_predictor import LightGBMPredictor
from backend.ml.feature_engineering import FeatureEngineering


class TestLightGBMPredictor:
    """LightGBMPredictorのテストクラス"""

    @pytest.fixture
    def predictor(self):
        """LightGBMPredictorインスタンス作成"""
        return LightGBMPredictor()

    @pytest.fixture
    def feature_engineer(self):
        """FeatureEngineeringインスタンス作成"""
        return FeatureEngineering()

    def test_prepare_labels_basic(self, predictor, sample_price_data):
        """基本的なラベル作成テスト"""
        # ラベル作成
        df_with_labels = predictor.prepare_labels(sample_price_data)
        
        # 必要なカラムが追加されていることを確認
        assert 'label' in df_with_labels.columns
        assert 'future_return' in df_with_labels.columns
        
        # ラベルが0, 1, 2のいずれかであることを確認
        valid_labels = df_with_labels['label'].dropna()
        assert all(label in [0, 1, 2] for label in valid_labels)
        
        # 将来リターンが計算されていることを確認
        assert df_with_labels['future_return'].notna().sum() > 0

    def test_prepare_labels_thresholds(self, predictor, sample_price_data):
        """異なる閾値でのラベル作成テスト"""
        # カスタム閾値設定
        df_with_labels = predictor.prepare_labels(
            sample_price_data, 
            lookforward_periods=5,
            sell_threshold=-0.5,
            buy_threshold=0.5
        )
        
        # ラベルが適切に分類されていることを確認
        labels = df_with_labels['label'].dropna()
        assert len(labels) > 0
        
        # 各ラベルの分布を確認（少なくとも2つのクラスは存在すべき）
        unique_labels = labels.unique()
        assert len(unique_labels) >= 2

    def test_prepare_labels_edge_cases(self, predictor):
        """エッジケースでのラベル作成テスト"""
        # 少量データでのテスト
        small_data = pd.DataFrame({
            'time': pd.date_range('2023-01-01', periods=5, freq='H'),
            'open': [130.0, 130.1, 130.2, 130.1, 130.0],
            'high': [130.1, 130.2, 130.3, 130.2, 130.1],
            'low': [129.9, 130.0, 130.1, 130.0, 129.9],
            'close': [130.05, 130.15, 130.15, 130.05, 129.95],
            'tick_volume': [100, 120, 110, 105, 95]
        })
        
        df_with_labels = predictor.prepare_labels(small_data)
        
        # エラーが発生しないことを確認
        assert 'label' in df_with_labels.columns
        assert 'future_return' in df_with_labels.columns

    @patch('lightgbm.LGBMClassifier')
    def test_train_model_success(self, mock_lgbm, predictor, sample_price_data, feature_engineer):
        """モデル学習成功テスト"""
        # モックLGBMモデル設定
        mock_model = Mock()
        mock_model.fit.return_value = mock_model
        mock_model.predict.return_value = np.array([0, 1, 2, 1, 0])
        mock_model.predict_proba.return_value = np.array([
            [0.8, 0.1, 0.1],
            [0.2, 0.7, 0.1],
            [0.1, 0.2, 0.7],
            [0.3, 0.6, 0.1],
            [0.7, 0.2, 0.1]
        ])
        mock_lgbm.return_value = mock_model
        
        # 特徴量作成
        features = feature_engineer.create_features(sample_price_data)
        
        # ラベル作成
        labeled_data = predictor.prepare_labels(features)
        
        # NaN除去
        clean_data = labeled_data.dropna()
        
        if len(clean_data) > 50:  # 十分なデータがある場合
            X = clean_data.drop(['label', 'future_return'], axis=1)
            y = clean_data['label']
            
            # モデル学習
            metrics = predictor.train(X, y)
            
            # 結果確認
            assert 'accuracy' in metrics
            assert 'f1' in metrics
            assert 'precision' in metrics
            assert 'recall' in metrics
            assert predictor.model is not None
            assert predictor.feature_columns is not None
            
            # メトリクスが妥当な範囲内であることを確認
            assert 0 <= metrics['accuracy'] <= 1
            assert 0 <= metrics['f1'] <= 1

    def test_train_model_insufficient_data(self, predictor):
        """データ不足でのモデル学習テスト"""
        # 少量データ
        X = pd.DataFrame({
            'feature1': [1, 2, 3],
            'feature2': [4, 5, 6]
        })
        y = pd.Series([0, 1, 2])
        
        # データ不足でエラーになることを確認
        with pytest.raises(ValueError, match="Insufficient data"):
            predictor.train(X, y)

    def test_train_model_single_class(self, predictor):
        """単一クラスでのモデル学習テスト"""
        # 単一クラスのデータ
        X = pd.DataFrame({
            'feature1': range(100),
            'feature2': range(100, 200)
        })
        y = pd.Series([1] * 100)  # すべて同じクラス
        
        # 単一クラスでエラーになることを確認
        with pytest.raises(ValueError, match="Only one class"):
            predictor.train(X, y)

    @patch('lightgbm.LGBMClassifier')
    def test_predict_success(self, mock_lgbm, predictor, sample_price_data, feature_engineer):
        """予測成功テスト"""
        # モックモデル設定
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0, 1, 2, 1, 0])
        mock_model.predict_proba.return_value = np.array([
            [0.8, 0.1, 0.1],
            [0.2, 0.7, 0.1],
            [0.1, 0.2, 0.7],
            [0.3, 0.6, 0.1],
            [0.7, 0.2, 0.1]
        ])
        mock_lgbm.return_value = mock_model
        
        # モデル状態を設定
        predictor.model = mock_model
        predictor.feature_columns = ['feature1', 'feature2', 'feature3']
        
        # テストデータ作成
        test_features = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [6, 7, 8, 9, 10],
            'feature3': [11, 12, 13, 14, 15]
        })
        
        # 予測実行
        predictions, confidence = predictor.predict(test_features)
        
        # 結果確認
        assert len(predictions) == len(test_features)
        assert len(confidence) == len(test_features)
        assert all(p in [0, 1, 2] for p in predictions)
        assert all(0 <= c <= 1 for c in confidence)

    def test_predict_no_model(self, predictor):
        """未学習モデルでの予測テスト"""
        test_features = pd.DataFrame({
            'feature1': [1, 2, 3],
            'feature2': [4, 5, 6]
        })
        
        # 未学習モデルでエラーになることを確認
        with pytest.raises(ValueError, match="Model not trained"):
            predictor.predict(test_features)

    def test_predict_missing_features(self, predictor):
        """特徴量不足での予測テスト"""
        # モックモデル設定
        mock_model = Mock()
        predictor.model = mock_model
        predictor.feature_columns = ['feature1', 'feature2', 'feature3']
        
        # 不足した特徴量でのテストデータ
        test_features = pd.DataFrame({
            'feature1': [1, 2, 3],
            'feature2': [4, 5, 6]
            # feature3が不足
        })
        
        # 特徴量不足でエラーになることを確認
        with pytest.raises(ValueError, match="Missing features"):
            predictor.predict(test_features)

    def test_save_model(self, predictor, tmp_path):
        """モデル保存テスト"""
        # モックモデル設定
        mock_model = Mock()
        predictor.model = mock_model
        predictor.feature_columns = ['feature1', 'feature2']
        
        # 保存パス
        model_path = tmp_path / "test_model.pkl"
        
        with patch('joblib.dump') as mock_dump:
            predictor.save_model(str(model_path))
            mock_dump.assert_called_once()

    def test_save_model_no_model(self, predictor, tmp_path):
        """未学習モデル保存テスト"""
        model_path = tmp_path / "test_model.pkl"
        
        # 未学習モデルでエラーになることを確認
        with pytest.raises(ValueError, match="No model to save"):
            predictor.save_model(str(model_path))

    def test_load_model(self, predictor, tmp_path):
        """モデル読み込みテスト"""
        model_path = tmp_path / "test_model.pkl"
        
        # モックデータ
        mock_data = {
            'model': Mock(),
            'feature_columns': ['feature1', 'feature2'],
            'metadata': {'version': '1.0', 'created_at': '2023-01-01'}
        }
        
        with patch('joblib.load', return_value=mock_data):
            predictor.load_model(str(model_path))
            
            assert predictor.model is not None
            assert predictor.feature_columns == ['feature1', 'feature2']

    def test_load_model_file_not_found(self, predictor):
        """存在しないモデルファイル読み込みテスト"""
        with pytest.raises(FileNotFoundError):
            predictor.load_model("nonexistent_model.pkl")

    def test_get_feature_importance(self, predictor):
        """特徴量重要度取得テスト"""
        # モックモデル設定
        mock_model = Mock()
        mock_model.feature_importances_ = np.array([0.3, 0.2, 0.5])
        predictor.model = mock_model
        predictor.feature_columns = ['rsi', 'macd', 'bollinger']
        
        importance = predictor.get_feature_importance()
        
        assert len(importance) == 3
        assert 'rsi' in importance
        assert 'macd' in importance
        assert 'bollinger' in importance
        assert importance['bollinger'] == 0.5  # 最も重要

    def test_get_feature_importance_no_model(self, predictor):
        """未学習モデルでの特徴量重要度取得テスト"""
        # 未学習モデルでエラーになることを確認
        with pytest.raises(ValueError, match="Model not trained"):
            predictor.get_feature_importance()

    def test_evaluate_model(self, predictor):
        """モデル評価テスト"""
        # 実際のラベルと予測結果
        y_true = np.array([0, 1, 2, 1, 0, 2, 1, 0])
        y_pred = np.array([0, 1, 1, 1, 0, 2, 2, 0])
        
        metrics = predictor.evaluate_model(y_true, y_pred)
        
        assert 'accuracy' in metrics
        assert 'f1' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        
        # メトリクスが妥当な範囲内であることを確認
        assert 0 <= metrics['accuracy'] <= 1
        assert 0 <= metrics['f1'] <= 1

    def test_cross_validate(self, predictor, sample_price_data, feature_engineer):
        """クロスバリデーションテスト"""
        # 特徴量とラベル作成
        features = feature_engineer.create_features(sample_price_data)
        labeled_data = predictor.prepare_labels(features)
        clean_data = labeled_data.dropna()
        
        if len(clean_data) > 100:  # 十分なデータがある場合
            X = clean_data.drop(['label', 'future_return'], axis=1)
            y = clean_data['label']
            
            with patch('lightgbm.LGBMClassifier'):
                cv_scores = predictor.cross_validate(X, y, cv_folds=3)
                
                assert 'accuracy_scores' in cv_scores
                assert 'f1_scores' in cv_scores
                assert 'mean_accuracy' in cv_scores
                assert 'std_accuracy' in cv_scores
                
                # スコアが妥当な範囲内であることを確認
                assert 0 <= cv_scores['mean_accuracy'] <= 1

    def test_predict_single_sample(self, predictor):
        """単一サンプル予測テスト"""
        # モックモデル設定
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1])
        mock_model.predict_proba.return_value = np.array([[0.2, 0.7, 0.1]])
        predictor.model = mock_model
        predictor.feature_columns = ['feature1', 'feature2']
        
        # 単一サンプル
        sample = pd.DataFrame({
            'feature1': [1.5],
            'feature2': [2.5]
        })
        
        predictions, confidence = predictor.predict(sample)
        
        assert len(predictions) == 1
        assert len(confidence) == 1
        assert predictions[0] == 1
        assert confidence[0] == 0.7