"""第 1 步：配置模型与 JSON 读写测试。"""

import json
import tempfile
import unittest
from pathlib import Path

from core.config import AppConfig, VpnEntry, load, save


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "config.json"

    def test_roundtrip(self):
        cfg = AppConfig(
            vpn_entries=[
                VpnEntry("RabbitPro", r"D:\rabbitpro\RabbitPro.exe"),
                VpnEntry("中文名", r"C:\带空格 路径\vpn.exe"),
            ],
            blacklist=["UIBE-WLAN", "UIBE-Guest"],
        )
        save(cfg, self.path)
        loaded, was_reset = load(self.path)
        self.assertFalse(was_reset)
        self.assertEqual(loaded.vpn_entries, cfg.vpn_entries)
        self.assertEqual(loaded.blacklist, cfg.blacklist)

    def test_missing_file(self):
        loaded, was_reset = load(self.path)
        self.assertFalse(was_reset)
        self.assertEqual(loaded.blacklist, ["UIBE-WLAN"])
        self.assertEqual(loaded.vpn_entries, [])

    def test_corrupt_file(self):
        self.path.write_text("{ not a json", encoding="utf-8")
        loaded, was_reset = load(self.path)
        self.assertTrue(was_reset)
        self.assertEqual(loaded.blacklist, ["UIBE-WLAN"])
        # 原损坏文件不被改写
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{ not a json")

    def test_atomic_save_no_temp_leftover(self):
        save(AppConfig(vpn_entries=[VpnEntry("X", r"D:\x\X.exe")], blacklist=["A"]), self.path)
        self.assertTrue(self.path.exists())
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_default_blacklist_when_key_missing(self):
        json_data = {"vpn_entries": [{"name": "n", "exe_path": "e"}]}
        self.path.write_text(json.dumps(json_data), encoding="utf-8")
        loaded, _ = load(self.path)
        self.assertEqual(loaded.blacklist, ["UIBE-WLAN"])
        self.assertEqual(loaded.vpn_entries, [VpnEntry("n", "e")])

    def test_empty_blacklist_preserved_if_provided(self):
        json_data = {"vpn_entries": [], "blacklist": []}
        self.path.write_text(json.dumps(json_data), encoding="utf-8")
        loaded, _ = load(self.path)
        self.assertEqual(loaded.blacklist, [])

    def test_missing_optional_keys_tolerated(self):
        self.path.write_text("{}", encoding="utf-8")
        loaded, was_reset = load(self.path)
        self.assertFalse(was_reset)
        self.assertEqual(loaded.blacklist, ["UIBE-WLAN"])
        self.assertEqual(loaded.vpn_entries, [])


if __name__ == "__main__":
    unittest.main()
