"""
Walk-Forward Optimization (WFO) モジュール
過学習を防止するためのパラメータ最適化
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import logging
from itertools import product
import json

from backtest_engine import BacktestEngine
from data_loader import DataLoader
from config import TRADING_RULES

class WFOptimizer:
    """Walk-Forward Optimizationクラス"""
    
    def __init__(self, strategy: str):
        self.strategy = strategy
        self.rules = TRADING_RULES[strategy]
        self.logger = logging.getLogger(__name__)
        
        # パラメータ探索範囲の定義
        self.param_ranges = self._define_param_ranges()
        
    def _define_param_ranges(self) -> Dict[str, List]:
        """パラメータ探索範囲の定義"""
        if self.strategy == "day_trading":
            return {
                "volume_multiplier": [1.5, 2.0, 2.5, 3.0],
                "profit_target": [0.01, 0.015, 0.02, 0.025],
                "stop_loss": [0.01, 0.015, 0.02, 0.025],
                "rsi_overbought": [65, 70, 75, 80]
            }
        elif self.strategy == "swing_trading":
            return {
                "rsi_range_low": [35, 40, 45],
                "rsi_range_high": [50, 55, 60],
                "volume_multiplier": [1.2, 1.5, 1.8, 2.0],
                "profit_target": [0.05, 0.075, 0.10, 0.125],
                "stop_loss": [0.03, 0.05, 0.07, 0.10],
                "partial_profit_first": [0.03, 0.05, 0.07]
            }
        else:  # long_term
            return {
                "profit_target": [0.20, 0.25, 0.30, 0.35],
                "stop_loss": [0.05, 0.075, 0.10, 0.125],
                "volume_surge_threshold": [1.2, 1.5, 1.8, 2.0]
            }
    
    def run_wfo(self, symbols: List[str], start_date: str, end_date: str,
                train_period: int = 252, test_period: int = 63, 
                step_size: int = 21) -> Dict:
        """
        Walk-Forward Optimization実行
        
        Args:
            symbols: 対象銘柄リスト
            start_date: 開始日
            end_date: 終了日
            train_period: 訓練期間（日数）
            test_period: テスト期間（日数）
            step_size: ステップサイズ（日数）
        
        Returns:
            Dict: WFO結果
        """
        self.logger.info(f"WFO開始: {self.strategy}")
        
        # 日付範囲の設定
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # 期間分割
        periods = self._split_periods(start_dt, end_dt, train_period, test_period, step_size)
        
        # 各期間での最適化と検証
        wfo_results = []
        optimal_params_history = []
        
        for i, (train_start, train_end, test_start, test_end) in enumerate(periods):
            self.logger.info(f"期間 {i+1}/{len(periods)}: 訓練期間 {train_start}〜{train_end}, テスト期間 {test_start}〜{test_end}")
            
            # 訓練期間での最適化
            optimal_params = self._optimize_parameters(
                symbols, train_start, train_end
            )
            
            if optimal_params:
                # テスト期間での検証
                test_results = self._validate_parameters(
                    symbols, test_start, test_end, optimal_params
                )
                
                wfo_results.append({
                    "period": i + 1,
                    "train_start": train_start,
                    "train_end": train_end,
                    "test_start": test_start,
                    "test_end": test_end,
                    "optimal_params": optimal_params,
                    "test_results": test_results
                })
                
                optimal_params_history.append(optimal_params)
        
        # 結果の集計
        summary = self._summarize_wfo_results(wfo_results)
        
        return {
            "strategy": self.strategy,
            "wfo_results": wfo_results,
            "summary": summary,
            "optimal_params_history": optimal_params_history
        }
    
    def _split_periods(self, start_dt: datetime, end_dt: datetime,
                      train_period: int, test_period: int, step_size: int) -> List[Tuple]:
        """期間分割"""
        periods = []
        current_start = start_dt
        
        while current_start + timedelta(days=train_period + test_period) <= end_dt:
            train_start = current_start
            train_end = train_start + timedelta(days=train_period - 1)
            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=test_period - 1)
            
            periods.append((
                train_start.strftime("%Y-%m-%d"),
                train_end.strftime("%Y-%m-%d"),
                test_start.strftime("%Y-%m-%d"),
                test_end.strftime("%Y-%m-%d")
            ))
            
            current_start += timedelta(days=step_size)
        
        return periods
    
    def _optimize_parameters(self, symbols: List[str], start_date: str, end_date: str) -> Dict:
        """パラメータ最適化"""
        self.logger.info(f"パラメータ最適化開始: {start_date}〜{end_date}")
        
        # パラメータの組み合わせを生成
        param_combinations = self._generate_param_combinations()
        
        best_params = None
        best_score = float('-inf')
        
        # 各パラメータ組み合わせでバックテスト実行
        for params in param_combinations:
            try:
                # カスタムルールでバックテスト実行
                results = self._run_backtest_with_params(symbols, start_date, end_date, params)
                
                if results and "error" not in results:
                    # スコア計算（シャープレシオを重視）
                    score = self._calculate_optimization_score(results)
                    
                    if score > best_score:
                        best_score = score
                        best_params = params
                        
            except Exception as e:
                self.logger.warning(f"パラメータ最適化エラー: {params}, {e}")
                continue
        
        self.logger.info(f"最適パラメータ: {best_params}, スコア: {best_score}")
        return best_params
    
    def _generate_param_combinations(self) -> List[Dict]:
        """パラメータ組み合わせの生成"""
        # パラメータ名のリスト
        param_names = list(self.param_ranges.keys())
        
        # 値の組み合わせを生成
        value_combinations = list(product(*self.param_ranges.values()))
        
        # 辞書形式に変換
        combinations = []
        for values in value_combinations:
            param_dict = dict(zip(param_names, values))
            combinations.append(param_dict)
        
        return combinations
    
    def _run_backtest_with_params(self, symbols: List[str], start_date: str, 
                                 end_date: str, params: Dict) -> Dict:
        """カスタムパラメータでバックテスト実行"""
        # カスタムルールの作成
        custom_rules = self._create_custom_rules(params)
        
        # バックテストエンジンの初期化（カスタムルール使用）
        engine = BacktestEngine(self.strategy)
        engine.rules = custom_rules
        
        # バックテスト実行
        return engine.run_backtest(symbols, start_date, end_date)
    
    def _create_custom_rules(self, params: Dict) -> Dict:
        """カスタムルールの作成"""
        # 基本ルールをコピー
        custom_rules = self.rules.copy()
        
        # パラメータの適用
        if self.strategy == "day_trading":
            custom_rules["entry_conditions"]["volume_multiplier"] = params.get("volume_multiplier", 2.0)
            custom_rules["exit_conditions"]["profit_target"] = params.get("profit_target", 0.015)
            custom_rules["exit_conditions"]["stop_loss"] = params.get("stop_loss", 0.015)
            custom_rules["exit_conditions"]["rsi_overbought"] = params.get("rsi_overbought", 70)
            
        elif self.strategy == "swing_trading":
            rsi_low = params.get("rsi_range_low", 40)
            rsi_high = params.get("rsi_range_high", 50)
            custom_rules["entry_conditions"]["rsi_range"] = (rsi_low, rsi_high)
            custom_rules["entry_conditions"]["volume_multiplier"] = params.get("volume_multiplier", 1.5)
            custom_rules["exit_conditions"]["profit_target"] = params.get("profit_target", 0.075)
            custom_rules["exit_conditions"]["stop_loss"] = params.get("stop_loss", 0.05)
            custom_rules["exit_conditions"]["partial_profit"]["first_target"] = params.get("partial_profit_first", 0.05)
            
        else:  # long_term
            custom_rules["exit_conditions"]["profit_target"] = params.get("profit_target", 0.30)
            custom_rules["exit_conditions"]["stop_loss"] = params.get("stop_loss", 0.085)
            custom_rules["entry_conditions"]["volume_surge_threshold"] = params.get("volume_surge_threshold", 1.5)
        
        return custom_rules
    
    def _calculate_optimization_score(self, results: Dict) -> float:
        """最適化スコアの計算"""
        # シャープレシオを重視したスコア計算
        sharpe_ratio = results.get('sharpe_ratio', 0)
        total_return = results.get('total_return', 0)
        max_drawdown = abs(results.get('max_drawdown', 0))
        win_rate = results.get('win_rate', 0)
        total_trades = results.get('total_trades', 0)
        
        # 取引数が少ない場合はペナルティ
        if total_trades < 10:
            return float('-inf')
        
        # スコア計算（シャープレシオを重視）
        score = (
            sharpe_ratio * 0.4 +  # シャープレシオ（40%）
            total_return * 0.3 +  # 総リターン（30%）
            (1 - max_drawdown) * 0.2 +  # ドローダウン（20%）
            win_rate * 0.1  # 勝率（10%）
        )
        
        return score
    
    def _validate_parameters(self, symbols: List[str], start_date: str, 
                           end_date: str, params: Dict) -> Dict:
        """パラメータ検証"""
        return self._run_backtest_with_params(symbols, start_date, end_date, params)
    
    def _summarize_wfo_results(self, wfo_results: List[Dict]) -> Dict:
        """WFO結果の集計"""
        if not wfo_results:
            return {"error": "WFO結果がありません"}
        
        # テスト期間の結果を集計
        test_returns = []
        test_sharpe_ratios = []
        test_max_drawdowns = []
        test_win_rates = []
        test_trade_counts = []
        
        for result in wfo_results:
            test_result = result["test_results"]
            if "error" not in test_result:
                test_returns.append(test_result.get('total_return', 0))
                test_sharpe_ratios.append(test_result.get('sharpe_ratio', 0))
                test_max_drawdowns.append(abs(test_result.get('max_drawdown', 0)))
                test_win_rates.append(test_result.get('win_rate', 0))
                test_trade_counts.append(test_result.get('total_trades', 0))
        
        if not test_returns:
            return {"error": "有効なテスト結果がありません"}
        
        # 統計計算
        summary = {
            "total_periods": len(wfo_results),
            "valid_periods": len(test_returns),
            "avg_return": np.mean(test_returns),
            "std_return": np.std(test_returns),
            "avg_sharpe_ratio": np.mean(test_sharpe_ratios),
            "avg_max_drawdown": np.mean(test_max_drawdowns),
            "avg_win_rate": np.mean(test_win_rates),
            "avg_trade_count": np.mean(test_trade_counts),
            "best_period": np.argmax(test_returns) + 1,
            "worst_period": np.argmin(test_returns) + 1,
            "positive_periods": sum(1 for r in test_returns if r > 0),
            "negative_periods": sum(1 for r in test_returns if r < 0)
        }
        
        # パラメータ安定性の分析
        param_stability = self._analyze_parameter_stability(wfo_results)
        summary["parameter_stability"] = param_stability
        
        return summary
    
    def _analyze_parameter_stability(self, wfo_results: List[Dict]) -> Dict:
        """パラメータ安定性の分析"""
        if not wfo_results:
            return {}
        
        # 各パラメータの値の分布を分析
        param_values = {}
        
        for result in wfo_results:
            params = result["optimal_params"]
            if params:
                for param_name, param_value in params.items():
                    if param_name not in param_values:
                        param_values[param_name] = []
                    param_values[param_name].append(param_value)
        
        stability_analysis = {}
        for param_name, values in param_values.items():
            if len(values) > 1:
                stability_analysis[param_name] = {
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "cv": np.std(values) / np.mean(values) if np.mean(values) != 0 else 0,
                    "min": min(values),
                    "max": max(values),
                    "unique_values": len(set(values))
                }
        
        return stability_analysis
    
    def get_recommended_params(self, wfo_results: List[Dict]) -> Dict:
        """推奨パラメータの取得"""
        if not wfo_results:
            return {}
        
        # 最も良い結果を出した期間のパラメータを推奨
        best_period = None
        best_score = float('-inf')
        
        for result in wfo_results:
            test_result = result["test_results"]
            if "error" not in test_result:
                score = self._calculate_optimization_score(test_result)
                if score > best_score:
                    best_score = score
                    best_period = result
        
        if best_period:
            return best_period["optimal_params"]
        
        return {}
    
    def save_wfo_results(self, wfo_results: Dict, filename: str = None):
        """WFO結果の保存"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wfo_results_{self.strategy}_{timestamp}.json"
        
        # JSON形式で保存
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(wfo_results, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"WFO結果保存: {filename}")
