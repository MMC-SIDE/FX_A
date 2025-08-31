"""
取引可能な通貨ペアと時間軸の設定
"""

# メジャー通貨ペア (Major Pairs)
MAJOR_PAIRS = [
    "USDJPY",  # 米ドル/円
    "EURUSD",  # ユーロ/米ドル
    "GBPUSD",  # ポンド/米ドル
    "USDCHF",  # 米ドル/スイスフラン
    "AUDUSD",  # 豪ドル/米ドル
    "USDCAD",  # 米ドル/カナダドル
    "NZDUSD",  # NZドル/米ドル
]

# クロス円ペア (JPY Cross Pairs)
JPY_CROSS_PAIRS = [
    "EURJPY",  # ユーロ/円
    "GBPJPY",  # ポンド/円
    "AUDJPY",  # 豪ドル/円
    "NZDJPY",  # NZドル/円
    "CADJPY",  # カナダドル/円
    "CHFJPY",  # スイスフラン/円
]

# その他のクロスペア (Other Cross Pairs)
OTHER_CROSS_PAIRS = [
    "EURGBP",  # ユーロ/ポンド
    "EURAUD",  # ユーロ/豪ドル
    "EURCAD",  # ユーロ/カナダドル
    "EURNZD",  # ユーロ/NZドル
    "EURCHF",  # ユーロ/スイスフラン
    "GBPAUD",  # ポンド/豪ドル
    "GBPCAD",  # ポンド/カナダドル
    "GBPNZD",  # ポンド/NZドル
    "GBPCHF",  # ポンド/スイスフラン
    "AUDCAD",  # 豪ドル/カナダドル
    "AUDNZD",  # 豪ドル/NZドル
    "AUDCHF",  # 豪ドル/スイスフラン
    "NZDCAD",  # NZドル/カナダドル
    "NZDCHF",  # NZドル/スイスフラン
    "CADCHF",  # カナダドル/スイスフラン
]

# エキゾチック通貨ペア (Exotic Pairs)
EXOTIC_PAIRS = [
    "USDMXN",  # 米ドル/メキシコペソ
    "USDZAR",  # 米ドル/南アフリカランド
    "USDTRY",  # 米ドル/トルコリラ
    "USDSEK",  # 米ドル/スウェーデンクローナ
    "USDNOK",  # 米ドル/ノルウェークローネ
    "USDDKK",  # 米ドル/デンマーククローネ
    "USDSGD",  # 米ドル/シンガポールドル
    "USDHKD",  # 米ドル/香港ドル
    "USDCNH",  # 米ドル/人民元
    "EURTRY",  # ユーロ/トルコリラ
    "EURPLN",  # ユーロ/ポーランドズロチ
    "EURHUF",  # ユーロ/ハンガリーフォリント
    "EURCZK",  # ユーロ/チェココルナ
]

# 貴金属 (Precious Metals)
METALS = [
    "XAUUSD",  # 金/米ドル
    "XAGUSD",  # 銀/米ドル
    "XAUEUR",  # 金/ユーロ
    "XAGEUR",  # 銀/ユーロ
    "XAUAUD",  # 金/豪ドル
    "XAUGBP",  # 金/ポンド
    "XAUJPY",  # 金/円
]

# エネルギー (Energy)
ENERGY = [
    "USOIL",   # WTI原油
    "UKOIL",   # ブレント原油
    "NGAS",    # 天然ガス
]

# 株価指数 (Stock Indices)
INDICES = [
    "US30",    # ダウ工業株30種平均
    "US500",   # S&P 500
    "NAS100",  # ナスダック100
    "JP225",   # 日経225
    "GER40",   # ドイツDAX40
    "UK100",   # イギリスFTSE 100
    "FRA40",   # フランスCAC 40
    "EU50",    # ユーロストックス50
    "AUS200",  # オーストラリアASX 200
    "HK50",    # 香港ハンセン50
]

# 仮想通貨 (Cryptocurrencies) - ブローカーがサポートしている場合
CRYPTO = [
    "BTCUSD",  # ビットコイン/米ドル
    "ETHUSD",  # イーサリアム/米ドル
    "XRPUSD",  # リップル/米ドル
    "LTCUSD",  # ライトコイン/米ドル
    "BCHUSD",  # ビットコインキャッシュ/米ドル
]

# 全通貨ペアリスト
ALL_FOREX_PAIRS = MAJOR_PAIRS + JPY_CROSS_PAIRS + OTHER_CROSS_PAIRS + EXOTIC_PAIRS
ALL_INSTRUMENTS = ALL_FOREX_PAIRS + METALS + ENERGY + INDICES + CRYPTO

# デフォルトで使用する通貨ペア
DEFAULT_PAIRS = MAJOR_PAIRS + JPY_CROSS_PAIRS

# 時間軸 (Timeframes)
TIMEFRAMES = {
    "M1": "1分足",
    "M5": "5分足",
    "M15": "15分足",
    "M30": "30分足",
    "H1": "1時間足",
    "H4": "4時間足",
    "D1": "日足",
    "W1": "週足",
    "MN1": "月足"
}

# MT5での時間軸定数
MT5_TIMEFRAMES = {
    "M1": 1,      # TIMEFRAME_M1
    "M5": 5,      # TIMEFRAME_M5
    "M15": 15,    # TIMEFRAME_M15
    "M30": 30,    # TIMEFRAME_M30
    "H1": 60,     # TIMEFRAME_H1
    "H4": 240,    # TIMEFRAME_H4
    "D1": 1440,   # TIMEFRAME_D1
    "W1": 10080,  # TIMEFRAME_W1
    "MN1": 43200  # TIMEFRAME_MN1
}

# デフォルトで使用する時間軸
DEFAULT_TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]

# 通貨ペアのカテゴリ
PAIR_CATEGORIES = {
    "メジャー通貨": MAJOR_PAIRS,
    "クロス円": JPY_CROSS_PAIRS,
    "その他クロス": OTHER_CROSS_PAIRS,
    "エキゾチック": EXOTIC_PAIRS,
    "貴金属": METALS,
    "エネルギー": ENERGY,
    "株価指数": INDICES,
    "仮想通貨": CRYPTO
}

# 通貨ペアの詳細情報
PAIR_INFO = {
    "USDJPY": {
        "name": "米ドル/円",
        "pip_size": 0.01,
        "pip_value": 100,
        "typical_spread": 0.3,
        "min_lot": 0.01,
        "max_lot": 100,
        "category": "major"
    },
    "EURUSD": {
        "name": "ユーロ/米ドル",
        "pip_size": 0.0001,
        "pip_value": 10,
        "typical_spread": 0.2,
        "min_lot": 0.01,
        "max_lot": 100,
        "category": "major"
    },
    "GBPJPY": {
        "name": "ポンド/円",
        "pip_size": 0.01,
        "pip_value": 100,
        "typical_spread": 1.0,
        "min_lot": 0.01,
        "max_lot": 100,
        "category": "jpy_cross"
    },
    "XAUUSD": {
        "name": "金/米ドル",
        "pip_size": 0.01,
        "pip_value": 1,
        "typical_spread": 0.3,
        "min_lot": 0.01,
        "max_lot": 50,
        "category": "metal"
    }
    # 他の通貨ペアも必要に応じて追加
}

def get_pair_info(symbol: str) -> dict:
    """通貨ペア情報を取得"""
    default_info = {
        "name": symbol,
        "pip_size": 0.0001 if "JPY" not in symbol else 0.01,
        "pip_value": 10 if "JPY" not in symbol else 100,
        "typical_spread": 1.0,
        "min_lot": 0.01,
        "max_lot": 100,
        "category": "other"
    }
    return PAIR_INFO.get(symbol, default_info)

def get_pairs_by_category(category: str) -> list:
    """カテゴリ別に通貨ペアを取得"""
    return PAIR_CATEGORIES.get(category, [])

def is_valid_pair(symbol: str) -> bool:
    """有効な通貨ペアかチェック"""
    return symbol in ALL_INSTRUMENTS

def is_valid_timeframe(timeframe: str) -> bool:
    """有効な時間軸かチェック"""
    return timeframe in TIMEFRAMES