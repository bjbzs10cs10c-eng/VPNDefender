"""第 5 步：主窗口 smoke 测试（无显示环境自动跳过）。"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import starter
from core.config import AppConfig, VpnEntry
from ui.main_window import (
    NO_SELECTION_TEXT,
    run_launcher,
    status_text_for,
)


class StartFlowLogicTest(unittest.TestCase):
    """不依赖 Tk 的“启动”集成逻辑测试。"""

    def test_run_launcher_passes_through(self):
        calls = {}

        def fake_launcher(entry, cfg, wlan):
            calls["entry"] = entry
            calls["cfg"] = cfg
            calls["wlan"] = wlan
            return "blocked", "UIBE-WLAN"

        cfg = AppConfig()
        entry = VpnEntry("RabbitPro", r"D:\rabbitpro\RabbitPro.exe")
        result, ssid = run_launcher(entry, cfg, "fake-wlan", fake_launcher)
        self.assertEqual(result, "blocked")
        self.assertEqual(ssid, "UIBE-WLAN")
        self.assertIs(calls["entry"], entry)
        self.assertIs(calls["cfg"], cfg)
        self.assertEqual(calls["wlan"], "fake-wlan")

    def test_run_launcher_captures_error(self):
        def bad_launcher(entry, cfg, wlan):
            raise RuntimeError("boom")

        result, info = run_launcher(VpnEntry("x", "y"), AppConfig(), None, bad_launcher)
        self.assertEqual(result, "error")
        self.assertIn("boom", info)

    def test_status_text_blocked(self):
        self.assertEqual(
            status_text_for("blocked", "RabbitPro", "UIBE-WLAN"),
            "已在校园网 UIBE-WLAN 下拦截，未启动。",
        )

    def test_status_text_launched(self):
        self.assertEqual(status_text_for("launched", "RabbitPro", None), "已启动：RabbitPro")

    def test_status_text_error(self):
        self.assertEqual(status_text_for("error", ssid="boom"), "启动失败：boom")

    def test_no_selection_text(self):
        self.assertEqual(NO_SELECTION_TEXT, "请先选择一个 VPN 软件。")


def _make_window():
    from ui.main_window import MainWindow

    tmp = tempfile.TemporaryDirectory()
    cfg_path = Path(tmp.name) / "config.json"
    cfg = AppConfig(
        vpn_entries=[VpnEntry("RabbitPro", r"D:\rabbitpro\RabbitPro.exe")],
        blacklist=["UIBE-WLAN"],
    )
    win = MainWindow(config_data=cfg, config_path=cfg_path)
    return win


class GuiSmokeTest(unittest.TestCase):
    def test_window_builds_and_lists_sync(self):
        try:
            win = _make_window()
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"无法初始化 Tk：{exc}")
        try:
            rows = win.vpn_tree.get_children()
            self.assertEqual(len(rows), 1)
            self.assertEqual(win.vpn_tree.item(rows[0], "values")[0], "RabbitPro")
            self.assertEqual(win.blacklist_list.size(), 1)
            self.assertEqual(win.blacklist_list.get(0), "UIBE-WLAN")
        finally:
            win.destroy()

    def test_on_start_blocked_shows_exact_message(self):
        try:
            win = _make_window()
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"无法初始化 Tk：{exc}")
        try:
            win.launcher = lambda entry, cfg, wlan: ("blocked", "UIBE-WLAN")
            win.vpn_tree.selection_set(win.vpn_tree.get_children()[0])
            with mock.patch("ui.main_window.messagebox.showwarning") as warn:
                win._on_start()
            warn.assert_called_once_with("已拦截", starter.BLOCKED_TEXT)
            self.assertEqual(win.status_var.get(), "已在校园网 UIBE-WLAN 下拦截，未启动。")
        finally:
            win.destroy()

    def test_on_start_launched_sets_status(self):
        try:
            win = _make_window()
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"无法初始化 Tk：{exc}")
        try:
            win.launcher = lambda entry, cfg, wlan: ("launched", None)
            win.vpn_tree.selection_set(win.vpn_tree.get_children()[0])
            with mock.patch("ui.main_window.messagebox.showwarning") as warn:
                win._on_start()
            warn.assert_not_called()
            self.assertEqual(win.status_var.get(), "已启动：RabbitPro")
        finally:
            win.destroy()

    def test_on_start_no_selection_sets_status(self):
        try:
            win = _make_window()
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"无法初始化 Tk：{exc}")
        try:
            win.vpn_tree.selection_remove(*win.vpn_tree.get_children())
            win._on_start()
            self.assertEqual(win.status_var.get(), "请先选择一个 VPN 软件。")
        finally:
            win.destroy()


if __name__ == "__main__":
    unittest.main()
