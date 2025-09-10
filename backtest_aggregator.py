"""
バックテスト結果集計モジュール
複数回のランダム抽出バックテスト結果を蓄積・集計
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any
import logging

class BacktestAggregator:
    """バックテスト結果集計クラス"""
    
    def __init__(self, results_dir: str = "results"):
        """
        初期化
        
        Args:
            results_dir: 結果保存ディレクトリ
        """
        self.results_dir = results_dir
        self.logger = logging.getLogger(__name__)
        
        # 結果ディレクトリの作成
        os.makedirs(results_dir, exist_ok=True)
        os.makedirs(os.path.join(results_dir, "individual"), exist_ok=True)
        os.makedirs(os.path.join(results_dir, "aggregated"), exist_ok=True)
    
    def _convert_timestamps(self, obj):
        """
        Timestampオブジェクトを文字列に変換
        
        Args:
            obj: 変換対象オブジェクト
        
        Returns:
            変換されたオブジェクト
        """
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._convert_timestamps(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_timestamps(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.int32):
            return int(obj)
        elif isinstance(obj, np.int64):
            return int(obj)
        elif isinstance(obj, np.float32):
            return float(obj)
        elif isinstance(obj, np.float64):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    def save_individual_result(self, strategy: str, run_id: int, 
                             random_seed: int, stocks: List[str], 
                             results: Dict[str, Any]) -> str:
        """
        個別バックテスト結果を保存
        
        Args:
            strategy: 戦略名
            run_id: 実行ID
            random_seed: 乱数シード
            stocks: 使用銘柄リスト
            results: バックテスト結果
        
        Returns:
            str: 保存されたファイルパス
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{strategy}_run_{run_id:03d}_seed_{random_seed}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, "individual", filename)
        
        # 保存データの作成
        save_data = {
            "strategy": strategy,
            "run_id": run_id,
            "random_seed": random_seed,
            "timestamp": timestamp,
            "stocks": stocks,
            "results": self._convert_timestamps(results)
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"個別結果保存: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"個別結果保存エラー: {e}")
            return ""
    
    def load_individual_results(self, strategy: str = None) -> List[Dict[str, Any]]:
        """
        個別バックテスト結果を読み込み
        
        Args:
            strategy: 戦略名（Noneの場合は全戦略）
        
        Returns:
            List[Dict]: 個別結果リスト
        """
        individual_dir = os.path.join(self.results_dir, "individual")
        results = []
        
        try:
            for filename in os.listdir(individual_dir):
                if not filename.endswith('.json'):
                    continue
                
                if strategy and not filename.startswith(strategy):
                    continue
                
                filepath = os.path.join(individual_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results.append(data)
            
            # 実行IDでソート
            results.sort(key=lambda x: x['run_id'])
            self.logger.info(f"個別結果読み込み: {len(results)}件")
            
        except Exception as e:
            self.logger.error(f"個別結果読み込みエラー: {e}")
        
        return results
    
    def aggregate_results(self, strategy: str, min_runs: int = 1) -> Dict[str, Any]:
        """
        バックテスト結果を集計
        
        Args:
            strategy: 戦略名
            min_runs: 最小実行回数
        
        Returns:
            Dict: 集計結果
        """
        individual_results = self.load_individual_results(strategy)
        
        if len(individual_results) < min_runs:
            self.logger.warning(f"戦略 {strategy} の実行回数({len(individual_results)})が最小回数({min_runs})未満")
            return {}
        
        # 集計対象の指標
        metrics = [
            'total_return', 'annual_return', 'volatility', 'sharpe_ratio',
            'max_drawdown', 'win_rate', 'profit_factor', 'total_trades',
            'avg_trade_return', 'avg_win', 'avg_loss'
        ]
        
        aggregated = {
            "strategy": strategy,
            "total_runs": len(individual_results),
            "first_run": individual_results[0]['run_id'],
            "last_run": individual_results[-1]['run_id'],
            "aggregation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 各指標の統計計算
        for metric in metrics:
            values = []
            for result in individual_results:
                if 'results' in result and metric in result['results']:
                    values.append(result['results'][metric])
            
            if values:
                aggregated[f"{metric}_mean"] = np.mean(values)
                aggregated[f"{metric}_std"] = np.std(values)
                aggregated[f"{metric}_min"] = np.min(values)
                aggregated[f"{metric}_max"] = np.max(values)
                aggregated[f"{metric}_median"] = np.median(values)
                aggregated[f"{metric}_q25"] = np.percentile(values, 25)
                aggregated[f"{metric}_q75"] = np.percentile(values, 75)
        
        # 銘柄使用頻度の集計
        stock_usage = {}
        for result in individual_results:
            for stock in result.get('stocks', []):
                stock_usage[stock] = stock_usage.get(stock, 0) + 1
        
        aggregated['stock_usage'] = stock_usage
        aggregated['unique_stocks'] = len(stock_usage)
        
        self.logger.info(f"結果集計完了: {strategy}, {len(individual_results)}回実行")
        return aggregated
    
    def save_aggregated_result(self, aggregated_result: Dict[str, Any]) -> str:
        """
        集計結果を保存
        
        Args:
            aggregated_result: 集計結果
        
        Returns:
            str: 保存されたファイルパス
        """
        strategy = aggregated_result['strategy']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{strategy}_aggregated_{timestamp}.json"
        filepath = os.path.join(self.results_dir, "aggregated", filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(aggregated_result, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"集計結果保存: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"集計結果保存エラー: {e}")
            return ""
    
    def generate_summary_report(self, strategies: List[str] = None) -> str:
        """
        サマリーレポート生成
        
        Args:
            strategies: 対象戦略リスト
        
        Returns:
            str: レポートファイルパス
        """
        if strategies is None:
            strategies = ["swing_trading", "long_term"]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_summary_{timestamp}.html"
        filepath = os.path.join(self.results_dir, "aggregated", filename)
        
        # HTMLレポートの生成
        html_content = self._generate_html_report(strategies)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"サマリーレポート生成: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"サマリーレポート生成エラー: {e}")
            return ""
    
    def _generate_html_report(self, strategies: List[str]) -> str:
        """HTMLレポート内容を生成"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>バックテスト集計レポート</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .strategy-section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        .metric-table th, .metric-table td {{ border: 1px solid #ddd; padding: 8px; text-align: right; }}
        .metric-table th {{ background-color: #f5f5f5; text-align: center; }}
        .stock-usage {{ max-height: 300px; overflow-y: auto; }}
        .error {{ color: red; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>バックテスト集計レポート</h1>
        <p>生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
"""
        
        for strategy in strategies:
            aggregated = self.aggregate_results(strategy)
            if not aggregated:
                html += f"""
    <div class="strategy-section">
        <h2>{strategy}</h2>
        <p class="error">データが不足しています</p>
    </div>
"""
                continue
            
            html += f"""
    <div class="strategy-section">
        <h2>{strategy}</h2>
        <p>実行回数: {aggregated['total_runs']}回</p>
        <p>実行期間: {aggregated['first_run']} 〜 {aggregated['last_run']}</p>
        
        <h3>主要指標</h3>
        <table class="metric-table">
            <tr>
                <th>指標</th>
                <th>平均</th>
                <th>標準偏差</th>
                <th>最小</th>
                <th>最大</th>
                <th>中央値</th>
            </tr>
"""
            
            # 主要指標の表示
            key_metrics = ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']
            for metric in key_metrics:
                if f"{metric}_mean" in aggregated:
                    html += f"""
            <tr>
                <td>{metric}</td>
                <td>{aggregated[f'{metric}_mean']:.4f}</td>
                <td>{aggregated[f'{metric}_std']:.4f}</td>
                <td>{aggregated[f'{metric}_min']:.4f}</td>
                <td>{aggregated[f'{metric}_max']:.4f}</td>
                <td>{aggregated[f'{metric}_median']:.4f}</td>
            </tr>
"""
            
            html += """
        </table>
        
        <h3>銘柄使用頻度（上位20銘柄）</h3>
        <div class="stock-usage">
            <table class="metric-table">
                <tr>
                    <th>銘柄</th>
                    <th>使用回数</th>
                </tr>
"""
            
            # 銘柄使用頻度の表示（上位20銘柄）
            stock_usage = aggregated.get('stock_usage', {})
            sorted_stocks = sorted(stock_usage.items(), key=lambda x: x[1], reverse=True)[:20]
            
            for stock, count in sorted_stocks:
                html += f"""
                <tr>
                    <td>{stock}</td>
                    <td>{count}</td>
                </tr>
"""
            
            html += """
            </table>
        </div>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        return html
    
    def get_performance_summary(self, strategy: str) -> Dict[str, float]:
        """
        戦略のパフォーマンスサマリーを取得
        
        Args:
            strategy: 戦略名
        
        Returns:
            Dict: パフォーマンスサマリー
        """
        aggregated = self.aggregate_results(strategy)
        if not aggregated:
            return {}
        
        return {
            "total_return_mean": aggregated.get("total_return_mean", 0),
            "sharpe_ratio_mean": aggregated.get("sharpe_ratio_mean", 0),
            "max_drawdown_mean": aggregated.get("max_drawdown_mean", 0),
            "win_rate_mean": aggregated.get("win_rate_mean", 0),
            "total_runs": aggregated.get("total_runs", 0)
        }
