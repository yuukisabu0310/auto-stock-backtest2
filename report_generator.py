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

from config import REPORT_DIR, REPORT_TEMPLATES, TRADING_RULES

class ReportGenerator:
    """レポート生成クラス"""
    
    def __init__(self):
        self.report_dir = REPORT_DIR
        self.logger = logging.getLogger(__name__)
        self._ensure_report_dir()
    
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
    
    def generate_strategy_report(self, results: Dict, strategy_name: str) -> str:
        """
        戦略別レポートの生成
        
        Args:
            results: バックテスト結果
            strategy_name: 戦略名
        
        Returns:
            str: レポートファイルパス
        """
        if "error" in results:
            self.logger.error(f"レポート生成エラー: {results['error']}")
            return ""
        
        # チャートの生成
        charts = self._generate_charts(results)
        
        # HTMLレポートの生成
        html_content = self._generate_html_report(results, strategy_name, charts)
        
        # ファイル保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{strategy_name}_{timestamp}.html"
        filepath = os.path.join(self.report_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"レポート生成完了: {filepath}")
        return filepath
    
    def _generate_charts(self, results: Dict) -> Dict[str, str]:
        """チャートの生成"""
        charts = {}
        
        # エクイティカーブ
        if "equity_curve" in results:
            charts["equity_curve"] = self._create_equity_chart(results["equity_curve"])
        
        # 取引履歴
        if "trades" in results:
            charts["trades"] = self._create_trades_chart(results["trades"])
        
        # 月次リターン
        charts["monthly_returns"] = self._create_monthly_returns_chart(results)
        
        # ドローダウン
        if "equity_curve" in results:
            charts["drawdown"] = self._create_drawdown_chart(results["equity_curve"])
        
        return charts
    
    def _create_equity_chart(self, equity_data: Dict) -> str:
        """エクイティカーブチャート"""
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=equity_data["dates"],
            y=equity_data["values"],
            mode='lines',
            name='ポートフォリオ価値',
            line=dict(color='blue', width=2)
        ))
        
        fig.update_layout(
            title='エクイティカーブ',
            xaxis_title='日付',
            yaxis_title='ポートフォリオ価値 (円)',
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def _create_trades_chart(self, trades: List[Dict]) -> str:
        """取引履歴チャート"""
        if not trades:
            return ""
        
        df = pd.DataFrame(trades)
        df['entry_date'] = pd.to_datetime(df['entry_date'])
        df['exit_date'] = pd.to_datetime(df['exit_date'])
        
        fig = go.Figure()
        
        # 利益取引
        profit_trades = df[df['profit_loss'] > 0]
        if not profit_trades.empty:
            fig.add_trace(go.Scatter(
                x=profit_trades['exit_date'],
                y=profit_trades['profit_loss_pct'] * 100,
                mode='markers',
                name='利益取引',
                marker=dict(color='green', size=8),
                hovertemplate='<b>%{x}</b><br>利益: %{y:.2f}%<extra></extra>'
            ))
        
        # 損失取引
        loss_trades = df[df['profit_loss'] < 0]
        if not loss_trades.empty:
            fig.add_trace(go.Scatter(
                x=loss_trades['exit_date'],
                y=loss_trades['profit_loss_pct'] * 100,
                mode='markers',
                name='損失取引',
                marker=dict(color='red', size=8),
                hovertemplate='<b>%{x}</b><br>損失: %{y:.2f}%<extra></extra>'
            ))
        
        fig.update_layout(
            title='取引履歴',
            xaxis_title='決済日',
            yaxis_title='損益率 (%)',
            hovermode='closest',
            template='plotly_white'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def _create_monthly_returns_chart(self, results: Dict) -> str:
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
        
        fig.update_layout(
            title='月次リターン',
            xaxis_title='月',
            yaxis_title='リターン (%)',
            template='plotly_white'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def _create_drawdown_chart(self, equity_data: Dict) -> str:
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
        
        fig.update_layout(
            title='ドローダウン',
            xaxis_title='日付',
            yaxis_title='ドローダウン (%)',
            template='plotly_white'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def _generate_html_report(self, results: Dict, strategy_name: str, charts: Dict[str, str]) -> str:
        """HTMLレポートの生成"""
        # 基本統計の計算
        stats = self._calculate_statistics(results)
        
        # 戦略条件の取得
        strategy_conditions = self._get_strategy_conditions(strategy_name)
        strategy_conditions_html = self._generate_strategy_conditions_html(strategy_conditions)
        
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
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #007bff;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .chart-section {{
            margin: 30px 0;
        }}
        .chart-title {{
            font-size: 1.5em;
            margin-bottom: 15px;
            color: #333;
        }}
        .ai-analysis {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 30px 0;
            border-left: 4px solid #007bff;
        }}
        .ai-analysis h3 {{
            color: #007bff;
            margin-top: 0;
        }}
        .trades-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .trades-table th, .trades-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .trades-table th {{
            background-color: #007bff;
            color: white;
        }}
        .profit {{
            color: green;
            font-weight: bold;
        }}
        .loss {{
            color: red;
            font-weight: bold;
        }}
        .strategy-conditions {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 30px 0;
            border-left: 4px solid #28a745;
        }}
        .strategy-conditions h3 {{
            color: #28a745;
            margin-top: 0;
            margin-bottom: 20px;
        }}
        .conditions-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .condition-section {{
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }}
        .condition-section h4 {{
            color: #495057;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.1em;
        }}
        .condition-section ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .condition-section li {{
            padding: 8px 0;
            border-bottom: 1px solid #f1f3f4;
        }}
        .condition-section li:last-child {{
            border-bottom: none;
        }}
        .condition-section strong {{
            color: #495057;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>バックテスト結果レポート</h1>
            <h2>{strategy_name}</h2>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats['total_return_pct']:.2f}%</div>
                <div class="stat-label">総リターン</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['sharpe_ratio']:.2f}</div>
                <div class="stat-label">シャープレシオ</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['max_drawdown_pct']:.2f}%</div>
                <div class="stat-label">最大ドローダウン</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['win_rate_pct']:.1f}%</div>
                <div class="stat-label">勝率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['total_trades']}</div>
                <div class="stat-label">総取引数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['profit_factor']:.2f}</div>
                <div class="stat-label">プロフィットファクター</div>
            </div>
        </div>
        
        {strategy_conditions_html}
        
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
            <div class="chart-title">💼 取引履歴</div>
            {charts.get('trades', '')}
        </div>
        
        <div class="chart-section">
            <div class="chart-title">📋 詳細取引履歴</div>
            {self._generate_trades_table(results.get('trades', []))}
        </div>
    </div>
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
        全戦略のサマリーレポート生成
        
        Args:
            all_results: 全戦略の結果辞書
        
        Returns:
            str: サマリーレポートファイルパス
        """
        # サマリーレポートの実装
        # （簡略化のため、基本的な比較表のみ実装）
        
        summary_html = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>戦略比較サマリー</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>戦略比較サマリー</h1>
    <table>
        <tr>
            <th>戦略</th>
            <th>総リターン</th>
            <th>シャープレシオ</th>
            <th>最大ドローダウン</th>
            <th>勝率</th>
            <th>取引数</th>
        </tr>
        """
        
        for strategy, results in all_results.items():
            if "error" not in results:
                summary_html += f"""
                <tr>
                    <td>{strategy}</td>
                    <td>{results.get('total_return', 0)*100:.2f}%</td>
                    <td>{results.get('sharpe_ratio', 0):.2f}</td>
                    <td>{results.get('max_drawdown', 0)*100:.2f}%</td>
                    <td>{results.get('win_rate', 0)*100:.1f}%</td>
                    <td>{results.get('total_trades', 0)}</td>
                </tr>
                """
        
        summary_html += """
    </table>
</body>
</html>
        """
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"summary_{timestamp}.html"
        filepath = os.path.join(self.report_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary_html)
        
        return filepath
