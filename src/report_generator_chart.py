"""
個別銘柄チャート生成モジュール
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List
import numpy as np
import logging






def generate_individual_chart(symbol: str, data: pd.DataFrame, backtest_result: Dict, config: Dict = None) -> str:
    """個別銘柄のチャートを生成（設定可能な期間表示）"""
    if data.empty:
        return "<p>データがありません</p>"
    
    # 設定から表示期間を取得（デフォルト: 2年+3ヶ月余白）
    if config and 'reports' in config and 'chart_display' in config['reports']:
        years_back = config['reports']['chart_display'].get('years_back', 2)
        months_forward = config['reports']['chart_display'].get('months_forward_margin', 3)
    else:
        years_back = 2
        months_forward = 3
    
    # チャート表示期間の計算
    from datetime import datetime, timedelta
    
    # データの実際の範囲を取得
    data_start_date = data.index[0] if not data.empty else datetime.now()
    data_end_date = data.index[-1] if not data.empty else datetime.now()
    
    # 現在時刻を基準とした表示範囲の計算
    current_date = datetime.now()
    chart_start_date = current_date - timedelta(days=365 * years_back)  # 指定年数前
    chart_end_date = current_date + timedelta(days=30 * months_forward)  # 指定月数後
    
    # データの実際の範囲と表示範囲の調整
    # 開始日はデータ範囲を優先（過去データが不足する場合）
    if data_start_date < chart_start_date:
        chart_start_date = data_start_date
    
    # 終了日は余白を確実に表示するため、設定された余白期間を維持
    # データの終了日に関係なく、現在時刻+余白期間を表示
    # chart_end_date は変更しない（余白表示を優先）
    
    # データの準備（フィルタリングしない - 余白表示のため）
    dates = data.index
    close_prices = data['close']
    
    # OHLCデータの準備（ローソクチャート用）
    open_prices = data['open']
    high_prices = data['high']
    low_prices = data['low']
    
    # 技術指標の計算（全データを使用）
    sma_20 = data.get('sma_20', pd.Series())
    sma_25 = data.get('sma_25', pd.Series())
    ema_20 = data.get('ema_20', pd.Series())
    ema_60 = data.get('ema_60', pd.Series())
    ema_120 = data.get('ema_120', pd.Series())
    ema_240 = data.get('ema_240', pd.Series())
    rsi = data.get('rsi', pd.Series())
    bb_upper = data.get('bb_upper', pd.Series())
    bb_lower = data.get('bb_lower', pd.Series())
    bb_middle = data.get('bb_middle', pd.Series())
    
    # シグナルデータの取得
    buy_signals = backtest_result.get('buy_signals', [])
    sell_signals = backtest_result.get('sell_signals', [])
    
    # デバッグログ: データ情報
    logger = logging.getLogger(__name__)
    logger.info(f"\n=== チャート生成開始 ===")
    logger.info(f"データ期間: {data_start_date.strftime('%Y-%m-%d')} ～ {data_end_date.strftime('%Y-%m-%d')}")
    logger.info(f"現在時刻: {current_date.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"設定表示期間: {current_date.strftime('%Y-%m-%d')}から{years_back}年+{months_forward}ヶ月")
    logger.info(f"計算された表示期間: {chart_start_date.strftime('%Y-%m-%d')} ～ {chart_end_date.strftime('%Y-%m-%d')}")
    logger.info(f"余白期間: {current_date.strftime('%Y-%m-%d')} ～ {chart_end_date.strftime('%Y-%m-%d')} ({months_forward}ヶ月)")
    logger.info(f"データ数: {len(data)}")
    logger.info(f"価格範囲: {data['close'].min():.2f} ～ {data['close'].max():.2f}")
    
    # サブプロットの作成
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=('価格チャート', 'RSI', 'MACD'),
        row_heights=[0.6, 0.2, 0.2]
    )
    
    # ローソクチャート
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=open_prices,
            high=high_prices,
            low=low_prices,
            close=close_prices,
            name='価格',
            increasing_line_color='#26a69a',  # 上昇：緑
            decreasing_line_color='#ef5350',  # 下降：赤
            increasing_fillcolor='rgba(38, 166, 154, 0.2)',
            decreasing_fillcolor='rgba(239, 83, 80, 0.2)',
            line=dict(width=1)
        ),
        row=1, col=1
    )
    
    
    # SMA
    if not sma_20.empty:
        fig.add_trace(
            go.Scatter(x=dates, y=sma_20, name='SMA20', line=dict(color='orange', width=1)),
            row=1, col=1
        )
    
    # EMA
    if not ema_20.empty:
        fig.add_trace(
            go.Scatter(x=dates, y=ema_20, name='EMA20', line=dict(color='green', width=1)),
            row=1, col=1
        )
    if not ema_60.empty:
        fig.add_trace(
            go.Scatter(x=dates, y=ema_60, name='EMA60', line=dict(color='purple', width=1)),
            row=1, col=1
        )
    if not ema_120.empty:
        fig.add_trace(
            go.Scatter(x=dates, y=ema_120, name='EMA120', line=dict(color='red', width=1)),
            row=1, col=1
        )
    if not ema_240.empty:
        fig.add_trace(
            go.Scatter(x=dates, y=ema_240, name='EMA240', line=dict(color='brown', width=1)),
            row=1, col=1
        )
    
    # ボリンジャーバンド
    if not bb_upper.empty and not bb_lower.empty:
        fig.add_trace(
            go.Scatter(x=dates, y=bb_upper, name='BB上', line=dict(color='gray', width=1, dash='dash')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=dates, y=bb_lower, name='BB下', line=dict(color='gray', width=1, dash='dash')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=dates, y=bb_middle, name='BB中', line=dict(color='gray', width=1, dash='dot')),
            row=1, col=1
        )
    
    # 買いシグナル
    if buy_signals:
        buy_dates = [signal['date'] for signal in buy_signals]
        buy_prices = [signal['price'] for signal in buy_signals]
        fig.add_trace(
            go.Scatter(
                x=buy_dates, y=buy_prices, 
                mode='markers', 
                name='買いシグナル',
                marker=dict(color='green', size=10, symbol='triangle-up')
            ),
            row=1, col=1
        )
    
    # 売りシグナル
    if sell_signals:
        sell_dates = [signal['date'] for signal in sell_signals]
        sell_prices = [signal['price'] for signal in sell_signals]
        fig.add_trace(
            go.Scatter(
                x=sell_dates, y=sell_prices, 
                mode='markers', 
                name='売りシグナル',
                marker=dict(color='red', size=10, symbol='triangle-down')
            ),
            row=1, col=1
        )
    
    # RSI
    if not rsi.empty:
        fig.add_trace(
            go.Scatter(x=dates, y=rsi, name='RSI', line=dict(color='purple', width=2)),
            row=2, col=1
        )
        # RSIの基準線
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", row=2, col=1)
    
    # MACD
    macd_line = data.get('macd', pd.Series())
    macd_signal = data.get('macd_signal', pd.Series())
    macd_histogram = data.get('macd_histogram', pd.Series())
    
    if not macd_line.empty:
        fig.add_trace(
            go.Scatter(x=dates, y=macd_line, name='MACD', line=dict(color='blue', width=2)),
            row=3, col=1
        )
    if not macd_signal.empty:
        fig.add_trace(
            go.Scatter(x=dates, y=macd_signal, name='MACD Signal', line=dict(color='red', width=2)),
            row=3, col=1
        )
    if not macd_histogram.empty:
        colors = ['green' if x >= 0 else 'red' for x in macd_histogram]
        fig.add_trace(
            go.Bar(x=dates, y=macd_histogram, name='MACD Histogram', marker_color=colors),
            row=3, col=1
        )
    
    # レイアウトの設定（設定可能な期間表示）
    fig.update_layout(
        title=f'{symbol} 価格チャートとシグナル ({years_back}年+{months_forward}ヶ月余白)',
        height=800,
        showlegend=True,
        hovermode='x unified',
        xaxis_rangeslider_visible=False,  # ローソクチャートの下部スライダーを非表示
        xaxis=dict(
            rangeslider=dict(visible=False),
            type='date',
            range=[chart_start_date, chart_end_date],  # 表示範囲を強制設定
            autorange=False  # 自動範囲調整を無効化
        )
    )
    
    # 全てのサブプロットのx軸範囲を統一
    fig.update_xaxes(
        range=[chart_start_date, chart_end_date],
        autorange=False,
        row=1, col=1
    )
    fig.update_xaxes(
        range=[chart_start_date, chart_end_date],
        autorange=False,
        row=2, col=1
    )
    fig.update_xaxes(
        range=[chart_start_date, chart_end_date],
        autorange=False,
        row=3, col=1
    )
    
    # 軸の設定
    fig.update_xaxes(title_text="日付", row=3, col=1)
    fig.update_yaxes(title_text="価格", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    
    # HTMLに変換
    chart_html = fig.to_html(include_plotlyjs='cdn', div_id=f"chart_{symbol.replace('.', '_')}")
    
    return chart_html
