"""第 5 步：配置数据操作测试（纯逻辑，无需 GUI）。"""

import unittest

from core.config import AppConfig, VpnEntry
from core.config_ops import (
    add_blacklist,
    add_vpn,
    delete_blacklist,
    delete_vpn,
    update_vpn,
)


class ConfigOpsTest(unittest.TestCase):
    def test_add_vpn_rejects_empty(self):
        cfg = AppConfig()
        ok, msg = add_vpn(cfg, "", r"D:\v.exe")
        self.assertFalse(ok)
        self.assertIn("不能为空", msg)
        self.assertEqual(cfg.vpn_entries, [])

    def test_add_vpn_valid(self):
        cfg = AppConfig()
        ok, _ = add_vpn(cfg, "RabbitPro", r"D:\rabbitpro\RabbitPro.exe")
        self.assertTrue(ok)
        self.assertEqual(cfg.vpn_entries, [VpnEntry("RabbitPro", r"D:\rabbitpro\RabbitPro.exe")])

    def test_add_vpn_duplicate_warns_but_saves(self):
        cfg = AppConfig(vpn_entries=[VpnEntry("A", r"D:\a\a.exe")])
        ok, msg = add_vpn(cfg, "A", r"D:\a2\b.exe")
        self.assertTrue(ok)
        self.assertIn("建议显示名称唯一", msg)
        self.assertEqual(len(cfg.vpn_entries), 2)

    def test_update_vpn(self):
        cfg = AppConfig(vpn_entries=[VpnEntry("A", r"D:\a\a.exe")])
        ok, _ = update_vpn(cfg, 0, "B", r"D:\b\b.exe")
        self.assertTrue(ok)
        self.assertEqual(cfg.vpn_entries[0], VpnEntry("B", r"D:\b\b.exe"))

    def test_update_vpn_out_of_range(self):
        cfg = AppConfig(vpn_entries=[VpnEntry("A", r"D:\a\a.exe")])
        ok, msg = update_vpn(cfg, 5, "B", r"D:\b\b.exe")
        self.assertFalse(ok)
        self.assertIn("无效", msg)

    def test_delete_vpn(self):
        cfg = AppConfig(vpn_entries=[VpnEntry("A", r"D:\a\a.exe")])
        ok, _ = delete_vpn(cfg, 0)
        self.assertTrue(ok)
        self.assertEqual(cfg.vpn_entries, [])

    def test_delete_vpn_out_of_range(self):
        cfg = AppConfig()
        ok, _ = delete_vpn(cfg, 0)
        self.assertFalse(ok)

    def test_add_blacklist_rejects_empty_and_duplicate(self):
        cfg = AppConfig(blacklist=[])
        ok, _ = add_blacklist(cfg, "  ")
        self.assertFalse(ok)
        ok, _ = add_blacklist(cfg, "UIBE-WLAN")
        self.assertTrue(ok)
        ok, msg = add_blacklist(cfg, "UIBE-WLAN")
        self.assertFalse(ok)
        self.assertIn("已存在", msg)

    def test_delete_blacklist(self):
        cfg = AppConfig(blacklist=["UIBE-WLAN", "A"])
        ok, _ = delete_blacklist(cfg, "UIBE-WLAN")
        self.assertTrue(ok)
        self.assertEqual(cfg.blacklist, ["A"])
        ok, _ = delete_blacklist(cfg, "不存在")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
