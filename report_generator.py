"""
レポート生成モジュール
"""

import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import json
from typing import Dict, List
import logging
import pytz

from config import REPORT_DIR, REPORT_TEMPLATES, TRADING_RULES

class ReportGenerator:
    """レポート生成クラス"""
    
    def __init__(self):
        self.report_dir = REPORT_DIR
        self.logger = logging.getLogger(__name__)
        self._ensure_report_dir()
    
    def _get_jst_datetime(self) -> datetime:
        """
        現在の日本時間を取得
        
        Returns:
            datetime: 日本時間の現在日時
        """
        utc_now = datetime.now(pytz.UTC)
        jst = pytz.timezone('Asia/Tokyo')
        return utc_now.astimezone(jst)
    
    def _get_jst_timestamp(self) -> str:
        """
        日本時間のタイムスタンプ文字列を取得
        
        Returns:
            str: 日本時間のタイムスタンプ（YYYYMMDD_HHMMSS形式）
        """
        return self._get_jst_datetime().strftime("%Y%m%d_%H%M%S")
    
    def _get_jst_datetime_str(self) -> str:
        """
        日本時間の日時文字列を取得
        
        Returns:
            str: 日本時間の日時（YYYY年MM月DD日 HH:MM:SS形式）
        """
        return self._get_jst_datetime().strftime('%Y年%m月%d日 %H:%M:%S')
    
    def _ensure_report_dir(self):
        """レポートディレクトリの作成"""
        os.makedirs(self.report_dir, exist_ok=True)
        os.makedirs(os.path.join(self.report_dir, "assets"), exist_ok=True)
    
    def _get_strategy_conditions(self, strategy_name: str) -> Dict:
        """
        戦略の条件を取得
        
        Args:
            strategy_name: 戦略名
        
        Returns:
            Dict: 戦略条件
        """
        # 戦略名からキーを特定
        strategy_key = None
        for key, value in TRADING_RULES.items():
            if value["name"] == strategy_name:
                strategy_key = key
                break
        
        if not strategy_key:
            return {}
        
        return TRADING_RULES[strategy_key]
    
    def _translate_condition_name(self, condition_name: str) -> str:
        """
        条件名を日本語に変換
        
        Args:
            condition_name: 条件名
        
        Returns:
            str: 日本語の条件名
        """
        translations = {
            'timeframe': '時間足',
            'max_holding_days': '最大保有日数',
            'max_positions': '最大ポジション数',
            'risk_per_trade': '取引リスク',
            'max_position_size': '最大ポジションサイズ',
            'golden_cross': 'ゴールデンクロス',
            'rsi_range': 'RSI範囲',
            'volume_multiplier': '出来高倍率',
            'new_high_preference': '新高値優先',
            'above_ma200': '200日線上',
            'fundamental_growth': 'ファンダメンタル成長',
            'volume_new_high': '出来高新高値',
            'macro_environment': 'マクロ環境',
            'profit_target': '利益目標',
            'stop_loss': '損切り',
            'rsi_overbought': 'RSI過買い',
            'below_ma25': '25日線下',
            'partial_profit': '部分利確',
            'below_ma200': '200日線下',
            'fundamental_divergence': 'ファンダメンタル乖離',
            'enabled': '有効',
            'first_target': '第1目標',
            'second_target': '第2目標'
        }
        
        return translations.get(condition_name, condition_name)
    
    def _generate_strategy_conditions_html(self, strategy_conditions: Dict) -> str:
        """
        戦略条件のHTML生成
        
        Args:
            strategy_conditions: 戦略条件
        
        Returns:
            str: HTML文字列
        """
        if not strategy_conditions:
            return "<p>戦略条件が見つかりませんでした。</p>"
        
        html = f"""
        <div class="strategy-conditions">
            <h3>📋 戦略条件</h3>
            <div class="conditions-grid">
                <div class="condition-section">
                    <h4>🕒 基本設定</h4>
                    <ul>
                        <li><strong>{self._translate_condition_name('timeframe')}:</strong> {strategy_conditions.get('timeframe', 'N/A')}</li>
                        <li><strong>{self._translate_condition_name('max_holding_days')}:</strong> {strategy_conditions.get('max_holding_days', 'N/A')}日</li>
                        <li><strong>{self._translate_condition_name('max_positions')}:</strong> {strategy_conditions.get('max_positions', 'N/A')}銘柄</li>
                        <li><strong>{self._translate_condition_name('risk_per_trade')}:</strong> {strategy_conditions.get('risk_per_trade', 0)*100:.1f}%</li>
                        <li><strong>{self._translate_condition_name('max_position_size')}:</strong> {strategy_conditions.get('max_position_size', 0)*100:.1f}%</li>
                    </ul>
                </div>
        """
        
        # エントリー条件
        entry_conditions = strategy_conditions.get('entry_conditions', {})
        if entry_conditions:
            html += """
                <div class="condition-section">
                    <h4>📈 エントリー条件</h4>
                    <ul>
            """
            for condition, value in entry_conditions.items():
                translated_condition = self._translate_condition_name(condition)
                if isinstance(value, bool):
                    status = "✅ 有効" if value else "❌ 無効"
                    html += f"<li><strong>{translated_condition}:</strong> {status}</li>"
                elif isinstance(value, tuple):
                    html += f"<li><strong>{translated_condition}:</strong> {value[0]}〜{value[1]}</li>"
                else:
                    html += f"<li><strong>{translated_condition}:</strong> {value}</li>"
            html += "</ul></div>"
        
        # エグジット条件
        exit_conditions = strategy_conditions.get('exit_conditions', {})
        if exit_conditions:
            html += """
                <div class="condition-section">
                    <h4>📉 エグジット条件</h4>
                    <ul>
            """
            for condition, value in exit_conditions.items():
                translated_condition = self._translate_condition_name(condition)
                if isinstance(value, bool):
                    status = "✅ 有効" if value else "❌ 無効"
                    html += f"<li><strong>{translated_condition}:</strong> {status}</li>"
                elif isinstance(value, dict):
                    # 部分利確などの複雑な条件
                    html += f"<li><strong>{translated_condition}:</strong>"
                    for sub_key, sub_value in value.items():
                        translated_sub_key = self._translate_condition_name(sub_key)
                        if isinstance(sub_value, bool):
                            status = "✅ 有効" if sub_value else "❌ 無効"
                            html += f" {translated_sub_key}: {status}"
                        else:
                            html += f" {translated_sub_key}: {sub_value}"
                    html += "</li>"
                else:
                    html += f"<li><strong>{translated_condition}:</strong> {value}</li>"
            html += "</ul></div>"
        
        html += """
            </div>
        </div>
        """
        
        return html
    
    def generate_stocks_list_report(self, stocks: List[str], strategy_name: str, random_seed: int) -> str:
        """
        対象銘柄一覧レポートの生成
        
        Args:
            stocks: 銘柄リスト
            strategy_name: 戦略名
            random_seed: 乱数シード
        
        Returns:
            str: レポートファイルパス
        """
        # 銘柄を指数別に分類
        stocks_by_index = self._categorize_stocks_by_index(stocks)
        
        # HTMLレポートの生成
        html_content = self._generate_stocks_list_html(stocks_by_index, strategy_name, random_seed)
        
        # ファイル保存
        timestamp = self._get_jst_timestamp()
        filename = f"{strategy_name}_{timestamp}.html"
        filepath = os.path.join(self.report_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"銘柄一覧レポート生成完了: {filepath}")
        return filepath
    
    def _categorize_stocks_by_index(self, stocks: List[str]) -> Dict[str, List[str]]:
        """
        銘柄を指数別に分類
        
        Args:
            stocks: 銘柄リスト
        
        Returns:
            Dict[str, List[str]]: 指数別銘柄リスト
        """
        stocks_by_index = {
            "SP500": [],
            "NASDAQ100": [],
            "NIKKEI225": []
        }
        
        # index_stocks.csvから正確な分類を取得
        try:
            import pandas as pd
            stocks_df = pd.read_csv("index_stocks.csv")
            
            for stock in stocks:
                stock_info = stocks_df[stocks_df['symbol'] == stock]
                if not stock_info.empty:
                    index_name = stock_info.iloc[0]['index']
                    if index_name in stocks_by_index:
                        stocks_by_index[index_name].append(stock)
                    else:
                        # 分類できない場合は、.Tで終わるかどうかで判断
                        if stock.endswith('.T'):
                            stocks_by_index["NIKKEI225"].append(stock)
                        else:
                            stocks_by_index["SP500"].append(stock)
                else:
                    # CSVにない場合は、.Tで終わるかどうかで判断
                    if stock.endswith('.T'):
                        stocks_by_index["NIKKEI225"].append(stock)
                    else:
                        stocks_by_index["SP500"].append(stock)
        except Exception as e:
            # CSV読み込みエラーの場合は、簡易分類
            for stock in stocks:
                if stock.endswith('.T'):
                    stocks_by_index["NIKKEI225"].append(stock)
                else:
                    stocks_by_index["SP500"].append(stock)
        
        return stocks_by_index
    
    def _generate_stocks_list_html(self, stocks_by_index: Dict[str, List[str]], 
                                  strategy_name: str, random_seed: int) -> str:
        """
        銘柄一覧HTMLの生成
        
        Args:
            stocks_by_index: 指数別銘柄リスト
            strategy_name: 戦略名
            random_seed: 乱数シード
        
        Returns:
            str: HTML文字列
        """
        total_stocks = sum(len(stocks) for stocks in stocks_by_index.values())
        
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>対象銘柄一覧 - {strategy_name}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #2d3748;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            color: white;
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="white" opacity="0.1"/><circle cx="75" cy="75" r="1" fill="white" opacity="0.1"/><circle cx="50" cy="10" r="0.5" fill="white" opacity="0.1"/><circle cx="10" cy="60" r="0.5" fill="white" opacity="0.1"/><circle cx="90" cy="40" r="0.5" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
            opacity: 0.3;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 10px;
            position: relative;
            z-index: 1;
        }}
        
        .header h2 {{
            font-size: 1.5em;
            font-weight: 500;
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }}
        
        .header p {{
            font-size: 1em;
            opacity: 0.8;
            margin-top: 10px;
            position: relative;
            z-index: 1;
        }}
        
        .summary {{
            background: linear-gradient(135deg, #e0f2fe 0%, #b3e5fc 100%);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 40px;
            text-align: center;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
        }}
        
        .summary h3 {{
            color: #0277bd;
            margin-top: 0;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}
        
        .summary h3::before {{
            content: '📊';
            font-size: 1.2em;
        }}
        
        .index-section {{
            margin: 40px 0;
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            padding: 30px;
            border-radius: 15px;
            border-left: 5px solid #22c55e;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
        }}
        
        .index-section h3 {{
            color: #15803d;
            margin-top: 0;
            margin-bottom: 20px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .index-section h3::before {{
            content: '📈';
            font-size: 1.2em;
        }}
        
        .stocks-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 15px;
        }}
        
        .stock-item {{
            background: rgba(255, 255, 255, 0.9);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid rgba(34, 197, 94, 0.2);
            text-align: center;
            font-weight: 600;
            color: #374151;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}
        
        .stock-item::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(34, 197, 94, 0.1), transparent);
            transition: left 0.5s;
        }}
        
        .stock-item:hover::before {{
            left: 100%;
        }}
        
        .stock-item:hover {{
            background: rgba(255, 255, 255, 1);
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 10px 25px rgba(34, 197, 94, 0.2);
            border-color: #22c55e;
        }}
        
        .back-link {{
            text-align: center;
            margin-top: 40px;
        }}
        
        .back-link a {{
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 1.1em;
            transition: all 0.3s ease;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }}
        
        .back-link a:hover {{
            transform: translateY(-2px);
            box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
        }}
        
        /* レスポンシブデザイン */
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .container {{
                padding: 20px;
                border-radius: 15px;
            }}
            
            .header {{
                padding: 20px 0;
                margin-bottom: 30px;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
            
            .header h2 {{
                font-size: 1.3em;
            }}
            
            .stocks-grid {{
                grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                gap: 10px;
            }}
            
            .stock-item {{
                padding: 12px;
                font-size: 0.9em;
            }}
        }}
        
        @media (max-width: 480px) {{
            .stocks-grid {{
                grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            }}
            
            .header h1 {{
                font-size: 1.8em;
            }}
            
            .header h2 {{
                font-size: 1.2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 対象銘柄一覧</h1>
            <h2>{strategy_name}</h2>
            <p>生成日時: {self._get_jst_datetime_str()}</p>
        </div>
        
        <div class="summary">
            <h3>📊 銘柄構成サマリー</h3>
            <p><strong>総銘柄数:</strong> {total_stocks}銘柄</p>
            <p><strong>乱数シード:</strong> {random_seed}</p>
            <p><strong>戦略:</strong> {strategy_name}</p>
        </div>
"""
        
        # 各指数の銘柄一覧
        for index_name, stocks in stocks_by_index.items():
            if stocks:  # 空でない場合のみ表示
                html_content += f"""
        <div class="index-section">
            <h3>📈 {index_name} ({len(stocks)}銘柄)</h3>
            <div class="stocks-grid">
"""
                for stock in stocks:
                    html_content += f'                <div class="stock-item">{stock}</div>\n'
                
                html_content += """
            </div>
        </div>
"""
        
        html_content += """
        <div class="back-link">
            <a href="javascript:history.back()">← バックテスト結果に戻る</a>
        </div>
    </div>
</body>
</html>
        """
        
        return html_content
    
    def generate_strategy_report(self, results: Dict, strategy_name: str, 
                               stocks: List[str] = None, random_seed: int = None) -> str:
        """
        戦略別レポートの生成
        
        Args:
            results: バックテスト結果
            strategy_name: 戦略名
            stocks: 使用銘柄リスト
            random_seed: 乱数シード
        
        Returns:
            str: レポートファイルパス
        """
        if "error" in results:
            self.logger.error(f"レポート生成エラー: {results['error']}")
            return ""
        
        # 銘柄一覧レポートの生成（stocksとrandom_seedが提供されている場合）
        stocks_report_path = ""
        if stocks and random_seed is not None:
            stocks_report_path = self.generate_stocks_list_report(stocks, strategy_name, random_seed)
        
        # チャートの生成
        charts = self._generate_charts(results)
        
        # HTMLレポートの生成（銘柄一覧レポートのパスを渡す）
        html_content = self._generate_html_report(results, strategy_name, charts, stocks, random_seed, stocks_report_path)
        
        # ファイル保存
        timestamp = self._get_jst_timestamp()
        filename = f"{strategy_name}_{timestamp}.html"
        filepath = os.path.join(self.report_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"レポート生成完了: {filepath}")
        return filepath
    
    def _generate_charts(self, results: Dict) -> Dict[str, str]:
        """チャートの生成"""
        charts = {}
        
        # 共通の日付範囲を取得
        date_range = self._get_common_date_range(results)
        
        # エクイティカーブ
        if "equity_curve" in results:
            charts["equity_curve"] = self._create_equity_chart(results["equity_curve"], date_range)
        
        # 取引履歴
        if "trades" in results:
            charts["trades"] = self._create_trades_chart(results["trades"], date_range)
        
        # 月次リターン
        charts["monthly_returns"] = self._create_monthly_returns_chart(results, date_range)
        
        # ドローダウン
        if "equity_curve" in results:
            charts["drawdown"] = self._create_drawdown_chart(results["equity_curve"], date_range)
        
        # VIXチャート
        if "vix_data" in results and results["vix_data"]:
            charts["vix"] = self._create_vix_chart(results["vix_data"], date_range)
        
        return charts
    
    def _get_common_date_range(self, results: Dict) -> Dict:
        """
        全チャートで使用する共通の日付範囲を取得
        
        Args:
            results: バックテスト結果
        
        Returns:
            Dict: 日付範囲情報
        """
        date_ranges = []
        
        # エクイティカーブの日付範囲
        if "equity_curve" in results and results["equity_curve"]:
            equity_dates = results["equity_curve"]["dates"]
            if equity_dates:
                date_ranges.append((equity_dates[0], equity_dates[-1]))
        
        # VIXデータの日付範囲
        if "vix_data" in results and results["vix_data"] and "dates" in results["vix_data"]:
            vix_dates = results["vix_data"]["dates"]
            if vix_dates:
                date_ranges.append((vix_dates[0], vix_dates[-1]))
        
        # 取引履歴の日付範囲
        if "trades" in results and results["trades"]:
            trade_dates = []
            for trade in results["trades"]:
                if "entry_date" in trade:
                    trade_dates.append(trade["entry_date"])
                if "exit_date" in trade:
                    trade_dates.append(trade["exit_date"])
            if trade_dates:
                trade_dates.sort()
                date_ranges.append((trade_dates[0], trade_dates[-1]))
        
        if not date_ranges:
            return {"start": None, "end": None}
        
        # 全範囲の開始日と終了日を取得
        start_dates = [pd.to_datetime(dr[0]) for dr in date_ranges]
        end_dates = [pd.to_datetime(dr[1]) for dr in date_ranges]
        
        # 最も早い開始日と最も遅い終了日
        common_start = min(start_dates).strftime('%Y-%m-%d')
        common_end = max(end_dates).strftime('%Y-%m-%d')
        
        return {
            "start": common_start,
            "end": common_end,
            "start_date": pd.to_datetime(common_start),
            "end_date": pd.to_datetime(common_end)
        }
    
    def _create_equity_chart(self, equity_data: Dict, date_range: Dict = None) -> str:
        """エクイティカーブチャート"""
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=equity_data["dates"],
            y=equity_data["values"],
            mode='lines',
            name='ポートフォリオ価値',
            line=dict(color='blue', width=2)
        ))
        
        # 共通の日付範囲を設定
        xaxis_config = {
            'title': '日付',
            'hoverformat': '%Y-%m-%d'
        }
        
        if date_range and date_range.get("start") and date_range.get("end"):
            xaxis_config['range'] = [date_range["start"], date_range["end"]]
        
        fig.update_layout(
            title='エクイティカーブ',
            xaxis=xaxis_config,
            yaxis_title='ポートフォリオ価値 (円)',
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def _create_vix_chart(self, vix_data: Dict, date_range: Dict = None) -> str:
        """VIXチャート"""
        fig = go.Figure()
        
        # VIXライン
        fig.add_trace(go.Scatter(
            x=vix_data["dates"],
            y=vix_data["values"],
            mode='lines',
            name='VIX',
            line=dict(color='red', width=2)
        ))
        
        # 高ボラティリティ閾値ライン
        fig.add_hline(y=30, line_dash="dash", line_color="orange", 
                      annotation_text="高ボラティリティ (VIX > 30)")
        fig.add_hline(y=50, line_dash="dash", line_color="red", 
                      annotation_text="極端ボラティリティ (VIX > 50)")
        
        # 高ボラティリティ期間をハイライト
        if "high_volatility_periods" in vix_data:
            for period in vix_data["high_volatility_periods"]:
                fig.add_vline(x=period["date"], line_dash="dot", 
                              line_color="red", opacity=0.3)
        
        # 共通の日付範囲を設定
        xaxis_config = {
            'title': '日付',
            'hoverformat': '%Y-%m-%d'
        }
        
        if date_range and date_range.get("start") and date_range.get("end"):
            xaxis_config['range'] = [date_range["start"], date_range["end"]]
        
        fig.update_layout(
            title='VIX（恐怖指数）',
            xaxis=xaxis_config,
            yaxis_title='VIX',
            hovermode='x unified',
            template='plotly_white',
            height=400
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def _create_trades_chart(self, trades: List[Dict], date_range: Dict = None) -> str:
        """取引履歴チャート（累積損益率）"""
        if not trades:
            return ""
        
        df = pd.DataFrame(trades)
        df['entry_date'] = pd.to_datetime(df['entry_date'])
        df['exit_date'] = pd.to_datetime(df['exit_date'])
        
        # 決済日でソート
        df = df.sort_values('exit_date')
        
        # 累積損益率を計算
        df['cumulative_profit'] = df['profit_loss_pct'].cumsum() * 100
        
        fig = go.Figure()
        
        # 利益取引の累積
        profit_trades = df[df['profit_loss'] > 0]
        if not profit_trades.empty:
            fig.add_trace(go.Scatter(
                x=profit_trades['exit_date'],
                y=profit_trades['cumulative_profit'],
                mode='lines+markers',
                name='利益取引',
                line=dict(color='green', width=2),
                marker=dict(color='green', size=6),
                hovertemplate='<b>%{x}</b><br>累積利益: %{y:.2f}%<extra></extra>'
            ))
        
        # 損失取引の累積
        loss_trades = df[df['profit_loss'] < 0]
        if not loss_trades.empty:
            fig.add_trace(go.Scatter(
                x=loss_trades['exit_date'],
                y=loss_trades['cumulative_profit'],
                mode='lines+markers',
                name='損失取引',
                line=dict(color='red', width=2),
                marker=dict(color='red', size=6),
                hovertemplate='<b>%{x}</b><br>累積損益: %{y:.2f}%<extra></extra>'
            ))
        
        # 共通の日付範囲を設定
        xaxis_config = {
            'title': '決済日',
            'hoverformat': '%Y-%m-%d'
        }
        
        if date_range and date_range.get("start") and date_range.get("end"):
            xaxis_config['range'] = [date_range["start"], date_range["end"]]
        
        fig.update_layout(
            title='取引履歴',
            xaxis=xaxis_config,
            yaxis_title='累積損益率 (%)',
            hovermode='closest',
            template='plotly_white'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def _create_monthly_returns_chart(self, results: Dict, date_range: Dict = None) -> str:
        """月次リターンチャート"""
        if "equity_curve" not in results:
            return ""
        
        equity_series = pd.Series(
            results["equity_curve"]["values"],
            index=pd.to_datetime(results["equity_curve"]["dates"])
        )
        
        monthly_returns = equity_series.resample('M').last().pct_change().dropna()
        
        fig = go.Figure()
        
        colors = ['green' if x > 0 else 'red' for x in monthly_returns]
        
        fig.add_trace(go.Bar(
            x=monthly_returns.index,
            y=monthly_returns.values * 100,
            marker_color=colors,
            name='月次リターン'
        ))
        
        # 共通の日付範囲を設定
        xaxis_config = {
            'title': '月',
            'hoverformat': '%Y-%m'
        }
        
        if date_range and date_range.get("start") and date_range.get("end"):
            xaxis_config['range'] = [date_range["start"], date_range["end"]]
        
        fig.update_layout(
            title='月次リターン',
            xaxis=xaxis_config,
            yaxis_title='リターン (%)',
            template='plotly_white'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def _create_drawdown_chart(self, equity_data: Dict, date_range: Dict = None) -> str:
        """ドローダウンチャート"""
        equity_series = pd.Series(
            equity_data["values"],
            index=pd.to_datetime(equity_data["dates"])
        )
        
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=drawdown.index,
            y=drawdown.values,
            fill='tonexty',
            fillcolor='rgba(255,0,0,0.3)',
            line=dict(color='red'),
            name='ドローダウン'
        ))
        
        # 共通の日付範囲を設定
        xaxis_config = {
            'title': '日付',
            'hoverformat': '%Y-%m-%d'
        }
        
        if date_range and date_range.get("start") and date_range.get("end"):
            xaxis_config['range'] = [date_range["start"], date_range["end"]]
        
        fig.update_layout(
            title='ドローダウン',
            xaxis=xaxis_config,
            yaxis_title='ドローダウン (%)',
            template='plotly_white'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def _generate_html_report(self, results: Dict, strategy_name: str, charts: Dict[str, str], 
                            stocks: List[str] = None, random_seed: int = None, stocks_report_path: str = "") -> str:
        """HTMLレポートの生成"""
        # 基本統計の計算
        stats = self._calculate_statistics(results)
        
        # 戦略条件の取得
        strategy_conditions = self._get_strategy_conditions(strategy_name)
        strategy_conditions_html = self._generate_strategy_conditions_html(strategy_conditions)
        
        # 銘柄一覧へのリンク生成
        stocks_link_html = ""
        if stocks_report_path:
            # 実際に生成された銘柄一覧レポートのファイル名を取得
            stocks_filename = os.path.basename(stocks_report_path)
            stocks_link_html = f"""
        <div class="stocks-link">
            <a href="{stocks_filename}" target="_blank" class="stocks-link-btn">
                📋 対象銘柄一覧を確認 ({len(stocks)}銘柄)
            </a>
        </div>
"""
        
        # AI分析コメント
        ai_analysis = self._generate_ai_analysis(results, strategy_name)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>バックテスト結果 - {strategy_name}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #2d3748;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            color: white;
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="white" opacity="0.1"/><circle cx="75" cy="75" r="1" fill="white" opacity="0.1"/><circle cx="50" cy="10" r="0.5" fill="white" opacity="0.1"/><circle cx="10" cy="60" r="0.5" fill="white" opacity="0.1"/><circle cx="90" cy="40" r="0.5" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
            opacity: 0.3;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 10px;
            position: relative;
            z-index: 1;
        }}
        
        .header h2 {{
            font-size: 1.5em;
            font-weight: 500;
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }}
        
        .header p {{
            font-size: 1em;
            opacity: 0.8;
            margin-top: 10px;
            position: relative;
            z-index: 1;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }}
        
        .stat-card:hover::before {{
            left: 100%;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 20px 40px rgba(102, 126, 234, 0.3);
        }}
        
        .stat-value {{
            font-size: 2.2em;
            font-weight: 700;
            margin-bottom: 8px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .stat-label {{
            font-size: 0.95em;
            opacity: 0.9;
            font-weight: 500;
        }}
        
        .info-icon {{
            font-size: 0.8em;
            margin-left: 8px;
            opacity: 0.7;
            cursor: help;
            transition: opacity 0.2s ease;
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
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(5px);
            animation: fadeIn 0.3s ease;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        .modal-content {{
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            margin: 3% auto;
            padding: 40px;
            border-radius: 20px;
            width: 85%;
            max-width: 700px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
            position: relative;
            border: 1px solid rgba(255, 255, 255, 0.2);
            animation: slideIn 0.3s ease;
        }}
        
        @keyframes slideIn {{
            from {{ 
                transform: translateY(-50px);
                opacity: 0;
            }}
            to {{ 
                transform: translateY(0);
                opacity: 1;
            }}
        }}
        
        .close {{
            color: #94a3b8;
            float: right;
            font-size: 32px;
            font-weight: 300;
            position: absolute;
            right: 25px;
            top: 20px;
            cursor: pointer;
            transition: all 0.2s ease;
            line-height: 1;
        }}
        
        .close:hover {{
            color: #ef4444;
            transform: scale(1.1);
        }}
        
        .modal-title {{
            font-size: 1.8em;
            font-weight: 700;
            margin-bottom: 20px;
            color: #1e293b;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .modal-description {{
            font-size: 1.1em;
            line-height: 1.7;
            color: #475569;
            margin-bottom: 25px;
        }}
        
        .modal-formula {{
            background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
            padding: 20px;
            border-radius: 12px;
            border-left: 5px solid #667eea;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }}
        
        .modal-interpretation {{
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            padding: 20px;
            border-radius: 12px;
            border-left: 5px solid #22c55e;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }}
        
        .chart-section {{
            margin: 40px 0;
            background: rgba(255, 255, 255, 0.7);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}
        
        .chart-title {{
            font-size: 1.6em;
            margin-bottom: 20px;
            color: #1e293b;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .chart-title::before {{
            content: '📊';
            font-size: 1.2em;
        }}
        
        .ai-analysis {{
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            padding: 25px;
            border-radius: 15px;
            margin: 40px 0;
            border-left: 5px solid #f59e0b;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
        }}
        
        .ai-analysis h3 {{
            color: #92400e;
            margin-top: 0;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .ai-analysis h3::before {{
            content: '🤖';
            font-size: 1.1em;
        }}
        
        .trades-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
        }}
        
        .trades-table th, .trades-table td {{
            padding: 15px 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .trades-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        .trades-table tr:hover {{
            background-color: #f8fafc;
        }}
        
        .profit {{
            color: #16a34a;
            font-weight: 600;
        }}
        
        .loss {{
            color: #dc2626;
            font-weight: 600;
        }}
        .strategy-conditions {{
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            padding: 30px;
            border-radius: 15px;
            margin: 40px 0;
            border-left: 5px solid #22c55e;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
        }}
        
        .strategy-conditions h3 {{
            color: #15803d;
            margin-top: 0;
            margin-bottom: 25px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .strategy-conditions h3::before {{
            content: '⚙️';
            font-size: 1.2em;
        }}
        
        .conditions-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 25px;
        }}
        
        .condition-section {{
            background: rgba(255, 255, 255, 0.8);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid rgba(34, 197, 94, 0.2);
            transition: all 0.2s ease;
        }}
        
        .condition-section:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }}
        
        .condition-section h4 {{
            color: #1e293b;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.1em;
            font-weight: 600;
        }}
        
        .condition-section ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .condition-section li {{
            padding: 10px 0;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .condition-section li:last-child {{
            border-bottom: none;
        }}
        
        .condition-section strong {{
            color: #374151;
            font-weight: 600;
        }}
        
        .stocks-link {{
            text-align: center;
            margin: 30px 0;
        }}
        
        .stocks-link-btn {{
            display: inline-block;
            padding: 12px 24px;
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
            font-size: 1.1em;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);
        }}
        .stocks-link-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(40, 167, 69, 0.4);
            background: linear-gradient(135deg, #218838 0%, #1ea085 100%);
        }}
        
        /* レスポンシブデザイン */
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .container {{
                padding: 20px;
                border-radius: 15px;
            }}
            
            .header {{
                padding: 20px 0;
                margin-bottom: 30px;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
            
            .header h2 {{
                font-size: 1.3em;
            }}
            
            .stats-grid {{
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                padding: 20px;
            }}
            
            .stat-value {{
                font-size: 1.8em;
            }}
            
            .chart-section {{
                padding: 20px;
                margin: 30px 0;
            }}
            
            .chart-title {{
                font-size: 1.4em;
            }}
            
            .conditions-grid {{
                grid-template-columns: 1fr;
                gap: 20px;
            }}
            
            .modal-content {{
                width: 95%;
                margin: 5% auto;
                padding: 25px;
            }}
            
            .trades-table {{
                font-size: 0.9em;
            }}
            
            .trades-table th, .trades-table td {{
                padding: 10px 8px;
            }}
        }}
        
        @media (max-width: 480px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            
            .stat-value {{
                font-size: 1.6em;
            }}
            
            .header h1 {{
                font-size: 1.8em;
            }}
            
            .header h2 {{
                font-size: 1.2em;
            }}
        }}
        
        /* スクロールバーのスタイリング */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
        }}
        
        /* ローディングアニメーション */
        .loading {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }}
        
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        
        /* フローティングアクションボタン */
        .floating-btn {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            text-decoration: none;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
            transition: all 0.3s ease;
            z-index: 100;
        }}
        
        .floating-btn:hover {{
            transform: scale(1.1);
            box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>バックテスト結果レポート</h1>
            <h2>{strategy_name}</h2>
            <p>生成日時: {self._get_jst_datetime_str()}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card" onclick="showMetricModal('total_return')">
                <div class="stat-value">{stats['total_return_pct']:.2f}%</div>
                <div class="stat-label">総リターン <span class="info-icon">ℹ️</span></div>
            </div>
            <div class="stat-card" onclick="showMetricModal('sharpe_ratio')">
                <div class="stat-value">{stats['sharpe_ratio']:.2f}</div>
                <div class="stat-label">シャープレシオ <span class="info-icon">ℹ️</span></div>
            </div>
            <div class="stat-card" onclick="showMetricModal('max_drawdown')">
                <div class="stat-value">{stats['max_drawdown_pct']:.2f}%</div>
                <div class="stat-label">最大ドローダウン <span class="info-icon">ℹ️</span></div>
            </div>
            <div class="stat-card" onclick="showMetricModal('win_rate')">
                <div class="stat-value">{stats['win_rate_pct']:.1f}%</div>
                <div class="stat-label">勝率 <span class="info-icon">ℹ️</span></div>
            </div>
            <div class="stat-card" onclick="showMetricModal('total_trades')">
                <div class="stat-value">{stats['total_trades']}</div>
                <div class="stat-label">総取引数 <span class="info-icon">ℹ️</span></div>
            </div>
            <div class="stat-card" onclick="showMetricModal('profit_factor')">
                <div class="stat-value">{stats['profit_factor']:.2f}</div>
                <div class="stat-label">プロフィットファクター <span class="info-icon">ℹ️</span></div>
            </div>
        </div>
        
        {strategy_conditions_html}
        
        {stocks_link_html}
        
        <div class="ai-analysis">
            <h3>🤖 AI分析・評価</h3>
            {ai_analysis}
        </div>
        
        <div class="chart-section">
            <div class="chart-title">📈 エクイティカーブ</div>
            {charts.get('equity_curve', '')}
        </div>
        
        <div class="chart-section">
            <div class="chart-title">📊 月次リターン</div>
            {charts.get('monthly_returns', '')}
        </div>
        
        <div class="chart-section">
            <div class="chart-title">📉 ドローダウン</div>
            {charts.get('drawdown', '')}
        </div>
        
        <div class="chart-section">
            <div class="chart-title">📊 VIX（恐怖指数）</div>
            {charts.get('vix', '')}
        </div>
        
        <div class="chart-section">
            <div class="chart-title">💼 取引履歴</div>
            {charts.get('trades', '')}
        </div>
        
        <div class="chart-section">
            <div class="chart-title">📋 詳細取引履歴</div>
            {self._generate_trades_table(results.get('trades', []))}
        </div>
    </div>
    
    <!-- 指標説明モーダル -->
    <div id="metricModal" class="modal">
        <div class="modal-content">
            <span class="close">&times;</span>
            <div id="modalContent"></div>
        </div>
    </div>
    
    <script>
        // モーダル表示関数
        function showMetricModal(metricType) {{
            const modal = document.getElementById('metricModal');
            const modalContent = document.getElementById('modalContent');
            
            const metricData = {{
                'total_return': {{
                    title: '総リターン (Total Return)',
                    description: '投資期間全体での収益率を表す指標です。初期投資額に対する最終的な利益の割合を示します。',
                    formula: '総リターン = (最終エクイティ - 初期資本) / 初期資本 × 100',
                    interpretation: '• 正の値: 利益を獲得<br>• 負の値: 損失を発生<br>• 高い値ほど良いパフォーマンス'
                }},
                'sharpe_ratio': {{
                    title: 'シャープレシオ (Sharpe Ratio)',
                    description: 'リスク調整後のリターンを測定する指標です。リターンの変動性（リスク）を考慮した投資効率を表します。',
                    formula: 'シャープレシオ = (平均リターン - リスクフリーレート) / リターンの標準偏差',
                    interpretation: '• 1.0以上: 優秀なパフォーマンス<br>• 0.5-1.0: 良好なパフォーマンス<br>• 0.5未満: 改善が必要'
                }},
                'max_drawdown': {{
                    title: '最大ドローダウン (Maximum Drawdown)',
                    description: '投資期間中に発生した最大の損失幅を表す指標です。ピークからボトムまでの最大下落率を示します。',
                    formula: '最大ドローダウン = (ピーク時の資産価値 - ボトム時の資産価値) / ピーク時の資産価値 × 100',
                    interpretation: '• 0%: 損失なし<br>• -10%未満: 優秀なリスク管理<br>• -20%未満: 許容範囲<br>• -20%以上: リスク管理の見直しが必要'
                }},
                'win_rate': {{
                    title: '勝率 (Win Rate)',
                    description: '利益を上げた取引の割合を表す指標です。全取引数に対する勝ち取引の割合を示します。',
                    formula: '勝率 = 利益取引数 / 総取引数 × 100',
                    interpretation: '• 60%以上: 高い勝率<br>• 50-60%: 良好な勝率<br>• 50%未満: 改善が必要'
                }},
                'total_trades': {{
                    title: '総取引数 (Total Trades)',
                    description: 'バックテスト期間中に実行された取引の総数を表す指標です。戦略の活動度を示します。',
                    formula: '総取引数 = エントリー取引数 + エグジット取引数',
                    interpretation: '• 多い: 活発な取引戦略<br>• 少ない: 保守的な取引戦略<br>• 適度な取引数が理想的'
                }},
                'profit_factor': {{
                    title: 'プロフィットファクター (Profit Factor)',
                    description: '総利益と総損失の比率を表す指標です。利益効率を測定する重要な指標です。',
                    formula: 'プロフィットファクター = 総利益 / |総損失|',
                    interpretation: '• 2.0以上: 優秀な利益効率<br>• 1.5-2.0: 良好な利益効率<br>• 1.0-1.5: 改善が必要<br>• 1.0未満: 損失超過'
                }}
            }};
            
            const data = metricData[metricType];
            modalContent.innerHTML = `
                <div class="modal-title">${{data.title}}</div>
                <div class="modal-description">${{data.description}}</div>
                <div class="modal-formula"><strong>計算式:</strong><br>${{data.formula}}</div>
                <div class="modal-interpretation"><strong>評価基準:</strong><br>${{data.interpretation}}</div>
            `;
            
            modal.style.display = 'block';
        }}
        
        // モーダルを閉じる
        document.querySelector('.close').onclick = function() {{
            document.getElementById('metricModal').style.display = 'none';
        }}
        
        // モーダル外をクリックして閉じる
        window.onclick = function(event) {{
            const modal = document.getElementById('metricModal');
            if (event.target == modal) {{
                modal.style.display = 'none';
            }}
        }}
        
        // ESCキーでモーダルを閉じる
        document.addEventListener('keydown', function(event) {{
            if (event.key === 'Escape') {{
                document.getElementById('metricModal').style.display = 'none';
            }}
        }});
    </script>
</body>
</html>
        """
        
        return html_content
    
    def _calculate_statistics(self, results: Dict) -> Dict:
        """統計情報の計算"""
        stats = {}
        
        # 基本統計
        stats['total_return_pct'] = results.get('total_return', 0) * 100
        stats['sharpe_ratio'] = results.get('sharpe_ratio', 0)
        stats['max_drawdown_pct'] = results.get('max_drawdown', 0) * 100
        stats['win_rate_pct'] = results.get('win_rate', 0) * 100
        stats['total_trades'] = results.get('total_trades', 0)
        
        # プロフィットファクター
        avg_profit = results.get('avg_profit', 0)
        avg_loss = abs(results.get('avg_loss', 0))
        stats['profit_factor'] = avg_profit / avg_loss if avg_loss > 0 else 0
        
        return stats
    
    def _generate_ai_analysis(self, results: Dict, strategy_name: str) -> str:
        """AI分析コメントの生成"""
        total_return = results.get('total_return', 0)
        sharpe_ratio = results.get('sharpe_ratio', 0)
        max_drawdown = results.get('max_drawdown', 0)
        win_rate = results.get('win_rate', 0)
        total_trades = results.get('total_trades', 0)
        
        analysis = []
        
        # 総合評価
        if total_return > 0.2:
            analysis.append("✅ <strong>優秀なパフォーマンス:</strong> 20%を超える高いリターンを達成しています。")
        elif total_return > 0.1:
            analysis.append("👍 <strong>良好なパフォーマンス:</strong> 10%を超える安定したリターンを記録しています。")
        elif total_return > 0:
            analysis.append("⚠️ <strong>微益:</strong> プラスのリターンですが、改善の余地があります。")
        else:
            analysis.append("❌ <strong>改善が必要:</strong> マイナスリターンのため、戦略の見直しが必要です。")
        
        # リスク評価
        if sharpe_ratio > 1.5:
            analysis.append("✅ <strong>優秀なリスク調整後リターン:</strong> シャープレシオが1.5を超えており、リスクに対して十分なリターンを得ています。")
        elif sharpe_ratio > 1.0:
            analysis.append("👍 <strong>良好なリスク調整後リターン:</strong> シャープレシオが1.0を超えており、適切なリスク管理ができています。")
        else:
            analysis.append("⚠️ <strong>リスク調整後リターンの改善が必要:</strong> シャープレシオが低く、リスクに対して十分なリターンが得られていません。")
        
        # ドローダウン評価
        if abs(max_drawdown) < 0.1:
            analysis.append("✅ <strong>優秀なリスク管理:</strong> 最大ドローダウンが10%未満で、優れたリスク管理ができています。")
        elif abs(max_drawdown) < 0.2:
            analysis.append("👍 <strong>適切なリスク管理:</strong> 最大ドローダウンが20%未満で、許容範囲内のリスク管理です。")
        else:
            analysis.append("⚠️ <strong>リスク管理の改善が必要:</strong> 最大ドローダウンが20%を超えており、リスク管理の見直しが必要です。")
        
        # 勝率評価
        if win_rate > 0.6:
            analysis.append("✅ <strong>高い勝率:</strong> 60%を超える高い勝率で、安定した取引ができています。")
        elif win_rate > 0.5:
            analysis.append("👍 <strong>良好な勝率:</strong> 50%を超える勝率で、バランスの取れた取引ができています。")
        else:
            analysis.append("⚠️ <strong>勝率の改善が必要:</strong> 勝率が50%未満で、エントリー条件の見直しが必要です。")
        
        # 取引数評価
        if total_trades < 10:
            analysis.append("⚠️ <strong>取引数が少ない:</strong> 取引数が少なく、統計的な信頼性が低い可能性があります。")
        elif total_trades > 100:
            analysis.append("✅ <strong>十分な取引数:</strong> 十分な取引数があり、統計的に信頼できる結果です。")
        
        # 戦略別アドバイス
        if strategy_name == "デイトレード":
            analysis.append("<strong>デイトレード戦略のアドバイス:</strong> 短期での利益確定が重要です。VWAPと出来高の条件を厳格に適用し、素早い決済を心がけてください。")
        elif strategy_name == "スイングトレード":
            analysis.append("<strong>スイングトレード戦略のアドバイス:</strong> トレンドフォローが重要です。部分利確を活用し、利益を伸ばすことを心がけてください。")
        elif strategy_name == "中長期投資":
            analysis.append("<strong>中長期投資戦略のアドバイス:</strong> ファンダメンタルズとテクニカル指標の両方を重視し、長期トレンドに乗ることが重要です。")
        
        return "<br>".join(analysis)
    
    def _generate_trades_table(self, trades: List[Dict]) -> str:
        """取引履歴テーブルの生成"""
        if not trades:
            return "<p>取引履歴がありません。</p>"
        
        df = pd.DataFrame(trades)
        df['entry_date'] = pd.to_datetime(df['entry_date']).dt.strftime('%Y-%m-%d')
        df['exit_date'] = pd.to_datetime(df['exit_date']).dt.strftime('%Y-%m-%d')
        df['profit_loss_pct'] = df['profit_loss_pct'] * 100
        
        table_html = """
        <table class="trades-table">
            <thead>
                <tr>
                    <th>銘柄</th>
                    <th>エントリー日</th>
                    <th>決済日</th>
                    <th>エントリー価格</th>
                    <th>決済価格</th>
                    <th>数量</th>
                    <th>損益率</th>
                    <th>保有日数</th>
                    <th>決済理由</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for _, row in df.iterrows():
            profit_class = "profit" if row['profit_loss_pct'] > 0 else "loss"
            table_html += f"""
                <tr>
                    <td>{row['symbol']}</td>
                    <td>{row['entry_date']}</td>
                    <td>{row['exit_date']}</td>
                    <td>{row['entry_price']:.2f}</td>
                    <td>{row['exit_price']:.2f}</td>
                    <td>{row['quantity']}</td>
                    <td class="{profit_class}">{row['profit_loss_pct']:.2f}%</td>
                    <td>{row['holding_days']}</td>
                    <td>{row['exit_reason']}</td>
                </tr>
            """
        
        table_html += """
            </tbody>
        </table>
        """
        
        return table_html
    
    def generate_summary_report(self, all_results: Dict[str, Dict]) -> str:
        """
        全戦略のサマリーレポート生成（無効化）
        
        Args:
            all_results: 全戦略の結果辞書
        
        Returns:
            str: 空文字列（ファイル生成しない）
        """
        # summaryファイルの生成を無効化
        self.logger.info("サマリーレポート生成をスキップしました")
        return ""
