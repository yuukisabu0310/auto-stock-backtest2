"""
銘柄管理ユーティリティ
銘柄ファイルの管理と操作を行うスクリプト
"""
import sys
import os
import argparse
import json
from typing import List, Dict

# パスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from symbol_manager import SymbolManager


def list_symbols(symbol_manager: SymbolManager):
    """銘柄一覧を表示"""
    print("📊 銘柄一覧")
    print("="*60)
    
    # カスタム銘柄のみ
    custom_symbols = symbol_manager.get_custom_symbols()
    print(f"\n🔹 カスタム銘柄 ({len(custom_symbols)}銘柄):")
    for symbol in custom_symbols:
        print(f"  {symbol}")


def add_symbol(symbol_manager: SymbolManager, symbol: str, category: str = "custom"):
    """銘柄を追加"""
    if not symbol_manager.validate_symbol(symbol):
        print(f"❌ 無効な銘柄シンボル: {symbol}")
        print("有効な形式: SYMBOL.US, SYMBOL.JP など")
        return False
    
    # カスタム銘柄のみサポート
    if category != "custom":
        print(f"⚠️ カスタム銘柄のみサポートしています。カテゴリを 'custom' に変更します。")
        category = "custom"
    
    success = symbol_manager.add_custom_symbol(symbol)
    
    if success:
        print(f"✅ 銘柄を追加しました: {symbol}")
    else:
        print(f"⚠️ 銘柄は既に存在します: {symbol}")
    
    return success


def remove_symbol(symbol_manager: SymbolManager, symbol: str, category: str = "custom"):
    """銘柄を削除"""
    # カスタム銘柄のみサポート
    if category != "custom":
        print(f"⚠️ カスタム銘柄のみサポートしています。カテゴリを 'custom' に変更します。")
        category = "custom"
    
    success = symbol_manager.remove_custom_symbol(symbol)
    
    if success:
        print(f"✅ 銘柄を削除しました: {symbol}")
    else:
        print(f"⚠️ 銘柄が見つかりません: {symbol}")
    
    return success


def show_symbol_info(symbol_manager: SymbolManager, symbol: str):
    """銘柄の詳細情報を表示"""
    info = symbol_manager.get_symbol_info(symbol)
    
    print(f"📊 銘柄情報: {symbol}")
    print("="*40)
    print(f"カスタム銘柄: {'✅' if info['is_custom'] else '❌'}")


def export_symbols(symbol_manager: SymbolManager, output_file: str):
    """銘柄リストをCSVにエクスポート"""
    symbol_manager.export_symbols_to_csv(output_file)
    print(f"✅ 銘柄リストをエクスポートしました: {output_file}")


def import_symbols(symbol_manager: SymbolManager, input_file: str):
    """CSVから銘柄リストをインポート"""
    if not os.path.exists(input_file):
        print(f"❌ ファイルが見つかりません: {input_file}")
        return False
    
    symbol_manager.import_symbols_from_csv(input_file)
    print(f"✅ 銘柄リストをインポートしました: {input_file}")
    return True




def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='銘柄管理ユーティリティ')
    parser.add_argument('--symbols-file', default='symbols.json', help='銘柄ファイルパス')
    
    subparsers = parser.add_subparsers(dest='command', help='利用可能なコマンド')
    
    # 銘柄一覧表示
    list_parser = subparsers.add_parser('list', help='銘柄一覧を表示')
    
    # 銘柄追加
    add_parser = subparsers.add_parser('add', help='銘柄を追加')
    add_parser.add_argument('symbol', help='銘柄シンボル')
    add_parser.add_argument('--category', default='custom', 
                           choices=['custom'],
                           help='カテゴリ（customのみサポート）')
    
    # 銘柄削除
    remove_parser = subparsers.add_parser('remove', help='銘柄を削除')
    remove_parser.add_argument('symbol', help='銘柄シンボル')
    remove_parser.add_argument('--category', default='custom',
                             choices=['custom'],
                             help='カテゴリ（customのみサポート）')
    
    # 銘柄情報表示
    info_parser = subparsers.add_parser('info', help='銘柄情報を表示')
    info_parser.add_argument('symbol', help='銘柄シンボル')
    
    # エクスポート
    export_parser = subparsers.add_parser('export', help='銘柄リストをCSVにエクスポート')
    export_parser.add_argument('--output', default='symbols_export.csv', help='出力ファイル名')
    
    # インポート
    import_parser = subparsers.add_parser('import', help='CSVから銘柄リストをインポート')
    import_parser.add_argument('--input', required=True, help='入力ファイル名')
    
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # 銘柄管理クラスの初期化
        symbol_manager = SymbolManager(args.symbols_file)
        
        if args.command == 'list':
            list_symbols(symbol_manager)
        
        elif args.command == 'add':
            add_symbol(symbol_manager, args.symbol, args.category)
        
        elif args.command == 'remove':
            remove_symbol(symbol_manager, args.symbol, args.category)
        
        elif args.command == 'info':
            show_symbol_info(symbol_manager, args.symbol)
        
        elif args.command == 'export':
            export_symbols(symbol_manager, args.output)
        
        elif args.command == 'import':
            import_symbols(symbol_manager, args.input)
        
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
