"""
データ取得専用モジュール
全戦略の銘柄データを事前に一括取得する
"""

import logging
from typing import List, Set, Dict
from datetime import datetime
from data_loader import DataLoader
from config import get_data_period, LOCAL_TEST_MODE

class DataFetcher:
    """データ取得専用クラス"""
    
    def __init__(self, local_test_mode: bool = LOCAL_TEST_MODE):
        """
        初期化
        
        Args:
            local_test_mode: ローカルテストモード
        """
        self.data_loader = DataLoader(local_test_mode=local_test_mode)
        self.logger = logging.getLogger(__name__)
        self.local_test_mode = local_test_mode
    
    def collect_all_strategy_stocks(self, strategies: List[str], 
                                   num_runs: int = 3, base_seed: int = 42) -> Set[str]:
        """
        全戦略の銘柄を収集
        
        Args:
            strategies: 戦略リスト
            num_runs: 実行回数
            base_seed: ベース乱数シード
        
        Returns:
            Set[str]: 全銘柄のセット
        """
        all_stocks = set()
        
        self.logger.info("全戦略の銘柄を収集中...")
        
        for strategy in strategies:
            self.logger.info(f"戦略 {strategy} の銘柄を収集中...")
            
            for run_id in range(1, num_runs + 1):
                random_seed = base_seed + run_id
                stocks = self.data_loader.get_strategy_stocks(strategy, random_seed)
                all_stocks.update(stocks)
                
                self.logger.info(f"  {strategy} 実行{run_id}: {len(stocks)}銘柄")
        
        self.logger.info(f"全戦略の銘柄収集完了: {len(all_stocks)}銘柄")
        return all_stocks
    
    def fetch_all_stocks_data(self, strategies: List[str], 
                             num_runs: int = 3, base_seed: int = 42,
                             execution_date: datetime = None) -> Dict[str, int]:
        """
        全戦略の銘柄データを一括取得
        
        Args:
            strategies: 戦略リスト
            num_runs: 実行回数
            base_seed: ベース乱数シード
            execution_date: 実行日（Noneの場合は現在日時）
        
        Returns:
            Dict[str, int]: 取得結果の統計
        """
        self.logger.info("=== フェーズ1: データ取得開始 ===")
        
        # 動的なデータ取得期間を計算
        start_date, end_date = get_data_period(execution_date)
        
        # 全銘柄を収集
        all_stocks = self.collect_all_strategy_stocks(strategies, num_runs, base_seed)
        
        if not all_stocks:
            self.logger.error("取得対象の銘柄がありません")
            return {"total": 0, "success": 0, "failed": 0}
        
        # 一括データ取得
        self.logger.info(f"一括データ取得開始: {len(all_stocks)}銘柄")
        self.logger.info(f"取得期間: {start_date} ～ {end_date}")
        
        try:
            # 並列でデータ取得
            stocks_data = self.data_loader.get_stock_data_batch(
                list(all_stocks), start_date, end_date
            )
            
            success_count = len(stocks_data)
            failed_count = len(all_stocks) - success_count
            
            self.logger.info(f"データ取得完了: 成功 {success_count}銘柄, 失敗 {failed_count}銘柄")
            
            # VIXデータも取得
            self.logger.info("VIXデータを取得中...")
            vix_data = self.data_loader.get_vix_data(start_date, end_date)
            if not vix_data.empty:
                self.logger.info(f"VIXデータ取得成功: {len(vix_data)}行")
            else:
                self.logger.warning("VIXデータの取得に失敗しました")
            
            self.logger.info("=== フェーズ1: データ取得完了 ===")
            
            return {
                "total": len(all_stocks),
                "success": success_count,
                "failed": failed_count
            }
            
        except Exception as e:
            self.logger.error(f"データ取得エラー: {e}")
            return {"total": len(all_stocks), "success": 0, "failed": len(all_stocks)}
    
    def validate_data_completeness(self, strategies: List[str], 
                                  num_runs: int = 3, base_seed: int = 42) -> Dict[str, Dict]:
        """
        データの完全性を検証
        
        Args:
            strategies: 戦略リスト
            num_runs: 実行回数
            base_seed: ベース乱数シード
        
        Returns:
            Dict[str, Dict]: 戦略別の完全性情報
        """
        self.logger.info("データ完全性を検証中...")
        
        completeness_info = {}
        
        for strategy in strategies:
            self.logger.info(f"戦略 {strategy} の完全性を検証中...")
            
            strategy_completeness = {
                "total_runs": num_runs,
                "complete_runs": 0,
                "missing_stocks": []
            }
            
            for run_id in range(1, num_runs + 1):
                random_seed = base_seed + run_id
                stocks = self.data_loader.get_strategy_stocks(strategy, random_seed)
                
                # 各銘柄のキャッシュ存在確認
                missing_stocks = []
                for stock in stocks:
                    cache_file = f"{stock}_1d_{DATA_START_DATE}_{DATA_END_DATE}.pkl"
                    if not self.data_loader._file_exists(cache_file):
                        missing_stocks.append(stock)
                
                if not missing_stocks:
                    strategy_completeness["complete_runs"] += 1
                else:
                    strategy_completeness["missing_stocks"].extend(missing_stocks)
            
            completeness_info[strategy] = strategy_completeness
            
            self.logger.info(f"  {strategy}: {strategy_completeness['complete_runs']}/{num_runs}回完全")
        
        return completeness_info
    
    def get_strategy_stocks_for_run(self, strategy: str, run_id: int, 
                                   base_seed: int = 42) -> List[str]:
        """
        特定の戦略・実行の銘柄リストを取得
        
        Args:
            strategy: 戦略名
            run_id: 実行ID
            base_seed: ベース乱数シード
        
        Returns:
            List[str]: 銘柄リスト
        """
        random_seed = base_seed + run_id
        return self.data_loader.get_strategy_stocks(strategy, random_seed)
