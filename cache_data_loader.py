"""
キャッシュ専用データローダーモジュール
既存のキャッシュファイルからのみデータを読み込む（書き込みなし）
"""

import os
import pandas as pd
import pickle
import logging
from typing import List, Optional, Dict

class CacheOnlyDataLoader:
    """キャッシュ専用データローダークラス"""
    
    def __init__(self, cache_dir: str = "cache"):
        """
        初期化
        
        Args:
            cache_dir: キャッシュディレクトリ
        """
        self.cache_dir = cache_dir
        self.logger = logging.getLogger(__name__)
        
        # キャッシュディレクトリの存在確認
        if not os.path.exists(cache_dir):
            raise FileNotFoundError(f"キャッシュディレクトリが見つかりません: {cache_dir}")
    
    def get_stock_data_from_cache(self, symbol: str, start_date: str, 
                                 end_date: str, interval: str = "1d") -> pd.DataFrame:
        """
        キャッシュからのみデータを取得（書き込みなし）
        マスタデータから要求された期間をスライスして返す
        
        Args:
            symbol: 銘柄コード
            start_date: 開始日
            end_date: 終了日
            interval: 時間間隔
        
        Returns:
            DataFrame: 株価データ
        
        Raises:
            FileNotFoundError: キャッシュファイルが見つからない場合
        """
        # マスタデータファイルを検索（最も広い期間のファイル）
        all_cache_files = [f for f in os.listdir(self.cache_dir) 
                          if f.startswith(f"{symbol}_{interval}_") and f.endswith(".pkl")]
        
        if not all_cache_files:
            raise FileNotFoundError(f"キャッシュファイルが見つかりません: {symbol} (銘柄コード: {symbol})")
        
        # 最も広い期間のファイル（マスタデータ）を選択
        master_file = None
        master_start = None
        master_end = None
        
        for cache_file_name in all_cache_files:
            try:
                # ファイル名から期間を抽出
                parts = cache_file_name.replace(f"{symbol}_{interval}_", "").replace(".pkl", "").split("_")
                if len(parts) >= 2:
                    file_start = parts[0]
                    file_end = parts[1]
                    
                    # 最も広い期間のファイルを選択
                    if (master_start is None or file_start <= master_start) and \
                       (master_end is None or file_end >= master_end):
                        master_file = cache_file_name
                        master_start = file_start
                        master_end = file_end
                        
            except Exception as e:
                self.logger.warning(f"ファイル名解析エラー: {cache_file_name}, {e}")
                continue
        
        if not master_file:
            raise FileNotFoundError(f"有効なキャッシュファイルが見つかりません: {symbol} (銘柄コード: {symbol})")
        
        # マスタデータファイルからデータを読み込み
        master_cache_file = os.path.join(self.cache_dir, master_file)
        self.logger.info(f"マスタデータファイルを使用: {master_file}")
        
        try:
            with open(master_cache_file, 'rb') as f:
                master_data = pickle.load(f)
            
            if master_data.empty:
                raise ValueError(f"マスタデータファイルが空です: {master_cache_file}")
            
            self.logger.info(f"マスタデータ読み込み: {symbol} ({len(master_data)}行, {master_start} ～ {master_end})")
            
            # 要求された期間にスライス
            try:
                sliced_data = master_data.loc[start_date:end_date]
                if sliced_data.empty:
                    self.logger.warning(f"スライス後のデータが空です: {symbol} ({start_date} ～ {end_date})")
                    # 空のDataFrameでも返す（エラーにしない）
                    return sliced_data
                
                self.logger.info(f"期間スライス完了: {symbol} ({len(sliced_data)}行, {start_date} ～ {end_date})")
                return sliced_data
                
            except Exception as e:
                self.logger.warning(f"期間スライスエラー: {symbol}, {e}")
                self.logger.info(f"マスタデータをそのまま返します: {symbol} ({len(master_data)}行)")
                return master_data
                
        except Exception as e:
            if "numpy._core" in str(e):
                self.logger.error(f"numpy._coreエラー: {symbol}, キャッシュファイルが古いnumpyバージョンで作成されています")
                # 空のDataFrameを返して処理を継続
                return pd.DataFrame()
            else:
                self.logger.error(f"マスタデータ読み込みエラー: {symbol}, {e}")
                raise
    
    def get_stock_data_batch_from_cache(self, symbols: List[str], 
                                       start_date: str, end_date: str, 
                                       interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        複数銘柄のデータをキャッシュから一括取得
        
        Args:
            symbols: 銘柄コードリスト
            start_date: 開始日
            end_date: 終了日
            interval: 時間間隔
        
        Returns:
            Dict: 銘柄コードをキーとしたデータ辞書
        """
        all_data = {}
        missing_symbols = []
        
        for symbol in symbols:
            try:
                data = self.get_stock_data_from_cache(symbol, start_date, end_date, interval)
                all_data[symbol] = data
            except (FileNotFoundError, ValueError) as e:
                missing_symbols.append(symbol)
                self.logger.warning(f"銘柄データ取得失敗: {symbol}, {e}")
        
        if missing_symbols:
            self.logger.warning(f"取得できなかった銘柄: {missing_symbols}")
        
        self.logger.info(f"キャッシュからデータ取得完了: {len(all_data)}/{len(symbols)}銘柄")
        return all_data
    
    def get_vix_data_from_cache(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        VIXデータをキャッシュから取得
        マスタデータから要求された期間をスライスして返す
        
        Args:
            start_date: 開始日
            end_date: 終了日
        
        Returns:
            DataFrame: VIXデータ
        """
        # VIXマスタデータファイルを検索（最も広い期間のファイル）
        vix_cache_files = [f for f in os.listdir(self.cache_dir) 
                          if f.startswith("VIX_1d_") and f.endswith(".pkl")]
        
        if not vix_cache_files:
            self.logger.warning(f"VIXキャッシュファイルが見つかりません")
            return pd.DataFrame()
        
        # 最も広い期間のファイル（マスタデータ）を選択
        master_file = None
        master_start = None
        master_end = None
        
        for cache_file_name in vix_cache_files:
            try:
                # ファイル名から期間を抽出
                parts = cache_file_name.replace("VIX_1d_", "").replace(".pkl", "").split("_")
                if len(parts) >= 2:
                    file_start = parts[0]
                    file_end = parts[1]
                    
                    # 最も広い期間のファイルを選択
                    if (master_start is None or file_start <= master_start) and \
                       (master_end is None or file_end >= master_end):
                        master_file = cache_file_name
                        master_start = file_start
                        master_end = file_end
                        
            except Exception as e:
                self.logger.warning(f"VIXファイル名解析エラー: {cache_file_name}, {e}")
                continue
        
        if not master_file:
            self.logger.warning(f"有効なVIXキャッシュファイルが見つかりません")
            return pd.DataFrame()
        
        # VIXマスタデータファイルからデータを読み込み
        master_cache_file = os.path.join(self.cache_dir, master_file)
        self.logger.info(f"VIXマスタデータファイルを使用: {master_file}")
        
        try:
            with open(master_cache_file, 'rb') as f:
                master_data = pickle.load(f)
            
            if master_data.empty:
                self.logger.warning(f"VIXマスタデータファイルが空です: {master_cache_file}")
                return pd.DataFrame()
            
            self.logger.info(f"VIXマスタデータ読み込み: {len(master_data)}行, {master_start} ～ {master_end}")
            
            # 要求された期間にスライス
            try:
                sliced_data = master_data.loc[start_date:end_date]
                if sliced_data.empty:
                    self.logger.warning(f"VIXスライス後のデータが空です: {start_date} ～ {end_date}")
                    # 空のDataFrameでも返す（エラーにしない）
                    return sliced_data
                
                self.logger.info(f"VIX期間スライス完了: {len(sliced_data)}行, {start_date} ～ {end_date}")
                return sliced_data
                
            except Exception as e:
                self.logger.warning(f"VIX期間スライスエラー: {e}")
                self.logger.info(f"VIXマスタデータをそのまま返します: {len(master_data)}行")
                return master_data
                
        except Exception as e:
            if "numpy._core" in str(e):
                self.logger.error(f"VIX numpy._coreエラー: キャッシュファイルが古いnumpyバージョンで作成されています")
                # 空のDataFrameを返して処理を継続
                return pd.DataFrame()
            else:
                self.logger.error(f"VIXマスタデータ読み込みエラー: {e}")
                return pd.DataFrame()
    
    def validate_cache_completeness(self, symbols: List[str], 
                                   start_date: str, end_date: str, 
                                   interval: str = "1d") -> Dict[str, bool]:
        """
        キャッシュの完全性を検証
        
        Args:
            symbols: 銘柄コードリスト
            start_date: 開始日
            end_date: 終了日
            interval: 時間間隔
        
        Returns:
            Dict: 銘柄コードをキーとした完全性フラグ
        """
        completeness = {}
        
        for symbol in symbols:
            cache_file = os.path.join(self.cache_dir, 
                                     f"{symbol}_{interval}_{start_date}_{end_date}.pkl")
            
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                    completeness[symbol] = not data.empty
                except:
                    completeness[symbol] = False
            else:
                completeness[symbol] = False
        
        complete_count = sum(completeness.values())
        self.logger.info(f"キャッシュ完全性: {complete_count}/{len(symbols)}銘柄")
        
        return completeness
    
    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        データのクリーニング（元のDataLoaderと同じ処理）
        
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
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        データの妥当性を検証（元のDataLoaderと同じ処理）
        
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
