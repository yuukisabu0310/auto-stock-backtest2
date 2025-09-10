"""
並列化対応自動株式バックテストシステム メインスクリプト
銘柄取得処理と戦略バックテスト処理を分離し、戦略並列実行を実現
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import argparse
import random
import concurrent.futures
import time

from data_fetcher import DataFetcher
from cache_data_loader import CacheOnlyDataLoader
from backtest_engine import BacktestEngine
from report_generator import ReportGenerator
from backtest_aggregator import BacktestAggregator
from config import get_dynamic_backtest_period
from config import TRADING_RULES, START_DATE, END_DATE, get_backtest_period, DATA_START_DATE, DATA_END_DATE, LOCAL_TEST_MODE, LOCAL_TEST_STOCKS, LOCAL_TEST_RUNS

def setup_logging():
    """ログ設定"""
    os.makedirs("logs", exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/backtest_parallel.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def run_single_backtest_from_cache(strategy: str, random_seed: int, 
                                  start_date: str, end_date: str, 
                                  use_parallel: bool = True) -> Dict:
    """
    キャッシュ専用の単一バックテスト実行
    
    Args:
        strategy: 戦略名
        random_seed: 乱数シード
        start_date: 開始日
        end_date: 終了日
        use_parallel: 並列処理を使用するか
    
    Returns:
        Dict: バックテスト結果
    """
    logger = logging.getLogger(f"{__name__}.{strategy}")
    logger.info(f"キャッシュ専用バックテスト開始: {strategy}, シード: {random_seed}")
    
    try:
        # キャッシュ専用データローダー
        cache_loader = CacheOnlyDataLoader()
        
        # 戦略に応じた銘柄リストを取得（ランダム抽出）
        data_fetcher = DataFetcher()
        stocks = data_fetcher.get_strategy_stocks_for_run(strategy, 1, random_seed)
        
        if not stocks:
            logger.error(f"銘柄リストが空: {strategy}")
            return {"error": "銘柄リストが空"}
        
        # 利用可能なキャッシュファイルを確認
        import os
        from config import get_data_period
        
        # 既存のキャッシュファイルを検索（2004-12-31 ～ 2024-12-31）
        cache_files = [f for f in os.listdir("cache") if f.endswith(".pkl")]
        
        # 利用可能な銘柄のみをフィルタリング
        available_stocks = []
        for stock in stocks:
            # 既存のキャッシュファイル（2004-12-31 ～ 2024-12-31）を検索
            cache_file = f"{stock}_1d_2004-12-31_2024-12-31.pkl"
            if cache_file in cache_files:
                available_stocks.append(stock)
        
        if not available_stocks:
            logger.error(f"利用可能な銘柄がありません: {strategy}")
            return {"error": "利用可能な銘柄がありません"}
        
        stocks = available_stocks
        logger.info(f"使用銘柄数: {len(stocks)}")
        logger.info(f"使用銘柄: {stocks[:10]}...")  # 最初の10銘柄のみ表示
        
        # キャッシュ専用バックテストエンジンの初期化
        engine = BacktestEngine(strategy, cache_only=True)
        
        # バックテスト実行
        results = engine.run_backtest(stocks, start_date, end_date)
        
        if "error" in results:
            logger.error(f"バックテストエラー: {results['error']}")
            return results
        
        logger.info(f"キャッシュ専用バックテスト完了: {strategy}")
        logger.info(f"総リターン: {results.get('total_return', 0)*100:.2f}%")
        logger.info(f"取引数: {results.get('total_trades', 0)}")
        
        return results
        
    except Exception as e:
        logger.error(f"キャッシュ専用バックテスト実行エラー: {strategy}, {e}")
        return {"error": str(e)}

def run_strategy_multiple_backtests(strategy: str, num_runs: int, 
                                   start_date: str, end_date: str,
                                   base_seed: int = 42) -> Dict[str, List]:
    """
    単一戦略の複数回バックテスト実行（キャッシュ専用）
    
    Args:
        strategy: 戦略名
        num_runs: 実行回数
        start_date: 開始日
        end_date: 終了日
        base_seed: ベース乱数シード
    
    Returns:
        Dict: 実行結果の辞書
    """
    logger = logging.getLogger(f"{__name__}.{strategy}")
    logger.info(f"戦略複数回バックテスト開始: {strategy}, 実行回数: {num_runs}")
    
    # 結果集計器の初期化
    aggregator = BacktestAggregator()
    
    all_results = []
    successful_runs = 0
    
    for run_id in range(1, num_runs + 1):
        logger.info(f"実行 {run_id}/{num_runs}")
        
        # 各実行で異なるシードを使用
        random_seed = base_seed + run_id
        
        # 単一バックテスト実行（キャッシュ専用）
        result = run_single_backtest_from_cache(strategy, random_seed, start_date, end_date)
        
        # 個別結果を保存
        data_fetcher = DataFetcher()
        stocks = data_fetcher.get_strategy_stocks_for_run(strategy, run_id, base_seed)
        aggregator.save_individual_result(strategy, run_id, random_seed, stocks, result)
        
        if "error" not in result:
            successful_runs += 1
            all_results.append(result)
            
            # 進捗表示
            total_return = result.get('total_return', 0) * 100
            logger.info(f"実行 {run_id} 完了: リターン {total_return:.2f}%")
            
            # 銘柄一覧レポートの生成（最新の実行のみ）
            if run_id == num_runs:
                try:
                    report_generator = ReportGenerator()
                    stocks_report = report_generator.generate_stocks_list_report(stocks, strategy, random_seed)
                    logger.info(f"銘柄一覧レポート生成: {stocks_report}")
                except Exception as e:
                    logger.warning(f"銘柄一覧レポート生成エラー: {e}")
        else:
            logger.warning(f"実行 {run_id} 失敗: {result['error']}")
    
    logger.info(f"戦略複数回バックテスト完了: {strategy}")
    logger.info(f"成功回数: {successful_runs}/{num_runs}")
    
    return {
        "strategy": strategy,
        "total_runs": num_runs,
        "successful_runs": successful_runs,
        "results": all_results
    }

def run_parallel_strategies(num_runs: int = 3, base_seed: int = 42):
    """並列化された全戦略バックテスト実行"""
    logger = logging.getLogger(__name__)
    logger.info("=== 並列化バックテストシステム開始 ===")
    
    # 戦略リスト
    strategies = ["swing_trading", "long_term"]
    
    # フェーズ1: データ取得（逐次実行）
    logger.info("=== フェーズ1: データ取得開始 ===")
    data_fetcher = DataFetcher()
    
    try:
        # 実行日を渡して動的なデータ取得期間を使用
        execution_date = datetime.now()
        fetch_results = data_fetcher.fetch_all_stocks_data(strategies, num_runs, base_seed, execution_date)
        logger.info(f"データ取得結果: {fetch_results}")
        
        if fetch_results["success"] == 0:
            logger.error("データ取得に失敗しました")
            return {}
        
    except Exception as e:
        logger.error(f"データ取得エラー: {e}")
        return {}
    
    # フェーズ2: 並列バックテスト実行
    logger.info("=== フェーズ2: 並列バックテスト開始 ===")
    
    # 結果集計器の初期化
    aggregator = BacktestAggregator()
    all_strategy_results = {}
    
    # 並列実行
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # 各戦略を並列実行
        future_to_strategy = {}
        
        for strategy in strategies:
            # 戦略別の期間を取得
            start_date, end_date = get_backtest_period(strategy)
            logger.info(f"{strategy} バックテスト期間: {start_date} 〜 {end_date}")
            
            # 並列実行の開始
            future = executor.submit(
                run_strategy_multiple_backtests, 
                strategy, num_runs, start_date, end_date, base_seed
            )
            future_to_strategy[future] = strategy
        
        # 結果の収集
        for future in concurrent.futures.as_completed(future_to_strategy):
            strategy = future_to_strategy[future]
            try:
                strategy_results = future.result()
                all_strategy_results[strategy] = strategy_results
                logger.info(f"✅ {strategy} バックテスト完了")
                
                # 集計結果の保存
                if strategy_results["successful_runs"] > 0:
                    aggregated = aggregator.aggregate_results(strategy)
                    if aggregated:
                        aggregator.save_aggregated_result(aggregated)
                
            except Exception as e:
                logger.error(f"❌ {strategy} バックテストエラー: {e}")
                all_strategy_results[strategy] = {"error": str(e)}
    
    logger.info("=== フェーズ2: 並列バックテスト完了 ===")
    
    # 結果サマリー
    logger.info("=== バックテスト結果サマリー ===")
    for strategy_key, strategy_data in all_strategy_results.items():
        if isinstance(strategy_data, dict) and "error" not in strategy_data:
            successful_runs = strategy_data.get("successful_runs", 0)
            total_runs = strategy_data.get("total_runs", 0)
            
            logger.info(f"{strategy_key}:")
            logger.info(f"  実行回数: {successful_runs}/{total_runs}")
            
            # 集計結果の表示
            performance = aggregator.get_performance_summary(strategy_key)
            if performance:
                logger.info(f"  平均総リターン: {performance.get('total_return_mean', 0)*100:.2f}%")
                logger.info(f"  平均シャープレシオ: {performance.get('sharpe_ratio_mean', 0):.2f}")
                logger.info(f"  平均最大ドローダウン: {performance.get('max_drawdown_mean', 0)*100:.2f}%")
                logger.info(f"  平均勝率: {performance.get('win_rate_mean', 0)*100:.1f}%")
        else:
            logger.error(f"{strategy_key}: エラー - {strategy_data.get('error', 'Unknown error')}")
    
    logger.info("=== 並列化バックテストシステム完了 ===")
    return all_strategy_results

def run_strategy_backtests(strategy: str, num_runs: int, base_seed: int) -> Dict:
    """
    単一戦略の複数回バックテスト実行（キャッシュ専用）
    
    Args:
        strategy: 戦略名
        num_runs: 実行回数
        base_seed: ベースシード
    
    Returns:
        Dict: バックテスト結果
    """
    logger = logging.getLogger(f"{__name__}.{strategy}")
    logger.info(f"戦略複数回バックテスト開始: {strategy}, 実行回数: {num_runs}")
    
    results = []
    
    for run in range(1, num_runs + 1):
        logger.info(f"実行 {run}/{num_runs}")
        
        # 動的期間計算
        start_date, end_date = get_dynamic_backtest_period(strategy)
        
        # キャッシュ専用バックテスト実行
        try:
            logger.info(f"キャッシュ専用バックテスト開始: {strategy}, シード: {base_seed + run}")
            
            # バックテストエンジンをキャッシュ専用モードで初期化
            engine = BacktestEngine(strategy, cache_only=True)
            
            # バックテスト実行
            result = engine.run_backtest(start_date, end_date, base_seed + run)
            
            if result:
                results.append(result)
                logger.info(f"実行 {run} 完了: リターン {result.get('total_return', 0):.2f}%")
            else:
                logger.warning(f"実行 {run} 失敗: 結果なし")
                
        except Exception as e:
            logger.error(f"実行 {run} エラー: {e}")
            continue
    
    logger.info(f"戦略複数回バックテスト完了: {strategy}")
    logger.info(f"成功回数: {len(results)}/{num_runs}")
    
    return {
        "strategy": strategy,
        "results": results,
        "success_count": len(results),
        "total_runs": num_runs
    }

def run_cache_only_backtests(num_runs: int, base_seed: int) -> Dict[str, Dict]:
    """
    キャッシュ専用バックテスト実行（動的期間計算）
    
    Args:
        num_runs: 実行回数
        base_seed: ベースシード
    
    Returns:
        Dict: バックテスト結果
    """
    logger = logging.getLogger(__name__)
    logger.info("=== キャッシュ専用バックテスト開始 ===")
    
    strategies = list(TRADING_RULES.keys())
    all_results = {}
    
    for strategy in strategies:
        # 動的期間計算
        start_date, end_date = get_dynamic_backtest_period(strategy)
        logger.info(f"{strategy} バックテスト期間: {start_date} 〜 {end_date}")
        
        # キャッシュ専用バックテスト実行
        strategy_results = run_strategy_backtests(strategy, num_runs, base_seed)
        all_results[strategy] = strategy_results
    
    logger.info("=== キャッシュ専用バックテスト完了 ===")
    return all_results

def generate_individual_reports(all_results: Dict[str, Dict]) -> List[str]:
    """
    個別レポート生成
    
    Args:
        all_results: 全戦略の結果
    
    Returns:
        List[str]: 生成されたレポートファイルパスのリスト
    """
    logger = logging.getLogger(__name__)
    logger.info("個別レポート生成開始")
    
    report_generator = ReportGenerator()
    report_files = []
    
    for strategy_key, strategy_data in all_results.items():
        if isinstance(strategy_data, dict) and "error" not in strategy_data:
            results = strategy_data.get("results", [])
            if results:
                try:
                    # 最新の結果を使用してレポート生成
                    latest_result = results[-1]
                    report_file = report_generator.generate_strategy_report(
                        latest_result, strategy_key
                    )
                    report_files.append(report_file)
                    logger.info(f"個別レポート生成完了: {report_file}")
                except Exception as e:
                    logger.error(f"個別レポート生成エラー: {strategy_key}, {e}")
    
    logger.info(f"個別レポート生成完了: {len(report_files)}ファイル")
    return report_files

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='並列化自動株式バックテストシステム')
    parser.add_argument('--strategy', choices=list(TRADING_RULES.keys()), 
                       help='特定の戦略のみ実行')
    parser.add_argument('--num-runs', type=int, default=LOCAL_TEST_RUNS if LOCAL_TEST_MODE else 3, 
                       help='実行回数（デフォルト: ローカルテスト時2回、通常時3回）')
    parser.add_argument('--base-seed', type=int, default=42, help='ベース乱数シード（デフォルト: 42）')
    parser.add_argument('--parallel', action='store_true', help='並列実行を使用する')
    parser.add_argument('--data-only', action='store_true', help='データ取得のみ実行')
    parser.add_argument('--cache-only', action='store_true', help='キャッシュからのみバックテスト実行')
    
    args = parser.parse_args()
    
    # ログ設定
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("並列化自動株式バックテストシステム開始")
    logger.info(f"データ取得期間: {DATA_START_DATE} 〜 {DATA_END_DATE}")
    logger.info(f"実行回数: {args.num_runs}")
    logger.info(f"ベースシード: {args.base_seed}")
    logger.info(f"並列実行: {args.parallel}")
    logger.info(f"ローカルテストモード: {LOCAL_TEST_MODE}")
    
    try:
        if args.data_only:
            # データ取得のみ実行
            logger.info("データ取得のみ実行")
            data_fetcher = DataFetcher()
            strategies = ["swing_trading", "long_term"]
            # 実行日を渡して動的なデータ取得期間を使用
            execution_date = datetime.now()
            results = data_fetcher.fetch_all_stocks_data(strategies, args.num_runs, args.base_seed, execution_date)
            logger.info(f"データ取得完了: {results}")
            return
        
        if args.cache_only:
            # キャッシュからのみバックテスト実行（動的期間計算）
            logger.info("キャッシュ専用バックテスト実行")
            all_results = run_cache_only_backtests(args.num_runs, args.base_seed)
        elif args.strategy:
            # 特定戦略のみ実行（動的期間計算）
            logger.info(f"戦略実行: {args.strategy}")
            start_date, end_date = get_dynamic_backtest_period(args.strategy)
            logger.info(f"{args.strategy} バックテスト期間: {start_date} 〜 {end_date}")
            
            strategy_results = run_strategy_multiple_backtests(
                args.strategy, args.num_runs, start_date, end_date, args.base_seed
            )
            all_results = {args.strategy: strategy_results}
        else:
            # 全戦略並列実行（動的期間計算）
            if args.parallel:
                all_results = run_parallel_strategies(args.num_runs, args.base_seed)
            else:
                # 従来の逐次実行
                logger.info("従来の逐次実行モード")
                from main import run_all_strategies_multiple_backtests
                all_results = run_all_strategies_multiple_backtests(args.num_runs, args.base_seed)
        
        # 個別レポート生成
        report_files = generate_individual_reports(all_results)
        
        # index.htmlの更新
        try:
            from main import update_index_html
            update_index_html()
            logger.info("index.htmlを更新しました")
        except Exception as e:
            logger.warning(f"index.html更新エラー: {e}")
        
        logger.info("並列化自動株式バックテストシステム完了")
        
    except Exception as e:
        logger.error(f"システム実行エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
