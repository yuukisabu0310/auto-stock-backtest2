#!/usr/bin/env python3
"""
戦略条件表示のテストスクリプト
"""

from report_generator import ReportGenerator
from config import TRADING_RULES

def test_strategy_conditions():
    """戦略条件の表示をテスト"""
    generator = ReportGenerator()
    
    # テスト用の結果データ
    test_results = {
        "total_return": 0.15,
        "sharpe_ratio": 1.2,
        "max_drawdown": -0.08,
        "win_rate": 0.65,
        "total_trades": 50,
        "avg_profit": 0.05,
        "avg_loss": -0.03,
        "equity_curve": {
            "dates": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "values": [1000000, 1010000, 1020000]
        },
        "trades": [
            {
                "symbol": "AAPL",
                "entry_date": "2020-01-01",
                "exit_date": "2020-01-02",
                "entry_price": 100,
                "exit_price": 105,
                "quantity": 100,
                "profit_loss": 500,
                "profit_loss_pct": 0.05,
                "holding_days": 1,
                "exit_reason": "profit_target"
            }
        ]
    }
    
    # スイングトレード戦略のレポート生成
    print("スイングトレード戦略のレポート生成中...")
    report_file = generator.generate_strategy_report(test_results, "スイングトレード")
    
    if report_file:
        print(f"✅ レポート生成完了: {report_file}")
        
        # 戦略条件の確認
        conditions = generator._get_strategy_conditions("スイングトレード")
        print(f"\n📋 戦略条件:")
        print(f"時間足: {conditions.get('timeframe', 'N/A')}")
        print(f"最大保有日数: {conditions.get('max_holding_days', 'N/A')}日")
        print(f"最大ポジション数: {conditions.get('max_positions', 'N/A')}銘柄")
        print(f"取引リスク: {conditions.get('risk_per_trade', 0)*100:.1f}%")
        
        # エントリー条件
        entry_conditions = conditions.get('entry_conditions', {})
        print(f"\n📈 エントリー条件:")
        for condition, value in entry_conditions.items():
            translated = generator._translate_condition_name(condition)
            if isinstance(value, bool):
                status = "✅ 有効" if value else "❌ 無効"
                print(f"  {translated}: {status}")
            else:
                print(f"  {translated}: {value}")
        
        # エグジット条件
        exit_conditions = conditions.get('exit_conditions', {})
        print(f"\n📉 エグジット条件:")
        for condition, value in exit_conditions.items():
            translated = generator._translate_condition_name(condition)
            if isinstance(value, bool):
                status = "✅ 有効" if value else "❌ 無効"
                print(f"  {translated}: {status}")
            elif isinstance(value, dict):
                print(f"  {translated}:")
                for sub_key, sub_value in value.items():
                    translated_sub = generator._translate_condition_name(sub_key)
                    print(f"    {translated_sub}: {sub_value}")
            else:
                print(f"  {translated}: {value}")
    else:
        print("❌ レポート生成に失敗しました")

if __name__ == "__main__":
    test_strategy_conditions()
