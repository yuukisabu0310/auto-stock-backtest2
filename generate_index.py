#!/usr/bin/env python3
"""
動的index.html生成スクリプト
最新のレポートを表示し、過去30日間のレポートにアクセスできるリンクを提供
"""

import os
import glob
from datetime import datetime, timedelta
import re
from typing import List, Dict, Tuple

def get_latest_reports(reports_dir: str = "reports") -> Dict[str, str]:
    """
    最新のレポートファイルを取得
    
    Args:
        reports_dir: レポートディレクトリ
    
    Returns:
        Dict: 戦略名と最新レポートファイルのマッピング
    """
    latest_reports = {}
    
    # 戦略別の最新レポートを取得
    strategies = {
        "swing_trading": "スイングトレード",
        "long_term": "中長期投資",
        "summary": "サマリー"
    }
    
    for strategy_key, strategy_name in strategies.items():
        pattern = os.path.join(reports_dir, f"{strategy_name}_*.html")
        files = glob.glob(pattern)
        
        if files:
            # ファイル名から日時を抽出して最新を特定
            latest_file = max(files, key=lambda x: extract_datetime_from_filename(x))
            latest_reports[strategy_key] = latest_file
    
    return latest_reports

def get_recent_reports(reports_dir: str = "reports", days: int = 30) -> List[Dict[str, str]]:
    """
    過去指定日数分のレポートを取得
    
    Args:
        reports_dir: レポートディレクトリ
        days: 取得する日数
    
    Returns:
        List: レポート情報のリスト
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_reports = []
    
    # すべてのHTMLファイルを取得
    pattern = os.path.join(reports_dir, "*.html")
    files = glob.glob(pattern)
    
    for file_path in files:
        filename = os.path.basename(file_path)
        
        # index.htmlは除外
        if filename == "index.html":
            continue
        
        # ファイル名から日時を抽出
        file_datetime = extract_datetime_from_filename(file_path)
        if file_datetime and file_datetime >= cutoff_date:
            # 戦略名を抽出
            strategy_name = extract_strategy_name(filename)
            
            recent_reports.append({
                "filename": filename,
                "filepath": file_path,
                "datetime": file_datetime,
                "strategy": strategy_name,
                "date_str": file_datetime.strftime("%Y-%m-%d %H:%M")
            })
    
    # 日時でソート（新しい順）
    recent_reports.sort(key=lambda x: x["datetime"], reverse=True)
    
    return recent_reports

def extract_datetime_from_filename(filepath: str) -> datetime:
    """
    ファイル名から日時を抽出
    
    Args:
        filepath: ファイルパス
    
    Returns:
        datetime: 抽出された日時
    """
    filename = os.path.basename(filepath)
    
    # パターン: 戦略名_YYYYMMDD_HHMMSS.html
    pattern = r'_(\d{8})_(\d{6})\.html$'
    match = re.search(pattern, filename)
    
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        
        try:
            return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
        except ValueError:
            pass
    
    return None

def extract_strategy_name(filename: str) -> str:
    """
    ファイル名から戦略名を抽出
    
    Args:
        filename: ファイル名
    
    Returns:
        str: 戦略名
    """
    # 戦略名のマッピング
    strategy_mapping = {
        "スイングトレード": "スイングトレード",
        "中長期投資": "中長期投資",
        "summary": "サマリー",
        "backtest_summary": "バックテスト集計"
    }
    
    for key, value in strategy_mapping.items():
        if key in filename:
            return value
    
    return "その他"

def generate_index_html(latest_reports: Dict[str, str], recent_reports: List[Dict[str, str]]) -> str:
    """
    動的index.htmlを生成
    
    Args:
        latest_reports: 最新レポートの辞書
        recent_reports: 最近のレポートリスト
    
    Returns:
        str: 生成されたHTML
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 自動株式バックテスト ダッシュボード</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            min-height: 100vh;
            color: #2d3748;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
            position: relative;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: -20px;
            left: 50%;
            transform: translateX(-50%);
            width: 100px;
            height: 4px;
            background: linear-gradient(90deg, #ff6b6b, #4ecdc4, #45b7d1);
            border-radius: 2px;
        }}
        
        .header h1 {{
            font-size: 3.5em;
            font-weight: 700;
            margin-bottom: 15px;
            text-shadow: 0 4px 20px rgba(0,0,0,0.3);
            background: linear-gradient(45deg, #fff, #f0f0f0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
            font-weight: 300;
            margin-bottom: 10px;
        }}
        
        .header .timestamp {{
            font-size: 0.9em;
            opacity: 0.7;
            font-weight: 400;
        }}
        
        .latest-reports {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            color: white;
            font-size: 2em;
            font-weight: 600;
            margin-bottom: 20px;
            text-align: center;
        }}
        
        .reports-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }}
        
        .report-card {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            position: relative;
            overflow: hidden;
        }}
        
        .report-card:hover {{
            transform: translateY(-10px);
            box-shadow: 0 30px 60px rgba(0, 0, 0, 0.15);
        }}
        
        .report-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #667eea, #764ba2);
        }}
        
        .report-icon {{
            font-size: 3em;
            margin-bottom: 20px;
            color: #667eea;
        }}
        
        .report-title {{
            font-size: 1.5em;
            font-weight: 600;
            margin-bottom: 15px;
            color: #2d3748;
        }}
        
        .report-date {{
            font-size: 0.9em;
            color: #718096;
            margin-bottom: 20px;
        }}
        
        .report-link {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 12px 30px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }}
        
        .report-link:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }}
        
        .recent-reports {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        .recent-reports h2 {{
            color: #2d3748;
            font-size: 1.8em;
            font-weight: 600;
            margin-bottom: 25px;
            text-align: center;
        }}
        
        .reports-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        .reports-table th,
        .reports-table td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .reports-table th {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            font-weight: 600;
        }}
        
        .reports-table tr:hover {{
            background: rgba(102, 126, 234, 0.05);
        }}
        
        .reports-table a {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s ease;
        }}
        
        .reports-table a:hover {{
            color: #764ba2;
            text-decoration: underline;
        }}
        
        .strategy-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 500;
            color: white;
        }}
        
        .strategy-swing {{
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
        }}
        
        .strategy-long {{
            background: linear-gradient(135deg, #4ecdc4, #44a08d);
        }}
        
        .strategy-summary {{
            background: linear-gradient(135deg, #667eea, #764ba2);
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            padding: 20px;
            opacity: 0.8;
        }}
        
        .footer a {{
            color: white;
            text-decoration: none;
            margin: 0 10px;
        }}
        
        .footer a:hover {{
            text-decoration: underline;
        }}
        
        .no-reports {{
            text-align: center;
            color: #718096;
            font-style: italic;
            padding: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 自動株式バックテスト</h1>
            <p>最新のバックテスト結果と過去30日間のレポート履歴</p>
            <div class="timestamp">最終更新: {current_time}</div>
        </div>
        
        <div class="latest-reports">
            <h2 class="section-title">📊 最新レポート</h2>
            <div class="reports-grid">
"""
    
    # 最新レポートのカードを生成
    strategy_icons = {
        "swing_trading": "📈",
        "long_term": "📊", 
        "summary": "📋"
    }
    
    for strategy_key, filepath in latest_reports.items():
        if filepath:
            filename = os.path.basename(filepath)
            file_datetime = extract_datetime_from_filename(filepath)
            date_str = file_datetime.strftime("%Y-%m-%d %H:%M") if file_datetime else "不明"
            
            strategy_name = {
                "swing_trading": "スイングトレード",
                "long_term": "中長期投資",
                "summary": "サマリー"
            }.get(strategy_key, strategy_key)
            
            icon = strategy_icons.get(strategy_key, "📄")
            
            html += f"""
                <div class="report-card">
                    <div class="report-icon">{icon}</div>
                    <div class="report-title">{strategy_name}</div>
                    <div class="report-date">{date_str}</div>
                    <a href="{filename}" class="report-link" target="_blank">
                        <i class="fas fa-external-link-alt"></i> レポートを開く
                    </a>
                </div>
"""
    
    html += """
            </div>
        </div>
        
        <div class="recent-reports">
            <h2>📅 過去30日間のレポート履歴</h2>
"""
    
    if recent_reports:
        html += """
            <table class="reports-table">
                <thead>
                    <tr>
                        <th>日時</th>
                        <th>戦略</th>
                        <th>ファイル名</th>
                        <th>アクション</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for report in recent_reports:
            strategy_class = {
                "スイングトレード": "strategy-swing",
                "中長期投資": "strategy-long", 
                "サマリー": "strategy-summary"
            }.get(report["strategy"], "strategy-summary")
            
            html += f"""
                    <tr>
                        <td>{report['date_str']}</td>
                        <td><span class="strategy-badge {strategy_class}">{report['strategy']}</span></td>
                        <td>{report['filename']}</td>
                        <td><a href="{report['filename']}" target="_blank"><i class="fas fa-external-link-alt"></i> 開く</a></td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
"""
    else:
        html += """
            <div class="no-reports">
                <p>過去30日間にレポートが見つかりませんでした。</p>
            </div>
"""
    
    html += """
        </div>
        
        <div class="footer">
            <p>🚀 自動株式バックテストシステム | 
            <a href="results/"><i class="fas fa-folder"></i> 結果ディレクトリ</a> | 
            <a href="cache/"><i class="fas fa-database"></i> キャッシュ</a></p>
        </div>
    </div>
</body>
</html>
"""
    
    return html

def main():
    """メイン処理"""
    print("動的index.htmlを生成中...")
    
    # 最新レポートを取得
    latest_reports = get_latest_reports()
    print(f"最新レポート: {len(latest_reports)}件")
    
    # 過去30日間のレポートを取得
    recent_reports = get_recent_reports(days=30)
    print(f"過去30日間のレポート: {len(recent_reports)}件")
    
    # HTMLを生成
    html_content = generate_index_html(latest_reports, recent_reports)
    
    # index.htmlに保存
    with open("reports/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("✅ index.htmlを生成しました")
    print(f"最新レポート: {list(latest_reports.keys())}")
    print(f"過去30日間のレポート数: {len(recent_reports)}")

if __name__ == "__main__":
    main()
