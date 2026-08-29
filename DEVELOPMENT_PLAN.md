# VPNDefender 分步开发路径（Development Plan）

> 版本：v1.0
> 关联文档：PRD.md、TDD.md
> 原则：小步快跑；每完成一步必须先跑该步测试，**测试全绿才进入下一步**。

## 通用约定

- 语言：Python 3.10+（推荐 3.11/3.12）。
- 依赖：仅标准库（`tkinter`、`json`、`ctypes`、`subprocess`、`os`、`pathlib`、`unittest`）。
- 测试：`unittest`（默认）或 `pytest`；WLAN/GUI 测试优先 mock，保证可离线、无界面环境运行。
- 目录：按 TDD.md §4 规划，可随开发微调。

---

## 第 0 步：项目骨架与环境

建立目录结构、各包 `__init__.py`、`app.py` 入口（最小可运行占位）。确认解释器、无第三方依赖。

**测试（smoke）**

- `import app`、`import core.config`、`import wlan.wrapper`、`import ui.main_window` 均无报错。
- `config.json` 默认黑名单含 `UIBE-WLAN`。

**通过标准**：所有 import 成功；默认配置可加载。

---

## 第 1 步：配置模型 + JSON 读写

实现 `core/config.py`：

- `VpnEntry`、`AppConfig`（含默认黑名单 `["UIBE-WLAN"]`）。
- `load()/save()`、原子写、缺失/损坏回退默认。
- 缺失 → 默认配置，`was_reset=False`；损坏 → 默认配置，`was_reset=True` 供 UI 提示“配置已重置，已恢复默认值”。

**测试（tests/test_config.py）**

- 保存→加载回读一致（含中文、反斜杠路径）。
- 文件缺失：返回默认配置，`was_reset=False`。
- 文件损坏：不抛异常、返回默认配置、`was_reset=True`。
- 原子写：保存后文件有效，损坏情况下原文件不被改写。

**通过标准**：以上 4 类用例全绿。

---

## 第 2 步：读取当前 WiFi SSID

实现 `wlan/wrapper.py` 的 `get_current_ssid() -> str|None`（`WlanQueryInterface`）。

**测试（tests/test_wlan.py，mock 底层）**

- 已连接：正确解析 `DOT11_SSID` 并返回字符串。
- 未连接：返回 `None`。
- 无无线接口：返回 `None`。
- 句柄在 `finally` 中释放（断言 `WlanCloseHandle` 被调用）。
- （可选真实）有 WiFi 机器返回实际 SSID 或 `None`。

**通过标准**：mock 用例全绿。

---

## 第 3 步：断开指定 WiFi

实现 `wlan/wrapper.py` 的 `disconnect() -> bool`（`WlanDisconnect`）。

**测试（tests/test_wlan.py，mock）**

- 成功断开：返回 `True`，且用正确接口句柄。
- 无连接/系统错误：返回 `False`（不抛异常）。
- 无接口：返回 `False`。
- 句柄释放：断言 `WlanCloseHandle` 被调用。

**通过标准**：mock 用例全绿。

---

## 第 4 步：启动流程编排

实现 `core/starter.py` 的 `start(vpn_entry, config, wlan)`。

**测试（tests/test_starter.py，mock wlan + subprocess）**

- SSID 命中黑名单：调用 `disconnect()`，不调用 `subprocess`，返回 `('blocked', ssid)`。
- SSID 未命中：调用 `Popen([exe_path])`，返回 `('launched', ssid)`。
- 无 SSID：直接启动，返回 `('launched', None)`。
- 精确匹配：黑名单 `UIBE-WLAN` 时 `uibe-wlan` 不命中。
- `disconnect()` 失败：仍返回 `blocked`（拦截优先）。
- `shell=False`，路径含空格可正确传参。

**通过标准**：以上用例全绿。

---

## 第 5 步：GUI 主窗口 + 列表管理

实现 `ui/main_window.py`：VPN 列表增/改/删/选中、黑名单增/删、关闭保存。

**测试（mock messagebox）**

- 添加非法（名称/路径为空）：提示且不写入。
- 添加合法：配置与列表同步并保存。
- 修改/删除：配置正确更新。
- 名称重复：提示“建议显示名称唯一”，但允许保存。
- 黑名单添加空名：拒绝；添加/删除后配置一致。
- 真实 `Tk` smoke（headless 跳过）。

**通过标准**：配置/控制器相关用例全绿；GUI smoke 在可显示环境通过。

---

## 第 6 步：“启动”按钮集成

将“启动”接到 `starter.start`，状态栏反馈。

**测试（注入 fake wlan + fake subprocess）**

- 命中黑名单：弹窗文本完全等于“不要通过校园网使用vpn，已为您断开校园网。”，状态栏显示已拦截。
- 未命中：正常启动并显示“已启动”。
- 未选中条目：提示“请先选择一个 VPN 软件”。
- 断网失败分支：仍显示拦截但不崩溃。

**通过标准**：注入用例全绿。

---

## 第 7 步：管理员提权 + 整体验收

启动即提权，非管理员时 `ShellExecuteW(..., "runas", ...)` 重启自身并退出。

**测试**

- 模拟非管理员：触发重启路径；模拟管理员：直接进入主界面。
- 集成验收清单（人工）：在 `UIBE-WLAN` 下点启动→断开+弹窗+不启动；其它/无网络→正常启动。

**通过标准**：提权逻辑 mock 测试全绿 + 人工验收通过。

---

## 验收出口

- 满足 PRD 全部需求。
- 全部分步测试通过。
- 无未处理异常；配置兜底、无网卡、断网失败等边界已覆盖。
