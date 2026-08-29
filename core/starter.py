"""启动流程编排：读 SSID → 判断黑名单 → 拦截/启动。"""

import subprocess

BLOCKED_TEXT = "不要通过校园网使用vpn，已为您断开校园网。"


def _launch(exe_path: str) -> None:
    """以非阻塞方式启动 vpn exe。"""
    subprocess.Popen([exe_path], shell=False)


def start(vpn_entry, config, wlan) -> tuple[str, str | None]:
    """执行启动流程。

    返回 (result, ssid)，result 为 ``"blocked"`` 或 ``"launched"``。
    - 命中黑名单：断开并返回 ``blocked``（即使断开失败也拦截）。
    - 未命中或未连接：正常启动 exe。
    """
    ssid = wlan.get_current_ssid()
    if ssid is not None and ssid in config.blacklist:
        wlan.disconnect()
        return ("blocked", ssid)
    _launch(vpn_entry.exe_path)
    return ("launched", ssid)
