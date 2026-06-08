# Keyboard Immulation Android

Android 版本采用原生软键盘实现，不复用桌面端 Tkinter 或桌面键盘模拟。

当前目录包含一个最小 Android 输入法工程，核心服务是：

```text
app/src/main/java/com/keyboardimmulation/ime/KeyboardImmulationImeService.java
```

它基于 `InputMethodService` 创建输入法面板，并通过当前输入框的 `InputConnection` 发送文本。

## 已实现能力

- 原生 Android 输入法服务
- 输入法面板内编辑待输出文本
- 延迟开始输出
- 设置每个字符的输入间隔
- 开始/停止输出
- 普通文本逐字符输入
- 程序输入模式：
  1. 发送换行
  2. 读取当前光标前文本
  3. 删除当前行中由目标编辑器自动插入的空格或 Tab 缩进
  4. 输入原文本中下一行自己的缩进和内容

## 构建

需要 Android Studio 或本机 Android SDK/Gradle 环境。

在 `android` 目录下执行：

```bash
./gradlew assembleRelease
```

Windows 下：

```powershell
.\gradlew.bat assembleRelease
```

如果没有 Gradle Wrapper，可以在 Android Studio 中打开 `android` 目录，让 Android Studio 同步并构建工程。

## 使用

1. 安装生成的 APK。
2. 在 Android 系统设置中启用 `Keyboard Immulation` 输入法。
3. 切换到该输入法。
4. 在输入法面板中输入待输出文本。
5. 设置延迟、间隔和程序输入模式。
6. 点击“开始输出”。

## Release

Android release 命名：

```text
keyboard_immulation_android
```

资产建议：

```text
keyboard_immulation_android.apk
```

如果当前构建环境没有 Android SDK，可以先发布源码压缩包：

```text
keyboard_immulation_android.zip
```

