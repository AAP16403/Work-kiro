import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageGrab, ImageFilter, ImageTk, ImageOps, ImageDraw
import pytesseract
import time
import sys
import gc
import threading
import json
import os
import shutil
import tempfile
import subprocess

try:
    import pystray  # optional: enables system tray support
except Exception:
    pystray = None

# --- Path handling for exe distribution ---
def get_base_dir():
    """Get base directory whether running as script or exe."""
    if getattr(sys, 'frozen', False):
        # Running as exe
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def find_tesseract():
    """Auto-detect Tesseract installation."""
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"D:\tesseract\tesseract.exe",
        os.path.join(get_base_dir(), 'tesseract.exe'),
        os.path.join(get_base_dir(), 'tesseract-ocr', 'tesseract.exe')
    ]

    # Also check PATH environment variable
    try:
        result = subprocess.run(['where', 'tesseract.exe'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            path = result.stdout.strip().split('\n')[0]
            if os.path.exists(path):
                return path
    except Exception:
        pass

    # Check possible paths
    for path in possible_paths:
        if os.path.exists(path):
            return path

    # Default if nothing found
    return possible_paths[0]

# --- Defaults / config persistence ---
BASE_DIR = get_base_dir()
CONFIG_PATH = os.path.join(BASE_DIR, 'psg_config.json')
FALLBACK_CONFIG_DIR = os.path.expandvars(r'%APPDATA%\PrivacyScreenGuard')
FALLBACK_CONFIG_PATH = os.path.join(FALLBACK_CONFIG_DIR, 'psg_config.json')
DEFAULT_SETTINGS = {
    "sensitive_keywords": [
        "porn", "brazzer", "xxx", "milf", "gonzo", "allsex", "masturbation", "lesbian"
    ],
    "check_interval": 2.0,
    "cooldown": 5.0,
    "blur_radius": 25,
    "screenshot_scale": 1.0,
    "force_gc_interval": 5,
    "tesseract_cmd": find_tesseract(),
    "fade_overlay": True,
    "overlay_alpha": 0.98,
    "overlay_fade_ms": 300,
    "overlay_fade_steps": 10,
    "ocr_lang": "eng",
    "ocr_psm": 6,
    "ocr_oem": 3,
    "cleanup_enabled": True,
    "cleanup_interval_hours": 24,
    "cleanup_temp_files": True,
    "cleanup_cache": True,
    "start_minimized": False,
    "minimize_to_tray": True,
}

def load_settings():
    try:
        config_to_read = None
        if os.path.exists(CONFIG_PATH):
            config_to_read = CONFIG_PATH
        elif os.path.exists(FALLBACK_CONFIG_PATH):
            config_to_read = FALLBACK_CONFIG_PATH

        if config_to_read:
            with open(config_to_read, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # merge defaults
            settings = DEFAULT_SETTINGS.copy()
            settings.update(data)
            # Re-verify tesseract path on load
            if not os.path.exists(settings.get('tesseract_cmd', '')):
                settings['tesseract_cmd'] = find_tesseract()
            return settings
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONFIG_PATH) or '.', exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Could not save settings: {e}")
        # Try fallback location in user appdata
        try:
            os.makedirs(FALLBACK_CONFIG_DIR, exist_ok=True)
            with open(FALLBACK_CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            print(f'Saved settings to fallback location: {FALLBACK_CONFIG_PATH}')
        except Exception as e2:
            print(f'Fallback save also failed: {e2}')

def cleanup_temp_files():
    """Clean up temporary files and cache."""
    try:
        temp_dir = tempfile.gettempdir()
        removed_count = 0
        # Look for pytesseract or PIL temporary files
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                if 'pil' in filename.lower() or 'tess' in filename.lower() or 'ocr' in filename.lower():
                    fpath = os.path.join(temp_dir, filename)
                    try:
                        if os.path.isfile(fpath):
                            os.remove(fpath)
                            removed_count += 1
                        elif os.path.isdir(fpath):
                            shutil.rmtree(fpath)
                            removed_count += 1
                    except Exception:
                        pass
        return removed_count
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return 0


class BlurOverlay:
    def __init__(self, parent, image, fade=True, alpha_target=0.98, fade_ms=300, fade_steps=10, on_close=None):
        # image is a PIL Image sized to the screen
        self.root = tk.Toplevel(parent)
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        try:
            self.root.attributes('-fullscreen', True)
        except Exception:
            pass
        self.root.config(cursor='none')
        self._on_close = on_close
        self._alpha_target = float(alpha_target)
        self._fade_steps = max(1, int(fade_steps))
        self._fade_ms = max(1, int(fade_ms))
        self._fade_step = 0

        self.photo = ImageTk.PhotoImage(image)
        self.label = tk.Label(self.root, image=self.photo)
        self.label.pack(fill='both', expand=True)

        self.root.bind('<Button-1>', self.close)
        self.root.bind('<Key>', self.close)

        if fade:
            try:
                self.root.attributes('-alpha', 0.0)
                self._fade_in()
            except Exception:
                pass
        else:
            try:
                self.root.attributes('-alpha', self._alpha_target)
            except Exception:
                pass

    def _fade_in(self):
        try:
            self._fade_step += 1
            a = (self._alpha_target / self._fade_steps) * self._fade_step
            self.root.attributes('-alpha', min(self._alpha_target, a))
            if self._fade_step < self._fade_steps:
                delay = int(self._fade_ms / self._fade_steps)
                self.root.after(max(1, delay), self._fade_in)
        except Exception:
            pass

    def close(self, event=None):
        try:
            self.label.destroy()
            self.root.destroy()
            if callable(self._on_close):
                self._on_close()
        finally:
            gc.collect()


class ScreenChecker(threading.Thread):
    def __init__(self, settings, on_detect=None):
        super().__init__(daemon=True)
        self.settings = settings
        self.on_detect = on_detect
        self.on_status = None
        self._running = threading.Event()
        self._running.clear()
        self.check_count = 0
        self.last_cleanup_time = time.time()

    def start_checking(self):
        self._running.set()
        if not self.is_alive():
            self.start()

    def stop_checking(self):
        self._running.clear()

    def run(self):
        if sys.platform == 'win32' and self.settings.get('tesseract_cmd'):
            pytesseract.pytesseract.tesseract_cmd = self.settings['tesseract_cmd']

        while True:
            if not self._running.is_set():
                # notify UI that we're idle
                try:
                    if callable(self.on_status):
                        self.on_status(False, self.check_count)
                except Exception:
                    pass
                time.sleep(0.1)
                continue

            self.check_count += 1
            # notify UI that we're active
            try:
                if callable(self.on_status):
                    self.on_status(True, self.check_count)
            except Exception:
                pass
            try:
                img = ImageGrab.grab()

                scale = max(0.25, float(self.settings.get('screenshot_scale', 1.0)))
                if scale != 1.0:
                    new_size = (int(img.width * scale), int(img.height * scale))
                    img_small = img.resize(new_size, Image.LANCZOS)
                else:
                    img_small = img

                # Improve OCR contrast
                img_proc = ImageOps.grayscale(img_small)
                # Let pytesseract run (timeout may not be available in all versions)
                try:
                    lang = self.settings.get('ocr_lang', 'eng') or 'eng'
                    psm = int(self.settings.get('ocr_psm', 6))
                    oem = int(self.settings.get('ocr_oem', 3))
                    config = f'--oem {oem} --psm {psm}'
                    text = pytesseract.image_to_string(img_proc, lang=lang, config=config).lower()
                except TypeError:
                    # Older pytesseract versions may not accept timeout kw
                    text = pytesseract.image_to_string(img_proc).lower()

                for kw in self.settings.get('sensitive_keywords', []):
                    if kw.strip().lower() and kw.lower() in text:
                        print(f"Detected keyword: {kw}")
                        if callable(self.on_detect):
                            self.on_detect(img, self.settings)
                        # cooldown
                        time.sleep(float(self.settings.get('cooldown', 5.0)))
                        break

            except pytesseract.TesseractNotFoundError:
                print('Tesseract not found. Update path in settings.')
                self._running.clear()
            except Exception as e:
                print(f'Error during check: {e}')
            finally:
                if self.check_count % int(self.settings.get('force_gc_interval', 5)) == 0:
                    gc.collect()

                # Periodic cleanup if enabled
                if self.settings.get('cleanup_enabled', True):
                    cleanup_interval_hours = float(self.settings.get('cleanup_interval_hours', 24))
                    cleanup_interval_secs = cleanup_interval_hours * 3600
                    if time.time() - self.last_cleanup_time > cleanup_interval_secs:
                        if self.settings.get('cleanup_temp_files', True) or self.settings.get('cleanup_cache', True):
                            removed = cleanup_temp_files()
                            print(f'[Cleanup] Removed {removed} temporary files.')
                            self.last_cleanup_time = time.time()

                time.sleep(float(self.settings.get('check_interval', 2.0)))


def _make_tray_image(size=64):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((10, 8, size - 10, size - 10), radius=12, fill=(28, 122, 56, 255))
    draw.text((size // 2 - 12, size // 2 - 14), "PS", fill=(255, 255, 255, 255))
    return img


class TrayController:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self._thread = None

    @property
    def available(self):
        return pystray is not None

    def start(self):
        if not self.available:
            return False
        if self.icon is not None:
            return True

        def _ui(fn, *args):
            try:
                self.app.root.after(0, lambda: fn(*args))
            except Exception:
                pass

        menu = pystray.Menu(
            pystray.MenuItem('Show', lambda: _ui(self.app.show_window)),
            pystray.MenuItem('Hide', lambda: _ui(self.app.hide_window)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Start', lambda: _ui(self.app.start)),
            pystray.MenuItem('Stop', lambda: _ui(self.app.stop)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', lambda: _ui(self.app.quit_app)),
        )

        self.icon = pystray.Icon('PrivacyScreenGuard', _make_tray_image(), 'Privacy Screen Guard', menu)
        self._thread = threading.Thread(target=self.icon.run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        try:
            if self.icon is not None:
                self.icon.stop()
        except Exception:
            pass
        finally:
            self.icon = None
            self._thread = None


class App:
    def __init__(self, root):
        self.root = root
        self.root.title('Privacy Screen Guard')
        self.root.minsize(560, 540)
        self.root.resizable(True, True)
        self.settings = load_settings()

        self.style = ttk.Style(self.root)
        try:
            if 'clam' in self.style.theme_names():
                self.style.theme_use('clam')
        except Exception:
            pass
        try:
            self.style.configure('TButton', padding=(10, 4))
            self.style.configure('TLabel', padding=(0, 2))
        except Exception:
            pass

        self._overlay_active = False
        self._overlay = None
        self._ignore_unmap = False
        self.tray = TrayController(self)

        # First-run setup check
        self._check_first_run()

        self.checker = ScreenChecker(self.settings, on_detect=self._on_detect_threadsafe)

        self._build_ui()
        self._set_initial_geometry()

        self.root.bind('<Unmap>', self._on_unmap)
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    def _check_first_run(self):
        """Check and alert on first run if Tesseract is not found."""
        tess_path = self.settings.get('tesseract_cmd', '')
        if not tess_path or not os.path.exists(tess_path):
            messagebox.showwarning(
                'Tesseract Not Found',
                'Tesseract-OCR is not installed or not found.\n'
                'Please install it from: https://github.com/UB-Mannheim/tesseract/wiki\n'
                'Then update the Tesseract path in Settings.'
            )
            print('[WARNING] Tesseract not found. Please install and configure the path.')

    def _set_initial_geometry(self):
        try:
            self.root.update_idletasks()
            req_w = self.root.winfo_reqwidth()
            req_h = self.root.winfo_reqheight()
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()

            w = min(max(req_w + 40, 640), int(screen_w * 0.8))
            h = min(max(req_h + 40, 620), int(screen_h * 0.85))
            x = max(0, int((screen_w - w) / 2))
            y = max(0, int((screen_h - h) / 3))
            self.root.geometry(f'{w}x{h}+{x}+{y}')
        except Exception:
            pass

    def _on_unmap(self, event=None):
        if self._ignore_unmap:
            return
        try:
            if event is not None and getattr(event, 'widget', None) is not self.root:
                return
            if self.root.state() == 'iconic' and self.settings.get('minimize_to_tray', True):
                if self.tray.available and self.tray.start():
                    self._ignore_unmap = True
                    self.root.after(1, self.hide_window)
                    self.root.after(50, lambda: setattr(self, '_ignore_unmap', False))
        except Exception:
            pass

    def _on_close(self):
        if self.settings.get('minimize_to_tray', True) and self.tray.available:
            if self.tray.start():
                self.hide_window()
            else:
                self.quit_app()
        else:
            self.quit_app()

    def hide_window(self):
        try:
            self.root.withdraw()
        except Exception:
            pass

    def show_window(self):
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

    def quit_app(self):
        try:
            try:
                self.checker.stop_checking()
            except Exception:
                pass
            self.tray.stop()
        except Exception:
            pass
        try:
            self.root.quit()
        finally:
            try:
                self.root.destroy()
            except Exception:
                pass

    def _on_detect_threadsafe(self, screenshot_image, settings):
        try:
            self.root.after(0, lambda: self._handle_detect(screenshot_image, settings))
        except Exception:
            pass

    def _handle_detect(self, screenshot_image, settings):
        if self._overlay_active:
            return
        self.show_blur(screenshot_image, settings)

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=12)
        container.grid(row=0, column=0, sticky='nsew')
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        notebook = ttk.Notebook(container)
        notebook.grid(row=0, column=0, sticky='nsew')
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        tab_main = ttk.Frame(notebook, padding=12)
        tab_settings = ttk.Frame(notebook, padding=12)
        notebook.add(tab_main, text='Main')
        notebook.add(tab_settings, text='Settings')

        # --- Main tab ---
        tab_main.grid_columnconfigure(0, weight=1)

        btn_row = ttk.Frame(tab_main)
        btn_row.grid(row=0, column=0, sticky='w', pady=(0, 10))
        self.start_btn = ttk.Button(btn_row, text='Start', command=self.start)
        self.start_btn.grid(row=0, column=0, sticky='w')
        self.stop_btn = ttk.Button(btn_row, text='Stop', command=self.stop)
        self.stop_btn.grid(row=0, column=1, sticky='w', padx=6)
        self.stop_btn.state(['disabled'])
        self.test_btn = ttk.Button(btn_row, text='Test Blur', command=self._test_blur)
        self.test_btn.grid(row=0, column=2, sticky='w')

        status_frame = ttk.LabelFrame(tab_main, text='Status')
        status_frame.grid(row=1, column=0, sticky='ew')
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_columnconfigure(1, weight=1)
        self.status_var = tk.StringVar(value='Idle')
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=0, sticky='w', padx=8, pady=6)
        self.last_check_var = tk.StringVar(value='Checks: 0')
        self.last_check_label = ttk.Label(status_frame, textvariable=self.last_check_var)
        self.last_check_label.grid(row=0, column=1, sticky='e', padx=8, pady=6)

        actions = ttk.Frame(tab_main)
        actions.grid(row=2, column=0, sticky='w', pady=(10, 0))
        ttk.Button(actions, text='Save Settings', command=self.save).grid(row=0, column=0, sticky='w')
        ttk.Button(actions, text='Clean Now', command=self.cleanup_now).grid(row=0, column=1, sticky='w', padx=6)
        if self.tray.available:
            ttk.Button(actions, text='Show Tray Icon', command=self.tray.start).grid(row=0, column=2, sticky='w', padx=6)

        info_text = f'Config: {CONFIG_PATH}\nFallback: {FALLBACK_CONFIG_PATH}\nBase Dir: {BASE_DIR}'
        ttk.Label(tab_main, text=info_text, font=('monospace', 8), foreground='gray').grid(row=3, column=0, sticky='w', pady=(12, 0))

        # --- Settings tab ---
        tab_settings.grid_rowconfigure(0, weight=1)
        tab_settings.grid_columnconfigure(0, weight=1)

        settings_frame = ttk.LabelFrame(tab_settings, text='Settings', padding=10)
        settings_frame.grid(row=0, column=0, sticky='nsew')
        settings_frame.grid_columnconfigure(1, weight=1)
        settings_frame.grid_rowconfigure(5, weight=1)  # keywords box expands

        ttk.Label(settings_frame, text='Check interval (s):').grid(row=0, column=0, sticky='w')
        self.check_interval_var = tk.DoubleVar(value=self.settings.get('check_interval', 2.0))
        ttk.Spinbox(settings_frame, from_=0.5, to=60, increment=0.5, textvariable=self.check_interval_var, width=8).grid(row=0, column=1, sticky='w')

        ttk.Label(settings_frame, text='Cooldown (s):').grid(row=1, column=0, sticky='w')
        self.cooldown_var = tk.DoubleVar(value=self.settings.get('cooldown', 5.0))
        ttk.Spinbox(settings_frame, from_=0, to=60, increment=0.5, textvariable=self.cooldown_var, width=8).grid(row=1, column=1, sticky='w')

        ttk.Label(settings_frame, text='Blur radius:').grid(row=2, column=0, sticky='w')
        self.blur_var = tk.IntVar(value=self.settings.get('blur_radius', 25))
        ttk.Scale(settings_frame, from_=1, to=60, orient='horizontal', variable=self.blur_var).grid(row=2, column=1, sticky='ew')

        ttk.Label(settings_frame, text='Screenshot scale:').grid(row=3, column=0, sticky='w')
        self.scale_var = tk.DoubleVar(value=self.settings.get('screenshot_scale', 1.0))
        ttk.Scale(settings_frame, from_=0.25, to=1.0, orient='horizontal', variable=self.scale_var).grid(row=3, column=1, sticky='ew')

        ttk.Label(settings_frame, text='Sensitive keywords (comma-separated):').grid(row=4, column=0, columnspan=2, sticky='w', pady=(10, 0))
        kw_frame = ttk.Frame(settings_frame)
        kw_frame.grid(row=5, column=0, columnspan=2, sticky='nsew')
        kw_frame.grid_rowconfigure(0, weight=1)
        kw_frame.grid_columnconfigure(0, weight=1)
        self.keywords_text = tk.Text(kw_frame, height=6, wrap='word')
        kw_scroll = ttk.Scrollbar(kw_frame, orient='vertical', command=self.keywords_text.yview)
        self.keywords_text.configure(yscrollcommand=kw_scroll.set)
        self.keywords_text.grid(row=0, column=0, sticky='nsew')
        kw_scroll.grid(row=0, column=1, sticky='ns')
        self.keywords_text.insert('1.0', ', '.join(self.settings.get('sensitive_keywords', [])))

        ttk.Label(settings_frame, text='Tesseract path:').grid(row=6, column=0, sticky='w', pady=(10, 0))
        self.tess_var = tk.StringVar(value=self.settings.get('tesseract_cmd', ''))
        ttk.Entry(settings_frame, textvariable=self.tess_var).grid(row=6, column=1, sticky='ew', pady=(10, 0))

        ttk.Separator(settings_frame, orient='horizontal').grid(row=7, column=0, columnspan=2, sticky='ew', pady=10)

        ttk.Label(settings_frame, text='Cleanup interval (hours):').grid(row=8, column=0, sticky='w')
        self.cleanup_interval_var = tk.DoubleVar(value=self.settings.get('cleanup_interval_hours', 24))
        ttk.Spinbox(settings_frame, from_=1, to=720, increment=1, textvariable=self.cleanup_interval_var, width=8).grid(row=8, column=1, sticky='w')

        self.cleanup_enabled_var = tk.BooleanVar(value=self.settings.get('cleanup_enabled', True))
        ttk.Checkbutton(settings_frame, text='Auto cleanup enabled', variable=self.cleanup_enabled_var).grid(row=9, column=0, columnspan=2, sticky='w')

        self.cleanup_temp_var = tk.BooleanVar(value=self.settings.get('cleanup_temp_files', True))
        ttk.Checkbutton(settings_frame, text='Cleanup temp files', variable=self.cleanup_temp_var).grid(row=10, column=0, columnspan=2, sticky='w')

        self.cleanup_cache_var = tk.BooleanVar(value=self.settings.get('cleanup_cache', True))
        ttk.Checkbutton(settings_frame, text='Cleanup cache', variable=self.cleanup_cache_var).grid(row=11, column=0, columnspan=2, sticky='w')

        ttk.Separator(settings_frame, orient='horizontal').grid(row=12, column=0, columnspan=2, sticky='ew', pady=10)

        ttk.Label(settings_frame, text='OCR language:').grid(row=13, column=0, sticky='w')
        self.ocr_lang_var = tk.StringVar(value=self.settings.get('ocr_lang', 'eng'))
        ttk.Entry(settings_frame, textvariable=self.ocr_lang_var, width=12).grid(row=13, column=1, sticky='w')

        ttk.Label(settings_frame, text='OCR PSM:').grid(row=14, column=0, sticky='w')
        self.ocr_psm_var = tk.IntVar(value=int(self.settings.get('ocr_psm', 6)))
        ttk.Spinbox(settings_frame, from_=3, to=13, increment=1, textvariable=self.ocr_psm_var, width=8).grid(row=14, column=1, sticky='w')

        ttk.Label(settings_frame, text='OCR OEM:').grid(row=15, column=0, sticky='w')
        self.ocr_oem_var = tk.IntVar(value=int(self.settings.get('ocr_oem', 3)))
        ttk.Spinbox(settings_frame, from_=0, to=3, increment=1, textvariable=self.ocr_oem_var, width=8).grid(row=15, column=1, sticky='w')

        ttk.Separator(settings_frame, orient='horizontal').grid(row=16, column=0, columnspan=2, sticky='ew', pady=10)

        self.start_minimized_var = tk.BooleanVar(value=self.settings.get('start_minimized', False))
        ttk.Checkbutton(settings_frame, text='Run minimized on start', variable=self.start_minimized_var).grid(row=17, column=0, columnspan=2, sticky='w')

        self.minimize_to_tray_var = tk.BooleanVar(value=self.settings.get('minimize_to_tray', True))
        tray_text = 'Minimize to system tray' if self.tray.available else 'Minimize to system tray (requires pystray)'
        ttk.Checkbutton(settings_frame, text=tray_text, variable=self.minimize_to_tray_var).grid(row=18, column=0, columnspan=2, sticky='w')

        self.fade_overlay_var = tk.BooleanVar(value=self.settings.get('fade_overlay', True))
        ttk.Checkbutton(settings_frame, text='Fade overlay', variable=self.fade_overlay_var).grid(row=19, column=0, columnspan=2, sticky='w', pady=(10, 0))

        ttk.Label(settings_frame, text='Overlay alpha:').grid(row=20, column=0, sticky='w')
        self.overlay_alpha_var = tk.DoubleVar(value=float(self.settings.get('overlay_alpha', 0.98)))
        ttk.Scale(settings_frame, from_=0.2, to=1.0, orient='horizontal', variable=self.overlay_alpha_var).grid(row=20, column=1, sticky='ew')

        ttk.Label(settings_frame, text='Fade duration (ms):').grid(row=21, column=0, sticky='w')
        self.overlay_fade_ms_var = tk.IntVar(value=int(self.settings.get('overlay_fade_ms', 300)))
        ttk.Spinbox(settings_frame, from_=0, to=5000, increment=50, textvariable=self.overlay_fade_ms_var, width=10).grid(row=21, column=1, sticky='w')

        ttk.Label(settings_frame, text='Fade steps:').grid(row=22, column=0, sticky='w')
        self.overlay_fade_steps_var = tk.IntVar(value=int(self.settings.get('overlay_fade_steps', 10)))
        ttk.Spinbox(settings_frame, from_=1, to=60, increment=1, textvariable=self.overlay_fade_steps_var, width=10).grid(row=22, column=1, sticky='w')

    def start(self):
        self._update_settings_from_ui()
        self.checker.settings = self.settings
        # connect status callback
        self.checker.on_status = lambda running, count: self.root.after(1, self.update_status, running, count)
        self.checker.start_checking()
        self.start_btn.state(['disabled'])
        self.stop_btn.state(['!disabled'])
        print('Checking started')

    def stop(self):
        self.checker.stop_checking()
        # update UI
        self.start_btn.state(['!disabled'])
        self.stop_btn.state(['disabled'])
        self.root.after(1, self.update_status, False, self.checker.check_count)
        print('Checking stopped')

    def save(self):
        self._update_settings_from_ui()
        save_settings(self.settings)
        messagebox.showinfo('Saved', 'Settings saved to psg_config.json')

    def _update_settings_from_ui(self):
        try:
            self.settings['check_interval'] = float(self.check_interval_var.get())
            self.settings['cooldown'] = float(self.cooldown_var.get())
            self.settings['blur_radius'] = int(self.blur_var.get())
            self.settings['screenshot_scale'] = float(self.scale_var.get())
            kws = [k.strip() for k in self.keywords_text.get('1.0', 'end').split(',') if k.strip()]
            self.settings['sensitive_keywords'] = kws
            self.settings['tesseract_cmd'] = self.tess_var.get().strip()

            self.settings['cleanup_enabled'] = self.cleanup_enabled_var.get()
            self.settings['cleanup_interval_hours'] = float(self.cleanup_interval_var.get())
            self.settings['cleanup_temp_files'] = self.cleanup_temp_var.get()
            self.settings['cleanup_cache'] = self.cleanup_cache_var.get()

            self.settings['ocr_lang'] = self.ocr_lang_var.get().strip() or 'eng'
            self.settings['ocr_psm'] = int(self.ocr_psm_var.get())
            self.settings['ocr_oem'] = int(self.ocr_oem_var.get())

            self.settings['start_minimized'] = self.start_minimized_var.get()
            self.settings['minimize_to_tray'] = self.minimize_to_tray_var.get()

            self.settings['fade_overlay'] = self.fade_overlay_var.get()
            self.settings['overlay_alpha'] = float(self.overlay_alpha_var.get())
            self.settings['overlay_fade_ms'] = int(self.overlay_fade_ms_var.get())
            self.settings['overlay_fade_steps'] = int(self.overlay_fade_steps_var.get())
        except Exception as e:
            messagebox.showerror('Invalid settings', f'Please check your settings values.\n\n{e}')

    def cleanup_now(self):
        """Manually trigger cleanup."""
        removed = cleanup_temp_files()
        self.checker.last_cleanup_time = time.time()
        messagebox.showinfo('Cleanup', f'Cleanup complete. Removed {removed} temporary files.')
        print(f'Manual cleanup: removed {removed} files.')

    def update_status(self, running, check_count):
        # Update status text and checks count in the UI thread
        try:
            if running:
                self.status_var.set('Running')
                self.status_label.configure(foreground='green')
            else:
                self.status_var.set('Idle')
                self.status_label.configure(foreground='red')
            self.last_check_var.set(f'Checks: {check_count}')
        except Exception:
            pass

    def show_blur(self, screenshot_image, settings):
        try:
            radius = int(settings.get('blur_radius', 25))
            # Apply blur to full-size screenshot for visual quality
            blurred = screenshot_image.filter(ImageFilter.GaussianBlur(radius))
            self._overlay_active = True
            self._overlay = BlurOverlay(
                self.root,
                blurred,
                fade=settings.get('fade_overlay', True),
                alpha_target=settings.get('overlay_alpha', 0.98),
                fade_ms=settings.get('overlay_fade_ms', 300),
                fade_steps=settings.get('overlay_fade_steps', 10),
                on_close=self._on_overlay_closed,
            )
            # Wait until the overlay is dismissed; event loop handles it
            # Update last check label when detection occurs
            try:
                self.root.after(1, self.update_status, True, self.checker.check_count)
            except Exception:
                pass
        except Exception as e:
            print(f'Could not show blur: {e}')
            self._overlay_active = False
            self._overlay = None

    def _on_overlay_closed(self):
        self._overlay_active = False
        self._overlay = None

    def _test_blur(self):
        try:
            img = ImageGrab.grab()
            self.show_blur(img, self.settings)
        except Exception as e:
            messagebox.showerror('Error', f'Failed to capture screen: {e}')


def main():
    root = tk.Tk()
    app = App(root)
    if app.settings.get('start_minimized', False):
        if app.settings.get('minimize_to_tray', True) and app.tray.available and app.tray.start():
            app.hide_window()
        else:
            root.iconify()
    root.mainloop()


if __name__ == '__main__':
    main()
