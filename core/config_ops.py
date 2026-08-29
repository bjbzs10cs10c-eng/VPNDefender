"""配置数据操作（增/删/改），纯逻辑便于测试。"""

from .config import VpnEntry


def add_vpn(config, name: str, path: str) -> tuple[bool, str]:
    """添加 VPN 条目。返回 (是否成功, 提示信息)。"""
    name = (name or "").strip()
    path = (path or "").strip()
    if not name or not path:
        return False, "显示名称与路径都不能为空。"
    duplicate = any(e.name == name for e in config.vpn_entries)
    config.vpn_entries.append(VpnEntry(name=name, exe_path=path))
    return True, ("建议显示名称唯一。" if duplicate else "")


def update_vpn(config, index: int, name: str, path: str) -> tuple[bool, str]:
    """修改指定位置 VPN 条目。"""
    name = (name or "").strip()
    path = (path or "").strip()
    if not name or not path:
        return False, "显示名称与路径都不能为空。"
    if not (0 <= index < len(config.vpn_entries)):
        return False, "无效的条目。"
    config.vpn_entries[index].name = name
    config.vpn_entries[index].exe_path = path
    return True, ""


def delete_vpn(config, index: int) -> tuple[bool, str]:
    """删除指定位置 VPN 条目。"""
    if not (0 <= index < len(config.vpn_entries)):
        return False, "无效的条目。"
    del config.vpn_entries[index]
    return True, ""


def add_blacklist(config, name: str) -> tuple[bool, str]:
    """添加黑名单网络名称。"""
    name = (name or "").strip()
    if not name:
        return False, "网络名称不能为空。"
    if name in config.blacklist:
        return False, "该网络名称已存在。"
    config.blacklist.append(name)
    return True, ""


def delete_blacklist(config, name: str) -> tuple[bool, str]:
    """删除黑名单网络名称。"""
    if name in config.blacklist:
        config.blacklist.remove(name)
        return True, ""
    return False, "该网络名称不存在。"
