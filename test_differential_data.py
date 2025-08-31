#!/usr/bin/env python3
"""
差分取得機能のテストスクリプト
"""

import logging
import os
from data_loader import DataLoader

def test_differential_data():
    """差分取得機能のテスト"""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    logger = logging.getLogger(__name__)
    
    dl = DataLoader()
    
    # テスト1: 既存キャッシュから完全なデータを取得
    logger.info("=== テスト1: 既存キャッシュから完全なデータを取得 ===")
    data1 = dl.get_stock_data('AAPL', '2024-01-01', '2024-01-31')
    logger.info(f"データ1取得成功: {data1.shape}")
    
    # テスト2: 同じ期間で再度取得（キャッシュから取得されるはず）
    logger.info("\n=== テスト2: 同じ期間で再度取得 ===")
    data2 = dl.get_stock_data('AAPL', '2024-01-01', '2024-01-31')
    logger.info(f"データ2取得成功: {data2.shape}")
    
    # テスト3: より長い期間で取得（差分取得が発生するはず）
    logger.info("\n=== テスト3: より長い期間で取得 ===")
    data3 = dl.get_stock_data('AAPL', '2024-01-01', '2024-12-31')
    logger.info(f"データ3取得成功: {data3.shape}")
    
    # テスト4: より短い期間で取得（キャッシュから取得されるはず）
    logger.info("\n=== テスト4: より短い期間で取得 ===")
    data4 = dl.get_stock_data('AAPL', '2024-01-15', '2024-01-20')
    logger.info(f"データ4取得成功: {data4.shape}")
    
    # テスト5: 新しい銘柄で取得
    logger.info("\n=== テスト5: 新しい銘柄で取得 ===")
    data5 = dl.get_stock_data('MSFT', '2024-01-01', '2024-01-31')
    logger.info(f"データ5取得成功: {data5.shape}")
    
    # 結果の確認
    logger.info("\n=== 結果確認 ===")
    logger.info(f"データ1期間: {data1.index.min().date()} 〜 {data1.index.max().date()}")
    logger.info(f"データ2期間: {data2.index.min().date()} 〜 {data2.index.max().date()}")
    logger.info(f"データ3期間: {data3.index.min().date()} 〜 {data3.index.max().date()}")
    logger.info(f"データ4期間: {data4.index.min().date()} 〜 {data4.index.max().date()}")
    logger.info(f"データ5期間: {data5.index.min().date()} 〜 {data5.index.max().date()}")
    
    # キャッシュファイルの確認
    cache_dir = dl.cache_dir
    logger.info(f"\n=== キャッシュファイル確認 ===")
    logger.info(f"キャッシュディレクトリ: {cache_dir}")
    if os.path.exists(cache_dir):
        files = os.listdir(cache_dir)
        for file in files:
            logger.info(f"キャッシュファイル: {file}")

if __name__ == "__main__":
    test_differential_data()
