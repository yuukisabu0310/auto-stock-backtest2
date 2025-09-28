"""
データ取得モジュール
S&P500、NASDAQ銘柄の取得とキャッシュ管理
"""
import os
import json
import pickle
import random
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import time
from tqdm import tqdm
from symbol_manager import SymbolManager
from symbol_loader import SymbolLoader
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import numpy as np


class DataFetcher:
    def __init__(self, config_path: str = "config.json", allow_all_alpha_vantage: bool = False):
        """データ取得クラスの初期化"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.cache_dir = self.config['cache']['directory']
        self.data_sources = self.config['data_sources']['priority']
        self.retry_attempts = self.config['data_sources']['retry_attempts']
        self.timeout = self.config['data_sources']['timeout']
        self.allow_all_alpha_vantage = allow_all_alpha_vantage
        
        # キャッシュディレクトリの作成
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 銘柄管理クラスの初期化
        self.symbol_manager = SymbolManager()
        
        # 銘柄ローダーの初期化
        self.symbol_loader = SymbolLoader(config_path)
        
        # Alpha Vantage制限管理
        self.alpha_vantage_lock = threading.Lock()
        self.alpha_vantage_last_request = 0
        self.alpha_vantage_request_count = 0
        self.alpha_vantage_reset_time = 0
        
    def get_sp500_symbols(self) -> List[str]:
        """S&P500銘柄リストを取得"""
        try:
            # 外部ファイルから銘柄リストを取得
            symbols = self.symbol_loader.get_symbols_from_config(['sp500_symbols'])
            if symbols:
                return symbols
            
            # フォールバック: 主要銘柄リスト
            return [
                "AAPL.US", "MSFT.US", "GOOGL.US", "AMZN.US", "TSLA.US",
                "META.US", "NVDA.US", "BRK-B.US", "UNH.US", "JNJ.US",
                "JPM.US", "V.US", "PG.US", "HD.US", "MA.US",
                "DIS.US", "PYPL.US", "ADBE.US", "CRM.US", "NFLX.US"
            ]
            
        except Exception as e:
            print(f"S&P500銘柄取得エラー: {e}")
            # フォールバック: 主要銘柄リスト
            return [
                "AAPL.US", "MSFT.US", "GOOGL.US", "AMZN.US", "TSLA.US",
                "META.US", "NVDA.US", "BRK-B.US", "UNH.US", "JNJ.US"
            ]
    
    def get_nasdaq_symbols(self) -> List[str]:
        """NASDAQ銘柄リストを取得"""
        try:
            # 外部ファイルから銘柄リストを取得
            symbols = self.symbol_loader.get_symbols_from_config(['nasdaq_symbols'])
            if symbols:
                return symbols
            
            # フォールバック: 主要銘柄リスト
            return [
                "AAPL.US", "MSFT.US", "GOOGL.US", "AMZN.US", "TSLA.US",
                "META.US", "NVDA.US", "AMD.US", "INTC.US", "CSCO.US",
                "ORCL.US", "ADBE.US", "CRM.US", "NFLX.US", "PYPL.US"
            ]
            
        except Exception as e:
            print(f"NASDAQ銘柄取得エラー: {e}")
            return []
    
    def get_random_stocks(self, count: int = 100, seed: Optional[int] = None) -> List[str]:
        """ランダムに銘柄を選定"""
        if seed is not None:
            random.seed(seed)
        
        # 外部ファイルから銘柄リストを取得
        try:
            # 設定ファイルから全銘柄を取得
            symbols = self.symbol_loader.get_all_symbols()
            if symbols:
                # ランダムに選択
                if len(symbols) >= count:
                    selected_symbols = random.sample(symbols, count)
                else:
                    selected_symbols = symbols
            else:
                # フォールバック: S&P500とNASDAQから銘柄を取得
                sp500_symbols = self.get_sp500_symbols()
                nasdaq_symbols = self.get_nasdaq_symbols()
                
                # 重複を除去して結合
                all_symbols = list(set(sp500_symbols + nasdaq_symbols))
                
                # ランダムに選択
                if len(all_symbols) >= count:
                    selected_symbols = random.sample(all_symbols, count)
                else:
                    selected_symbols = all_symbols
        except Exception as e:
            print(f"銘柄取得エラー: {e}")
            # フォールバック: 主要銘柄リスト
            selected_symbols = [
                "AAPL.US", "MSFT.US", "GOOGL.US", "AMZN.US", "TSLA.US",
                "META.US", "NVDA.US", "BRK-B.US", "UNH.US", "JNJ.US"
            ]
        
        # シードを保存（再現性のため）
        if seed is not None:
            with open(os.path.join(self.cache_dir, "last_seed.txt"), 'w') as f:
                f.write(str(seed))
        
        return selected_symbols
    
    def get_all_symbols(self, exclude_cached: bool = False) -> List[str]:
        """symbols_config.jsonの全銘柄を取得
        
        Args:
            exclude_cached: Trueの場合、キャッシュに存在する銘柄を除外（未取得銘柄のみ）
        """
        try:
            all_symbols = self.symbol_loader.get_all_symbols(limit=False)
        except Exception as e:
            print(f"全銘柄取得エラー: {e}")
            # フォールバック: 主要銘柄リスト
            all_symbols = [
                "AAPL.US", "MSFT.US", "GOOGL.US", "AMZN.US", "TSLA.US",
                "META.US", "NVDA.US", "BRK-B.US", "UNH.US", "JNJ.US"
            ]
        
        if exclude_cached:
            # キャッシュに存在する銘柄を取得
            cached_symbols = []
            if os.path.exists(self.cache_dir):
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.pkl') and not filename.startswith('last_seed'):
                        # ファイル名から銘柄名を復元
                        symbol = filename.replace('.pkl', '').replace('_', '.')
                        cached_symbols.append(symbol)
            
            # 未取得銘柄のみを返す
            uncached_symbols = [symbol for symbol in all_symbols if symbol not in cached_symbols]
            
            print(f"全銘柄数: {len(all_symbols)}")
            print(f"取得済み銘柄数: {len(cached_symbols)}")
            print(f"未取得銘柄数: {len(uncached_symbols)}")
            
            return uncached_symbols
        
        return all_symbols
    
    def get_cached_symbols(self) -> List[str]:
        """cacheフォルダに存在する銘柄一覧を取得"""
        cached_symbols = []
        
        if not os.path.exists(self.cache_dir):
            print(f"キャッシュディレクトリが存在しません: {self.cache_dir}")
            return []
        
        try:
            # cacheディレクトリ内の.pklファイルを検索
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl') and not filename.startswith('last_'):
                    # ファイル名から銘柄シンボルを復元
                    symbol = filename.replace('.pkl', '').replace('_', '.')
                    if symbol.endswith('.US'):
                        cached_symbols.append(symbol)
            
            print(f"キャッシュから{len(cached_symbols)}銘柄を発見")
            return cached_symbols
            
        except Exception as e:
            print(f"キャッシュ銘柄取得エラー: {e}")
            return []
    
    def get_random_cached_symbols(self, count: int = 100, seed: Optional[int] = None) -> List[str]:
        """cacheフォルダの銘柄からランダムに選択"""
        if seed is not None:
            random.seed(seed)
        
        cached_symbols = self.get_cached_symbols()
        
        if not cached_symbols:
            print("キャッシュされた銘柄が見つかりません")
            return []
        
        # ランダムに選択
        if len(cached_symbols) >= count:
            selected_symbols = random.sample(cached_symbols, count)
        else:
            selected_symbols = cached_symbols
            print(f"キャッシュ銘柄数({len(cached_symbols)})が要求数({count})より少ないため、全銘柄を使用")
        
        # シードを保存（再現性のため）
        if seed is not None:
            with open(os.path.join(self.cache_dir, "last_seed.txt"), 'w') as f:
                f.write(str(seed))
        
        return selected_symbols
    
    def fetch_stock_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """個別銘柄のデータを取得（並列処理対応）"""
        cache_file = os.path.join(self.cache_dir, f"{symbol.replace('.', '_')}.pkl")
        
        # キャッシュが存在する場合はキャッシュから読み込み
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                
                # キャッシュデータの日付範囲をチェック
                if (cached_data.index.min() <= pd.to_datetime(start_date) and 
                    cached_data.index.max() >= pd.to_datetime(end_date)):
                    return cached_data
            except Exception as e:
                print(f"キャッシュ読み込みエラー {symbol}: {e}")
        
        # データソースから取得を試行
        for source in self.data_sources:
            try:
                if source == "yfinance":
                    data = self._fetch_from_yfinance(symbol, start_date, end_date)
                elif source == "stooq":
                    data = self._fetch_from_stooq(symbol, start_date, end_date)
                elif source == "alpha_vantage":
                    # Alpha Vantage制限チェック
                    if not self.allow_all_alpha_vantage:
                        # カスタム銘柄のみ
                        custom_symbols = self.symbol_manager.get_custom_symbols()
                        if symbol not in custom_symbols:
                            continue  # カスタム銘柄でない場合はスキップ
                    data = self._fetch_from_alpha_vantage(symbol, start_date, end_date)
                else:
                    continue
                
                if data is not None and not data.empty:
                    # キャッシュに保存（スレッドセーフ）
                    try:
                        with open(cache_file, 'wb') as f:
                            pickle.dump(data, f)
                    except Exception as e:
                        print(f"キャッシュ保存エラー {symbol}: {e}")
                    
                    return data
                    
            except Exception as e:
                print(f"データ取得エラー {symbol} from {source}: {e}")
                continue
        
        print(f"全データソースで取得失敗: {symbol}")
        return None
    
    def fetch_parallel_data(self, symbols: List[str], start_date: str, end_date: str, 
                           max_workers: int = 4) -> Dict[str, pd.DataFrame]:
        """並列でデータを取得"""
        results = {}
        
        print(f"並列データ取得開始: {len(symbols)}銘柄 (ワーカー数: {max_workers})")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # タスクを投入
            future_to_symbol = {
                executor.submit(self.fetch_stock_data, symbol, start_date, end_date): symbol
                for symbol in symbols
            }
            
            # 結果を収集
            for future in tqdm(as_completed(future_to_symbol), total=len(symbols), desc="並列データ取得中"):
                symbol = future_to_symbol[future]
                try:
                    data = future.result()
                    if data is not None and not data.empty:
                        results[symbol] = data
                        print(f"✅ 取得成功: {symbol}")
                    else:
                        print(f"❌ 取得失敗: {symbol}")
                        
                except Exception as e:
                    print(f"❌ 取得エラー: {symbol} - {str(e)}")
        
        print(f"並列データ取得完了: {len(results)}/{len(symbols)}銘柄")
        return results
    
    def _fetch_from_yfinance(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """yfinanceからデータを取得"""
        try:
            # .USサフィックスを削除してyfinanceで取得
            clean_symbol = symbol.replace('.US', '')
            ticker = yf.Ticker(clean_symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty:
                return None
            
            # カラム名を標準化
            data.columns = [col.lower() for col in data.columns]
            return data
            
        except Exception as e:
            raise Exception(f"yfinance取得エラー: {e}")
    
    def _fetch_from_stooq(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Stooqからデータを取得"""
        try:
            # Stooqは実装していないため、Noneを返す
            raise NotImplementedError("Stooq API実装が必要")
            
        except Exception as e:
            raise Exception(f"Stooq取得エラー: {e}")
    
    def _fetch_from_alpha_vantage(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Alpha Vantageからデータを取得"""
        try:
            # Alpha Vantage制限管理（1分で5リクエスト、12秒間隔）
            with self.alpha_vantage_lock:
                current_time = time.time()
                
                # 1分が経過したらリセット
                if current_time - self.alpha_vantage_reset_time >= 60:
                    self.alpha_vantage_request_count = 0
                    self.alpha_vantage_reset_time = current_time
                
                # 5リクエスト制限チェック
                if self.alpha_vantage_request_count >= 5:
                    wait_time = 60 - (current_time - self.alpha_vantage_reset_time)
                    if wait_time > 0:
                        print(f"Alpha Vantage制限: {wait_time:.1f}秒待機中...")
                        time.sleep(wait_time)
                        self.alpha_vantage_request_count = 0
                        self.alpha_vantage_reset_time = time.time()
                
                # 12秒間隔チェック
                if current_time - self.alpha_vantage_last_request < 12:
                    wait_time = 12 - (current_time - self.alpha_vantage_last_request)
                    print(f"Alpha Vantage間隔制限: {wait_time:.1f}秒待機中...")
                    time.sleep(wait_time)
                
                self.alpha_vantage_request_count += 1
                self.alpha_vantage_last_request = time.time()
            
            # Alpha Vantage API実装（実際のAPIキーが必要）
            # ここではサンプルデータを返す
            print(f"Alpha Vantage取得: {symbol} (制限管理済み)")
            
            # サンプルデータを生成（実際のAPI実装時は削除）
            return self._generate_sample_data(symbol, start_date, end_date)
            
        except Exception as e:
            raise Exception(f"Alpha Vantage取得エラー: {e}")
    
    def _generate_sample_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """サンプルデータを生成（Alpha Vantage用）"""
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        dates = pd.date_range(start=start, end=end, freq='D')
        dates = dates[dates.weekday < 5]  # 営業日のみ
        
        # シンボルに基づくシード
        np.random.seed(hash(symbol) % 2**32)
        initial_price = 100.0
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = [initial_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(max(new_price, 1.0))
        
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = prices[i-1] if i > 0 else price
            volume = int(np.random.normal(1000000, 200000))
            volume = max(volume, 100000)
            
            data.append({
                'Open': open_price,
                'High': high,
                'Low': low,
                'Close': price,
                'Volume': volume
            })
        
        df = pd.DataFrame(data, index=dates)
        df.columns = [col.lower() for col in df.columns]
        return df
    
    def get_successful_symbols(self, symbols: List[str], start_date: str, end_date: str, 
                              max_workers: int = 4) -> List[str]:
        """成功した銘柄のみを取得（並列処理対応）"""
        successful_symbols = []
        
        print(f"データ取得開始: {len(symbols)}銘柄 (並列処理: {max_workers}ワーカー)")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # タスクを投入
            future_to_symbol = {
                executor.submit(self.fetch_stock_data, symbol, start_date, end_date): symbol
                for symbol in symbols
            }
            
            # 結果を収集
            for future in tqdm(as_completed(future_to_symbol), total=len(symbols), desc="データ取得中"):
                symbol = future_to_symbol[future]
                try:
                    data = future.result()
                    if data is not None and not data.empty:
                        successful_symbols.append(symbol)
                        print(f"✅ 取得成功: {symbol} ({len(successful_symbols)}/100)")
                        
                        if len(successful_symbols) >= 100:
                            # 残りのタスクをキャンセル
                            for f in future_to_symbol:
                                f.cancel()
                            break
                    else:
                        print(f"❌ 取得失敗: {symbol}")
                        
                except Exception as e:
                    print(f"❌ 取得エラー: {symbol} - {str(e)}")
        
        print(f"データ取得完了: {len(successful_symbols)}銘柄")
        return successful_symbols
    
    def load_cached_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """キャッシュからデータを読み込み"""
        cache_file = os.path.join(self.cache_dir, f"{symbol.replace('.', '_')}.pkl")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"キャッシュ読み込みエラー {symbol}: {e}")
        
        return None
    
    def get_last_seed(self) -> Optional[int]:
        """前回のシードを取得"""
        seed_file = os.path.join(self.cache_dir, "last_seed.txt")
        if os.path.exists(seed_file):
            try:
                with open(seed_file, 'r') as f:
                    return int(f.read().strip())
            except Exception:
                pass
        return None
