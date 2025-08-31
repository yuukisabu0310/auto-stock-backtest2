"""
バックテストエンジン
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from enum import Enum

from data_loader import DataLoader
from technical_indicators import TechnicalIndicators
from config import TRADING_RULES, INITIAL_CAPITAL

class TradeType(Enum):
    BUY = "buy"
    SELL = "sell"

@dataclass
class Trade:
    """取引情報"""
    symbol: str
    entry_date: datetime
    exit_date: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    trade_type: TradeType
    strategy: str
    entry_reason: str
    exit_reason: Optional[str]
    profit_loss: Optional[float]
    profit_loss_pct: Optional[float]
    holding_days: Optional[int]

class Portfolio:
    """ポートフォリオ管理クラス"""
    
    def __init__(self, initial_capital: float = INITIAL_CAPITAL):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Dict] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [initial_capital]
        self.dates: List[datetime] = [datetime.now()]
        
    def add_position(self, symbol: str, quantity: int, price: float, 
                    date: datetime, strategy: str, reason: str):
        """ポジション追加"""
        if symbol in self.positions:
            # 既存ポジションの更新
            pos = self.positions[symbol]
            total_quantity = pos['quantity'] + quantity
            avg_price = ((pos['quantity'] * pos['price']) + (quantity * price)) / total_quantity
            pos['quantity'] = total_quantity
            pos['price'] = avg_price
        else:
            # 新規ポジション
            self.positions[symbol] = {
                'quantity': quantity,
                'price': price,
                'entry_date': date,
                'strategy': strategy,
                'entry_reason': reason
            }
        
        self.cash -= quantity * price
        
    def close_position(self, symbol: str, quantity: int, price: float, 
                      date: datetime, reason: str) -> Optional[Trade]:
        """ポジション決済"""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        if quantity >= pos['quantity']:
            # 全決済
            trade = Trade(
                symbol=symbol,
                entry_date=pos['entry_date'],
                exit_date=date,
                entry_price=pos['price'],
                exit_price=price,
                quantity=pos['quantity'],
                trade_type=TradeType.SELL,
                strategy=pos['strategy'],
                entry_reason=pos['entry_reason'],
                exit_reason=reason,
                profit_loss=(price - pos['price']) * pos['quantity'],
                profit_loss_pct=(price - pos['price']) / pos['price'],
                holding_days=(date - pos['entry_date']).days
            )
            
            self.cash += pos['quantity'] * price
            del self.positions[symbol]
            self.trades.append(trade)
            return trade
        else:
            # 部分決済
            trade = Trade(
                symbol=symbol,
                entry_date=pos['entry_date'],
                exit_date=date,
                entry_price=pos['price'],
                exit_price=price,
                quantity=quantity,
                trade_type=TradeType.SELL,
                strategy=pos['strategy'],
                entry_reason=pos['entry_reason'],
                exit_reason=reason,
                profit_loss=(price - pos['price']) * quantity,
                profit_loss_pct=(price - pos['price']) / pos['price'],
                holding_days=(date - pos['entry_date']).days
            )
            
            pos['quantity'] -= quantity
            self.cash += quantity * price
            self.trades.append(trade)
            return trade
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """総資産価値の計算"""
        total = self.cash
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                total += pos['quantity'] * current_prices[symbol]
        return total
    
    def update_equity_curve(self, current_prices: Dict[str, float], date: datetime):
        """エクイティカーブの更新"""
        total_value = self.get_total_value(current_prices)
        self.equity_curve.append(total_value)
        self.dates.append(date)

class BacktestEngine:
    """バックテストエンジン"""
    
    def __init__(self, strategy: str):
        self.strategy = strategy
        self.rules = TRADING_RULES[strategy]
        self.data_loader = DataLoader()
        self.indicators = TechnicalIndicators()
        self.portfolio = Portfolio()
        self.logger = logging.getLogger(__name__)
        
        # 戦略固有の設定
        self.max_positions = self.rules["max_positions"]
        self.risk_per_trade = self.rules["risk_per_trade"]
        self.max_holding_days = self.rules["max_holding_days"]
        
    def run_backtest(self, symbols: List[str], start_date: str, end_date: str) -> Dict:
        """
        バックテスト実行
        
        Args:
            symbols: 対象銘柄リスト
            start_date: 開始日
            end_date: 終了日
        
        Returns:
            Dict: バックテスト結果
        """
        self.logger.info(f"バックテスト開始: {self.strategy}")
        
        # データ取得
        all_data = {}
        for symbol in symbols:
            data = self.data_loader.get_stock_data(
                symbol, start_date, end_date, 
                interval=self.rules["timeframe"]
            )
            if not data.empty:
                data = self.data_loader.clean_data(data)
                if self.data_loader.validate_data(data):
                    data = self.indicators.calculate_all_indicators(data)
                    all_data[symbol] = data
        
        if not all_data:
            self.logger.error("有効なデータがありません")
            return {}
        
        # 日付範囲の取得
        all_dates = set()
        for data in all_data.values():
            all_dates.update(data.index)
        all_dates = sorted(list(all_dates))
        
        # バックテスト実行
        for date in all_dates:
            self._process_date(date, all_data)
        
        # 結果計算
        results = self._calculate_results()
        
        self.logger.info(f"バックテスト完了: {self.strategy}")
        return results
    
    def _process_date(self, date: datetime, all_data: Dict[str, pd.DataFrame]):
        """特定日の処理"""
        current_prices = {}
        
        # 現在価格の取得
        for symbol, data in all_data.items():
            if date in data.index:
                current_prices[symbol] = data.loc[date, 'Close']
        
        # エグジット条件のチェック
        self._check_exit_conditions(date, all_data, current_prices)
        
        # エントリー条件のチェック
        self._check_entry_conditions(date, all_data, current_prices)
        
        # エクイティカーブの更新
        self.portfolio.update_equity_curve(current_prices, date)
    
    def _check_entry_conditions(self, date: datetime, all_data: Dict[str, pd.DataFrame], 
                              current_prices: Dict[str, float]):
        """エントリー条件のチェック"""
        # 最大ポジション数のチェック
        if len(self.portfolio.positions) >= self.max_positions:
            return
        
        for symbol, data in all_data.items():
            if symbol in self.portfolio.positions:
                continue  # 既にポジション保有
            
            if date not in data.index:
                continue
            
            # エントリー条件の確認
            entry_conditions = self.indicators.check_entry_conditions(data, self.strategy)
            
            if entry_conditions.loc[date]:
                # ポジションサイズの計算
                position_size = self._calculate_position_size(symbol, current_prices[symbol])
                
                if position_size > 0:
                    self.portfolio.add_position(
                        symbol=symbol,
                        quantity=position_size,
                        price=current_prices[symbol],
                        date=date,
                        strategy=self.strategy,
                        reason="entry_conditions_met"
                    )
                    self.logger.info(f"エントリー: {symbol} at {current_prices[symbol]:.2f}")
    
    def _check_exit_conditions(self, date: datetime, all_data: Dict[str, pd.DataFrame], 
                             current_prices: Dict[str, float]):
        """エグジット条件のチェック"""
        for symbol in list(self.portfolio.positions.keys()):
            if symbol not in all_data or date not in all_data[symbol].index:
                continue
            
            pos = self.portfolio.positions[symbol]
            current_price = current_prices[symbol]
            
            # エグジット条件の確認
            exit_conditions = self.indicators.check_exit_conditions(
                all_data[symbol], self.strategy, pos['price'], current_price
            )
            
            # 保有期間のチェック
            holding_days = (date - pos['entry_date']).days
            if holding_days >= self.max_holding_days:
                exit_conditions["exit"] = True
                exit_conditions["reason"] = "max_holding_days"
            
            if exit_conditions["exit"]:
                # 全決済
                self.portfolio.close_position(
                    symbol=symbol,
                    quantity=pos['quantity'],
                    price=current_price,
                    date=date,
                    reason=exit_conditions["reason"]
                )
                self.logger.info(f"エグジット: {symbol} at {current_price:.2f} ({exit_conditions['reason']})")
            
            elif exit_conditions["partial_exit"] and self.strategy == "swing_trading":
                # 部分決済（スイングトレードのみ）
                partial_quantity = pos['quantity'] // 2
                if partial_quantity > 0:
                    self.portfolio.close_position(
                        symbol=symbol,
                        quantity=partial_quantity,
                        price=current_price,
                        date=date,
                        reason="partial_profit"
                    )
                    self.logger.info(f"部分決済: {symbol} {partial_quantity}株 at {current_price:.2f}")
    
    def _calculate_position_size(self, symbol: str, price: float) -> int:
        """ポジションサイズの計算"""
        # リスクベースのポジションサイズ計算
        risk_amount = self.portfolio.get_total_value({}) * self.risk_per_trade
        
        # 最大ポジションサイズのチェック
        max_position_value = self.portfolio.get_total_value({}) * self.rules.get("max_position_size", 0.25)
        
        # 利用可能資金のチェック
        available_cash = self.portfolio.cash
        
        # 最小値を採用
        max_quantity_by_risk = int(risk_amount / price)
        max_quantity_by_position = int(max_position_value / price)
        max_quantity_by_cash = int(available_cash / price)
        
        quantity = min(max_quantity_by_risk, max_quantity_by_position, max_quantity_by_cash)
        
        return max(0, quantity)
    
    def _calculate_results(self) -> Dict:
        """バックテスト結果の計算"""
        if not self.portfolio.trades:
            return {"error": "取引がありません"}
        
        trades_df = pd.DataFrame([
            {
                'symbol': t.symbol,
                'entry_date': t.entry_date,
                'exit_date': t.exit_date,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'quantity': t.quantity,
                'profit_loss': t.profit_loss,
                'profit_loss_pct': t.profit_loss_pct,
                'holding_days': t.holding_days,
                'strategy': t.strategy,
                'entry_reason': t.entry_reason,
                'exit_reason': t.exit_reason
            }
            for t in self.portfolio.trades
        ])
        
        # 基本統計
        total_return = (self.portfolio.equity_curve[-1] - self.portfolio.initial_capital) / self.portfolio.initial_capital
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['profit_loss'] > 0])
        losing_trades = len(trades_df[trades_df['profit_loss'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 平均利益・損失
        avg_profit = trades_df[trades_df['profit_loss'] > 0]['profit_loss'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['profit_loss'] < 0]['profit_loss'].mean() if losing_trades > 0 else 0
        
        # 最大ドローダウン
        equity_series = pd.Series(self.portfolio.equity_curve, index=self.portfolio.dates)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # シャープレシオ
        returns = equity_series.pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        results = {
            "strategy": self.strategy,
            "total_return": total_return,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "final_equity": self.portfolio.equity_curve[-1],
            "initial_capital": self.portfolio.initial_capital,
            "trades": trades_df.to_dict('records'),
            "equity_curve": {
                "dates": [d.strftime("%Y-%m-%d") for d in self.portfolio.dates],
                "values": self.portfolio.equity_curve
            }
        }
        
        return results
