# -*- coding: utf-8 -*-
"""Keyboard Simulation - cross-platform keyboard relay tool."""

from __future__ import annotations

import json
import platform
import random
import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional, Sequence, Tuple

APP_NAME = "Keyboard Simulation"
APP_VERSION = "1.1.0"
CONFIG_DIR = Path.home() / ".keyboard_simulation"
CONFIG_PATH = CONFIG_DIR / "config.json"
HISTORY_PATH = CONFIG_DIR / "history.json"
MAX_HISTORY = 20

KEY_ENTER = "enter"
KEY_TAB = "tab"
KEY_CLEAR_AUTO_INDENT = "clear_auto_indent"

Action = Tuple[str, str]

SCENE_PRESETS = {
    "默认": {
        "delay": "3",
        "interval": "5",
        "newline_mode": "enter",
        "tab_mode": "unicode",
        "program_mode": False,
        "humanize": False,
        "jitter": "20",
        "slow_start": True,
    },
    "表单/考试": {
        "delay": "3",
        "interval": "25",
        "newline_mode": "enter",
        "tab_mode": "unicode",
        "program_mode": False,
        "humanize": True,
        "jitter": "30",
        "slow_start": True,
    },
    "代码/IDE": {
        "delay": "3",
        "interval": "8",
        "newline_mode": "enter",
        "tab_mode": "unicode",
        "program_mode": True,
        "humanize": False,
        "jitter": "10",
        "slow_start": True,
    },
    "长文稳定": {
        "delay": "3",
        "interval": "12",
        "newline_mode": "enter",
        "tab_mode": "unicode",
        "program_mode": False,
        "humanize": False,
        "jitter": "15",
        "slow_start": True,
    },
}


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def save_json(path: Path, data) -> None:
    ensure_config_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_newlines(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def clean_text(content: str) -> str:
    """Remove zero-width and BOM noise, normalize newlines, strip trailing spaces per line."""
    text = content.replace("\ufeff", "")
    text = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", text)
    text = normalize_newlines(text)
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    return "\n".join(lines)


def iter_plain_output_actions(content: str, newline_mode: str, tab_mode: str):
    for ch in content:
        if ch == "\r":
            continue
        if ch == "\n" and newline_mode == "enter":
            yield ("key", KEY_ENTER)
        elif ch == "\t" and tab_mode == "key":
            yield ("key", KEY_TAB)
        else:
            yield ("char", ch)


def emit_text_actions(text: str, tab_mode: str):
    for ch in text:
        if ch == "\t" and tab_mode == "key":
            yield ("key", KEY_TAB)
        else:
            yield ("char", ch)


def iter_program_output_actions(content: str, tab_mode: str):
    lines = normalize_newlines(content).split("\n")
    if not lines:
        return
    yield from emit_text_actions(lines[0], tab_mode)
    for index in range(1, len(lines)):
        yield ("key", KEY_ENTER)
        yield ("key", KEY_CLEAR_AUTO_INDENT)
        yield from emit_text_actions(lines[index], tab_mode)


def iter_output_actions(content: str, newline_mode: str, tab_mode: str, program_mode: bool) -> List[Action]:
    if program_mode and newline_mode == "enter":
        return list(iter_program_output_actions(content, tab_mode))
    return list(iter_plain_output_actions(content, newline_mode, tab_mode))


def estimate_duration_seconds(
    action_count: int,
    delay: float,
    interval_ms: float,
    humanize: bool,
    jitter_percent: float,
    slow_start: bool,
) -> float:
    if action_count <= 0:
        return delay
    base = interval_ms / 1000.0
    if humanize and jitter_percent > 0:
        base *= 1.0 + (jitter_percent / 200.0)
    total = delay + action_count * base
    if slow_start and action_count > 0:
        warm = min(12, action_count)
        total += warm * base * 0.75
    return total


def format_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m{sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"

class KeyboardBackend:
    name = "unknown"

    def send_char(self, ch: str) -> None:
        raise NotImplementedError

    def send_key(self, key_name: str) -> None:
        raise NotImplementedError

    def stop_is_down(self) -> bool:
        return False

    def pause_is_down(self) -> bool:
        return False

    def close(self) -> None:
        pass


class WindowsKeyboardBackend(KeyboardBackend):
    name = "Windows SendInput"

    def __init__(self) -> None:
        import ctypes

        self.ctypes = ctypes
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.INPUT_KEYBOARD = 1
        self.KEYEVENTF_KEYUP = 0x0002
        self.KEYEVENTF_UNICODE = 0x0004
        self.VK_ESCAPE = 0x1B
        self.VK_F8 = 0x77
        self.VK_RETURN = 0x0D
        self.VK_TAB = 0x09
        self.VK_SHIFT = 0x10
        self.VK_HOME = 0x24
        self.VK_DELETE = 0x2E
        self.ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
        backend = self

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = (
                ("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", backend.ULONG_PTR),
            )

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = (
                ("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", backend.ULONG_PTR),
            )

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = (
                ("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_ushort),
                ("wParamH", ctypes.c_ushort),
            )

        class INPUT_UNION(ctypes.Union):
            _fields_ = (
                ("ki", KEYBDINPUT),
                ("mi", MOUSEINPUT),
                ("hi", HARDWAREINPUT),
            )

        class INPUT(ctypes.Structure):
            _fields_ = (("type", ctypes.c_ulong), ("union", INPUT_UNION))

        self.KEYBDINPUT = KEYBDINPUT
        self.INPUT_UNION = INPUT_UNION
        self.INPUT = INPUT
        self._pause_was_down = False

    def _keyboard_input(self, vk: int = 0, scan: int = 0, flags: int = 0):
        return self.INPUT(
            type=self.INPUT_KEYBOARD,
            union=self.INPUT_UNION(ki=self.KEYBDINPUT(vk, scan, flags, 0, 0)),
        )

    def _send_input(self, *inputs) -> None:
        array_type = self.INPUT * len(inputs)
        sent = self.user32.SendInput(len(inputs), array_type(*inputs), self.ctypes.sizeof(self.INPUT))
        if sent != len(inputs):
            raise self.ctypes.WinError(self.ctypes.get_last_error())

    def _send_vk(self, vk: int) -> None:
        self._send_input(self._keyboard_input(vk=vk), self._keyboard_input(vk=vk, flags=self.KEYEVENTF_KEYUP))

    def _send_shift_home_delete(self) -> None:
        self._send_input(
            self._keyboard_input(vk=self.VK_SHIFT),
            self._keyboard_input(vk=self.VK_HOME),
            self._keyboard_input(vk=self.VK_HOME, flags=self.KEYEVENTF_KEYUP),
            self._keyboard_input(vk=self.VK_SHIFT, flags=self.KEYEVENTF_KEYUP),
        )
        self._send_vk(self.VK_DELETE)

    def _send_utf16_unit(self, unit: int) -> None:
        self._send_input(
            self._keyboard_input(scan=unit, flags=self.KEYEVENTF_UNICODE),
            self._keyboard_input(scan=unit, flags=self.KEYEVENTF_UNICODE | self.KEYEVENTF_KEYUP),
        )

    def send_char(self, ch: str) -> None:
        encoded = ch.encode("utf-16-le", errors="surrogatepass")
        for index in range(0, len(encoded), 2):
            self._send_utf16_unit(int.from_bytes(encoded[index : index + 2], "little"))

    def send_key(self, key_name: str) -> None:
        if key_name == KEY_ENTER:
            self._send_vk(self.VK_RETURN)
        elif key_name == KEY_TAB:
            self._send_vk(self.VK_TAB)
        elif key_name == KEY_CLEAR_AUTO_INDENT:
            self._send_shift_home_delete()
        else:
            raise ValueError(f"Unsupported key action: {key_name}")

    def _key_down(self, vk: int) -> bool:
        return bool(self.user32.GetAsyncKeyState(vk) & 0x8000)

    def stop_is_down(self) -> bool:
        return self._key_down(self.VK_ESCAPE)

    def pause_is_down(self) -> bool:
        down = self._key_down(self.VK_F8)
        edge = down and not self._pause_was_down
        self._pause_was_down = down
        return edge


class PynputKeyboardBackend(KeyboardBackend):
    def __init__(self) -> None:
        try:
            from pynput import keyboard
        except ImportError as exc:
            raise RuntimeError("macOS/Linux 需要先安装 pynput：python3 -m pip install pynput") from exc

        self.keyboard = keyboard
        self.controller = keyboard.Controller()
        self.name = f"{platform.system()} pynput"
        self._stop_flag = False
        self._pause_edge = False
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def _on_press(self, key) -> None:
        try:
            if key == self.keyboard.Key.esc:
                self._stop_flag = True
            elif key == self.keyboard.Key.f8:
                self._pause_edge = True
        except Exception:
            pass

    def send_char(self, ch: str) -> None:
        self.controller.type(ch)

    def send_key(self, key_name: str) -> None:
        key = self.keyboard.Key
        if key_name == KEY_ENTER:
            self.controller.press(key.enter)
            self.controller.release(key.enter)
        elif key_name == KEY_TAB:
            self.controller.press(key.tab)
            self.controller.release(key.tab)
        elif key_name == KEY_CLEAR_AUTO_INDENT:
            self._clear_auto_indent()
        else:
            raise ValueError(f"Unsupported key action: {key_name}")

    def _clear_auto_indent(self) -> None:
        key = self.keyboard.Key
        system = platform.system()
        if system == "Darwin":
            with self.controller.pressed(key.shift):
                with self.controller.pressed(key.cmd):
                    self.controller.press(key.left)
                    self.controller.release(key.left)
        else:
            with self.controller.pressed(key.shift):
                self.controller.press(key.home)
                self.controller.release(key.home)
        self.controller.press(key.delete)
        self.controller.release(key.delete)

    def stop_is_down(self) -> bool:
        if self._stop_flag:
            self._stop_flag = False
            return True
        return False

    def pause_is_down(self) -> bool:
        if self._pause_edge:
            self._pause_edge = False
            return True
        return False

    def close(self) -> None:
        try:
            self._listener.stop()
        except Exception:
            pass


def create_keyboard_backend() -> KeyboardBackend:
    system = platform.system()
    if system == "Windows":
        return WindowsKeyboardBackend()
    if system in ("Darwin", "Linux"):
        return PynputKeyboardBackend()
    raise RuntimeError(f"暂不支持当前系统：{system}")

class RelayApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("980x720")
        self.minsize(820, 600)

        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.worker: Optional[threading.Thread] = None

        self.delay_var = tk.StringVar(value="3")
        self.interval_var = tk.StringVar(value="5")
        self.newline_mode_var = tk.StringVar(value="enter")
        self.tab_mode_var = tk.StringVar(value="unicode")
        self.program_mode_var = tk.BooleanVar(value=False)
        self.humanize_var = tk.BooleanVar(value=False)
        self.jitter_var = tk.StringVar(value="20")
        self.slow_start_var = tk.BooleanVar(value=True)
        self.save_history_var = tk.BooleanVar(value=True)
        self.scene_var = tk.StringVar(value="默认")
        self.status_var = tk.StringVar(
            value="输入内容后点开始；倒计时内切换到目标输入框。Esc 停止，F8 暂停/继续。"
        )
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text_var = tk.StringVar(value="进度 0/0 · ETA --")
        self.history_var = tk.StringVar(value="")

        self.resume_actions: List[Action] = []
        self.resume_index = 0
        self.resume_meta: dict = {}

        try:
            self.keyboard_backend: Optional[KeyboardBackend] = create_keyboard_backend()
        except Exception as exc:
            self.keyboard_backend = None
            self.status_var.set(str(exc))

        self.history_items: List[dict] = load_json(HISTORY_PATH, [])
        self._load_settings()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(120, self._poll_hotkeys_idle)
        self._refresh_estimate()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text=APP_NAME, font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="本地运行 · 不上传内容 · 免费开源", foreground="#555").grid(
            row=0, column=1, sticky="e"
        )

        options = ttk.LabelFrame(root, text="参数与场景", padding=8)
        options.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        for col in range(10):
            options.columnconfigure(col, weight=0)
        options.columnconfigure(9, weight=1)

        ttk.Label(options, text="场景预设").grid(row=0, column=0, padx=(0, 6), pady=4, sticky="w")
        scene_box = ttk.Combobox(
            options,
            state="readonly",
            width=12,
            textvariable=self.scene_var,
            values=tuple(SCENE_PRESETS.keys()),
        )
        scene_box.grid(row=0, column=1, padx=(0, 16), pady=4, sticky="w")
        scene_box.bind("<<ComboboxSelected>>", lambda _e: self._apply_scene_preset())

        ttk.Label(options, text="延迟(秒)").grid(row=0, column=2, padx=(0, 6), pady=4, sticky="w")
        ttk.Spinbox(options, from_=0, to=60, increment=1, width=6, textvariable=self.delay_var).grid(
            row=0, column=3, padx=(0, 16), pady=4
        )
        ttk.Label(options, text="间隔(毫秒)").grid(row=0, column=4, padx=(0, 6), pady=4, sticky="w")
        ttk.Spinbox(options, from_=0, to=1000, increment=1, width=7, textvariable=self.interval_var).grid(
            row=0, column=5, padx=(0, 16), pady=4
        )
        ttk.Label(options, text="换行").grid(row=0, column=6, padx=(0, 6), pady=4, sticky="w")
        ttk.Combobox(
            options, state="readonly", width=10, textvariable=self.newline_mode_var, values=("enter", "unicode")
        ).grid(row=0, column=7, padx=(0, 16), pady=4)
        ttk.Label(options, text="Tab").grid(row=0, column=8, padx=(0, 6), pady=4, sticky="w")
        ttk.Combobox(
            options, state="readonly", width=10, textvariable=self.tab_mode_var, values=("unicode", "key")
        ).grid(row=0, column=9, sticky="w", pady=4)

        ttk.Checkbutton(
            options,
            text="程序输入模式（智能缩进）",
            variable=self.program_mode_var,
            command=self._refresh_estimate,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Checkbutton(options, text="慢启动", variable=self.slow_start_var, command=self._refresh_estimate).grid(
            row=1, column=3, sticky="w", pady=4
        )
        ttk.Checkbutton(options, text="拟人抖动", variable=self.humanize_var, command=self._refresh_estimate).grid(
            row=1, column=4, sticky="w", pady=4
        )
        ttk.Label(options, text="抖动%").grid(row=1, column=5, padx=(0, 6), sticky="e")
        ttk.Spinbox(options, from_=0, to=80, increment=5, width=6, textvariable=self.jitter_var).grid(
            row=1, column=6, sticky="w", pady=4
        )
        ttk.Checkbutton(options, text="保存本地历史", variable=self.save_history_var).grid(
            row=1, column=7, columnspan=2, sticky="w", pady=4
        )
        backend_name = self.keyboard_backend.name if self.keyboard_backend else "不可用"
        ttk.Label(options, text=f"输入后端: {backend_name}").grid(row=1, column=9, sticky="e", pady=4)

        text_frame = ttk.LabelFrame(root, text="待输出内容", padding=8)
        text_frame.grid(row=2, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(1, weight=1)

        tools = ttk.Frame(text_frame)
        tools.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tools.columnconfigure(6, weight=1)
        ttk.Button(tools, text="导入文件", command=self.import_file).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(tools, text="清洗文本", command=self.clean_content).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(tools, text="清空", command=self.clear_content).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(tools, text="复制参数摘要", command=self.copy_settings_summary).grid(row=0, column=3, padx=(0, 12))
        ttk.Label(tools, text="历史").grid(row=0, column=4, padx=(0, 6))
        self.history_combo = ttk.Combobox(
            tools, state="readonly", width=28, textvariable=self.history_var, values=self._history_labels()
        )
        self.history_combo.grid(row=0, column=5, padx=(0, 6))
        self.history_combo.bind("<<ComboboxSelected>>", lambda _e: self._load_selected_history())
        ttk.Button(tools, text="清除历史", command=self.clear_history).grid(row=0, column=6, sticky="w")

        editor = ttk.Frame(text_frame)
        editor.grid(row=1, column=0, sticky="nsew")
        editor.columnconfigure(0, weight=1)
        editor.rowconfigure(0, weight=1)
        self.text = tk.Text(editor, wrap="none", undo=True, font=("Consolas", 11))
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text.bind("<<Modified>>", self._on_text_modified)
        ybar = ttk.Scrollbar(editor, orient=tk.VERTICAL, command=self.text.yview)
        ybar.grid(row=0, column=1, sticky="ns")
        xbar = ttk.Scrollbar(editor, orient=tk.HORIZONTAL, command=self.text.xview)
        xbar.grid(row=1, column=0, sticky="ew")
        self.text.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)

        progress_frame = ttk.Frame(root)
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        progress_frame.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(progress_frame, maximum=100, variable=self.progress_var)
        self.progress.grid(row=0, column=0, sticky="ew")
        ttk.Label(progress_frame, textvariable=self.progress_text_var).grid(row=1, column=0, sticky="w", pady=(4, 0))

        footer = ttk.Frame(root)
        footer.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(5, weight=1)
        self.start_button = ttk.Button(footer, text="开始输出", command=self.start)
        self.start_button.grid(row=0, column=0, padx=(0, 6))
        self.pause_button = ttk.Button(footer, text="暂停(F8)", command=self.toggle_pause, state=tk.DISABLED)
        self.pause_button.grid(row=0, column=1, padx=(0, 6))
        self.continue_button = ttk.Button(
            footer, text="断点续打", command=self.continue_from_checkpoint, state=tk.DISABLED
        )
        self.continue_button.grid(row=0, column=2, padx=(0, 6))
        self.stop_button = ttk.Button(footer, text="停止(Esc)", command=self.stop, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=3, padx=(0, 12))
        ttk.Label(footer, textvariable=self.status_var, wraplength=520, justify="left").grid(
            row=0, column=5, sticky="w"
        )

        for var in (
            self.delay_var,
            self.interval_var,
            self.jitter_var,
            self.newline_mode_var,
            self.tab_mode_var,
        ):
            var.trace_add("write", lambda *_args: self._refresh_estimate())

    def _on_text_modified(self, _event=None) -> None:
        if self.text.edit_modified():
            self.text.edit_modified(False)
            self._refresh_estimate()

    def _parse_number(self, value: str, fallback: float) -> float:
        try:
            return float(value)
        except ValueError:
            return fallback

    def _current_settings(self) -> dict:
        return {
            "delay": self.delay_var.get(),
            "interval": self.interval_var.get(),
            "newline_mode": self.newline_mode_var.get(),
            "tab_mode": self.tab_mode_var.get(),
            "program_mode": bool(self.program_mode_var.get()),
            "humanize": bool(self.humanize_var.get()),
            "jitter": self.jitter_var.get(),
            "slow_start": bool(self.slow_start_var.get()),
            "save_history": bool(self.save_history_var.get()),
            "scene": self.scene_var.get(),
        }

    def _apply_settings(self, data: dict) -> None:
        self.delay_var.set(str(data.get("delay", "3")))
        self.interval_var.set(str(data.get("interval", "5")))
        self.newline_mode_var.set(data.get("newline_mode", "enter"))
        self.tab_mode_var.set(data.get("tab_mode", "unicode"))
        self.program_mode_var.set(bool(data.get("program_mode", False)))
        self.humanize_var.set(bool(data.get("humanize", False)))
        self.jitter_var.set(str(data.get("jitter", "20")))
        self.slow_start_var.set(bool(data.get("slow_start", True)))
        self.save_history_var.set(bool(data.get("save_history", True)))
        scene = data.get("scene", "默认")
        if scene in SCENE_PRESETS:
            self.scene_var.set(scene)

    def _load_settings(self) -> None:
        data = load_json(CONFIG_PATH, {})
        if isinstance(data, dict) and data:
            self._apply_settings(data)

    def _save_settings(self) -> None:
        save_json(CONFIG_PATH, self._current_settings())

    def _apply_scene_preset(self) -> None:
        preset = SCENE_PRESETS.get(self.scene_var.get())
        if not preset:
            return
        self.delay_var.set(preset["delay"])
        self.interval_var.set(preset["interval"])
        self.newline_mode_var.set(preset["newline_mode"])
        self.tab_mode_var.set(preset["tab_mode"])
        self.program_mode_var.set(preset["program_mode"])
        self.humanize_var.set(preset["humanize"])
        self.jitter_var.set(preset["jitter"])
        self.slow_start_var.set(preset["slow_start"])
        self._refresh_estimate()
        self.status_var.set(f"已应用场景预设：{self.scene_var.get()}")

    def _history_labels(self) -> List[str]:
        labels = []
        for item in self.history_items:
            preview = item.get("preview", "").replace("\n", " ")
            labels.append(f'{item.get("time", "")} | {preview[:40]}')
        return labels

    def _refresh_history_combo(self) -> None:
        labels = self._history_labels()
        self.history_combo.configure(values=labels)
        self.history_var.set(labels[0] if labels else "")

    def _push_history(self, content: str) -> None:
        if not self.save_history_var.get():
            return
        preview = clean_text(content).strip()
        if not preview:
            return
        item = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "preview": preview[:80],
            "content": content,
            "settings": self._current_settings(),
        }
        self.history_items = [item] + [old for old in self.history_items if old.get("content") != content]
        self.history_items = self.history_items[:MAX_HISTORY]
        save_json(HISTORY_PATH, self.history_items)
        self._refresh_history_combo()

    def _load_selected_history(self) -> None:
        label = self.history_var.get()
        labels = self._history_labels()
        if label not in labels:
            return
        item = self.history_items[labels.index(label)]
        self.text.delete("1.0", "end")
        self.text.insert("1.0", item.get("content", ""))
        if isinstance(item.get("settings"), dict):
            self._apply_settings(item["settings"])
        self._refresh_estimate()
        self.status_var.set("已载入本地历史内容。")

    def clear_history(self) -> None:
        if not messagebox.askyesno("清除历史", "确定清除全部本地历史记录？"):
            return
        self.history_items = []
        save_json(HISTORY_PATH, [])
        self._refresh_history_combo()
        self.status_var.set("本地历史已清除。")

    def import_file(self) -> None:
        path = filedialog.askopenfilename(
            title="导入文本文件",
            filetypes=(("Text", "*.txt;*.py;*.md;*.json;*.csv;*.log"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = Path(path).read_text(encoding="gbk", errors="replace")
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc))
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self._refresh_estimate()
        self.status_var.set(f"已导入：{Path(path).name}")

    def clean_content(self) -> None:
        cleaned = clean_text(self.text.get("1.0", "end-1c"))
        self.text.delete("1.0", "end")
        self.text.insert("1.0", cleaned)
        self._refresh_estimate()
        self.status_var.set("已清洗零宽字符、统一换行并去除行尾空白。")

    def clear_content(self) -> None:
        self.text.delete("1.0", "end")
        self._refresh_estimate()

    def copy_settings_summary(self) -> None:
        s = self._current_settings()
        summary = (
            f"{APP_NAME} v{APP_VERSION}\n"
            f"scene={s['scene']} delay={s['delay']}s interval={s['interval']}ms\n"
            f"newline={s['newline_mode']} tab={s['tab_mode']} program={s['program_mode']}\n"
            f"humanize={s['humanize']} jitter={s['jitter']}% slow_start={s['slow_start']}"
        )
        self.clipboard_clear()
        self.clipboard_append(summary)
        self.status_var.set("参数摘要已复制到剪贴板。")

    def _build_actions_from_ui(self) -> Optional[List[Action]]:
        content = self.text.get("1.0", "end-1c")
        if not content:
            messagebox.showinfo("没有内容", "请先输入需要输出的文本。")
            return None
        return iter_output_actions(
            content,
            self.newline_mode_var.get(),
            self.tab_mode_var.get(),
            bool(self.program_mode_var.get()),
        )

    def _refresh_estimate(self) -> None:
        content = ""
        try:
            content = self.text.get("1.0", "end-1c")
        except Exception:
            pass
        actions = iter_output_actions(
            content,
            self.newline_mode_var.get(),
            self.tab_mode_var.get(),
            bool(self.program_mode_var.get()),
        )
        delay = max(0.0, self._parse_number(self.delay_var.get(), 3.0))
        interval = max(0.0, self._parse_number(self.interval_var.get(), 5.0))
        jitter = max(0.0, self._parse_number(self.jitter_var.get(), 20.0))
        total = estimate_duration_seconds(
            len(actions),
            delay,
            interval,
            bool(self.humanize_var.get()),
            jitter,
            bool(self.slow_start_var.get()),
        )
        chars = len(content.replace("\r", ""))
        self.progress_text_var.set(f"动作 {len(actions)} · 字符 {chars} · 预计 {format_duration(total)}")
        if not (self.worker and self.worker.is_alive()):
            self.progress_var.set(0.0)

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.keyboard_backend:
            messagebox.showerror("后端不可用", self.status_var.get())
            return

        actions = self._build_actions_from_ui()
        if actions is None:
            return
        if not actions:
            messagebox.showinfo("没有内容", "没有可输出的动作。")
            return

        try:
            delay = max(0.0, float(self.delay_var.get()))
            interval_ms = max(0.0, float(self.interval_var.get()))
            jitter = max(0.0, float(self.jitter_var.get()))
        except ValueError:
            messagebox.showerror("参数错误", "延迟、间隔和抖动必须是数字。")
            return

        content = self.text.get("1.0", "end-1c")
        self._push_history(content)
        self._save_settings()

        self.resume_actions = actions
        self.resume_index = 0
        self.resume_meta = {
            "delay": delay,
            "interval_ms": interval_ms,
            "jitter": jitter,
            "humanize": bool(self.humanize_var.get()),
            "slow_start": bool(self.slow_start_var.get()),
        }
        self._launch_worker(start_index=0, use_delay=True)

    def continue_from_checkpoint(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.resume_actions or self.resume_index >= len(self.resume_actions):
            messagebox.showinfo("无断点", "当前没有可续打的断点。")
            return
        self._launch_worker(start_index=self.resume_index, use_delay=False)

    def _launch_worker(self, start_index: int, use_delay: bool) -> None:
        self.stop_event.clear()
        self.pause_event.clear()
        self.start_button.configure(state=tk.DISABLED)
        self.pause_button.configure(state=tk.NORMAL, text="暂停(F8)")
        self.continue_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)

        meta = dict(self.resume_meta)
        meta["use_delay"] = use_delay
        self.worker = threading.Thread(
            target=self._type_worker,
            args=(self.resume_actions, start_index, meta),
            daemon=True,
        )
        self.worker.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.pause_event.clear()
        self._set_status("正在停止...")

    def toggle_pause(self) -> None:
        if not (self.worker and self.worker.is_alive()):
            return
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.configure(text="暂停(F8)")
            self._set_status("已继续输出。")
        else:
            self.pause_event.set()
            self.pause_button.configure(text="继续(F8)")
            self._set_status("已暂停。按 F8 或点击继续。")

    def _poll_hotkeys_idle(self) -> None:
        if self.worker and self.worker.is_alive() and self.keyboard_backend:
            if self.keyboard_backend.stop_is_down():
                self.stop()
            elif self.keyboard_backend.pause_is_down():
                self.toggle_pause()
        self.after(120, self._poll_hotkeys_idle)

    def _sleep_interruptible(self, seconds: float) -> bool:
        end = time.monotonic() + max(0.0, seconds)
        while True:
            if self.stop_event.is_set():
                return True
            if self.keyboard_backend and self.keyboard_backend.stop_is_down():
                self.stop_event.set()
                return True
            if self.keyboard_backend and self.keyboard_backend.pause_is_down():
                if self.pause_event.is_set():
                    self.pause_event.clear()
                    self.after(0, lambda: self.pause_button.configure(text="暂停(F8)"))
                    self._set_status("已继续输出。")
                else:
                    self.pause_event.set()
                    self.after(0, lambda: self.pause_button.configure(text="继续(F8)"))
                    self._set_status("已暂停。按 F8 或点击继续。")

            while self.pause_event.is_set() and not self.stop_event.is_set():
                time.sleep(0.05)
                if self.keyboard_backend and self.keyboard_backend.stop_is_down():
                    self.stop_event.set()
                    return True
                if self.keyboard_backend and self.keyboard_backend.pause_is_down():
                    self.pause_event.clear()
                    self.after(0, lambda: self.pause_button.configure(text="暂停(F8)"))
                    self._set_status("已继续输出。")

            remaining = end - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(0.05, remaining))

    def _action_interval(self, index: int, meta: dict) -> float:
        base = max(0.0, float(meta.get("interval_ms", 0.0))) / 1000.0
        if meta.get("slow_start"):
            if index < 8:
                base *= 2.2 - index * 0.12
            elif index < 16:
                base *= 1.3
        if meta.get("humanize"):
            jitter = max(0.0, float(meta.get("jitter", 0.0))) / 100.0
            if jitter > 0 and base > 0:
                base *= 1.0 + random.uniform(-jitter, jitter)
        return max(0.0, base)

    def _send_with_retry(self, action: str, value: str, retries: int = 2) -> None:
        last_exc = None
        for attempt in range(retries + 1):
            try:
                if action == "key":
                    self.keyboard_backend.send_key(value)
                else:
                    self.keyboard_backend.send_char(value)
                return
            except Exception as exc:
                last_exc = exc
                time.sleep(0.02 * (attempt + 1))
        raise last_exc

    def _type_worker(self, actions: Sequence[Action], start_index: int, meta: dict) -> None:
        total = len(actions)
        index = start_index
        try:
            if meta.get("use_delay", True):
                delay = float(meta.get("delay", 0.0))
                if self._countdown(delay):
                    self.resume_index = index
                    self._set_status("已中断。")
                    return

            while index < total:
                if self.stop_event.is_set() or (
                    self.keyboard_backend and self.keyboard_backend.stop_is_down()
                ):
                    self.stop_event.set()
                    break

                while self.pause_event.is_set() and not self.stop_event.is_set():
                    if self.keyboard_backend and self.keyboard_backend.pause_is_down():
                        self.pause_event.clear()
                        self.after(0, lambda: self.pause_button.configure(text="暂停(F8)"))
                        self._set_status("已继续输出。")
                        break
                    if self.keyboard_backend and self.keyboard_backend.stop_is_down():
                        self.stop_event.set()
                        break
                    time.sleep(0.05)

                if self.stop_event.is_set():
                    break

                action, value = actions[index]
                self._send_with_retry(action, value)
                index += 1
                self.resume_index = index

                done = index
                percent = 100.0 * done / total if total else 100.0
                remain_actions = total - done
                avg = self._action_interval(max(0, index - 1), meta)
                eta = remain_actions * avg
                self.after(0, self.progress_var.set, percent)
                self.after(
                    0,
                    self.progress_text_var.set,
                    f"进度 {done}/{total} · {percent:.1f}% · ETA {format_duration(eta)}",
                )
                if done % 20 == 0 or done == total:
                    self._set_status(f"输出中：{done}/{total}。Esc 停止，F8 暂停/继续。")

                interval = self._action_interval(index - 1, meta)
                if interval > 0 and self._sleep_interruptible(interval):
                    break

            if self.stop_event.is_set():
                if self.resume_index < total:
                    self._set_status(f"已中断，断点 {self.resume_index}/{total}。可点“断点续打”。")
                else:
                    self._set_status("已中断。")
            else:
                self.resume_index = total
                self.after(0, self.progress_var.set, 100.0)
                self.after(0, self.progress_text_var.set, f"进度 {total}/{total} · 100% · 完成")
                self._set_status("输出完成。")
        except Exception as exc:
            self.resume_index = index
            self._set_status(f"出错，已保留断点 {index}/{total}：{exc}")
            self.after(0, lambda: messagebox.showerror("输出失败", str(exc)))
        finally:
            self.after(0, self._reset_buttons)

    def _countdown(self, delay: float) -> bool:
        remaining_total = max(0.0, delay)
        end_time = time.monotonic() + remaining_total
        while not self.stop_event.is_set():
            if self.keyboard_backend and self.keyboard_backend.stop_is_down():
                self.stop_event.set()
                break
            if self.keyboard_backend and self.keyboard_backend.pause_is_down():
                left = max(0.0, end_time - time.monotonic())
                self.pause_event.set()
                self.after(0, lambda: self.pause_button.configure(text="继续(F8)"))
                self._set_status("倒计时已暂停。")
                while self.pause_event.is_set() and not self.stop_event.is_set():
                    time.sleep(0.05)
                    if self.keyboard_backend and self.keyboard_backend.pause_is_down():
                        self.pause_event.clear()
                        end_time = time.monotonic() + left
                        self.after(0, lambda: self.pause_button.configure(text="暂停(F8)"))
                    if self.keyboard_backend and self.keyboard_backend.stop_is_down():
                        self.stop_event.set()
                        break
            remaining = end_time - time.monotonic()
            if remaining <= 0:
                break
            self._set_status(f"{remaining:.1f} 秒后开始，请切换到目标输入位置。Esc 停止，F8 暂停。")
            time.sleep(min(0.1, remaining))
        return self.stop_event.is_set()

    def _set_status(self, text: str) -> None:
        self.after(0, self.status_var.set, text)

    def _reset_buttons(self) -> None:
        self.start_button.configure(state=tk.NORMAL)
        self.pause_button.configure(state=tk.DISABLED, text="暂停(F8)")
        self.stop_button.configure(state=tk.DISABLED)
        can_continue = bool(self.resume_actions) and 0 < self.resume_index < len(self.resume_actions)
        self.continue_button.configure(state=tk.NORMAL if can_continue else tk.DISABLED)
        self.pause_event.clear()

    def _on_close(self) -> None:
        self.stop_event.set()
        self._save_settings()
        if self.keyboard_backend:
            self.keyboard_backend.close()
        self.destroy()


if __name__ == "__main__":
    app = RelayApp()
    app.mainloop()

