"""
自動銘柄取得モジュール
S&P500、NASDAQ100、日経225の銘柄を自動取得
"""

import requests
import pandas as pd
import time
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re

class StockFetcher:
    """自動銘柄取得クラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def fetch_sp500_stocks(self) -> List[Dict[str, str]]:
        """
        S&P500銘柄を取得
        
        Returns:
            List[Dict]: 銘柄情報のリスト
        """
        self.logger.info("S&P500銘柄の取得を開始")
        
        try:
            # WikipediaからS&P500銘柄を取得
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'class': 'wikitable'})
            
            if not table:
                self.logger.error("S&P500銘柄テーブルが見つかりません")
                return []
            
            stocks = []
            rows = table.find_all('tr')[1:]  # ヘッダーを除外
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    symbol = cells[0].get_text(strip=True)
                    name = cells[1].get_text(strip=True)
                    
                    # 基本的な銘柄情報
                    stock_info = {
                        'symbol': symbol,
                        'name': name,
                        'index': 'SP500',
                        'category': 'high',
                        'country': 'US',
                        'description': f'{name} (S&P500)'
                    }
                    stocks.append(stock_info)
            
            self.logger.info(f"S&P500銘柄取得完了: {len(stocks)}銘柄")
            return stocks
            
        except Exception as e:
            self.logger.error(f"S&P500銘柄取得エラー: {e}")
            return []
    
    def fetch_nasdaq100_stocks(self) -> List[Dict[str, str]]:
        """
        NASDAQ100銘柄を取得
        
        Returns:
            List[Dict]: 銘柄情報のリスト
        """
        self.logger.info("NASDAQ100銘柄の取得を開始")
        
        try:
            # WikipediaからNASDAQ100銘柄を取得
            url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # NASDAQ100銘柄テーブルを探す（複数の方法で試行）
            target_table = None
            
            # 方法1: クラス名で検索
            tables = soup.find_all('table', {'class': 'wikitable'})
            for table in tables:
                if 'Symbol' in table.get_text() and 'Company' in table.get_text():
                    target_table = table
                    break
            
            # 方法2: より柔軟な検索
            if not target_table:
                for table in soup.find_all('table'):
                    text = table.get_text()
                    if ('Symbol' in text or 'Ticker' in text) and ('Company' in text or 'Name' in text):
                        target_table = table
                        break
            
            # 方法3: 特定のテキストを含むテーブルを検索
            if not target_table:
                for table in soup.find_all('table'):
                    if 'AAPL' in table.get_text() or 'MSFT' in table.get_text():
                        target_table = table
                        break
            
            if not target_table:
                self.logger.error("NASDAQ100銘柄テーブルが見つかりません")
                # フォールバック: 主要なNASDAQ100銘柄を手動で提供
                return self._get_fallback_nasdaq100_stocks()
            
            stocks = []
            rows = target_table.find_all('tr')[1:]  # ヘッダーを除外
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    symbol = cells[0].get_text(strip=True)
                    name = cells[1].get_text(strip=True)
                    
                    # 基本的な銘柄情報
                    stock_info = {
                        'symbol': symbol,
                        'name': name,
                        'index': 'NASDAQ100',
                        'category': 'high',
                        'country': 'US',
                        'description': f'{name} (NASDAQ100)'
                    }
                    stocks.append(stock_info)
            
            self.logger.info(f"NASDAQ100銘柄取得完了: {len(stocks)}銘柄")
            return stocks
            
        except Exception as e:
            self.logger.error(f"NASDAQ100銘柄取得エラー: {e}")
            return self._get_fallback_nasdaq100_stocks()
    
    def fetch_nikkei225_stocks(self) -> List[Dict[str, str]]:
        """
        日経225銘柄を取得
        
        Returns:
            List[Dict]: 銘柄情報のリスト
        """
        self.logger.info("日経225銘柄の取得を開始")
        
        try:
            # Wikipediaから日経225銘柄を取得
            url = "https://en.wikipedia.org/wiki/Nikkei_225"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 日経225銘柄テーブルを探す（複数の方法で試行）
            target_table = None
            
            # 方法1: クラス名で検索
            tables = soup.find_all('table', {'class': 'wikitable'})
            for table in tables:
                if 'Code' in table.get_text() and 'Name' in table.get_text():
                    target_table = table
                    break
            
            # 方法2: より柔軟な検索
            if not target_table:
                for table in soup.find_all('table'):
                    text = table.get_text()
                    if ('Code' in text or 'Symbol' in text) and ('Name' in text or 'Company' in text):
                        target_table = table
                        break
            
            # 方法3: 特定のテキストを含むテーブルを検索
            if not target_table:
                for table in soup.find_all('table'):
                    if '7203' in table.get_text() or '6758' in table.get_text():
                        target_table = table
                        break
            
            if not target_table:
                self.logger.error("日経225銘柄テーブルが見つかりません")
                # フォールバック: 主要な日経225銘柄を手動で提供
                return self._get_fallback_nikkei225_stocks()
            
            stocks = []
            rows = target_table.find_all('tr')[1:]  # ヘッダーを除外
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    code = cells[0].get_text(strip=True)
                    name = cells[1].get_text(strip=True)
                    
                    # 銘柄コードを正規化（.Tを追加）
                    if not code.endswith('.T'):
                        code = f"{code}.T"
                    
                    # 基本的な銘柄情報
                    stock_info = {
                        'symbol': code,
                        'name': name,
                        'index': 'NIKKEI225',
                        'category': 'high',
                        'country': 'JP',
                        'description': f'{name} (日経225)'
                    }
                    stocks.append(stock_info)
            
            self.logger.info(f"日経225銘柄取得完了: {len(stocks)}銘柄")
            return stocks
            
        except Exception as e:
            self.logger.error(f"日経225銘柄取得エラー: {e}")
            return self._get_fallback_nikkei225_stocks()
    
    def fetch_all_stocks(self) -> Dict[str, List[Dict[str, str]]]:
        """
        全指数の銘柄を取得
        
        Returns:
            Dict: 指数別銘柄情報
        """
        self.logger.info("全指数の銘柄取得を開始")
        
        all_stocks = {}
        
        # S&P500銘柄取得
        sp500_stocks = self.fetch_sp500_stocks()
        if sp500_stocks:
            all_stocks['SP500'] = sp500_stocks
            time.sleep(2)  # レート制限対策
        
        # NASDAQ100銘柄取得
        nasdaq100_stocks = self.fetch_nasdaq100_stocks()
        if nasdaq100_stocks:
            all_stocks['NASDAQ100'] = nasdaq100_stocks
            time.sleep(2)  # レート制限対策
        
        # 日経225銘柄取得
        nikkei225_stocks = self.fetch_nikkei225_stocks()
        if nikkei225_stocks:
            all_stocks['NIKKEI225'] = nikkei225_stocks
        
        # 統計情報
        total_stocks = sum(len(stocks) for stocks in all_stocks.values())
        self.logger.info(f"全指数銘柄取得完了: 合計{total_stocks}銘柄")
        
        for index_name, stocks in all_stocks.items():
            self.logger.info(f"{index_name}: {len(stocks)}銘柄")
        
        return all_stocks
    
    def save_stocks_to_csv(self, stocks_dict: Dict[str, List[Dict[str, str]]], 
                          filename: str = "index_stocks_auto.csv") -> str:
        """
        取得した銘柄をCSVファイルに保存
        
        Args:
            stocks_dict: 指数別銘柄情報
            filename: 保存ファイル名
        
        Returns:
            str: 保存されたファイルパス
        """
        try:
            # 全銘柄を1つのリストに結合
            all_stocks = []
            for index_name, stocks in stocks_dict.items():
                all_stocks.extend(stocks)
            
            # DataFrameに変換
            df = pd.DataFrame(all_stocks)
            
            # CSVファイルに保存
            df.to_csv(filename, index=False, encoding='utf-8')
            
            self.logger.info(f"銘柄情報を保存: {filename}")
            self.logger.info(f"保存銘柄数: {len(all_stocks)}銘柄")
            
            return filename
            
        except Exception as e:
            self.logger.error(f"CSV保存エラー: {e}")
            return ""
    
    def merge_with_existing_stocks(self, new_stocks_dict: Dict[str, List[Dict[str, str]]], 
                                  existing_file: str = "index_stocks.csv") -> str:
        """
        既存の銘柄リストと新しい銘柄リストをマージ
        
        Args:
            new_stocks_dict: 新しく取得した銘柄情報
            existing_file: 既存のCSVファイル
        
        Returns:
            str: マージされたファイルパス
        """
        try:
            # 既存の銘柄リストを読み込み
            existing_stocks = []
            if pd.io.common.file_exists(existing_file):
                existing_df = pd.read_csv(existing_file, encoding='utf-8')
                existing_stocks = existing_df.to_dict('records')
                self.logger.info(f"既存銘柄読み込み: {len(existing_stocks)}銘柄")
            
            # 新しい銘柄リストを結合
            new_stocks = []
            for index_name, stocks in new_stocks_dict.items():
                new_stocks.extend(stocks)
            
            # 重複を除去（symbolで判定）
            existing_symbols = {stock['symbol'] for stock in existing_stocks}
            unique_new_stocks = [stock for stock in new_stocks if stock['symbol'] not in existing_symbols]
            
            # マージ
            merged_stocks = existing_stocks + unique_new_stocks
            
            # DataFrameに変換して保存
            merged_df = pd.DataFrame(merged_stocks)
            merged_filename = "index_stocks_merged.csv"
            merged_df.to_csv(merged_filename, index=False, encoding='utf-8')
            
            self.logger.info(f"銘柄リストマージ完了: {merged_filename}")
            self.logger.info(f"既存銘柄: {len(existing_stocks)}銘柄")
            self.logger.info(f"新規銘柄: {len(unique_new_stocks)}銘柄")
            self.logger.info(f"合計銘柄: {len(merged_stocks)}銘柄")
            
            return merged_filename
            
        except Exception as e:
            self.logger.error(f"銘柄リストマージエラー: {e}")
            return ""
    
    def validate_stock_symbols(self, stocks_dict: Dict[str, List[Dict[str, str]]]) -> Dict[str, List[Dict[str, str]]]:
        """
        銘柄シンボルの妥当性をチェック
        
        Args:
            stocks_dict: 指数別銘柄情報
        
        Returns:
            Dict: 妥当性チェック済みの銘柄情報
        """
        self.logger.info("銘柄シンボルの妥当性チェックを開始")
        
        validated_stocks = {}
        
        for index_name, stocks in stocks_dict.items():
            valid_stocks = []
            
            for stock in stocks:
                symbol = stock['symbol']
                
                # 基本的な妥当性チェック
                if self._is_valid_symbol(symbol, index_name):
                    valid_stocks.append(stock)
                else:
                    self.logger.warning(f"無効なシンボルを除外: {symbol} ({index_name})")
            
            validated_stocks[index_name] = valid_stocks
            self.logger.info(f"{index_name}: {len(valid_stocks)}/{len(stocks)}銘柄が有効")
        
        return validated_stocks
    
    def _is_valid_symbol(self, symbol: str, index_name: str) -> bool:
        """
        銘柄シンボルの妥当性をチェック
        
        Args:
            symbol: 銘柄シンボル
            index_name: 指数名
        
        Returns:
            bool: 妥当性
        """
        if not symbol or len(symbol) < 1:
            return False
        
        # 米国株のチェック
        if index_name in ['SP500', 'NASDAQ100']:
            # 英数字のみ、1-5文字
            if not re.match(r'^[A-Z]{1,5}$', symbol):
                return False
        
        # 日本株のチェック
        elif index_name == 'NIKKEI225':
            # 数字.T形式
            if not re.match(r'^\d{4}\.T$', symbol):
                return False
        
        return True
    
    def _get_fallback_nasdaq100_stocks(self) -> List[Dict[str, str]]:
        """NASDAQ100銘柄のフォールバックリスト"""
        fallback_stocks = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Apple Inc. (NASDAQ100)'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Microsoft Corporation (NASDAQ100)'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Alphabet Inc. (NASDAQ100)'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Amazon.com Inc. (NASDAQ100)'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Tesla Inc. (NASDAQ100)'},
            {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Meta Platforms Inc. (NASDAQ100)'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'NVIDIA Corporation (NASDAQ100)'},
            {'symbol': 'NFLX', 'name': 'Netflix Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Netflix Inc. (NASDAQ100)'},
            {'symbol': 'ADBE', 'name': 'Adobe Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Adobe Inc. (NASDAQ100)'},
            {'symbol': 'CRM', 'name': 'Salesforce Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Salesforce Inc. (NASDAQ100)'},
            {'symbol': 'PYPL', 'name': 'PayPal Holdings Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'PayPal Holdings Inc. (NASDAQ100)'},
            {'symbol': 'INTC', 'name': 'Intel Corporation', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Intel Corporation (NASDAQ100)'},
            {'symbol': 'AMD', 'name': 'Advanced Micro Devices', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Advanced Micro Devices (NASDAQ100)'},
            {'symbol': 'CSCO', 'name': 'Cisco Systems Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Cisco Systems Inc. (NASDAQ100)'},
            {'symbol': 'ORCL', 'name': 'Oracle Corporation', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Oracle Corporation (NASDAQ100)'},
            {'symbol': 'ZM', 'name': 'Zoom Video Communications', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Zoom Video Communications (NASDAQ100)'},
            {'symbol': 'UBER', 'name': 'Uber Technologies Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Uber Technologies Inc. (NASDAQ100)'},
            {'symbol': 'LYFT', 'name': 'Lyft Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Lyft Inc. (NASDAQ100)'},
            {'symbol': 'TEAM', 'name': 'Atlassian Corporation', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Atlassian Corporation (NASDAQ100)'},
            {'symbol': 'SPLK', 'name': 'Splunk Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Splunk Inc. (NASDAQ100)'},
            {'symbol': 'OKTA', 'name': 'Okta Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Okta Inc. (NASDAQ100)'},
            {'symbol': 'CRWD', 'name': 'CrowdStrike Holdings', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'CrowdStrike Holdings (NASDAQ100)'},
            {'symbol': 'ZS', 'name': 'Zscaler Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Zscaler Inc. (NASDAQ100)'},
            {'symbol': 'PANW', 'name': 'Palo Alto Networks', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Palo Alto Networks (NASDAQ100)'},
            {'symbol': 'FTNT', 'name': 'Fortinet Inc.', 'index': 'NASDAQ100', 'category': 'high', 'country': 'US', 'description': 'Fortinet Inc. (NASDAQ100)'}
        ]
        self.logger.info(f"NASDAQ100フォールバック銘柄: {len(fallback_stocks)}銘柄")
        return fallback_stocks
    
    def _get_fallback_nikkei225_stocks(self) -> List[Dict[str, str]]:
        """日経225銘柄のフォールバックリスト"""
        fallback_stocks = [
            {'symbol': '7203.T', 'name': 'トヨタ自動車株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'トヨタ自動車株式会社 (日経225)'},
            {'symbol': '6758.T', 'name': 'ソニーグループ株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ソニーグループ株式会社 (日経225)'},
            {'symbol': '9984.T', 'name': 'ソフトバンクグループ株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ソフトバンクグループ株式会社 (日経225)'},
            {'symbol': '6861.T', 'name': 'キーエンス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'キーエンス株式会社 (日経225)'},
            {'symbol': '6954.T', 'name': 'ファナック株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ファナック株式会社 (日経225)'},
            {'symbol': '6594.T', 'name': 'ニデック株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ニデック株式会社 (日経225)'},
            {'symbol': '7974.T', 'name': '任天堂株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '任天堂株式会社 (日経225)'},
            {'symbol': '8306.T', 'name': '三菱UFJフィナンシャル・グループ', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '三菱UFJフィナンシャル・グループ (日経225)'},
            {'symbol': '9433.T', 'name': 'KDDI株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'KDDI株式会社 (日経225)'},
            {'symbol': '7267.T', 'name': 'ホンダ技研工業株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ホンダ技研工業株式会社 (日経225)'},
            {'symbol': '4502.T', 'name': '武田薬品工業株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '武田薬品工業株式会社 (日経225)'},
            {'symbol': '4519.T', 'name': '中外製薬株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '中外製薬株式会社 (日経225)'},
            {'symbol': '4523.T', 'name': 'エーザイ株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'エーザイ株式会社 (日経225)'},
            {'symbol': '4568.T', 'name': '第一三共株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '第一三共株式会社 (日経225)'},
            {'symbol': '4901.T', 'name': '富士フイルムホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '富士フイルムホールディングス株式会社 (日経225)'},
            {'symbol': '4902.T', 'name': 'コニカミノルタ株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'コニカミノルタ株式会社 (日経225)'},
            {'symbol': '4911.T', 'name': '資生堂株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '資生堂株式会社 (日経225)'},
            {'symbol': '5108.T', 'name': 'ブリヂストン株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ブリヂストン株式会社 (日経225)'},
            {'symbol': '5201.T', 'name': 'AGC株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'AGC株式会社 (日経225)'},
            {'symbol': '5401.T', 'name': '日本製鉄株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '日本製鉄株式会社 (日経225)'},
            {'symbol': '6501.T', 'name': '日立製作所株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '日立製作所株式会社 (日経225)'},
            {'symbol': '6502.T', 'name': '東芝株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '東芝株式会社 (日経225)'},
            {'symbol': '6503.T', 'name': '三菱電機株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '三菱電機株式会社 (日経225)'},
            {'symbol': '6752.T', 'name': 'パナソニックホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'パナソニックホールディングス株式会社 (日経225)'},
            {'symbol': '6762.T', 'name': 'TDK株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'TDK株式会社 (日経225)'},
            {'symbol': '6902.T', 'name': 'デンソー株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'デンソー株式会社 (日経225)'},
            {'symbol': '6971.T', 'name': '京セラ株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '京セラ株式会社 (日経225)'},
            {'symbol': '7004.T', 'name': '日産自動車株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '日産自動車株式会社 (日経225)'},
            {'symbol': '7201.T', 'name': '日産自動車株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '日産自動車株式会社 (日経225)'},
            {'symbol': '7269.T', 'name': 'スズキ株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'スズキ株式会社 (日経225)'},
            {'symbol': '7270.T', 'name': 'SUBARU株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'SUBARU株式会社 (日経225)'},
            {'symbol': '7731.T', 'name': 'ニコン株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ニコン株式会社 (日経225)'},
            {'symbol': '7733.T', 'name': 'オリンパス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'オリンパス株式会社 (日経225)'},
            {'symbol': '7741.T', 'name': 'HOYA株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'HOYA株式会社 (日経225)'},
            {'symbol': '7751.T', 'name': 'キヤノン株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'キヤノン株式会社 (日経225)'},
            {'symbol': '7752.T', 'name': 'リコー株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'リコー株式会社 (日経225)'},
            {'symbol': '8001.T', 'name': '伊藤忠商事株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '伊藤忠商事株式会社 (日経225)'},
            {'symbol': '8002.T', 'name': '丸紅株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '丸紅株式会社 (日経225)'},
            {'symbol': '8031.T', 'name': '三井物産株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '三井物産株式会社 (日経225)'},
            {'symbol': '8035.T', 'name': '東京エレクトロン株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '東京エレクトロン株式会社 (日経225)'},
            {'symbol': '8053.T', 'name': '住友商事株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '住友商事株式会社 (日経225)'},
            {'symbol': '8058.T', 'name': '三菱商事株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '三菱商事株式会社 (日経225)'},
            {'symbol': '8111.T', 'name': '旭硝子株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '旭硝子株式会社 (日経225)'},
            {'symbol': '8267.T', 'name': 'イオン株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'イオン株式会社 (日経225)'},
            {'symbol': '8308.T', 'name': 'りそなホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'りそなホールディングス株式会社 (日経225)'},
            {'symbol': '8316.T', 'name': '三井住友フィナンシャルグループ株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '三井住友フィナンシャルグループ株式会社 (日経225)'},
            {'symbol': '8354.T', 'name': 'みずほフィナンシャルグループ株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'みずほフィナンシャルグループ株式会社 (日経225)'},
            {'symbol': '8411.T', 'name': 'みずほ銀行株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'みずほ銀行株式会社 (日経225)'},
            {'symbol': '8601.T', 'name': '大和証券グループ本社株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '大和証券グループ本社株式会社 (日経225)'},
            {'symbol': '8604.T', 'name': '野村ホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '野村ホールディングス株式会社 (日経225)'},
            {'symbol': '8630.T', 'name': 'SOMPOホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'SOMPOホールディングス株式会社 (日経225)'},
            {'symbol': '8725.T', 'name': 'MS&ADインシュアランスグループホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'MS&ADインシュアランスグループホールディングス株式会社 (日経225)'},
            {'symbol': '8750.T', 'name': '第一生命ホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '第一生命ホールディングス株式会社 (日経225)'},
            {'symbol': '8766.T', 'name': '東京海上ホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '東京海上ホールディングス株式会社 (日経225)'},
            {'symbol': '8801.T', 'name': '三井不動産株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '三井不動産株式会社 (日経225)'},
            {'symbol': '8802.T', 'name': '三菱地所株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '三菱地所株式会社 (日経225)'},
            {'symbol': '8830.T', 'name': '住友不動産株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '住友不動産株式会社 (日経225)'},
            {'symbol': '9001.T', 'name': '東武鉄道株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '東武鉄道株式会社 (日経225)'},
            {'symbol': '9005.T', 'name': '東京急行電鉄株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '東京急行電鉄株式会社 (日経225)'},
            {'symbol': '9020.T', 'name': '東日本旅客鉄道株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '東日本旅客鉄道株式会社 (日経225)'},
            {'symbol': '9021.T', 'name': '西日本旅客鉄道株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '西日本旅客鉄道株式会社 (日経225)'},
            {'symbol': '9022.T', 'name': '東海旅客鉄道株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '東海旅客鉄道株式会社 (日経225)'},
            {'symbol': '9062.T', 'name': '日本通運株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '日本通運株式会社 (日経225)'},
            {'symbol': '9064.T', 'name': 'ヤマトホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ヤマトホールディングス株式会社 (日経225)'},
            {'symbol': '9101.T', 'name': '日本郵船株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '日本郵船株式会社 (日経225)'},
            {'symbol': '9104.T', 'name': '商船三井株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '商船三井株式会社 (日経225)'},
            {'symbol': '9201.T', 'name': '日本航空株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '日本航空株式会社 (日経225)'},
            {'symbol': '9202.T', 'name': '全日本空輸株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '全日本空輸株式会社 (日経225)'},
            {'symbol': '9432.T', 'name': '日本電信電話株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '日本電信電話株式会社 (日経225)'},
            {'symbol': '9434.T', 'name': 'ソフトバンク株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ソフトバンク株式会社 (日経225)'},
            {'symbol': '9501.T', 'name': '東京電力ホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '東京電力ホールディングス株式会社 (日経225)'},
            {'symbol': '9502.T', 'name': '中部電力株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '中部電力株式会社 (日経225)'},
            {'symbol': '9503.T', 'name': '関西電力株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '関西電力株式会社 (日経225)'},
            {'symbol': '9531.T', 'name': '東京ガス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '東京ガス株式会社 (日経225)'},
            {'symbol': '9532.T', 'name': '大阪ガス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '大阪ガス株式会社 (日経225)'},
            {'symbol': '9602.T', 'name': '東宝株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': '東宝株式会社 (日経225)'},
            {'symbol': '9613.T', 'name': 'ＮＴＴデータ株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ＮＴＴデータ株式会社 (日経225)'},
            {'symbol': '9735.T', 'name': 'セコム株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'セコム株式会社 (日経225)'},
            {'symbol': '9766.T', 'name': 'コナミホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'コナミホールディングス株式会社 (日経225)'},
            {'symbol': '9783.T', 'name': 'ベネッセホールディングス株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ベネッセホールディングス株式会社 (日経225)'},
            {'symbol': '9983.T', 'name': 'ファーストリテイリング株式会社', 'index': 'NIKKEI225', 'category': 'high', 'country': 'JP', 'description': 'ファーストリテイリング株式会社 (日経225)'}
        ]
        self.logger.info(f"日経225フォールバック銘柄: {len(fallback_stocks)}銘柄")
        return fallback_stocks
