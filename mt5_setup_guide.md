# MT5接続エラー解決ガイド

## エラー内容
- エラーコード: -6
- メッセージ: Terminal: Authorization failed
- 意味: MT5ターミナルへの認証に失敗

## 解決手順

### 1. MT5ターミナルの確認と起動

1. **MT5ターミナルをインストール**
   - XMTradingの公式サイトからMT5をダウンロード
   - インストール先: `C:\Program Files\XM Trading MT5\` (デフォルト)

2. **MT5ターミナルを起動**
   - デスクトップのショートカットから「XM Trading MT5」を起動
   - または `C:\Program Files\XM Trading MT5\terminal64.exe` を実行

3. **手動でログイン**
   - MT5ターミナルで以下の情報でログイン:
     - ログインID: 72009058
     - パスワード: 5@u$pAxhPSKy2cp
     - サーバー: XMTrading-MT5 3

### 2. 自動売買の許可設定

MT5ターミナルで以下の設定を行う:

1. **メニューから設定を開く**
   - ツール → オプション（または Ctrl+O）

2. **エキスパートアドバイザタブ**
   - ✅ 自動売買を許可する
   - ✅ DLLの使用を許可する（信頼できるアプリケーションのみ）
   - ✅ WebRequestを許可するURLリスト（必要な場合）

3. **設定を適用**
   - OKをクリックして設定を保存

### 3. Python環境からの接続テスト

管理者権限でコマンドプロンプトを開いて実行:

```bash
# 管理者権限でコマンドプロンプトを開く
# スタートメニュー → cmd → 右クリック → 管理者として実行

cd C:\app\FX_A
python test_mt5_connection.py
```

### 4. 追加の確認事項

#### ファイアウォール/アンチウイルス
- MT5とPythonの通信がブロックされていないか確認
- Windows Defenderの例外にMT5とPythonを追加

#### アカウント状態
- デモ口座の有効期限が切れていないか
- アカウントがロックされていないか
- サーバー名が正しいか（大文字小文字も含めて）

#### ネットワーク
- インターネット接続が安定しているか
- プロキシ設定が必要な場合は設定する

### 5. 代替案: モックモードでの開発

MT5に接続できない場合でも開発を続けるため、モックモードが用意されています:

```python
# backend/core/mt5_client.py では
# MT5が利用できない場合、自動的にモックモードで動作
MT5_AVAILABLE = False  # モックモードになる
```

## トラブルシューティング

### よくある問題と解決策

1. **「Terminal: Authorization failed」エラー**
   - MT5ターミナルが起動していない → 起動する
   - 自動売買が許可されていない → オプションで許可する
   - 認証情報が間違っている → config/mt5_config.jsonを確認

2. **「ModuleNotFoundError: No module named 'MetaTrader5'」**
   ```bash
   pip install MetaTrader5
   ```

3. **「MT5 initialization failed」**
   - MT5を管理者権限で起動
   - Pythonスクリプトも管理者権限で実行

4. **接続は成功するが、データが取得できない**
   - 通貨ペア名を確認（例: "USDJPY" vs "USDJPY.a"）
   - マーケットが開いているか確認（週末は閉場）

## 確認用コマンド

```bash
# MT5モジュールの確認
python -c "import MetaTrader5 as mt5; print(mt5.__version__)"

# 簡易接続テスト
python -c "import MetaTrader5 as mt5; print('Init:', mt5.initialize()); mt5.shutdown()"

# 詳細テスト
python test_mt5_connection.py
```

## 次のステップ

1. 上記の手順を実行してMT5への接続を確立
2. 接続成功後、`python backend/main.py`でバックエンドを起動
3. `npm run dev`でフロントエンドを起動
4. http://localhost:3000 でシステムにアクセス