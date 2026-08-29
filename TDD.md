# VPNDefender 技术架构设计文档（TDD）

> 版本：v1.0  
> 状态：设计完成，待开发  
> 编写日期：2026-08-29  
> 关联文档：PRD.md

## 1. 概述

技术架构设计文档描述 VPNDefender 的模块划分、数据结构、关键接口、WLAN 控制实现方式、GUI 布局以及测试策略，为后续按 PRD 第 7 节的分步开发提供落地依据。

## 2. 运行环境

- 操作系统：Windows 10 / 11（64 位）。
- Python 版本：3.10+（推荐 3.11 或 3.12）。
- 权限：启动时以管理员（elevated）权限运行。
- 依赖：优先使用 Python 标准库（`tkinter`、`json`、`ctypes`、`subprocess`、`os`、`pathlib`）。
- 交付形态：不打包 `.exe`，以 `python app.py` 脚本方式运行。

## 3. 总体架构

采用 **单进程 / 分层** 架构，界面与业务逻辑分离，便于测试与替换实现：

```
┌───────────────────────────────┐
│        GUI 层 (tkinter)        │   view
│   主窗口、列表管理、启动按钮    │
├───────────────────────────────┤
│       控制器 / 业务层          │   controller
│   启动流程编排、校验、弹窗      │
├───────────────┬───────────────┤
│   配置服务     │   WLAN 服务    │   service
│  JSON 读写     │ 读取 SSID/断开 │
└───────────────┴───────────────┘
```

- **view**：只负责界面展示与用户输入收集，不直接操作 WLAN 或文件。
- **controller**：串联界面与 service，执行“启动”流程、黑名单判断、输出提醒。
- **config_service**：负责 VPN 条目与黑名单的 JSON 持久化。
- **wlan_service**：封装 Windows WLAN API，提供读取当前 SSID 与断开连接的能力。

## 4. 目录结构

```
VPNDefender/
├── PRD.md              # 需求文档
├── TDD.md              # 技术架构设计文档（本文件）
├── app.py              # 程序入口（提权 + 启动 GUI）
├── ui/
│   ├── __init__.py
│   └── main_window.py  # 主窗口（列表、黑名单、启动按钮）
├── core/
│   ├── __init__.py
│   ├── config.py       # 配置模型与 JSON 存取
│   └── starter.py      # 启动流程编排
├── wlan/
│   ├── __init__.py
│   ├── wrapper.py      # ctypes 封装 Windows WLAN API
│   └── models.py       # WLAN 相关数据结构
├── config.json         # 运行期生成的配置（首次运行创建）
├── tests/
│   ├── test_config.py
│   ├── test_starter.py
│   └── util_mock.py
└── requirements.txt    # （可选）目前无第三方必需依赖
```

> 说明：目录结构为规划目标；随开发推进允许调整，但需保持 view / controller / service 分层。

## 5. 数据模型（config.py）

```python
@dataclass
class VpnEntry:
    name: str          # 显示名称，如 "RabbitPro"
    exe_path: str      # 完整 exe 路径，如 "D:\\rabbitpro\\RabbitPro.exe"

@dataclass
class AppConfig:
    vpn_entries: list[VpnEntry] = field(default_factory=list)
    blacklist: list[str] = field(default_factory=lambda: ["UIBE-WLAN"])
```

配置文件 `config.json` 结构：

```json
{
  "vpn_entries": [
    { "name": "RabbitPro", "exe_path": "D:\\rabbitpro\\RabbitPro.exe" }
  ],
  "blacklist": ["UIBE-WLAN"]
}
```

### 5.1 配置存取规则

- `load()`：读取 `config.json`；文件不存在或损坏时，返回默认配置（`blacklist` 含 `UIBE-WLAN`），并向外提供“配置已重置”信号（如返回 `(config, was_reset)`），不抛异常；controller/GUI 据此提示“配置已重置，已恢复默认值”。
- `save()`：原子写（先写临时文件再替换），避免崩溃导致配置损坏。
- 校验：`exe_path` 非空；`name` 非空；多个条目允许重名，不做强制去重，仅提示“建议显示名称唯一”。

## 6. WLAN 服务（wlan/）

### 6.1 封装目标

对 GUI 层只暴露两个高级接口：

```python
def get_current_ssid() -> str | None:
    """返回当前连接 WiFi 的 SSID；未连接返回 None。"""

def disconnect() -> bool:
    """断开当前无线连接；成功返回 True。"""
```

### 6.2 底层实现（Windows WLAN API，ctypes）

使用 `wlanapi.dll`：

1. `WlanOpenHandle` → 打开会话。
2. `WlanEnumInterfaces` → 枚举无线接口，取第一个可用接口 GUID。
3. `WlanQueryInterface`，`wlan_intf_opcode_current_connection` → 读取连接状态与 BSSID/SSID。
4. `WlanDisconnect` → 断开指定接口的连接。
5. `WlanCloseHandle` → 释放会话。

关键数据结构（ctypes 定义）：

- `WLAN_INTERFACE_INFO`（接口 GUID、状态、描述）。
- `WLAN_CONNECTION_ATTRIBUTES` / `DOT11_SSID`（读取 SSID）。
- `WLAN_NOTIFICATION_DATA`（断开时可监听通知，非必需）。

### 6.3 错误与边界

- 若无无线接口或接口未连接 → `get_current_ssid()` 返回 `None`。
- 断开失败（无连接 / 权限 / 系统错误）→ `disconnect()` 返回 `False`，由 controller 记录并提示。
- 所有原生句柄需在 `finally` 中关闭，避免句柄泄漏。

## 7. 启动流程编排（starter.py）

`start(vpn_entry, config, wlan)` 方法逻辑：

1. `ssid = wlan.get_current_ssid()`。
2. 若 `ssid` 为 `None`：直接启动 `vpn_entry.exe_path`（未连网按正常启动）。
3. 若 `ssid` 在 `config.blacklist`：
   - SSID 与黑名单采用**精确匹配**，区分大小写。
   - `wlan.disconnect()`；
   - 弹窗提示 **“不要通过校园网使用vpn，已为您断开校园网。”**；
   - **不启动** exe；
   - 返回结果如 `("blocked", ssid)`。
4. 若 `ssid` 不在黑名单：启动 exe，返回 `("launched", ssid)`。

启动 exe 使用 `subprocess.Popen([exe_path], shell=False)`，不阻塞主线程。

## 8. GUI 设计（ui/main_window.py）

基于 `tkinter.ttk`：

- **VPN 软件列表**：`ttk.Treeview` 显示“显示名称 / exe 完整路径”，支持选中。
- **按钮区**：添加、编辑、删除（对 VPN 条目）。
- **网络黑名单列表**：`ttk.Listbox` 或 `ttk.Treeview`，显示黑名单网络名。
- **按钮区**：添加、删除（对黑名单）。
- **“启动”按钮**：读取选中条目，调用 `starter.start`。
- **状态栏**：展示最近一次操作结果（如启动成功 / 已拦截）。
- 关闭窗口时自动保存配置。

### 8.1 交互流程

- 添加/编辑 VPN 条目：弹出一个对话框，输入名称与路径，校验非空后写回配置。
- 添加/编辑时若出现重名，提示“建议显示名称唯一”，但不阻止保存。
- 添加黑名单：请输入非空网络名称，默认不允许为空。
- “启动”按钮：无选中条目时提示“请先选择一个 VPN 软件”。

## 9. 权限（提权）

- 方案：应用启动即以管理员身份运行。若未提权，通过：
  - 使用 Python 中 `ctypes` 调用 `ShellExecuteW(..., "runas", ...)` 重启自身并退出当前进程（本项目不打包 `.exe`，不采用 UAC 清单方案）。
- 提权后关键路径（读取 SSID、断开 WiFi）才可用；权限不足时在界面给出明确提示。

## 10. 测试策略

采用 **单元测试 + 集成测试**，使用 `pytest`（或标准库 `unittest`）。

### 10.1 单元测试

- `test_config.py`：
  - 保存→加载回读一致（roundtrip）。
  - 文件缺失时返回默认配置。
  - 文件内容损坏（非法 JSON）时不崩溃、回退默认配置，并返回“已重置”信号。
- `test_starter.py`：
  - 命中黑名单 → 不调用 `subprocess`，返回 `blocked`。
  - 未命中黑名单 → 调用 `subprocess`，返回 `launched`。
  - 无 SSID → 直接启动，返回 `launched`。
  - 使用 mock 代替真实的 WLAN 与 subprocess，保证测试可离线运行。
- `test_wlan.py`（可选，受环境影响）：
  - 真实环境：读取当前 SSID；未连接时返回 `None`。

### 10.2 集成测试

- 启动真实 GUI 主窗口，验证添加/删除条目后配置正确写入。
- 模拟“启动”流程，验证拦截弹窗与正常启动分支。

### 10.3 测试用例与 PRD 对齐

每个开发步骤在 PRD 第 7 节对应一个测试验收目标，本节测试补充实现细节。

## 11. 关键风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| `netsh wlan disconnect` 在 Win10/11 失效 | 无法断开 | 使用 WLAN API `WlanDisconnect`，不依赖 netsh |
| 读取 SSID/断开需要管理员权限 | 功能不可用 | 启动即提权，失败给出明确提示 |
| 无无线网卡或未连接 | 无 SSID | 按“未连网→正常启动”处理，返回 None |
| 配置损坏 | 程序崩溃 | load 兜底默认配置 + 原子写 |
| 杀软拦截提权/断开 | 功能异常 | 使用标准 WLAN API，避免非标行为 |

## 12. 已确认决策补充

- 不需要打包为独立 `.exe`，以脚本方式运行。
- VPN 条目允许多个，不强制去重，仅提示“建议显示名称唯一”。
- 配置损坏/缺失时回退默认配置（黑名单仍含 `UIBE-WLAN`），并提示“配置已重置”。
- 黑名单匹配采用精确匹配，SSID 区分大小写。
