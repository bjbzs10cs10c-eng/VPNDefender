"""主窗口：VPN 列表、黑名单、启动按钮。"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from core import config, config_ops, starter
from wlan import wrapper

NO_SELECTION_TEXT = "请先选择一个 VPN 软件。"


def run_launcher(entry, cfg, wlan, launcher):
    """调用启动流程。返回 (result, info)。

    - 正常：返回 starter.start 的结果，如 ("blocked", ssid) / ("launched", ssid)。
    - 异常：返回 ("error", 错误信息)。
    """
    try:
        return launcher(entry, cfg, wlan)
    except Exception as exc:  # noqa: BLE001
        return ("error", str(exc))


def status_text_for(result, entry_name=None, ssid=None) -> str:
    """根据结果生成状态栏文案。"""
    if result == "blocked":
        return f"已在校园网 {ssid} 下拦截，未启动。"
    if result == "error":
        return f"启动失败：{ssid}"
    return f"已启动：{entry_name}"


class MainWindow(tk.Tk):
    """主窗口。可通过注入 wlan/launcher 便于测试。"""

    def __init__(self, config_data=None, config_path=None, wlan=None, launcher=None):
        super().__init__()
        self.title("VPNDefender")
        self.config_path = config_path or config.CONFIG_PATH
        if config_data is None:
            config_data, _ = config.load(self.config_path)
        self.config = config_data
        self.wlan = wlan if wlan is not None else wrapper
        self.launcher = launcher if launcher is not None else starter.start
        self._build_ui()
        self._refresh_vpn()
        self._refresh_blacklist()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        self.status_var = tk.StringVar(value="就绪")
        body = ttk.Frame(self, padding=8)
        body.pack(fill=tk.BOTH, expand=True)

        # VPN 列表
        vpn_frame = ttk.LabelFrame(body, text="VPN 软件（选中后点击“启动”）", padding=6)
        vpn_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cols = ("name", "path")
        self.vpn_tree = ttk.Treeview(vpn_frame, columns=cols, show="headings")
        self.vpn_tree.heading("name", text="显示名称")
        self.vpn_tree.heading("path", text="exe 完整路径")
        self.vpn_tree.column("name", width=140)
        self.vpn_tree.column("path", width=280)
        self.vpn_tree.pack(fill=tk.BOTH, expand=True)

        vpn_btns = ttk.Frame(vpn_frame)
        vpn_btns.pack(fill=tk.X, pady=6)
        ttk.Button(vpn_btns, text="启动", command=self._on_start).pack(side=tk.LEFT, padx=2)
        ttk.Button(vpn_btns, text="添加", command=self._add_vpn).pack(side=tk.LEFT, padx=2)
        ttk.Button(vpn_btns, text="编辑", command=self._edit_vpn).pack(side=tk.LEFT, padx=2)
        ttk.Button(vpn_btns, text="删除", command=self._delete_vpn).pack(side=tk.LEFT, padx=2)

        # 黑名单
        bl_frame = ttk.LabelFrame(body, text="网络黑名单（校园网，不可启动 VPN）", padding=6)
        bl_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.blacklist_list = tk.Listbox(bl_frame, width=24, height=12)
        self.blacklist_list.pack(fill=tk.BOTH, expand=True)
        bl_btns = ttk.Frame(bl_frame)
        bl_btns.pack(fill=tk.X, pady=6)
        ttk.Button(bl_btns, text="添加", command=self._add_blacklist).pack(side=tk.LEFT, padx=2)
        ttk.Button(bl_btns, text="删除", command=self._delete_blacklist).pack(side=tk.LEFT, padx=2)

        status = ttk.Label(body, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status.pack(side=tk.BOTTOM, fill=tk.X, pady=4)

    def _selected_vpn_index(self):
        sel = self.vpn_tree.selection()
        if not sel:
            return None
        return self.vpn_tree.index(sel[0])

    def _refresh_vpn(self):
        self.vpn_tree.delete(*self.vpn_tree.get_children())
        for entry in self.config.vpn_entries:
            self.vpn_tree.insert("", "end", values=(entry.name, entry.exe_path))

    def _refresh_blacklist(self):
        self.blacklist_list.delete(0, tk.END)
        for name in self.config.blacklist:
            self.blacklist_list.insert(tk.END, name)

    def _set_status(self, text):
        self.status_var.set(text)

    def _save(self):
        config.save(self.config, self.config_path)

    def _on_close(self):
        self._save()
        self.destroy()

    def _add_vpn(self):
        name = simpledialog.askstring("添加 VPN", "显示名称：")
        if name is None:
            return
        path = simpledialog.askstring("添加 VPN", "exe 完整路径：")
        if path is None:
            return
        ok, msg = config_ops.add_vpn(self.config, name, path)
        if not ok:
            messagebox.showwarning("无法添加", msg)
        elif msg:
            messagebox.showwarning("提示", msg)
        self._save_and_refresh()

    def _edit_vpn(self):
        index = self._selected_vpn_index()
        if index is None:
            messagebox.showwarning("提示", "请先选择一个 VPN 软件。")
            return
        entry = self.config.vpn_entries[index]
        name = simpledialog.askstring("编辑 VPN", "显示名称：", initialvalue=entry.name)
        if name is None:
            return
        path = simpledialog.askstring("编辑 VPN", "exe 完整路径：", initialvalue=entry.exe_path)
        if path is None:
            return
        ok, msg = config_ops.update_vpn(self.config, index, name, path)
        if not ok:
            messagebox.showwarning("无法修改", msg)
        elif msg:
            messagebox.showwarning("提示", msg)
        self._save_and_refresh()

    def _delete_vpn(self):
        index = self._selected_vpn_index()
        if index is None:
            messagebox.showwarning("提示", "请先选择一个 VPN 软件。")
            return
        ok, msg = config_ops.delete_vpn(self.config, index)
        if not ok:
            messagebox.showwarning("无法删除", msg)
        self._save_and_refresh()

    def _add_blacklist(self):
        name = simpledialog.askstring("添加黑名单", "网络名称：")
        if name is None:
            return
        ok, msg = config_ops.add_blacklist(self.config, name)
        if not ok:
            messagebox.showwarning("无法添加", msg)
        self._save_and_refresh()

    def _delete_blacklist(self):
        selection = self.blacklist_list.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个网络名称。")
            return
        name = self.blacklist_list.get(selection[0])
        ok, msg = config_ops.delete_blacklist(self.config, name)
        if not ok:
            messagebox.showwarning("无法删除", msg)
        self._save_and_refresh()

    def _save_and_refresh(self):
        self._save()
        self._refresh_vpn()
        self._refresh_blacklist()

    def _on_start(self):
        index = self._selected_vpn_index()
        if index is None:
            self._set_status(NO_SELECTION_TEXT)
            return
        entry = self.config.vpn_entries[index]
        result, info = run_launcher(entry, self.config, self.wlan, self.launcher)
        if result == "error":
            self._set_status(status_text_for(result, ssid=info))
            return
        if result == "blocked":
            messagebox.showwarning("已拦截", starter.BLOCKED_TEXT)
        self._set_status(status_text_for(result, entry.name, info))
