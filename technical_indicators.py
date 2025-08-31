"""
技術指標計算モジュール
"""

import pandas as pd
import numpy as np
import ta
from typing import Dict, Tuple, Optional
import logging

from config import TECHNICAL_INDICATORS

class TechnicalIndicators:
    """技術指標計算クラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.params = TECHNICAL_INDICATORS
    
    def calculate_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        全ての技術指標を計算
        
        Args:
            data: 株価データ
        
        Returns:
            DataFrame: 技術指標付きデータ
        """
        if data.empty:
            return data
        
        # 基本指標
        data = self._calculate_moving_averages(data)
        data = self._calculate_rsi(data)
        data = self._calculate_volume_indicators(data)
        data = self._calculate_vwap(data)
        data = self._calculate_bollinger_bands(data)
        data = self._calculate_momentum_indicators(data)
        
        return data
    
    def _calculate_moving_averages(self, data: pd.DataFrame) -> pd.DataFrame:
        """移動平均線の計算"""
        try:
            # 短期移動平均
            data[f'SMA_{self.params["sma_short"]}'] = ta.trend.sma_indicator(
                data['Close'], window=self.params["sma_short"]
            )
            
            # 中期移動平均
            data[f'SMA_{self.params["sma_medium"]}'] = ta.trend.sma_indicator(
                data['Close'], window=self.params["sma_medium"]
            )
            
            # 長期移動平均
            data[f'SMA_{self.params["sma_long"]}'] = ta.trend.sma_indicator(
                data['Close'], window=self.params["sma_long"]
            )
            
            # ゴールデンクロス・デッドクロス判定
            data['Golden_Cross'] = (
                (data[f'SMA_{self.params["sma_short"]}'] > data[f'SMA_{self.params["sma_medium"]}']) &
                (data[f'SMA_{self.params["sma_short"]}'].shift(1) <= data[f'SMA_{self.params["sma_medium"]}'].shift(1))
            )
            
            data['Dead_Cross'] = (
                (data[f'SMA_{self.params["sma_short"]}'] < data[f'SMA_{self.params["sma_medium"]}']) &
                (data[f'SMA_{self.params["sma_short"]}'].shift(1) >= data[f'SMA_{self.params["sma_medium"]}'].shift(1))
            )
            
        except Exception as e:
            self.logger.error(f"移動平均計算エラー: {e}")
        
        return data
    
    def _calculate_rsi(self, data: pd.DataFrame) -> pd.DataFrame:
        """RSIの計算"""
        try:
            data['RSI'] = ta.momentum.rsi(
                data['Close'], window=self.params["rsi_period"]
            )
            
            # RSIの過買い・過売り判定
            data['RSI_Overbought'] = data['RSI'] > 70
            data['RSI_Oversold'] = data['RSI'] < 30
            
        except Exception as e:
            self.logger.error(f"RSI計算エラー: {e}")
        
        return data
    
    def _calculate_volume_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """出来高関連指標の計算"""
        try:
            # 出来高移動平均（手動計算）
            data['Volume_SMA'] = data['Volume'].rolling(window=self.params["volume_period"]).mean()
            
            # 出来高比率
            data['Volume_Ratio'] = data['Volume'] / data['Volume_SMA']
            
            # 出来高増加判定
            data['Volume_Surge'] = data['Volume_Ratio'] > 1.5
            
        except Exception as e:
            self.logger.error(f"出来高指標計算エラー: {e}")
        
        return data
    
    def _calculate_vwap(self, data: pd.DataFrame) -> pd.DataFrame:
        """VWAPの計算"""
        try:
            # VWAP計算
            data['VWAP'] = ta.volume.volume_weighted_average_price(
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                volume=data['Volume']
            )
            
            # VWAPに対する位置
            data['Above_VWAP'] = data['Close'] > data['VWAP']
            data['Below_VWAP'] = data['Close'] < data['VWAP']
            
        except Exception as e:
            self.logger.error(f"VWAP計算エラー: {e}")
        
        return data
    
    def _calculate_bollinger_bands(self, data: pd.DataFrame) -> pd.DataFrame:
        """ボリンジャーバンドの計算"""
        try:
            bb = ta.volatility.BollingerBands(
                data['Close'],
                window=self.params["bollinger_period"],
                window_dev=self.params["bollinger_std"]
            )
            
            data['BB_Upper'] = bb.bollinger_hband()
            data['BB_Middle'] = bb.bollinger_mavg()
            data['BB_Lower'] = bb.bollinger_lband()
            
            # ボリンジャーバンド位置
            data['BB_Position'] = (data['Close'] - data['BB_Lower']) / (data['BB_Upper'] - data['BB_Lower'])
            
            # +2σ到達判定
            data['BB_Upper2'] = data['BB_Middle'] + 2 * (data['BB_Upper'] - data['BB_Middle'])
            data['BB_Upper2_Reached'] = data['Close'] >= data['BB_Upper2']
            
        except Exception as e:
            self.logger.error(f"ボリンジャーバンド計算エラー: {e}")
        
        return data
    
    def _calculate_momentum_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """モメンタム指標の計算"""
        try:
            # MACD
            macd = ta.trend.MACD(data['Close'])
            data['MACD'] = macd.macd()
            data['MACD_Signal'] = macd.macd_signal()
            data['MACD_Histogram'] = macd.macd_diff()
            
            # ストキャスティクス
            stoch = ta.momentum.StochasticOscillator(
                data['High'], data['Low'], data['Close']
            )
            data['Stoch_K'] = stoch.stoch()
            data['Stoch_D'] = stoch.stoch_signal()
            
            # 価格モメンタム
            data['Price_Momentum'] = data['Close'].pct_change(periods=5)
            
        except Exception as e:
            self.logger.error(f"モメンタム指標計算エラー: {e}")
        
        return data
    
    def check_entry_conditions(self, data: pd.DataFrame, strategy: str) -> pd.Series:
        """
        エントリー条件のチェック
        
        Args:
            data: 技術指標付きデータ
            strategy: 戦略名
        
        Returns:
            Series: エントリー条件を満たすかどうか
        """
        if data.empty:
            return pd.Series([False] * len(data), index=data.index)
        
        conditions = pd.Series([True] * len(data), index=data.index)
        
        if strategy == "day_trading":
            # デイトレード条件
            conditions &= data['Golden_Cross']  # ゴールデンクロス
            conditions &= data['Above_VWAP']    # VWAPより上
            conditions &= data['Volume_Ratio'] >= 2.0  # 出来高2倍以上
            
        elif strategy == "swing_trading":
            # スイングトレード条件
            conditions &= data['Golden_Cross']  # ゴールデンクロス
            conditions &= (data['RSI'] >= 40) & (data['RSI'] <= 50)  # RSI 40-50
            conditions &= data['Volume_Ratio'] >= 1.5  # 出来高1.5倍以上
            
        elif strategy == "long_term":
            # 中長期投資条件
            conditions &= data['Close'] > data[f'SMA_{self.params["sma_long"]}']  # 200日線上
            conditions &= data['Volume_Surge']  # 出来高増加
            
        return conditions
    
    def check_exit_conditions(self, data: pd.DataFrame, strategy: str, 
                            entry_price: float, current_price: float) -> Dict[str, bool]:
        """
        エグジット条件のチェック
        
        Args:
            data: 技術指標付きデータ
            strategy: 戦略名
            entry_price: エントリー価格
            current_price: 現在価格
        
        Returns:
            Dict: エグジット条件の判定結果
        """
        if data.empty:
            return {"exit": False, "reason": "no_data"}
        
        latest = data.iloc[-1]
        price_change = (current_price - entry_price) / entry_price
        
        exit_conditions = {
            "exit": False,
            "reason": "",
            "partial_exit": False
        }
        
        if strategy == "day_trading":
            # デイトレードのエグジット条件
            if price_change >= 0.015:  # 1.5%利確
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "profit_target"
            elif price_change <= -0.015:  # 1.5%損切り
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "stop_loss"
            elif latest['RSI_Overbought']:  # RSI過買い
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "rsi_overbought"
            elif latest['Below_VWAP']:  # VWAP割れ
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "below_vwap"
                
        elif strategy == "swing_trading":
            # スイングトレードのエグジット条件
            if price_change >= 0.075:  # 7.5%利確
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "profit_target"
            elif price_change <= -0.05:  # 5%損切り
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "stop_loss"
            elif latest['RSI_Overbought']:  # RSI過買い
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "rsi_overbought"
            elif latest['Close'] < latest[f'SMA_{self.params["sma_medium"]}']:  # 25日線割れ
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "below_ma25"
            elif price_change >= 0.05:  # 5%で部分利確
                exit_conditions["partial_exit"] = True
                exit_conditions["reason"] = "partial_profit"
                
        elif strategy == "long_term":
            # 中長期投資のエグジット条件
            if price_change >= 0.30:  # 30%利確
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "profit_target"
            elif price_change <= -0.085:  # 8.5%損切り
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "stop_loss"
            elif latest['Close'] < latest[f'SMA_{self.params["sma_long"]}']:  # 200日線割れ
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "below_ma200"
        
        return exit_conditions
    
    def get_support_resistance(self, data: pd.DataFrame, window: int = 20) -> Tuple[float, float]:
        """
        サポート・レジスタンスレベルの計算
        
        Args:
            data: 株価データ
            window: 計算期間
        
        Returns:
            Tuple: (サポートレベル, レジスタンスレベル)
        """
        if len(data) < window:
            return 0.0, 0.0
        
        recent_data = data.tail(window)
        support = recent_data['Low'].min()
        resistance = recent_data['High'].max()
        
        return support, resistance
