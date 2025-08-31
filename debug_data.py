"""
データ取得デバッグスクリプト
"""

import logging
import pandas as pd
from data_loader import DataLoader
from config import START_DATE, END_DATE

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_data_loading():
    """データ取得のテスト"""
    logger.info("データ取得テスト開始")
    
    # DataLoaderの初期化
    data_loader = DataLoader()
    
    # テスト用銘柄（より安定した銘柄）
    test_symbols = ["AAPL", "MSFT", "GOOGL", "7203.T", "6758.T", "9984.T"]
    
    for symbol in test_symbols:
        logger.info(f"銘柄 {symbol} のデータ取得テスト")
        
        # データ取得
        data = data_loader.get_stock_data(symbol, START_DATE, END_DATE)
        
        if data.empty:
            logger.error(f"データが空: {symbol}")
            continue
        
        logger.info(f"データ取得成功: {symbol}")
        logger.info(f"データ形状: {data.shape}")
        logger.info(f"データ期間: {data.index.min()} から {data.index.max()}")
        logger.info(f"カラム: {list(data.columns)}")
        
        # データ検証
        is_valid = data_loader.validate_data(data)
        logger.info(f"データ妥当性: {is_valid}")
        
        if is_valid:
            # データクリーニング
            cleaned_data = data_loader.clean_data(data)
            logger.info(f"クリーニング後データ形状: {cleaned_data.shape}")
        else:
            logger.warning(f"データが妥当ではありません: {symbol}")
        
        print("-" * 50)

def test_japanese_stocks():
    """日本株銘柄リストのテスト"""
    logger.info("日本株銘柄リストテスト")
    
    data_loader = DataLoader()
    
    categories = ["high", "medium", "low"]
    
    for category in categories:
        stocks = data_loader.get_japanese_stocks(category)
        logger.info(f"{category}流動性銘柄数: {len(stocks)}")
        logger.info(f"銘柄例: {stocks[:5]}")

if __name__ == "__main__":
    print("=== データ取得デバッグテスト ===")
    print(f"期間: {START_DATE} から {END_DATE}")
    print()
    
    test_japanese_stocks()
    print()
    test_data_loading()
