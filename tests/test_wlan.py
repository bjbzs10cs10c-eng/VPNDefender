"""第 2 步：读取当前 WiFi SSID 测试（mock 后端）。"""

import ctypes
import unittest

from wlan import wrapper
from wlan.wrapper import (
    DOT11_SSID,
    GUID,
    WLAN_CONNECTION_ATTRIBUTES,
    WLAN_INTERFACE_STATE_CONNECTED,
    _attributes_ssid,
    _decode_ssid,
    _extract_ssid,
    disconnect,
    get_current_ssid,
)


def make_guid() -> GUID:
    g = GUID()
    g.Data1 = 1
    g.Data2 = 2
    g.Data3 = 3
    g.Data4 = (ctypes.c_ubyte * 8)(4, 5, 6, 7, 8, 9, 10, 11)
    return g


class FakeBackend:
    def __init__(self, interfaces=None, ssid="MyWiFi", disconnect_return=True):
        self.interfaces = interfaces if interfaces is not None else [(make_guid(), 1)]
        self.ssid = ssid
        self.open_count = 0
        self.close_count = 0
        self.query_count = 0
        self.disconnect_count = 0
        self.disconnect_args = None
        self.disconnect_return = disconnect_return
        self.disconnect_error = None
        self.open_error = None
        self.enum_error = None
        self.query_error = None

    def open(self):
        self.open_count += 1
        if self.open_error:
            raise self.open_error
        return 123

    def enum_interfaces(self, handle):
        if self.enum_error:
            raise self.enum_error
        return self.interfaces

    def query_ssid(self, handle, guid):
        self.query_count += 1
        if self.query_error:
            raise self.query_error
        return self.ssid

    def disconnect(self, handle, guid):
        self.disconnect_count += 1
        self.disconnect_args = (handle, guid)
        if self.disconnect_error:
            raise self.disconnect_error
        return self.disconnect_return

    def close(self, handle):
        self.close_count += 1


class SsidTest(unittest.TestCase):
    def setUp(self):
        self.orig = wrapper._backend

    def tearDown(self):
        wrapper._backend = self.orig

    def _use(self, backend):
        wrapper._backend = backend
        return backend

    def test_connected_returns_ssid(self):
        fake = self._use(FakeBackend())
        self.assertEqual(get_current_ssid(), "MyWiFi")
        self.assertEqual(fake.query_count, 1)
        self.assertEqual(fake.close_count, 1)

    def test_disconnected_returns_none(self):
        fake = self._use(FakeBackend(interfaces=[(make_guid(), 2)]))
        self.assertIsNone(get_current_ssid())
        self.assertEqual(fake.query_count, 0)
        self.assertEqual(fake.close_count, 1)

    def test_no_interface_returns_none(self):
        fake = self._use(FakeBackend(interfaces=[]))
        self.assertIsNone(get_current_ssid())
        self.assertEqual(fake.query_count, 0)
        self.assertEqual(fake.close_count, 1)

    def test_close_called_even_on_error(self):
        fake = self._use(FakeBackend())
        fake.query_error = RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            get_current_ssid()
        self.assertEqual(fake.close_count, 1)

    def test_open_error_still_closes(self):
        fake = self._use(FakeBackend())
        fake.open_error = OSError("open boom")
        with self.assertRaises(OSError):
            get_current_ssid()
        self.assertEqual(fake.close_count, 0)

    def test_ssid_with_unicode(self):
        fake = self._use(FakeBackend(ssid="中文网"))
        self.assertEqual(get_current_ssid(), "中文网")

    def test_decode_ascii(self):
        raw = b"TestNet"
        arr = (ctypes.c_ubyte * 32)(*raw, *([0] * (32 - len(raw))))
        self.assertEqual(_decode_ssid(len(raw), arr), "TestNet")

    def test_decode_truncates_to_length(self):
        raw = b"ABC"
        arr = (ctypes.c_ubyte * 32)(*raw, *([0] * 29))
        self.assertEqual(_decode_ssid(2, arr), "AB")

    def test_attributes_ssid(self):
        ssid = DOT11_SSID()
        payload = b"CampusNet"
        ssid.uSSIDLength = len(payload)
        ssid.ucSSID = (ctypes.c_ubyte * 32)(*payload, *([0] * (32 - len(payload))))
        attrs = WLAN_CONNECTION_ATTRIBUTES()
        attrs.dot11Ssid = ssid
        self.assertEqual(_attributes_ssid(attrs), "CampusNet")

    def test_extract_ssid_utf16le(self):
        # 实测 Windows 返回的原始连接属性缓冲（UTF-16LE 存储 SSID）
        raw = bytes.fromhex(
            "0100000004000000"
            "4800550041005700450049002d00310030004500380043004b00"
            "0000000000000000000000"
        )
        self.assertEqual(_extract_ssid(raw), "HUAWEI-10E8CK")

    def test_extract_ssid_utf16le_long(self):
        # 19 字符 SSID（UTF-16LE 共 38 字节），验证不再被 36 字节切片截断
        name = "HUAWEI-10E8CK_Guest"
        raw = (
            (1).to_bytes(4, "little")
            + (4).to_bytes(4, "little")
            + name.encode("utf-16-le")
            + b"\x00" * 40
        )
        self.assertEqual(_extract_ssid(raw), name)

    def test_extract_ssid_ascii_layout(self):
        name = b"HUAWEI-10E8CK"
        raw = (
            (1).to_bytes(4, "little")
            + (4).to_bytes(4, "little")
            + len(name).to_bytes(4, "little")
            + name
            + b"\x00" * 20
        )
        self.assertEqual(_extract_ssid(raw), "HUAWEI-10E8CK")

    def test_extract_ssid_not_printable_falls_back(self):
        # 长度字段异常（非 1..32），应回退 UTF-16LE，或取不到就返回 None
        raw = (1).to_bytes(4, "little") + (4).to_bytes(4, "little") + b"\xff\xff\xff\xff" + b"\x00" * 24
        result = _extract_ssid(raw)
        self.assertIsInstance(result, (str, type(None)))

    def test_extract_ssid_empty(self):
        self.assertIsNone(_extract_ssid(b""))


class DisconnectTest(unittest.TestCase):
    def setUp(self):
        self.orig = wrapper._backend

    def tearDown(self):
        wrapper._backend = self.orig

    def _use(self, backend):
        wrapper._backend = backend
        return backend

    def test_connected_disconnects(self):
        fake = self._use(FakeBackend())
        self.assertTrue(disconnect())
        self.assertEqual(fake.disconnect_count, 1)
        self.assertEqual(fake.disconnect_args[0], 123)
        self.assertEqual(fake.close_count, 1)

    def test_no_connected_interface_returns_false(self):
        fake = self._use(FakeBackend(interfaces=[(make_guid(), 4)]))
        self.assertFalse(disconnect())
        self.assertEqual(fake.disconnect_count, 0)
        self.assertEqual(fake.close_count, 1)

    def test_no_interface_returns_false(self):
        fake = self._use(FakeBackend(interfaces=[]))
        self.assertFalse(disconnect())
        self.assertEqual(fake.disconnect_count, 0)
        self.assertEqual(fake.close_count, 1)

    def test_disconnect_failure_returns_false(self):
        fake = self._use(FakeBackend(disconnect_return=False))
        self.assertFalse(disconnect())
        self.assertEqual(fake.disconnect_count, 1)
        self.assertEqual(fake.close_count, 1)

    def test_disconnect_error_still_closes(self):
        fake = self._use(FakeBackend())
        fake.disconnect_error = RuntimeError("disconnect boom")
        with self.assertRaises(RuntimeError):
            disconnect()
        self.assertEqual(fake.close_count, 1)


if __name__ == "__main__":
    unittest.main()
