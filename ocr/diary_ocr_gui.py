#!/usr/bin/env python3
"""受付日誌OCR自動化システム - GUIアプリ"""

import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

sys.path.insert(0, str(Path(__file__).parent.parent))  # プロジェクトルートをパスに追加

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class _StdoutCapture:
    """バックグラウンドスレッドの print をGUIログに転送する"""

    def __init__(self, log_fn):
        self._log = log_fn
        self._buf = ""

    def write(self, text: str) -> None:
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line:
                self._log(line)

    def flush(self) -> None:
        if self._buf.strip():
            self._log(self._buf)
            self._buf = ""


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("受付日誌OCRシステム")
        self.resizable(False, False)
        self._build_ui()
        self._center_window()

    # ──────────────────────── UI構築 ────────────────────────

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 4}

        # ── Step 1: PNG → Markdown ──
        f1 = ttk.LabelFrame(self, text=" Step 1: OCR変換（PNG → Markdown）", padding=10)
        f1.grid(row=0, column=0, **pad, sticky="ew")
        f1.columnconfigure(1, weight=1)

        ttk.Label(f1, text="画像フォルダ:").grid(row=0, column=0, sticky="w")
        self.dir_var = tk.StringVar()
        ttk.Entry(f1, textvariable=self.dir_var, width=44).grid(row=0, column=1, padx=(6, 4))
        ttk.Button(f1, text="参照...", command=self._browse_dir).grid(row=0, column=2)

        ttk.Label(f1, text="展覧会名:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.exhibition_var = tk.StringVar()
        ttk.Entry(f1, textvariable=self.exhibition_var, width=44).grid(
            row=1, column=1, padx=(6, 4), pady=(6, 0)
        )
        ttk.Label(f1, text="例: 8_春季展_前期", foreground="gray").grid(
            row=1, column=2, sticky="w", pady=(6, 0)
        )

        self.overwrite_var = tk.BooleanVar()
        ttk.Checkbutton(f1, text="既存MDファイルを上書きする", variable=self.overwrite_var).grid(
            row=2, column=1, sticky="w", padx=(6, 0), pady=(6, 0)
        )

        self.btn_ocr = ttk.Button(
            f1, text="OCR実行", command=self._run_ocr, style="Accent.TButton"
        )
        self.btn_ocr.grid(row=2, column=2, pady=(6, 0))

        # ── Step 2: Markdown → JSON ──
        f2 = ttk.LabelFrame(self, text=" Step 2: JSON変換（Markdown → JSON）", padding=10)
        f2.grid(row=1, column=0, **pad, sticky="ew")
        f2.columnconfigure(1, weight=1)

        ttk.Label(f2, text="Markdownファイル:").grid(row=0, column=0, sticky="w")
        self.md_var = tk.StringVar()
        ttk.Entry(f2, textvariable=self.md_var, width=44).grid(row=0, column=1, padx=(6, 4))
        ttk.Button(f2, text="参照...", command=self._browse_md).grid(row=0, column=2)

        ttk.Label(f2, text="出力JSON:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.json_out_var = tk.StringVar()
        ttk.Entry(f2, textvariable=self.json_out_var, width=44).grid(
            row=1, column=1, padx=(6, 4), pady=(6, 0)
        )
        ttk.Label(f2, text="空欄で自動設定", foreground="gray").grid(
            row=1, column=2, sticky="w", pady=(6, 0)
        )

        self.btn_json = ttk.Button(
            f2, text="JSON変換", command=self._run_json, style="Accent.TButton"
        )
        self.btn_json.grid(row=2, column=2, pady=(8, 0))

        # ── ログ ──
        f3 = ttk.LabelFrame(self, text=" ログ", padding=6)
        f3.grid(row=2, column=0, **pad, sticky="nsew")

        self.log_text = scrolledtext.ScrolledText(
            f3, width=72, height=14, state="disabled",
            font=("Courier New", 9), background="#1e1e1e", foreground="#d4d4d4",
            insertbackground="white",
        )
        self.log_text.pack(fill="both", expand=True)

        self.log_text.tag_config("ok",    foreground="#4ec9b0")
        self.log_text.tag_config("skip",  foreground="#808080")
        self.log_text.tag_config("warn",  foreground="#dcdcaa")
        self.log_text.tag_config("error", foreground="#f44747")
        self.log_text.tag_config("saved", foreground="#9cdcfe")
        self.log_text.tag_config("info",  foreground="#c586c0")

        # ── プログレスバー ──
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=400)
        self.progress.grid(row=3, column=0, padx=10, pady=(0, 8), sticky="ew")

    def _center_window(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    # ──────────────────────── ファイル選択 ────────────────────────

    def _browse_dir(self) -> None:
        path = filedialog.askdirectory(title="画像フォルダを選択")
        if path:
            self.dir_var.set(path)

    def _browse_md(self) -> None:
        path = filedialog.askopenfilename(
            title="Markdownファイルを選択",
            filetypes=[("Markdown", "*.md"), ("すべて", "*.*")],
        )
        if path:
            self.md_var.set(path)

    # ──────────────────────── ログ出力 ────────────────────────

    def _log(self, message: str) -> None:
        self.after(0, lambda m=message: self._append_log(m))

    def _append_log(self, message: str) -> None:
        tag = None
        m = message.upper()
        if "[OK]" in m or "→" in m:
            tag = "ok"
        elif "[SKIP]" in m:
            tag = "skip"
        elif "[WARN]" in m:
            tag = "warn"
        elif "[ERROR]" in m:
            tag = "error"
        elif "[SAVED]" in m:
            tag = "saved"
        elif "[INFO]" in m or "[OCR]" in m or "[DONE]" in m:
            tag = "info"

        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n", tag or "")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _log_separator(self, label: str) -> None:
        self._append_log(f"\n{'─' * 30}  {label}  {'─' * 30}")

    # ──────────────────────── ボタン制御 ────────────────────────

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.btn_ocr.configure(state=state)
        self.btn_json.configure(state=state)
        if busy:
            self.progress.start(10)
        else:
            self.progress.stop()

    # ──────────────────────── Step 1: OCR → Markdown ────────────────────────

    def _run_ocr(self) -> None:
        dir_path = self.dir_var.get().strip()
        exhibition = self.exhibition_var.get().strip()

        if not dir_path:
            self._log("[ERROR] 画像フォルダを指定してください")
            return
        if not exhibition:
            self._log("[ERROR] 展覧会名を入力してください")
            return

        self._set_busy(True)
        threading.Thread(
            target=self._ocr_worker,
            args=(dir_path, exhibition, self.overwrite_var.get()),
            daemon=True,
        ).start()

    def _ocr_worker(self, dir_path: str, exhibition: str, overwrite: bool) -> None:
        from core import diary_ocr

        self._log_separator("OCR開始")
        old_stdout = sys.stdout
        sys.stdout = _StdoutCapture(self._log)
        try:
            md_path = diary_ocr.run(dir_path, exhibition, overwrite=overwrite)
            if md_path:
                self.after(0, lambda: self.md_var.set(str(md_path)))
                self._log(f"\n[DONE] OCR完了 → {md_path.name}")
                self._log("[INFO] Markdownを確認・修正後、Step 2でJSON変換してください")
        except Exception as e:
            self._log(f"[ERROR] {e}")
        finally:
            sys.stdout = old_stdout
            self.after(0, lambda: self._set_busy(False))

    # ──────────────────────── Step 2: Markdown → JSON ────────────────────────

    def _run_json(self) -> None:
        md_path = self.md_var.get().strip()
        json_out = self.json_out_var.get().strip() or None

        if not md_path:
            self._log("[ERROR] Markdownファイルを指定してください")
            return
        if not Path(md_path).exists():
            self._log(f"[ERROR] ファイルが見つかりません: {md_path}")
            return

        self._set_busy(True)
        threading.Thread(
            target=self._json_worker,
            args=(md_path, json_out),
            daemon=True,
        ).start()

    def _json_worker(self, md_path: str, json_out: str | None) -> None:
        from core import md_to_json

        self._log_separator("JSON変換開始")
        old_stdout = sys.stdout
        sys.stdout = _StdoutCapture(self._log)
        try:
            out_path = md_to_json.run(md_path, json_out)
            if out_path:
                self._log(f"\n[DONE] JSON変換完了 → {out_path.name}")
        except Exception as e:
            self._log(f"[ERROR] {e}")
        finally:
            sys.stdout = old_stdout
            self.after(0, lambda: self._set_busy(False))


# ──────────────────────── エントリポイント ────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
