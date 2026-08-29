"""第 0 步：骨架与环境 smoke 测试。"""

import sys
import unittest


class SmokeTest(unittest.TestCase):
    def test_import_all_modules(self):
        import app  # noqa: F401
        import core.config  # noqa: F401
        import wlan.wrapper  # noqa: F401
        import ui.main_window  # noqa: F401

    def test_default_config_has_uibe(self):
        from core.config import AppConfig

        cfg = AppConfig()
        self.assertIn("UIBE-WLAN", cfg.blacklist)

    def test_runtime_version(self):
        self.assertGreaterEqual(sys.version_info[:2], (3, 10))


if __name__ == "__main__":
    unittest.main()
