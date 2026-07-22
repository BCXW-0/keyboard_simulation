# Keyboard Simulation

跨平台键盘中转输入工具：把准备好的文本，通过系统键盘接口逐字符输出到当前焦点位置。  
适用于无法粘贴、粘贴受限、或只能接收键盘输入的场景。

- 桌面端：可视化面板 + 键盘模拟（Windows / macOS / Linux）
- Android 端：原生输入法（`InputMethodService`）
- 本地运行，不上传内容，免费开源

仓库：https://github.com/BCXW-0/keyboard_simulation

## 功能

- 延迟启动、字符间隔、进度与 ETA
- `Esc` 停止，`F8` 暂停/继续，支持断点续打
- 场景预设：默认 / 表单考试 / 代码 IDE / 长文稳定
- 程序输入模式：适配 IDE 自动缩进
- 慢启动、拟人抖动、失败重试
- 导入文件、清洗文本、本地历史（可关）

## 快速开始

### Windows

```powershell
py -3 keyboard_relay.py
```

或双击 `run.bat`。

### macOS / Linux

```bash
python3 -m pip install -r requirements.txt
sh run.sh
```

macOS 需在「系统设置 -> 隐私与安全性 -> 辅助功能」中授权。  
Linux 需要图形桌面和 Tkinter（部分发行版安装 `python3-tk`）。

### Android

1. 安装 `keyboard_simulation_android.apk`
2. 启用并切换到输入法 `Keyboard Simulation`
3. 在面板中输入内容并开始输出

源码见 [android/](android/)。

## 使用说明

1. 打开工具，输入/导入待输出内容
2. 选择场景或调整参数
3. 点击「开始输出」
4. 倒计时内切换到目标输入框
5. 过程中可用 `Esc` / `F8` 控制；中断后可「断点续打」

### 常用参数

| 参数 | 说明 |
| --- | --- |
| 延迟(秒) | 开始后等待多久再输出，默认 3 |
| 间隔(毫秒) | 每个动作间隔；丢字时可调到 20~50 |
| 程序输入模式 | 输入代码时开启，处理自动缩进 |
| 慢启动 / 拟人抖动 | 提升稳定性与输入节奏 |
| 换行 / Tab | `enter`+`unicode` 适合大多数场景 |

程序模式流程：发送回车 -> 清除编辑器自动缩进 -> 输出原文下一行。

## 构建发布

| 平台 | 产物 |
| --- | --- |
| Windows | `keyboard_simulation_windows.exe` |
| macOS | `keyboard_simulation_macos.dmg` |
| Linux | `keyboard_simulation_linux` |
| Android | `keyboard_simulation_android.apk` |

Windows：

```powershell
py -3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pyinstaller
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name keyboard_simulation_windows keyboard_relay_gui.pyw
```

macOS / Linux 在对应系统用 PyInstaller 构建；Android 用 Android Studio / Gradle 构建 [android/](android/)。

## 项目结构

| 路径 | 说明 |
| --- | --- |
| `keyboard_relay.py` | 桌面端主程序 |
| `keyboard_relay_gui.pyw` | Windows 无控制台入口 |
| `run.bat` / `run.sh` | 启动脚本 |
| `android/` | Android 输入法工程 |
| `scripts/package_releases.ps1` | 本地 release 整理 |

配置与历史：`~/.keyboard_simulation/`

## 注意

- 不会自动激活窗口，开始后请手动切换目标输入位置
- 丢字时增大间隔并开启慢启动
- 目标程序若以管理员权限运行，本工具也可能需要同等权限
- 请在合法合规场景使用

当前版本：`1.1.0`
