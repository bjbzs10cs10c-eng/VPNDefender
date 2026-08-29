"""VPNDefender 程序入口：管理员提权 + 启动 GUI。"""

import ctypes
import os
import sys


def is_admin() -> bool:
    """判断当前进程是否以管理员权限运行。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """用 runas 以管理员身份重新启动自身。返回是否成功发起。"""
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    if getattr(sys, "frozen", False):
        # 打包后 sys.executable 即 exe，直接以管理员重新启动 exe
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    else:
        script = os.path.abspath(sys.argv[0])
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
    return ret > 32


def decide_admin_action(is_admin_value: bool, relaunch_success: bool) -> str:
    """根据提权结果决定动作：run / relaunch / cancel。"""
    if is_admin_value:
        return "run"
    if relaunch_success:
        return "relaunch"
    return "cancel"


def run_app() -> None:
    """加载配置并启动图形界面。"""
    from core.config import load
    from ui.main_window import MainWindow

    config_data, _ = load()
    try:
        win = MainWindow(config_data=config_data)
    except Exception as exc:  # noqa: BLE001
        print(f"无法启动图形界面：{exc}")
        print("请使用安装了 Tk 的完整 Python 运行本程序。")
        return
    win.mainloop()


def main() -> int:
    """程序主流程。返回退出码。"""
    is_admin_value = is_admin()
    relaunch_success = relaunch_as_admin() if not is_admin_value else False
    action = decide_admin_action(is_admin_value, relaunch_success)
    if action == "run":
        run_app()
        return 0
    if action == "relaunch":
        return 0
    print("需要管理员权限（已取消提权）才能读取/断开 Wi-Fi。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
