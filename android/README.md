# Keyboard Immulation Android

Android 版本采用原生软键盘实现，不复用桌面端 Tkinter 或桌面键盘模拟。

核心思路是实现一个 Android 输入法服务 `InputMethodService`。用户启用并切换到该输入法后，应用通过当前输入框的 `InputConnection` 发送文本、换行、Tab 或删除等输入动作，从而实现和桌面端一致的“键盘中转输入”体验。

## 目标功能

- 在输入法界面中输入或载入待输出文本
- 点击开始后按顺序向当前输入框发送内容
- 支持字符间隔，避免目标应用处理不过来
- 支持换行和 Tab
- 支持程序输入模式：
  1. 发送换行
  2. 清除目标编辑器自动插入的当前行缩进
  3. 输入原文本中下一行自己的缩进和内容
- 支持停止输出

## 推荐实现

### 输入服务

使用 `InputMethodService` 创建原生输入法：

```kotlin
class KeyboardImmulationImeService : InputMethodService() {
    override fun onCreateInputView(): View {
        // 创建输入法面板 UI
    }
}
```

### 文本输入

通过当前输入框的 `InputConnection` 输入内容：

```kotlin
currentInputConnection.commitText(text, 1)
```

### 换行

优先发送编辑器动作或换行字符：

```kotlin
currentInputConnection.commitText("\n", 1)
```

### 清除自动缩进

Android 输入法无法像桌面端一样发送 `Shift + Home`。推荐用 `InputConnection` 查询当前光标前文本，并删除当前行行首到光标之间的空格或 Tab：

```kotlin
val beforeCursor = currentInputConnection.getTextBeforeCursor(256, 0)?.toString() ?: ""
val currentLine = beforeCursor.substringAfterLast('\n')
val autoIndentLength = currentLine.takeWhile { it == ' ' || it == '\t' }.length
if (autoIndentLength > 0 && currentLine.length == autoIndentLength) {
    currentInputConnection.deleteSurroundingText(autoIndentLength, 0)
}
```

然后再提交原文本中下一行自己的缩进和内容。

## 工程状态

当前目录先保留 Android 原生输入法版本的设计说明。下一步可以补充完整 Gradle 工程：

- `settings.gradle`
- 根目录 `build.gradle`
- `app/build.gradle`
- `AndroidManifest.xml`
- `InputMethodService`
- 输入法面板布局
- release APK 构建脚本

## Release

Android release 建议命名为：

```text
keyboard_immulation_android
```

资产建议为：

```text
keyboard_immulation_android.apk
```

