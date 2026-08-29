"""第 7 步：管理员提权逻辑测试。"""

import unittest
from unittest import mock

import app


class ElevationTest(unittest.TestCase):
    def test_decide_run_when_admin(self):
        self.assertEqual(app.decide_admin_action(True, False), "run")

    def test_decide_relaunch(self):
        self.assertEqual(app.decide_admin_action(False, True), "relaunch")

    def test_decide_cancel(self):
        self.assertEqual(app.decide_admin_action(False, False), "cancel")

    def test_main_admin_runs_app(self):
        with mock.patch.object(app, "is_admin", return_value=True), mock.patch.object(
            app, "run_app"
        ) as run, mock.patch.object(app, "relaunch_as_admin") as rel:
            code = app.main()
        self.assertEqual(code, 0)
        run.assert_called_once()
        rel.assert_not_called()

    def test_main_non_admin_relaunches(self):
        with mock.patch.object(app, "is_admin", return_value=False), mock.patch.object(
            app, "relaunch_as_admin", return_value=True
        ) as rel, mock.patch.object(app, "run_app") as run:
            code = app.main()
        self.assertEqual(code, 0)
        rel.assert_called_once()
        run.assert_not_called()

    def test_main_non_admin_cancel(self):
        with mock.patch.object(app, "is_admin", return_value=False), mock.patch.object(
            app, "relaunch_as_admin", return_value=False
        ), mock.patch.object(app, "run_app") as run:
            code = app.main()
        self.assertEqual(code, 1)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
