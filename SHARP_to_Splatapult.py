"""
SHARP -> Splatapult  |  Single-image to 3D Gaussian Splat launcher
Accepts an image via command-line (Send To) or the built-in file picker.
"""

import sys
import os

# When frozen by PyInstaller the hook-_tkinter.py may bundle Tcl/Tk files from
# a wrong system installation (version mismatch).  We force TCL_LIBRARY and
# TK_LIBRARY to the copies we explicitly bundled via --add-data BEFORE tkinter
# is imported so the runtime picks up the correct version.
if getattr(sys, "frozen", False):
    _mp = sys._MEIPASS
    os.environ["TCL_LIBRARY"] = os.path.join(_mp, "tcl")
    os.environ["TK_LIBRARY"]  = os.path.join(_mp, "tk")

import json
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

# When frozen by PyInstaller, sys.executable is the .exe itself.
if getattr(sys, "frozen", False):
    EXE_DIR = os.path.dirname(sys.executable)
else:
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))

SPLATAPULT_DIR = os.path.join(EXE_DIR, "splatapult")
SPLATAPULT_EXE = os.path.join(SPLATAPULT_DIR, "build", "Release", "splatapult.exe")
CONDA_ENV_NAME = "sharp"
SETTINGS_PATH  = os.path.join(EXE_DIR, "sharp_to_splatapult_settings.json")

# ─────────────────────────────────────────────────────────────────────────────
# Conda / SHARP discovery
# ─────────────────────────────────────────────────────────────────────────────

def _conda_candidates():
    home  = os.path.expanduser("~")
    local = os.environ.get("LOCALAPPDATA", "")
    appdata = os.environ.get("APPDATA", "")
    program_data = os.environ.get("ProgramData", "C:\\ProgramData")

    search_roots = [home, local, appdata, program_data, "C:\\", "D:\\"]
    names = ["anaconda3", "miniconda3", "Anaconda3", "Miniconda3",
             "anaconda", "miniconda", "Anaconda", "Miniconda"]
    for root in search_roots:
        for name in names:
            yield os.path.join(root, name)

    # CONDA_PREFIX env vars set in activated shells
    for var in ("CONDA_PREFIX_1", "CONDA_PREFIX"):
        prefix = os.environ.get(var, "")
        if prefix:
            yield prefix
            yield os.path.dirname(prefix)

    # Ask conda itself — most reliable, works for any install location
    try:
        result = subprocess.run(
            ["conda", "info", "--base"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=10
        )
        base = result.stdout.strip()
        if base:
            yield base
    except Exception:
        pass

def find_conda_base():
    seen = set()
    for base in _conda_candidates():
        base = os.path.normpath(base)
        if base in seen or not os.path.isdir(base):
            continue
        seen.add(base)
        # Accept if condabin\conda.bat OR Scripts\conda.exe exists (handles all install types)
        if (os.path.exists(os.path.join(base, "condabin", "conda.bat")) or
                os.path.exists(os.path.join(base, "Scripts", "conda.exe")) or
                os.path.exists(os.path.join(base, "bin", "conda"))):
            return base
    return None

def find_sharp_exe():
    base = find_conda_base()
    if not base:
        return None
    path = os.path.join(base, "envs", CONDA_ENV_NAME, "Scripts", "sharp.exe")
    return path if os.path.exists(path) else None

def find_3dgsconverter_exe():
    base = find_conda_base()
    if not base:
        return None
    path = os.path.join(base, "envs", CONDA_ENV_NAME, "Scripts", "3dgsconverter.exe")
    return path if os.path.exists(path) else None

# ─────────────────────────────────────────────────────────────────────────────
# PLY transformation  (no PyTorch – bundled plyfile + numpy are enough)
# ─────────────────────────────────────────────────────────────────────────────

def transform_ply(input_path, output_path):
    """
    Strip Apple-specific metadata elements, and convert from SHARP's
    OpenCV convention (+Z forward, Y-down) to splatapult's OpenGL convention
    (-Z forward, Y-up).  Rotation quaternion Y/Z components are negated to
    match the axis flip.
    """
    from plyfile import PlyData, PlyElement
    d = PlyData.read(input_path)
    v = d["vertex"].data.copy()
    v["y"]     = -v["y"]
    v["z"]     = -v["z"]
    v["rot_2"] = -v["rot_2"]
    v["rot_3"] = -v["rot_3"]
    PlyData([PlyElement.describe(v, "vertex")], text=False).write(output_path)

def replace_file(src, dst):
    """Atomically replace dst with src, retrying on Windows lock errors."""
    for attempt in range(6):
        try:
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
            return
        except PermissionError:
            if attempt < 5:
                time.sleep(0.4)
            else:
                raise

# ─────────────────────────────────────────────────────────────────────────────
# Settings persistence
# ─────────────────────────────────────────────────────────────────────────────

def load_settings():
    try:
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(updates):
    """Merge *updates* into the on-disk settings file."""
    try:
        try:
            with open(SETTINGS_PATH, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}
        data.update(updates)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# GUI colours
# ─────────────────────────────────────────────────────────────────────────────

BG      = "#1e1e1e"
BG2     = "#2a2a2a"
BG3     = "#333333"
ACCENT  = "#4ec9b0"
FG      = "#d4d4d4"
FG_DIM  = "#6a6a6a"
ERR     = "#f44747"
OK_COL  = "#4ec9b0"
WARN    = "#dcdcaa"

# ─────────────────────────────────────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self, initial_file=""):
        super().__init__()
        self.title("SHARP → Splatapult")
        self.geometry("640x520")
        self.minsize(520, 440)
        self.configure(bg=BG)
        self.iconbitmap(default="")   # no icon crash if missing

        self._running  = False
        self._device   = tk.StringVar(value="cuda")
        _s = load_settings()
        self._export_fmt = tk.StringVar(value=_s.get("export_format", "spz"))
        self._export_fmt.trace_add("write",
            lambda *_: save_settings({"export_format": self._export_fmt.get()}))
        default_exe = _s.get("splatapult_exe", SPLATAPULT_EXE)
        self._splatapult_exe_var = tk.StringVar(value=default_exe)
        self._splatapult_exe_var.trace_add("write",
            lambda *_: save_settings({"splatapult_exe": self._splatapult_exe_var.get()}))

        self._build_ui()
        self._check_prereqs()

        if initial_file:
            self.after(300, lambda: self._start(initial_file))

    # ── Prereq check ─────────────────────────────────────────────────────────

    def _check_prereqs(self):
        ok = True
        exe = self._splatapult_exe_var.get()
        if os.path.exists(exe):
            self._log(f"✓  splatapult found", "ok")
        else:
            self._log(f"⚠  splatapult.exe not found: {exe}", "err")
            self._log("   Use the Browse button to locate splatapult.exe.", "dim")
            ok = False

        conda_base = find_conda_base()
        sharp = find_sharp_exe()
        if sharp:
            self._log(f"✓  SHARP conda env found  ({conda_base})", "ok")
        else:
            if conda_base:
                self._log(f"⚠  Conda found at {conda_base}", "warn")
                self._log(f"   but env '{CONDA_ENV_NAME}' is missing inside it.", "err")
                self._log("   Run  Setup_NewPC.bat  to create the sharp env.", "dim")
            else:
                self._log("⚠  Conda/Anaconda/Miniconda not found on this PC.", "err")
                self._log("   Install Anaconda or Miniconda, then run Setup_NewPC.bat.", "dim")
                self._log("   https://www.anaconda.com/download", "dim")
            ok = False

        if ok:
            self._log("Ready – select an image to begin.", "dim")

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header
        hdr = tk.Frame(self, bg="#111111", pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="SHARP  →  Splatapult",
                 font=("Segoe UI", 15, "bold"), fg=ACCENT, bg="#111111").pack()
        tk.Label(hdr, text="Convert any photo to a 3D Gaussian Splat and view it instantly",
                 font=("Segoe UI", 8), fg=FG_DIM, bg="#111111").pack()

        # ── Drop / select zone
        self._zone = tk.Frame(self, bg=BG3, cursor="hand2", pady=26)
        self._zone.pack(fill=tk.X, padx=20, pady=(14, 6))
        self._lbl_file = tk.Label(self._zone,
            text="▸  Click here – or use  Send To – to select a JPEG / PNG",
            font=("Segoe UI", 10), fg=FG_DIM, bg=BG3)
        self._lbl_file.pack()
        for w in (self._zone, self._lbl_file):
            w.bind("<Button-1>", lambda _: self._browse())
            w.bind("<Enter>",    lambda _: (self._zone.config(bg="#3d3d3d"),
                                            self._lbl_file.config(bg="#3d3d3d")))
            w.bind("<Leave>",    lambda _: (self._zone.config(bg=BG3),
                                            self._lbl_file.config(bg=BG3)))

        # ── Options row
        opt = tk.Frame(self, bg=BG, pady=2)
        opt.pack(fill=tk.X, padx=24)
        tk.Label(opt, text="Compute:", font=("Segoe UI", 8),
                 fg=FG_DIM, bg=BG).pack(side=tk.LEFT)
        for val, lbl in (("cuda", "CUDA (GPU)"), ("cpu", "CPU (slow)")):
            tk.Radiobutton(opt, text=lbl, variable=self._device, value=val,
                           font=("Segoe UI", 8), fg=FG, bg=BG,
                           selectcolor=BG2, activebackground=BG,
                           activeforeground=FG).pack(side=tk.LEFT, padx=8)

        # ── Export format row
        fmt = tk.Frame(self, bg=BG, pady=2)
        fmt.pack(fill=tk.X, padx=24)
        tk.Label(fmt, text="Export:", font=("Segoe UI", 8),
                 fg=FG_DIM, bg=BG).pack(side=tk.LEFT)
        for val, lbl in (("spz", "SPZ (compressed)"), ("ply", "PLY (original)")):
            tk.Radiobutton(fmt, text=lbl, variable=self._export_fmt, value=val,
                           font=("Segoe UI", 8), fg=FG, bg=BG,
                           selectcolor=BG2, activebackground=BG,
                           activeforeground=FG).pack(side=tk.LEFT, padx=8)

        # ── Viewer path row
        vwr = tk.Frame(self, bg=BG, pady=3)
        vwr.pack(fill=tk.X, padx=20)
        tk.Label(vwr, text="Viewer:", font=("Segoe UI", 8),
                 fg=FG_DIM, bg=BG, width=7, anchor="w").pack(side=tk.LEFT)
        tk.Entry(vwr, textvariable=self._splatapult_exe_var,
                 font=("Consolas", 7), bg=BG2, fg=FG,
                 insertbackground=FG, relief="flat",
                 bd=4).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(vwr, text="Browse…", font=("Segoe UI", 8),
                  bg=BG3, fg=FG, activebackground="#444", activeforeground=FG,
                  relief="flat", bd=0, padx=8,
                  command=self._browse_splatapult).pack(side=tk.LEFT)

        # ── Progress / status bar
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill=tk.X, padx=20, pady=4)
        self._lbl_status = tk.Label(bar, text="", font=("Segoe UI", 8),
                                     fg=FG_DIM, bg=BG, anchor="w")
        self._lbl_status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._progress = ttk.Progressbar(bar, mode="indeterminate", length=160)
        self._progress.pack(side=tk.RIGHT)

        # ── Log area
        self._log_area = scrolledtext.ScrolledText(
            self, height=14, bg="#0d0d0d", fg="#b5b5b5",
            font=("Consolas", 8), insertbackground=FG,
            relief="flat", wrap=tk.WORD)
        self._log_area.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))
        self._log_area.tag_config("ok",   foreground=OK_COL)
        self._log_area.tag_config("err",  foreground=ERR)
        self._log_area.tag_config("warn", foreground=WARN)
        self._log_area.tag_config("dim",  foreground=FG_DIM)

    def _log(self, text, tag=""):
        def _do():
            self._log_area.insert(tk.END, text + "\n", tag)
            self._log_area.see(tk.END)
        self.after(0, _do)

    def _set_status(self, text):
        self.after(0, lambda: self._lbl_status.config(text=text))

    # ── File picker ───────────────────────────────────────────────────────────

    def _browse(self):
        if self._running:
            return
        path = filedialog.askopenfilename(
            title="Select image to convert",
            filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")]
        )
        if path:
            self._start(path)

    def _browse_splatapult(self):
        path = filedialog.askopenfilename(
            title="Locate splatapult.exe",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self._splatapult_exe_var.set(path)
            self._log(f"✓  splatapult path updated: {path}", "ok")

    def _ask_splatapult_exe(self):
        """Ask the user to locate splatapult.exe from the main thread.
        Returns the chosen path, or empty string if cancelled.
        Safe to call from a background thread."""
        result = [""]
        done   = threading.Event()
        def _ask():
            path = filedialog.askopenfilename(
                title="Locate splatapult.exe",
                filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
            )
            result[0] = path or ""
            done.set()
        self.after(0, _ask)
        done.wait()
        return result[0]

    # ── Pipeline ──────────────────────────────────────────────────────────────

    def _start(self, image_path):
        if self._running:
            return
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            self._log(f"✗  Unsupported format '{ext}' – use .jpg or .png", "err")
            return
        if not os.path.exists(image_path):
            self._log(f"✗  File not found: {image_path}", "err")
            return
        self._running = True
        self._progress.start(12)
        self.after(0, lambda: self._lbl_file.config(
            text=os.path.basename(image_path), fg=FG))
        threading.Thread(target=self._pipeline, args=(image_path,),
                         daemon=True).start()

    def _pipeline(self, image_path):
        try:
            stem    = os.path.splitext(os.path.basename(image_path))[0]
            out_dir = os.path.dirname(image_path)
            ply     = os.path.join(out_dir, stem + ".ply")

            # ── Step 1: SHARP prediction ──────────────────────────────────
            sharp_exe = find_sharp_exe()
            if not sharp_exe:
                self._log(f"✗  SHARP not found. Run Setup_NewPC.bat first.", "err")
                return

            self._set_status("Step 1/3  –  Running SHARP…")
            self._log(f"\n▶  Input:  {image_path}")
            self._log(f"   Output: {ply}")

            cmd = [sharp_exe, "predict",
                   "-i", image_path,
                   "-o", out_dir,
                   "--device", self._device.get()]

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in proc.stdout:
                stripped = line.rstrip()
                if stripped:
                    self._log("   " + stripped)
            proc.wait()

            if proc.returncode != 0:
                self._log(f"✗  SHARP exited with code {proc.returncode}", "err")
                return

            if not os.path.exists(ply):
                self._log(f"✗  Expected PLY not created: {ply}", "err")
                return

            # ── Step 2: Transform PLY ─────────────────────────────────────
            self._set_status("Step 2/3  –  Transforming coordinate system…")
            self._log("   Fixing coordinate system for splatapult…")
            tmp = ply + ".tmp"
            transform_ply(ply, tmp)
            replace_file(tmp, ply)
            self._log(f"✓  PLY ready: {ply}", "ok")

            # ── Step 3: Convert PLY to SPZ (optional) ─────────────────────
            viewer_file = ply
            if self._export_fmt.get() == "spz":
                spz = os.path.join(out_dir, stem + ".spz")
                self._set_status("Step 3/3  –  Converting to SPZ…")
                self._log("   Converting PLY to SPZ format…")
                converter_exe = find_3dgsconverter_exe()
                if not converter_exe:
                    self._log("⚠  3dgsconverter not found in conda env, using PLY instead", "warn")
                else:
                    try:
                        conv_cmd = [converter_exe, "-i", ply, "-f", "spz", "--force"]
                        conv_proc = subprocess.Popen(
                            conv_cmd,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace",
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        for line in conv_proc.stdout:
                            stripped = line.rstrip()
                            if stripped:
                                self._log("   " + stripped)
                        conv_proc.wait()
                        if os.path.exists(spz):
                            os.remove(ply)
                            viewer_file = spz
                            self._log(f"✓  SPZ ready: {spz}", "ok")
                        else:
                            self._log("⚠  SPZ conversion failed, using PLY instead", "warn")
                    except Exception as e:
                        self._log(f"⚠  SPZ conversion error: {e}, using PLY instead", "warn")
            else:
                self._log("   SPZ conversion skipped (PLY format selected).", "dim")

            # ── Step 4: Launch splatapult ─────────────────────────────────
            self._set_status("Launching splatapult…")
            splatapult_exe = self._splatapult_exe_var.get()
            if not os.path.exists(splatapult_exe):
                self._log("⚠  splatapult.exe not found – please locate it now…", "warn")
                splatapult_exe = self._ask_splatapult_exe()
                if not splatapult_exe:
                    self._log("✗  Launch cancelled – no splatapult.exe selected.", "err")
                    self._set_status("Cancelled – splatapult not found")
                    return
                self._splatapult_exe_var.set(splatapult_exe)
                self._log(f"✓  splatapult path saved: {splatapult_exe}", "ok")
            splatapult_dir = os.path.dirname(splatapult_exe)
            subprocess.Popen([splatapult_exe, viewer_file], cwd=splatapult_dir)
            self._log("✅  Done!  splatapult is opening.", "ok")
            self._set_status("Done – click to convert another image")
            self.after(0, lambda: self._lbl_file.config(
                text="▸  Click here to convert another image", fg=FG_DIM))

        except Exception:
            import traceback
            self._log(f"✗  {traceback.format_exc()}", "err")
            self._set_status("Error – see log")
        finally:
            self._running = False
            self.after(0, self._progress.stop)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    initial = sys.argv[1] if len(sys.argv) > 1 else ""
    App(initial).mainloop()
