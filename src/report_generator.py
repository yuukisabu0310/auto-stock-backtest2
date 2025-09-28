"""
レポート生成システム
HTML/Plotlyによるインタラクティブレポート生成
"""
import os
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np


class ReportGenerator:
    def __init__(self, config_path: str = "config.json", symbol_manager=None):
        """レポート生成クラスの初期化"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.reports_dir = self.config['reports']['output_dir']
        self.history_days = self.config['reports']['history_days']
        self.chart_height = self.config['reports']['chart_height']
        self.include_ai_analysis = self.config['reports']['include_ai_analysis']
        self.symbol_manager = symbol_manager
        
        # レポートディレクトリの作成
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def generate_index_report(self) -> str:
        """メインインデックスレポートを生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"index.html"
        filepath = os.path.join(self.reports_dir, filename)
        
        # 過去のレポート履歴を取得
        history = self.get_report_history()
        
        # 最新レポートへのリンクを生成
        latest_links = ""
        if history:
            latest_report = history[0]  # 最新のレポート
            latest_folder = latest_report.get('folder', '')
            latest_main = latest_report.get('link_path', '')
            latest_stocks = latest_main.replace('swing_trading_', 'swing_trading_stocks_')
            
            latest_links = f"""
            <div class="latest-reports">
                <h3>🎯 最新分析結果</h3>
                <div class="latest-buttons">
                    <a href="{latest_main}" class="btn btn-primary">📊 メインレポート</a>
                    <a href="{latest_stocks}" class="btn btn-secondary">📋 銘柄一覧</a>
                </div>
            </div>
            """
        
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>スイングトレード分析システム - メインダッシュボード</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 20px;
        }}
        .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            color: #7f8c8d;
            margin: 10px 0 0 0;
            font-size: 1.1em;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .stat-card p {{
            margin: 0;
            opacity: 0.9;
        }}
        .history-section {{
            margin-top: 40px;
        }}
        .history-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .history-table th,
        .history-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .history-table th {{
            background-color: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }}
        .history-table tr:hover {{
            background-color: #f5f5f5;
        }}
        .latest-reports {{
            background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin: 30px 0;
            text-align: center;
        }}
        .latest-reports h3 {{
            margin: 0 0 20px 0;
            font-size: 1.5em;
        }}
        .latest-buttons {{
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background-color 0.3s;
        }}
        .btn:hover {{
            background-color: #2980b9;
        }}
        .btn-success {{
            background-color: #27ae60;
        }}
        .btn-success:hover {{
            background-color: #229954;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 スイングトレード分析システム</h1>
            <p>AI駆動の株式分析とバックテストレポート</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>{len(history)}</h3>
                <p>過去30日間のレポート数</p>
            </div>
            <div class="stat-card">
                <h3>100+</h3>
                <p>分析対象銘柄数</p>
            </div>
            <div class="stat-card">
                <h3>5年</h3>
                <p>バックテスト期間</p>
            </div>
            <div class="stat-card">
                <h3>AI</h3>
                <p>分析コメント生成</p>
            </div>
        </div>
        
        {latest_links}
        
        <div class="history-section">
            <h2>📈 最新レポート</h2>
            <p>過去{self.history_days}日間の分析履歴</p>
            
            <table class="history-table">
                <thead>
                    <tr>
                        <th>日時</th>
                        <th>戦略</th>
                        <th>ファイル名</th>
                        <th>アクション</th>
                    </tr>
                </thead>
                <tbody>
                    {self.generate_history_rows(history)}
                </tbody>
            </table>
        </div>
        
        <div style="text-align: center; margin-top: 40px;">
            <a href="#" class="btn btn-success">新しい分析を実行</a>
        </div>
    </div>
</body>
</html>
        """
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def generate_history_rows(self, history: List[Dict]) -> str:
        """履歴テーブルの行を生成"""
        rows = []
        for report in history:
            link_path = report.get('link_path', report['filename'])
            rows.append(f"""
                <tr>
                    <td>{report['datetime']}</td>
                    <td>{report['strategy']}</td>
                    <td>{report['filename']}</td>
                    <td><a href="{link_path}" class="btn">表示</a></td>
                </tr>
            """)
        return ''.join(rows)
    
    def get_report_history(self) -> List[Dict]:
        """過去のレポート履歴を取得（アーカイブフォルダも含む）"""
        history = []
        
        if not os.path.exists(self.reports_dir):
            return history
        
        # アーカイブフォルダを検索
        for item in os.listdir(self.reports_dir):
            item_path = os.path.join(self.reports_dir, item)
            
            if os.path.isdir(item_path) and item.startswith('analysis_'):
                # アーカイブフォルダ内のレポートを検索
                for filename in os.listdir(item_path):
                    if filename.startswith('swing_trading_') and filename.endswith('.html'):
                        filepath = os.path.join(item_path, filename)
                        stat = os.stat(filepath)
                        mod_time = datetime.fromtimestamp(stat.st_mtime)
                        
                        # 過去30日以内のファイルのみ
                        if (datetime.now() - mod_time).days <= self.history_days:
                            history.append({
                                'datetime': mod_time.strftime('%Y-%m-%d %H:%M'),
                                'strategy': 'スイングトレード',
                                'filename': filename,
                                'folder': item,
                                'link_path': f"{item}/{filename}"
                            })
        
        # 日時でソート（新しい順）
        history.sort(key=lambda x: x['datetime'], reverse=True)
        
        return history
    
    def generate_swing_trading_report(self, backtest_results: Dict) -> str:
        """スイングトレードレポートを生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"swing_trading_{timestamp}.html"
        filepath = os.path.join(self.reports_dir, filename)
        
        # パフォーマンス指標
        overall_stats = backtest_results.get('overall_stats', {})
        
        # インタラクティブチャートを生成
        equity_chart = self.create_equity_chart(backtest_results)
        vix_chart = self.create_vix_chart(backtest_results)
        trade_history_chart = self.create_trade_history_chart(backtest_results)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>スイングトレード分析レポート - {timestamp}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 20px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .metric-card h3 {{
            margin: 0 0 10px 0;
            font-size: 1.8em;
        }}
        .metric-card p {{
            margin: 0;
            opacity: 0.9;
        }}
        .chart-container {{
            margin: 30px 0;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        .section-title {{
            color: #2c3e50;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin: 30px 0 20px 0;
        }}
        .ai-comment {{
            background: #f8f9fa;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background-color 0.3s;
        }}
        .btn:hover {{
            background-color: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 スイングトレード分析レポート</h1>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>{float(overall_stats.get('total_return_sum', 0)):.1f}%</h3>
                <p>合計総リターン</p>
            </div>
            <div class="metric-card">
                <h3>{overall_stats.get('avg_sharpe_ratio', 0):.2f}</h3>
                <p>平均シャープレシオ</p>
            </div>
            <div class="metric-card">
                <h3>{float(overall_stats.get('avg_max_drawdown', 0)):.1f}%</h3>
                <p>平均最大ドローダウン</p>
            </div>
            <div class="metric-card">
                <h3>{len(backtest_results.get('successful_results', []))}</h3>
                <p>取引数</p>
            </div>
        </div>
        
        <div class="chart-container">
            <h2 class="section-title">📈 エクイティカーブ</h2>
            <div id="equity-chart" style="height: {self.chart_height}px;"></div>
        </div>
        
        <div class="chart-container">
            <h2 class="section-title">📊 VIX指数</h2>
            <div id="vix-chart" style="height: {self.chart_height}px;"></div>
        </div>
        
        <div class="chart-container">
            <h2 class="section-title">📋 取引履歴</h2>
            <div id="trade-history-chart" style="height: {self.chart_height}px;"></div>
        </div>
        
        <div class="ai-comment">
            <h3>🤖 AI分析コメント</h3>
            <p>市場全体の分析結果に基づく投資判断の参考情報を提供します。</p>
        </div>
        
        <div style="text-align: center; margin-top: 40px;">
            <a href="swing_trading_stocks_{timestamp}.html" class="btn">📋 対象銘柄一覧を見る</a>
            <a href="../index.html" class="btn" style="margin-left: 10px;">📊 ダッシュボードに戻る</a>
        </div>
    </div>
    
    <script>
        {equity_chart}
        {vix_chart}
        {trade_history_chart}
    </script>
</body>
</html>
        """
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def create_equity_chart(self, backtest_results: Dict) -> str:
        """エクイティカーブチャートを生成"""
        successful_results = backtest_results.get('successful_results', [])
        
        if not successful_results:
            # データがない場合のデフォルト表示
            chart_js = """
            var equityData = {
                x: [],
                y: [],
                type: 'scatter',
                mode: 'lines',
                name: 'エクイティカーブ',
                line: {color: '#2E86AB', width: 2}
            };
            
            var layout = {
                title: 'ポートフォリオパフォーマンス',
                xaxis: {title: '日付'},
                yaxis: {title: '累積リターン (%)'},
                showlegend: true
            };
            
            Plotly.newPlot('equity-chart', [equityData], layout);
            """
            return chart_js
        
        # 実際のバックテスト結果からエクイティカーブを生成
        # 各銘柄のパフォーマンスを統合
        total_returns = []
        dates = []
        
        for result in successful_results:
            performance = result.get('performance', {})
            total_return = performance.get('total_return', 0)
            total_returns.append(total_return)
        
        # 平均リターンでエクイティカーブを近似
        avg_return = np.mean(total_returns) if total_returns else 0
        
        # 日付範囲を取得
        start_date = backtest_results.get('start_date', '2020-01-01')
        end_date = backtest_results.get('end_date', '2024-12-31')
        
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # エクイティカーブを生成（平均リターンを日次で分散）
        daily_return = avg_return / len(dates) if len(dates) > 0 else 0
        equity = np.cumsum([daily_return] * len(dates)) + 100
        
        chart_js = f"""
        var equityData = {{
            x: {list(dates.strftime('%Y-%m-%d'))},
            y: {equity.tolist()},
            type: 'scatter',
            mode: 'lines',
            name: 'エクイティカーブ',
            line: {{color: '#2E86AB', width: 2}}
        }};
        
        var layout = {{
            title: 'ポートフォリオパフォーマンス',
            xaxis: {{title: '日付'}},
            yaxis: {{title: '累積リターン (%)'}},
            showlegend: true
        }};
        
        Plotly.newPlot('equity-chart', [equityData], layout);
        """
        
        return chart_js
    
    def create_vix_chart(self, backtest_results: Dict) -> str:
        """VIX指数チャートを生成"""
        # バックテスト期間を取得
        start_date = backtest_results.get('start_date', '2020-01-01')
        end_date = backtest_results.get('end_date', '2024-12-31')
        
        # エクイティカーブと同じ日付範囲でVIXデータを生成
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # サンプルVIXデータ（実際の実装ではVIXデータを取得）
        vix = 20 + np.random.randn(len(dates)) * 5
        vix = np.maximum(vix, 10)  # VIXは10以下にならない
        
        chart_js = f"""
        var vixData = {{
            x: {list(dates.strftime('%Y-%m-%d'))},
            y: {vix.tolist()},
            type: 'scatter',
            mode: 'lines',
            name: 'VIX指数',
            line: {{color: '#E74C3C', width: 2}},
            fill: 'tonexty'
        }};
        
        var layout = {{
            title: 'VIX指数（恐怖指数）',
            xaxis: {{title: '日付'}},
            yaxis: {{title: 'VIX値'}},
            showlegend: true
        }};
        
        Plotly.newPlot('vix-chart', [vixData], layout);
        """
        
        return chart_js
    
    def create_trade_history_chart(self, backtest_results: Dict) -> str:
        """取引履歴チャートを生成"""
        successful_results = backtest_results.get('successful_results', [])
        
        if not successful_results:
            # データがない場合のデフォルト表示
            chart_js = """
            var tradeData = {
                x: [],
                y: [],
                type: 'bar',
                name: '取引リターン',
                marker: {color: '#27AE60'}
            };
            
            var layout = {
                title: '取引履歴',
                xaxis: {title: '日付'},
                yaxis: {title: 'リターン (%)'},
                showlegend: true
            };
            
            Plotly.newPlot('trade-history-chart', [tradeData], layout);
            """
            return chart_js
        
        # 実際の取引履歴を生成
        trade_data = []
        for result in successful_results:
            symbol = result.get('symbol', '')
            performance = result.get('performance', {})
            total_return = performance.get('total_return', 0)
            
            trade_data.append({
                'symbol': symbol,
                'return': total_return,
                'date': backtest_results.get('end_date', '2024-12-31')
            })
        
        # 取引データを日付順にソート
        trade_data.sort(key=lambda x: x['date'])
        
        symbols = [d['symbol'] for d in trade_data]
        returns = [d['return'] for d in trade_data]
        dates = [d['date'] for d in trade_data]
        
        chart_js = f"""
        var tradeData = {{
            x: {symbols},
            y: {returns},
            type: 'bar',
            name: '銘柄別リターン',
            marker: {{
                color: {returns}.map(val => val > 0 ? '#27AE60' : '#E74C3C')
            }}
        }};
        
        var layout = {{
            title: '銘柄別取引リターン',
            xaxis: {{title: '銘柄'}},
            yaxis: {{title: 'リターン (%)'}},
            showlegend: true
        }};
        
        Plotly.newPlot('trade-history-chart', [tradeData], layout);
        """
        
        return chart_js
    
    def generate_stocks_report(self, backtest_results: Dict, custom_symbols: List[str] = None) -> str:
        """対象銘柄一覧レポートを生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"swing_trading_stocks_{timestamp}.html"
        filepath = os.path.join(self.reports_dir, filename)
        
        successful_results = backtest_results.get('successful_results', [])
        
        # custom_symbolsを優先してソート
        if custom_symbols:
            def sort_key(result):
                symbol = result['symbol']
                if symbol in custom_symbols:
                    return (0, custom_symbols.index(symbol))  # custom_symbolsを最初に
                else:
                    return (1, 0)  # その他の銘柄は後
            
            successful_results = sorted(successful_results, key=sort_key)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>対象銘柄一覧 - {timestamp}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 20px;
        }}
        .stocks-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        .stock-card {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .stock-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        .stock-card.premium {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}
        .stock-card.premium:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }}
        .stock-card.premium .stock-symbol {{
            color: white;
        }}
        .stock-symbol {{
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .stock-metrics {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 15px 0;
        }}
        .metric {{
            text-align: center;
            padding: 8px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .metric-value {{
            font-weight: bold;
            color: #2c3e50;
        }}
        .metric-label {{
            font-size: 0.9em;
            color: #7f8c8d;
        }}
        .signal {{
            text-align: center;
            padding: 8px;
            border-radius: 5px;
            margin: 10px 0;
            font-weight: bold;
        }}
        .signal-strong-buy {{ background: #d4edda; color: #155724; }}
        .signal-buy {{ background: #c8e6c9; color: #2e7d32; }}
        .signal-neutral {{ background: #e2e3e5; color: #383d41; }}
        .signal-sell {{ background: #ffcdd2; color: #c62828; }}
        .signal-strong-sell {{ background: #f5c6cb; color: #721c24; }}
        .btn {{
            display: inline-block;
            padding: 8px 16px;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 0.9em;
            transition: background-color 0.3s;
        }}
        .btn:hover {{
            background-color: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 対象銘柄一覧</h1>
            <p>分析対象銘柄: {len(successful_results)}銘柄</p>
        </div>
        
        <div class="stocks-grid">
            {self.generate_stock_cards(successful_results, custom_symbols)}
        </div>
        
        <div style="text-align: center; margin-top: 40px;">
            <a href="swing_trading_{timestamp}.html" class="btn">📊 メインレポートに戻る</a>
            <a href="../index.html" class="btn" style="margin-left: 10px;">🏠 ダッシュボードに戻る</a>
        </div>
    </div>
</body>
</html>
        """
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def generate_stock_cards(self, successful_results: List[Dict], custom_symbols: List[str] = None) -> str:
        """銘柄カードを生成"""
        cards = []
        
        for result in successful_results:
            symbol = result['symbol']
            performance = result.get('performance', {})
            signal = performance.get('latest_signal', 'N/A')
            score = performance.get('latest_score', 0)
            total_return = performance.get('total_return', 0)
            sharpe_ratio = performance.get('sharpe_ratio', 0)
            
            # symbols_config.jsonのcustom_symbolsかどうかを判定
            config_custom_symbols = self.symbol_manager.get_custom_symbols()
            is_config_custom = symbol in config_custom_symbols
            
            # コマンドライン指定銘柄かどうかを判定
            is_cmd_custom = custom_symbols and symbol in custom_symbols
            
            # プレミアム銘柄かどうか（設定ファイルのcustom_symbols）
            is_premium = is_config_custom
            
            # バッジの設定（プレミアム銘柄はバッジなし、カード色のみで区別）
            custom_badge = ''
            
            # シグナルクラスを決定
            signal_class = 'signal-neutral'
            if '強い買い' in signal:
                signal_class = 'signal-strong-buy'
            elif '買い' in signal:
                signal_class = 'signal-buy'
            elif '売り' in signal:
                signal_class = 'signal-sell'
            elif '強い売り' in signal:
                signal_class = 'signal-strong-sell'
            
            card = f"""
            <div class="stock-card{' premium' if is_premium else ''}">
                <div class="stock-symbol">{symbol} {custom_badge}</div>
                <div class="stock-metrics">
                    <div class="metric">
                        <div class="metric-value">{float(total_return):.1f}%</div>
                        <div class="metric-label">総リターン</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{sharpe_ratio:.2f}</div>
                        <div class="metric-label">シャープレシオ</div>
                    </div>
                </div>
                <div class="signal {signal_class}">
                    {signal} (スコア: {float(score):.1f})
                </div>
                <div style="text-align: center; margin-top: 15px;">
                    <a href="individual_{symbol.replace('.', '_')}_swing_trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html" class="btn">
                        詳細分析
                    </a>
                </div>
            </div>
            """
            cards.append(card)
        
        return ''.join(cards)
    
    def generate_individual_report(self, symbol: str, backtest_result: Dict, archive_folder: str = None) -> str:
        """個別銘柄レポートを生成"""
        # アーカイブフォルダが指定されている場合は、そのフォルダ名からタイムスタンプを抽出
        if archive_folder:
            # フォルダ名から analysis_YYYYMMDD_HHMMSS の部分を抽出
            folder_name = os.path.basename(archive_folder)
            if folder_name.startswith('analysis_'):
                timestamp = folder_name.replace('analysis_', '')
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        filename = f"individual_{symbol.replace('.', '_')}_swing_trading_{timestamp}.html"
        
        # アーカイブフォルダが指定されている場合はそこに保存
        if archive_folder:
            filepath = os.path.join(archive_folder, filename)
        else:
            filepath = os.path.join(self.reports_dir, filename)
        
        performance = backtest_result.get('performance', {})
        ai_comment = backtest_result.get('ai_comment', '')
        data = backtest_result.get('data', pd.DataFrame())
        
        # チャート生成
        from report_generator_chart import generate_individual_chart
        chart_html = generate_individual_chart(symbol, data, backtest_result, self.config)
        
        # f-stringの問題を回避するため、文字列テンプレートを使用
        html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} 個別分析レポート</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 20px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .ai-comment {{
            background: #f8f9fa;
            border-left: 4px solid #28a745;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .section {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        .signal-strong-buy {{ background: #d4edda; color: #155724; padding: 4px 8px; border-radius: 4px; }}
        .signal-buy {{ background: #c8e6c9; color: #2e7d32; padding: 4px 8px; border-radius: 4px; }}
        .signal-neutral {{ background: #e2e3e5; color: #383d41; padding: 4px 8px; border-radius: 4px; }}
        .signal-sell {{ background: #ffcdd2; color: #c62828; padding: 4px 8px; border-radius: 4px; }}
        .signal-strong-sell {{ background: #f5c6cb; color: #721c24; padding: 4px 8px; border-radius: 4px; }}
        .info-icon {{
            cursor: pointer;
            margin-left: 8px;
            font-size: 0.8em;
            opacity: 0.7;
            transition: opacity 0.3s;
        }}
        .info-icon:hover {{
            opacity: 1;
        }}
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }}
        .modal-content {{
            background-color: #fefefe;
            margin: 5% auto;
            padding: 20px;
            border-radius: 10px;
            width: 80%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
        }}
        .close {{
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }}
        .close:hover {{
            color: black;
        }}
        .signal-explanation {{
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
        }}
        .signal-explanation h4 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
        }}
        .signal-explanation p {{
            margin: 5px 0;
            line-height: 1.6;
        }}
        .buy-section {{
            background: #f0f8ff;
            border-left: 4px solid #27ae60;
        }}
        .sell-section {{
            background: #fff5f5;
            border-left: 4px solid #e74c3c;
        }}
        .filter-section {{
            background: #fff8dc;
            border-left: 4px solid #ffa500;
        }}
        .annotations {{
            margin-top: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #6c757d;
        }}
        .annotation-item {{
            color: #6c757d;
            font-size: 0.9em;
            margin: 5px 0;
        }}
        .condition-info-icon {{
            cursor: pointer;
            font-size: 0.7em;
            opacity: 0.7;
            transition: opacity 0.3s;
        }}
        .condition-info-icon:hover {{
            opacity: 1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {symbol} 個別分析レポート</h1>
            <p>生成日時: """ + datetime.now().strftime('%Y年%m月%d日 %H:%M:%S') + """</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>{total_return:.1f}%</h3>
                <p>総リターン</p>
            </div>
            <div class="metric-card">
                <h3>{sharpe_ratio:.2f}</h3>
                <p>シャープレシオ</p>
            </div>
            <div class="metric-card">
                <h3>{max_drawdown:.1f}%</h3>
                <p>最大ドローダウン</p>
            </div>
            <div class="metric-card">
                <h3>{data_points}</h3>
                <p>取引数</p>
            </div>
        </div>
        
        <div class="ai-comment">
            <h3>🤖 AI分析コメント</h3>
            <p>{ai_comment}</p>
        </div>
        
        <div class="section">
            <h3>📈 価格チャートとシグナル</h3>
            {chart_html}
        </div>
        
        <div class="section">
            <h3>📊 パフォーマンス評価</h3>
            <p>リスク調整後リターンとリスク指標</p>
        </div>
        
        <div class="section">
            <h3>🎯 シグナル判定</h3>
            <p>現在のシグナル: <strong class="signal-{signal_class}">{latest_signal}</strong></p>
            <p>スコア: <strong>{latest_score:.1f}</strong></p>
            
            <div style="margin-top: 20px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <!-- 買い条件 -->
                    <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; border-left: 4px solid #27ae60;">
                        <h4 style="margin: 0 0 10px 0; color: #27ae60;">🟢 買い条件 (スコア: {buy_score_total})</h4>
                        <div style="max-height: 300px; overflow-y: auto;">
                            {buy_conditions_html}
                        </div>
                    </div>
                    
                    <!-- 売り条件 -->
                    <div style="background: #fff5f5; padding: 15px; border-radius: 8px; border-left: 4px solid #e74c3c;">
                        <h4 style="margin: 0 0 10px 0; color: #e74c3c;">🔴 売り条件 (スコア: {sell_score_total})</h4>
                        <div style="max-height: 300px; overflow-y: auto;">
                            {sell_conditions_html}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 注釈表示 -->
            {annotations_html}
        </div>
        
        <div class="section">
            <h3>💰 価格情報</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                    <h4 style="margin: 0 0 5px 0; color: #2c3e50;">買い価格</h4>
                    <p style="margin: 0; font-size: 1.2em; font-weight: bold; color: #27ae60;">
                        {buy_price}
                    </p>
                </div>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                    <h4 style="margin: 0 0 5px 0; color: #2c3e50;">売り価格</h4>
                    <p style="margin: 0; font-size: 1.2em; font-weight: bold; color: #e74c3c;">
                        {sell_price}
                    </p>
                </div>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                    <h4 style="margin: 0 0 5px 0; color: #2c3e50;">現在価格</h4>
                    <p style="margin: 0; font-size: 1.2em; font-weight: bold; color: #3498db;">
                        {current_price}
                    </p>
                </div>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                    <h4 style="margin: 0 0 5px 0; color: #2c3e50;">価格変動</h4>
                    <p style="margin: 0; font-size: 1.2em; font-weight: bold; color: #3498db;">
                        {price_change}
                    </p>
                </div>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 40px;">
            <a href="swing_trading_stocks_{timestamp}.html" class="btn">📋 銘柄一覧に戻る</a>
            <a href="swing_trading_{timestamp}.html" class="btn" style="margin-left: 10px;">📊 メインレポートに戻る</a>
            <a href="../../index.html" class="btn" style="margin-left: 10px;">🏠 ダッシュボードに戻る</a>
        </div>
    </div>
    
    <!-- 条件詳細説明モーダル -->
    <div id="conditionModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeConditionModal()">&times;</span>
            <h2 id="conditionModalTitle">📊 条件詳細説明</h2>
            <div id="conditionModalContent">
                <!-- 条件ごとの説明が動的に挿入される -->
            </div>
        </div>
    </div>
    
    <script>
        const conditionExplanations = {{
            'ゴールデンクロス＋傾き確認': {{
                title: '🟢 ゴールデンクロス＋傾き確認（2点）',
                content: `
                    <div class="signal-explanation buy-section">
                        <h4>👉 条件</h4>
                        <p>短期線（25日平均）が長期線（50日平均）を上に抜けて、しかも両方が上向き。</p>
                        
                        <h4>→ 意味</h4>
                        <p>「株価の流れが本格的に上昇に転じた」サイン。</p>
                        
                        <h4>⚠️ 注意点</h4>
                        <p>ゴールデンクロスは「だまし」が多いので、線が横ばいでなく上向きを条件に加えて精度を上げている。</p>
                    </div>
                `
            }},
            '出来高継続増加': {{
                title: '🟢 出来高継続増加（1点）',
                content: `
                    <div class="signal-explanation buy-section">
                        <h4>👉 条件</h4>
                        <p>出来高が平均より20%以上多い状態が2日続く。</p>
                        
                        <h4>→ 意味</h4>
                        <p>「買い手が本気で集まってきた」証拠。</p>
                        
                        <h4>⚠️ 注意点</h4>
                        <p>1日だけの増加は仕掛けやフェイクの場合があるので、連続していることがポイント。</p>
                    </div>
                `
            }},
            'RSI狭域レンジ': {{
                title: '🟢 RSI狭域レンジ（1点）',
                content: `
                    <div class="signal-explanation buy-section">
                        <h4>👉 条件</h4>
                        <p>RSIが45〜55の範囲。</p>
                        
                        <h4>→ 意味</h4>
                        <p>「売られすぎでもなく、買われすぎでもない」ちょうど中立の位置。</p>
                        
                        <h4>⚠️ 注意点</h4>
                        <p>ここから大きく動くことが多く、反発やトレンド開始の予兆になりやすい。</p>
                    </div>
                `
            }},
            'MACD強気判定': {{
                title: '🟢 MACD強気判定（1点）',
                content: `
                    <div class="signal-explanation buy-section">
                        <h4>👉 条件</h4>
                        <p>MACDがシグナルより上、かつ0より上。</p>
                        
                        <h4>→ 意味</h4>
                        <p>「勢いがプラス圏で上向き」＝本物の上昇トレンドに乗っているサイン。</p>
                        
                        <h4>⚠️ 注意点</h4>
                        <p>単にシグナルを超えただけより、信頼度が高い。</p>
                    </div>
                `
            }},
            'デッドクロス＋傾き確認': {{
                title: '🔴 デッドクロス＋傾き確認（2点）',
                content: `
                    <div class="signal-explanation sell-section">
                        <h4>👉 条件</h4>
                        <p>短期線（25日）が長期線（50日）を下に割り込み、両方が下向き。</p>
                        
                        <h4>→ 意味</h4>
                        <p>「下落トレンドが本格化した」サイン。</p>
                        
                        <h4>⚠️ 注意点</h4>
                        <p>ただのクロスだけではなく、傾きが下向きであることが重要。</p>
                    </div>
                `
            }},
            '出来高伴う陰線': {{
                title: '🔴 出来高伴う陰線（1点）',
                content: `
                    <div class="signal-explanation sell-section">
                        <h4>👉 条件</h4>
                        <p>終値が始値より低く、しかも出来高が急増。</p>
                        
                        <h4>→ 意味</h4>
                        <p>「投げ売りが出た」可能性が高く、売り圧力が強まっている。</p>
                    </div>
                `
            }},
            'RSI過熱': {{
                title: '🔴 RSI過熱（1点）',
                content: `
                    <div class="signal-explanation sell-section">
                        <h4>👉 条件</h4>
                        <p>RSIが70以上。</p>
                        
                        <h4>→ 意味</h4>
                        <p>「買われすぎて、そろそろ一服」しやすい状態。</p>
                        
                        <h4>⚠️ 注意点</h4>
                        <p>利確売りが出やすいタイミング。</p>
                    </div>
                `
            }},
            'MACD弱気判定': {{
                title: '🔴 MACD弱気判定（1点）',
                content: `
                    <div class="signal-explanation sell-section">
                        <h4>👉 条件</h4>
                        <p>MACDがシグナルより下、かつ0より下。</p>
                        
                        <h4>→ 意味</h4>
                        <p>「下落の勢いが本格的にマイナス圏に入った」状態。</p>
                        
                        <h4>⚠️ 注意点</h4>
                        <p>短期的な下げでなく、トレンド転換の可能性。</p>
                    </div>
                `
            }}
        }};
        
        function showConditionModal(conditionName) {{
            const explanation = conditionExplanations[conditionName];
            if (explanation) {{
                document.getElementById('conditionModalTitle').innerHTML = explanation.title;
                document.getElementById('conditionModalContent').innerHTML = explanation.content;
                document.getElementById('conditionModal').style.display = 'block';
            }}
        }}
        
        function closeConditionModal() {{
            document.getElementById('conditionModal').style.display = 'none';
        }}
        
        // モーダル外クリックで閉じる
        window.onclick = function(event) {{
            var modal = document.getElementById('conditionModal');
            if (event.target == modal) {{
                modal.style.display = 'none';
            }}
        }}
    </script>
</body>
</html>
        """
        
        # 変数を事前に計算
        total_return = float(performance.get('total_return', 0))
        sharpe_ratio = float(performance.get('sharpe_ratio', 0))
        max_drawdown = float(performance.get('max_drawdown', 0))
        latest_score = float(performance.get('latest_score', 0))
        latest_signal = performance.get('latest_signal', 'N/A')
        data_points = performance.get('data_points', 0)
        
        # データ関連の計算
        buy_price = float(data['close'].iloc[0]) if not data.empty else 0
        sell_price = float(data['close'].iloc[-1]) if not data.empty else 0
        current_price = sell_price  # 現在価格は最新の価格
        price_change = float((data['close'].iloc[-1] - data['close'].iloc[0]) / data['close'].iloc[0] * 100) if not data.empty else 0
        
        # 価格表示用の文字列を準備
        buy_price_display = f"{buy_price:.2f}" if not data.empty else "-"
        sell_price_display = f"{sell_price:.2f}" if not data.empty else "-"
        current_price_display = f"{current_price:.2f}" if not data.empty else "-"
        price_change_display = f"{price_change:.2f}%" if not data.empty else "-"
        
        # シグナル条件詳細の取得とHTML生成
        signal_conditions = backtest_result.get('signal_conditions', {})
        buy_conditions_html = self.generate_conditions_html(signal_conditions.get('buy_conditions', []), 'buy')
        sell_conditions_html = self.generate_conditions_html(signal_conditions.get('sell_conditions', []), 'sell')
        buy_score_total = signal_conditions.get('total_buy_score', 0)
        sell_score_total = signal_conditions.get('total_sell_score', 0)
        annotations_html = self.generate_annotations_html(signal_conditions.get('annotations', []))
        
        # シグナルクラスを決定
        signal_class = 'neutral'
        if '強い買い' in latest_signal:
            signal_class = 'strong-buy'
        elif '買い' in latest_signal:
            signal_class = 'buy'
        elif '売り' in latest_signal:
            signal_class = 'sell'
        elif '強い売り' in latest_signal:
            signal_class = 'strong-sell'
        
        # 変数を置換
        html_content = html_content.format(
            symbol=symbol,
            ai_comment=ai_comment,
            chart_html=chart_html,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            data_points=data_points,
            latest_signal=latest_signal,
            latest_score=latest_score,
            buy_price=buy_price_display,
            sell_price=sell_price_display,
            current_price=current_price_display,
            price_change=price_change_display,
            data_empty=not data.empty,
            timestamp=timestamp,
            buy_conditions_html=buy_conditions_html,
            sell_conditions_html=sell_conditions_html,
            buy_score_total=buy_score_total,
            sell_score_total=sell_score_total,
            signal_class=signal_class,
            annotations_html=annotations_html
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def generate_conditions_html(self, conditions: List[Dict], condition_type: str) -> str:
        """条件の詳細をHTMLで生成"""
        if not conditions:
            return "<p style='color: #666; font-style: italic;'>条件データがありません</p>"
        
        html_parts = []
        for condition in conditions:
            met = condition.get('met', False)
            name = condition.get('name', '')
            description = condition.get('description', '')
            score = condition.get('score', 0)
            
            # アイコンと色を決定
            if met:
                icon = "✅"  # 買い・売り両方で✅マークを使用
                bg_color = "#e8f5e8" if condition_type == 'buy' else "#ffeaea"
                border_color = "#27ae60" if condition_type == 'buy' else "#e74c3c"
            else:
                icon = "⚪"
                bg_color = "#f8f9fa"
                border_color = "#ddd"
            
            # JavaScript用に条件名をエスケープ
            escaped_name = name.replace("'", "\\'")
            html_parts.append(f"""
                <div style="
                    background: {bg_color}; 
                    border: 1px solid {border_color}; 
                    border-radius: 6px; 
                    padding: 8px; 
                    margin: 5px 0;
                    font-size: 0.9em;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: bold;">{icon} {name}: {description}</span>
                        <div style="display: flex; align-items: center; gap: 5px;">
                            <span style="color: #666; font-size: 0.8em;">+{score}</span>
                            <span class="condition-info-icon" onclick="showConditionModal('{escaped_name}')" title="条件詳細説明">ℹ️</span>
                        </div>
                    </div>
                </div>
            """)
        
        return "".join(html_parts)
    
    def generate_annotations_html(self, annotations: List[Dict]) -> str:
        """注釈をHTMLで生成"""
        if not annotations:
            return ""
        
        html_parts = []
        for annotation in annotations:
            html_parts.append(f"""
                <div class="annotation-item">
                    {annotation.get('message', '')}
                </div>
            """)
        
        return f"""
        <div class="annotations">
            <h4 style="margin: 0 0 10px 0; color: #6c757d;">📝 注釈</h4>
            {"".join(html_parts)}
        </div>
        """
