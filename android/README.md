# Android 原生输入法

本目录是 Keyboard Simulation 的 Android 端实现。

它不是桌面 Tkinter 的移植，而是通过 `InputMethodService` 作为系统输入法，把待输出内容提交到当前获得焦点的输入框。

## 功能

- 场景预设：默认 / 表单考试 / 代码 IDE / 长文稳定
- 延迟、间隔、程序模式、慢启动、拟人抖动
- 开始 / 暂停继续 / 停止 / 断点续打
- 剪贴板载入、清洗文本、进度显示
- 程序模式下清除自动缩进后按原文输出

## 使用

1. 构建并安装 APK
2. 系统设置中启用输入法 `Keyboard Simulation`
3. 切换到该输入法
4. 在目标 App 输入框中唤起键盘
5. 在面板中输入内容并开始输出

## 构建

使用 Android Studio 打开本目录上级的 `android/` 工程，或使用本机 Gradle/SDK 构建。

建议产物命名：

```text
keyboard_simulation_android.apk
```