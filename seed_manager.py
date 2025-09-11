"""
シード値と銘柄のマッピングを管理するモジュール
"""
import os
import json
import logging
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pytz

from data_loader import DataLoader
from cache_data_loader import CacheOnlyDataLoader

logger = logging.getLogger(__name__)


class SeedManager:
    """シード値と銘柄のマッピングを管理するクラス"""
    
    def __init__(self, seed_mapping_file: str = "seed_mapping.json"):
        self.seed_mapping_file = seed_mapping_file
        self.data_loader = DataLoader()
        self.cache_loader = CacheOnlyDataLoader()
        
    def _get_jst_datetime_str(self) -> str:
        """現在時刻をJSTで文字列として取得"""
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        return now.strftime('%Y-%m-%d %H:%M:%S JST')
    
    def load_seed_mapping(self) -> Dict:
        """シード値マッピングファイルを読み込み"""
        if os.path.exists(self.seed_mapping_file):
            try:
                with open(self.seed_mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"シード値マッピングファイルを読み込み: {len(data.get('mappings', {}))}件のマッピング")
                    return data
            except Exception as e:
                logger.error(f"シード値マッピングファイルの読み込みに失敗: {e}")
                return {"mappings": {}, "metadata": {}}
        else:
            logger.info("シード値マッピングファイルが存在しません。新規作成します。")
            return {"mappings": {}, "metadata": {}}
    
    def save_seed_mapping(self, data: Dict) -> None:
        """シード値マッピングファイルを保存"""
        try:
            # メタデータを更新
            data["metadata"]["last_updated"] = self._get_jst_datetime_str()
            data["metadata"]["version"] = data["metadata"].get("version", 0) + 1
            
            with open(self.seed_mapping_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"シード値マッピングファイルを保存: {self.seed_mapping_file}")
        except Exception as e:
            logger.error(f"シード値マッピングファイルの保存に失敗: {e}")
    
    def create_initial_seeds_from_cache(self, num_seeds: int = 10) -> Dict:
        """キャッシュに存在する銘柄から初期シード値を生成"""
        logger.info("キャッシュから初期シード値を生成開始")
        
        # キャッシュに存在する銘柄を取得
        cached_symbols = self.cache_loader.get_available_cached_symbols()
        logger.info(f"キャッシュに存在する銘柄数: {len(cached_symbols)}")
        
        if len(cached_symbols) == 0:
            logger.error("キャッシュに銘柄が存在しません")
            return {}
        
        # 各戦略の設定を取得
        strategy_configs = {
            "swing_trading": {"target_count": 100, "indices": ["SP500", "NASDAQ100", "NIKKEI225"]},
            "long_term": {"target_count": 50, "indices": ["SP500", "NIKKEI225"]},
            "momentum": {"target_count": 75, "indices": ["SP500", "NASDAQ100"]},
            "value": {"target_count": 60, "indices": ["SP500", "NIKKEI225"]},
            "growth": {"target_count": 80, "indices": ["SP500", "NASDAQ100"]}
        }
        
        mappings = {}
        base_seed = 42
        
        for strategy, config in strategy_configs.items():
            logger.info(f"{strategy}戦略のシード値を生成中...")
            strategy_mappings = {}
            
            for i in range(num_seeds):
                seed = base_seed + i
                random.seed(seed)
                
                # 各指数から銘柄を選択
                selected_symbols = []
                
                for index in config["indices"]:
                    try:
                        # 指数の全銘柄を取得
                        index_symbols = self.data_loader.get_stocks_by_index(index)
                        # キャッシュに存在する銘柄のみにフィルタ
                        available_symbols = [s for s in index_symbols if s in cached_symbols]
                        
                        if available_symbols:
                            # 戦略の目標数に応じて各指数から選択
                            target_per_index = config["target_count"] // len(config["indices"])
                            num_to_select = min(target_per_index, len(available_symbols))
                            selected = random.sample(available_symbols, num_to_select)
                            selected_symbols.extend(selected)
                            logger.debug(f"{index}: {num_to_select}銘柄選択 ({len(available_symbols)}中)")
                        else:
                            logger.warning(f"{index}: キャッシュに利用可能な銘柄がありません")
                            
                    except Exception as e:
                        logger.error(f"{index}の銘柄取得でエラー: {e}")
                
                # 重複を除去し、目標数まで調整
                selected_symbols = list(set(selected_symbols))
                if len(selected_symbols) > config["target_count"]:
                    selected_symbols = random.sample(selected_symbols, config["target_count"])
                
                strategy_mappings[str(seed)] = {
                    "symbols": selected_symbols,
                    "count": len(selected_symbols),
                    "created_at": self._get_jst_datetime_str(),
                    "strategy": strategy
                }
                
                logger.info(f"{strategy} シード{seed}: {len(selected_symbols)}銘柄選択")
            
            mappings[strategy] = strategy_mappings
        
        # マッピングデータを構築
        mapping_data = {
            "mappings": mappings,
            "metadata": {
                "created_at": self._get_jst_datetime_str(),
                "total_strategies": len(strategy_configs),
                "seeds_per_strategy": num_seeds,
                "base_seed": base_seed,
                "cached_symbols_count": len(cached_symbols)
            }
        }
        
        logger.info(f"初期シード値生成完了: {len(strategy_configs)}戦略 × {num_seeds}シード")
        return mapping_data
    
    def get_symbols_for_seed(self, strategy: str, seed: int) -> List[str]:
        """指定された戦略とシード値に対応する銘柄リストを取得"""
        data = self.load_seed_mapping()
        
        if strategy not in data.get("mappings", {}):
            logger.error(f"戦略 '{strategy}' のマッピングが見つかりません")
            return []
        
        strategy_mappings = data["mappings"][strategy]
        
        if str(seed) not in strategy_mappings:
            logger.error(f"シード値 {seed} のマッピングが見つかりません")
            return []
        
        symbols = strategy_mappings[str(seed)]["symbols"]
        logger.info(f"{strategy} シード{seed}: {len(symbols)}銘柄を取得")
        return symbols
    
    def get_latest_seed_for_strategy(self, strategy: str) -> Optional[int]:
        """指定された戦略の最新シード値を取得"""
        data = self.load_seed_mapping()
        
        if strategy not in data.get("mappings", {}):
            logger.error(f"戦略 '{strategy}' のマッピングが見つかりません")
            return None
        
        strategy_mappings = data["mappings"][strategy]
        
        if not strategy_mappings:
            logger.error(f"戦略 '{strategy}' にシード値が登録されていません")
            return None
        
        # シード値を数値として並び替えて最新を取得
        seeds = [int(k) for k in strategy_mappings.keys()]
        latest_seed = max(seeds)
        
        logger.info(f"{strategy}の最新シード値: {latest_seed}")
        return latest_seed
    
    def add_new_seed_mapping(self, strategy: str, seed: int, symbols: List[str]) -> None:
        """新しいシード値マッピングを追加"""
        data = self.load_seed_mapping()
        
        if strategy not in data["mappings"]:
            data["mappings"][strategy] = {}
        
        data["mappings"][strategy][str(seed)] = {
            "symbols": symbols,
            "count": len(symbols),
            "created_at": self._get_jst_datetime_str(),
            "strategy": strategy
        }
        
        self.save_seed_mapping(data)
        logger.info(f"新しいシード値マッピングを追加: {strategy} シード{seed} ({len(symbols)}銘柄)")
    
    def get_mapping_summary(self) -> Dict:
        """マッピングの概要を取得"""
        data = self.load_seed_mapping()
        summary = {
            "total_strategies": len(data.get("mappings", {})),
            "strategies": {}
        }
        
        for strategy, mappings in data.get("mappings", {}).items():
            summary["strategies"][strategy] = {
                "seed_count": len(mappings),
                "seeds": list(mappings.keys()),
                "total_symbols": sum(m["count"] for m in mappings.values())
            }
        
        return summary
    
    def create_random_seed_for_strategy(self, strategy: str, target_count: int = None) -> Tuple[int, List[str]]:
        """指定された戦略用にランダムなシード値と銘柄を生成（保存しない）"""
        logger.info(f"{strategy}戦略用のランダムシード値を生成")
        
        # 戦略設定
        strategy_configs = {
            "swing_trading": {"target_count": 100, "indices": ["SP500", "NASDAQ100", "NIKKEI225"]},
            "long_term": {"target_count": 50, "indices": ["SP500", "NIKKEI225"]},
            "momentum": {"target_count": 75, "indices": ["SP500", "NASDAQ100"]},
            "value": {"target_count": 60, "indices": ["SP500", "NIKKEI225"]},
            "growth": {"target_count": 80, "indices": ["SP500", "NASDAQ100"]}
        }
        
        if strategy not in strategy_configs:
            logger.error(f"未知の戦略: {strategy}")
            return None, []
        
        config = strategy_configs[strategy]
        if target_count is None:
            target_count = config["target_count"]
        
        # ランダムシード値を生成
        random_seed = random.randint(1000, 9999)
        random.seed(random_seed)
        
        # キャッシュに存在する銘柄を取得
        cached_symbols = self.cache_loader.get_available_cached_symbols()
        logger.info(f"キャッシュに存在する銘柄数: {len(cached_symbols)}")
        
        # 各指数から銘柄を選択
        selected_symbols = []
        
        for index in config["indices"]:
            try:
                # 指数の全銘柄を取得
                index_symbols = self.data_loader.get_stocks_by_index(index)
                # キャッシュに存在する銘柄のみにフィルタ
                available_symbols = [s for s in index_symbols if s in cached_symbols]
                
                if available_symbols:
                    # 戦略の目標数に応じて各指数から選択
                    target_per_index = target_count // len(config["indices"])
                    num_to_select = min(target_per_index, len(available_symbols))
                    selected = random.sample(available_symbols, num_to_select)
                    selected_symbols.extend(selected)
                    logger.debug(f"{index}: {num_to_select}銘柄選択 ({len(available_symbols)}中)")
                    
            except Exception as e:
                logger.error(f"{index}の銘柄取得でエラー: {e}")
        
        # 重複を除去し、目標数まで調整
        selected_symbols = list(set(selected_symbols))
        if len(selected_symbols) > target_count:
            selected_symbols = random.sample(selected_symbols, target_count)
        
        logger.info(f"{strategy} ランダムシード{random_seed}: {len(selected_symbols)}銘柄選択")
        return random_seed, selected_symbols
