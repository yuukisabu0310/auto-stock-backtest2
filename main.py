"""
自動株式バックテストシステム メインスクリプト
指数別ランダム抽出・複数回実行・結果集計対応版
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import argparse
import random

from data_loader import DataLoader
from backtest_engine import BacktestEngine
from report_generator import ReportGenerator
from backtest_aggregator import BacktestAggregator
from config import TRADING_RULES, START_DATE, END_DATE

def setup_logging():
    """ログ設定"""
    os.makedirs("logs", exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/backtest.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_index_summary() -> Dict[str, int]:
    """指数別銘柄数の取得"""
    data_loader = DataLoader()
    return data_loader.get_index_summary()

def run_single_backtest(strategy: str, random_seed: int, 
                       start_date: str, end_date: str) -> Dict:
    """
    単一バックテスト実行
    
    Args:
        strategy: 戦略名
        random_seed: 乱数シード
        start_date: 開始日
        end_date: 終了日
    
    Returns:
        Dict: バックテスト結果
    """
    logger = logging.getLogger(__name__)
    logger.info(f"単一バックテスト開始: {strategy}, シード: {random_seed}")
    
    try:
        # データローダーの初期化
        data_loader = DataLoader()
        
        # 戦略に応じた銘柄リストを取得（ランダム抽出）
        stocks = data_loader.get_strategy_stocks(strategy, random_seed)
        
        if not stocks:
            logger.error(f"銘柄リストが空: {strategy}")
            return {"error": "銘柄リストが空"}
        
        logger.info(f"使用銘柄数: {len(stocks)}")
        logger.info(f"使用銘柄: {stocks[:10]}...")  # 最初の10銘柄のみ表示
        
        # バックテストエンジンの初期化
        engine = BacktestEngine(strategy)
        
        # バックテスト実行
        results = engine.run_backtest(stocks, start_date, end_date)
        
        if "error" in results:
            logger.error(f"バックテストエラー: {results['error']}")
            return results
        
        logger.info(f"単一バックテスト完了: {strategy}")
        logger.info(f"総リターン: {results.get('total_return', 0)*100:.2f}%")
        logger.info(f"取引数: {results.get('total_trades', 0)}")
        
        return results
        
    except Exception as e:
        logger.error(f"単一バックテスト実行エラー: {strategy}, {e}")
        return {"error": str(e)}

def run_multiple_backtests(strategy: str, num_runs: int, 
                          start_date: str, end_date: str,
                          base_seed: int = 42) -> Dict[str, List]:
    """
    複数回バックテスト実行
    
    Args:
        strategy: 戦略名
        num_runs: 実行回数
        start_date: 開始日
        end_date: 終了日
        base_seed: ベース乱数シード
    
    Returns:
        Dict: 実行結果の辞書
    """
    logger = logging.getLogger(__name__)
    logger.info(f"複数回バックテスト開始: {strategy}, 実行回数: {num_runs}")
    
    # 結果集計器の初期化
    aggregator = BacktestAggregator()
    
    all_results = []
    successful_runs = 0
    
    for run_id in range(1, num_runs + 1):
        logger.info(f"実行 {run_id}/{num_runs}")
        
        # 各実行で異なるシードを使用
        random_seed = base_seed + run_id
        
        # 単一バックテスト実行
        result = run_single_backtest(strategy, random_seed, start_date, end_date)
        
        # 個別結果を保存
        stocks = DataLoader().get_strategy_stocks(strategy, random_seed)
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
    
    logger.info(f"複数回バックテスト完了: {strategy}")
    logger.info(f"成功回数: {successful_runs}/{num_runs}")
    
    return {
        "strategy": strategy,
        "total_runs": num_runs,
        "successful_runs": successful_runs,
        "results": all_results
    }

def run_all_strategies_multiple_backtests(num_runs: int = 5, 
                                         start_date: str = START_DATE,
                                         end_date: str = END_DATE,
                                         base_seed: int = 42):
    """全戦略の複数回バックテスト実行"""
    logger = logging.getLogger(__name__)
    logger.info("全戦略複数回バックテスト開始")
    
    # 戦略リスト
    strategies = ["swing_trading", "long_term"]
    
    # 結果集計器の初期化
    aggregator = BacktestAggregator()
    
    all_strategy_results = {}
    
    for strategy in strategies:
        logger.info(f"戦略実行中: {strategy}")
        
        # 複数回バックテスト実行
        strategy_results = run_multiple_backtests(
            strategy, num_runs, start_date, end_date, base_seed
        )
        
        all_strategy_results[strategy] = strategy_results
        
        # 集計結果の保存
        if strategy_results["successful_runs"] > 0:
            aggregated = aggregator.aggregate_results(strategy)
            if aggregated:
                aggregator.save_aggregated_result(aggregated)
    
    # サマリーレポート生成（無効化）
    # summary_report = aggregator.generate_summary_report(strategies)
    # if summary_report:
    #     logger.info(f"サマリーレポート生成: {summary_report}")
    logger.info("サマリーレポート生成をスキップしました")
    
    logger.info("全戦略複数回バックテスト完了")
    return all_strategy_results

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
    
    # 各戦略のレポート生成
    for strategy_key, strategy_data in all_results.items():
        if "error" in strategy_data:
            logger.warning(f"レポート生成スキップ: {strategy_key} - {strategy_data['error']}")
            continue
        
        # 最新の結果を使用してレポート生成
        results = strategy_data.get("results", [])
        if results:
            latest_result = results[-1]  # 最新の結果
            strategy_name = TRADING_RULES[strategy_key]["name"]
            
            # 最新の実行で使用された銘柄リストを取得
            latest_stocks = None
            latest_seed = None
            try:
                # 最新の実行の乱数シードを計算
                total_runs = strategy_data.get("total_runs", 0)
                base_seed = 42  # デフォルト値
                latest_seed = base_seed + total_runs
                
                # 最新の銘柄リストを取得
                data_loader = DataLoader()
                latest_stocks = data_loader.get_strategy_stocks(strategy_key, latest_seed)
            except Exception as e:
                logger.warning(f"銘柄リスト取得エラー: {e}")
            
            report_file = report_generator.generate_strategy_report(
                latest_result, strategy_name, latest_stocks, latest_seed
            )
            
            if report_file:
                report_files.append(report_file)
                logger.info(f"個別レポート生成完了: {report_file}")
    
    logger.info(f"個別レポート生成完了: {len(report_files)}ファイル")
    return report_files

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='自動株式バックテストシステム（指数別ランダム抽出版）')
    parser.add_argument('--start-date', default=START_DATE, help='開始日 (YYYY-MM-DD)')
    parser.add_argument('--end-date', default=END_DATE, help='終了日 (YYYY-MM-DD)')
    parser.add_argument('--strategy', choices=list(TRADING_RULES.keys()), 
                       help='特定の戦略のみ実行')
    parser.add_argument('--num-runs', type=int, default=5, help='実行回数（デフォルト: 5）')
    parser.add_argument('--base-seed', type=int, default=42, help='ベース乱数シード（デフォルト: 42）')
    parser.add_argument('--show-indices', action='store_true', help='指数別銘柄数を表示')
    
    args = parser.parse_args()
    
    # ログ設定
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("自動株式バックテストシステム開始（指数別ランダム抽出版）")
    logger.info(f"期間: {args.start_date} 〜 {args.end_date}")
    logger.info(f"実行回数: {args.num_runs}")
    logger.info(f"ベースシード: {args.base_seed}")
    
    try:
        # 指数別銘柄数の表示
        if args.show_indices:
            index_summary = get_index_summary()
            logger.info("=== 指数別銘柄数 ===")
            for index_name, count in index_summary.items():
                logger.info(f"{index_name}: {count}銘柄")
            return
        
        if args.strategy:
            # 特定戦略のみ実行
            logger.info(f"戦略実行: {args.strategy}")
            
            strategy_results = run_multiple_backtests(
                args.strategy, args.num_runs, args.start_date, args.end_date, args.base_seed
            )
            all_results = {args.strategy: strategy_results}
            
        else:
            # 全戦略実行
            all_results = run_all_strategies_multiple_backtests(
                args.num_runs, args.start_date, args.end_date, args.base_seed
            )
        
        # 個別レポート生成
        report_files = generate_individual_reports(all_results)
        
        # 結果サマリー
        logger.info("=== バックテスト結果サマリー ===")
        aggregator = BacktestAggregator()
        
        for strategy_key, strategy_data in all_results.items():
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
        
        logger.info(f"レポートファイル: {report_files}")
        
        # index.htmlの更新
        try:
            from generate_index import main as generate_index_main
            generate_index_main()
            logger.info("index.htmlを更新しました")
        except Exception as e:
            logger.warning(f"index.html更新エラー: {e}")
        
        logger.info("自動株式バックテストシステム完了")
        
    except Exception as e:
        logger.error(f"システム実行エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
