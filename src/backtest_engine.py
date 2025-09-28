"""
バックテストエンジン
並列処理による高速バックテスト実行
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime, timedelta
from strategy import SwingTradingStrategy
from data_fetcher import DataFetcher
from symbol_manager import SymbolManager
import json


class BacktestEngine:
    def __init__(self, config_path: str = "config.json"):
        """バックテストエンジンの初期化"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.data_fetcher = DataFetcher(config_path)
        self.strategy = SwingTradingStrategy(self.config)
        
        # 銘柄管理クラスの初期化
        self.symbol_manager = SymbolManager()
        
        # バックテスト設定
        self.period_years = self.config['backtest']['period_years']
        self.start_date_offset = self.config['backtest']['start_date_offset_months']
        self.use_cache_only = self.config['backtest']['use_cache_only']
        
    def get_backtest_period(self) -> Tuple[str, str]:
        """バックテスト期間を計算"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * self.period_years)
        
        # 前月末から開始
        if self.start_date_offset > 0:
            start_date = start_date.replace(day=1) - timedelta(days=1)
        
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def get_stock_symbols(self, custom_symbols: List[str] = None, seed: Optional[int] = None, 
                         use_file_symbols: bool = True) -> List[str]:
        """対象銘柄を取得"""
        symbols = []
        
        # symbols_config.jsonのcustom_symbolsを追加
        config_custom_symbols = self.symbol_manager.get_custom_symbols()
        if config_custom_symbols:
            symbols.extend(config_custom_symbols)
            print(f"設定ファイル指定銘柄: {len(config_custom_symbols)}銘柄")
        
        # custom_symbols（コマンドライン指定銘柄）を追加
        if custom_symbols:
            symbols.extend(custom_symbols)
            print(f"コマンドライン指定銘柄: {len(custom_symbols)}銘柄")
        
        # cacheフォルダの銘柄からランダム選択（分析実行時）
        if seed is None and self.config['strategy']['seed_management']['use_last_seed']:
            seed = self.data_fetcher.get_last_seed()
        
        random_count = self.config['strategy']['random_stocks_count']
        
        # キャッシュから銘柄を取得
        cached_symbols = self.data_fetcher.get_random_cached_symbols(random_count, seed)
        
        if cached_symbols:
            symbols.extend(cached_symbols)
            print(f"キャッシュから{len(cached_symbols)}銘柄を選択")
        else:
            # フォールバック: ファイルから銘柄を取得
            if use_file_symbols:
                file_symbols = self.symbol_manager.get_all_symbols()
                symbols.extend(file_symbols)
            
            # ランダム選定銘柄
            random_symbols = self.data_fetcher.get_random_stocks(random_count, seed)
            symbols.extend(random_symbols)
            print(f"フォールバック: ファイルから{len(random_symbols)}銘柄を選択")
        
        # 重複除去して返す
        unique_symbols = list(set(symbols))
        print(f"合計対象銘柄数: {len(unique_symbols)}銘柄")
        return unique_symbols
    
    def backtest_single_stock(self, symbol: str, start_date: str, end_date: str) -> Dict:
        """単一銘柄のバックテスト"""
        try:
            # データ取得
            if self.use_cache_only:
                data = self.data_fetcher.load_cached_data(symbol)
                if data is None:
                    return {
                        'symbol': symbol,
                        'status': 'failed',
                        'error': 'キャッシュデータが見つかりません'
                    }
            else:
                data = self.data_fetcher.fetch_stock_data(symbol, start_date, end_date)
                if data is None or data.empty:
                    return {
                        'symbol': symbol,
                        'status': 'failed',
                        'error': 'データ取得に失敗'
                    }
            
            # 日付範囲でフィルタリング
            data = data[(data.index >= start_date) & (data.index <= end_date)]
            
            if data.empty:
                return {
                    'symbol': symbol,
                    'status': 'failed',
                    'error': '指定期間のデータがありません'
                }
            
            # 戦略分析実行
            analyzed_data = self.strategy.analyze_stock(data, symbol)
            
            # パフォーマンス計算
            performance = self.calculate_performance(analyzed_data, symbol)
            
            # AI分析コメント生成
            ai_comment = self.strategy.generate_ai_comment(analyzed_data, symbol)
            
            # シグナル条件詳細生成
            signal_conditions = self.strategy.generate_signal_conditions_detail(analyzed_data)
            
            return {
                'symbol': symbol,
                'status': 'success',
                'data': analyzed_data,
                'performance': performance,
                'ai_comment': ai_comment,
                'signal_conditions': signal_conditions
            }
            
        except Exception as e:
            return {
                'symbol': symbol,
                'status': 'failed',
                'error': str(e)
            }
    
    def calculate_performance(self, data: pd.DataFrame, symbol: str) -> Dict:
        """パフォーマンス指標を計算"""
        if data.empty:
            return {}
        
        # 基本統計
        total_return = (data['close'].iloc[-1] / data['close'].iloc[0] - 1) * 100
        
        # シャープレシオ
        returns = data['close'].pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # 最大ドローダウン
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        # 勝率
        profitable_days = (returns > 0).sum()
        total_days = len(returns)
        win_rate = (profitable_days / total_days * 100) if total_days > 0 else 0
        
        # 最新シグナル
        latest_signal = data['signal'].iloc[-1] if 'signal' in data.columns else 'N/A'
        latest_score = data['total_score'].iloc[-1] if 'total_score' in data.columns else 0
        
        return {
            'total_return': round(total_return, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'win_rate': round(win_rate, 2),
            'latest_signal': latest_signal,
            'latest_score': round(latest_score, 2),
            'data_points': len(data)
        }
    
    def run_backtest(self, custom_symbols: List[str] = None, seed: Optional[int] = None, 
                    max_workers: int = 4, use_file_symbols: bool = True) -> Dict:
        """バックテスト実行（並列処理）"""
        print("バックテスト開始...")
        
        # バックテスト期間を取得
        start_date, end_date = self.get_backtest_period()
        print(f"バックテスト期間: {start_date} ～ {end_date}")
        
        # 対象銘柄を取得
        symbols = self.get_stock_symbols(custom_symbols, seed, use_file_symbols)
        print(f"対象銘柄数: {len(symbols)}")
        
        # ファイルから取得した銘柄数を表示
        if use_file_symbols:
            file_symbols = self.symbol_manager.get_all_symbols()
            print(f"ファイルから取得した銘柄数: {len(file_symbols)}")
        
        # 並列処理でバックテスト実行
        results = []
        successful_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # タスクを投入
            future_to_symbol = {
                executor.submit(self.backtest_single_stock, symbol, start_date, end_date): symbol
                for symbol in symbols
            }
            
            # 結果を収集
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['status'] == 'success':
                        successful_count += 1
                        print(f"完了: {symbol} ({successful_count}/{len(symbols)})")
                    else:
                        print(f"失敗: {symbol} - {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"エラー: {symbol} - {str(e)}")
                    results.append({
                        'symbol': symbol,
                        'status': 'failed',
                        'error': str(e)
                    })
        
        # 結果を整理
        successful_results = [r for r in results if r['status'] == 'success']
        failed_results = [r for r in results if r['status'] == 'failed']
        
        # 全体統計
        overall_stats = self.calculate_overall_performance(successful_results)
        
        print(f"\nバックテスト完了:")
        print(f"成功: {len(successful_results)}銘柄")
        print(f"失敗: {len(failed_results)}銘柄")
        print(f"成功率: {len(successful_results)/len(symbols)*100:.1f}%")
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_symbols': len(symbols),
            'successful_symbols': len(successful_results),
            'failed_symbols': len(failed_results),
            'success_rate': len(successful_results)/len(symbols)*100,
            'results': results,
            'successful_results': successful_results,
            'failed_results': failed_results,
            'overall_stats': overall_stats,
            'timestamp': datetime.now().isoformat()
        }
    
    def calculate_overall_performance(self, successful_results: List[Dict]) -> Dict:
        """全体パフォーマンス統計を計算"""
        if not successful_results:
            return {}
        
        # 各指標の平均値を計算
        total_returns = [r['performance']['total_return'] for r in successful_results]
        sharpe_ratios = [r['performance']['sharpe_ratio'] for r in successful_results]
        max_drawdowns = [r['performance']['max_drawdown'] for r in successful_results]
        win_rates = [r['performance']['win_rate'] for r in successful_results]
        
        # シグナル分布
        signals = [r['performance']['latest_signal'] for r in successful_results]
        signal_counts = pd.Series(signals).value_counts().to_dict()
        
        return {
            'avg_total_return': round(np.mean(total_returns), 2),
            'total_return_sum': round(np.sum(total_returns), 2),
            'avg_sharpe_ratio': round(np.mean(sharpe_ratios), 2),
            'avg_max_drawdown': round(np.mean(max_drawdowns), 2),
            'avg_win_rate': round(np.mean(win_rates), 2),
            'signal_distribution': signal_counts,
            'best_performer': max(successful_results, key=lambda x: x['performance']['total_return']),
            'worst_performer': min(successful_results, key=lambda x: x['performance']['total_return'])
        }
