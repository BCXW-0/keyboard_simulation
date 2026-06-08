import ctypes
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk


user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_ESCAPE = 0x1B
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_SHIFT = 0x10
VK_HOME = 0x24
VK_DELETE = 0x2E

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    )


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
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


def _send_input(*inputs):
    array_type = INPUT * len(inputs)
    sent = user32.SendInput(len(inputs), array_type(*inputs), ctypes.sizeof(INPUT))
    if sent != len(inputs):
        raise ctypes.WinError(ctypes.get_last_error())


def _keyboard_input(vk=0, scan=0, flags=0):
    return INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(ki=KEYBDINPUT(vk, scan, flags, 0, 0)),
    )


def send_vk(vk):
    _send_input(_keyboard_input(vk=vk), _keyboard_input(vk=vk, flags=KEYEVENTF_KEYUP))


def send_shift_home_delete():
    _send_input(
        _keyboard_input(vk=VK_SHIFT),
        _keyboard_input(vk=VK_HOME),
        _keyboard_input(vk=VK_HOME, flags=KEYEVENTF_KEYUP),
        _keyboard_input(vk=VK_SHIFT, flags=KEYEVENTF_KEYUP),
    )
    send_vk(VK_DELETE)


def send_utf16_unit(unit):
    _send_input(
        _keyboard_input(scan=unit, flags=KEYEVENTF_UNICODE),
        _keyboard_input(scan=unit, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP),
    )


def send_text_char(ch):
    encoded = ch.encode("utf-16-le", errors="surrogatepass")
    for index in range(0, len(encoded), 2):
        send_utf16_unit(int.from_bytes(encoded[index : index + 2], "little"))


def escape_is_down():
    return bool(user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000)


def iter_plain_output_actions(content, newline_mode, tab_mode):
    for ch in content:
        if ch == "\r":
            continue
        if ch == "\n" and newline_mode == "enter":
            yield ("vk", VK_RETURN)
        elif ch == "\t" and tab_mode == "key":
            yield ("vk", VK_TAB)
        else:
            yield ("char", ch)


def iter_output_actions(content, newline_mode, tab_mode, program_mode):
    if program_mode and newline_mode == "enter":
        yield from iter_program_output_actions(content, tab_mode)
        return

    yield from iter_plain_output_actions(content, newline_mode, tab_mode)


def emit_text_actions(text, tab_mode):
    for ch in text:
        if ch == "\t" and tab_mode == "key":
            yield ("vk", VK_TAB)
        else:
            yield ("char", ch)


def iter_program_output_actions(content, tab_mode):
    normalized = content.replace("\r\n", "\n").replace("\r", "")
    lines = normalized.split("\n")
    if not lines:
        return

    yield from emit_text_actions(lines[0], tab_mode)

    for index in range(1, len(lines)):
        yield ("vk", VK_RETURN)
        yield ("clear_auto_indent", None)
        yield from emit_text_actions(lines[index], tab_mode)


class RelayApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("键盘中转输入工具")
        self.geometry("900x640")
        self.minsize(760, 520)

        self.stop_event = threading.Event()
        self.worker = None

        self.delay_var = tk.StringVar(value="3")
        self.interval_var = tk.StringVar(value="5")
        self.newline_mode_var = tk.StringVar(value="enter")
        self.tab_mode_var = tk.StringVar(value="unicode")
        self.program_mode_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="输入内容后点击开始，3 秒内切到目标位置。Esc 可中断。")

        self._build_ui()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        options = ttk.Frame(root)
        options.grid(row=0, column=0, sticky="ew")
        for col in range(8):
            options.columnconfigure(col, weight=0)
        options.columnconfigure(7, weight=1)

        ttk.Label(options, text="延迟(秒)").grid(row=0, column=0, padx=(0, 6), pady=(0, 8))
        ttk.Spinbox(options, from_=0, to=60, increment=1, width=6, textvariable=self.delay_var).grid(
            row=0, column=1, padx=(0, 16), pady=(0, 8)
        )

        ttk.Label(options, text="间隔(毫秒)").grid(row=0, column=2, padx=(0, 6), pady=(0, 8))
        ttk.Spinbox(options, from_=0, to=1000, increment=1, width=7, textvariable=self.interval_var).grid(
            row=0, column=3, padx=(0, 16), pady=(0, 8)
        )

        ttk.Label(options, text="换行").grid(row=0, column=4, padx=(0, 6), pady=(0, 8))
        ttk.Combobox(
            options,
            state="readonly",
            width=12,
            textvariable=self.newline_mode_var,
            values=("enter", "unicode"),
        ).grid(row=0, column=5, padx=(0, 16), pady=(0, 8))

        ttk.Label(options, text="Tab").grid(row=0, column=6, padx=(0, 6), pady=(0, 8))
        ttk.Combobox(
            options,
            state="readonly",
            width=12,
            textvariable=self.tab_mode_var,
            values=("unicode", "key"),
        ).grid(row=0, column=7, sticky="w", pady=(0, 8))

        ttk.Checkbutton(
            options,
            text="程序输入模式（智能缩进）",
            variable=self.program_mode_var,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))

        text_frame = ttk.Frame(root)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.text = tk.Text(text_frame, wrap="none", undo=True, font=("Consolas", 11))
        self.text.grid(row=0, column=0, sticky="nsew")

        ybar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text.yview)
        ybar.grid(row=0, column=1, sticky="ns")
        xbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.text.xview)
        xbar.grid(row=1, column=0, sticky="ew")
        self.text.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)

        footer = ttk.Frame(root)
        footer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(2, weight=1)

        self.start_button = ttk.Button(footer, text="开始输出", command=self.start)
        self.start_button.grid(row=0, column=0, padx=(0, 8))
        self.stop_button = ttk.Button(footer, text="停止", command=self.stop, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(0, 12))
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=2, sticky="w")

    def start(self):
        if self.worker and self.worker.is_alive():
            return

        content = self.text.get("1.0", "end-1c")
        if not content:
            messagebox.showinfo("没有内容", "请先输入需要输出的文本。")
            return

        try:
            delay = max(0.0, float(self.delay_var.get()))
            interval = max(0.0, float(self.interval_var.get())) / 1000.0
        except ValueError:
            messagebox.showerror("参数错误", "延迟和间隔必须是数字。")
            return

        self.stop_event.clear()
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.worker = threading.Thread(
            target=self._type_worker,
            args=(
                content,
                delay,
                interval,
                self.newline_mode_var.get(),
                self.tab_mode_var.get(),
                self.program_mode_var.get(),
            ),
            daemon=True,
        )
        self.worker.start()

    def stop(self):
        self.stop_event.set()
        self.status_var.set("正在停止...")

    def _type_worker(self, content, delay, interval, newline_mode, tab_mode, program_mode):
        try:
            self._countdown(delay)
            if self.stop_event.is_set():
                return

            total = len(content)
            sent = 0
            for action, value in iter_output_actions(content, newline_mode, tab_mode, program_mode):
                if self.stop_event.is_set() or escape_is_down():
                    self.stop_event.set()
                    break

                if action == "vk":
                    send_vk(value)
                elif action == "clear_auto_indent":
                    send_shift_home_delete()
                else:
                    send_text_char(value)

                sent += 1
                if sent % 25 == 0:
                    self._set_status(f"输出中: 已发送 {sent} 个动作，Esc 可中断")
                if interval:
                    time.sleep(interval)

            if self.stop_event.is_set():
                self._set_status("已中断。")
            else:
                self._set_status("输出完成。")
        except Exception as exc:
            self._set_status(f"出错: {exc}")
            self.after(0, lambda: messagebox.showerror("输出失败", str(exc)))
        finally:
            self.after(0, self._reset_buttons)

    def _countdown(self, delay):
        end_time = time.monotonic() + delay
        while not self.stop_event.is_set():
            remaining = end_time - time.monotonic()
            if remaining <= 0:
                break
            self._set_status(f"{remaining:.1f} 秒后开始，请切到目标输入位置。Esc 可中断。")
            time.sleep(min(0.1, remaining))

    def _set_status(self, text):
        self.after(0, self.status_var.set, text)

    def _reset_buttons(self):
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)


if __name__ == "__main__":
    app = RelayApp()
    app.mainloop()
