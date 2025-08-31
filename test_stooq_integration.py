"""
stooq.com統合テストスクリプト
"""

import logging
import pandas as pd
from data_loader import DataLoader
from config import START_DATE, END_DATE

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_stooq_integration():
    """stooq.com統合テスト"""
    logger.info("=== stooq.com統合テスト開始 ===")
    
    # DataLoaderの初期化
    data_loader = DataLoader()
    
    # テスト用銘柄
    test_symbols = ["AAPL", "MSFT", "GOOGL", "7203.T", "6758.T", "9984.T"]
    
    for symbol in test_symbols:
        logger.info(f"\n--- {symbol} 統合テスト ---")
        
        try:
            # データ取得
            data = data_loader.get_stock_data(symbol, START_DATE, END_DATE)
            
            if not data.empty:
                logger.info(f"✅ データ取得成功: {symbol}")
                logger.info(f"データ形状: {data.shape}")
                logger.info(f"期間: {data.index.min()} から {data.index.max()}")
                logger.info(f"カラム: {list(data.columns)}")
                
                # データ検証
                is_valid = data_loader.validate_data(data)
                logger.info(f"データ妥当性: {is_valid}")
                
                if is_valid:
                    # データクリーニング
                    cleaned_data = data_loader.clean_data(data)
                    logger.info(f"クリーニング後データ形状: {cleaned_data.shape}")
                    
                    # サンプルデータ表示
                    logger.info("サンプルデータ:")
                    logger.info(cleaned_data.head())
                else:
                    logger.warning(f"⚠️ データが妥当ではありません: {symbol}")
            else:
                logger.error(f"❌ データが空: {symbol}")
                
        except Exception as e:
            logger.error(f"❌ エラー: {symbol}")
            logger.error(f"  エラータイプ: {type(e).__name__}")
            logger.error(f"  エラーメッセージ: {str(e)}")

def test_stooq_vs_yahoo():
    """stooq.comとYahoo Financeの比較テスト"""
    logger.info("=== stooq.com vs Yahoo Finance比較テスト ===")
    
    data_loader = DataLoader()
    test_symbols = ["AAPL", "7203.T"]
    
    for symbol in test_symbols:
        logger.info(f"\n--- {symbol} 比較テスト ---")
        
        try:
            # stooq.comからデータ取得
            logger.info("stooq.comからデータ取得中...")
            stooq_data = data_loader._get_from_stooq(symbol, START_DATE, END_DATE, "1d", 3)
            
            if not stooq_data.empty:
                logger.info(f"✅ stooq.comデータ取得成功")
                logger.info(f"stooq.comデータ形状: {stooq_data.shape}")
                logger.info(f"stooq.com期間: {stooq_data.index.min()} から {stooq_data.index.max()}")
            else:
                logger.warning("⚠️ stooq.comデータが空")
                
        except Exception as e:
            logger.error(f"❌ stooq.comエラー: {e}")
        
        try:
            # Yahoo Financeからデータ取得
            logger.info("Yahoo Financeからデータ取得中...")
            yahoo_data = data_loader._get_from_yahoo_finance(symbol, START_DATE, END_DATE, "1d", 3)
            
            if not yahoo_data.empty:
                logger.info(f"✅ Yahoo Financeデータ取得成功")
                logger.info(f"Yahoo Financeデータ形状: {yahoo_data.shape}")
                logger.info(f"Yahoo Finance期間: {yahoo_data.index.min()} から {yahoo_data.index.max()}")
            else:
                logger.warning("⚠️ Yahoo Financeデータが空")
                
        except Exception as e:
            logger.error(f"❌ Yahoo Financeエラー: {e}")

def test_different_intervals():
    """異なる時間足でのテスト"""
    logger.info("=== 異なる時間足テスト ===")
    
    data_loader = DataLoader()
    test_symbol = "7203.T"
    intervals = ["1d", "1wk"]
    
    for interval in intervals:
        logger.info(f"\n--- {interval} 時間足テスト ---")
        
        try:
            data = data_loader._get_from_stooq(test_symbol, START_DATE, END_DATE, interval, 3)
            
            if not data.empty:
                logger.info(f"✅ {interval}データ取得成功")
                logger.info(f"データ形状: {data.shape}")
                logger.info(f"期間: {data.index.min()} から {data.index.max()}")
                
                # サンプルデータ表示
                logger.info("サンプルデータ:")
                logger.info(data.head())
            else:
                logger.warning(f"⚠️ {interval}データが空")
                
        except Exception as e:
            logger.error(f"❌ {interval}エラー: {e}")

if __name__ == "__main__":
    logger.info("stooq.com統合テスト開始")
    
    # 1. 統合テスト
    test_stooq_integration()
    
    # 2. 比較テスト
    test_stooq_vs_yahoo()
    
    # 3. 時間足テスト
    test_different_intervals()
    
    logger.info("stooq.com統合テスト完了")
