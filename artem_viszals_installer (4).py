"""
Установщик Артём viszals.

Что делает:
1. Показывает лицензионное соглашение (принять можно только галочкой).
2. Спрашивает папку установки.
3. Скачивает файл лаунчера с прогресс-баром.
4. Создаёт ярлык запуска (.bat) на рабочем столе.

Сборка в .exe (Windows):  pip install pyinstaller
                          pyinstaller --onefile --windowed artem_viszals_installer.py
Процесс установки виден в Диспетчере задач под именем собранного .exe.
"""

import queue
import threading
import urllib.request
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_NAME = "Артём viszals"
# ВАЖНО: вставь сюда прямую ссылку на файл лаунчера на твоём сайте.
LAUNCHER_URL = "https://example.com/artem_viszals_launcher.py"
LAUNCHER_FILE = "artem_viszals_launcher.py"

LICENSE_TEXT = """Лицензионное соглашение Артём viszals

1. Лаунчер — неофициальная программа. Он не связан с Mojang Studios и Microsoft.
2. Для игры в Minecraft нужна лицензионная копия игры и аккаунт Microsoft.
3. Лаунчер не обходит проверку владения игрой и не выдаёт игру бесплатно.
4. Программа предоставляется «как есть», без гарантий работы.
5. Устанавливая программу, ты соглашаешься с этими условиями.
"""


class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Установка: {APP_NAME}")
        self.geometry("520x380")
        self.resizable(False, False)
        self.install_dir = tk.StringVar(value=str(Path.home() / APP_NAME))
        self.accepted = tk.BooleanVar(value=False)
        self.queue = queue.Queue()
        self.page = None
        self.show_license()

    def clear(self):
        if self.page:
            self.page.destroy()
        self.page = tk.Frame(self, padx=20, pady=16)
        self.page.pack(fill="both", expand=True)
        return self.page

    def show_license(self):
        p = self.clear()
        tk.Label(p, text="Лицензионное соглашение", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        txt = tk.Text(p, height=12, wrap="word")
        txt.insert("1.0", LICENSE_TEXT)
        txt.config(state="disabled")
        txt.pack(fill="both", expand=True, pady=8)
        tk.Checkbutton(p, text="Я принимаю условия соглашения", variable=self.accepted,
                       command=self._toggle_next).pack(anchor="w")
        row = tk.Frame(p)
        row.pack(fill="x", pady=(12, 0))
        tk.Button(row, text="Отмена", command=self.destroy).pack(side="right", padx=4)
        self.next_btn = tk.Button(row, text="Далее", state="disabled", command=self.show_folder)
        self.next_btn.pack(side="right")
        self._toggle_next()

    def _toggle_next(self):
        self.next_btn.config(state="normal" if self.accepted.get() else "disabled")

    def show_folder(self):
        p = self.clear()
        tk.Label(p, text="Папка установки", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(p, text="Файл лаунчера будет сохранён в эту папку:").pack(anchor="w", pady=(8, 4))
        row = tk.Frame(p)
        row.pack(fill="x")
        tk.Entry(row, textvariable=self.install_dir).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Обзор...", command=self.browse).pack(side="left", padx=4)
        btns = tk.Frame(p)
        btns.pack(side="bottom", fill="x")
        tk.Button(btns, text="Назад", command=self.show_license).pack(side="left")
        tk.Button(btns, text="Установить", command=self.start_install).pack(side="right")

    def browse(self):
        folder = filedialog.askdirectory(initialdir=self.install_dir.get())
        if folder:
            self.install_dir.set(str(Path(folder) / APP_NAME))

    def start_install(self):
        target = Path(self.install_dir.get())
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Ошибка", f"Не удалось создать папку:\n{e}")
            return
        self.show_progress(target)

    def show_progress(self, target):
        p = self.clear()
        tk.Label(p, text="Установка", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.status = tk.Label(p, text="Подключение...")
        self.status.pack(anchor="w", pady=8)
        self.bar = ttk.Progressbar(p, length=460, mode="determinate")
        self.bar.pack(fill="x")
        threading.Thread(target=self._download, args=(target,), daemon=True).start()
        self.after(100, self._poll)

    def _download(self, target):
        try:
            dest = target / LAUNCHER_FILE
            with urllib.request.urlopen(LAUNCHER_URL) as resp, open(dest, "wb") as out:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    if total:
                        self.queue.put(("progress", done * 100 // total))
            self._make_shortcut(target)
            self.queue.put(("done", str(dest)))
        except Exception as e:
            self.queue.put(("error", str(e)))

    def _make_shortcut(self, target):
        desktop = Path.home() / "Desktop"
        if desktop.exists():
            bat = desktop / f"{APP_NAME}.bat"
            bat.write_text(f'@echo off\npython "{target / LAUNCHER_FILE}"\n', encoding="utf-8")

    def _poll(self):
        try:
            while True:
                kind, value = self.queue.get_nowait()
                if kind == "progress":
                    self.bar["value"] = value
                    self.status.config(text=f"Скачивание: {value}%")
                elif kind == "done":
                    self.show_finish(value)
                    return
                elif kind == "error":
                    messagebox.showerror("Ошибка", f"Не удалось скачать файл:\n{value}")
                    self.show_folder()
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def show_finish(self, path):
        p = self.clear()
        tk.Label(p, text="Готово", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(p, text=f"Лаунчер установлен:\n{path}", justify="left").pack(anchor="w", pady=8)
        tk.Button(p, text="Закрыть", command=self.destroy).pack(side="right")


if __name__ == "__main__":
    Installer().mainloop()
