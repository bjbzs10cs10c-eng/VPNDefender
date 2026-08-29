"""配置模型与 JSON 持久化。"""

import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path


def _base_dir() -> Path:
    """配置目录：打包后放在 exe 同级，脚本模式放在项目根目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


CONFIG_PATH = _base_dir() / "config.json"


@dataclass
class VpnEntry:
    """单个 VPN 软件条目。"""

    name: str
    exe_path: str


@dataclass
class AppConfig:
    """应用全局配置。"""

    vpn_entries: list[VpnEntry] = field(default_factory=list)
    blacklist: list[str] = field(default_factory=lambda: ["UIBE-WLAN"])

    def to_dict(self) -> dict:
        return {
            "vpn_entries": [asdict(entry) for entry in self.vpn_entries],
            "blacklist": self.blacklist,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        entries = [
            VpnEntry(name=item.get("name", ""), exe_path=item.get("exe_path", ""))
            for item in data.get("vpn_entries", [])
        ]
        blacklist = data.get("blacklist", ["UIBE-WLAN"])
        return cls(vpn_entries=entries, blacklist=list(blacklist))


def load(path: Path = CONFIG_PATH) -> tuple[AppConfig, bool]:
    """加载配置。

    返回 (AppConfig, was_reset)。was_reset 为 True 表示配置文件损坏、已回退到默认。
    文件不存在时按首次运行处理，was_reset 为 False。
    """
    if not path.exists():
        return AppConfig(), False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppConfig.from_dict(data), False
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return AppConfig(), True


def save(config: AppConfig, path: Path = CONFIG_PATH) -> None:
    """原子写配置：先写临时文件，再替换原文件。"""
    payload = json.dumps(config.to_dict(), ensure_ascii=False, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, str(path))
    except Exception:
        # 清理临时文件，避免残留
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
