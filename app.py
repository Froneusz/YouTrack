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

import json
import os
import sys
import threading
import time
import queue
import subprocess
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import yt_dlp
from yt_dlp.extractor.youtube import YoutubeIE
from yt_dlp.postprocessor.common import PostProcessor
import imageio_ffmpeg

from theme import apply_theme, style_text_widget

APP_TITLE = "YouTrak"
DEFAULT_OUTPUT_DIR = str(Path.home() / "Music" / "YouTrak")
ICON_PATH = Path(__file__).resolve().parent / "assets" / "icon.ico"
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "icon.png"
CONFIG_PATH = Path(os.environ.get("APPDATA", str(Path.home()))) / "YouTrak" / "config.json"
COOKIE_BROWSERS = ["brak", "firefox", "chrome", "edge", "brave", "opera", "vivaldi"]
# Kolejne zestawy klientów YouTube próbowane, gdy YouTube blokuje pobieranie (weryfikacja "bot",
# HTTP 403 na strumieniu bez PO Tokena, brak formatów przez SABR). None = domyślny wybór yt-dlp.
# web_embedded (odtwarzacz osadzony) zwykle nie wymaga PO Tokena ani logowania.
FALLBACK_PLAYER_CLIENTS = [None, ["web_embedded"], ["tv", "web_safari"], ["mweb"]]
RETRYABLE_ERRORS = (
    "not a bot",
    "HTTP Error 403",
    "Requested format is not available",
    "page needs to be reloaded",
)

BOT_CHECK_HINT = (
    "YouTube zablokował anonimowe pobieranie z Twojego IP "
    "(weryfikacja \"nie jestem botem\").\n\n"
    "Rozwiązanie: wskaż plik cookies.txt wyeksportowany z przeglądarki, w której jesteś "
    "zalogowany do YouTube (np. rozszerzeniem \"Get cookies.txt LOCALLY\"), "
    "albo wybierz Firefoksa jako źródło cookies.\n\n"
    "Chrome/Edge na Windows szyfrują cookies (App-Bound Encryption) i blokują bazę, "
    "gdy są uruchomione - dlatego plik cookies.txt jest najpewniejszy."
)


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except OSError:
        pass


ARCHIVE_NAME = ".youtrak_archive.json"


class DownloadArchive:
    """Rejestr pobranych utworów w folderze docelowym: {video_id: {"title", "file"}}.

    Utwór uznajemy za pobrany, dopóki jego plik MP3 nadal istnieje - usunięcie pliku
    pozwala pobrać go ponownie.
    """

    def __init__(self, out_dir: Path):
        self.path = out_dir / ARCHIVE_NAME
        try:
            self.entries = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.entries = {}

    def find(self, video_id: str):
        entry = self.entries.get(video_id)
        if entry and Path(entry["file"]).is_file():
            return entry
        return None

    def add(self, video_id: str, title: str, file: str) -> None:
        self.entries[video_id] = {"title": title, "file": file}
        try:
            self.path.write_text(json.dumps(self.entries, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


class _ArchivePP(PostProcessor):
    """Po zapisaniu gotowego MP3 dopisuje utwór do archiwum."""

    def __init__(self, archive: DownloadArchive):
        super().__init__()
        self._archive = archive

    def run(self, info):
        self._archive.add(info["id"], info.get("title", info["id"]), info["filepath"])
        return [], info


def get_ffmpeg_path() -> str:
    """Zwraca ścieżkę do binarki ffmpeg dostarczonej przez imageio-ffmpeg."""
    return imageio_ffmpeg.get_ffmpeg_exe()


class DownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("680x640")
        self.root.minsize(580, 460)
        apply_theme(self.root)
        self._set_window_icon()

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.output_dir = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.url_var = tk.StringVar()
        self.quality_var = tk.StringVar(value="320")
        self.playlist_var = tk.BooleanVar(value=False)
        cfg = load_config()
        self.cookie_file_var = tk.StringVar(value=cfg.get("cookie_file", ""))
        self.cookie_browser_var = tk.StringVar(value=cfg.get("cookie_browser", "brak"))
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

        cookies = ttk.Frame(outer)
        cookies.pack(fill="x", pady=(16, 0))
        cookies.columnconfigure(0, weight=1)
        ttk.Label(
            cookies,
            text="COOKIES YOUTUBE (gdy YouTube żąda logowania)",
            style="Section.TLabel",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Entry(cookies, textvariable=self.cookie_file_var).grid(
            row=1, column=0, sticky="ew", ipady=4, padx=(0, 8)
        )
        ttk.Button(cookies, text="cookies.txt...", command=self._choose_cookie_file).grid(
            row=1, column=1, padx=(0, 8)
        )
        ttk.Combobox(
            cookies,
            textvariable=self.cookie_browser_var,
            values=COOKIE_BROWSERS,
            width=9,
            state="readonly",
        ).grid(row=1, column=2)

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

    def _choose_cookie_file(self):
        chosen = filedialog.askopenfilename(
            title="Wybierz plik cookies.txt (format Netscape)",
            filetypes=[("Cookies", "*.txt"), ("Wszystkie pliki", "*.*")],
        )
        if chosen:
            self.cookie_file_var.set(chosen)

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

        cookie_file = self.cookie_file_var.get().strip()
        if cookie_file and not Path(cookie_file).is_file():
            messagebox.showerror(APP_TITLE, f"Plik cookies nie istnieje:\n{cookie_file}")
            return
        save_config({"cookie_file": cookie_file, "cookie_browser": self.cookie_browser_var.get()})

        # szybkie sprawdzenie pojedynczego utworu bez łączenia się z YouTube
        video_id = YoutubeIE.get_temp_id(url)
        if video_id and not self.playlist_var.get():
            entry = DownloadArchive(out_dir).find(video_id)
            if entry:
                self.log(f"Pominięto - już pobrane: {entry['title']}")
                messagebox.showinfo(
                    APP_TITLE,
                    f"Ta piosenka jest już pobrana:\n\n{entry['title']}\n\n{entry['file']}",
                )
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
            # łagodniej dla limitów YouTube (HTTP 429), szczególnie przy playlistach
            "sleep_interval_requests": 1,
            "sleep_interval": 2,
            "max_sleep_interval": 5,
        }

        cookie_file = self.cookie_file_var.get().strip()
        cookie_browser = self.cookie_browser_var.get()
        if cookie_file:
            ydl_opts["cookiefile"] = cookie_file
        elif cookie_browser and cookie_browser != "brak":
            ydl_opts["cookiesfrombrowser"] = (cookie_browser, None, None, None)

        archive = DownloadArchive(out_dir)
        skipped: dict = {}
        downloaded: list = []

        def match_filter(info, *, incomplete=False):
            video_id = info.get("id")
            title = info.get("title") or video_id
            entry = archive.find(video_id) if video_id else None
            if entry is None and not incomplete and ydl_ref:
                # plik mógł zostać pobrany wcześniej, zanim istniało archiwum
                target = Path(ydl_ref[0].prepare_filename(info)).with_suffix(".mp3")
                if target.is_file():
                    archive.add(video_id, title, str(target))
                    entry = archive.find(video_id)
            if entry:
                if video_id not in skipped:
                    skipped[video_id] = entry
                    self.log(f"Pominięto - już pobrane: {entry['title']}")
                return f"{title} jest już pobrane"
            if not incomplete and video_id not in downloaded:
                downloaded.append(video_id)
            return None

        ydl_opts["match_filter"] = match_filter
        ydl_ref: list = []

        try:
            self.log(f"Start: {url}")
            for attempt, clients in enumerate(FALLBACK_PLAYER_CLIENTS):
                opts = dict(ydl_opts)
                if clients:
                    opts["extractor_args"] = {"youtube": {"player_client": clients}}
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl_ref[:] = [ydl]
                        ydl.add_post_processor(_ArchivePP(archive), when="after_move")
                        ydl.download([url])
                    break
                except yt_dlp.utils.DownloadError as exc:
                    if not any(e in str(exc) for e in RETRYABLE_ERRORS) or attempt == len(FALLBACK_PLAYER_CLIENTS) - 1:
                        raise
                    self.log(f"YouTube zablokował strumień - ponawiam z klientami: {', '.join(FALLBACK_PLAYER_CLIENTS[attempt + 1])}")
                    time.sleep(3)
            if skipped and not downloaded:
                info = (
                    "Ta piosenka jest już pobrana:\n\n{title}\n\n{file}".format(**next(iter(skipped.values())))
                    if len(skipped) == 1
                    else f"Wszystkie utwory ({len(skipped)}) są już pobrane."
                )
                self.log(info.split(":")[0] + " - nic nie pobrano.")
                self.root.after(0, lambda: messagebox.showinfo(APP_TITLE, info))
            else:
                if skipped:
                    self.log(f"Pominięto {len(skipped)} już pobranych utworów.")
                self.log("Gotowe! Plik(i) MP3 zapisane w: " + str(out_dir))
        except Exception as exc:  # noqa: BLE001 - pokazujemy dowolny błąd użytkownikowi
            msg = str(exc)
            if "not a bot" in msg:
                msg = BOT_CHECK_HINT
            elif "Could not copy Chrome cookie database" in msg or "decrypt" in msg:
                msg = (
                    "Nie udało się odczytać cookies z przeglądarki (zablokowana baza lub "
                    "App-Bound Encryption). Zamknij przeglądarkę albo użyj pliku cookies.txt."
                )
            self.log(f"BŁĄD: {msg}")
            self.root.after(0, lambda: messagebox.showerror(APP_TITLE, msg))
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
