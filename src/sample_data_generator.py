"""
サンプルデータ生成モジュール
テスト用の株価データを生成
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List
import os


class SampleDataGenerator:
    def __init__(self, cache_dir: str = "cache"):
        """サンプルデータ生成クラスの初期化"""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def generate_sample_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """サンプル株価データを生成"""
        # 日付範囲を生成
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        dates = pd.date_range(start=start, end=end, freq='D')
        
        # 営業日のみにフィルタリング（土日を除外）
        dates = dates[dates.weekday < 5]
        
        # 初期価格を設定
        initial_price = 100.0
        
        # ランダムウォークで価格を生成
        np.random.seed(hash(symbol) % 2**32)  # シンボルに基づくシード
        returns = np.random.normal(0.001, 0.02, len(dates))  # 平均0.1%、標準偏差2%の日次リターン
        prices = [initial_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(max(new_price, 1.0))  # 価格が1ドル未満にならないように
        
        # OHLCVデータを生成
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # 高値・安値を生成
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            
            # 始値（前日の終値）
            open_price = prices[i-1] if i > 0 else price
            
            # 出来高を生成
            volume = int(np.random.normal(1000000, 200000))
            volume = max(volume, 100000)  # 最小出来高
            
            data.append({
                'Open': open_price,
                'High': high,
                'Low': low,
                'Close': price,
                'Volume': volume
            })
        
        # DataFrameを作成
        df = pd.DataFrame(data, index=dates)
        df.columns = [col.lower() for col in df.columns]
        
        return df
    
    def create_sample_cache(self, symbols: List[str], start_date: str, end_date: str):
        """サンプルキャッシュファイルを作成"""
        print(f"サンプルデータを生成中: {len(symbols)}銘柄")
        
        for symbol in symbols:
            try:
                # サンプルデータを生成
                data = self.generate_sample_data(symbol, start_date, end_date)
                
                # キャッシュファイルに保存
                cache_file = os.path.join(self.cache_dir, f"{symbol.replace('.', '_')}.pkl")
                data.to_pickle(cache_file)
                
                print(f"✅ サンプルデータ生成完了: {symbol} ({len(data)}日分)")
                
            except Exception as e:
                print(f"❌ サンプルデータ生成エラー {symbol}: {e}")
    
    def create_vix_sample_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """VIXサンプルデータを生成"""
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        dates = pd.date_range(start=start, end=end, freq='D')
        dates = dates[dates.weekday < 5]  # 営業日のみ
        
        # VIXは10-50の範囲で変動
        vix_values = []
        current_vix = 20.0
        
        for date in dates:
            # VIXの変動（市場のボラティリティを反映）
            change = np.random.normal(0, 2.0)
            current_vix += change
            current_vix = max(10.0, min(50.0, current_vix))  # 10-50の範囲に制限
            vix_values.append(current_vix)
        
        df = pd.DataFrame({'VIX': vix_values}, index=dates)
        return df


def main():
    """サンプルデータ生成のメイン実行"""
    generator = SampleDataGenerator()
    
    # 対象銘柄
    symbols = [
        "AAPL.US", "MSFT.US", "GOOGL.US", "AMZN.US", "TSLA.US",
        "META.US", "NVDA.US", "BRK-B.US", "UNH.US", "JNJ.US",
        "NFLX.US"
    ]
    
    # データ期間
    start_date = "2020-01-01"
    end_date = "2024-12-31"
    
    print("🎲 サンプルデータを生成しています...")
    generator.create_sample_cache(symbols, start_date, end_date)
    
    # VIXサンプルデータも生成
    vix_data = generator.create_vix_sample_data(start_date, end_date)
    vix_file = os.path.join(generator.cache_dir, "VIX.pkl")
    vix_data.to_pickle(vix_file)
    print(f"✅ VIXサンプルデータ生成完了: {len(vix_data)}日分")
    
    print("\n🎉 サンプルデータ生成が完了しました！")
    print("これで `python main.py` を実行できます。")


if __name__ == "__main__":
    main()
