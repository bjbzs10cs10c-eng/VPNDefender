# VPNDefender

防止在校园网（如 `UIBE-WLAN`）下误开 VPN 的拦截/提醒工具。启动前先读当前连接的 WiFi SSID，命中黑名单就断开并提醒、不启动 VPN；否则正常启动所选 VPN。

## 运行前提

- Windows 10 / 11。
- Python 3.10+，且**必须安装了完整的 Tk（含 `tk8.6/init.tcl`）**。标准 Python 官网安装包自带；精简版/嵌入式 Python 可能缺失 Tk。
- 本机已安装 **Python 3.13.14 到 `D:\python`**（含 Tk、pip），并已加入系统 PATH。
- 需要以**管理员权限**运行，才能读取/断开 Wi‑Fi（程序启动会自动请求 UAC 提权）。

## 启动

**方式一（推荐）**：直接双击打包好的可执行文件 `dist\VPNDefender.exe`。
该 exe 已嵌入“需要管理员”UAC 清单，双击后 Windows 会弹出一次 UAC 提权确认，点“是”即直接已管理员身份运行图形界面；无需依赖 Python。

**方式二（源码）**：双击项目目录内的 `start.bat`（自动定位 `D:\python\python.exe` 并启动）。也可以手动执行：

```
python app.py
```

程序会自动请求管理员权限并打开图形界面。

> 说明：`config.json`（VPN 列表、网络黑名单）会生成在 exe 同级目录；打包后它就在 `dist\config.json`，请把 exe 放在可写目录（如 D 盘或桌面），不要放进 `Program Files`。

## 使用

- **VPN 软件**：点“添加”填入显示名称与 exe 完整路径（如 `D:\rabbitpro\RabbitPro.exe`）；可编辑/删除；从列表选中后点“启动”。
- **网络黑名单**：默认含 `UIBE-WLAN`，可继续添加/删除其它校园网名称。所有 VPN 条目共用这一份黑名单。
- 点击“启动”时：若当前连接的网络命中黑名单 → 自动断开该 Wi‑Fi、弹出“不要通过校园网使用vpn，已为您断开校园网。”并**不启动**；若不在黑名单或未连接 Wi‑Fi → 正常启动。

## 配置

配置保存在项目根目录 `config.json`（首次运行自动按默认值生成）：

```json
{
  "vpn_entries": [],
  "blacklist": ["UIBE-WLAN"]
}
```

格式异常或缺失时程序回退到默认配置并提示“配置已重置，已恢复默认值”。

## 测试

```
python -m unittest discover -s tests -v
```

> 说明：使用带 Tk 的 Python（如 `D:\python`）运行时，全部用例（含 4 个 GUI 场景）都会实际执行。
