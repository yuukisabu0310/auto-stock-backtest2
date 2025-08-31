# 自動株式バックテストシステム

## 📊 GitHub Pages レポート

### メインダッシュボード
```
https://yuukisabu0310.github.io/auto-stock-backtest2/
```

### 個別レポートへのアクセス
- **スイングトレード戦略**: `https://yuukisabu0310.github.io/auto-stock-backtest2/スイングトレード_YYYYMMDD_HHMMSS.html`
- **中長期投資戦略**: `https://yuukisabu0310.github.io/auto-stock-backtest2/中長期投資_YYYYMMDD_HHMMSS.html`
- **対象銘柄一覧**: `https://yuukisabu0310.github.io/auto-stock-backtest2/swing_trading_stocks_YYYYMMDD_HHMMSS.html`

### 最新レポート例
- [スイングトレード最新レポート](https://yuukisabu0310.github.io/auto-stock-backtest2/スイングトレード_20250831_210336.html)
- [対象銘柄一覧](https://yuukisabu0310.github.io/auto-stock-backtest2/swing_trading_stocks_20250831_210334.html)

## 🚀 概要

自動株式バックテストシステム（指数別ランダム抽出版）は、S&P500、NASDAQ100、日経225の銘柄を使用して、複数の投資戦略のバックテストを自動実行し、結果をレポート化するシステムです。

## 📈 特徴

- **指数別ランダム抽出**: SP500、NASDAQ100、日経225からランダムに銘柄を選択
- **複数戦略対応**: スイングトレード、中長期投資戦略
- **複数回実行**: 統計的有意性を確保するため複数回実行
- **結果集計**: 複数回の結果を集計して平均性能を算出
- **自動レポート生成**: HTML形式で詳細なレポートを自動生成
- **差分データ取得**: 効率的なデータ取得でAPI負荷を軽減

## 🎯 戦略

### スイングトレード戦略
- **対象銘柄数**: 75銘柄（各指数25銘柄）
- **時間枠**: 日次データ
- **特徴**: 短期の価格変動を活用

### 中長期投資戦略
- **対象銘柄数**: 150銘柄（各指数50銘柄）
- **時間枠**: 週次データ
- **特徴**: 長期の成長トレンドを活用

## 📊 データソース

- **主要データソース**: stooq.com
- **期間**: 2020年1月1日 〜 2025年8月31日
- **データ形式**: 日次・週次株価データ

## 🔧 技術仕様

- **Python 3.9**
- **主要ライブラリ**: pandas, numpy, plotly, pandas-datareader
- **自動実行**: GitHub Actions（毎日06:00 UTC）
- **レポート**: HTML + Plotly（インタラクティブチャート）

## 📁 ファイル構成

```
auto-stock-backtest2/
├── main.py                 # メインスクリプト
├── data_loader.py          # データ取得・管理
├── backtest_engine.py      # バックテストエンジン
├── report_generator.py     # レポート生成
├── backtest_aggregator.py  # 結果集計
├── config.py              # 設定ファイル
├── index_stocks.csv       # 銘柄リスト
├── cache/                 # 株価データキャッシュ
├── reports/               # 生成レポート
├── results/               # バックテスト結果
└── logs/                  # ログファイル
```

## 🚀 使用方法

### 1. 環境セットアップ
```bash
pip install -r requirements.txt
```

### 2. 全戦略バックテスト実行
```bash
python main.py --num-runs 5 --base-seed 42
```

### 3. 特定戦略のみ実行
```bash
python main.py --strategy swing_trading --num-runs 3
```

### 4. 指数別銘柄数確認
```bash
python main.py --show-indices
```

## 📈 レポート内容

### パフォーマンス指標
- 総リターン
- シャープレシオ
- 最大ドローダウン
- 勝率
- 取引回数

### チャート
- エクイティカーブ
- 月次リターン
- ドローダウン推移
- 取引履歴

### 戦略条件
- エントリー条件
- エグジット条件
- リスク管理設定

## 🔄 自動実行

### GitHub Actions設定
- **実行スケジュール**: 毎日06:00 UTC（日本時間15:00）
- **実行内容**: 全戦略の3回実行
- **自動デプロイ**: レポートの自動更新

### 差分データ取得
- 既存キャッシュを活用
- 不足期間のみ新規取得
- 効率的なデータ管理

## 📊 結果の解釈

### 統計的有意性
- 複数回実行による平均性能
- 標準偏差によるリスク評価
- 信頼区間の算出

### 戦略比較
- リターン比較
- リスク調整後リターン
- ドローダウン比較

## 🔧 カスタマイズ

### 戦略パラメータ変更
`config.py`の`TRADING_RULES`を編集

### 銘柄リスト更新
```bash
python update_stocks.py
```

### 期間変更
```bash
python main.py --start-date 2023-01-01 --end-date 2024-12-31
```

## 📝 注意事項

- デイトレード戦略は5分足データの取得制限により除去
- 無料APIの制限により、差分データ取得を採用
- 過去の結果は将来の保証ではありません

## 🤝 貢献

バグ報告や機能要望は、GitHubのIssuesでお知らせください。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。  
