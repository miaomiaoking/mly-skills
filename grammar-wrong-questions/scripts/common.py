"""公共路径与配置：所有脚本都从这里取，避免硬编码。"""
import json, os
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = SKILL_ROOT / "config.json"

def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    cwd = Path.cwd()
    cfg["_data"] = cwd / cfg.get("data_dir", ".grammar_wrong")
    cfg["_out"] = (cwd / cfg.get("output_dir", ".")).resolve()
    cfg["_data"].mkdir(parents=True, exist_ok=True)
    cfg["_out"].mkdir(parents=True, exist_ok=True)
    return cfg

def state_path(cfg):
    return cfg["_data"] / "gi_state.json"

def wrong_json(cfg):
    return cfg["_data"] / "wrong_all.json"

def dict_json(cfg):
    return cfg["_data"] / "dict_points.json"

def prefix(cfg):
    return cfg.get("file_prefix", "语法错题整理")
