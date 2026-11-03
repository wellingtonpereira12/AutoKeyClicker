"""
Auto Key Clicker - Multi-Screen & Multi-Key Background Game Auto-Clicker
Interface gráfica moderna dark mode compacta, com suporte a ABAS (Tabs) e MODO MINI (HUD).
"""
import tkinter as tk
from tkinter import ttk, messagebox
import time
import os
import sys
import json
import ctypes

from window_manager import list_user_windows, is_window_alive
from key_sender import KEY_MAP, resolve_key
from clicker_engine import ClickerEngine

# Enable DPI Awareness on Windows
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Dark theme palette
BG_DARK = "#18191c"
BG_CARD = "#232428"
BG_BOX = "#2b2d31"
BG_INPUT = "#383a40"
FG_WHITE = "#f2f3f5"
FG_MUTED = "#949ba4"
ACCENT_BLUE = "#5865f2"
ACCENT_GREEN = "#23a55a"
ACCENT_RED = "#da373c"
BORDER_COLOR = "#3f4147"

COMMON_KEYS = [
    "F10", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F11", "F12",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    "SPACE", "ENTER", "TAB", "ESC",
    "Q", "W", "E", "R", "T", "Y",
    "A", "S", "D", "F", "G", "H",
    "Z", "X", "C", "V", "B",
    "MOUSE_LEFT", "MOUSE_RIGHT"
]

AVAILABLE_HOTKEYS = [
    "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    "F1", "F2", "F3", "F4", "F5",
    "PAUSE", "INSERT", "HOME", "END", "PAGE_UP", "PAGE_DOWN", "DELETE",
    "SPACE", "TAB", "`",
    "Q", "W", "E", "R", "T", "Y",
    "A", "S", "D", "F", "G", "H",
    "Z", "X", "C", "V", "B",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"
]

def get_setups_file_path():
    """Gets the persistent path for setups.json beside the executable or in AppData."""
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    local_path = os.path.join(app_dir, "setups.json")
    try:
        test_file = os.path.join(app_dir, ".test_write")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return local_path
    except Exception:
        appdata = os.path.expandvars(r"%APPDATA%\AutoKeyClicker")
        os.makedirs(appdata, exist_ok=True)
        return os.path.join(appdata, "setups.json")

def get_app_icon_path():
    """Gets the path to app_icon.ico if present in executable or source folder."""
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    ico = os.path.join(base_dir, "app_icon.ico")
    if os.path.exists(ico):
        return ico
    if getattr(sys, 'frozen', False):
        beside = os.path.join(os.path.dirname(sys.executable), "app_icon.ico")
        if os.path.exists(beside):
            return beside
    return None

class AutoKeyClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Key Clicker")
        self.normal_width = 560
        self.normal_height = 540
        self.root.geometry(f"{self.normal_width}x{self.normal_height}")
        self.root.minsize(480, 480)
        self.root.configure(bg=BG_DARK)

        # Apply application icon
        icon_path = get_app_icon_path()
        if icon_path:
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Apply Windows 10/11 Dark Titlebar & Dark Border Frame
        self._apply_dark_window_frame()

        self.is_mini_mode = False

        # Engine instance
        self.engine = ClickerEngine(
            on_tick=self._on_tick_callback,
            on_state_change=self._on_state_change_callback,
            on_hotkey_start=self._on_hotkey_toggle_callback,
            on_hotkey_stop=self._on_hotkey_toggle_callback,
            on_hotkey_toggle=self._on_hotkey_toggle_callback
        )

        self.windows_cache = []
        self.selected_window = None
        self.key_cards = []
        self.mini_key_cards = []
        self.all_setups = {}
        self._last_gui_update = 0.0

        self._apply_styles()
        self._build_ui()
        self.load_setups_from_disk()
        self.refresh_windows_list()

        # Start cooldown animated tubes loop
        self._animate_tubinhos()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_dark_window_frame(self):
        """Forces Windows 10/11 to render the titlebar and window border in dark mode matching FakeDC."""
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if hwnd == 0:
                hwnd = self.root.winfo_id()

            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 10 20H1+ and Windows 11)
            # DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19 (Windows 10 1809-1909)
            val = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))

            # Windows 11 custom title bar colors:
            # DWMWA_CAPTION_COLOR = 35 (#111214 -> 0x141211)
            # DWMWA_TEXT_COLOR = 36 (#f2f3f5 -> 0xf5f3f2)
            # DWMWA_BORDER_COLOR = 34 (#3f4147 -> 0x47413f)
            cap_color = ctypes.c_int(0x141211)
            text_color = ctypes.c_int(0xf5f3f2)
            border_color = ctypes.c_int(0x47413f)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(cap_color), ctypes.sizeof(cap_color))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text_color), ctypes.sizeof(text_color))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_color), ctypes.sizeof(border_color))

            # Force redraw of frame
            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER)
        except Exception:
            pass

    def _apply_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Notebook (Tabs) styling
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=BG_CARD,
            foreground=FG_MUTED,
            padding=[14, 6],
            font=("Segoe UI", 9, "bold"),
            borderwidth=0
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", ACCENT_BLUE)],
            foreground=[("selected", FG_WHITE)]
        )

        # Combobox styling
        style.configure(
            "TCombobox",
            fieldbackground=BG_INPUT,
            background=BG_CARD,
            foreground=FG_WHITE,
            darkcolor=BORDER_COLOR,
            lightcolor=BORDER_COLOR,
            bordercolor=BORDER_COLOR,
            arrowcolor=FG_WHITE
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", BG_INPUT)],
            selectbackground=[("readonly", ACCENT_BLUE)],
            selectforeground=[("readonly", FG_WHITE)]
        )

        # Scrollbar styling
        style.configure(
            "Vertical.TScrollbar",
            gripcount=0,
            background=BG_INPUT,
            darkcolor=BG_DARK,
            lightcolor=BG_DARK,
            troughcolor=BG_DARK,
            bordercolor=BG_DARK,
            arrowcolor=FG_MUTED
        )

    def _build_ui(self):
        # ----------------- TOP HEADER -----------------
        self.header_frame = tk.Frame(self.root, bg=BG_DARK, padx=12, pady=6)
        self.header_frame.pack(fill="x")

        self.title_lbl = tk.Label(
            self.header_frame,
            text="⚡ AUTO KEY CLICKER",
            font=("Segoe UI", 12, "bold"),
            bg=BG_DARK,
            fg=FG_WHITE
        )
        self.title_lbl.pack(side="left")

        # Top Right Controls
        self.btn_mini = tk.Button(
            self.header_frame,
            text="🗗 Modo Mini",
            command=self.toggle_mini_mode,
            font=("Segoe UI", 8, "bold"),
            bg=BG_INPUT,
            fg=FG_WHITE,
            activebackground=ACCENT_BLUE,
            activeforeground=FG_WHITE,
            relief="flat",
            padx=8,
            pady=1,
            cursor="hand2"
        )
        self.btn_mini.pack(side="right", padx=(6, 0))

        self.ontop_var = tk.BooleanVar(value=True)
        self.cb_ontop = tk.Checkbutton(
            self.header_frame,
            text="📌 No Topo",
            variable=self.ontop_var,
            command=self._toggle_always_on_top,
            bg=BG_DARK,
            fg=FG_WHITE,
            selectcolor=BG_INPUT,
            activebackground=BG_DARK,
            activeforeground=FG_WHITE,
            font=("Segoe UI", 8)
        )
        self.cb_ontop.pack(side="right")
        self.root.wm_attributes("-topmost", True)

        # ----------------- BODY CONTAINER (Hides in Mini Mode) -----------------
        self.body_container = tk.Frame(self.root, bg=BG_DARK, padx=12)
        self.body_container.pack(fill="both", expand=True)

        # ----------------- MINI HUD CONTAINER (Shown ONLY in Mini Mode) -----------------
        self.mini_hud_frame = tk.Frame(self.root, bg=BG_DARK, padx=10, pady=2)

        # Target Window Bar
        win_bar = tk.Frame(self.body_container, bg=BG_CARD, padx=8, pady=4, bd=1, relief="solid")
        win_bar.pack(fill="x", pady=(0, 6))

        tk.Label(win_bar, text="🎯 Jogo:", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=FG_WHITE).pack(side="left", padx=(0, 6))

        self.window_combo = ttk.Combobox(
            win_bar,
            state="readonly",
            font=("Segoe UI", 9),
            postcommand=self._on_combo_dropdown_open
        )
        self.window_combo.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.window_combo.bind("<<ComboboxSelected>>", self._on_window_selected)

        btn_refresh = tk.Button(
            win_bar,
            text="🔄",
            command=self.refresh_windows_list,
            font=("Segoe UI", 9, "bold"),
            bg=BG_INPUT,
            fg=FG_WHITE,
            activebackground=ACCENT_BLUE,
            activeforeground=FG_WHITE,
            relief="flat",
            padx=6,
            cursor="hand2"
        )
        btn_refresh.pack(side="right")

        # ----------------- TABS NOTEBOOK -----------------
        self.notebook = ttk.Notebook(self.body_container)
        self.notebook.pack(fill="both", expand=True)

        # TAB 1: Teclas & Setups
        self.tab_keys = tk.Frame(self.notebook, bg=BG_DARK, padx=6, pady=6)
        self.notebook.add(self.tab_keys, text="  ⌨️ Teclas & Setups  ")

        # TAB 2: Opções & Multitelas
        self.tab_opts = tk.Frame(self.notebook, bg=BG_DARK, padx=8, pady=8)
        self.notebook.add(self.tab_opts, text="  ⚙️ Opções & Modo  ")

        self._build_tab_keys()
        self._build_tab_opts()

        # ----------------- BOTTOM DOCKED BAR (Always Visible) -----------------
        self.bottom_frame = tk.Frame(self.root, bg=BG_DARK, padx=12, pady=6)
        self.bottom_frame.pack(fill="x", side="bottom")

        # Status & Stats row
        stat_row = tk.Frame(self.bottom_frame, bg=BG_DARK)
        stat_row.pack(fill="x", pady=(0, 4))

        self.status_badge = tk.Label(
            stat_row,
            text="● PARADO",
            font=("Segoe UI", 9, "bold"),
            bg=BG_INPUT,
            fg=ACCENT_RED,
            padx=8,
            pady=2
        )
        self.status_badge.pack(side="left")

        self.stats_lbl = tk.Label(
            stat_row,
            text="Cliques: 0  |  00:00",
            font=("Segoe UI", 9, "bold"),
            bg=BG_DARK,
            fg=FG_WHITE
        )
        self.stats_lbl.pack(side="right")

        # Action Buttons row
        btn_row = tk.Frame(self.bottom_frame, bg=BG_DARK)
        btn_row.pack(fill="x")

        self.btn_start = tk.Button(
            btn_row,
            text="▶ INICIAR (F6)",
            command=self.start_clicker,
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT_GREEN,
            fg=FG_WHITE,
            activebackground="#1b8547",
            activeforeground=FG_WHITE,
            relief="flat",
            height=1,
            cursor="hand2"
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_stop = tk.Button(
            btn_row,
            text="⏹ PARAR (F6)",
            command=self.stop_clicker,
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT_RED,
            fg=FG_WHITE,
            activebackground="#a8282c",
            activeforeground=FG_WHITE,
            relief="flat",
            height=1,
            state="disabled",
            cursor="hand2"
        )
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=(4, 0))

    def _build_tab_keys(self):
        # Setups Row
        setup_box = tk.Frame(self.tab_keys, bg=BG_CARD, padx=8, pady=5, bd=1, relief="solid")
        setup_box.pack(fill="x", pady=(0, 6))

        # Row 1: Save setup
        r1 = tk.Frame(setup_box, bg=BG_CARD)
        r1.pack(fill="x", pady=(0, 3))

        tk.Label(r1, text="Nome:", font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=FG_MUTED).pack(side="left", padx=(0, 4))
        self.setup_name_var = tk.StringVar(value="Meu Setup 1")
        self.setup_name_entry = tk.Entry(
            r1, textvariable=self.setup_name_var, font=("Segoe UI", 8),
            bg=BG_INPUT, fg=FG_WHITE, insertbackground=FG_WHITE, relief="flat"
        )
        self.setup_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=2)

        btn_save = tk.Button(
            r1, text="💾 Salvar", command=self.save_current_setup,
            font=("Segoe UI", 8, "bold"), bg=ACCENT_BLUE, fg=FG_WHITE,
            relief="flat", padx=8, cursor="hand2"
        )
        btn_save.pack(side="right")

        # Row 2: Select / Load setup
        r2 = tk.Frame(setup_box, bg=BG_CARD)
        r2.pack(fill="x")

        tk.Label(r2, text="Perfil:", font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=FG_MUTED).pack(side="left", padx=(0, 6))
        self.saved_setups_combo = ttk.Combobox(r2, state="readonly", font=("Segoe UI", 8))
        self.saved_setups_combo.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.saved_setups_combo.bind("<<ComboboxSelected>>", self._on_setup_combo_selected)

        btn_del = tk.Button(
            r2, text="🗑️", command=self.delete_selected_setup,
            font=("Segoe UI", 8, "bold"), bg=BG_INPUT, fg=ACCENT_RED,
            relief="flat", padx=6, cursor="hand2"
        )
        btn_del.pack(side="right")

        # Keys Header & Add Button
        kh_row = tk.Frame(self.tab_keys, bg=BG_DARK, pady=2)
        kh_row.pack(fill="x")

        tk.Label(
            kh_row, text="Quadradinhos de Teclas (Arraste para reordenar disparo):",
            font=("Segoe UI", 9, "bold"), bg=BG_DARK, fg=FG_WHITE
        ).pack(side="left")

        btn_add = tk.Button(
            kh_row, text="➕ Adicionar Tecla",
            command=self._on_click_add_key,
            font=("Segoe UI", 8, "bold"), bg=ACCENT_GREEN, fg=FG_WHITE,
            relief="flat", padx=8, pady=1, cursor="hand2"
        )
        btn_add.pack(side="right")

        # Scrollable Cards Area
        cards_outer = tk.Frame(self.tab_keys, bg=BG_CARD, bd=1, relief="solid")
        cards_outer.pack(fill="both", expand=True)

        self.cards_canvas = tk.Canvas(cards_outer, bg=BG_CARD, highlightthickness=0)
        self.cards_scrollbar = ttk.Scrollbar(cards_outer, orient="vertical", command=self.cards_canvas.yview)
        
        self.cards_inner_frame = tk.Frame(self.cards_canvas, bg=BG_CARD, padx=4, pady=4)
        self.cards_window = self.cards_canvas.create_window((0, 0), window=self.cards_inner_frame, anchor="nw")
        
        self.cards_canvas.configure(yscrollcommand=self.cards_scrollbar.set)
        self.cards_canvas.pack(side="left", fill="both", expand=True)
        self.cards_scrollbar.pack(side="right", fill="y")

        self.cards_inner_frame.bind(
            "<Configure>",
            lambda e: self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all"))
        )
        self.cards_canvas.bind(
            "<Configure>",
            lambda e: self.cards_canvas.itemconfig(self.cards_window, width=e.width)
        )

        self.cards_canvas.bind("<Enter>", self._bind_mousewheel)
        self.cards_canvas.bind("<Leave>", self._unbind_mousewheel)

    def _build_tab_opts(self):
        # Card 1: Modo de Envio
        m_card = self._create_card(self.tab_opts, "Modo de Funcionamento (Multitelas)")
        self.mode_var = tk.StringVar(value="background")

        rb_bg = tk.Radiobutton(
            m_card,
            text="Modo Segundo Plano (PostMessage) — Recomendado\n(NÃO puxa a tela nem rouba foco: você mexe em outros programas livremente)",
            variable=self.mode_var, value="background", justify="left",
            bg=BG_CARD, fg=FG_WHITE, selectcolor=BG_INPUT,
            activebackground=BG_CARD, activeforeground=FG_WHITE, font=("Segoe UI", 8)
        )
        rb_bg.pack(anchor="w", pady=2)

        rb_fg = tk.Radiobutton(
            m_card,
            text="Modo Foco Ativo (SendInput / DirectInput)\n(Puxa a tela do jogo para a frente a cada clique para enviar scancodes diretos)",
            variable=self.mode_var, value="foreground", justify="left",
            bg=BG_CARD, fg=FG_WHITE, selectcolor=BG_INPUT,
            activebackground=BG_CARD, activeforeground=FG_WHITE, font=("Segoe UI", 8)
        )
        rb_fg.pack(anchor="w", pady=2)

        # Card 2: Proteções & Atalhos
        p_card = self._create_card(self.tab_opts, "Proteções do Jogo & Atalhos")

        self.jitter_var = tk.BooleanVar(value=True)
        cb_jitter = tk.Checkbutton(
            p_card,
            text="🛡️ Anti-Ban: Variação humana de intervalo (±25ms)",
            variable=self.jitter_var,
            bg=BG_CARD, fg=FG_WHITE, selectcolor=BG_INPUT,
            activebackground=BG_CARD, activeforeground=FG_WHITE, font=("Segoe UI", 8)
        )
        cb_jitter.pack(anchor="w", pady=2)

        col_frame = tk.Frame(p_card, bg=BG_CARD)
        col_frame.pack(fill="x", pady=2)

        tk.Label(
            col_frame,
            text="🛡️ Anti-Colisão: Pausa de",
            font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=ACCENT_GREEN
        ).pack(side="left")

        self.collision_delay_var = tk.StringVar(value="3.0")
        col_combo = ttk.Combobox(
            col_frame,
            textvariable=self.collision_delay_var,
            values=["1.0", "2.0", "3.0", "4.0", "5.0"],
            width=4,
            font=("Segoe UI", 8, "bold")
        )
        col_combo.pack(side="left", padx=4)

        tk.Label(
            col_frame,
            text="segundos se teclas forem apertar juntas",
            font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=ACCENT_GREEN
        ).pack(side="left")

        # Configuração do Botão Único de Iniciar/Parar (Toggle)
        hk_frame = tk.Frame(p_card, bg=BG_CARD)
        hk_frame.pack(fill="x", pady=(8, 2))

        tk.Label(
            hk_frame,
            text="⌨️ Tecla Única (Iniciar / Parar):",
            font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=FG_WHITE
        ).pack(side="left")

        self.hotkey_var = tk.StringVar(value="F6")
        self.hotkey_combo = ttk.Combobox(
            hk_frame,
            textvariable=self.hotkey_var,
            values=AVAILABLE_HOTKEYS,
            width=7,
            state="readonly",
            font=("Segoe UI", 8, "bold")
        )
        self.hotkey_combo.pack(side="left", padx=6)
        self.hotkey_combo.bind("<<ComboboxSelected>>", self._on_hotkey_changed)

        lbl_hk = tk.Label(
            p_card,
            text="💡 Um único botão para as duas funções: se apertar inicia, se apertar de novo para.",
            font=("Segoe UI", 7, "italic"), bg=BG_CARD, fg=ACCENT_BLUE
        )
        lbl_hk.pack(anchor="w", pady=(1, 4))

    def _create_card(self, parent, title):
        card = tk.LabelFrame(
            parent,
            text=f"  {title}  ",
            bg=BG_CARD,
            fg=FG_WHITE,
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=6,
            relief="solid",
            bd=1
        )
        card.pack(fill="x", pady=4)
        return card

    # ----------------- MINI MODE / HUD TOGGLE -----------------
    def _build_mini_cards(self):
        """Constructs compact, read-only visual cards with cooldown tubinhos for Mini Mode."""
        for widget in self.mini_hud_frame.winfo_children():
            widget.destroy()
        self.mini_key_cards.clear()

        # Get current configured keys from key_cards
        configured_cards = []
        for idx, cd in enumerate(self.key_cards):
            k = cd['key_combo'].get().strip()
            if not k:
                continue
            t = cd['time_ent'].get().strip()
            u = cd['unit_combo'].get().strip()
            time_str = f"{t}{u}" if t else "500ms"
            configured_cards.append({
                'key': k,
                'time_str': time_str,
                'card_index': idx
            })

        if not configured_cards:
            lbl_empty = tk.Label(
                self.mini_hud_frame,
                text="Nenhuma tecla configurada",
                font=("Segoe UI", 8, "italic"),
                bg=BG_DARK,
                fg=FG_MUTED
            )
            lbl_empty.pack(pady=4)
            return

        total = len(configured_cards)
        cols = 3 if total in (5, 6) else (4 if total > 4 else total)
        for i, item in enumerate(configured_cards):
            row = i // cols
            col = i % cols

            box = tk.Frame(
                self.mini_hud_frame,
                bg=BG_BOX,
                bd=1,
                relief="solid",
                padx=6,
                pady=3
            )
            box.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
            self.mini_hud_frame.grid_columnconfigure(col, weight=1)

            # Top label row: Key on left (bold), Timer on right (muted)
            top_lbl = tk.Frame(box, bg=BG_BOX)
            top_lbl.pack(fill="x")

            k_lbl = tk.Label(
                top_lbl,
                text=item['key'],
                font=("Segoe UI", 9, "bold"),
                bg=BG_BOX,
                fg=FG_WHITE
            )
            k_lbl.pack(side="left")

            t_lbl = tk.Label(
                top_lbl,
                text=item['time_str'],
                font=("Segoe UI", 8),
                bg=BG_BOX,
                fg=FG_MUTED
            )
            t_lbl.pack(side="right")

            # Cooldown Tubinho
            c = tk.Canvas(
                box,
                height=7,
                bg="#18191c",
                highlightthickness=1,
                highlightbackground="#3f4147",
                bd=0
            )
            c.pack(fill="x", pady=(2, 0))
            bar_id = c.create_rectangle(0, 0, 0, 7, fill=ACCENT_BLUE, width=0)

            self.mini_key_cards.append({
                'frame': box,
                'tube_canvas': c,
                'bar_id': bar_id,
                'card_index': item['card_index']
            })

    def toggle_mini_mode(self):
        """Switches between full window and compact floating mini HUD with visual key cards."""
        self.is_mini_mode = not self.is_mini_mode

        if self.is_mini_mode:
            # Save normal geometry and switch to compact
            self.normal_width = max(500, self.root.winfo_width())
            self.normal_height = max(480, self.root.winfo_height())
            
            # Hide heavy body container
            self.body_container.pack_forget()

            # Build and display mini visual cards
            self._build_mini_cards()
            self.mini_hud_frame.pack(fill="x", expand=True, padx=8, pady=2, before=self.bottom_frame)

            # Change mini button appearance
            self.btn_mini.config(text="⚙️ Expandir", bg=ACCENT_BLUE)
            
            # Update title to show target executable if available
            target_str = f" [{self.selected_window['exe']}]" if self.selected_window else ""
            self.title_lbl.config(text=f"⚡ AutoClicker{target_str}", font=("Segoe UI", 10, "bold"))

            # Update status badge text format for compact HUD
            if self.engine.is_running:
                active_count = len(self.mini_key_cards)
                self.status_badge.config(text=f"● ATIVO ({active_count}T)")
            
            # Dynamic height depending on number of rows of keys
            total_keys = len(self.mini_key_cards)
            if total_keys <= 4:
                req_h = 150
            else:
                req_h = 185
            self.root.minsize(360, req_h)
            self.root.geometry(f"390x{req_h}")
        else:
            # Hide mini HUD
            self.mini_hud_frame.pack_forget()
            for widget in self.mini_hud_frame.winfo_children():
                widget.destroy()
            self.mini_key_cards.clear()

            # Restore normal window controls
            self.btn_mini.config(text="🗗 Modo Mini", bg=BG_INPUT)
            self.title_lbl.config(text="⚡ AUTO KEY CLICKER", font=("Segoe UI", 12, "bold"))

            # Re-pack body container above bottom frame
            self.body_container.pack(fill="both", expand=True, before=self.bottom_frame)

            # Restore normal status badge text format
            if self.engine.is_running:
                target_exe = self.selected_window['exe'] if self.selected_window else 'Jogo'
                active_count = len(self._get_configured_keys())
                self.status_badge.config(text=f"● CLICANDO ({active_count} TECLAS) EM {target_exe}")

            self.root.minsize(480, 480)
            self.root.geometry(f"{self.normal_width}x{self.normal_height}")

    def _bind_mousewheel(self, event):
        self.cards_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.cards_canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.cards_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_click_add_key(self):
        if self.engine.is_running:
            messagebox.showinfo("Aviso", "Pare o clicker antes de adicionar novas teclas!")
            return
        self.add_key_card(default_key="F1", default_time="5", default_unit="s")

    # ----------------- DYNAMIC KEY CARDS ("QUADRADINHOS") -----------------
    def add_key_card(self, default_key="F10", default_time="5", default_unit="s"):
        """Creates an intuitive, clean 'quadradinho' card with key selector on top, timer, and cooldown tube underneath."""
        card_box = tk.Frame(
            self.cards_inner_frame,
            bg=BG_BOX,
            bd=1,
            relief="solid",
            padx=6,
            pady=4,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
            highlightcolor=BORDER_COLOR
        )

        top_row = tk.Frame(card_box, bg=BG_BOX, cursor="fleur")
        top_row.pack(fill="x", pady=(0, 2))

        drag_grip = tk.Label(
            top_row,
            text="⠿",
            font=("Segoe UI", 9, "bold"),
            bg=BG_BOX,
            fg=FG_MUTED,
            cursor="fleur"
        )
        drag_grip.pack(side="left", padx=(0, 3))

        tag_lbl = tk.Label(
            top_row,
            text=f"Tecla #{len(self.key_cards) + 1}",
            font=("Segoe UI", 8, "bold"),
            bg=BG_BOX,
            fg=FG_MUTED,
            cursor="fleur"
        )
        tag_lbl.pack(side="left")

        btn_del = tk.Button(
            top_row,
            text="✕",
            font=("Segoe UI", 8, "bold"),
            bg=BG_BOX,
            fg=ACCENT_RED,
            activebackground=ACCENT_RED,
            activeforeground=FG_WHITE,
            relief="flat",
            bd=0,
            padx=4,
            pady=0,
            cursor="hand2"
        )
        btn_del.pack(side="right")

        key_combo = ttk.Combobox(
            card_box,
            values=COMMON_KEYS,
            font=("Segoe UI", 10, "bold"),
            width=6,
            justify="center"
        )
        key_combo.set(default_key)
        key_combo.pack(fill="x", pady=(1, 4))

        time_frame = tk.Frame(card_box, bg=BG_BOX)
        time_frame.pack(fill="x")

        time_ent = tk.Entry(
            time_frame,
            font=("Segoe UI", 9, "bold"),
            bg=BG_INPUT,
            fg=FG_WHITE,
            insertbackground=FG_WHITE,
            justify="center",
            width=4,
            relief="flat"
        )
        time_ent.insert(0, str(default_time))
        time_ent.pack(side="left", fill="x", expand=True, padx=(0, 2))

        unit_combo = ttk.Combobox(
            time_frame,
            values=["ms", "s"],
            state="readonly",
            font=("Segoe UI", 8, "bold"),
            width=3
        )
        unit_combo.set(default_unit)
        unit_combo.pack(side="right")

        # Cooldown Tube ("Tubinho") - animates as the timer elapses
        tube_frame = tk.Frame(card_box, bg=BG_BOX, pady=3, cursor="fleur")
        tube_frame.pack(fill="x")

        tube_canvas = tk.Canvas(
            tube_frame,
            height=8,
            bg="#18191c",
            highlightthickness=1,
            highlightbackground="#3f4147",
            bd=0
        )
        tube_canvas.pack(fill="x", expand=True)

        bar_id = tube_canvas.create_rectangle(0, 0, 0, 8, fill=ACCENT_BLUE, width=0)

        card_data = {
            'frame': card_box,
            'top_row': top_row,
            'drag_grip': drag_grip,
            'tag_lbl': tag_lbl,
            'btn_del': btn_del,
            'key_combo': key_combo,
            'time_ent': time_ent,
            'unit_combo': unit_combo,
            'tube_frame': tube_frame,
            'tube_canvas': tube_canvas,
            'bar_id': bar_id,
            'card_index': len(self.key_cards)
        }

        # Bind drag-and-drop to top row, drag grip, tag label, card frame and tube frame
        for w in (card_box, top_row, drag_grip, tag_lbl, tube_frame):
            w.bind("<ButtonPress-1>", lambda e, cd=card_data: self._on_card_drag_start(cd, e))
            w.bind("<B1-Motion>", lambda e, cd=card_data: self._on_card_drag_motion(cd, e))
            w.bind("<ButtonRelease-1>", lambda e, cd=card_data: self._on_card_drag_release(cd, e))

        btn_del.config(command=lambda cd=card_data: self.remove_key_card(cd))
        self.key_cards.append(card_data)
        self._reposition_cards()

    def _apply_drag_highlight(self, card_data, is_dragging):
        """Highlights the active dragged card visually with an accent border."""
        try:
            if is_dragging:
                card_data['frame'].config(
                    bg="#2d3139",
                    highlightthickness=2,
                    highlightbackground=ACCENT_BLUE,
                    highlightcolor=ACCENT_BLUE
                )
                card_data['top_row'].config(bg="#2d3139")
                card_data['drag_grip'].config(bg="#2d3139", fg=ACCENT_BLUE)
                card_data['tag_lbl'].config(bg="#2d3139", fg=FG_WHITE)
                if 'tube_frame' in card_data:
                    card_data['tube_frame'].config(bg="#2d3139")
            else:
                card_data['frame'].config(
                    bg=BG_BOX,
                    highlightthickness=1,
                    highlightbackground=BORDER_COLOR,
                    highlightcolor=BORDER_COLOR
                )
                card_data['top_row'].config(bg=BG_BOX)
                card_data['drag_grip'].config(bg=BG_BOX, fg=FG_MUTED)
                card_data['tag_lbl'].config(bg=BG_BOX, fg=FG_MUTED)
                if 'tube_frame' in card_data:
                    card_data['tube_frame'].config(bg=BG_BOX)
        except Exception:
            pass

    def _on_card_drag_start(self, card_data, event):
        """Initiates card dragging to rearrange execution order."""
        if self.engine.is_running:
            return
        self._drag_data = {
            'card': card_data,
            'start_x': event.x_root,
            'start_y': event.y_root,
            'moved': False
        }
        self._apply_drag_highlight(card_data, True)

    def _on_card_drag_motion(self, card_data, event):
        """Reorders cards live as the user drags across slots."""
        if self.engine.is_running or not hasattr(self, '_drag_data') or not self._drag_data:
            return
        if self._drag_data.get('card') != card_data:
            return

        mx = event.x_root
        my = event.y_root
        if abs(mx - self._drag_data['start_x']) > 4 or abs(my - self._drag_data['start_y']) > 4:
            self._drag_data['moved'] = True

        # Auto-scroll canvas if dragging near top or bottom
        try:
            cy = self.cards_canvas.winfo_rooty()
            ch = self.cards_canvas.winfo_height()
            if my < cy + 15:
                self.cards_canvas.yview_scroll(-1, "units")
            elif my > cy + ch - 15:
                self.cards_canvas.yview_scroll(1, "units")
        except Exception:
            pass

        # Identify target card under cursor
        src_idx = self.key_cards.index(card_data)
        target_idx = None
        for idx, other in enumerate(self.key_cards):
            if other == card_data:
                continue
            ox1 = other['frame'].winfo_rootx()
            oy1 = other['frame'].winfo_rooty()
            ox2 = ox1 + other['frame'].winfo_width()
            oy2 = oy1 + other['frame'].winfo_height()
            if ox1 <= mx <= ox2 and oy1 <= my <= oy2:
                target_idx = idx
                break

        # If not over a specific card, check if dragging past the end of the cards
        if target_idx is None and len(self.key_cards) > 1:
            try:
                last_card = self.key_cards[-1]
                if last_card != card_data:
                    last_y = last_card['frame'].winfo_rooty()
                    last_h = last_card['frame'].winfo_height()
                    if my > last_y + last_h:
                        target_idx = len(self.key_cards) - 1
                    elif my >= last_y:
                        last_x = last_card['frame'].winfo_rootx() + last_card['frame'].winfo_width()
                        if mx > last_x:
                            target_idx = len(self.key_cards) - 1
            except Exception:
                pass

        if target_idx is not None and target_idx != src_idx:
            self.key_cards.insert(target_idx, self.key_cards.pop(src_idx))
            self._reposition_cards()
            self._apply_drag_highlight(card_data, True)

    def _on_card_drag_release(self, card_data, event):
        """Finalizes card placement and restores normal card appearance."""
        if hasattr(self, '_drag_data') and self._drag_data:
            self._apply_drag_highlight(card_data, False)
            self._drag_data = None
            self._reposition_cards()

    def remove_key_card(self, card_data):
        if self.engine.is_running:
            messagebox.showinfo("Aviso", "Pare o clicker antes de remover teclas!")
            return
        if len(self.key_cards) <= 1:
            messagebox.showinfo("Aviso", "Você deve manter pelo menos uma tecla configurada!")
            return
        card_data['frame'].destroy()
        self.key_cards.remove(card_data)
        self._reposition_cards()

    def _reposition_cards(self):
        """Arranges cards in a clean 3-column grid and updates execution order labels."""
        for idx, cd in enumerate(self.key_cards):
            row = idx // 3
            col = idx % 3
            cd['card_index'] = idx
            cd['frame'].grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
            self.cards_inner_frame.grid_columnconfigure(col, weight=1)
            cd['tag_lbl'].config(text=f"Tecla #{idx + 1}")

    def _get_configured_keys(self):
        keys_list = []
        for idx, cd in enumerate(self.key_cards):
            k = cd['key_combo'].get().strip()
            if not k:
                continue

            try:
                raw_time = float(cd['time_ent'].get().strip().replace(',', '.'))
            except ValueError:
                raw_time = 500.0

            unit = cd['unit_combo'].get()
            if unit == "s":
                interval_ms = max(1, int(raw_time * 1000.0))
            else:
                interval_ms = max(1, int(raw_time))

            keys_list.append({
                'key': k,
                'interval_ms': interval_ms,
                'enabled': True,
                'card_index': idx
            })
        return keys_list

    def _animate_tubinhos(self):
        """Smoothly animates the cooldown tubes underneath each key card at ~30 FPS."""
        try:
            progress_data = self.engine.get_progress_for_all()
            is_running = self.engine.is_running
            now_t = time.time()

            # Select active cards: mini HUD cards in mini mode, or main cards in normal mode
            active_cards = self.mini_key_cards if self.is_mini_mode else self.key_cards

            if active_cards:
                for idx, cd in enumerate(active_cards):
                    tube_canvas = cd.get('tube_canvas')
                    bar_id = cd.get('bar_id')
                    card_idx = cd.get('card_index', idx)
                    if not tube_canvas or not bar_id:
                        continue

                    if is_running and card_idx in progress_data:
                        info = progress_data[card_idx]
                        p = info.get('progress', 0.0)
                        is_waiting = info.get('waiting_collision', False)
                        last_click = info.get('last_click_time', 0.0)
                        
                        w = tube_canvas.winfo_width()
                        if w > 1:
                            # 1. Visual GREEN flash when click fires (lasts 200ms)
                            if now_t - last_click < 0.20:
                                tube_canvas.coords(bar_id, 0, 0, w, 12)
                                tube_canvas.itemconfig(bar_id, fill=ACCENT_GREEN)
                            # 2. Yellow/Amber: waiting on anti-collision sequential delay
                            elif is_waiting:
                                tube_canvas.coords(bar_id, 0, 0, w, 12)
                                tube_canvas.itemconfig(bar_id, fill="#faa61a")
                            # 3. Normal progress: filling up progressively in vibrant blue
                            else:
                                fill_w = max(0, min(w, int(w * p)))
                                tube_canvas.coords(bar_id, 0, 0, fill_w, 12)
                                tube_canvas.itemconfig(bar_id, fill=ACCENT_BLUE)
                    else:
                        # Reset to 0 when idle/stopped
                        tube_canvas.coords(bar_id, 0, 0, 0, 12)
                        tube_canvas.itemconfig(bar_id, fill=ACCENT_BLUE)
        except Exception:
            pass

        self.root.after(33, self._animate_tubinhos)

    def _on_hotkey_toggle_callback(self):
        self.root.after(0, self._toggle_clicker)

    def _toggle_clicker(self):
        """Single button toggle: starts if stopped, stops if running."""
        if self.engine.is_running:
            self.stop_clicker()
        else:
            self.start_clicker()

    def _on_hotkey_start_callback(self):
        self.root.after(0, self.start_clicker)

    def _on_hotkey_stop_callback(self):
        self.root.after(0, self.stop_clicker)

    def _on_hotkey_changed(self, event=None):
        hk = self.hotkey_var.get().strip().upper()
        if not hk:
            hk = "F6"
            self.hotkey_var.set(hk)
        vk, _ = resolve_key(hk)
        self.engine.set_hotkey_toggle(vk)
        self.btn_start.config(text=f"▶ INICIAR ({hk})")
        self.btn_stop.config(text=f"⏹ PARAR ({hk})")

    # ----------------- SETUPS (SALVAR / CARREGAR) -----------------
    def load_setups_from_disk(self):
        filepath = get_setups_file_path()
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    self.all_setups = json.load(f)
            except Exception:
                self.all_setups = {}
        else:
            self.all_setups = {
                "Farm Ragnarok F10": {
                    "name": "Farm Ragnarok F10",
                    "mode": "background",
                    "jitter": True,
                    "keys": [
                        {"key": "F10", "time": "500", "unit": "ms"},
                        {"key": "F1", "time": "2000", "unit": "ms"}
                    ]
                },
                "Auto Pot & Buffs": {
                    "name": "Auto Pot & Buffs",
                    "mode": "background",
                    "jitter": True,
                    "keys": [
                        {"key": "1", "time": "250", "unit": "ms"},
                        {"key": "2", "time": "1500", "unit": "ms"},
                        {"key": "SPACE", "time": "3000", "unit": "ms"}
                    ]
                }
            }
            self._save_setups_to_disk()

        self._refresh_setups_dropdown()

        if self.all_setups:
            first_name = list(self.all_setups.keys())[0]
            self.saved_setups_combo.set(first_name)
            self._apply_setup(self.all_setups[first_name])
        else:
            self.add_key_card(default_key="F10", default_time="5", default_unit="s")
            self.add_key_card(default_key="F1", default_time="2", default_unit="s")

    def _save_setups_to_disk(self):
        filepath = get_setups_file_path()
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.all_setups, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar setups:\n{e}")
            return False

    def _refresh_setups_dropdown(self):
        names = list(self.all_setups.keys())
        self.saved_setups_combo['values'] = names

    def save_current_setup(self):
        name = self.setup_name_var.get().strip()
        if not name:
            messagebox.showwarning("Nome Obrigatório", "Digite um nome para descrever este setup!")
            self.setup_name_entry.focus()
            return

        keys_data = []
        for cd in self.key_cards:
            k = cd['key_combo'].get().strip()
            t = cd['time_ent'].get().strip()
            u = cd['unit_combo'].get().strip()
            if k:
                keys_data.append({
                    "key": k,
                    "time": t if t else "500",
                    "unit": u if u else "ms"
                })

        if not keys_data:
            messagebox.showwarning("Nenhuma Tecla", "Configure pelo menos uma tecla válida!")
            return

        self.all_setups[name] = {
            "name": name,
            "mode": self.mode_var.get(),
            "jitter": self.jitter_var.get(),
            "collision_delay": self.collision_delay_var.get() if hasattr(self, 'collision_delay_var') else "3.0",
            "hotkey": self.hotkey_var.get() if hasattr(self, 'hotkey_var') else "F6",
            "keys": keys_data
        }

        if self._save_setups_to_disk():
            self._refresh_setups_dropdown()
            self.saved_setups_combo.set(name)
            messagebox.showinfo("Sucesso", f"Setup '{name}' salvo!")

    def _on_setup_combo_selected(self, event):
        name = self.saved_setups_combo.get().strip()
        if name in self.all_setups:
            self._apply_setup(self.all_setups[name])

    def _apply_setup(self, setup_data):
        self.setup_name_var.set(setup_data.get('name', ''))
        self.mode_var.set(setup_data.get('mode', 'background'))
        self.jitter_var.set(setup_data.get('jitter', True))
        if hasattr(self, 'collision_delay_var'):
            self.collision_delay_var.set(str(setup_data.get('collision_delay', '3.0')))
        if hasattr(self, 'hotkey_var'):
            self.hotkey_var.set(setup_data.get('hotkey', 'F6'))
            self._on_hotkey_changed(None)

        for cd in list(self.key_cards):
            cd['frame'].destroy()
        self.key_cards.clear()

        keys = setup_data.get('keys', [])
        if keys:
            for k in keys:
                self.add_key_card(
                    default_key=k.get('key', 'F10'),
                    default_time=k.get('time', '500'),
                    default_unit=k.get('unit', 's')
                )
        else:
            self.add_key_card("F10", "5", "s")

    def delete_selected_setup(self):
        name = self.saved_setups_combo.get().strip()
        if not name or name not in self.all_setups:
            return

        if messagebox.askyesno("Confirmar", f"Excluir o setup '{name}'?"):
            del self.all_setups[name]
            self._save_setups_to_disk()
            self._refresh_setups_dropdown()
            if self.all_setups:
                first = list(self.all_setups.keys())[0]
                self.saved_setups_combo.set(first)
                self._apply_setup(self.all_setups[first])
            else:
                self.saved_setups_combo.set("")
                self.setup_name_var.set("")

    def _toggle_always_on_top(self):
        self.root.wm_attributes("-topmost", self.ontop_var.get())

    def _on_combo_dropdown_open(self):
        current_selection = self.selected_window['hwnd'] if self.selected_window else None
        self.windows_cache = list_user_windows()
        display_values = [w['display'] for w in self.windows_cache]
        self.window_combo['values'] = display_values

        if current_selection:
            for idx, w in enumerate(self.windows_cache):
                if w['hwnd'] == current_selection:
                    self.window_combo.current(idx)
                    return

    def refresh_windows_list(self):
        self.windows_cache = list_user_windows()
        display_values = [w['display'] for w in self.windows_cache]
        self.window_combo['values'] = display_values

        if display_values:
            selected_idx = 0
            for idx, w in enumerate(self.windows_cache):
                name_low = w['exe'].lower()
                if any(g in name_low for g in ['ragnarok', 'ragexe', 'rf_online', 'game']):
                    selected_idx = idx
                    break

            self.window_combo.current(selected_idx)
            self._on_window_selected(None)
        else:
            self.window_combo.set("Nenhum jogo encontrado. Clique em 🔄")
            self.selected_window = None

    def _on_window_selected(self, event):
        idx = self.window_combo.current()
        if 0 <= idx < len(self.windows_cache):
            self.selected_window = self.windows_cache[idx]
            if self.is_mini_mode:
                self.title_lbl.config(text=f"⚡ AutoClicker [{self.selected_window['exe']}]")

    def start_clicker(self):
        if not self.selected_window or not is_window_alive(self.selected_window['hwnd']):
            self.refresh_windows_list()
            if not self.selected_window:
                messagebox.showerror(
                    "Janela Não Selecionada",
                    "Por favor, selecione o jogo na lista antes de iniciar!"
                )
                return

        keys = self._get_configured_keys()
        if not keys:
            messagebox.showerror(
                "Nenhuma Tecla",
                "Configure pelo menos uma tecla e tempo válido!"
            )
            return

        mode = self.mode_var.get()
        jitter = self.jitter_var.get()
        try:
            col_delay = float(self.collision_delay_var.get().replace(',', '.'))
        except (ValueError, AttributeError):
            col_delay = 3.0

        self.engine.set_config(
            target_hwnd=self.selected_window['hwnd'],
            target_title=self.selected_window['title'],
            keys_list=keys,
            mode=mode,
            jitter_enabled=jitter,
            collision_pause=col_delay
        )
        self.engine.start()

    def stop_clicker(self):
        self.engine.stop()

    def _on_tick_callback(self, count, elapsed):
        now = time.time()
        if now - self._last_gui_update < 0.05:
            return
        self._last_gui_update = now

        def update():
            try:
                mins = int(elapsed // 60)
                secs = int(elapsed % 60)
                time_str = f"{mins:02d}:{secs:02d}"
                self.stats_lbl.config(text=f"Cliques: {count:,}  |  {time_str}")
            except Exception:
                pass
        try:
            self.root.after(0, update)
        except Exception:
            pass

    def _on_state_change_callback(self, is_running, message):
        def update():
            try:
                if is_running:
                    target_exe = self.selected_window['exe'] if self.selected_window else 'Jogo'
                    active_count = len(self._get_configured_keys())
                    mode_tag = " [2º Plano]" if self.mode_var.get() == "background" else " [Foco Ativo]"
                    status_txt = f"● ATIVO ({active_count}T){mode_tag}" if self.is_mini_mode else f"● CLICANDO ({active_count} TECLAS) EM {target_exe}{mode_tag}"
                    self.status_badge.config(
                        text=status_txt,
                        fg=ACCENT_GREEN
                    )
                    self.btn_start.config(state="disabled")
                    self.btn_stop.config(state="normal")
                else:
                    self.status_badge.config(
                        text="● PARADO",
                        fg=ACCENT_RED
                    )
                    self.btn_start.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    if message and "Erro" in message:
                        messagebox.showwarning("Aviso", message)
            except Exception:
                pass
        try:
            self.root.after(0, update)
        except Exception:
            pass

    def _on_close(self):
        self.engine.shutdown()
        self.root.destroy()
        sys.exit(0)

def main():
    root = tk.Tk()
    app = AutoKeyClickerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
