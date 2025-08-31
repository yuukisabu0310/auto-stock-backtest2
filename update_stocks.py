"""
銘柄リスト自動更新スクリプト
"""

import os
import sys
import logging
from datetime import datetime
import argparse

from stock_fetcher import StockFetcher

def setup_logging():
    """ログ設定"""
    os.makedirs("logs", exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/stock_update.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='銘柄リスト自動更新')
    parser.add_argument('--fetch-only', action='store_true', help='取得のみ実行（保存しない）')
    parser.add_argument('--merge', action='store_true', help='既存ファイルとマージ')
    parser.add_argument('--validate', action='store_true', help='銘柄シンボルの妥当性チェック')
    parser.add_argument('--output', default='index_stocks_updated.csv', help='出力ファイル名')
    
    args = parser.parse_args()
    
    # ログ設定
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("銘柄リスト自動更新開始")
    
    try:
        # 自動銘柄取得クラスの初期化
        fetcher = StockFetcher()
        
        # 全指数の銘柄を取得
        stocks_dict = fetcher.fetch_all_stocks()
        
        if not stocks_dict:
            logger.error("銘柄の取得に失敗しました")
            return
        
        # 統計情報の表示
        total_stocks = sum(len(stocks) for stocks in stocks_dict.values())
        logger.info(f"取得完了: 合計{total_stocks}銘柄")
        
        for index_name, stocks in stocks_dict.items():
            logger.info(f"{index_name}: {len(stocks)}銘柄")
        
        # 取得のみの場合はここで終了
        if args.fetch_only:
            logger.info("取得のみ実行のため終了")
            return
        
        # 妥当性チェック
        if args.validate:
            logger.info("銘柄シンボルの妥当性チェックを実行")
            stocks_dict = fetcher.validate_stock_symbols(stocks_dict)
        
        # 既存ファイルとマージ
        if args.merge:
            logger.info("既存ファイルとマージを実行")
            output_file = fetcher.merge_with_existing_stocks(stocks_dict)
        else:
            # 新しいファイルとして保存
            output_file = fetcher.save_stocks_to_csv(stocks_dict, args.output)
        
        if output_file:
            logger.info(f"銘柄リスト更新完了: {output_file}")
            
            # 最終統計
            import pandas as pd
            df = pd.read_csv(output_file, encoding='utf-8')
            index_counts = df['index'].value_counts()
            
            logger.info("=== 最終統計 ===")
            for index_name, count in index_counts.items():
                logger.info(f"{index_name}: {count}銘柄")
            logger.info(f"合計: {len(df)}銘柄")
        else:
            logger.error("ファイル保存に失敗しました")
        
    except Exception as e:
        logger.error(f"銘柄リスト更新エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
