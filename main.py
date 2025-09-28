"""
スイングトレード分析システム - メイン実行スクリプト
"""
import os
import sys
import json
import argparse
import shutil
import logging
from datetime import datetime
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# パスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from report_generator import ReportGenerator
from symbol_manager import SymbolManager


def setup_logging():
    """ログ設定を初期化"""
    # ログディレクトリを作成
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイル名（タイムスタンプ付き）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f"swing_trading_{timestamp}.log")
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)  # コンソール出力も維持
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"ログファイル: {log_file}")
    
    return logger


class SwingTradingSystem:
    def __init__(self, config_path: str = "config.json", allow_all_alpha_vantage: bool = False):
        """スイングトレード分析システムの初期化"""
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        
        # 設定ファイルの読み込み
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # 各コンポーネントの初期化
        self.data_fetcher = DataFetcher(config_path, allow_all_alpha_vantage)
        self.backtest_engine = BacktestEngine(config_path)
        
        # 銘柄管理クラスの初期化
        self.symbol_manager = SymbolManager()
        
        # レポート生成クラスの初期化（symbol_managerを渡す）
        self.report_generator = ReportGenerator(config_path, self.symbol_manager)
        
        self.logger.info("🚀 スイングトレード分析システムが初期化されました")
    
    def create_archive_folder(self) -> str:
        """分析結果用のアーカイブフォルダを作成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_folder = os.path.join(self.config['reports']['output_dir'], f"analysis_{timestamp}")
        os.makedirs(archive_folder, exist_ok=True)
        print(f"📁 アーカイブフォルダ作成: {archive_folder}")
        return archive_folder
    
    def generate_single_individual_report(self, result: Dict, archive_folder: str, custom_symbols: List[str] = None) -> Dict:
        """単一の個別レポートを生成するヘルパー関数（並列処理用）"""
        symbol = result['symbol']
        is_custom = custom_symbols and symbol in custom_symbols
        prefix = "🎯" if is_custom else "📊"
        
        try:
            individual_report_path = self.report_generator.generate_individual_report(symbol, result, archive_folder)
            return {
                'success': True,
                'symbol': symbol,
                'path': individual_report_path,
                'prefix': prefix,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'symbol': symbol,
                'path': None,
                'prefix': prefix,
                'error': str(e)
            }
    
    def archive_reports(self, report_paths: Dict[str, str], archive_folder: str) -> Dict[str, str]:
        """レポートファイルをアーカイブフォルダに移動（index.htmlは除外）"""
        archived_paths = {}
        
        for report_type, original_path in report_paths.items():
            if original_path and os.path.exists(original_path):
                filename = os.path.basename(original_path)
                
                # index.htmlはreports配下に残す
                if filename == 'index.html':
                    archived_paths[report_type] = original_path
                    print(f"📋 インデックスレポート保持: {original_path}")
                else:
                    new_path = os.path.join(archive_folder, filename)
                    shutil.move(original_path, new_path)
                    archived_paths[report_type] = new_path
                    print(f"📦 アーカイブ移動: {filename}")
        
        return archived_paths
    
    def run_analysis(self, custom_symbols: List[str] = None, seed: Optional[int] = None, 
                    max_workers: int = 4, use_file_symbols: bool = True) -> Dict:
        """分析を実行"""
        print("\n" + "="*60)
        print("📊 スイングトレード分析を開始します")
        print("="*60)
        
        # バックテスト実行
        print("\n🔄 バックテストを実行中...")
        backtest_results = self.backtest_engine.run_backtest(
            custom_symbols=custom_symbols,
            seed=seed,
            max_workers=max_workers,
            use_file_symbols=use_file_symbols
        )
        
        # アーカイブフォルダ作成
        archive_folder = self.create_archive_folder()
        
        # レポート生成
        print("\n📝 レポートを生成中...")
        
        # メインレポート生成
        main_report_path = self.report_generator.generate_swing_trading_report(backtest_results)
        print(f"✅ メインレポート生成完了: {main_report_path}")
        
        # 銘柄一覧レポート生成
        stocks_report_path = self.report_generator.generate_stocks_report(backtest_results, custom_symbols)
        print(f"✅ 銘柄一覧レポート生成完了: {stocks_report_path}")
        
        # 個別銘柄レポート生成（全銘柄）
        successful_results = backtest_results.get('successful_results', [])
        individual_reports = []
        
        # custom_symbolsを優先してソート
        def sort_key(result):
            symbol = result['symbol']
            if custom_symbols and symbol in custom_symbols:
                return (0, custom_symbols.index(symbol))  # custom_symbolsを最初に、その順序で
            else:
                return (1, 0)  # その他の銘柄は後
        
        sorted_results = sorted(successful_results, key=sort_key)
        
        print(f"📝 個別レポート生成開始: {len(sorted_results)}銘柄")
        
        # 並列処理で個別レポートを生成
        individual_reports = []
        successful_reports = 0
        failed_reports = 0
        
        # 進捗表示用のロック
        progress_lock = threading.Lock()
        
        # 最適なワーカー数を決定（CPUコア数の2倍、最大8）
        max_workers = min(max_workers * 2, 8, len(sorted_results))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 全タスクをキューに投入
            future_to_result = {
                executor.submit(self.generate_single_individual_report, result, archive_folder, custom_symbols): result
                for result in sorted_results
            }
            
            # 完了したタスクを順次処理
            for future in as_completed(future_to_result):
                report_result = future.result()
                
                with progress_lock:
                    if report_result['success']:
                        individual_reports.append(report_result['path'])
                        successful_reports += 1
                        print(f"{report_result['prefix']} 個別レポート生成完了: {report_result['symbol']} - {report_result['path']}")
                    else:
                        failed_reports += 1
                        print(f"❌ 個別レポート生成失敗: {report_result['symbol']} - {report_result['error']}")
                    
                    # 進捗表示
                    total_processed = successful_reports + failed_reports
                    progress = (total_processed / len(sorted_results)) * 100
                    print(f"📊 進捗: {total_processed}/{len(sorted_results)} ({progress:.1f}%) - 成功: {successful_reports}, 失敗: {failed_reports}")
        
        print(f"✅ 個別レポート生成完了: 成功 {successful_reports}件, 失敗 {failed_reports}件")
        
        # 結果サマリー
        print("\n" + "="*60)
        print("📈 分析結果サマリー")
        print("="*60)
        
        overall_stats = backtest_results.get('overall_stats', {})
        print(f"対象銘柄数: {backtest_results.get('total_symbols', 0)}")
        print(f"成功銘柄数: {backtest_results.get('successful_symbols', 0)}")
        print(f"成功率: {backtest_results.get('success_rate', 0):.1f}%")
        print(f"平均総リターン: {overall_stats.get('avg_total_return', 0):.1f}%")
        print(f"平均シャープレシオ: {overall_stats.get('avg_sharpe_ratio', 0):.2f}")
        print(f"平均最大ドローダウン: {overall_stats.get('avg_max_drawdown', 0):.1f}%")
        
        # シグナル分布
        signal_dist = overall_stats.get('signal_distribution', {})
        if signal_dist:
            print("\n📊 シグナル分布:")
            for signal, count in signal_dist.items():
                print(f"  {signal}: {count}銘柄")
        
        # ベスト・ワーストパフォーマー
        best = overall_stats.get('best_performer')
        worst = overall_stats.get('worst_performer')
        
        if best:
            print(f"\n🏆 ベストパフォーマー: {best['symbol']} ({best['performance']['total_return']:.1f}%)")
        if worst:
            print(f"📉 ワーストパフォーマー: {worst['symbol']} ({worst['performance']['total_return']:.1f}%)")
        
        # レポートをアーカイブフォルダに移動
        print("\n📦 レポートをアーカイブフォルダに移動中...")
        report_paths = {
            'main_report': main_report_path,
            'stocks_report': stocks_report_path
        }
        
        # 個別レポートも追加
        for i, individual_path in enumerate(individual_reports):
            report_paths[f'individual_report_{i}'] = individual_path
        
        archived_paths = self.archive_reports(report_paths, archive_folder)
        
        # アーカイブ移動後にインデックスレポート更新（最新レポートを反映）
        index_report_path = self.report_generator.generate_index_report()
        print(f"✅ インデックスレポート更新完了: {index_report_path}")
        
        print(f"\n🎉 分析完了！結果は以下に保存されました:")
        print(f"📁 アーカイブフォルダ: {archive_folder}")
        print(f"📊 メインレポート: {archived_paths.get('main_report', 'N/A')}")
        print(f"📋 銘柄一覧レポート: {archived_paths.get('stocks_report', 'N/A')}")
        print(f"🔗 インデックスレポート: {index_report_path}")
        print(f"📄 個別レポート: {len([k for k in archived_paths.keys() if k.startswith('individual_report_')])}件")
        
        return {
            'backtest_results': backtest_results,
            'archive_folder': archive_folder,
            'archived_paths': archived_paths,
            'individual_reports_count': len(individual_reports)
        }
    
    def update_data(self, symbols: List[str] = None, max_workers: int = 4, use_all_symbols: bool = False, uncached_only: bool = False) -> bool:
        """データを更新（初回データ取得時）"""
        print("\n" + "="*60)
        print("📥 データ更新を開始します")
        print("="*60)
        
        if symbols is None:
            if use_all_symbols:
                if uncached_only:
                    # 未取得銘柄のみを取得
                    symbols = self.data_fetcher.get_all_symbols(exclude_cached=True)
                    print(f"未取得銘柄のみを対象: {len(symbols)}銘柄")
                else:
                    # symbols_config.jsonの全銘柄を取得
                    symbols = self.data_fetcher.get_all_symbols()
                    print(f"symbols_config.jsonから全銘柄を取得: {len(symbols)}銘柄")
            else:
                # ランダム銘柄を取得
                symbols = self.data_fetcher.get_random_stocks(100)
        
        # バックテスト期間を取得
        start_date, end_date = self.backtest_engine.get_backtest_period()
        
        print(f"データ取得期間: {start_date} ～ {end_date}")
        print(f"対象銘柄数: {len(symbols)}")
        print(f"並列処理数: {max_workers}ワーカー")
        
        # 並列データ取得
        successful_symbols = self.data_fetcher.get_successful_symbols(symbols, start_date, end_date, max_workers)
        
        print(f"\n✅ データ更新完了: {len(successful_symbols)}銘柄のデータを取得")
        
        return len(successful_symbols) > 0


def main():
    """メイン実行関数"""
    # ログ設定を初期化
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description='スイングトレード分析システム')
    parser.add_argument('--symbols', nargs='+', help='指定銘柄（例: AAPL.US MSFT.US）')
    parser.add_argument('--seed', type=int, help='ランダムシード（指定しない場合は前回のシードを使用）')
    parser.add_argument('--workers', type=int, default=4, help='並列処理数（デフォルト: 4）')
    parser.add_argument('--update-data', action='store_true', help='データ更新を実行（全銘柄）')
    parser.add_argument('--init-data', action='store_true', help='初期データ取得（Alpha Vantage全銘柄対応）')
    parser.add_argument('--no-file-symbols', action='store_true', help='ファイルから銘柄を読み込まない')
    parser.add_argument('--config', default='config.json', help='設定ファイルパス')
    
    args = parser.parse_args()
    
    logger.info(f"実行開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"引数: {vars(args)}")
    
    try:
        # システム初期化
        allow_all_alpha_vantage = args.init_data
        system = SwingTradingSystem(args.config, allow_all_alpha_vantage)
        
        # 銘柄選択ロジック
        custom_symbols = args.symbols
        
        if args.update_data:
            # データ更新モード（全銘柄）
            success = system.update_data(custom_symbols, max_workers=args.workers, use_all_symbols=True)
            if success:
                print("✅ データ更新が完了しました")
            else:
                print("❌ データ更新に失敗しました")
                sys.exit(1)
        elif args.init_data:
            # 初期データ取得モード（未取得銘柄のみ）
            success = system.update_data(custom_symbols, max_workers=args.workers, use_all_symbols=True, uncached_only=True)
            if success:
                print("✅ 初期データ取得が完了しました")
            else:
                print("❌ 初期データ取得に失敗しました")
                sys.exit(1)
        else:
            # 分析実行モード
            use_file_symbols = not args.no_file_symbols
            results = system.run_analysis(
                custom_symbols=custom_symbols,
                seed=args.seed,
                max_workers=args.workers,
                use_file_symbols=use_file_symbols
            )
            
            print("\n🎉 分析が完了しました！")
            print(f"📊 メインレポート: {results['archived_paths']['main_report']}")
            print(f"📈 銘柄一覧: {results['archived_paths']['stocks_report']}")
            
    except KeyboardInterrupt:
        print("\n⚠️ ユーザーによって中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
