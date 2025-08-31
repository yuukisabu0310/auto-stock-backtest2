"""
ネットワーク接続とデータ取得テストスクリプト
"""

import logging
import requests
import yfinance as yf
from data_loader import DataLoader
from config import START_DATE, END_DATE

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_network_connection():
    """ネットワーク接続テスト"""
    logger.info("=== ネットワーク接続テスト ===")
    
    data_loader = DataLoader()
    
    # ネットワーク接続確認
    is_connected = data_loader._check_network_connection()
    logger.info(f"ネットワーク接続状態: {'成功' if is_connected else '失敗'}")
    
    return is_connected

def test_yahoo_finance_direct():
    """Yahoo Finance直接テスト"""
    logger.info("=== Yahoo Finance直接テスト ===")
    
    test_symbols = ["AAPL", "MSFT", "7203.T"]
    
    for symbol in test_symbols:
        logger.info(f"銘柄 {symbol} の直接テスト")
        
        try:
            # 直接yfinanceを使用
            ticker = yf.Ticker(symbol)
            data = ticker.history(start="2024-01-01", end="2024-01-31", interval="1d")
            
            if not data.empty:
                logger.info(f"✅ 成功: {symbol} - データ形状: {data.shape}")
                logger.info(f"   期間: {data.index.min()} から {data.index.max()}")
            else:
                logger.warning(f"⚠️ データ空: {symbol}")
                
        except Exception as e:
            logger.error(f"❌ エラー: {symbol} - {e}")

def test_data_loader():
    """DataLoaderテスト"""
    logger.info("=== DataLoaderテスト ===")
    
    data_loader = DataLoader()
    test_symbols = ["AAPL", "MSFT", "7203.T"]
    
    for symbol in test_symbols:
        logger.info(f"銘柄 {symbol} のDataLoaderテスト")
        
        try:
            data = data_loader.get_stock_data(symbol, "2024-01-01", "2024-01-31")
            
            if not data.empty:
                logger.info(f"✅ 成功: {symbol} - データ形状: {data.shape}")
                logger.info(f"   期間: {data.index.min()} から {data.index.max()}")
                logger.info(f"   カラム: {list(data.columns)}")
            else:
                logger.warning(f"⚠️ データ空: {symbol}")
                
        except Exception as e:
            logger.error(f"❌ エラー: {symbol} - {e}")

def test_alternative_data_sources():
    """代替データソーステスト"""
    logger.info("=== 代替データソーステスト ===")
    
    # 複数のエンドポイントをテスト
    endpoints = [
        "https://finance.yahoo.com",
        "https://www.google.com/finance",
        "https://www.marketwatch.com",
        "https://www.investing.com"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            if response.status_code == 200:
                logger.info(f"✅ 接続成功: {endpoint}")
            else:
                logger.warning(f"⚠️ ステータスエラー: {endpoint} - {response.status_code}")
        except Exception as e:
            logger.error(f"❌ 接続失敗: {endpoint} - {e}")

if __name__ == "__main__":
    print("ネットワーク接続とデータ取得テスト開始")
    print("=" * 50)
    
    # 1. ネットワーク接続テスト
    network_ok = test_network_connection()
    print()
    
    # 2. Yahoo Finance直接テスト
    test_yahoo_finance_direct()
    print()
    
    # 3. DataLoaderテスト
    test_data_loader()
    print()
    
    # 4. 代替データソーステスト
    test_alternative_data_sources()
    print()
    
    print("=" * 50)
    print("テスト完了")
    
    if network_ok:
        print("✅ ネットワーク接続は正常です")
    else:
        print("❌ ネットワーク接続に問題があります")
        print("   プロキシ設定やファイアウォールを確認してください")
