"""config/master.json の読み書き（アトミック更新）"""

import json
import os
from pathlib import Path


def load(config_dir: Path) -> dict:
    p = config_dir / "master.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(config_dir: Path, data: dict) -> None:
    p = config_dir / "master.json"
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
