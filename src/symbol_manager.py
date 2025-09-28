"""
銘柄管理モジュール
指定銘柄のファイル管理とセクター別銘柄管理
"""
import json
import os
from typing import List, Dict, Optional, Set


class SymbolManager:
    def __init__(self, symbols_file: str = None):
        """銘柄管理クラスの初期化"""
        self.symbols_file = symbols_file
        # symbols.jsonへの依存を除去
        self.symbols_data = {}
    
    def load_symbols(self) -> Dict:
        """銘柄ファイルを読み込み"""
        if not os.path.exists(self.symbols_file):
            # デフォルトの銘柄ファイルを作成
            self.create_default_symbols_file()
        
        try:
            with open(self.symbols_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"銘柄ファイル読み込みエラー: {e}")
            return self.get_default_symbols()
    
    def create_default_symbols_file(self):
        """デフォルトの銘柄ファイルを作成"""
        default_symbols = self.get_default_symbols()
        self.save_symbols(default_symbols)
        print(f"デフォルトの銘柄ファイルを作成しました: {self.symbols_file}")
    
    def get_default_symbols(self) -> Dict:
        """デフォルトの銘柄データを取得"""
        return {
            "custom_symbols": [
                "AAPL.US", "MSFT.US", "GOOGL.US", "AMZN.US", "TSLA.US",
                "META.US", "NVDA.US", "BRK-B.US", "UNH.US", "JNJ.US"
            ]
        }
    
    def save_symbols(self, symbols_data: Dict):
        """銘柄ファイルを保存"""
        try:
            with open(self.symbols_file, 'w', encoding='utf-8') as f:
                json.dump(symbols_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"銘柄ファイル保存エラー: {e}")
    
    def get_custom_symbols(self) -> List[str]:
        """カスタム銘柄リストを取得（symbols_config.jsonから）"""
        from symbol_loader import SymbolLoader
        symbol_loader = SymbolLoader()
        return symbol_loader.get_custom_symbols()
    
    
    def get_excluded_symbols(self) -> List[str]:
        """除外銘柄リストを取得"""
        return self.symbols_data.get('excluded_symbols', [])
    
    def add_custom_symbol(self, symbol: str) -> bool:
        """カスタム銘柄を追加"""
        if symbol not in self.symbols_data.get('custom_symbols', []):
            self.symbols_data.setdefault('custom_symbols', []).append(symbol)
            self.save_symbols(self.symbols_data)
            return True
        return False
    
    def remove_custom_symbol(self, symbol: str) -> bool:
        """カスタム銘柄を削除"""
        if symbol in self.symbols_data.get('custom_symbols', []):
            self.symbols_data['custom_symbols'].remove(symbol)
            self.save_symbols(self.symbols_data)
            return True
        return False
    
    
    def get_all_symbols(self, exclude_symbols: List[str] = None) -> List[str]:
        """全銘柄を取得（除外銘柄を除く）"""
        # カスタム銘柄のみを取得
        all_symbols = self.get_custom_symbols()
        
        # 除外銘柄を除去
        if exclude_symbols:
            all_symbols = [symbol for symbol in all_symbols if symbol not in exclude_symbols]
        
        return all_symbols
    
    
    def validate_symbol(self, symbol: str) -> bool:
        """銘柄シンボルの形式を検証"""
        # 基本的な形式チェック（.US、.JP等のサフィックス）
        if '.' not in symbol:
            return False
        
        suffix = symbol.split('.')[-1]
        valid_suffixes = ['US', 'JP', 'UK', 'DE', 'FR', 'CA', 'AU']
        
        return suffix.upper() in valid_suffixes
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """銘柄の詳細情報を取得"""
        info = {
            'symbol': symbol,
            'is_custom': symbol in self.get_custom_symbols()
        }
        
        return info
    
    def export_symbols_to_csv(self, output_file: str = "symbols_export.csv"):
        """銘柄リストをCSVファイルにエクスポート"""
        import pandas as pd
        
        symbols_data = []
        
        # カスタム銘柄のみ
        for symbol in self.get_custom_symbols():
            symbols_data.append({
                'symbol': symbol,
                'type': 'custom'
            })
        
        # CSVファイルに保存
        df = pd.DataFrame(symbols_data)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"銘柄リストをエクスポートしました: {output_file}")
    
    def import_symbols_from_csv(self, input_file: str):
        """CSVファイルから銘柄リストをインポート"""
        import pandas as pd
        
        try:
            df = pd.read_csv(input_file, encoding='utf-8')
            
            # カスタム銘柄のみを更新
            custom_symbols = df[df['type'] == 'custom']['symbol'].tolist()
            self.symbols_data['custom_symbols'] = custom_symbols
            
            self.save_symbols(self.symbols_data)
            print(f"銘柄リストをインポートしました: {input_file}")
            
        except Exception as e:
            print(f"CSVインポートエラー: {e}")
