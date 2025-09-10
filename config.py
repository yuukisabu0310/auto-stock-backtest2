"""
自動株式バックテストシステム設定ファイル
"""

import os
from datetime import datetime, timedelta

# 基本設定
# データ取得期間（去年12/31まで）
DATA_END_YEAR = datetime.now().year - 1  # 去年
DATA_START_DATE = "2004-12-31"  # 20年分のデータを取得するため
DATA_END_DATE = f"{DATA_END_YEAR}-12-31"

# バックテスト期間（戦略別）
SWING_TRADING_YEARS = 5  # スイングトレード: 5年
LONG_TERM_YEARS = 20     # 中長期投資: 20年

# バックテスト期間計算
def get_backtest_period(strategy: str, execution_date: datetime = None) -> tuple:
    """
    戦略別のバックテスト期間を取得
    実行日の前月末日から過去N年を計算
    
    Args:
        strategy: 戦略名 ("swing_trading" or "long_term")
        execution_date: 実行日（Noneの場合は現在日時）
    
    Returns:
        tuple: (start_date, end_date) の文字列タプル
    """
    if execution_date is None:
        execution_date = datetime.now()
    
    if strategy == "swing_trading":
        years = SWING_TRADING_YEARS
    elif strategy == "long_term":
        years = LONG_TERM_YEARS
    else:
        years = SWING_TRADING_YEARS  # デフォルト
    
    # 実行日の前月末日を計算
    if execution_date.month == 1:
        # 1月の場合は前年12月
        end_date = datetime(execution_date.year - 1, 12, 31)
    else:
        # その他の月は前月の最終日
        end_date = datetime(execution_date.year, execution_date.month, 1) - timedelta(days=1)
    
    # 前月末日から過去N年を計算
    start_date = datetime(end_date.year - years + 1, end_date.month, 1)
    
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def get_dynamic_backtest_period(strategy: str) -> tuple:
    """
    動的なバックテスト期間を取得（実行日基準）
    既存コードとの互換性のため
    """
    return get_backtest_period(strategy, datetime.now())

# 後方互換性のため（既存コード用）
START_DATE = "2020-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")
INITIAL_CAPITAL = 10000000  # 1000万円

# パフォーマンス設定
MAX_WORKERS = 8  # 並列処理の最大ワーカー数（5から8に増加）
BATCH_SIZE = 10  # バッチ処理のサイズ
CACHE_ENABLED = True  # キャッシュの有効/無効
RETRY_DELAY = 2  # リトライ間隔（秒）

# データ取得設定
DATA_FETCH_TIMEOUT = 30  # データ取得タイムアウト（秒）
MAX_RETRIES = 3  # 最大リトライ回数
DATA_SOURCE = "stooq"
CACHE_DIR = "cache"
REPORT_DIR = "reports"

# バックテスト対象銘柄数（ローカルテスト用に削減）
STOCKS_PER_CATEGORY = 50  # 100から50に削減

# ローカルテスト用設定
LOCAL_TEST_MODE = True  # ローカルテストモード
LOCAL_TEST_STOCKS = 30  # ローカルテスト時の銘柄数
LOCAL_TEST_RUNS = 2     # ローカルテスト時の実行回数

# トレードルール設定
TRADING_RULES = {
    # デイトレード戦略を除去
    # 理由: 5分足データの取得制限により、Yahoo Finance APIから十分なデータを取得できない
    # 5分足は過去30日分のみの制限があり、長期バックテストに不適切
    # また、レート制限（HTTP 429）により、高頻度データ取得が困難
    
    "swing_trading": {
        "name": "スイングトレード",
        "timeframe": "1d",
        "max_holding_days": 30,
        "max_positions": 5,
        "risk_per_trade": 0.015,  # 1.5%
        "max_position_size": 0.25,  # 25%
        "entry_conditions": {
            "golden_cross": True,  # 5日 > 25日
            "rsi_range": (40, 50),
            "volume_multiplier": 1.5,  # 20日平均の1.5倍以上
            "new_high_preference": True,
        },
        "exit_conditions": {
            "profit_target": 0.075,  # 7.5%
            "stop_loss": 0.05,  # 5%
            "rsi_overbought": 70,
            "below_ma25": True,
            "partial_profit": {
                "enabled": True,
                "first_target": 0.05,  # 5%で半分売却
                "second_target": 0.10,  # 10%で残り売却
            }
        }
    },
    "long_term": {
        "name": "中長期投資",
        "timeframe": "1wk",
        "max_holding_days": 365 * 2,  # 2年
        "max_positions": 10,
        "risk_per_trade": 0.015,  # 1.5%
        "max_position_size": 0.15,  # 15%
        "entry_conditions": {
            "above_ma200": True,  # 200日線上
            "fundamental_growth": True,
            "volume_new_high": True,
            "macro_environment": True,
        },
        "exit_conditions": {
            "profit_target": 0.30,  # 30%
            "stop_loss": 0.085,  # 8.5%
            "below_ma200": True,
            "fundamental_divergence": True,
        }
    }
}

# 技術指標パラメータ
TECHNICAL_INDICATORS = {
    "sma_short": 5,
    "sma_medium": 25,
    "sma_long": 200,
    "rsi_period": 14,
    "volume_period": 20,
    "bollinger_period": 20,
    "bollinger_std": 2,
}

# レポート設定
REPORT_TEMPLATES = {
    "html_template": "templates/report_template.html",
    "css_template": "templates/style.css",
}

# ログ設定
LOG_LEVEL = "INFO"
LOG_FILE = "logs/backtest.log"

# データベース設定（将来的な拡張用）
DATABASE = {
    "type": "sqlite",
    "path": "data/backtest.db"
}

# GitHub Actions設定
GITHUB_ACTIONS = {
    "schedule": "0 6 * * *",  # 毎日朝6時に実行
    "timezone": "Asia/Tokyo"
}
