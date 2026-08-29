"""Windows WLAN API 封装（读取 SSID / 断开连接）。"""

import ctypes
from ctypes import wintypes

WLAN_CLIENT_VERSION = 2
WLAN_SUCCEEDED = 0
WLAN_INTERFACE_STATE_CONNECTED = 1
wlan_intf_opcode_current_connection = 7


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class DOT11_SSID(ctypes.Structure):
    _fields_ = [
        ("uSSIDLength", ctypes.c_ulong),
        ("ucSSID", ctypes.c_ubyte * 32),
    ]


class WLAN_INTERFACE_INFO(ctypes.Structure):
    _fields_ = [
        ("InterfaceGuid", GUID),
        ("strInterfaceDescription", wintypes.WCHAR * 256),
        ("isState", wintypes.ULONG),
    ]


class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
    _fields_ = [
        ("dwNumberOfItems", wintypes.DWORD),
        ("dwIndex", wintypes.DWORD),
        ("InterfaceInfo", WLAN_INTERFACE_INFO * 1),
    ]


class WLAN_CONNECTION_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("isState", wintypes.ULONG),
        ("wlanConnectionMode", wintypes.DWORD),
        ("dot11Ssid", DOT11_SSID),
        ("dot11BssType", wintypes.DWORD),
        ("dot11Bssid", ctypes.c_ubyte * 6),
        ("ulRxRate", wintypes.ULONG),
        ("ulTxRate", wintypes.ULONG),
    ]


def _decode_ssid(length: int, raw) -> str:
    """将 SSID 字节数组解码为字符串。"""
    return bytes(raw)[: int(length)].decode("utf-8", errors="replace")


def _attributes_ssid(attrs) -> str:
    """从 WLAN_CONNECTION_ATTRIBUTES 提取 SSID 字符串。"""
    ssid = attrs.dot11Ssid
    return _decode_ssid(ssid.uSSIDLength, ssid.ucSSID)


def _extract_ssid(raw: bytes) -> str | None:
    """从连接属性缓冲中稳健提取 SSID。

    兼容两种情况：
    - 标准布局（uSSIDLength + utf-8 ucSSID）；
    - Windows 实测以 UTF-16LE 直接存放的 SSID（无长度前缀）。
    WLAN_CONNECTION_ATTRIBUTES 中 DOT11_SSID 位于偏移 8（isState 4 + wlanConnectionMode 4）。
    注意：不能按固定长度截断，否则超过 18 个 UTF-16 字符的 SSID 会被切掉。
    """
    if len(raw) < 8:
        return None
    body = raw[8:]
    # 标准布局：4 字节长度 + utf-8 ucSSID（ucSSID 最多 32 字节）
    if len(body) >= 4:
        length = int.from_bytes(body[:4], "little")
        if 1 <= length <= 32:
            candidate = body[4 : 4 + length].decode("utf-8", errors="replace")
            if candidate and candidate.isprintable():
                return candidate.strip()
    # 实测：SSID 以 UTF-16LE 直接存放（无长度前缀），NUL 结尾。
    # SSID 原始最大 32 字节，UTF-16 最多 64 字节，取 96 字节为裕量。
    if len(body) >= 2 and body[1] == 0:
        text = body[: min(len(body), 96)].decode("utf-16-le", errors="replace")
        text = text.split("\x00")[0]
        return text.strip() or None
    # 兜底：UTF-8/ASCII，NUL 结尾
    text = body.split(b"\x00")[0].decode("utf-8", errors="replace")
    return text.strip() or None


class WlanBackend:
    """封装 Windows WLAN API 的 ctypes 调用。"""

    def __init__(self) -> None:
        self._api = ctypes.WinDLL("wlanapi.dll")
        self._configure()

    def _configure(self) -> None:
        a = self._api
        a.WlanOpenHandle.argtypes = [
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.PDWORD,
            wintypes.PHANDLE,
        ]
        a.WlanOpenHandle.restype = wintypes.DWORD

        a.WlanEnumInterfaces.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            ctypes.POINTER(ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)),
        ]
        a.WlanEnumInterfaces.restype = wintypes.DWORD

        a.WlanQueryInterface.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(GUID),
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.PDWORD,
            ctypes.POINTER(wintypes.LPVOID),
            ctypes.POINTER(wintypes.DWORD),
        ]
        a.WlanQueryInterface.restype = wintypes.DWORD

        a.WlanDisconnect.argtypes = [wintypes.HANDLE, ctypes.POINTER(GUID), wintypes.LPVOID]
        a.WlanDisconnect.restype = wintypes.DWORD

        a.WlanCloseHandle.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
        a.WlanCloseHandle.restype = wintypes.DWORD

        a.WlanFreeMemory.argtypes = [wintypes.LPVOID]
        a.WlanFreeMemory.restype = None

    def open(self) -> int:
        handle = wintypes.HANDLE()
        negotiated = wintypes.DWORD()
        ret = self._api.WlanOpenHandle(
            WLAN_CLIENT_VERSION, None, ctypes.byref(negotiated), ctypes.byref(handle)
        )
        if ret != WLAN_SUCCEEDED:
            raise OSError(f"WlanOpenHandle 失败，错误码 {ret}")
        return handle.value

    def enum_interfaces(self, handle: int):
        ptr = ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)()
        ret = self._api.WlanEnumInterfaces(handle, None, ctypes.byref(ptr))
        if ret != WLAN_SUCCEEDED:
            raise OSError(f"WlanEnumInterfaces 失败，错误码 {ret}")
        if not ptr:
            return []
        try:
            lst = ptr.contents
            return [
                (lst.InterfaceInfo[i].InterfaceGuid, lst.InterfaceInfo[i].isState)
                for i in range(lst.dwNumberOfItems)
            ]
        finally:
            self._api.WlanFreeMemory(ptr)

    def query_ssid(self, handle: int, guid) -> str | None:
        size = wintypes.DWORD()
        data = wintypes.LPVOID()
        opcode_type = wintypes.DWORD()
        ret = self._api.WlanQueryInterface(
            handle,
            ctypes.byref(guid),
            wlan_intf_opcode_current_connection,
            None,
            ctypes.byref(size),
            ctypes.byref(data),
            ctypes.byref(opcode_type),
        )
        if ret != WLAN_SUCCEEDED:
            # 读取当前连接需要管理员权限；失败时不要“当作没网”，否则会误放行
            raise OSError(f"读取 Wi-Fi SSID 失败，错误码 {ret}")
        try:
            if not data.value:
                return None
            raw = ctypes.string_at(data.value, int(size.value))
            return _extract_ssid(raw)
        finally:
            self._api.WlanFreeMemory(data)

    def disconnect(self, handle: int, guid) -> bool:
        ret = self._api.WlanDisconnect(handle, ctypes.byref(guid), None)
        return ret == WLAN_SUCCEEDED

    def close(self, handle: int) -> None:
        self._api.WlanCloseHandle(handle, None)


_backend: WlanBackend = WlanBackend()


def get_current_ssid() -> str | None:
    """返回当前连接 WiFi 的 SSID；未连接或没有接口时返回 None。"""
    handle = _backend.open()
    try:
        interfaces = _backend.enum_interfaces(handle)
        for guid, state in interfaces:
            if state == WLAN_INTERFACE_STATE_CONNECTED:
                return _backend.query_ssid(handle, guid)
        return None
    finally:
        _backend.close(handle)


def disconnect() -> bool:
    """断开当前连接的 WiFi；成功返回 True。"""
    handle = _backend.open()
    try:
        interfaces = _backend.enum_interfaces(handle)
        for guid, state in interfaces:
            if state == WLAN_INTERFACE_STATE_CONNECTED:
                return _backend.disconnect(handle, guid)
        return False
    finally:
        _backend.close(handle)
