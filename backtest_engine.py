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
import time
import concurrent.futures
from functools import partial

from data_loader import DataLoader
from cache_data_loader import CacheOnlyDataLoader
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
    
    def __init__(self, strategy: str, cache_only: bool = False):
        self.strategy = strategy
        self.rules = TRADING_RULES[strategy]
        
        # データローダーの選択
        if cache_only:
            self.data_loader = CacheOnlyDataLoader()
            self.logger = logging.getLogger(f"{__name__}.{strategy}.cache_only")
        else:
            self.data_loader = DataLoader()
            self.logger = logging.getLogger(f"{__name__}.{strategy}.full")
        
        self.indicators = TechnicalIndicators()
        self.portfolio = Portfolio()
        
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
        
        # データ取得（キャッシュ専用モードの場合は専用メソッドを使用）
        if isinstance(self.data_loader, CacheOnlyDataLoader):
            all_data = self._get_data_from_cache(symbols, start_date, end_date)
        else:
            all_data = self._get_data_from_loader(symbols, start_date, end_date)
        
        if not all_data:
            self.logger.error("有効なデータがありません")
            return {}
        
        # VIXデータを取得
        if isinstance(self.data_loader, CacheOnlyDataLoader):
            self.vix_data = self.data_loader.get_vix_data_from_cache(start_date, end_date)
        else:
            self.vix_data = self.data_loader.get_vix_data(start_date, end_date)
        
        # 日付範囲の取得
        all_dates = set()
        for data in all_data.values():
            all_dates.update(data.index)
        
        # バックテスト実行
        return self._execute_backtest(all_data, start_date, end_date)
    
    def _get_data_from_cache(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        キャッシュからデータを取得
        
        Args:
            symbols: 対象銘柄リスト
            start_date: 開始日
            end_date: 終了日
        
        Returns:
            Dict: 銘柄コードをキーとしたデータ辞書
        """
        all_data = {}
        
        for symbol in symbols:
            try:
                data = self.data_loader.get_stock_data_from_cache(
                    symbol, start_date, end_date, 
                    interval=self.rules["timeframe"]
                )
                if not data.empty:
                    data = self.data_loader.clean_data(data)
                    if self.data_loader.validate_data(data):
                        data = self.indicators.calculate_all_indicators(data)
                        all_data[symbol] = data
            except (FileNotFoundError, ValueError) as e:
                self.logger.warning(f"キャッシュからデータ取得失敗: {symbol}, {e}")
        
        return all_data
    
    def _get_data_from_loader(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        データローダーからデータを取得（従来の方法）
        
        Args:
            symbols: 対象銘柄リスト
            start_date: 開始日
            end_date: 終了日
        
        Returns:
            Dict: 銘柄コードをキーとしたデータ辞書
        """
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
        
        return all_data
    
    def _execute_backtest(self, all_data: Dict[str, pd.DataFrame], start_date: str, end_date: str) -> Dict:
        """
        バックテストの実行部分
        
        Args:
            all_data: 銘柄データ辞書
            start_date: 開始日
            end_date: 終了日
        
        Returns:
            Dict: バックテスト結果
        """
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
    
    def run_backtest_parallel(self, stocks_data: Dict[str, pd.DataFrame], 
                             start_date: str, end_date: str, 
                             max_workers: int = 3) -> Dict:
        """
        並列処理によるバックテスト実行（高速化版）
        
        Args:
            stocks_data: 銘柄コードをキーとしたデータ辞書
            start_date: 開始日
            end_date: 終了日
            max_workers: 並列処理の最大ワーカー数
        
        Returns:
            Dict: バックテスト結果
        """
        self.logger.info(f"並列バックテスト開始: {len(stocks_data)}銘柄")
        start_time = time.time()
        
        # VIXデータを取得
        self.vix_data = self.data_loader.get_vix_data(start_date, end_date)
        
        # データの前処理
        processed_data = {}
        for symbol, data in stocks_data.items():
            if not data.empty and self.validate_data(data):
                processed_data[symbol] = data
        
        if not processed_data:
            return {"error": "有効なデータがありません"}
        
        self.logger.info(f"有効なデータ: {len(processed_data)}銘柄")
        
        # 並列処理でバックテスト実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 部分関数を作成
            backtest_func = partial(
                self._run_single_stock_backtest,
                start_date=start_date,
                end_date=end_date
            )
            
            # 並列実行
            future_to_symbol = {
                executor.submit(backtest_func, symbol, data): symbol 
                for symbol, data in processed_data.items()
            }
            
            all_trades = []
            completed = 0
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                completed += 1
                
                try:
                    trades = future.result()
                    if trades:
                        all_trades.extend(trades)
                    
                    # 進捗表示
                    if completed % 10 == 0 or completed == len(processed_data):
                        self.logger.info(f"バックテスト進捗: {completed}/{len(processed_data)} 完了")
                        
                except Exception as e:
                    self.logger.error(f"バックテストエラー: {symbol}, {e}")
        
        # 結果の集計
        if all_trades:
            # ポートフォリオを再構築
            self.portfolio = Portfolio()
            
            # 取引を日付順にソート
            all_trades.sort(key=lambda x: x.entry_date)
            
            # 取引を適用
            for trade in all_trades:
                self.portfolio.trades.append(trade)
            
            # エクイティカーブを再構築
            self._reconstruct_equity_curve(processed_data, start_date, end_date)
            
            # 結果を計算
            results = self._calculate_results()
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"並列バックテスト完了: 所要時間 {elapsed_time:.2f}秒")
            
            return results
        else:
            return {"error": "有効な取引がありません"}
    
    def _reconstruct_equity_curve(self, stocks_data: Dict[str, pd.DataFrame], 
                                 start_date: str, end_date: str):
        """
        エクイティカーブの再構築
        
        Args:
            stocks_data: 銘柄データ辞書
            start_date: 開始日
            end_date: 終了日
        """
        try:
            # 全取引を日付順にソート
            all_trades = sorted(self.portfolio.trades, key=lambda x: x.entry_date)
            
            # 期間内の全日付を取得
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            # 全銘柄の日付を統合
            all_dates = set()
            for data in stocks_data.values():
                if not data.empty:
                    period_data = data[(data.index >= start_dt) & (data.index <= end_dt)]
                    all_dates.update(period_data.index)
            
            all_dates = sorted(list(all_dates))
            
            # ポートフォリオの初期化
            self.portfolio.equity_curve = [self.portfolio.initial_capital]
            self.portfolio.dates = [all_dates[0] if all_dates else start_dt]
            
            # 各日付でエクイティを計算
            current_cash = self.portfolio.initial_capital
            current_positions = {}  # {symbol: {'quantity': int, 'entry_price': float}}
            
            for date in all_dates:
                # その日の取引を処理（エントリーとエグジット両方）
                entry_trades = [t for t in all_trades if t.entry_date.date() == date.date()]
                exit_trades = [t for t in all_trades if t.exit_date and t.exit_date.date() == date.date()]
                
                # エグジット取引の処理（先に処理）
                for trade in exit_trades:
                    if trade.symbol in current_positions:
                        pos = current_positions[trade.symbol]
                        if pos['quantity'] >= trade.quantity:
                            # 決済処理
                            current_cash += trade.quantity * trade.exit_price
                            pos['quantity'] -= trade.quantity
                            if pos['quantity'] <= 0:
                                del current_positions[trade.symbol]
                
                # エントリー取引の処理
                for trade in entry_trades:
                    # ポジション追加
                    if trade.symbol not in current_positions:
                        current_positions[trade.symbol] = {
                            'quantity': trade.quantity,
                            'entry_price': trade.entry_price
                        }
                        current_cash -= trade.quantity * trade.entry_price
                    else:
                        # 既存ポジションの更新
                        pos = current_positions[trade.symbol]
                        pos['quantity'] += trade.quantity
                        current_cash -= trade.quantity * trade.entry_price
                
                # 現在価格での総資産価値を計算
                total_value = current_cash
                for symbol, pos in current_positions.items():
                    if symbol in stocks_data and not stocks_data[symbol].empty:
                        if date in stocks_data[symbol].index:
                            current_price = stocks_data[symbol].loc[date, 'Close']
                            total_value += pos['quantity'] * current_price
                
                # エクイティカーブに追加
                self.portfolio.equity_curve.append(total_value)
                self.portfolio.dates.append(date)
            
            self.logger.info(f"エクイティカーブ再構築完了: {len(self.portfolio.equity_curve)}ポイント")
            
        except Exception as e:
            self.logger.error(f"エクイティカーブ再構築エラー: {e}")
            # フォールバック: 初期資本のみ
            self.portfolio.equity_curve = [self.portfolio.initial_capital]
            self.portfolio.dates = [pd.to_datetime(start_date)]
    
    def _run_single_stock_backtest(self, symbol: str, data: pd.DataFrame, 
                                  start_date: str, end_date: str) -> List[Trade]:
        """
        単一銘柄のバックテスト実行
        
        Args:
            symbol: 銘柄コード
            data: 株価データ
            start_date: 開始日
            end_date: 終了日
        
        Returns:
            List[Trade]: 取引リスト
        """
        try:
            # 期間でフィルタリング
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            data = data[(data.index >= start_dt) & (data.index <= end_dt)]
            
            if data.empty:
                return []
            
            # テクニカル指標の計算
            indicators = TechnicalIndicators()
            data = indicators.calculate_all_indicators(data)
            
            # 取引シグナルの生成
            trades = []
            position = None
            
            for date, row in data.iterrows():
                # エントリー条件のチェック
                if position is None:
                    # 単一銘柄用のエントリー条件チェック
                    entry_signal = self._check_single_stock_entry_conditions(row, symbol)
                    if entry_signal:
                        position = {
                            'symbol': symbol,
                            'entry_date': date,
                            'entry_price': row['Close'],
                            'quantity': self._calculate_position_size(symbol, row['Close']),
                            'entry_reason': entry_signal
                        }
                
                # エグジット条件のチェック
                elif position:
                    exit_signal = self._check_single_stock_exit_conditions(row, position, date)
                    if exit_signal:
                        trade = Trade(
                            symbol=position['symbol'],
                            entry_date=position['entry_date'],
                            exit_date=date,
                            entry_price=position['entry_price'],
                            exit_price=row['Close'],
                            quantity=position['quantity'],
                            trade_type=TradeType.SELL,
                            strategy=self.strategy,
                            entry_reason=position['entry_reason'],
                            exit_reason=exit_signal,
                            profit_loss=(row['Close'] - position['entry_price']) * position['quantity'],
                            profit_loss_pct=(row['Close'] - position['entry_price']) / position['entry_price'],
                            holding_days=(date - position['entry_date']).days
                        )
                        trades.append(trade)
                        position = None
            
            return trades
            
        except Exception as e:
            self.logger.error(f"単一銘柄バックテストエラー: {symbol}, {e}")
            return []
    
    def _check_single_stock_entry_conditions(self, row: pd.Series, symbol: str) -> Optional[str]:
        """
        単一銘柄のエントリー条件チェック
        
        Args:
            row: 現在のデータ行
            symbol: 銘柄コード
        
        Returns:
            Optional[str]: エントリー理由
        """
        try:
            # VIXが30以上の場合、取引しない
            if hasattr(self, 'vix_data') and not self.vix_data.empty:
                current_date = row.name
                if current_date in self.vix_data.index:
                    vix_value = self.vix_data.loc[current_date, 'Close']
                    if vix_value >= 30:
                        return None  # VIXが高いため取引しない
            
            # スイングトレード戦略
            if self.strategy == "swing_trading":
                # RSIが30以下で買われすぎ
                if 'RSI' in row and row['RSI'] < 30:
                    return "RSI_oversold"
                
                # MACDがゴールデンクロス
                if 'MACD' in row and 'MACD_Signal' in row and row['MACD'] > row['MACD_Signal']:
                    return "MACD_golden_cross"
                
                # 移動平均線のゴールデンクロス
                if 'SMA_20' in row and 'SMA_50' in row and row['SMA_20'] > row['SMA_50']:
                    return "SMA_golden_cross"
            
            # 中長期投資戦略
            elif self.strategy == "long_term":
                # 長期移動平均線の上昇トレンド
                if 'SMA_200' in row and 'SMA_50' in row and row['SMA_200'] > row['SMA_50']:
                    return "long_term_uptrend"
                
                # ボリンジャーバンドの下軌道タッチ
                if 'BB_Lower' in row and row['Close'] <= row['BB_Lower']:
                    return "bollinger_oversold"
            
            return None
            
        except Exception as e:
            self.logger.error(f"エントリー条件チェックエラー: {symbol}, {e}")
            return None
    
    def _check_single_stock_exit_conditions(self, row: pd.Series, position: dict, date: datetime) -> Optional[str]:
        """
        単一銘柄のエグジット条件チェック
        
        Args:
            row: 現在のデータ行
            position: ポジション情報
            date: 現在の日付
        
        Returns:
            Optional[str]: エグジット理由
        """
        try:
            entry_price = position['entry_price']
            current_price = row['Close']
            
            # 利益確定（10%以上）
            if current_price >= entry_price * 1.10:
                return "profit_taking"
            
            # 損切り（-5%以下）
            if current_price <= entry_price * 0.95:
                return "stop_loss"
            
            # スイングトレード戦略
            if self.strategy == "swing_trading":
                # RSIが70以上で売られすぎ
                if 'RSI' in row and row['RSI'] > 70:
                    return "RSI_overbought"
                
                # MACDがデッドクロス
                if 'MACD' in row and 'MACD_Signal' in row and row['MACD'] < row['MACD_Signal']:
                    return "MACD_dead_cross"
                
                # 保有期間が30日を超える
                holding_days = (date - position['entry_date']).days
                if holding_days > 30:
                    return "time_exit"
            
            # 中長期投資戦略
            elif self.strategy == "long_term":
                # 保有期間が1年を超える
                holding_days = (date - position['entry_date']).days
                if holding_days > 365:
                    return "long_term_exit"
                
                # 長期移動平均線の下降トレンド
                if 'SMA_200' in row and 'SMA_50' in row and row['SMA_200'] < row['SMA_50']:
                    return "trend_reversal"
            
            return None
            
        except Exception as e:
            self.logger.error(f"エグジット条件チェックエラー: {position['symbol']}, {e}")
            return None
    
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
            },
            "vix_data": self._prepare_vix_data(self.vix_data) if not self.vix_data.empty else {}
        }
        
        return results
    
    def _prepare_vix_data(self, vix_data: pd.DataFrame) -> Dict:
        """
        VIXデータをレポート用に準備
        
        Args:
            vix_data: VIXデータのDataFrame
        
        Returns:
            Dict: レポート用のVIXデータ
        """
        if vix_data.empty:
            return {}
        
        # 日付とVIX値を抽出
        vix_dates = [d.strftime("%Y-%m-%d") for d in vix_data.index]
        vix_values = vix_data['Close'].tolist()
        
        # VIX統計を計算
        vix_stats = {
            "min": float(vix_data['Close'].min()),
            "max": float(vix_data['Close'].max()),
            "mean": float(vix_data['Close'].mean()),
            "std": float(vix_data['Close'].std())
        }
        
        # 高ボラティリティ期間を特定
        high_vol_periods = []
        for i, (date, value) in enumerate(zip(vix_dates, vix_values)):
            if value > 30:  # VIX > 30を高ボラティリティとする
                high_vol_periods.append({
                    "date": date,
                    "vix": value
                })
        
        return {
            "dates": vix_dates,
            "values": vix_values,
            "stats": vix_stats,
            "high_volatility_periods": high_vol_periods
        }

    def validate_data(self, data: pd.DataFrame) -> bool:
        """データの妥当性チェック"""
        if data.empty:
            return False
        
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_columns):
            return False
        
        if len(data) < 30:
            return False
        
        return True
