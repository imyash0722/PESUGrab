"""
PESUGrab — Desktop app for downloading course materials from PESU Academy.
Tkinter GUI with headless Playwright automation on a dedicated worker thread.
"""

import ctypes
import os
import re
import queue
import subprocess
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Type checking / IDE support
if False:
    from scraper import AcademySession

# ────────────────────────────────────────────────────────────
# Palette
# ────────────────────────────────────────────────────────────
BG           = "#111111"
SURFACE      = "#1c1c1c"
FIELD        = "#262626"
ELEVATED     = "#333333"
HOVER        = "#444444"
ACCENT       = "#7e57c2"
ACCENT_HOVER = "#6d45b0"
ACCENT_DIM   = "#2d2640"
TEXT         = "#d4d4d4"
TEXT_DIM     = "#777777"
TEXT_HI      = "#f0f0f0"
HEADING      = "#b39ddb"
SEL          = "#352a4a"

FONT         = ("Segoe UI", 10)
FONT_B       = ("Segoe UI", 10, "bold")
FONT_TITLE   = ("Segoe UI", 14, "bold")
FONT_SEC     = ("Segoe UI", 11, "bold")
FONT_SM      = ("Segoe UI", 9)
FONT_LOG     = ("Cascadia Code", 9)
FONT_LOGIN_T = ("Segoe UI", 16, "bold")

# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────

def _dark_titlebar(win):
    """Windows-only: force dark window chrome."""
    try:
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20,
            ctypes.byref(ctypes.c_int(1)),
            ctypes.sizeof(ctypes.c_int),
        )
    except Exception:
        pass


def _center(win, w, h):
    """Place *win* at the centre of the screen."""
    win.geometry(
        f"{w}x{h}"
        f"+{(win.winfo_screenwidth()  - w) // 2}"
        f"+{(win.winfo_screenheight() - h) // 2}"
    )

# ────────────────────────────────────────────────────────────
# Application
# ────────────────────────────────────────────────────────────

class PESUGrab:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PESUGrab")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self.root.withdraw()                       # hidden until login

        # State
        self.session   = AcademySession()
        self.semesters = []
        self.courses   = []
        self.units     = []
        self.save_dir  = os.path.join(os.path.expanduser("~"), "Downloads")
        self._busy     = False

        # Worker thread (Playwright is thread-bound)
        self._q = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()

        self._theme()
        self._build_main()
        self.root.after(50, self._open_login)

    # ── Worker ──────────────────────────────────────────

    def _worker(self):
        while True:
            job = self._q.get()
            if job is None:
                break
            fn, args = job
            try:
                fn(*args)
            except Exception as e:
                self._log(f"ERROR: {e}")
            self._q.task_done()

    def _push(self, fn, *a):
        if self._busy:
            return
        self._set_busy(True)
        self._q.put((fn, a))

    # ── Theme ───────────────────────────────────────────

    def _theme(self):
        s = ttk.Style()
        s.theme_use("clam")

        s.configure(".",           background=BG,      foreground=TEXT,    font=FONT)
        s.configure("TFrame",      background=BG)
        s.configure("Card.TFrame", background=SURFACE)

        s.configure("TLabel",      background=SURFACE, foreground=TEXT,    font=FONT)
        s.configure("Title.TLabel",background=BG,      foreground=TEXT_HI, font=FONT_TITLE)
        s.configure("Sec.TLabel",  background=SURFACE, foreground=HEADING, font=FONT_SEC)
        s.configure("Dim.TLabel",  background=SURFACE, foreground=TEXT_DIM,font=FONT_SM)
        s.configure("LT.TLabel",   background=SURFACE, foreground=TEXT_HI, font=FONT_LOGIN_T)

        s.configure("TEntry", fieldbackground=FIELD, foreground=TEXT,
                    insertcolor=TEXT, borderwidth=1, relief="flat")

        s.configure("TButton", background=ELEVATED, foreground=TEXT,
                    font=FONT_B, borderwidth=0, padding=(12, 6))
        s.map("TButton",
              background=[("active", HOVER), ("disabled", "#1a1a1a")],
              foreground=[("disabled", "#444")])

        s.configure("Accent.TButton", background=ACCENT, foreground="#fff",
                    font=FONT_B, borderwidth=0, padding=(14, 8))
        s.map("Accent.TButton",
              background=[("active", ACCENT_HOVER), ("disabled", ACCENT_DIM)],
              foreground=[("disabled", "#555")])

        s.configure("TCombobox", fieldbackground=FIELD, background=FIELD,
                    foreground=TEXT, arrowcolor=TEXT, borderwidth=1)
        s.map("TCombobox",
              fieldbackground=[("readonly", FIELD)],
              selectbackground=[("readonly", FIELD)],
              selectforeground=[("readonly", TEXT)])

        s.configure("Treeview", background=FIELD, foreground=TEXT,
                    fieldbackground=FIELD, font=FONT, rowheight=28, borderwidth=0)
        s.configure("Treeview.Heading", background=ELEVATED, foreground=TEXT_HI, font=FONT_B)
        s.map("Treeview",
              background=[("selected", SEL)],
              foreground=[("selected", TEXT_HI)])

        s.configure("Horizontal.TProgressbar",
                    background=ACCENT, troughcolor=FIELD, borderwidth=0, thickness=5)

    # ── Login Dialog ────────────────────────────────────

    def _open_login(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("PESUGrab — Login")
        dlg.configure(bg=SURFACE)
        dlg.resizable(False, False)
        dlg.protocol("WM_DELETE_WINDOW", self._quit)
        _center(dlg, 420, 280)
        dlg.update_idletasks()
        _dark_titlebar(dlg)
        self._login_dlg = dlg

        p = tk.Frame(dlg, bg=SURFACE)
        p.pack(fill="both", expand=True, padx=30, pady=24)

        ttk.Label(p, text="PESUGrab",                  style="LT.TLabel").pack(anchor="w", pady=(0, 3))
        ttk.Label(p, text="Sign in to PESU Academy",   style="Dim.TLabel").pack(anchor="w", pady=(0, 18))

        r1 = tk.Frame(p, bg=SURFACE); r1.pack(fill="x", pady=(0, 10))
        ttk.Label(r1, text="SRN / PRN", width=10).pack(side="left")
        self._srn = tk.StringVar()
        e1 = ttk.Entry(r1, textvariable=self._srn, width=28)
        e1.pack(side="left", padx=(8, 0))

        r2 = tk.Frame(p, bg=SURFACE); r2.pack(fill="x", pady=(0, 16))
        ttk.Label(r2, text="Password", width=10).pack(side="left")
        self._pwd = tk.StringVar()
        ttk.Entry(r2, textvariable=self._pwd, width=28, show="•").pack(side="left", padx=(8, 0))

        r3 = tk.Frame(p, bg=SURFACE); r3.pack(fill="x")
        self._lbtn = ttk.Button(r3, text="Login", style="Accent.TButton", command=self._do_login)
        self._lbtn.pack(side="left")
        self._lstatus = ttk.Label(r3, text="", style="Dim.TLabel")
        self._lstatus.pack(side="left", padx=(14, 0))

        dlg.bind("<Return>", lambda _: self._do_login())
        e1.focus_set()

    def _do_login(self):
        srn = self._srn.get().strip()
        pwd = self._pwd.get().strip()
        if not srn or not pwd:
            messagebox.showwarning("Login", "Enter SRN and password.",
                                   parent=self._login_dlg)
            return
        self._lbtn.configure(state="disabled")
        self._lstatus.configure(text="Connecting…")
        self._q.put((self._job_login, (srn, pwd)))

    def _job_login(self, srn, pwd):
        def _ls(t):
            self.root.after(0, lambda: self._lstatus.configure(text=t))

        try:
            _ls("Launching browser…")
            self.session.open()
            _ls("Authenticating…")
            self.session.authenticate(srn, pwd)
            _ls("Loading courses…")
            sems    = self.session.list_semesters()
            courses = self.session.list_courses()
            self.root.after(0, self._login_ok, sems, courses)
        except Exception as e:
            _ls(f"✗ {e}")
            self.root.after(0, lambda: self._lbtn.configure(state="normal"))
            self.session.close()

    def _login_ok(self, sems, courses):
        self.semesters = sems
        self._sem_cb["values"] = sems
        if sems:
            self._sem_cb.current(0)
        self._log(f"Logged in — {', '.join(sems)}")
        self._login_dlg.destroy()

        # Show main window, centered, terminal-sized
        _center(self.root, 1100, 700)
        self.root.deiconify()
        self.root.update_idletasks()
        _dark_titlebar(self.root)

        self._show_courses(courses)

    # ── Main Layout ─────────────────────────────────────

    def _build_main(self):
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="both", expand=True, padx=18, pady=10)

        ttk.Label(wrap, text="PESUGrab", style="Title.TLabel").pack(anchor="w", pady=(2, 12))

        # Controls
        cc = ttk.Frame(wrap, style="Card.TFrame")
        cc.pack(fill="x", pady=(0, 8))
        ci = tk.Frame(cc, bg=SURFACE)
        ci.pack(fill="x", padx=14, pady=11)
        ci.columnconfigure(3, weight=1)            # path entry stretches

        ttk.Label(ci, text="Controls", style="Sec.TLabel").grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0, 7))

        ttk.Label(ci, text="Semester:").grid(row=1, column=0, sticky="w", padx=(0, 6))
        self._sem_var = tk.StringVar()
        self._sem_cb = ttk.Combobox(ci, textvariable=self._sem_var,
                                     state="readonly", width=14)
        self._sem_cb.grid(row=1, column=1, padx=(0, 14))
        self._sem_cb.bind("<<ComboboxSelected>>", self._on_sem)

        ttk.Label(ci, text="Save to:").grid(row=1, column=2, sticky="w", padx=(0, 6))
        self._dir_var = tk.StringVar(value=self.save_dir)
        ttk.Entry(ci, textvariable=self._dir_var).grid(
            row=1, column=3, sticky="ew", padx=(0, 6))
        ttk.Button(ci, text="Browse", command=self._pick_dir).grid(
            row=1, column=4)

        # Courses + Units
        mid = tk.Frame(wrap, bg=BG)
        mid.pack(fill="both", expand=True, pady=(0, 8))
        mid.columnconfigure(0, weight=3)
        mid.columnconfigure(1, weight=2)
        mid.rowconfigure(0, weight=1)

        # Courses
        lc = ttk.Frame(mid, style="Card.TFrame")
        lc.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        lci = tk.Frame(lc, bg=SURFACE)
        lci.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Label(lci, text="Courses", style="Sec.TLabel").pack(anchor="w", pady=(0, 5))

        self._tree = ttk.Treeview(lci, columns=("code", "title"),
                                  show="headings", height=12)
        self._tree.heading("code", text="Code")
        self._tree.heading("title", text="Title")
        self._tree.column("code", width=120, minwidth=90)
        self._tree.column("title", width=320, minwidth=140)
        self._tree.pack(fill="both", expand=True)
        self._tree.bind("<<TreeviewSelect>>", self._on_course)

        # Units (with loading overlay)
        rc = ttk.Frame(mid, style="Card.TFrame")
        rc.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        rci = tk.Frame(rc, bg=SURFACE)
        rci.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Label(rci, text="Units", style="Sec.TLabel").pack(anchor="w", pady=(0, 5))

        # Container so we can swap between listbox and loading label
        self._units_frame = tk.Frame(rci, bg=FIELD)
        self._units_frame.pack(fill="both", expand=True)

        self._units_lb = tk.Listbox(
            self._units_frame, bg=FIELD, fg=TEXT, selectbackground=SEL,
            selectforeground=TEXT_HI, font=FONT, borderwidth=0,
            highlightthickness=0, activestyle="none",
        )
        self._units_lb.pack(fill="both", expand=True)

        # Loading label (hidden initially)
        self._units_loading = tk.Label(
            self._units_frame, bg=FIELD, fg=TEXT_DIM,
            font=("Segoe UI", 10), text="",
            anchor="center", justify="center",
        )
        self._loading_dots = 0
        self._loading_after = None

        # Download bar
        dc = ttk.Frame(wrap, style="Card.TFrame")
        dc.pack(fill="x", pady=(0, 8))
        di = tk.Frame(dc, bg=SURFACE)
        di.pack(fill="x", padx=14, pady=11)
        ttk.Label(di, text="Download", style="Sec.TLabel").pack(anchor="w", pady=(0, 7))

        br = tk.Frame(di, bg=SURFACE); br.pack(fill="x")
        self._btn_u = ttk.Button(br, text="Download Selected Unit",
                                 style="Accent.TButton", command=self._dl_unit)
        self._btn_u.pack(side="left", padx=(0, 6))
        self._btn_c = ttk.Button(br, text="Download All Units (Course)",
                                 command=self._dl_course)
        self._btn_c.pack(side="left", padx=(0, 6))
        self._btn_s = ttk.Button(br, text="Download All Courses (Semester)",
                                 command=self._dl_sem)
        self._btn_s.pack(side="left")

        # Log
        lcard = ttk.Frame(wrap, style="Card.TFrame")
        lcard.pack(fill="x")
        lf = tk.Frame(lcard, bg=SURFACE)
        lf.pack(fill="x", padx=14, pady=10)

        self._pbar = ttk.Progressbar(lf, mode="determinate",
                                     style="Horizontal.TProgressbar")
        self._pbar.pack(fill="x", pady=(0, 5))

        self._logbox = tk.Text(
            lf, bg="#0e0e0e", fg="#b0a0d0", font=FONT_LOG, height=8,
            borderwidth=0, insertbackground=TEXT, state="disabled",
            wrap="word",
        )
        self._logbox.pack(fill="x")

    # ── Loading indicator ───────────────────────────────

    def _show_loading(self, label="Loading units"):
        """Replace the units listbox with an animated loading message."""
        self._units_lb.pack_forget()
        self._units_loading.pack(fill="both", expand=True)
        self._loading_dots = 0
        self._loading_base = label
        self._tick_loading()

    def _tick_loading(self):
        self._loading_dots = (self._loading_dots + 1) % 4
        dots = "." * self._loading_dots
        self._units_loading.configure(text=f"⏳  {self._loading_base}{dots}")
        self._loading_after = self.root.after(400, self._tick_loading)

    def _hide_loading(self):
        """Swap back to the units listbox."""
        if self._loading_after:
            self.root.after_cancel(self._loading_after)
            self._loading_after = None
        self._units_loading.pack_forget()
        self._units_lb.pack(fill="both", expand=True)

    # ── Thread-safe helpers ─────────────────────────────

    def _log(self, msg):
        def _w():
            self._logbox.configure(state="normal")
            self._logbox.insert("end", msg + "\n")
            self._logbox.see("end")
            self._logbox.configure(state="disabled")
        self.root.after(0, _w)

    def _set_busy(self, b):
        def _w():
            self._busy = b
            st = "disabled" if b else "normal"
            for w in (self._btn_u, self._btn_c, self._btn_s):
                w.configure(state=st)
        self.root.after(0, _w)

    def _set_pbar(self, v):
        self.root.after(0, lambda: self._pbar.configure(value=v))

    @staticmethod
    def _safe(s):
        return re.sub(r"[^\w\- ]", "", s).strip()

    def _pick_dir(self):
        d = filedialog.askdirectory(initialdir=self.save_dir, title="Choose folder")
        if d:
            self.save_dir = d
            self._dir_var.set(d)

    # ── UI callbacks ────────────────────────────────────

    def _on_sem(self, _e):
        sem = self._sem_var.get()
        if sem:
            self.root.after(0, self._show_loading, "Loading courses")
            self._push(self._job_semester, sem)

    def _on_course(self, _e):
        sel = self._tree.selection()
        if sel:
            self.root.after(0, self._show_loading, "Loading units")
            self._push(self._job_units, self._tree.index(sel[0]))

    def _dl_unit(self):
        ci, ui = self._need_course(), self._need_unit()
        if ci is not None and ui is not None:
            self._push(self._job_dl_unit, ci, ui)

    def _dl_course(self):
        ci = self._need_course()
        if ci is not None:
            self._push(self._job_dl_all_units, ci)

    def _dl_sem(self):
        if not self.courses:
            messagebox.showwarning("No courses", "Load a semester first.")
            return
        self._push(self._job_dl_all_courses)

    def _need_course(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Pick a course first.")
            return None
        return self._tree.index(sel[0])

    def _need_unit(self):
        sel = self._units_lb.curselection()
        if not sel:
            messagebox.showwarning("Select", "Pick a unit first.")
            return None
        return sel[0]

    # ── Worker jobs ─────────────────────────────────────

    def _job_semester(self, sem):
        try:
            self._log(f"Switching to {sem}…")
            self.session.switch_semester(sem)
            courses = self.session.list_courses()
            self.root.after(0, self._show_courses, courses)
        except Exception as e:
            self._log(f"Error: {e}")
            self.root.after(0, self._hide_loading)
            self._set_busy(False)

    def _show_courses(self, courses):
        self.courses = courses
        self._tree.delete(*self._tree.get_children())
        for c in courses:
            self._tree.insert("", "end", values=(c["code"], c["title"]))
        self._units_lb.delete(0, "end")
        self.units = []
        self._hide_loading()
        self._log(f"{len(courses)} courses loaded ✓")
        self._set_busy(False)

    def _job_units(self, idx):
        try:
            c = self.courses[idx]
            self._log(f"Opening {c['title']}…")
            self.session.navigate_to_courses()
            self.session.switch_semester(self._sem_var.get())
            self.session.list_courses()
            self.session.open_course(idx)
            names = self.session.list_units()
            self.root.after(0, self._show_units, names)
        except Exception as e:
            self._log(f"Error: {e}")
            self.root.after(0, self._hide_loading)
            self._set_busy(False)

    def _show_units(self, names):
        self.units = names
        self._units_lb.delete(0, "end")
        for i, n in enumerate(names):
            self._units_lb.insert("end", f"  {i+1}. {n}")
        self._hide_loading()
        self._log(f"{len(names)} units loaded ✓")
        self._set_busy(False)

    # ── Download jobs ───────────────────────────────────

    def _job_dl_unit(self, ci, ui):
        try:
            co = self.courses[ci]; un = self.units[ui]
            self._log(f"\n{'─'*40}\nDownloading: {co['title']} → {un}")
            self._nav(ci)
            self._log("Scanning files…")
            files = self.session.discover_files(
                ui, progress_cb=lambda m: self._log(f"  {m}"))
            self._log(f"{len(files)} files found")
            self._save(files, co["title"], un)
            self._log("Download complete ✓")
        except Exception as e:
            self._log(f"Error: {e}")
        finally:
            self._set_busy(False); self._set_pbar(0)

    def _job_dl_all_units(self, ci):
        try:
            co = self.courses[ci]
            self._log(f"\n{'─'*40}\nAll units for: {co['title']}")
            self._nav(ci)
            all_u = self.session.list_units()
            total = 0
            for ui, un in enumerate(all_u):
                self._log(f"\n── Unit {ui+1}/{len(all_u)}: {un}")
                self._nav(ci)
                files = self.session.discover_files(
                    ui, progress_cb=lambda m: self._log(f"  {m}"))
                self._save(files, co["title"], un)
                total += len(files)
            self._log(f"\n{total} files across {len(all_u)} units ✓")
        except Exception as e:
            self._log(f"Error: {e}")
        finally:
            self._set_busy(False); self._set_pbar(0)

    def _job_dl_all_courses(self):
        try:
            sem = self._sem_var.get()
            self._log(f"\n{'─'*40}\nAll courses for {sem}")
            total = 0
            for ci, co in enumerate(self.courses):
                self._log(f"\n═ Course {ci+1}/{len(self.courses)}: {co['title']}")
                self._nav(ci)
                try:
                    all_u = self.session.list_units()
                except Exception:
                    self._log("  ⚠ No units — skipping"); continue
                for ui, un in enumerate(all_u):
                    self._log(f"  ── Unit {ui+1}/{len(all_u)}: {un}")
                    self._nav(ci)
                    try:
                        files = self.session.discover_files(
                            ui, progress_cb=lambda m: self._log(f"    {m}"))
                    except Exception as e:
                        self._log(f"    ⚠ {e}"); continue
                    self._save(files, co["title"], un)
                    total += len(files)
            self._log(f"\n{total} files total ✓")
        except Exception as e:
            self._log(f"Error: {e}")
        finally:
            self._set_busy(False); self._set_pbar(0)

    # ── Shared helpers ──────────────────────────────────

    def _nav(self, course_idx):
        """Navigate to a course's unit listing page."""
        self.session.navigate_to_courses()
        self.session.switch_semester(self._sem_var.get())
        self.session.list_courses()
        self.session.open_course(course_idx)
        self.session.list_units()

    def _save(self, files, course_title, unit_name):
        """Download a batch of files into an organised folder."""
        if not files:
            self._log("  No files"); return
        folder = os.path.join(
            self._dir_var.get(),
            self._safe(course_title),
            self._safe(unit_name),
        )
        os.makedirs(folder, exist_ok=True)
        n = len(files)
        for i, f in enumerate(files):
            self._set_pbar(int((i + 1) / n * 100))
            name = self._safe(f["name"])[:55] or f"file_{i+1}"
            ext  = f".{f.get('filetype', 'pdf')}"
            fname = f"{i+1:03d}_{name}{ext}"
            self._log(f"  [{i+1}/{n}] {fname}")
            if not self.session.retrieve_file(f["href"],
                                              os.path.join(folder, fname)):
                self._log("    ⚠ failed")
        self._log(f"  ✓ {n} files → {folder}")

    # ── Cleanup ─────────────────────────────────────────

    def _quit(self):
        self._q.put(None)
        self.session.close()
        self.root.destroy()


def _run_setup_and_launch():
    """Verify and install dependencies and Chromium before launching the app."""
    import importlib.util

    setup_root = tk.Tk()
    setup_root.title("PESUGrab Setup")
    setup_root.configure(bg=BG)
    _center(setup_root, 400, 150)
    setup_root.resizable(False, False)
    _dark_titlebar(setup_root)
    
    # Hide the setup window initially while we check if setup is even needed
    setup_root.withdraw()

    # Determine if we need to do any work
    needs_pip = (importlib.util.find_spec("playwright") is None) or (importlib.util.find_spec("dotenv") is None)
    
    # Check for playwright browsers
    needs_chromium = False
    if not needs_pip:
        try:
            # Quick check if browsers are installed
            out = subprocess.run([sys.executable, "-m", "playwright", "install", "--dry-run"], capture_output=True, text=True)
            if "chromium" in out.stdout.lower() and "download" in out.stdout.lower():
                 needs_chromium = True
        except Exception:
            needs_chromium = True
            
    if not needs_pip and not needs_chromium:
        setup_root.destroy()
        _launch_main()
        return

    # Work is needed! Show UI
    setup_root.deiconify()
    
    lbl = tk.Label(setup_root, text="Setting up PESUGrab for first use...", bg=BG, fg=TEXT_HI, font=FONT_TITLE)
    lbl.pack(pady=(20, 10))
    
    status_lbl = tk.Label(setup_root, text="Checking requirements...", bg=BG, fg=TEXT_DIM, font=FONT)
    status_lbl.pack(pady=(0, 10))

    def _setup_worker():
        try:
            if needs_pip:
                setup_root.after(0, lambda: status_lbl.config(text="Installing Python dependencies..."))
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "playwright", "python-dotenv"],
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            
            setup_root.after(0, lambda: status_lbl.config(text="Installing Playwright Chromium...\n(This may take a few minutes)"))
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            setup_root.after(0, setup_root.destroy)
            setup_root.after(0, _launch_main)
            
        except Exception as e:
            setup_root.after(0, lambda: status_lbl.config(text=f"Setup failed! Please run manually.\n{e}"))

    threading.Thread(target=_setup_worker, daemon=True).start()
    setup_root.mainloop()


def _launch_main():
    """Launch the actual application after setup is guaranteed."""
    # We must import scraper here locally inside _launch_main, 
    # because if playwright wasn't installed, importing it at the top of the file would crash the script!
    global AcademySession
    from scraper import AcademySession

    root = tk.Tk()
    PESUGrab(root)
    root.mainloop()


if __name__ == "__main__":
    _run_setup_and_launch()
