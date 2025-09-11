"""
データローダーモジュール
株価データの取得、キャッシュ、検証、クリーニング
"""

import os
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import List, Optional, Dict
import pickle
import time
import concurrent.futures
from functools import partial

class DataLoader:
    """データローダークラス"""
    
    def __init__(self, cache_dir: str = "cache", max_workers: int = 3, local_test_mode: bool = False):
        """
        初期化
        
        Args:
            cache_dir: キャッシュディレクトリ
            max_workers: 並列処理の最大ワーカー数
        """
        self.cache_dir = cache_dir
        self.max_workers = max_workers
        self.local_test_mode = local_test_mode
        self.logger = logging.getLogger(__name__)
        
        # キャッシュディレクトリの作成
        os.makedirs(cache_dir, exist_ok=True)
    
    def _file_exists(self, filename: str) -> bool:
        """
        ファイルの存在確認
        
        Args:
            filename: ファイル名
        
        Returns:
            bool: ファイルの存在
        """
        filepath = os.path.join(self.cache_dir, filename)
        return os.path.exists(filepath)
    
    def get_stock_data(self, symbol: str, start_date: str = "2020-01-01", 
                       end_date: str = "2025-08-31", interval: str = "1d", 
                       max_retries: int = 3) -> pd.DataFrame:
        """
        株価データを取得（差分取得対応）
        
        Args:
            symbol: 銘柄コード
            start_date: 開始日
            end_date: 終了日
            interval: 時間間隔 (1d, 1wk等)
            max_retries: 最大リトライ回数
        
        Returns:
            DataFrame: 株価データ
        """
        cache_file = os.path.join(self.cache_dir, f"{symbol}_{interval}_{start_date}_{end_date}.pkl")
        
        # 既存のキャッシュデータを読み込み
        existing_data = pd.DataFrame()
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    existing_data = pickle.load(f)
                if not existing_data.empty:
                    self.logger.info(f"既存キャッシュを読み込み: {symbol}")
            except Exception as e:
                self.logger.warning(f"キャッシュ読み込みエラー: {symbol}, {e}")
        
        # 不足している期間を特定
        missing_periods = self._get_missing_periods(existing_data, start_date, end_date)
        
        if not missing_periods:
            # データが完全に揃っている場合
            self.logger.info(f"キャッシュから完全なデータを取得: {symbol}")
            return existing_data
        
        # 不足している期間のデータを取得
        self.logger.info(f"差分データ取得開始: {symbol} (不足期間: {len(missing_periods)}個)")
        new_data_parts = []
        for i, (period_start, period_end) in enumerate(missing_periods, 1):
            self.logger.info(f"不足期間 {i}/{len(missing_periods)} のデータを取得: {symbol} ({period_start} 〜 {period_end})")
            
            try:
                period_data = self._get_from_stooq(symbol, period_start, period_end, interval, max_retries)
                if not period_data.empty:
                    new_data_parts.append(period_data)
                    self.logger.info(f"期間データ取得成功: {symbol} ({period_start} 〜 {period_end}) - {len(period_data)}行")
                else:
                    self.logger.warning(f"期間データが空: {symbol} ({period_start} 〜 {period_end})")
            except Exception as e:
                self.logger.error(f"期間データ取得失敗: {symbol} ({period_start} 〜 {period_end}), {e}")
        
        # 新規データをマージ
        if new_data_parts:
            new_data = pd.concat(new_data_parts)
            new_data = new_data[~new_data.index.duplicated(keep='first')]
            new_data = new_data.sort_index()
            
            self.logger.info(f"新規データマージ: {symbol} (新規: {len(new_data)}行, 既存: {len(existing_data)}行)")
            
            # 既存データとマージ
            final_data = self._merge_data(existing_data, new_data)
            
            # 要求期間でフィルタリング
            final_data = final_data[
                (final_data.index >= pd.to_datetime(start_date)) & 
                (final_data.index <= pd.to_datetime(end_date))
            ]
            
            # キャッシュに保存
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(final_data, f)
                self.logger.info(f"差分データ取得完了: {symbol} (最終: {len(final_data)}行, 新規追加: {len(new_data)}行)")
            except Exception as e:
                self.logger.warning(f"キャッシュ保存エラー: {symbol}, {e}")
            
            return final_data
        else:
            # 新規データが取得できなかった場合
            if not existing_data.empty:
                self.logger.warning(f"新規データ取得失敗、既存キャッシュを使用: {symbol}")
                return existing_data
            else:
                self.logger.error(f"データ取得完全失敗: {symbol}")
                return pd.DataFrame()
    
    def _get_missing_periods(self, existing_data: pd.DataFrame, start_date: str, end_date: str) -> list:
        """
        不足している期間を特定
        
        Args:
            existing_data: 既存データ
            start_date: 要求開始日
            end_date: 要求終了日
        
        Returns:
            list: 不足期間のリスト [(start, end), ...]
        """
        if existing_data.empty:
            self.logger.info(f"既存データなし、全期間を取得: {start_date} 〜 {end_date}")
            return [(start_date, end_date)]
        
        # 既存データの期間を確認
        existing_start = existing_data.index.min().strftime('%Y-%m-%d')
        existing_end = existing_data.index.max().strftime('%Y-%m-%d')
        
        self.logger.info(f"要求期間: {start_date} 〜 {end_date}")
        self.logger.info(f"既存データ期間: {existing_start} 〜 {existing_end}")
        
        missing_periods = []
        
        # 開始日より前の期間
        if start_date < existing_start:
            missing_periods.append((start_date, existing_start))
        
        # 終了日より後の期間
        if end_date > existing_end:
            missing_periods.append((existing_end, end_date))
        
        if missing_periods:
            self.logger.info(f"不足期間を特定: {missing_periods}")
        else:
            self.logger.info("不足期間なし")
        
        return missing_periods
    
    def _merge_data(self, existing_data: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
        """
        既存データと新規データをマージ
        
        Args:
            existing_data: 既存データ
            new_data: 新規データ
        
        Returns:
            DataFrame: マージされたデータ
        """
        if existing_data.empty:
            return new_data
        
        # データを結合
        merged_data = pd.concat([existing_data, new_data])
        
        # 重複を除去（新しいデータを優先）
        merged_data = merged_data[~merged_data.index.duplicated(keep='last')]
        
        # 日付順にソート
        merged_data = merged_data.sort_index()
        
        return merged_data
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        データの妥当性を検証
        
        Args:
            data: 株価データ
        
        Returns:
            bool: 妥当性
        """
        if data.empty:
            return False
        
        # 必要なカラムの確認
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_columns):
            return False
        
        # データ量の確認（最低30日分）
        if len(data) < 30:
            return False
        
        # 欠損値の確認
        if data[required_columns].isnull().any().any():
            return False
        
        return True
    
    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        データのクリーニング
        
        Args:
            data: 株価データ
        
        Returns:
            DataFrame: クリーニング済みデータ
        """
        # 欠損値の処理
        data = data.dropna()
        
        # 異常値の処理（価格が0以下の場合）
        data = data[data['Close'] > 0]
        data = data[data['Volume'] >= 0]
        
        # 重複データの削除
        data = data[~data.index.duplicated(keep='first')]
        
        # 日付順にソート
        data = data.sort_index()
        
        return data
    
    def _get_from_stooq(self, symbol: str, start_date: str, end_date: str, 
                        interval: str, max_retries: int) -> pd.DataFrame:
        """stooq.comからデータ取得（リトライなし）"""
        try:
                import pandas_datareader.data as web
                
                # 正しいシンボル形式に変換
                if symbol.endswith('.T'):
                    # 日本株の場合: 7203.T -> 7203.JP
                    stooq_symbol = symbol.replace('.T', '.JP')
                else:
                    # 米国株の場合: AAPL -> AAPL.US
                    stooq_symbol = f"{symbol}.US"
                
                # 間隔の変換
                interval_map = {
                    "1d": "d",  # 日足
                    "1wk": "w",  # 週足
                    "1mo": "m",  # 月足
                }
                stooq_interval = interval_map.get(interval, "d")
                
                self.logger.info(f"stooq.comからデータ取得: {symbol} -> {stooq_symbol}")
                
                # データ取得
                data = web.DataReader(
                    stooq_symbol, 
                    data_source='stooq', 
                    start=start_date, 
                    end=end_date
                )
                
                if not data.empty:
                    # カラム名の統一
                    if 'Adj Close' in data.columns:
                        data = data.drop('Adj Close', axis=1)
                    
                    # 日付順にソート
                    data = data.sort_index()
                    
                    self.logger.info(f"stooq.comデータ取得成功: {symbol} - 形状: {data.shape}")
                    return data
                else:
                    self.logger.warning(f"stooq.com データが空: {symbol}")
                    return pd.DataFrame()
                    
        except ImportError:
            self.logger.warning("pandas-datareaderがインストールされていません")
            return pd.DataFrame()
        except Exception as e:
            self.logger.warning(f"stooq.com エラー: {symbol}, {e}")
            return pd.DataFrame()
    
    def get_test_stocks(self) -> List[str]:
        """テスト用銘柄リスト"""
        return ['AAPL', 'MSFT', 'GOOGL']
    
    def get_american_stocks(self) -> List[str]:
        """米国株銘柄リスト"""
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
            'JPM', 'JNJ', 'PG', 'UNH', 'HD', 'MA', 'V', 'PYPL', 'ADBE', 'CRM'
        ]
    
    def get_vix_data(self, start_date: str = "2020-01-01", 
                     end_date: str = "2025-08-31") -> pd.DataFrame:
        """
        VIX（恐怖指数）データを取得（差分取得・キャッシュ対応）
        
        Args:
            start_date: 開始日
            end_date: 終了日
        
        Returns:
            DataFrame: VIXデータ
        """
        cache_file = os.path.join(self.cache_dir, f"VIX_1d_{start_date}_{end_date}.pkl")
        
        # 既存のキャッシュデータを読み込み
        existing_data = pd.DataFrame()
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    existing_data = pickle.load(f)
                if not existing_data.empty:
                    self.logger.info(f"VIXキャッシュデータを読み込み: {existing_data.shape}")
                    return existing_data
            except Exception as e:
                self.logger.warning(f"VIXキャッシュ読み込みエラー: {e}")
        
        # 差分取得を試行
        missing_periods = self._get_missing_periods(existing_data, start_date, end_date)
        if missing_periods:
            self.logger.info(f"VIX差分取得期間: {missing_periods}")
            new_data = self._fetch_vix_data_periods(missing_periods)
            if not new_data.empty:
                # 既存データとマージ
                if not existing_data.empty:
                    merged_data = self._merge_data(existing_data, new_data)
                else:
                    merged_data = new_data
                
                # キャッシュに保存
                try:
                    with open(cache_file, 'wb') as f:
                        pickle.dump(merged_data, f)
                    self.logger.info(f"VIXデータをキャッシュに保存: {cache_file}")
                except Exception as e:
                    self.logger.warning(f"VIXキャッシュ保存エラー: {e}")
                
                return merged_data
        
        # 差分取得ができない場合は新規取得
        try:
            import yfinance as yf
            
            # VIXデータを取得（複数のシンボルを試行）
            vix_symbols = ["^VIX", "VIX", "VIXCLS"]
            vix = pd.DataFrame()
            
            for symbol in vix_symbols:
                try:
                    self.logger.info(f"VIXデータ取得試行: {symbol}")
                    vix = yf.download(symbol, start=start_date, end=end_date, progress=False)
                    if not vix.empty:
                        self.logger.info(f"VIXデータ取得成功: {symbol}")
                        break
                except Exception as e:
                    self.logger.warning(f"VIXデータ取得失敗: {symbol}, {e}")
                    continue
            
            if vix.empty:
                self.logger.warning("すべてのVIXシンボルでデータ取得に失敗しました")
                # VIXデータをシミュレート
                vix = self._simulate_vix_data(start_date, end_date)
            
            # カラム名を統一
            if len(vix.columns) == 6:  # Adj Closeが含まれている場合
                vix.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
                vix = vix.drop('Adj Close', axis=1)
            elif len(vix.columns) == 5:  # Adj Closeが含まれていない場合
                vix.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            
            # 日付順にソート
            vix = vix.sort_index()
            
            # キャッシュに保存
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(vix, f)
                self.logger.info(f"VIXデータをキャッシュに保存: {cache_file}")
            except Exception as e:
                self.logger.warning(f"VIXキャッシュ保存エラー: {e}")
            
            self.logger.info(f"VIXデータ取得成功: 形状 {vix.shape}")
            return vix
            
        except ImportError:
            self.logger.warning("yfinanceがインストールされていません")
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"VIXデータ取得エラー: {e}")
            return pd.DataFrame()
    
    def _fetch_vix_data_periods(self, periods: List[tuple]) -> pd.DataFrame:
        """
        指定期間のVIXデータを取得
        
        Args:
            periods: 取得期間のリスト [(start_date, end_date), ...]
        
        Returns:
            DataFrame: VIXデータ
        """
        all_data = []
        
        for start_date, end_date in periods:
            try:
                import yfinance as yf
                
                # VIXデータを取得（複数のシンボルを試行）
                vix_symbols = ["^VIX", "VIX", "VIXCLS"]
                vix = pd.DataFrame()
                
                for symbol in vix_symbols:
                    try:
                        self.logger.info(f"VIX差分取得試行: {symbol} ({start_date} - {end_date})")
                        vix = yf.download(symbol, start=start_date, end=end_date, progress=False)
                        if not vix.empty:
                            self.logger.info(f"VIX差分取得成功: {symbol}")
                            break
                    except Exception as e:
                        self.logger.warning(f"VIX差分取得失敗: {symbol}, {e}")
                        continue
                
                if not vix.empty:
                    # カラム名を統一
                    if len(vix.columns) == 6:  # Adj Closeが含まれている場合
                        vix.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
                        vix = vix.drop('Adj Close', axis=1)
                    elif len(vix.columns) == 5:  # Adj Closeが含まれていない場合
                        vix.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    
                    all_data.append(vix)
                else:
                    # データが取得できない場合はシミュレート
                    simulated_vix = self._simulate_vix_data(start_date, end_date)
                    if not simulated_vix.empty:
                        all_data.append(simulated_vix)
                    
            except Exception as e:
                self.logger.error(f"VIX差分取得エラー ({start_date} - {end_date}): {e}")
                continue
        
        if all_data:
            # 全データを結合
            combined_data = pd.concat(all_data, axis=0)
            combined_data = combined_data.sort_index()
            combined_data = combined_data[~combined_data.index.duplicated(keep='first')]
            return combined_data
        
        return pd.DataFrame()
    
    def _simulate_vix_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        VIXデータをシミュレート（実際のデータが取得できない場合の代替手段）
        
        Args:
            start_date: 開始日
            end_date: 終了日
        
        Returns:
            DataFrame: シミュレートされたVIXデータ
        """
        try:
            import numpy as np
            
            # 日付範囲を生成
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            
            # 土日を除外（営業日のみ）
            business_days = date_range[date_range.weekday < 5]
            
            # VIX値をシミュレート（現実的な範囲で）
            np.random.seed(42)  # 再現性のため
            
            # ベースラインVIX値（通常は15-25の範囲）
            base_vix = 20
            
            # 期間別のVIXレベル調整
            vix_values = []
            for date in business_days:
                year = date.year
                month = date.month
                
                # 2020年3月-4月（COVID-19）: 高VIX
                if year == 2020 and month in [3, 4]:
                    vix = base_vix + np.random.normal(40, 15)  # 平均60, 標準偏差15
                # 2008年9月-10月（金融危機）: 高VIX
                elif year == 2008 and month in [9, 10]:
                    vix = base_vix + np.random.normal(35, 20)  # 平均55, 標準偏差20
                # 2022年2月-3月（ウクライナ侵攻）: 中程度のVIX
                elif year == 2022 and month in [2, 3]:
                    vix = base_vix + np.random.normal(15, 10)  # 平均35, 標準偏差10
                # 通常期間
                else:
                    vix = base_vix + np.random.normal(0, 8)  # 平均20, 標準偏差8
                
                # VIX値の範囲制限（5-100）
                vix = max(5, min(100, vix))
                vix_values.append(vix)
            
            # DataFrameを作成
            vix_data = pd.DataFrame({
                'Open': vix_values,
                'High': [v + np.random.uniform(0, 5) for v in vix_values],
                'Low': [v - np.random.uniform(0, 5) for v in vix_values],
                'Close': vix_values,
                'Volume': [np.random.randint(1000000, 10000000) for _ in vix_values]
            }, index=business_days)
            
            # High/Lowの調整
            vix_data['High'] = vix_data[['Open', 'High', 'Close']].max(axis=1)
            vix_data['Low'] = vix_data[['Open', 'Low', 'Close']].min(axis=1)
            
            self.logger.info(f"VIXデータをシミュレート: {vix_data.shape}")
            return vix_data
            
        except Exception as e:
            self.logger.error(f"VIXシミュレーションエラー: {e}")
            return pd.DataFrame()
    
    def load_index_stocks_from_csv(self, csv_file: str = "index_stocks.csv") -> pd.DataFrame:
        """
        指数別銘柄リストをCSVファイルから読み込み
        
        Args:
            csv_file: CSVファイルパス
        
        Returns:
            DataFrame: 指数別銘柄情報
        """
        try:
            if not os.path.exists(csv_file):
                self.logger.warning(f"指数銘柄CSVファイルが見つかりません: {csv_file}")
                # デフォルトの銘柄リストを返す
                default_stocks = pd.DataFrame({
                    'symbol': ['AAPL', 'MSFT', 'GOOGL', '7203.T', '6758.T', '9984.T'],
                    'name': ['Apple Inc.', 'Microsoft Corporation', 'Alphabet Inc.', 
                            'トヨタ自動車株式会社', 'ソニーグループ株式会社', 'ソフトバンクグループ株式会社'],
                    'index': ['SP500', 'SP500', 'SP500', 'NIKKEI225', 'NIKKEI225', 'NIKKEI225'],
                    'category': ['high', 'high', 'high', 'high', 'high', 'high'],
                    'country': ['US', 'US', 'US', 'JP', 'JP', 'JP'],
                    'description': ['テクノロジー大手', 'ソフトウェア大手', 'インターネット大手', 
                                   '自動車大手', 'エンターテイメント大手', '通信大手']
                })
                return default_stocks
            
            stocks_df = pd.read_csv(csv_file, encoding='utf-8')
            self.logger.info(f"指数銘柄CSVファイルから読み込み: {len(stocks_df)}銘柄")
            return stocks_df
            
        except Exception as e:
            self.logger.error(f"指数銘柄CSVファイル読み込みエラー: {e}")
            # エラー時はデフォルトの銘柄リストを返す
            return self.load_index_stocks_from_csv("index_stocks.csv")
    
    def get_stocks_by_index(self, index_name: str) -> List[str]:
        """
        指定された指数の銘柄リストを取得
        
        Args:
            index_name: 指数名（SP500, NASDAQ100, NIKKEI225）
        
        Returns:
            List[str]: 銘柄シンボルリスト
        """
        stocks_df = self.load_index_stocks_from_csv()
        index_stocks = stocks_df[stocks_df['index'] == index_name]
        symbols = index_stocks['symbol'].tolist()
        self.logger.info(f"指数銘柄リスト取得: {index_name}, 銘柄数={len(symbols)}")
        return symbols
    
    def get_all_indices(self) -> List[str]:
        """利用可能な指数リストを取得"""
        stocks_df = self.load_index_stocks_from_csv()
        indices = stocks_df['index'].unique().tolist()
        self.logger.info(f"利用可能な指数: {indices}")
        return indices
    
    def get_index_summary(self) -> Dict[str, int]:
        """各指数の銘柄数を取得"""
        stocks_df = self.load_index_stocks_from_csv()
        index_counts = stocks_df['index'].value_counts().to_dict()
        self.logger.info(f"指数別銘柄数: {index_counts}")
        return index_counts
    
    def random_sample_stocks(self, index_name: str, sample_size: int, 
                           random_seed: int = None) -> List[str]:
        """
        指定された指数からランダムに銘柄を抽出
        
        Args:
            index_name: 指数名
            sample_size: 抽出する銘柄数
            random_seed: 乱数シード（再現性のため）
        
        Returns:
            List[str]: 抽出された銘柄シンボルリスト
        """
        import random
        
        if random_seed is not None:
            random.seed(random_seed)
        
        all_stocks = self.get_stocks_by_index(index_name)
        
        if len(all_stocks) < sample_size:
            self.logger.warning(f"指数 {index_name} の銘柄数({len(all_stocks)})が要求数({sample_size})より少ないため、全銘柄を使用")
            return all_stocks
        
        sampled_stocks = random.sample(all_stocks, sample_size)
        self.logger.info(f"指数 {index_name} から {sample_size} 銘柄をランダム抽出: {sampled_stocks}")
        return sampled_stocks
    
    def get_strategy_stocks(self, strategy: str, random_seed: int = None) -> List[str]:
        """
        戦略に応じた銘柄リストを取得（ランダム抽出）
        
        Args:
            strategy: 戦略名（swing_trading, long_term）
            random_seed: 乱数シード
        
        Returns:
            List[str]: 戦略用銘柄リスト
        """
        indices = ["SP500", "NASDAQ100", "NIKKEI225"]  # TOPIX500を除外
        all_stocks = []
        
        # ローカルテストモードの場合は銘柄数を削減
        if hasattr(self, 'local_test_mode') and self.local_test_mode:
            if strategy == "swing_trading":
                # スイングトレード: 各指数から10銘柄ずつ（合計30銘柄）
                stocks_per_index = [10, 10, 10]  # SP500, NASDAQ100, NIKKEI225
                for i, index_name in enumerate(indices):
                    stocks = self.random_sample_stocks(index_name, stocks_per_index[i], random_seed)
                    all_stocks.extend(stocks)
                self.logger.info(f"スイングトレード用銘柄（ローカルテスト）: {len(all_stocks)}銘柄")
                
            elif strategy == "long_term":
                # 中長期投資: 各指数から10銘柄ずつ（合計30銘柄）
                stocks_per_index = [10, 10, 10]  # SP500, NASDAQ100, NIKKEI225
                for i, index_name in enumerate(indices):
                    stocks = self.random_sample_stocks(index_name, stocks_per_index[i], random_seed)
                    all_stocks.extend(stocks)
                self.logger.info(f"中長期投資用銘柄（ローカルテスト）: {len(all_stocks)}銘柄")
        else:
            if strategy == "swing_trading":
                # スイングトレード: 各指数から33-34銘柄ずつ（合計100銘柄）
                stocks_per_index = [34, 33, 33]  # SP500, NASDAQ100, NIKKEI225
                for i, index_name in enumerate(indices):
                    stocks = self.random_sample_stocks(index_name, stocks_per_index[i], random_seed)
                    all_stocks.extend(stocks)
                self.logger.info(f"スイングトレード用銘柄: {len(all_stocks)}銘柄")
                
            elif strategy == "long_term":
                # 中長期投資: 各指数から適切な数ずつ（合計200銘柄）
                # SP500: 74銘柄, NASDAQ100: 52銘柄(全銘柄), NIKKEI225: 74銘柄
                stocks_per_index = [74, 52, 74]  # SP500, NASDAQ100, NIKKEI225
                for i, index_name in enumerate(indices):
                    stocks = self.random_sample_stocks(index_name, stocks_per_index[i], random_seed)
                    all_stocks.extend(stocks)
                self.logger.info(f"中長期投資用銘柄: {len(all_stocks)}銘柄")
        
        if not all_stocks:
            self.logger.error(f"未対応の戦略: {strategy}")
            return []
        
        return all_stocks
    
    def get_all_index_stocks(self) -> List[str]:
        """
        全指数の全銘柄を取得
        
        Returns:
            List[str]: 全銘柄リスト（SP500 + NASDAQ100 + NIKKEI225）
        """
        indices = ["SP500", "NASDAQ100", "NIKKEI225"]
        all_stocks = []
        
        for index_name in indices:
            stocks = self.get_stocks_by_index(index_name)
            all_stocks.extend(stocks)
            self.logger.info(f"指数 {index_name} から {len(stocks)} 銘柄を取得")
        
        self.logger.info(f"全指数の全銘柄取得完了: {len(all_stocks)}銘柄")
        return all_stocks
    
    def get_fetch_metadata(self) -> Dict:
        """
        データ取得のメタデータを取得
        
        Returns:
            Dict: メタデータ（前回取得期間、取得日時など）
        """
        metadata_file = os.path.join(self.cache_dir, "fetch_metadata.json")
        
        if os.path.exists(metadata_file):
            try:
                import json
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                return metadata
            except Exception as e:
                self.logger.warning(f"メタデータ読み込みエラー: {e}")
        
        return {}
    
    def save_fetch_metadata(self, start_date: str, end_date: str, fetch_count: int = 0):
        """
        データ取得のメタデータを保存
        
        Args:
            start_date: 取得開始日
            end_date: 取得終了日
            fetch_count: 取得銘柄数
        """
        import json
        from datetime import datetime
        
        metadata = {
            "last_fetch_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "last_fetch_time": datetime.now().isoformat(),
            "last_fetch_count": fetch_count
        }
        
        metadata_file = os.path.join(self.cache_dir, "fetch_metadata.json")
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            self.logger.info(f"メタデータ保存完了: {start_date} ～ {end_date}")
        except Exception as e:
            self.logger.error(f"メタデータ保存エラー: {e}")
    
    def should_fetch_differential_data(self, current_start_date: str, current_end_date: str) -> bool:
        """
        差分データ取得が必要かどうかを判定
        
        Args:
            current_start_date: 現在の要求開始日
            current_end_date: 現在の要求終了日
        
        Returns:
            bool: 差分取得が必要かどうか
        """
        metadata = self.get_fetch_metadata()
        
        if not metadata or "last_fetch_period" not in metadata:
            self.logger.info("前回の取得期間データなし - 全データ取得が必要")
            return True
        
        last_period = metadata["last_fetch_period"]
        last_start = last_period.get("start_date", "")
        last_end = last_period.get("end_date", "")
        
        # 期間が異なる場合は差分取得が必要
        if last_start != current_start_date or last_end != current_end_date:
            self.logger.info(f"期間変更検出 - 差分取得が必要")
            self.logger.info(f"前回期間: {last_start} ～ {last_end}")
            self.logger.info(f"現在期間: {current_start_date} ～ {current_end_date}")
            return True
        
        self.logger.info("期間変更なし - 差分取得不要")
        return False

    def get_stock_data_batch(self, symbols: List[str], start_date: str = "2020-01-01", 
                            end_date: str = "2025-08-31", interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        複数銘柄のデータを並列で取得
        
        Args:
            symbols: 銘柄コードリスト
            start_date: 開始日
            end_date: 終了日
            interval: 時間間隔
        
        Returns:
            Dict: 銘柄コードをキーとしたデータ辞書
        """
        self.logger.info(f"並列データ取得開始: {len(symbols)}銘柄")
        start_time = time.time()
        
        # 並列処理でデータ取得
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 部分関数を作成（引数を固定）
            get_data_func = partial(
                self.get_stock_data, 
                start_date=start_date, 
                end_date=end_date, 
                interval=interval
            )
            
            # 並列実行
            future_to_symbol = {executor.submit(get_data_func, symbol): symbol for symbol in symbols}
            
            results = {}
            completed = 0
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                completed += 1
                
                try:
                    data = future.result()
                    results[symbol] = data
                    
                    # 進捗表示
                    if completed % 10 == 0 or completed == len(symbols):
                        self.logger.info(f"データ取得進捗: {completed}/{len(symbols)} 完了")
                        
                except Exception as e:
                    self.logger.error(f"データ取得エラー: {symbol}, {e}")
                    results[symbol] = pd.DataFrame()
        
        elapsed_time = time.time() - start_time
        self.logger.info(f"並列データ取得完了: {len(symbols)}銘柄, 所要時間: {elapsed_time:.2f}秒")
        
        return results
    
    def get_stock_data_batch_force(self, symbols: List[str], start_date: str = "2020-01-01", 
                                   end_date: str = "2025-08-31", interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        複数銘柄のデータを並列で取得（完全取得モード）
        不完全データと未取得銘柄のみを取得
        
        Args:
            symbols: 銘柄コードリスト
            start_date: 開始日
            end_date: 終了日
            interval: 時間間隔
        
        Returns:
            Dict: 銘柄コードをキーとしたデータ辞書
        """
        self.logger.info(f"完全取得モードで並列データ取得開始: {len(symbols)}銘柄")
        start_time = time.time()
        
        # 取得対象銘柄をフィルタリング
        target_symbols = []
        for symbol in symbols:
            cache_file = os.path.join(self.cache_dir, f"{symbol}_{interval}_{start_date}_{end_date}.pkl")
            
            if not os.path.exists(cache_file):
                # キャッシュファイルが存在しない場合
                target_symbols.append(symbol)
                self.logger.info(f"未取得銘柄を追加: {symbol}")
            else:
                # キャッシュファイルが存在する場合、データの完全性をチェック
                try:
                    with open(cache_file, 'rb') as f:
                        existing_data = pickle.load(f)
                    
                    if existing_data.empty:
                        # 空のデータの場合
                        target_symbols.append(symbol)
                        self.logger.info(f"空データ銘柄を追加: {symbol}")
                    else:
                        # データの完全性をチェック
                        missing_periods = self._get_missing_periods(existing_data, start_date, end_date)
                        if missing_periods:
                            # 不完全データの場合
                            target_symbols.append(symbol)
                            self.logger.info(f"不完全データ銘柄を追加: {symbol} (不足期間: {len(missing_periods)}個)")
                        else:
                            # 完全なデータの場合
                            self.logger.info(f"完全データ銘柄をスキップ: {symbol}")
                            
                except Exception as e:
                    # キャッシュファイルの読み込みエラーの場合
                    target_symbols.append(symbol)
                    self.logger.warning(f"キャッシュ読み込みエラー銘柄を追加: {symbol}, {e}")
        
        if not target_symbols:
            self.logger.info("取得対象の銘柄がありません（すべて完全なデータが存在）")
            return {}
        
        self.logger.info(f"取得対象銘柄数: {len(target_symbols)}/{len(symbols)}")
        
        # 並列処理でデータ取得
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 部分関数を作成（引数を固定）
            get_data_func = partial(
                self.get_stock_data, 
                start_date=start_date, 
                end_date=end_date, 
                interval=interval
            )
            
            # 並列実行
            future_to_symbol = {executor.submit(get_data_func, symbol): symbol for symbol in target_symbols}
            
            results = {}
            completed = 0
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                completed += 1
                
                try:
                    data = future.result()
                    results[symbol] = data
                    
                    # 進捗表示
                    if completed % 10 == 0 or completed == len(target_symbols):
                        self.logger.info(f"データ取得進捗: {completed}/{len(target_symbols)} 完了")
                        
                except Exception as e:
                    self.logger.error(f"データ取得エラー: {symbol}, {e}")
                    results[symbol] = pd.DataFrame()
        
        elapsed_time = time.time() - start_time
        self.logger.info(f"完全取得モード並列データ取得完了: {len(results)}銘柄, 所要時間: {elapsed_time:.2f}秒")
        
        return results
