# Keyboard Immulation

一个用于“不能直接粘贴文本”场景的跨平台键盘中转输入工具。

桌面端提供可视化面板：用户在工具里输入需要输出的内容，点击开始后在倒计时内切换到目标输入框，程序会通过系统键盘输入接口逐字符输出文本，不依赖系统剪贴板。

Android 端采用原生输入法思路：通过 Android `InputMethodService` 模拟软键盘输入，将待输出内容发送到当前获得焦点的输入框。

## 平台支持

| 平台 | 实现方式 | 状态 |
| --- | --- | --- |
| Windows | Python + Tkinter + Win32 `SendInput` | 已实现 |
| macOS | Python + Tkinter + `pynput` | 已提供桌面端兼容实现 |
| Linux | Python + Tkinter + `pynput` | 已提供桌面端兼容实现 |
| Android | 原生输入法 `InputMethodService` | 已提供最小原生输入法工程 |

## 功能特性

- 可视化交互面板，桌面端无需在终端中操作
- 不使用系统剪贴板，适合禁用粘贴或粘贴受限的场景
- 支持中文、英文、符号、换行和 Tab
- 支持开始延迟，方便手动切换到目标输入位置
- 支持字符输入间隔，适配响应较慢的网页、远程桌面或软件
- 支持 `Esc` 中断输出（桌面端）
- 提供“程序输入模式（智能缩进）”，适配 IDE、在线编译器和代码编辑器的自动缩进
- Android 版本按原生软键盘输入方向实现，不迁移桌面键盘模拟逻辑

## 适用场景

- 在线考试、在线编译器或网页表单不允许直接粘贴
- 远程桌面、虚拟机、受限终端中粘贴不稳定
- 某些软件只能接收键盘输入，不能接收剪贴板文本
- 需要把代码按原格式输入到带自动缩进的编辑器中
- 移动端需要通过软键盘把预设文本输入到当前输入框

## 快速开始

### Windows

推荐直接运行 release 或本地打包产物：

```text
dist\键盘中转输入工具.exe
```

也可以从源码启动：

```powershell
py -3 keyboard_relay.py
```

或双击：

```text
run.bat
```

### macOS

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

启动：

```bash
sh run.sh
```

macOS 首次使用可能需要在“系统设置 -> 隐私与安全性 -> 辅助功能”中允许终端或 Python 控制键盘输入。

### Linux

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

启动：

```bash
sh run.sh
```

Linux 需要图形桌面环境和 Tkinter。部分发行版需要额外安装 `python3-tk`。

### Android

Android 版本不使用 Tkinter。它应作为原生输入法安装到设备上：

1. 安装 Android APK。
2. 在系统输入法设置中启用 `Keyboard Immulation` 输入法。
3. 切换到该输入法。
4. 在输入法界面输入或选择待输出文本。
5. 由输入法调用当前输入框的 `InputConnection` 执行输入。

Android 原生输入法工程见 [android/](android/)。

## 桌面端使用方法

1. 打开工具。
2. 在大文本框中输入或粘贴需要中转输出的内容。
3. 根据目标软件情况设置参数：
   - `延迟(秒)`：点击开始后等待多久再输出，默认 `3`
   - `间隔(毫秒)`：每个输入动作之间的等待时间，默认 `5`
   - `换行`：换行的发送方式
   - `Tab`：Tab 的发送方式
   - `程序输入模式（智能缩进）`：用于输入代码
4. 点击“开始输出”。
5. 在倒计时结束前手动切换到目标窗口，并确保目标输入框已经获得焦点。
6. 程序开始模拟键盘输入。
7. 输出过程中可以按 `Esc` 或点击“停止”中断。

## 参数说明

| 参数 | 说明 | 建议 |
| --- | --- | --- |
| `延迟(秒)` | 点击开始后等待多少秒再输入 | 默认 `3`，留出切换窗口时间 |
| `间隔(毫秒)` | 每个字符或按键动作之间的间隔 | 如果目标软件丢字，调到 `20` 到 `50` |
| `换行 = enter` | 遇到换行时发送回车键 | 大多数输入框推荐 |
| `换行 = unicode` | 将换行作为 Unicode 字符发送 | 适合少数编辑器或终端 |
| `Tab = unicode` | 尽量输入制表符本身 | 默认推荐 |
| `Tab = key` | 遇到 Tab 时发送 Tab 键 | 某些表单会切换焦点，谨慎使用 |

## 程序输入模式（智能缩进）

许多 IDE、在线编译器和代码编辑器会在按回车后自动缩进。如果直接逐字符输入代码，编辑器自动缩进可能和原文本缩进叠加，导致格式错乱。

开启“程序输入模式（智能缩进）”后，工具在每次换行时会执行以下流程：

1. 发送 `Enter`
2. 清除当前新行中由目标编辑器自动插入的缩进
3. 输入原文本中下一行自己的缩进和内容

Windows 和 Linux 桌面端默认使用 `Shift + Home` 与 `Delete` 清除自动缩进。macOS 桌面端使用 `Shift + Command + Left` 与 `Delete`。

## 构建与打包

### Windows exe

```powershell
py -3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pyinstaller
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name "键盘中转输入工具" keyboard_relay_gui.pyw
```

输出：

```text
dist\键盘中转输入工具.exe
```

### macOS 应用程序

在 macOS 上使用 PyInstaller 原生构建 `.app`：

```bash
python3 -m pip install pyinstaller pynput
pyinstaller --noconfirm --clean --windowed --name keyboard_immulation_macos keyboard_relay.py
```

输出位于 `dist/keyboard_immulation_macos.app`。

### Linux 应用程序

在 Linux 上使用 PyInstaller 原生构建可执行文件：

```bash
python3 -m pip install pyinstaller pynput
pyinstaller --noconfirm --clean --onefile --windowed --name keyboard_immulation_linux keyboard_relay.py
```

输出位于 `dist/keyboard_immulation_linux`。

### Android APK

Android APK 需要在 Android SDK/Gradle 环境中构建。当前仓库的 [android/](android/) 目录已经包含最小原生输入法工程，可在 Android Studio 中打开并构建。

## Release 命名

不同系统的 release 资产建议按以下名称发布：

| 系统 | Release / 资产名称 |
| --- | --- |
| Windows | `keyboard_immulation_windows` |
| macOS | `keyboard_immulation_macos` |
| Linux | `keyboard_immulation_linux` |
| Android | `keyboard_immulation_android` |

release 资产可以是 `.zip`、`.tar.gz`、`.exe`、`.dmg`、`.AppImage` 或 `.apk`，按目标系统实际构建结果选择。

仓库已提供 GitHub Actions 工作流 [build-releases.yml](.github/workflows/build-releases.yml)，可以在对应系统 runner 上原生构建 Windows、macOS、Linux 和 Android 产物，并创建对应 release。

## 项目文件

| 文件 | 说明 |
| --- | --- |
| `keyboard_relay.py` | 桌面端主程序、GUI 和跨平台键盘输入后端 |
| `keyboard_relay_gui.pyw` | Windows 无控制台窗口启动入口 |
| `run.bat` | Windows 双击启动脚本 |
| `run.sh` | macOS/Linux 启动脚本 |
| `requirements.txt` | 桌面端 Python 依赖 |
| `android/` | Android 原生输入法工程 |
| `README.md` | 项目说明 |
| `dist\键盘中转输入工具.exe` | Windows 已打包窗口程序 |

## 注意事项

- 桌面端不会自动定位窗口，也不会自动激活窗口。点击开始后需要手动切换到目标输入位置。
- 模拟键盘输入会受目标软件影响。如果出现丢字，请增大输入间隔。
- 程序输入模式依赖系统快捷键清除当前行自动缩进。少数编辑器如果改写了相关快捷键，可能不适用。
- 如果目标程序以管理员权限运行，Windows 桌面端也可能需要以管理员权限运行。
- macOS/Linux 的全局键盘模拟依赖系统权限、桌面环境和输入法状态。
- Android 版本必须走原生输入法路线，不能直接复用桌面 Tkinter 程序。

## 运行环境

| 平台 | 环境 |
| --- | --- |
| Windows | Windows 10/11，Python 3.9+，Tkinter |
| macOS | macOS，Python 3.9+，Tkinter，pynput，辅助功能权限 |
| Linux | 图形桌面环境，Python 3.9+，Tkinter，pynput |
| Android | Android SDK/Gradle 原生工程，InputMethodService |
