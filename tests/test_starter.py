"""第 4 步：启动流程编排测试（mock wlan + subprocess）。"""

import unittest
from unittest import mock

from core import starter
from core.config import AppConfig, VpnEntry
from core.starter import start


class FakeWlan:
    def __init__(self, ssid, disconnect_result=True):
        self.ssid = ssid
        self.disconnect_result = disconnect_result
        self.disconnect_calls = 0

    def get_current_ssid(self):
        return self.ssid

    def disconnect(self):
        self.disconnect_calls += 1
        return self.disconnect_result


class StarterTest(unittest.TestCase):
    def setUp(self):
        self.entry = VpnEntry("RabbitPro", r"D:\rabbitpro\RabbitPro.exe")
        self.config = AppConfig(blacklist=["UIBE-WLAN"])

    def test_blacklist_blocks_and_disconnects(self):
        wlan = FakeWlan("UIBE-WLAN")
        with mock.patch.object(starter.subprocess, "Popen") as popen:
            result, ssid = start(self.entry, self.config, wlan)
        self.assertEqual(result, "blocked")
        self.assertEqual(ssid, "UIBE-WLAN")
        self.assertEqual(wlan.disconnect_calls, 1)
        popen.assert_not_called()

    def test_whitelist_launches(self):
        wlan = FakeWlan("HomeWiFi")
        with mock.patch.object(starter.subprocess, "Popen") as popen:
            result, ssid = start(self.entry, self.config, wlan)
        self.assertEqual(result, "launched")
        self.assertEqual(ssid, "HomeWiFi")
        popen.assert_called_once_with([r"D:\rabbitpro\RabbitPro.exe"], shell=False)

    def test_no_ssid_launches(self):
        wlan = FakeWlan(None)
        with mock.patch.object(starter.subprocess, "Popen") as popen:
            result, ssid = start(self.entry, self.config, wlan)
        self.assertEqual(result, "launched")
        self.assertIsNone(ssid)
        popen.assert_called_once()

    def test_case_sensitive_match(self):
        wlan = FakeWlan("uibe-wlan")
        with mock.patch.object(starter.subprocess, "Popen") as popen:
            result, ssid = start(self.entry, self.config, wlan)
        self.assertEqual(result, "launched")
        self.assertEqual(ssid, "uibe-wlan")
        popen.assert_called_once()

    def test_disconnect_failure_still_blocks(self):
        wlan = FakeWlan("UIBE-WLAN", disconnect_result=False)
        with mock.patch.object(starter.subprocess, "Popen") as popen:
            result, _ = start(self.entry, self.config, wlan)
        self.assertEqual(result, "blocked")
        self.assertEqual(wlan.disconnect_calls, 1)
        popen.assert_not_called()

    def test_path_with_spaces(self):
        entry = VpnEntry("S", r"C:\Program Files\VPN\app.exe")
        with mock.patch.object(starter.subprocess, "Popen") as popen:
            result, _ = start(entry, self.config, FakeWlan("Home"))
        self.assertEqual(result, "launched")
        popen.assert_called_once_with([r"C:\Program Files\VPN\app.exe"], shell=False)

    def test_blocked_text_constant(self):
        self.assertEqual(starter.BLOCKED_TEXT, "不要通过校园网使用vpn，已为您断开校园网。")


if __name__ == "__main__":
    unittest.main()
