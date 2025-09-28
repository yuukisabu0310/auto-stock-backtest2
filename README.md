# スイングトレード分析システム

## 概要

株式のスイングトレード分析を行うシステムです。複数のデータソースから株価データを取得し、技術指標に基づいたスイングトレード戦略をバックテストし、詳細な分析レポートを生成します。

## 主な機能

- **データ取得**: 複数のデータソース（yfinance、Alpha Vantage）から株価データを取得
- **並列処理**: 複数銘柄の同時データ取得で高速化
- **バックテスト**: スイングトレード戦略の過去データでの検証
- **技術指標**: SMA、RSI、MACD、ボリンジャーバンド等の計算
- **AI分析**: 各銘柄の分析コメントと推奨アクション
- **レポート生成**: インタラクティブなHTMLレポートの生成
- **銘柄管理**: 外部ファイルでの銘柄リスト管理
- **シグナル条件詳細表示**: 買い・売り条件の詳細とスコア表示
- **チャート期間設定**: 2年+3ヶ月余白の可視化設定

## システム構成

### ファイル構成
```
auto-stock-backtest2/
├── main.py                    # メイン実行ファイル
├── config.json               # システム設定ファイル
├── symbols_config.json        # 銘柄リスト設定ファイル
├── requirements.txt          # 依存関係
├── src/
│   ├── data_fetcher.py       # データ取得モジュール
│   ├── backtest_engine.py    # バックテストエンジン
│   ├── strategy.py           # スイングトレード戦略
│   ├── report_generator.py   # レポート生成
│   ├── report_generator_chart.py # チャート生成
│   ├── symbol_loader.py      # 銘柄ローダー
│   └── symbol_manager.py     # 銘柄管理
└── reports/                  # 生成レポート格納ディレクトリ
```

### 銘柄管理システム

#### **symbols_config.json** - 統合銘柄設定ファイル
```json
{
  "sp500_symbols": ["AAPL.US", "MSFT.US", ...],
  "nasdaq_symbols": ["AAPL.US", "MSFT.US", ...],
  "custom_symbols": ["AAPL.US", "MSFT.US", ...]
}
```

#### **銘柄の種類**
- **sp500_symbols**: S&P500銘柄
- **nasdaq_symbols**: NASDAQ銘柄
- **custom_symbols**: カスタム銘柄（ユーザー指定）

## インストール

### 1. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 2. 設定ファイルの確認
- `config.json`: システム全体の設定
- `symbols_config.json`: 銘柄リストの設定

## 使用方法

### 基本的な使用方法

#### **1. データ更新**
```bash
# デフォルト設定でデータ更新
python main.py --update-data

# 並列処理数を指定してデータ更新
python main.py --update-data --workers 8

# 初期データ取得（Alpha Vantage全銘柄対応）
python main.py --init-data

# 未取得銘柄のみ更新
python main.py --update-data --uncached-only
```

#### **2. 分析実行**
```bash
# デフォルト設定で分析実行
python main.py

# 指定銘柄を分析実行
python main.py --symbols AAPL.US MSFT.US GOOGL.US

# 並列処理数を指定
python main.py --workers 8

# ランダムシードを指定
python main.py --seed 12345

# ファイルから銘柄を読み込まない
python main.py --no-file-symbols

# カスタム設定ファイルを使用
python main.py --config custom_config.json
```

#### **3. 銘柄管理**
```bash
# 銘柄リストを表示
python symbol_management.py list

# カスタム銘柄を追加
python symbol_management.py add AAPL.US

# カスタム銘柄を削除
python symbol_management.py remove AAPL.US
```

### 高度な使用方法

#### **1. 設定ファイルのカスタマイズ**

**config.json**での設定例：
```json
{
  "data_sources": {
    "priority": ["yfinance", "alpha_vantage"],
    "max_workers": 4,
    "timeout": 30
  },
  "symbols": {
    "config_file": "symbols_config.json",
    "default_sources": ["sp500_symbols", "nasdaq_symbols", "custom_symbols"],
    "max_symbols": 100
  },
  "backtest": {
    "period_years": 5,
    "start_date_offset_months": 1,
    "timeframe": "daily"
  },
  "reports": {
    "chart_display": {
      "years_back": 2,
      "months_forward_margin": 3
    }
  }
}
```

#### **2. 銘柄リストの管理**

**symbols_config.json**での設定例：
```json
{
  "custom_symbols": [
    "AAPL.US", "MSFT.US", "GOOGL.US", "AMZN.US", "TSLA.US"
  ]
}
```

#### **3. プログラムでの銘柄管理**
```python
from src.symbol_loader import SymbolLoader

loader = SymbolLoader()

# カスタム銘柄を追加
loader.add_custom_symbol("NEW.US")

# カスタム銘柄を削除
loader.remove_custom_symbol("OLD.US")

# 全銘柄を取得
all_symbols = loader.get_all_symbols()

# カスタム銘柄を取得
custom_symbols = loader.get_custom_symbols()
```

## データソース

### 対応データソース
- **yfinance**: Yahoo Finance（無料、制限あり）
- **Alpha Vantage**: Alpha Vantage API（有料、高品質）

### Alpha Vantage制限
- **カスタム銘柄のみ**: Alpha Vantageはcustom_symbolsで指定された銘柄のみ
- **1分で5リクエスト**: 自動制限管理
- **12秒間隔**: リクエスト間隔の自動管理

## スイングトレード戦略

### 買いシグナル（各条件+1点）
1. **PER割安判定**: 価格 < 25日移動平均
2. **価格上昇トレンド**: 価格 > 25日移動平均
3. **中期トレンド確認**: 25日MA > 50日MA
4. **RSI条件**: RSI 30-50の適正範囲
5. **MACD条件**: MACD > シグナル線
6. **MACDヒストグラム**: ヒストグラム > 0
7. **出来高増加**: 出来高比率 > 1.2
8. **ボリンジャーバンド下限**: 価格 <= BB下限

### 売りシグナル（各条件+1点）
1. **PER過熱判定**: 価格 > 25日MA × 1.1
2. **価格下落トレンド**: 価格 < 25日移動平均
3. **中期トレンド悪化**: 25日MA < 50日MA
4. **RSI過熱**: RSI >= 70
5. **MACD悪化**: MACD < シグナル線
6. **MACDヒストグラム悪化**: ヒストグラム < 0
7. **出来高伴う陰線**: 陰線 & 出来高増加
8. **ボリンジャーバンド上限**: 価格 >= BB上限
9. **価格急落**: 1日変動率 < -5%

### スコアリングシステム
- **総合スコア**: 買いスコア - 売りスコア
- **強い買い**: スコア ≥ 7
- **買い注意**: スコア 4-6
- **様子見**: スコア -3〜3
- **売り注意**: スコア -4〜-6
- **強い売り**: スコア ≤ -7

## レポート生成

### 生成されるレポート
1. **index.html**: メインレポート（全銘柄の概要）
2. **swing_trading_YYYYMMDD_HHMMSS.html**: 詳細分析レポート
3. **swing_trading_stocks_YYYYMMDD_HHMMSS.html**: 銘柄別分析レポート
4. **individual_<TICKER>_swing_trading_YYYYMMDD_HHMMSS.html**: 個別銘柄レポート

### レポートの内容
- **チャート**: 価格、SMA、RSI、MACD、ボリンジャーバンド（2年+3ヶ月余白表示）
- **分析結果**: 買い/売りシグナル、スコア、推奨アクション
- **シグナル条件詳細**: 各条件の達成状況とスコア表示
- **AI分析**: 各銘柄の詳細分析コメント
- **統計情報**: 勝率、平均リターン、最大ドローダウン
- **価格情報**: 買い価格、売り価格、現在価格、価格変動率

### チャート表示設定
- **表示期間**: 2年間の過去データ + 3ヶ月の未来余白
- **技術指標**: SMA25/50、EMA20/60/120/240、RSI、MACD、ボリンジャーバンド
- **カスタマイズ**: config.jsonで表示期間を調整可能

### シグナル条件詳細表示
レポートでは以下の詳細情報が表示されます：

#### 買い条件（緑色表示）
- ✅ **達成条件**: 条件が満たされている場合
- ⚪ **未達成条件**: 条件が満たされていない場合
- **スコア表示**: 各条件のポイント数
- **詳細説明**: 具体的な数値と比較結果

#### 売り条件（赤色表示）
- ❌ **達成条件**: 売りシグナル条件が満たされている場合
- ⚪ **未達成条件**: 売りシグナル条件が満たされていない場合
- **スコア表示**: 各条件のポイント数
- **詳細説明**: 具体的な数値と比較結果

## トラブルシューティング

### よくある問題

#### **1. データ取得エラー**
```
Failed to get ticker 'AAPL' reason: Expecting value: line 1 column 1 (char 0)
```
**解決方法**: 
- インターネット接続を確認
- データソースの設定を確認
- サンプルデータモードを使用

#### **2. モジュールエラー**
```
ModuleNotFoundError: No module named 'talib'
```
**解決方法**:
```bash
pip install TA-Lib
```

#### **3. 銘柄が見つからない**
```
銘柄が見つかりません: AAPL.US
```
**解決方法**:
- symbols_config.jsonで銘柄を確認
- 銘柄コードの形式を確認（.USサフィックス等）

### デバッグ方法

#### **1. ログの確認**
```bash
python main.py --update-data --verbose
```

#### **2. 設定の確認**
```python
from src.symbol_loader import SymbolLoader

loader = SymbolLoader()
print(f"カスタム銘柄: {loader.get_custom_symbols()}")
```

#### **3. データの確認**
```python
from src.data_fetcher import DataFetcher

fetcher = DataFetcher()
data = fetcher.fetch_stock_data("AAPL.US", "2023-01-01", "2024-01-01")
print(f"データ形状: {data.shape}")
```

## 新機能

### シグナル条件詳細表示
- **透明性向上**: 各条件の達成状況を視覚的に表示
- **スコア可視化**: 買い・売り条件のスコア詳細
- **条件説明**: 具体的な数値と比較結果を表示
- **色分け表示**: 達成条件は緑/赤、未達成は灰色

### チャート期間カスタマイズ
- **デフォルト設定**: 2年+3ヶ月余白表示
- **設定可能**: config.jsonで期間を調整
- **未来余白**: 将来の予測スペースを表示
- **長期トレンド**: より長期的な視点での分析

### 価格情報表示
- **買い価格**: 期間開始時の価格
- **売り価格**: 期間終了時の価格
- **現在価格**: 最新の価格
- **価格変動**: 期間中の変動率

## パフォーマンス最適化

### 並列処理
- **デフォルト**: 4ワーカー
- **推奨**: 8ワーカー（CPUコア数に応じて調整）
- **制限**: システムリソースに応じて調整

### キャッシュ
- **自動キャッシュ**: 取得したデータは自動保存
- **キャッシュ利用**: 2回目以降は高速実行
- **キャッシュクリア**: 古いデータを手動削除

### メモリ使用量
- **バッチ処理**: 大量銘柄は分割処理
- **データ圧縮**: 不要なデータは削除
- **ガベージコレクション**: 定期的なメモリ解放

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

プルリクエストやイシューの報告を歓迎します。

## 更新履歴

- **v1.0.0**: 初回リリース
- **v1.1.0**: 並列処理対応
- **v1.2.0**: 外部ファイル銘柄管理対応
- **v1.3.0**: 統合銘柄管理システム
- **v1.4.0**: シグナル条件詳細表示機能追加
- **v1.5.0**: チャート表示期間カスタマイズ機能追加

## サポート

問題が発生した場合は、GitHubのIssuesで報告してください。