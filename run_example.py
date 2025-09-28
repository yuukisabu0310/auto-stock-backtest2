"""
スイングトレード分析システム - 実行例
実際の使用例を示すサンプルスクリプト
"""
import os
import sys
import subprocess
from datetime import datetime


def run_example():
    """実行例を表示"""
    print("🚀 スイングトレード分析システム - 実行例")
    print("="*60)
    
    print("\n📋 基本的な使用方法:")
    print("1. 前回のシードで分析実行:")
    print("   python main.py")
    
    print("\n2. 新しいシードで分析実行:")
    print("   python main.py --seed 12345")
    
    print("\n3. 指定銘柄で分析実行:")
    print("   python main.py --symbols AAPL.US MSFT.US GOOGL.US")
    
    print("\n4. 並列処理数を指定:")
    print("   python main.py --workers 8")
    
    print("\n5. 初回データ取得:")
    print("   python main.py --update-data")
    
    print("\n6. 指定銘柄のデータ更新:")
    print("   python main.py --update-data --symbols AAPL.US MSFT.US")
    
    print("\n" + "="*60)
    print("📊 システムの特徴:")
    print("• S&P500とNASDAQからランダムに100銘柄を選定")
    print("• ファンダメンタル + テクニカル分析")
    print("• 並列処理による高速バックテスト")
    print("• インタラクティブレポート生成")
    print("• AI分析コメント自動生成")
    
    print("\n" + "="*60)
    print("📁 出力ファイル:")
    print("• reports/index.html - メインダッシュボード")
    print("• reports/swing_trading_YYYYMMDD_HHMMSS.html - メインレポート")
    print("• reports/swing_trading_stocks_YYYYMMDD_HHMMSS.html - 銘柄一覧")
    print("• reports/individual_<TICKER>_swing_trading_YYYYMMDD_HHMMSS.html - 個別分析")
    
    print("\n" + "="*60)
    print("⚙️ 設定ファイル (config.json):")
    print("• バックテスト期間: 5年間")
    print("• ランダム銘柄数: 100銘柄")
    print("• 並列処理数: 4（デフォルト）")
    print("• テクニカル指標: RSI、MACD、移動平均線")
    
    print("\n" + "="*60)
    print("🎯 戦略パラメータ:")
    print("• 買いスコア: 0〜+10")
    print("• 売りスコア: 0〜−10")
    print("• シグナル判定:")
    print("  - +7以上 → 強い買い")
    print("  - +4〜6 → 買い注意")
    print("  - −3〜+3 → 様子見")
    print("  - −4〜−6 → 売り注意")
    print("  - −7以下 → 強い売り")
    
    print("\n" + "="*60)
    print("🤖 AI分析コメント例:")
    print("• 利益確保目安: 直近高値から10%下落で利確検討")
    print("• 損切り目安: 20日MA割れやMACDデッドクロスで損切り")
    print("• 市場分析: ボラティリティ上昇により注意深いポジション管理が必要")
    
    print("\n" + "="*60)
    print("📈 パフォーマンス:")
    print("• 並列処理: 4コアで約100銘柄を5分以内で分析")
    print("• キャッシュ活用: 2回目以降の実行は大幅に高速化")
    print("• メモリ効率: 必要最小限のメモリ使用量で動作")
    
    print("\n" + "="*60)
    print("⚠️ 注意事項:")
    print("• cache/ディレクトリ内の株価データ（.pklファイル）は削除しないでください")
    print("• 外部API問題時はキャッシュデータを活用してバックテストを継続")
    print("• 大量の銘柄データを処理する際は十分なメモリを確保してください")
    
    print("\n" + "="*60)
    print("🔄 実際に実行してみますか？")
    print("1. 基本的な分析実行")
    print("2. 指定銘柄での分析実行")
    print("3. データ更新実行")
    print("4. 終了")
    
    choice = input("\n選択してください (1-4): ").strip()
    
    if choice == "1":
        print("\n🔄 基本的な分析を実行中...")
        subprocess.run([sys.executable, "main.py"])
    elif choice == "2":
        symbols = input("指定銘柄を入力してください (例: AAPL.US MSFT.US): ").strip()
        if symbols:
            print(f"\n🔄 指定銘柄での分析を実行中: {symbols}")
            subprocess.run([sys.executable, "main.py", "--symbols"] + symbols.split())
        else:
            print("銘柄が指定されませんでした。")
    elif choice == "3":
        print("\n🔄 データ更新を実行中...")
        subprocess.run([sys.executable, "main.py", "--update-data"])
    elif choice == "4":
        print("👋 終了します。")
    else:
        print("❌ 無効な選択です。")


if __name__ == "__main__":
    run_example()
