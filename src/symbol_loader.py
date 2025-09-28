"""
銘柄リスト読み込みモジュール
外部ファイルから銘柄リストを読み込み
"""
import json
import pandas as pd
import os
from typing import List, Dict, Optional


class SymbolLoader:
    def __init__(self, config_path: str = "config.json"):
        """銘柄ローダーの初期化"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.symbols_config = self.config.get('symbols', {})
        self.config_file = self.symbols_config.get('config_file', 'symbols_config.json')
        self.default_sources = self.symbols_config.get('default_sources', ['sp500_symbols', 'nasdaq_symbols', 'custom_symbols'])
        self.max_symbols = self.symbols_config.get('max_symbols', 1000)
    
    def load_symbols_config(self) -> Dict:
        """銘柄設定ファイルを読み込み"""
        if not os.path.exists(self.config_file):
            print(f"銘柄設定ファイルが見つかりません: {self.config_file}")
            return {}
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"銘柄設定ファイル読み込みエラー: {e}")
            return {}
    
    def get_custom_symbols(self) -> List[str]:
        """カスタム銘柄を取得"""
        symbols_config = self.load_symbols_config()
        return symbols_config.get('custom_symbols', [])
    
    def get_symbols_from_config(self, sources: List[str] = None) -> List[str]:
        """設定ファイルから銘柄リストを取得"""
        if sources is None:
            sources = self.default_sources
        
        symbols_config = self.load_symbols_config()
        all_symbols = []
        
        for source in sources:
            if source in symbols_config:
                all_symbols.extend(symbols_config[source])
        
        # 重複除去
        return list(set(all_symbols))
    
    def get_all_symbols(self, limit: bool = True) -> List[str]:
        """全銘柄を取得（重複除去）"""
        symbols_config = self.load_symbols_config()
        all_symbols = []
        
        # 各ソースから銘柄を取得
        for source in self.default_sources:
            if source in symbols_config:
                all_symbols.extend(symbols_config[source])
        
        # 重複除去
        unique_symbols = list(set(all_symbols))
        
        # 最大銘柄数で制限（limit=Trueの場合のみ）
        if limit and len(unique_symbols) > self.max_symbols:
            return unique_symbols[:self.max_symbols]
        
        return unique_symbols
    
    
    def add_custom_symbol(self, symbol: str) -> bool:
        """カスタム銘柄を追加"""
        symbols_config = self.load_symbols_config()
        custom_symbols = symbols_config.get('custom_symbols', [])
        
        if symbol in custom_symbols:
            print(f"銘柄は既に存在します: {symbol}")
            return False
        
        custom_symbols.append(symbol)
        symbols_config['custom_symbols'] = custom_symbols
        
        # ファイルに保存
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(symbols_config, f, indent=2, ensure_ascii=False)
        
        print(f"カスタム銘柄を追加しました: {symbol}")
        return True
    
    def remove_custom_symbol(self, symbol: str) -> bool:
        """カスタム銘柄を削除"""
        symbols_config = self.load_symbols_config()
        custom_symbols = symbols_config.get('custom_symbols', [])
        
        if symbol not in custom_symbols:
            print(f"銘柄が見つかりません: {symbol}")
            return False
        
        custom_symbols.remove(symbol)
        symbols_config['custom_symbols'] = custom_symbols
        
        # ファイルに保存
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(symbols_config, f, indent=2, ensure_ascii=False)
        
        print(f"カスタム銘柄を削除しました: {symbol}")
        return True
