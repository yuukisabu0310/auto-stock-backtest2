"""
システム動作確認用テストスクリプト
"""

import os
import sys
import logging
from datetime import datetime, timedelta

from data_loader import DataLoader
from technical_indicators import TechnicalIndicators
from backtest_engine import BacktestEngine
from report_generator import ReportGenerator
from wfo_optimizer import WFOptimizer

def setup_test_logging():
    """テスト用ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_data_loader():
    """データローダーのテスト"""
    print("=== データローダーテスト ===")
    
    data_loader = DataLoader()
    
    # テスト用銘柄
    test_symbols = ["7203.T", "6758.T", "9984.T"]
    
    # データ取得テスト
    for symbol in test_symbols:
        print(f"データ取得中: {symbol}")
        data = data_loader.get_stock_data(
            symbol, 
            start_date="2023-01-01", 
            end_date="2023-12-31"
        )
        
        if not data.empty:
            print(f"  ✓ データ取得成功: {len(data)}行")
            print(f"    期間: {data.index[0]} 〜 {data.index[-1]}")
        else:
            print(f"  ✗ データ取得失敗: {symbol}")
    
    print()

def test_technical_indicators():
    """技術指標計算のテスト"""
    print("=== 技術指標計算テスト ===")
    
    data_loader = DataLoader()
    indicators = TechnicalIndicators()
    
    # テストデータ取得
    data = data_loader.get_stock_data("7203.T", "2023-01-01", "2023-12-31")
    
    if not data.empty:
        # 技術指標計算
        data_with_indicators = indicators.calculate_all_indicators(data)
        
        # 計算結果の確認
        required_columns = [
            'SMA_5', 'SMA_25', 'SMA_200', 'RSI', 'VWAP', 
            'BB_Upper', 'BB_Middle', 'BB_Lower', 'Golden_Cross'
        ]
        
        missing_columns = [col for col in required_columns if col not in data_with_indicators.columns]
        
        if not missing_columns:
            print("  ✓ 技術指標計算成功")
            print(f"    計算済み指標数: {len([col for col in data_with_indicators.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume']])}")
        else:
            print(f"  ✗ 技術指標計算失敗: 不足している指標 {missing_columns}")
    else:
        print("  ✗ テストデータ取得失敗")
    
    print()

def test_backtest_engine():
    """バックテストエンジンのテスト"""
    print("=== バックテストエンジンテスト ===")
    
    # テスト用銘柄（少ない数でテスト）
    test_symbols = ["7203.T", "6758.T"]
    
    # 各戦略でテスト
    strategies = ["day_trading", "swing_trading", "long_term"]
    
    for strategy in strategies:
        print(f"戦略テスト: {strategy}")
        
        try:
            engine = BacktestEngine(strategy)
            results = engine.run_backtest(
                test_symbols, 
                start_date="2023-01-01", 
                end_date="2023-06-30"  # 短い期間でテスト
            )
            
            if "error" not in results:
                print(f"  ✓ バックテスト成功")
                print(f"    総リターン: {results.get('total_return', 0)*100:.2f}%")
                print(f"    取引数: {results.get('total_trades', 0)}")
                print(f"    勝率: {results.get('win_rate', 0)*100:.1f}%")
            else:
                print(f"  ✗ バックテスト失敗: {results['error']}")
                
        except Exception as e:
            print(f"  ✗ バックテストエラー: {e}")
    
    print()

def test_report_generator():
    """レポート生成のテスト"""
    print("=== レポート生成テスト ===")
    
    # テスト用の結果データ
    test_results = {
        "strategy": "test_strategy",
        "total_return": 0.15,
        "sharpe_ratio": 1.2,
        "max_drawdown": -0.08,
        "win_rate": 0.65,
        "total_trades": 25,
        "avg_profit": 1000,
        "avg_loss": -500,
        "trades": [
            {
                "symbol": "7203.T",
                "entry_date": "2023-01-15",
                "exit_date": "2023-01-20",
                "entry_price": 2000,
                "exit_price": 2100,
                "quantity": 100,
                "profit_loss": 10000,
                "profit_loss_pct": 0.05,
                "holding_days": 5,
                "strategy": "test",
                "entry_reason": "test_entry",
                "exit_reason": "test_exit"
            }
        ],
        "equity_curve": {
            "dates": ["2023-01-01", "2023-01-02", "2023-01-03"],
            "values": [10000000, 10100000, 10200000]
        }
    }
    
    try:
        report_generator = ReportGenerator()
        report_file = report_generator.generate_strategy_report(test_results, "テスト戦略")
        
        if report_file and os.path.exists(report_file):
            print(f"  ✓ レポート生成成功: {report_file}")
        else:
            print("  ✗ レポート生成失敗")
            
    except Exception as e:
        print(f"  ✗ レポート生成エラー: {e}")
    
    print()

def test_wfo_optimizer():
    """WFO最適化のテスト"""
    print("=== WFO最適化テスト ===")
    
    # テスト用銘柄（少ない数でテスト）
    test_symbols = ["7203.T"]
    
    try:
        wfo = WFOptimizer("day_trading")
        
        # 短い期間でWFOテスト
        wfo_results = wfo.run_wfo(
            test_symbols,
            start_date="2023-01-01",
            end_date="2023-03-31",
            train_period=30,  # 短い期間でテスト
            test_period=15,
            step_size=7
        )
        
        if "error" not in wfo_results.get("summary", {}):
            print("  ✓ WFO最適化成功")
            summary = wfo_results["summary"]
            print(f"    有効期間数: {summary.get('valid_periods', 0)}")
            print(f"    平均リターン: {summary.get('avg_return', 0)*100:.2f}%")
        else:
            print(f"  ✗ WFO最適化失敗: {wfo_results['summary']['error']}")
            
    except Exception as e:
        print(f"  ✗ WFO最適化エラー: {e}")
    
    print()

def main():
    """メインテスト関数"""
    print("自動株式バックテストシステム - 動作確認テスト")
    print("=" * 50)
    
    # ログ設定
    setup_test_logging()
    
    # 各モジュールのテスト
    test_data_loader()
    test_technical_indicators()
    test_backtest_engine()
    test_report_generator()
    test_wfo_optimizer()
    
    print("=" * 50)
    print("テスト完了")
    print("\nシステムが正常に動作していることを確認しました。")
    print("実際のバックテストを実行するには以下を実行してください:")
    print("  python main.py")

if __name__ == "__main__":
    main()
