import os
import sys
import shutil
import subprocess
import threading
import winreg
import ctypes
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ---------------------------------------------------------------------------
# Helpers â€” resolve bundled resources
# ---------------------------------------------------------------------------
def _res(name: str) -> str:
    """Return path to a bundled resource (works frozen + source)."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)


def _read_version() -> str:
    try:
        with open(_res('VERSION'), 'r') as f:
            return f.read().strip()
    except Exception:
        return '1.0.0'


VERSION      = _read_version()
PRODUCT_NAME = 'APex IMM RCA Utility'
SERVICE_NAME = 'APexRCA'
DEFAULT_INSTALL_DIR = os.path.join(
    os.environ.get('PROGRAMFILES', r'C:\Program Files'), PRODUCT_NAME
)

# ---------------------------------------------------------------------------
# Design tokens: colours & typography
# ---------------------------------------------------------------------------
BG_DARK    = '#09090b'  # Modern deep gray/black
BG_PANEL   = '#18181b'  # Slightly lighter container
BG_CARD    = '#27272a'  # Card background
ACCENT     = '#3b82f6'  # Modern vibrant blue
TEXT_WHITE = '#f8fafc'
TEXT_GREY  = '#94a3b8'
TEXT_DIM   = '#64748b'
FONT_TITLE = ('Segoe UI', 24, 'bold')
FONT_HEAD  = ('Segoe UI', 16, 'bold')
FONT_BODY  = ('Segoe UI', 10)
FONT_SMALL = ('Segoe UI', 9)
FONT_CREDIT= ('Segoe UI', 9)
FONT_BTN   = ('Segoe UI', 11, 'bold')


# ---------------------------------------------------------------------------
# Setup Wizard Application
# ---------------------------------------------------------------------------
class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'{PRODUCT_NAME} Setup')
        self.resizable(False, False)
        self.configure(bg=BG_DARK)

        # Center on screen
        w, h = 680, 500
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')

        # State
        self.install_dir = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        self.create_desktop  = tk.BooleanVar(value=True)
        self.create_startmenu = tk.BooleanVar(value=True)
        self.start_service   = tk.BooleanVar(value=False)
        self.current_step    = 0

        # Set window icon
        try:
            self.iconbitmap(_res(os.path.join('frontend', 'assets', 'ApplicationIcon.ico')))
        except Exception:
            pass

        # Load logo image for header
        self.logo_img = None
        try:
            logo_path = _res(os.path.join('frontend', 'assets', 'logo.png'))
            if os.path.exists(logo_path):
                raw_img = tk.PhotoImage(file=logo_path)
                h = raw_img.height()
                sub = max(1, h // 50)
                self.logo_img = raw_img.subsample(sub, sub)
        except Exception:
            pass

        self._build_header()
        self._build_nav()
        self._build_body()
        self._show_step(0)

    # ------------------------------------------------------------------
    # Layout scaffolding
    # ------------------------------------------------------------------
    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_CARD, height=80)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)

        # Show logo if available
        if self.logo_img:
            lbl_logo = tk.Label(hdr, image=self.logo_img, bg=BG_CARD)
            lbl_logo.pack(side='left', padx=(20, 0), pady=10)

        title_padx = (10, 20) if self.logo_img else 20
        title_text = f'{PRODUCT_NAME} Setup' if self.logo_img else f'  {PRODUCT_NAME} Setup'

        tk.Label(
            hdr, text=title_text,
            font=FONT_TITLE, bg=BG_CARD, fg=ACCENT,
            anchor='w',
        ).pack(side='left', padx=title_padx, pady=16)

        tk.Label(
            hdr, text=f'v{VERSION}',
            font=FONT_BODY, bg=BG_CARD, fg=TEXT_GREY,
            anchor='e',
        ).pack(side='right', padx=20)

    def _build_body(self):
        self.body = tk.Frame(self, bg=BG_DARK)
        self.body.pack(fill='both', expand=True, padx=0, pady=0)

        # Step frames (only one visible at a time)
        self.steps = [
            self._make_step_welcome(),
            self._make_step_directory(),
            self._make_step_options(),
            self._make_step_progress(),
        ]

    def _build_nav(self):
        nav = tk.Frame(self, bg=BG_PANEL, height=60)
        nav.pack(fill='x', side='bottom')
        nav.pack_propagate(False)

        # Separator line
        tk.Frame(nav, bg=ACCENT, height=1).pack(fill='x')

        btn_frame = tk.Frame(nav, bg=BG_PANEL)
        btn_frame.pack(side='right', padx=24, pady=12)

        self.btn_cancel = tk.Button(
            btn_frame, text='Cancel', font=FONT_BTN,
            bg=BG_CARD, fg=TEXT_GREY, relief='flat', padx=18, pady=6,
            cursor='hand2', activebackground=BG_DARK, activeforeground=TEXT_WHITE,
            command=self._on_cancel,
        )
        self.btn_cancel.pack(side='right', padx=(8, 0))

        self.btn_next = tk.Button(
            btn_frame, text='Next  â€º', font=FONT_BTN,
            bg=ACCENT, fg='white', relief='flat', padx=20, pady=6,
            cursor='hand2', activebackground='#c73651', activeforeground='white',
            command=self._on_next,
        )
        self.btn_next.pack(side='right')

        self.btn_back = tk.Button(
            btn_frame, text='â€¹  Back', font=FONT_BTN,
            bg=BG_CARD, fg=TEXT_WHITE, relief='flat', padx=18, pady=6,
            cursor='hand2', activebackground=BG_DARK, activeforeground=TEXT_WHITE,
            command=self._on_back,
        )
        self.btn_back.pack(side='right', padx=(0, 6))

    # ------------------------------------------------------------------
    # Step 1 â€” Welcome & Credits (2-Column layout)
    # ------------------------------------------------------------------
    def _make_step_welcome(self) -> tk.Frame:
        f = tk.Frame(self.body, bg=BG_DARK)

        # Left accent bar
        tk.Frame(f, bg=ACCENT, width=4).pack(side='left', fill='y')

        # Main horizontal container
        container = tk.Frame(f, bg=BG_DARK)
        container.pack(fill='both', expand=True, padx=24, pady=24)

        # Left Column: Welcome text
        left_col = tk.Frame(container, bg=BG_DARK)
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 20))

        tk.Label(
            left_col, text='Welcome to the Setup Wizard',
            font=FONT_HEAD, bg=BG_DARK, fg=TEXT_WHITE, anchor='w',
        ).pack(fill='x')

        tk.Label(
            left_col, text=(
                'This wizard will guide you through the installation of\n'
                f'{PRODUCT_NAME} & RCA Tool on your machine.\n\n'
                'The application will be installed as a Windows Service,\n'
                'running silently in the background â€” no terminal window.\n\n'
                'Click  Next  to continue, or  Cancel  to exit.'
            ),
            font=FONT_BODY, bg=BG_DARK, fg=TEXT_GREY,
            anchor='nw', justify='left',
        ).pack(fill='both', expand=True, pady=(16, 0))

        # Right Column: Credits card container
        right_col = tk.Frame(container, bg=BG_DARK, width=280)
        right_col.pack(side='right', fill='y', expand=False)
        right_col.pack_propagate(False)

        # Credits card
        card = tk.Frame(right_col, bg=BG_PANEL, padx=16, pady=16)
        card.pack(fill='both', expand=True)

        lines = [
            ('Magic xpi IMM Diagnostic & RCA Utility', ('Segoe UI', 9, 'bold'), ACCENT),
            (f'Version {VERSION} (Enterprise Edition)', FONT_CREDIT,             TEXT_GREY),
            ('System Diagnostic Tool',             FONT_SMALL,              TEXT_DIM),
            ('',                                   FONT_CREDIT,             BG_PANEL),
            ('Created by:',                        FONT_SMALL,              TEXT_DIM),
            ('Aniruddh Potdar (ITS-Support)',      ('Segoe UI', 10, 'bold'), TEXT_WHITE),
            ('',                                   FONT_CREDIT,             BG_PANEL),
            ('APex IMM Enterprises Ltd.',    FONT_CREDIT,             TEXT_GREY),
            ('(A MATRIX Company)',                 FONT_CREDIT,             TEXT_DIM),
            ('',                                   FONT_CREDIT,             BG_PANEL),
            (f'\u00a9 2026 Aniruddh Potdar.',       FONT_SMALL,              TEXT_DIM),
            ('All rights reserved.',                FONT_SMALL,              TEXT_DIM),
        ]
        for text, font, colour in lines:
            tk.Label(card, text=text, font=font, bg=BG_PANEL,
                     fg=colour, anchor='w', justify='left').pack(fill='x', pady=1)

        return f

    # ------------------------------------------------------------------
    # Step 2 â€” Installation Directory
    # ------------------------------------------------------------------
    def _make_step_directory(self) -> tk.Frame:
        f = tk.Frame(self.body, bg=BG_DARK)
        tk.Frame(f, bg=ACCENT, width=4).pack(side='left', fill='y')
        inner = tk.Frame(f, bg=BG_DARK)
        inner.pack(side='left', fill='both', expand=True, padx=36, pady=30)

        tk.Label(
            inner, text='Choose Installation Directory',
            font=FONT_HEAD, bg=BG_DARK, fg=TEXT_WHITE, anchor='w',
        ).pack(fill='x')
        tk.Label(
            inner,
            text='Select the folder where the application will be installed.',
            font=FONT_BODY, bg=BG_DARK, fg=TEXT_GREY, anchor='w',
        ).pack(fill='x', pady=(6, 20))

        row = tk.Frame(inner, bg=BG_DARK)
        row.pack(fill='x')

        entry = tk.Entry(
            row, textvariable=self.install_dir,
            font=FONT_BODY, bg=BG_PANEL, fg=TEXT_WHITE,
            insertbackground=TEXT_WHITE, relief='flat',
            highlightbackground=BG_CARD, highlightthickness=1,
        )
        entry.pack(side='left', fill='x', expand=True, ipady=7, padx=(0, 8))

        tk.Button(
            row, text='Browseâ€¦', font=FONT_BTN,
            bg=BG_CARD, fg=TEXT_WHITE, relief='flat', padx=14, pady=4,
            cursor='hand2', activebackground=ACCENT, activeforeground='white',
            command=self._browse_dir,
        ).pack(side='right')

        tk.Label(
            inner,
            text=f'Default: {DEFAULT_INSTALL_DIR}',
            font=FONT_SMALL, bg=BG_DARK, fg=TEXT_DIM, anchor='w',
        ).pack(fill='x', pady=(6, 0))

        # Disk space info
        tk.Frame(inner, bg=BG_CARD, height=1).pack(fill='x', pady=18)
        tk.Label(
            inner,
            text='Required disk space: ~45 MB\nThe installer will create the directory if it does not exist.',
            font=FONT_SMALL, bg=BG_DARK, fg=TEXT_DIM, anchor='w', justify='left',
        ).pack(fill='x')

        return f

    def _browse_dir(self):
        chosen = filedialog.askdirectory(
            title='Select Installation Directory',
            initialdir=self.install_dir.get(),
        )
        if chosen:
            self.install_dir.set(chosen.replace('/', os.sep))

    # ------------------------------------------------------------------
    # Step 3 â€” Options
    # ------------------------------------------------------------------
    def _make_step_options(self) -> tk.Frame:
        f = tk.Frame(self.body, bg=BG_DARK)
        tk.Frame(f, bg=ACCENT, width=4).pack(side='left', fill='y')
        inner = tk.Frame(f, bg=BG_DARK)
        inner.pack(side='left', fill='both', expand=True, padx=36, pady=30)

        tk.Label(
            inner, text='Installation Options',
            font=FONT_HEAD, bg=BG_DARK, fg=TEXT_WHITE, anchor='w',
        ).pack(fill='x')
        tk.Label(
            inner, text='Choose additional options for this installation.',
            font=FONT_BODY, bg=BG_DARK, fg=TEXT_GREY, anchor='w',
        ).pack(fill='x', pady=(6, 20))

        def _chk(var, label, sub):
            row = tk.Frame(inner, bg=BG_PANEL, padx=14, pady=10)
            row.pack(fill='x', pady=4)
            tk.Checkbutton(
                row, variable=var, text=label,
                font=('Segoe UI', 10, 'bold'),
                bg=BG_PANEL, fg=TEXT_WHITE,
                selectcolor=BG_DARK, activebackground=BG_PANEL,
                activeforeground=TEXT_WHITE, cursor='hand2',
            ).pack(anchor='w')
            tk.Label(
                row, text=sub, font=FONT_SMALL,
                bg=BG_PANEL, fg=TEXT_DIM, anchor='w',
            ).pack(anchor='w', padx=22)

        _chk(self.create_desktop,
             'Create Desktop Shortcut',
             'Adds a shortcut on the Desktop that launches the tool in your browser.')
        _chk(self.create_startmenu,
             'Create Start Menu Entry',
             'Adds an entry under Start Menu â†’ APex IMM â†’ IMM Diagnostic.')
        _chk(self.start_service,
             'Launch APex RCA immediately after installation',
             'The tool will be accessible right after install completes.')

        tk.Frame(inner, bg=BG_CARD, height=1).pack(fill='x', pady=16)
        tk.Label(
            inner,
            text=(
                'The application has been installed successfully.'
            ),
            font=FONT_SMALL, bg=BG_DARK, fg=TEXT_DIM, anchor='w', justify='left',
        ).pack(fill='x')

        return f

    # ------------------------------------------------------------------
    # Step 4 â€” Progress
    # ------------------------------------------------------------------
    def _make_step_progress(self) -> tk.Frame:
        f = tk.Frame(self.body, bg=BG_DARK)
        tk.Frame(f, bg=ACCENT, width=4).pack(side='left', fill='y')
        inner = tk.Frame(f, bg=BG_DARK)
        inner.pack(side='left', fill='both', expand=True, padx=36, pady=30)

        self._prog_title = tk.Label(
            inner, text='Installingâ€¦',
            font=FONT_HEAD, bg=BG_DARK, fg=TEXT_WHITE, anchor='w',
        )
        self._prog_title.pack(fill='x')

        self._prog_status = tk.Label(
            inner, text='Preparingâ€¦',
            font=FONT_BODY, bg=BG_DARK, fg=TEXT_GREY, anchor='w',
        )
        self._prog_status.pack(fill='x', pady=(6, 14))

        self._prog_bar = ttk.Progressbar(
            inner, length=560, mode='determinate',
        )
        style = ttk.Style()
        style.theme_use('default')
        style.configure('red.Horizontal.TProgressbar',
                        background=ACCENT, troughcolor=BG_PANEL, borderwidth=0)
        self._prog_bar.configure(style='red.Horizontal.TProgressbar')
        self._prog_bar.pack(fill='x', pady=(0, 6))

        self._prog_pct = tk.Label(
            inner, text='0%',
            font=FONT_SMALL, bg=BG_DARK, fg=TEXT_DIM, anchor='e',
        )
        self._prog_pct.pack(fill='x')

        self._prog_log = tk.Text(
            inner, height=8,
            bg=BG_PANEL, fg=TEXT_GREY, font=('Consolas', 9),
            relief='flat', state='disabled', wrap='word',
        )
        self._prog_log.pack(fill='both', expand=True, pady=(14, 0))

        return f

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _show_step(self, idx: int):
        for s in self.steps:
            s.pack_forget()
        self.steps[idx].pack(fill='both', expand=True)
        self.current_step = idx

        self.btn_back.config(state='normal' if idx > 0 else 'disabled')

        if idx == 0:
            self.btn_next.config(text='Next  â€º', state='normal', command=self._on_next)
        elif idx == 2:
            self.btn_next.config(text='Install', state='normal', command=self._on_next)
        elif idx == 3:
            self.btn_next.config(text='Finish', state='disabled', command=self.destroy)
            self.btn_back.config(state='disabled')
            self.btn_cancel.config(state='disabled')
        else:
            self.btn_next.config(text='Next  â€º', state='normal', command=self._on_next)

    def _on_next(self):
        if self.current_step == 1:
            d = self.install_dir.get().strip()
            if not d:
                messagebox.showerror('Invalid Path', 'Please choose an installation directory.')
                return
        if self.current_step < 3:
            self._show_step(self.current_step + 1)
        if self.current_step == 3:
            threading.Thread(target=self._run_install, daemon=True).start()

    def _on_back(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _on_cancel(self):
        if messagebox.askyesno('Cancel Installation',
                                'Are you sure you want to cancel the setup?'):
            self.destroy()

    # ------------------------------------------------------------------
    # Installation Logic
    # ------------------------------------------------------------------
    def _log(self, msg: str):
        self._prog_log.config(state='normal')
        self._prog_log.insert('end', msg + '\n')
        self._prog_log.see('end')
        self._prog_log.config(state='disabled')

    def _set_progress(self, pct: int, status: str):
        self._prog_bar['value'] = pct
        self._prog_pct.config(text=f'{pct}%')
        self._prog_status.config(text=status)
        self.update_idletasks()

    def _run_install(self):
        install_dir = self.install_dir.get().strip()
        try:
            self._do_install(install_dir)
        except Exception as exc:
            self._log(f'\n[ERROR] Installation failed: {exc}')
            self._prog_title.config(text='Installation Failed', fg='#ff4444')
            self.btn_cancel.config(state='normal', text='Close')
            messagebox.showerror('Installation Failed', str(exc))

    def _do_install(self, install_dir: str):
        # ---- Step 1: Create directory --------------------------------
        self._set_progress(5, 'Creating installation directoryâ€¦')
        self._log(f'Installing to: {install_dir}')
        os.makedirs(install_dir, exist_ok=True)
        os.makedirs(os.path.join(install_dir, 'logs'), exist_ok=True)
        
        self._log('  Copying Enterprise Documentation â€¦')
        help_src = _res('Help')
        if os.path.exists(help_src):
            shutil.copytree(help_src, os.path.join(install_dir, 'Help'), dirs_exist_ok=True)
        
        for doc in ['README.md', 'release_notes.md']:
            doc_src = _res(doc)
            if not os.path.exists(doc_src):
                doc_src = _res(os.path.join('docs', doc)) if doc == 'release_notes.md' else doc_src
            if os.path.exists(doc_src):
                shutil.copy2(doc_src, install_dir)

        # ---- Step 2: Copy application files --------------------------
        self._set_progress(15, 'Copying application filesâ€¦')
        
        # Copy the bundled application executable to the target folder
        self._log('  Copying APex_RCA_Core.exe â€¦')
        exe_dst = os.path.join(install_dir, 'APex_RCA_Core.exe')
        
        # The app is bundled in the installer's MEIPASS directory
        bundled_exe = _res('APex_RCA_Core.exe')
        if not os.path.exists(bundled_exe):
            # Fallback in case of case-sensitivity differences
            bundled_exe = _res('APex_RCA_Core.exe')
            
        shutil.copy2(bundled_exe, exe_dst)

        # Write installed.tag marker file
        try:
            tag_path = os.path.join(install_dir, 'installed.tag')
            with open(tag_path, 'w') as fh:
                fh.write('installed')
            self._log('  Created installation marker tag.')
        except Exception as exc:
            self._log(f'  [WARN] Failed to write installation marker tag: {exc}')

        self._log('  Copying brand assets â€¦')
        logo_src = _res(os.path.join('frontend', 'assets', 'ApplicationIcon.ico'))
        logo_dst = os.path.join(install_dir, 'ApplicationIcon.ico')
        if os.path.exists(logo_src):
            shutil.copy2(logo_src, logo_dst)

        # ---- Step 3: Grant folder permissions via icacls -------------
        self._set_progress(35, 'Granting folder write permissionsâ€¦')
        self._log('  Setting folder permissions for Users groupâ€¦')
        try:
            # Grant modify access to Users recursively
            cmd = f'icacls "{install_dir}" /grant Users:(OI)(CI)M /T'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self._log('  Write permissions granted to Users group successfully.')
            else:
                self._log(f'  [WARN] Folder permission setup warning: {result.stderr.strip()}')
        except Exception as exc:
            self._log(f'  [WARN] Folder permission exception: {exc}')

        # ---- Step 4: Write uninstaller --------------------------------
        self._set_progress(45, 'Writing uninstallerâ€¦')
        self._write_uninstaller(install_dir)

        # ---- Step 5: Registry (Add/Remove Programs) ------------------
        self._set_progress(55, 'Registering with Windowsâ€¦')
        self._register_uninstall(install_dir)

        # ---- Step 6: Register Windows Service -------------------------
        self._set_progress(65, 'Registering Windows Serviceâ€¦')
        self._log(f'  Registering service: {SERVICE_NAME}')
        

        # ---- Step 7: Start service ------------------------------------
        if self.start_service.get():
            self._set_progress(80, 'Starting serviceâ€¦')
            self._log('  Starting serviceâ€¦')
            self._launch_app(install_dir)

        # ---- Step 8: Desktop shortcut ---------------------------------
        if self.create_desktop.get():
            self._set_progress(88, 'Creating desktop shortcutâ€¦')
            self._log('  Creating desktop shortcutâ€¦')

            self._create_shortcut(
                os.path.join(os.path.expanduser('~'), 'Desktop', f'{PRODUCT_NAME}.lnk'),
                install_dir,
            )


        # ---- Step 9: Start Menu entry ---------------------------------
        if self.create_startmenu.get():
            self._set_progress(95, 'Creating Start Menu entryâ€¦')
            self._log('  Creating Start Menu entryâ€¦')
            sm_dir = os.path.join(
                os.environ.get('ALLUSERSPROFILE', r'C:\ProgramData'),
                'Microsoft', 'Windows', 'Start Menu', 'Programs',
                'APex IMM',
            )
            os.makedirs(sm_dir, exist_ok=True)
            self._create_shortcut(
                os.path.join(sm_dir, f'{PRODUCT_NAME}.lnk'),
                install_dir,
            )
            
            help_path = os.path.join(install_dir, 'Help', 'html', 'How_To_Guide.html')
            if os.path.exists(help_path):
                self._create_shortcut(
                    os.path.join(sm_dir, f'{PRODUCT_NAME} Help.lnk'),
                    install_dir,
                    target_path=help_path,
                    arguments=''
                )

        # ---- Done ----------------------------------------------------
        self._set_progress(100, 'Installation complete!')
        self._log('\nâœ”  Installation completed successfully.')
        self._log(f'   The tool is running at: http://localhost:8080')
        self._prog_title.config(text='Installation Complete', fg='#4ade80')
        self.btn_next.config(text='Finish', state='normal', command=self.destroy)

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------
    def _write_uninstaller(self, install_dir: str):
        """Write a .bat uninstaller into the install directory."""
        bat = os.path.join(install_dir, 'Uninstall.bat')
        content = f"""@echo off
cd /d "%~dp0"
start "" APex_RCA_Core.exe --uninstall
"""
        with open(bat, 'w') as fh:
            fh.write(content)
        self._log('  Uninstaller written.')

    def _register_uninstall(self, install_dir: str):
        """Add the product to Windows Add/Remove Programs."""
        try:
            key_path = (
                r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\\'
                + SERVICE_NAME
            )
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                winreg.SetValueEx(key, 'DisplayName',    0, winreg.REG_SZ, PRODUCT_NAME)
                winreg.SetValueEx(key, 'DisplayVersion', 0, winreg.REG_SZ, VERSION)
                winreg.SetValueEx(key, 'Publisher',      0, winreg.REG_SZ,
                                  'APex IMM Enterprises Ltd.')
                winreg.SetValueEx(key, 'InstallLocation',0, winreg.REG_SZ, install_dir)
                winreg.SetValueEx(key, 'UninstallString',0, winreg.REG_SZ,
                                  f'"{os.path.join(install_dir, "APex_RCA_Core.exe")}" --uninstall')
                winreg.SetValueEx(key, 'NoModify',       0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, 'NoRepair',       0, winreg.REG_DWORD, 1)

                logo_path = os.path.join(install_dir, 'ApplicationIcon.ico')
                if os.path.exists(logo_path):
                    winreg.SetValueEx(key, 'DisplayIcon', 0, winreg.REG_SZ, logo_path)
            self._log('  Registered in Add/Remove Programs.')
        except Exception as exc:
            self._log(f'  [WARN] Could not register uninstall entry: {exc}')

    def _launch_app(self, install_dir):
        try:
            subprocess.Popen([os.path.join(install_dir, 'APex_RCA_Core.exe')], cwd=install_dir, creationflags=subprocess.CREATE_NO_WINDOW)
            self._log('  Application launched.')
        except Exception as exc:
            self._log(f'  [WARN] Could not launch app: {exc}')

    def _create_shortcut(self, link_path: str, install_dir: str, target_path: str = None, arguments: str = ''):
        """Create a .lnk shortcut pointing to the installed executable or document."""
        try:
            import pythoncom
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell', pythoncom.CoInitialize())
            shortcut = shell.CreateShortCut(link_path)
            
            exe_path = target_path if target_path else os.path.join(install_dir, 'APex_RCA_Core.exe')
            shortcut.Targetpath = exe_path
            shortcut.Arguments = arguments
            shortcut.WorkingDirectory = install_dir
            shortcut.Description = f'Launch {PRODUCT_NAME}'

            logo_path = os.path.join(install_dir, 'ApplicationIcon.ico')
            if os.path.exists(logo_path):
                shortcut.IconLocation = f"{logo_path},0"

            shortcut.save()
            self._log(f'  Shortcut created: {link_path}')
        except Exception as exc:
            self._log(f'  [WARN] Shortcut creation failed: {exc}')


# ---------------------------------------------------------------------------
# Setup GUI Entry Point
# ---------------------------------------------------------------------------
def _is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_installer():
    if not _is_admin():
        # Re-launch with UAC elevation
        ctypes.windll.shell32.ShellExecuteW(
            None, 'runas', sys.executable, ' '.join(sys.argv), None, 1
        )
        sys.exit()

    app = InstallerApp()
    app.mainloop()

if __name__ == '__main__':
    run_installer()


