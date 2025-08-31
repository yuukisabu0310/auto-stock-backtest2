"""
stooq.comからのデータ取得テストスクリプト
"""

import logging
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_stooq_direct():
    """stooq.comからの直接データ取得テスト"""
    logger.info("=== stooq.com直接テスト開始 ===")
    
    # テスト用銘柄（stooq.comの形式）
    test_symbols = [
        ("AAPL", "us"),  # 米国株
        ("MSFT", "us"), 
        ("7203", "jp"),  # 日本株（.Tなし）
        ("6758", "jp"),
        ("9984", "jp")
    ]
    
    for symbol, market in test_symbols:
        logger.info(f"\n--- {symbol} ({market}) テスト開始 ---")
        
        try:
            # stooq.comのURL形式
            if market == "jp":
                # 日本株の場合
                url = f"https://stooq.com/q/d/l/?s={symbol}.jp&d1=20200101&d2=20241231&i=d"
            else:
                # 米国株の場合
                url = f"https://stooq.com/q/d/l/?s={symbol}&d1=20200101&d2=20241231&i=d"
            
            logger.info(f"URL: {url}")
            
            # データ取得
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                logger.info(f"✅ HTTP 200: {symbol}")
                
                # CSVデータをパース
                try:
                    data = pd.read_csv(pd.StringIO(response.text))
                    logger.info(f"データ取得成功: {symbol}")
                    logger.info(f"データ形状: {data.shape}")
                    logger.info(f"カラム: {list(data.columns)}")
                    
                    if not data.empty:
                        logger.info(f"データサンプル:")
                        logger.info(data.head())
                        
                        # 日付範囲の確認
                        if 'Date' in data.columns:
                            data['Date'] = pd.to_datetime(data['Date'])
                            logger.info(f"期間: {data['Date'].min()} から {data['Date'].max()}")
                    else:
                        logger.warning(f"データが空: {symbol}")
                        
                except Exception as e:
                    logger.error(f"CSVパースエラー: {symbol}, {e}")
                    logger.error(f"レスポンス内容: {response.text[:500]}")
                    
            else:
                logger.error(f"❌ HTTP {response.status_code}: {symbol}")
                logger.error(f"レスポンス: {response.text[:200]}")
                
        except Exception as e:
            logger.error(f"❌ エラー: {symbol}")
            logger.error(f"  エラータイプ: {type(e).__name__}")
            logger.error(f"  エラーメッセージ: {str(e)}")
        
        # レート制限を避けるため少し待機
        time.sleep(1)

def test_stooq_pandas_datareader():
    """pandas-datareaderを使用したstooqテスト"""
    logger.info("=== pandas-datareader stooqテスト開始 ===")
    
    try:
        import pandas_datareader.data as web
        
        test_symbols = [
            ("AAPL", "us"),
            ("MSFT", "us"), 
            ("7203", "jp"),
            ("6758", "jp"),
            ("9984", "jp")
        ]
        
        for symbol, market in test_symbols:
            logger.info(f"\n--- pandas-datareader {symbol} ({market}) テスト ---")
            
            try:
                # stooq.comのシンボル形式
                if market == "jp":
                    stooq_symbol = f"{symbol}.jp"
                else:
                    stooq_symbol = symbol
                
                logger.info(f"stooqシンボル: {stooq_symbol}")
                
                # データ取得
                data = web.DataReader(
                    stooq_symbol, 
                    'stooq', 
                    start='2020-01-01', 
                    end='2024-12-31'
                )
                
                logger.info(f"✅ データ取得成功: {symbol}")
                logger.info(f"データ形状: {data.shape}")
                logger.info(f"カラム: {list(data.columns)}")
                
                if not data.empty:
                    logger.info(f"データサンプル:")
                    logger.info(data.head())
                    logger.info(f"期間: {data.index.min()} から {data.index.max()}")
                else:
                    logger.warning(f"データが空: {symbol}")
                    
            except Exception as e:
                logger.error(f"❌ pandas-datareaderエラー: {symbol}")
                logger.error(f"  エラータイプ: {type(e).__name__}")
                logger.error(f"  エラーメッセージ: {str(e)}")
            
            time.sleep(1)
            
    except ImportError:
        logger.error("pandas-datareaderがインストールされていません")
    except Exception as e:
        logger.error(f"pandas-datareaderテストエラー: {e}")

def test_stooq_url_patterns():
    """stooq.comのURLパターンをテスト"""
    logger.info("=== stooq.com URLパターンテスト ===")
    
    # 様々なURLパターンをテスト
    test_patterns = [
        # 基本パターン
        "https://stooq.com/q/d/l/?s=AAPL&d1=20200101&d2=20241231&i=d",
        "https://stooq.com/q/d/l/?s=7203.jp&d1=20200101&d2=20241231&i=d",
        
        # 週足パターン
        "https://stooq.com/q/d/l/?s=AAPL&d1=20200101&d2=20241231&i=w",
        "https://stooq.com/q/d/l/?s=7203.jp&d1=20200101&d2=20241231&i=w",
        
        # 月足パターン
        "https://stooq.com/q/d/l/?s=AAPL&d1=20200101&d2=20241231&i=m",
        "https://stooq.com/q/d/l/?s=7203.jp&d1=20200101&d2=20241231&i=m",
    ]
    
    for url in test_patterns:
        logger.info(f"\n--- URLテスト: {url} ---")
        
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                logger.info(f"✅ HTTP 200")
                
                # レスポンスの内容を確認
                content = response.text
                if "Date" in content and "Open" in content:
                    logger.info("✅ CSV形式のデータを確認")
                    
                    # 行数を確認
                    lines = content.strip().split('\n')
                    logger.info(f"データ行数: {len(lines)}")
                    
                    if len(lines) > 1:
                        logger.info("✅ 有効なデータを確認")
                    else:
                        logger.warning("⚠️ データ行が少ない")
                else:
                    logger.warning("⚠️ CSV形式ではない")
                    
            else:
                logger.error(f"❌ HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ エラー: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    logger.info("stooq.comデータ取得テスト開始")
    
    # 1. 直接URLテスト
    test_stooq_direct()
    
    # 2. pandas-datareaderテスト
    test_stooq_pandas_datareader()
    
    # 3. URLパターンテスト
    test_stooq_url_patterns()
    
    logger.info("stooq.comデータ取得テスト完了")
