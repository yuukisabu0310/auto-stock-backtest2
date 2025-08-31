"""
パフォーマンステストスクリプト
並列処理による高速化効果を測定
"""

import time
import logging
from datetime import datetime
from data_loader import DataLoader
from backtest_engine import BacktestEngine
from config import START_DATE, END_DATE

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_data_fetching_performance():
    """データ取得のパフォーマンステスト"""
    print("=" * 60)
    print("📊 データ取得パフォーマンステスト")
    print("=" * 60)
    
    # テスト用銘柄リスト（小規模）
    test_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'TSM', 'AVGO']
    
    # 逐次処理テスト
    print("\n🔄 逐次処理テスト")
    start_time = time.time()
    
    data_loader_sequential = DataLoader(max_workers=1)
    sequential_results = {}
    
    for symbol in test_stocks:
        print(f"  取得中: {symbol}")
        data = data_loader_sequential.get_stock_data(symbol, START_DATE, END_DATE)
        sequential_results[symbol] = data
    
    sequential_time = time.time() - start_time
    print(f"  逐次処理時間: {sequential_time:.2f}秒")
    
    # 並列処理テスト
    print("\n⚡ 並列処理テスト")
    start_time = time.time()
    
    data_loader_parallel = DataLoader(max_workers=5)
    parallel_results = data_loader_parallel.get_stock_data_batch(test_stocks, START_DATE, END_DATE)
    
    parallel_time = time.time() - start_time
    print(f"  並列処理時間: {parallel_time:.2f}秒")
    
    # 結果比較
    speedup = sequential_time / parallel_time if parallel_time > 0 else 0
    print(f"\n📈 高速化効果: {speedup:.2f}倍")
    print(f"   時間短縮: {sequential_time - parallel_time:.2f}秒")

def test_backtest_performance():
    """バックテストのパフォーマンステスト"""
    print("\n" + "=" * 60)
    print("📈 バックテストパフォーマンステスト")
    print("=" * 60)
    
    # テスト用銘柄リスト
    test_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    # データ取得
    data_loader = DataLoader(max_workers=5)
    stocks_data = data_loader.get_stock_data_batch(test_stocks, START_DATE, END_DATE)
    
    # 逐次処理テスト
    print("\n🔄 逐次バックテスト")
    start_time = time.time()
    
    engine_sequential = BacktestEngine("swing_trading")
    sequential_result = engine_sequential.run_backtest(list(stocks_data.keys()), START_DATE, END_DATE)
    
    sequential_time = time.time() - start_time
    print(f"  逐次処理時間: {sequential_time:.2f}秒")
    
    # 並列処理テスト
    print("\n⚡ 並列バックテスト")
    start_time = time.time()
    
    engine_parallel = BacktestEngine("swing_trading")
    parallel_result = engine_parallel.run_backtest_parallel(stocks_data, START_DATE, END_DATE)
    
    parallel_time = time.time() - start_time
    print(f"  並列処理時間: {parallel_time:.2f}秒")
    
    # 結果比較
    speedup = sequential_time / parallel_time if parallel_time > 0 else 0
    print(f"\n📈 高速化効果: {speedup:.2f}倍")
    print(f"   時間短縮: {sequential_time - parallel_time:.2f}秒")

def test_memory_usage():
    """メモリ使用量のテスト"""
    print("\n" + "=" * 60)
    print("💾 メモリ使用量テスト")
    print("=" * 60)
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    # 初期メモリ使用量
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"初期メモリ使用量: {initial_memory:.2f} MB")
    
    # 大量データ取得
    test_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'TSM', 'AVGO']
    data_loader = DataLoader(max_workers=5)
    stocks_data = data_loader.get_stock_data_batch(test_stocks, START_DATE, END_DATE)
    
    # データ取得後のメモリ使用量
    after_data_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"データ取得後メモリ使用量: {after_data_memory:.2f} MB")
    print(f"データ取得による増加: {after_data_memory - initial_memory:.2f} MB")
    
    # バックテスト実行
    engine = BacktestEngine("swing_trading")
    result = engine.run_backtest_parallel(stocks_data, START_DATE, END_DATE)
    
    # バックテスト後のメモリ使用量
    after_backtest_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"バックテスト後メモリ使用量: {after_backtest_memory:.2f} MB")
    print(f"バックテストによる増加: {after_backtest_memory - after_data_memory:.2f} MB")

def main():
    """メイン関数"""
    setup_logging()
    
    print("🚀 パフォーマンステスト開始")
    print(f"テスト期間: {START_DATE} 〜 {END_DATE}")
    
    try:
        # データ取得パフォーマンステスト
        test_data_fetching_performance()
        
        # バックテストパフォーマンステスト
        test_backtest_performance()
        
        # メモリ使用量テスト
        test_memory_usage()
        
        print("\n" + "=" * 60)
        print("✅ パフォーマンステスト完了")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        logging.error(f"パフォーマンステストエラー: {e}")

if __name__ == "__main__":
    main()
