"""
YouTrak
Prosty, lokalny konwerter linków YouTube na pliki MP3 do własnej kolekcji muzycznej.

Bezpieczeństwo / dlaczego tak, a nie gotowy "yt2mp3.exe" z internetu:
- Cały kod jest jawny i mieści się w tym jednym pliku.
- Jedyne zależności to yt-dlp (aktywnie rozwijany, open-source następca youtube-dl)
  oraz imageio-ffmpeg (dostarcza oficjalny, statyczny build ffmpeg z PyPI).
- Program nie łączy się z żadnym serwerem poza samym YouTube - nie ma reklam,
  nie ma pobierania "instalatorów", nie ma telemetrii.
"""

import os
import sys
import threading
import queue
import subprocess
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import yt_dlp
import imageio_ffmpeg

from theme import apply_theme, style_text_widget

APP_TITLE = "YouTrak"
DEFAULT_OUTPUT_DIR = str(Path.home() / "Music" / "YouTrak")
ICON_PATH = Path(__file__).resolve().parent / "assets" / "icon.ico"
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "icon.png"


def get_ffmpeg_path() -> str:
    """Zwraca ścieżkę do binarki ffmpeg dostarczonej przez imageio-ffmpeg."""
    return imageio_ffmpeg.get_ffmpeg_exe()


class DownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("680x560")
        self.root.minsize(580, 460)
        apply_theme(self.root)
        self._set_window_icon()

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.output_dir = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.url_var = tk.StringVar()
        self.quality_var = tk.StringVar(value="320")
        self.playlist_var = tk.BooleanVar(value=False)
        self.is_downloading = False

        self._build_ui()
        self.root.after(150, self._poll_log_queue)

    # ------------------------------------------------------------------ UI

    def _set_window_icon(self):
        if ICON_PATH.exists():
            try:
                self.root.iconbitmap(default=str(ICON_PATH))
            except tk.TclError:
                pass

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)

        # -------------------------------------------------------- nagłówek
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 18))

        if LOGO_PATH.exists():
            self._logo_image = tk.PhotoImage(file=str(LOGO_PATH)).subsample(12, 12)
            ttk.Label(header, image=self._logo_image).pack(side="left", padx=(0, 12))

        title_box = ttk.Frame(header)
        title_box.pack(side="left")
        ttk.Label(title_box, text="YouTrak", style="Brand.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text="Twoja prywatna kolekcja muzyki, zapisana lokalnie",
            style="Muted.TLabel",
        ).pack(anchor="w")

        # ------------------------------------------------------------ link
        ttk.Label(outer, text="LINK DO YOUTUBE", style="Section.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        entry = ttk.Entry(outer, textvariable=self.url_var)
        entry.pack(fill="x", ipady=4)
        entry.focus_set()

        # --------------------------------------------------------- opcje
        options = ttk.Frame(outer)
        options.pack(fill="x", pady=(16, 0))
        options.columnconfigure(0, weight=1)

        ttk.Label(options, text="FOLDER DOCELOWY", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Entry(options, textvariable=self.output_dir).grid(
            row=1, column=0, sticky="ew", ipady=4, padx=(0, 8)
        )
        ttk.Button(options, text="Wybierz...", command=self._choose_dir).grid(
            row=1, column=1
        )

        row2 = ttk.Frame(outer)
        row2.pack(fill="x", pady=(16, 0))

        quality_box_wrap = ttk.Frame(row2)
        quality_box_wrap.pack(side="left")
        ttk.Label(quality_box_wrap, text="JAKOŚĆ MP3", style="Section.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        quality_box = ttk.Combobox(
            quality_box_wrap,
            textvariable=self.quality_var,
            values=["128", "192", "256", "320"],
            width=6,
            state="readonly",
        )
        quality_box.pack(anchor="w")

        ttk.Checkbutton(
            row2,
            text="Pobierz całą playlistę / album",
            variable=self.playlist_var,
        ).pack(side="left", padx=(24, 0), pady=(18, 0))

        # ---------------------------------------------------- pobieranie
        action_row = ttk.Frame(outer)
        action_row.pack(fill="x", pady=(22, 0))
        self.download_btn = ttk.Button(
            action_row,
            text="Pobierz jako MP3",
            style="Accent.TButton",
            command=self._on_download_click,
        )
        self.download_btn.pack(side="left")
        ttk.Button(
            action_row, text="Otwórz folder z muzyką", command=self._open_output_dir
        ).pack(side="left", padx=(10, 0))

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(16, 0))

        # ------------------------------------------------------------- log
        ttk.Label(outer, text="DZIENNIK", style="Section.TLabel").pack(
            anchor="w", pady=(18, 4)
        )
        log_card = ttk.Frame(outer, style="Card.TFrame")
        log_card.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_card, height=10, state="disabled", wrap="word")
        style_text_widget(self.log_text)
        self.log_text.pack(fill="both", expand=True, padx=1, pady=1)

    def _choose_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.output_dir.get() or str(Path.home()))
        if chosen:
            self.output_dir.set(chosen)

    def _open_output_dir(self):
        path = Path(self.output_dir.get())
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)  # Windows

    # ------------------------------------------------------------- logging

    def log(self, message: str):
        self.log_queue.put(message)

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(150, self._poll_log_queue)

    # ------------------------------------------------------------ download

    def _on_download_click(self):
        if self.is_downloading:
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(APP_TITLE, "Wklej najpierw link do YouTube.")
            return

        out_dir = Path(self.output_dir.get())
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Nie można utworzyć folderu:\n{exc}")
            return

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="Pobieranie...")
        self.progress["value"] = 0
        threading.Thread(target=self._download_worker, args=(url, out_dir), daemon=True).start()

    def _progress_hook(self, d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                pct = downloaded / total * 100
                self.root.after(0, lambda: self.progress.configure(value=pct))
        elif d.get("status") == "finished":
            self.root.after(0, lambda: self.progress.configure(value=100))
            self.log("Pobrano dźwięk, trwa konwersja do MP3...")

    def _download_worker(self, url: str, out_dir: Path):
        ffmpeg_path = get_ffmpeg_path()

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(out_dir / "%(title)s.%(ext)s"),
            "ffmpeg_location": ffmpeg_path,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": self.quality_var.get(),
                },
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail"},
            ],
            "writethumbnail": True,
            "noplaylist": not self.playlist_var.get(),
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
            "logger": _YdlLogger(self.log),
        }

        try:
            self.log(f"Start: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.log("Gotowe! Plik(i) MP3 zapisane w: " + str(out_dir))
        except Exception as exc:  # noqa: BLE001 - pokazujemy dowolny błąd użytkownikowi
            self.log(f"BŁĄD: {exc}")
            self.root.after(0, lambda: messagebox.showerror(APP_TITLE, str(exc)))
        finally:
            self.is_downloading = False
            self.root.after(
                0,
                lambda: self.download_btn.configure(state="normal", text="Pobierz jako MP3"),
            )


class _YdlLogger:
    """Przekierowuje logi yt-dlp do okna aplikacji (tylko ostrzeżenia/błędy)."""

    def __init__(self, log_fn):
        self._log = log_fn

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        self._log(f"Ostrzeżenie: {msg}")

    def error(self, msg):
        self._log(f"Błąd: {msg}")


def main():
    root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
