#!/usr/bin/env python3
"""
銘柄一覧レポートのテストスクリプト
"""

from report_generator import ReportGenerator
from data_loader import DataLoader

def test_stocks_list_report():
    """銘柄一覧レポートのテスト"""
    print("銘柄一覧レポート生成テスト開始...")
    
    # データローダーで銘柄リストを取得
    data_loader = DataLoader()
    
    # スイングトレード用の銘柄リストを取得
    stocks = data_loader.get_strategy_stocks("swing_trading", 42)
    print(f"取得銘柄数: {len(stocks)}")
    print(f"銘柄例: {stocks[:10]}...")
    
    # レポート生成器で銘柄一覧レポートを生成
    report_generator = ReportGenerator()
    stocks_report = report_generator.generate_stocks_list_report(stocks, "スイングトレード", 42)
    
    if stocks_report:
        print(f"✅ 銘柄一覧レポート生成完了: {stocks_report}")
        
        # 分類結果の確認
        stocks_by_index = report_generator._categorize_stocks_by_index(stocks)
        print("\n📊 指数別分類結果:")
        for index_name, index_stocks in stocks_by_index.items():
            if index_stocks:
                print(f"  {index_name}: {len(index_stocks)}銘柄")
                print(f"    例: {index_stocks[:5]}...")
    else:
        print("❌ 銘柄一覧レポート生成に失敗しました")

if __name__ == "__main__":
    test_stocks_list_report()
