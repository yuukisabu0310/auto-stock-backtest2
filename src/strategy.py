"""
スイングトレード戦略ロジック
ファンダメンタル + テクニカル分析による買い・売りシグナル生成
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import talib


class SwingTradingStrategy:
    def __init__(self, config: Dict):
        """スイングトレード戦略の初期化"""
        self.config = config
        self.technical_config = config['strategy']['technical_indicators']
        self.scoring_config = config['strategy']['scoring']
        
    def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """テクニカル指標を計算"""
        df = data.copy()
        
        # 移動平均線
        for period in self.technical_config['sma_periods']:
            df[f'sma_{period}'] = talib.SMA(df['close'], timeperiod=period)
        
        # 指数移動平均線
        for period in self.technical_config['ema_periods']:
            df[f'ema_{period}'] = talib.EMA(df['close'], timeperiod=period)
        
        # RSI
        df['rsi'] = talib.RSI(df['close'], timeperiod=self.technical_config['rsi_period'])
        
        # MACD
        macd, macd_signal, macd_hist = talib.MACD(
            df['close'],
            fastperiod=self.technical_config['macd_fast'],
            slowperiod=self.technical_config['macd_slow'],
            signalperiod=self.technical_config['macd_signal']
        )
        df['macd'] = macd
        df['macd_signal'] = macd_signal
        df['macd_histogram'] = macd_hist
        
        # ボリンジャーバンド
        bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'])
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
        
        # ATR（Average True Range）
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        
        # 出来高移動平均
        df['volume_sma'] = talib.SMA(df['volume'], timeperiod=20)
        
        return df
    
    def calculate_fundamental_score(self, data: pd.DataFrame) -> pd.DataFrame:
        """ファンダメンタルスコアを計算（簡易版）"""
        df = data.copy()
        
        # 価格変動率
        df['price_change_1d'] = df['close'].pct_change(1)
        df['price_change_5d'] = df['close'].pct_change(5)
        df['price_change_20d'] = df['close'].pct_change(20)
        
        # ボラティリティ
        df['volatility_20d'] = df['close'].rolling(20).std()
        
        # 出来高分析
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
    def calculate_buy_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """買いシグナルを計算"""
        df = data.copy()
        df['buy_score'] = 0
        
        # 1. ゴールデンクロス＋傾き確認（2点）
        if 'sma_25' in df.columns and 'sma_50' in df.columns:
            # 移動平均の傾きを計算（前日比）
            df['sma_25_slope'] = df['sma_25'].diff()
            df['sma_50_slope'] = df['sma_50'].diff()
            
            # ゴールデンクロス＋傾き確認
            golden_cross_condition = (
                (df['sma_25'] > df['sma_50']) & 
                (df['sma_25_slope'] > 0) & 
                (df['sma_50_slope'] > 0)
            )
            df.loc[golden_cross_condition, 'buy_score'] += 2
        
        # 2. 出来高継続増加（1点）
        if 'volume_ratio' in df.columns:
            # 出来高比率 > 1.2 が 2日以上連続
            volume_condition = df['volume_ratio'] > 1.2
            # 2日連続の条件を確認
            volume_2days = volume_condition & volume_condition.shift(1)
            df.loc[volume_2days, 'buy_score'] += 1
        
        # 3. RSI狭域レンジ（1点）
        if 'rsi' in df.columns:
            rsi_condition = (df['rsi'] >= 45) & (df['rsi'] <= 55)
            df.loc[rsi_condition, 'buy_score'] += 1
        
        # 4. MACD強気判定（1点）
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            macd_bullish = (df['macd'] > df['macd_signal']) & (df['macd'] > 0)
            df.loc[macd_bullish, 'buy_score'] += 1
        
        return df
    
    def calculate_sell_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """売りシグナルを計算"""
        df = data.copy()
        df['sell_score'] = 0
        
        # 1. デッドクロス＋傾き確認（2点）
        if 'sma_25' in df.columns and 'sma_50' in df.columns:
            # 移動平均の傾きを計算（前日比）
            df['sma_25_slope'] = df['sma_25'].diff()
            df['sma_50_slope'] = df['sma_50'].diff()
            
            # デッドクロス＋傾き確認
            dead_cross_condition = (
                (df['sma_25'] < df['sma_50']) & 
                (df['sma_25_slope'] < 0) & 
                (df['sma_50_slope'] < 0)
            )
            df.loc[dead_cross_condition, 'sell_score'] += 2
        
        # 2. 出来高伴う陰線（1点）
        if 'volume_ratio' in df.columns:
            bearish_candle = (df['close'] < df['open']) & (df['volume_ratio'] > 1.2)
            df.loc[bearish_candle, 'sell_score'] += 1
        
        # 3. RSI過熱（1点）
        if 'rsi' in df.columns:
            rsi_overheated = df['rsi'] >= 70
            df.loc[rsi_overheated, 'sell_score'] += 1
        
        # 4. MACD弱気判定（1点）
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            macd_bearish = (df['macd'] < df['macd_signal']) & (df['macd'] < 0)
            df.loc[macd_bearish, 'sell_score'] += 1
        
        return df
    
    def calculate_combined_score(self, data: pd.DataFrame) -> pd.DataFrame:
        """買い・売りスコアを統合"""
        df = data.copy()
        
        # 買い・売りスコアが存在しない場合は0で初期化
        if 'buy_score' not in df.columns:
            df['buy_score'] = 0
        if 'sell_score' not in df.columns:
            df['sell_score'] = 0
        
        # ATRボラティリティフィルタ（ATR(14)/価格 > 5% の場合はシグナル無効）
        df['volatility_filter'] = False
        if 'atr' in df.columns and 'close' in df.columns:
            df['atr_ratio'] = df['atr'] / df['close']
            df.loc[df['atr_ratio'] > 0.05, 'volatility_filter'] = True
        
        # 買いと売りが同時に点灯した場合はシグナル無効
        df['conflict_filter'] = (df['buy_score'] > 0) & (df['sell_score'] > 0)
        
        # スコアが3点未満の場合は無効
        df['low_score_filter'] = (df['buy_score'] < 3) & (df['sell_score'] < 3)
        
        # シグナル判定
        df['signal'] = '様子見'  # デフォルト
        
        # フィルタが適用されていない場合のみシグナル判定
        valid_signals = ~(df['volatility_filter'] | df['conflict_filter'] | df['low_score_filter'])
        
        # 買いシグナル
        df.loc[valid_signals & (df['buy_score'] >= 5), 'signal'] = '強い買い'
        df.loc[valid_signals & (df['buy_score'] >= 3) & (df['buy_score'] < 5), 'signal'] = '買い'
        
        # 売りシグナル
        df.loc[valid_signals & (df['sell_score'] >= 5), 'signal'] = '強い売り'
        df.loc[valid_signals & (df['sell_score'] >= 3) & (df['sell_score'] < 5), 'signal'] = '売り'
        
        # 総合スコア（表示用）
        df['total_score'] = df['buy_score'] - df['sell_score']
        
        return df
    
    def generate_signal_conditions_detail(self, data: pd.DataFrame) -> Dict:
        """シグナル判定の詳細条件を生成"""
        if data.empty:
            return {'buy_conditions': [], 'sell_conditions': [], 'total_buy_score': 0, 'total_sell_score': 0}
        
        latest = data.iloc[-1]
        
        # 実際のデータから買い・売りスコアを取得
        actual_buy_score = latest.get('buy_score', 0)
        actual_sell_score = latest.get('sell_score', 0)
        
        conditions = {
            'buy_conditions': [],
            'sell_conditions': [],
            'total_buy_score': actual_buy_score,
            'total_sell_score': actual_sell_score
        }
        
        # 買い条件の詳細チェック
        buy_score = 0
        
        # 1. ゴールデンクロス＋傾き確認（2点）
        if len(data) >= 2 and 'sma_25' in data.columns and 'sma_50' in data.columns:
            current_sma25 = data['sma_25'].iloc[-1]
            current_sma50 = data['sma_50'].iloc[-1]
            sma25_slope = data['sma_25'].diff().iloc[-1]
            sma50_slope = data['sma_50'].diff().iloc[-1]
            
            if pd.notna(current_sma25) and pd.notna(current_sma50) and pd.notna(sma25_slope) and pd.notna(sma50_slope):
                golden_cross_condition = (
                    current_sma25 > current_sma50 and 
                    sma25_slope > 0 and 
                    sma50_slope > 0
                )
                if golden_cross_condition:
                    buy_score += 2
                    conditions['buy_conditions'].append({
                        'name': 'ゴールデンクロス＋傾き確認',
                        'description': f"25日MA({current_sma25:.2f}) > 50日MA({current_sma50:.2f}) 25日傾き({sma25_slope:.3f}) > 0 50日傾き({sma50_slope:.3f}) > 0",
                        'score': 2,
                        'met': True
                    })
                else:
                    conditions['buy_conditions'].append({
                        'name': 'ゴールデンクロス＋傾き確認',
                        'description': f"25日MA({current_sma25:.2f}) > 50日MA({current_sma50:.2f}) 25日傾き({sma25_slope:.3f}) > 0 50日傾き({sma50_slope:.3f}) > 0",
                        'score': 2,
                        'met': False
                    })
        
        # 2. 出来高継続増加（1点）
        if len(data) >= 2 and 'volume_ratio' in data.columns:
            current_volume = data['volume_ratio'].iloc[-1]
            prev_volume = data['volume_ratio'].iloc[-2]
            
            if pd.notna(current_volume) and pd.notna(prev_volume):
                volume_2days = current_volume > 1.2 and prev_volume > 1.2
                if volume_2days:
                    buy_score += 1
                    conditions['buy_conditions'].append({
                        'name': '出来高継続増加',
                        'description': f"当日出来高比率({current_volume:.2f}) > 1.2 前日出来高比率({prev_volume:.2f}) > 1.2",
                        'score': 1,
                        'met': True
                    })
                else:
                    conditions['buy_conditions'].append({
                        'name': '出来高継続増加',
                        'description': f"当日出来高比率({current_volume:.2f}) > 1.2 前日出来高比率({prev_volume:.2f}) > 1.2",
                        'score': 1,
                        'met': False
                    })
        
        # 3. RSI狭域レンジ（1点）
        if 'rsi' in latest and pd.notna(latest['rsi']):
            rsi_narrow = 45 <= latest['rsi'] <= 55
            if rsi_narrow:
                buy_score += 1
                conditions['buy_conditions'].append({
                    'name': 'RSI狭域レンジ',
                    'description': f"45 <= RSI({latest['rsi']:.1f}) <= 55",
                    'score': 1,
                    'met': True
                })
            else:
                conditions['buy_conditions'].append({
                    'name': 'RSI狭域レンジ',
                    'description': f"45 <= RSI({latest['rsi']:.1f}) <= 55",
                    'score': 1,
                    'met': False
                })
        
        # 4. MACD強気判定（1点）
        if 'macd' in latest and 'macd_signal' in latest and pd.notna(latest['macd']) and pd.notna(latest['macd_signal']):
            macd_bullish = latest['macd'] > latest['macd_signal'] and latest['macd'] > 0
            if macd_bullish:
                buy_score += 1
                conditions['buy_conditions'].append({
                    'name': 'MACD強気判定',
                    'description': f"MACD({latest['macd']:.3f}) > シグナル({latest['macd_signal']:.3f}) MACD({latest['macd']:.3f}) > 0",
                    'score': 1,
                    'met': True
                })
            else:
                conditions['buy_conditions'].append({
                    'name': 'MACD強気判定',
                    'description': f"MACD({latest['macd']:.3f}) > シグナル({latest['macd_signal']:.3f}) MACD({latest['macd']:.3f}) > 0",
                    'score': 1,
                    'met': False
                })
        
        # 売り条件の詳細チェック
        sell_score = 0
        
        # 1. デッドクロス＋傾き確認（2点）
        if len(data) >= 2 and 'sma_25' in data.columns and 'sma_50' in data.columns:
            current_sma25 = data['sma_25'].iloc[-1]
            current_sma50 = data['sma_50'].iloc[-1]
            sma25_slope = data['sma_25'].diff().iloc[-1]
            sma50_slope = data['sma_50'].diff().iloc[-1]
            
            if pd.notna(current_sma25) and pd.notna(current_sma50) and pd.notna(sma25_slope) and pd.notna(sma50_slope):
                dead_cross_condition = (
                    current_sma25 < current_sma50 and 
                    sma25_slope < 0 and 
                    sma50_slope < 0
                )
                if dead_cross_condition:
                    sell_score += 2
                    conditions['sell_conditions'].append({
                        'name': 'デッドクロス＋傾き確認',
                        'description': f"25日MA({current_sma25:.2f}) < 50日MA({current_sma50:.2f}) 25日傾き({sma25_slope:.3f}) < 0 50日傾き({sma50_slope:.3f}) < 0",
                        'score': 2,
                        'met': True
                    })
                else:
                    conditions['sell_conditions'].append({
                        'name': 'デッドクロス＋傾き確認',
                        'description': f"25日MA({current_sma25:.2f}) < 50日MA({current_sma50:.2f}) 25日傾き({sma25_slope:.3f}) < 0 50日傾き({sma50_slope:.3f}) < 0",
                        'score': 2,
                        'met': False
                    })
        
        # 2. 出来高伴う陰線（1点）
        if 'close' in latest and 'open' in latest and 'volume_ratio' in latest and pd.notna(latest['close']) and pd.notna(latest['open']) and pd.notna(latest['volume_ratio']):
            bearish_candle = latest['close'] < latest['open'] and latest['volume_ratio'] > 1.2
            if bearish_candle:
                sell_score += 1
                conditions['sell_conditions'].append({
                    'name': '出来高伴う陰線',
                    'description': f"終値({latest['close']:.2f}) < 始値({latest['open']:.2f}) 出来高比率({latest['volume_ratio']:.2f}) > 1.2",
                    'score': 1,
                    'met': True
                })
            else:
                conditions['sell_conditions'].append({
                    'name': '出来高伴う陰線',
                    'description': f"終値({latest['close']:.2f}) < 始値({latest['open']:.2f}) 出来高比率({latest['volume_ratio']:.2f}) > 1.2",
                    'score': 1,
                    'met': False
                })
        
        # 3. RSI過熱（1点）
        if 'rsi' in latest and pd.notna(latest['rsi']):
            rsi_overheated = latest['rsi'] >= 70
            if rsi_overheated:
                sell_score += 1
                conditions['sell_conditions'].append({
                    'name': 'RSI過熱',
                    'description': f"RSI({latest['rsi']:.1f}) >= 70",
                    'score': 1,
                    'met': True
                })
            else:
                conditions['sell_conditions'].append({
                    'name': 'RSI過熱',
                    'description': f"RSI({latest['rsi']:.1f}) >= 70",
                    'score': 1,
                    'met': False
                })
        
        # 4. MACD弱気判定（1点）
        if 'macd' in latest and 'macd_signal' in latest and pd.notna(latest['macd']) and pd.notna(latest['macd_signal']):
            macd_bearish = latest['macd'] < latest['macd_signal'] and latest['macd'] < 0
            if macd_bearish:
                sell_score += 1
                conditions['sell_conditions'].append({
                    'name': 'MACD弱気判定',
                    'description': f"MACD({latest['macd']:.3f}) < シグナル({latest['macd_signal']:.3f}) MACD({latest['macd']:.3f}) < 0",
                    'score': 1,
                    'met': True
                })
            else:
                conditions['sell_conditions'].append({
                    'name': 'MACD弱気判定',
                    'description': f"MACD({latest['macd']:.3f}) < シグナル({latest['macd_signal']:.3f}) MACD({latest['macd']:.3f}) < 0",
                    'score': 1,
                    'met': False
                })
        
        # フィルタ情報を追加
        if 'atr_ratio' in latest and pd.notna(latest['atr_ratio']):
            volatility_filter = latest['atr_ratio'] > 0.05
            if volatility_filter:
                conditions['buy_conditions'].append({
                    'name': '⚠️ ボラティリティフィルタ',
                    'description': f"ATR比率({latest['atr_ratio']:.3f}) > 5% - シグナル無効",
                    'score': 0,
                    'met': False
                })
                conditions['sell_conditions'].append({
                    'name': '⚠️ ボラティリティフィルタ',
                    'description': f"ATR比率({latest['atr_ratio']:.3f}) > 5% - シグナル無効",
                    'score': 0,
                    'met': False
                })
        
        conflict_filter = (actual_buy_score > 0) and (actual_sell_score > 0)
        if conflict_filter:
            conditions['buy_conditions'].append({
                'name': '⚠️ 競合フィルタ',
                'description': f"買いスコア({actual_buy_score}) > 0 かつ 売りスコア({actual_sell_score}) > 0 - シグナル無効",
                'score': 0,
                'met': False
            })
            conditions['sell_conditions'].append({
                'name': '⚠️ 競合フィルタ',
                'description': f"買いスコア({actual_buy_score}) > 0 かつ 売りスコア({actual_sell_score}) > 0 - シグナル無効",
                'score': 0,
                'met': False
            })
        
        # 注釈情報を追加
        conditions['annotations'] = []
        
        low_score_filter = (actual_buy_score < 3) and (actual_sell_score < 3)
        if low_score_filter:
            conditions['annotations'].append({
                'type': 'low_score_filter',
                'message': f"⚠️ 低スコアフィルタ: 買いスコア({actual_buy_score}) < 3 かつ 売りスコア({actual_sell_score}) < 3 - シグナル無効"
            })
        
        return conditions

    def generate_ai_comment(self, data: pd.DataFrame, symbol: str) -> str:
        """AI分析コメントを生成"""
        latest = data.iloc[-1]
        score = latest.get('total_score', 0)
        signal = latest.get('signal', '様子見')
        
        comments = []
        
        # 基本的なシグナルコメント
        if signal == '強い買い':
            comments.append("強力な買いシグナルが発生。エントリーチャンスを検討。")
        elif signal == '買い注意':
            comments.append("買いシグナルが確認。慎重にエントリーを検討。")
        elif signal == '様子見':
            comments.append("明確な方向性が見えない。様子見を推奨。")
        elif signal == '売り注意':
            comments.append("売りシグナルが確認。ポジション調整を検討。")
        elif signal == '強い売り':
            comments.append("強力な売りシグナルが発生。リスク回避を推奨。")
        
        # 利益確保・損切り目安
        if score > 0:  # 買いシグナルの場合
            if 'high' in data.columns:
                high_20d = data['high'].rolling(20).max().iloc[-1]
                profit_target = high_20d * 0.9  # 高値から10%下落で利確検討
                comments.append(f"利益確保目安: 直近高値から10%下落（{profit_target:.2f}）で利確検討")
            
            if 'sma_25' in latest:
                sma_25 = latest['sma_25']
                stop_loss = sma_25 * 0.95  # 25日MAの5%下で損切り
                comments.append(f"損切り目安: 25日MA割れ（{stop_loss:.2f}）で損切り")
        
        return " | ".join(comments) if comments else "分析データが不足しています。"
    
    def analyze_stock(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """個別銘柄の完全分析を実行"""
        # テクニカル指標計算
        df = self.calculate_technical_indicators(data)
        
        # ファンダメンタルスコア計算
        df = self.calculate_fundamental_score(df)
        
        # 買いシグナル計算
        df = self.calculate_buy_signals(df)
        
        # 売りシグナル計算
        df = self.calculate_sell_signals(df)
        
        # 統合スコア計算
        df = self.calculate_combined_score(df)
        
        return df
