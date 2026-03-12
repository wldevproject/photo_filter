import argparse
import io
import shutil
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox

try:
    import customtkinter as ctk
except ImportError as exc:
    raise SystemExit(
        "customtkinter belum terpasang. Install dulu dengan: pip install customtkinter"
    ) from exc

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError as exc:
    raise SystemExit(
        "Pillow belum terpasang. Install dulu dengan: pip install pillow"
    ) from exc

try:
    import rawpy
except ImportError:
    rawpy = None


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

RAW_EXTENSIONS = {
    ".nef",
    ".cr2",
    ".cr3",
    ".arw",
    ".dng",
    ".rw2",
    ".orf",
    ".raf",
    ".pef",
    ".srw",
    ".3fr",
    ".fff",
    ".iiq",
    ".raw",
    ".erf",
    ".kdc",
    ".mef",
    ".mos",
    ".mrw",
    ".nrw",
    ".rwl",
    ".x3f",
    ".dcr",
    ".cap",
    ".bay",
    ".gpr",
}

SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | RAW_EXTENSIONS

CATEGORY_CONFIG = [
    ("1", "Bagus", {"light": "#22c55e", "dark": "#16a34a"}),
    ("2", "Lumayan", {"light": "#f59e0b", "dark": "#d97706"}),
    ("3", "Jelek", {"light": "#ef4444", "dark": "#dc2626"}),
]

THEME_TOKENS = {
    "light": {
        "app_bg": "#edf2fb",
        "shell_bg": "#eaf0fa",
        "card_bg": "#fdfefe",
        "card_border": "#cfdced",
        "panel_bg": "#f4f8ff",
        "panel_border": "#d7e3f4",
        "preview_bg": "#f1f6ff",
        "text": "#13223f",
        "muted": "#5c7295",
        "accent": "#1765ff",
        "accent_hover": "#0f4fcf",
        "chip_bg": "#e3ecff",
        "action_bg": "#edf3ff",
        "action_hover": "#dfe9fb",
        "kicker": "#1f5bc7",
        "button_text": "#ffffff",
    },
    "dark": {
        "app_bg": "#10182b",
        "shell_bg": "#111c31",
        "card_bg": "#172339",
        "card_border": "#314766",
        "panel_bg": "#1c2b44",
        "panel_border": "#385173",
        "preview_bg": "#203150",
        "text": "#f1f6ff",
        "muted": "#a9bddb",
        "accent": "#5ea2ff",
        "accent_hover": "#7eb6ff",
        "chip_bg": "#2a4166",
        "action_bg": "#253852",
        "action_hover": "#2f4769",
        "kicker": "#7eb6ff",
        "button_text": "#f8fafc",
    },
}


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def resolve_destination(destination: Path) -> Path:
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    counter = 1
    while True:
        candidate = destination.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def get_runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resolve_asset_path(*parts: str) -> Path:
    runtime_base = get_runtime_base_dir()
    candidates = [
        runtime_base.joinpath("assets", *parts),
        Path(sys.executable).resolve().parent.joinpath("assets", *parts),
        Path(__file__).resolve().parent.joinpath("assets", *parts),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return runtime_base.joinpath("assets", *parts)


def truncate_middle(text: str, max_length: int = 110) -> str:
    if len(text) <= max_length:
        return text
    half = (max_length - 3) // 2
    return f"{text[:half]}...{text[-half:]}"


class PhotoSorterApp:
    def __init__(self, root: ctk.CTk, source_dir: Path | None = None):
        self.root = root
        self.root.title("Photo Sorter 2026")
        self.root.geometry("1380x880")
        self.root.minsize(1024, 700)
        self._icon_photo = None
        self._configure_window_icon()

        ctk.set_default_color_theme("blue")
        ctk.set_appearance_mode("light")
        self.compact_mode = False

        self.source_dir = source_dir.resolve() if source_dir else None
        self.target_dirs: dict[str, Path] = {}
        if self.source_dir is not None:
            self.target_dirs = {
                name: self.source_dir / name for _, name, _ in CATEGORY_CONFIG
            }
            for path in self.target_dirs.values():
                path.mkdir(parents=True, exist_ok=True)

        self.image_paths = self._load_images()
        self.category_counts = self._load_existing_category_counts()
        self.index = 0
        self.current_pil = None
        self.current_photo = None
        self.render_after_id = None
        self.move_history = []

        self.font_family = self._resolve_font_family()
        self.font_family_medium = self._resolve_font_family("medium")
        self.font_family_semibold = self._resolve_font_family("semibold")

        folder_label = (
            f"Folder Aktif: {truncate_middle(str(self.source_dir))}"
            if self.source_dir is not None
            else "Folder Aktif: belum dipilih"
        )
        self.folder_var = tk.StringVar(value=folder_label)
        self.progress_var = tk.StringVar(value="")
        self.remaining_var = tk.StringVar(value="")
        self.file_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")
        self.help_var = tk.StringVar(
            value=(
                "Shortcut: 1 Bagus | 2 Lumayan | 3 Jelek | 0/→ Skip | ← Previous | U Undo | Q/Esc Keluar"
            )
        )
        self.category_count_vars = {
            name: tk.StringVar(value="0") for _, name, _ in CATEGORY_CONFIG
        }

        self._build_ui()
        self._bind_shortcuts()
        self._show_current_image()

    def _configure_window_icon(self) -> None:
        ico_path = resolve_asset_path("app_icon.ico")
        png_path = resolve_asset_path("app_icon.png")

        try:
            if ico_path.exists():
                self.root.iconbitmap(default=str(ico_path))
        except Exception:
            pass

        try:
            if png_path.exists():
                self._icon_photo = tk.PhotoImage(file=str(png_path))
                self.root.iconphoto(True, self._icon_photo)
        except Exception:
            pass

    def _resolve_font_family(self, weight: str = "regular") -> str:
        candidates = {
            "regular": ["Manrope", "Poppins", "Segoe UI Variable Display", "Segoe UI", "Arial"],
            "medium": ["Manrope Medium", "Poppins Medium", "Manrope", "Poppins", "Segoe UI", "Arial"],
            "semibold": [
                "Manrope SemiBold",
                "Poppins SemiBold",
                "Poppins Semibold",
                "Manrope",
                "Poppins",
                "Segoe UI Semibold",
                "Segoe UI",
            ],
        }.get(weight, ["Manrope", "Poppins", "Segoe UI", "Arial"])

        available = {name.lower(): name for name in tkfont.families(self.root)}
        for candidate in candidates:
            selected = available.get(candidate.lower())
            if selected:
                return selected
        return "Arial"

    def _theme_name(self) -> str:
        return "dark" if ctk.get_appearance_mode().lower() == "dark" else "light"

    def _tokens(self) -> dict[str, str]:
        return THEME_TOKENS[self._theme_name()]

    def _layout(self) -> dict[str, int | bool]:
        if self.compact_mode:
            return {
                "shell_padx": 12,
                "shell_pady": 10,
                "card_corner": 14,
                "panel_corner": 11,
                "header_bottom_gap": 10,
                "header_side_pad": 14,
                "title_size": 28,
                "subtitle_size": 12,
                "show_subtitle": False,
                "button_height": 36,
                "button_font": 12,
                "open_width": 114,
                "theme_width": 104,
                "compact_width": 118,
                "progress_height": 13,
                "progress_label_width": 144,
                "sidebar_width": 324,
                "sidebar_title_size": 19,
                "remaining_font": 12,
                "preview_title_size": 20,
                "tip_wrap": 280,
                "category_height": 40,
                "category_font": 14,
                "category_keycap_width": 30,
                "action_height": 36,
                "action_font": 12,
                "action_keycap_width": 44,
            }
        return {
            "shell_padx": 18,
            "shell_pady": 16,
            "card_corner": 18,
            "panel_corner": 14,
            "header_bottom_gap": 14,
            "header_side_pad": 18,
            "title_size": 34,
            "subtitle_size": 13,
            "show_subtitle": True,
            "button_height": 40,
            "button_font": 13,
            "open_width": 128,
            "theme_width": 118,
            "compact_width": 130,
            "progress_height": 16,
            "progress_label_width": 172,
            "sidebar_width": 378,
            "sidebar_title_size": 22,
            "remaining_font": 13,
            "preview_title_size": 24,
            "tip_wrap": 340,
            "category_height": 46,
            "category_font": 16,
            "category_keycap_width": 36,
            "action_height": 42,
            "action_font": 13,
            "action_keycap_width": 52,
        }

    def _compact_label(self) -> str:
        return "Compact: On" if self.compact_mode else "Compact: Off"

    def _build_ui(self) -> None:
        tokens = self._tokens()
        layout = self._layout()
        self.root.configure(fg_color=tokens["app_bg"])

        self.shell = ctk.CTkFrame(self.root, fg_color=tokens["shell_bg"], corner_radius=0)
        self.shell.pack(
            fill="both",
            expand=True,
            padx=layout["shell_padx"],
            pady=layout["shell_pady"],
        )

        self.header_card = ctk.CTkFrame(
            self.shell,
            fg_color=tokens["card_bg"],
            border_color=tokens["card_border"],
            border_width=1,
            corner_radius=layout["card_corner"],
        )
        self.header_card.pack(fill="x", pady=(0, layout["header_bottom_gap"]))

        header_top = ctk.CTkFrame(self.header_card, fg_color="transparent")
        header_top.pack(fill="x", padx=layout["header_side_pad"], pady=(12, 4))

        brand_block = ctk.CTkFrame(header_top, fg_color="transparent")
        brand_block.pack(side="left", fill="x", expand=True)

        self.kicker_label = ctk.CTkLabel(
            brand_block,
            text="Photo Workflow",
            text_color=tokens["kicker"],
            font=(self.font_family_medium, 11),
            anchor="w",
        )
        self.kicker_label.pack(fill="x")

        self.title_label = ctk.CTkLabel(
            brand_block,
            text="Photo Sorter",
            text_color=tokens["text"],
            font=(self.font_family_semibold, layout["title_size"]),
            anchor="w",
        )
        self.title_label.pack(fill="x", pady=(0, 2))

        self.subtitle_label = ctk.CTkLabel(
            brand_block,
            text="Desktop culling cepat untuk JPG/PNG dan berbagai format RAW.",
            text_color=tokens["muted"],
            font=(self.font_family, layout["subtitle_size"]),
            anchor="w",
        )
        if layout["show_subtitle"]:
            self.subtitle_label.pack(fill="x")

        action_block = ctk.CTkFrame(header_top, fg_color="transparent")
        action_block.pack(side="right", padx=(10, 0))

        self.theme_button = ctk.CTkButton(
            action_block,
            text="Dark Mode" if self._theme_name() == "light" else "Light Mode",
            command=self.toggle_theme,
            height=layout["button_height"],
            corner_radius=12,
            fg_color=tokens["action_bg"],
            hover_color=tokens["action_hover"],
            text_color=tokens["text"],
            border_width=1,
            border_color=tokens["panel_border"],
            font=(self.font_family_medium, layout["button_font"]),
            width=layout["theme_width"],
        )
        self.theme_button.pack(side="right")

        self.compact_button = ctk.CTkButton(
            action_block,
            text=self._compact_label(),
            command=self.toggle_compact_mode,
            height=layout["button_height"],
            corner_radius=12,
            fg_color=tokens["action_bg"],
            hover_color=tokens["action_hover"],
            text_color=tokens["text"],
            border_width=1,
            border_color=tokens["panel_border"],
            font=(self.font_family_medium, layout["button_font"]),
            width=layout["compact_width"],
        )
        self.compact_button.pack(side="right", padx=(0, 8))

        self.open_button = ctk.CTkButton(
            action_block,
            text="Open Folder",
            command=self.open_folder,
            height=layout["button_height"],
            corner_radius=12,
            fg_color=tokens["accent"],
            hover_color=tokens["accent_hover"],
            text_color=tokens["button_text"],
            font=(self.font_family_semibold, layout["button_font"]),
            width=layout["open_width"],
        )
        self.open_button.pack(side="right", padx=(0, 8))

        self.folder_label = ctk.CTkLabel(
            self.header_card,
            textvariable=self.folder_var,
            text_color=tokens["muted"],
            font=(self.font_family, 13),
            anchor="w",
        )
        self.folder_label.pack(fill="x", padx=layout["header_side_pad"], pady=(8, 0))

        progress_row = ctk.CTkFrame(self.header_card, fg_color="transparent")
        progress_row.pack(fill="x", padx=layout["header_side_pad"], pady=(10, 12))

        self.progress_bar = ctk.CTkProgressBar(
            progress_row,
            height=layout["progress_height"],
            corner_radius=9,
            fg_color=tokens["chip_bg"],
            border_width=1,
            border_color=tokens["panel_border"],
            progress_color=tokens["accent"],
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_row,
            textvariable=self.progress_var,
            text_color=tokens["text"],
            font=(self.font_family_semibold, 13),
            width=layout["progress_label_width"],
            anchor="e",
        )
        self.progress_label.pack(side="left")

        content = ctk.CTkFrame(self.shell, fg_color="transparent")
        content.pack(fill="both", expand=True)

        self.sidebar_card = ctk.CTkFrame(
            content,
            fg_color=tokens["card_bg"],
            border_color=tokens["card_border"],
            border_width=1,
            corner_radius=layout["card_corner"],
            width=layout["sidebar_width"],
        )
        self.sidebar_card.pack(side="left", fill="y", padx=(0, 14))
        self.sidebar_card.pack_propagate(False)

        self.sidebar_title = ctk.CTkLabel(
            self.sidebar_card,
            text="Klasifikasi Cepat",
            text_color=tokens["text"],
            font=(self.font_family_semibold, layout["sidebar_title_size"]),
            anchor="w",
        )
        self.sidebar_title.pack(anchor="w", padx=16, pady=(14, 8))

        self.remaining_chip = ctk.CTkLabel(
            self.sidebar_card,
            textvariable=self.remaining_var,
            text_color=tokens["accent"],
            fg_color=tokens["chip_bg"],
            corner_radius=999,
            font=(self.font_family_semibold, layout["remaining_font"]),
            padx=14,
            pady=7,
        )
        self.remaining_chip.pack(anchor="w", padx=16, pady=(0, 12))

        self._build_category_segment()
        self._build_action_segment()

        self.tip_label = ctk.CTkLabel(
            self.sidebar_card,
            text="Tip: fokuskan jendela aplikasi, lalu gunakan keyboard untuk flow sortir paling cepat.",
            justify="left",
            text_color=tokens["muted"],
            font=(self.font_family, 12),
            wraplength=layout["tip_wrap"],
        )
        self.tip_label.pack(anchor="w", padx=16, pady=(12, 14))

        self.preview_card = ctk.CTkFrame(
            content,
            fg_color=tokens["card_bg"],
            border_color=tokens["card_border"],
            border_width=1,
            corner_radius=layout["card_corner"],
        )
        self.preview_card.pack(side="left", fill="both", expand=True)

        self.file_label = ctk.CTkLabel(
            self.preview_card,
            textvariable=self.file_var,
            text_color=tokens["text"],
            font=(self.font_family_semibold, layout["preview_title_size"]),
            anchor="w",
        )
        self.file_label.pack(fill="x", padx=16, pady=(14, 2))

        self.status_label = ctk.CTkLabel(
            self.preview_card,
            textvariable=self.status_var,
            text_color=tokens["muted"],
            font=(self.font_family, 12),
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=16, pady=(0, 10))

        self.image_card = ctk.CTkFrame(
            self.preview_card,
            fg_color=tokens["preview_bg"],
            border_color=tokens["panel_border"],
            border_width=1,
            corner_radius=layout["panel_corner"],
        )
        self.image_card.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.image_container = tk.Label(
            self.image_card,
            bg=tokens["preview_bg"],
            fg=tokens["muted"],
            text="Memuat foto...",
            font=(self.font_family, 12),
            justify="center",
        )
        self.image_container.pack(fill="both", expand=True, padx=14, pady=14)
        self.image_container.bind("<Configure>", self._on_preview_resize)

        self.help_label = ctk.CTkLabel(
            self.preview_card,
            textvariable=self.help_var,
            text_color=tokens["muted"],
            font=(self.font_family, 12),
            anchor="w",
            justify="left",
        )
        self.help_label.pack(fill="x", padx=16, pady=(0, 12))

    def _build_category_segment(self) -> None:
        tokens = self._tokens()
        layout = self._layout()

        section = ctk.CTkFrame(
            self.sidebar_card,
            fg_color=tokens["panel_bg"],
            corner_radius=layout["panel_corner"],
            border_width=1,
            border_color=tokens["panel_border"],
        )
        section.pack(fill="x", padx=16, pady=(0, 10))

        for key, name, colors in CATEGORY_CONFIG:
            row = ctk.CTkFrame(section, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=6)

            tone = colors[self._theme_name()]
            button = ctk.CTkButton(
                row,
                text=name,
                command=lambda n=name: self.move_current(n),
                height=layout["category_height"],
                corner_radius=13,
                fg_color=tone,
                hover_color=tone,
                text_color=self._tokens()["button_text"],
                font=(self.font_family_semibold, layout["category_font"]),
                anchor="w",
            )
            button.pack(side="left", fill="x", expand=True)

            keycap = ctk.CTkLabel(
                row,
                text=key,
                width=layout["category_keycap_width"],
                corner_radius=10,
                fg_color=tokens["card_bg"],
                text_color=tokens["text"],
                font=(self.font_family_semibold, 12),
            )
            keycap.pack(side="left", padx=(8, 8))

            count_label = ctk.CTkLabel(
                row,
                textvariable=self.category_count_vars[name],
                width=44,
                corner_radius=10,
                fg_color=tokens["card_bg"],
                text_color=tone,
                font=(self.font_family_semibold, 14),
            )
            count_label.pack(side="left")

    def _build_action_segment(self) -> None:
        tokens = self._tokens()
        layout = self._layout()

        title = ctk.CTkLabel(
            self.sidebar_card,
            text="Navigasi & Aksi",
            text_color=tokens["text"],
            font=(self.font_family_semibold, 16 if self.compact_mode else 18),
            anchor="w",
        )
        title.pack(fill="x", padx=16, pady=(6, 8))

        section = ctk.CTkFrame(
            self.sidebar_card,
            fg_color=tokens["panel_bg"],
            corner_radius=layout["panel_corner"],
            border_width=1,
            border_color=tokens["panel_border"],
        )
        section.pack(fill="x", padx=16)

        actions = [
            ("Skip", "0 / ->", self.next_image),
            ("Previous", "<-", self.prev_image),
            ("Undo", "U", self.undo_last_move),
            ("Keluar", "Q", self.root.quit),
        ]

        for label, hotkey, callback in actions:
            row = ctk.CTkFrame(section, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=6)

            button = ctk.CTkButton(
                row,
                text=label,
                command=callback,
                height=layout["action_height"],
                corner_radius=12,
                fg_color=tokens["action_bg"],
                hover_color=tokens["action_hover"],
                text_color=tokens["text"],
                font=(self.font_family_medium, layout["action_font"]),
                anchor="w",
            )
            button.pack(side="left", fill="x", expand=True)

            keycap = ctk.CTkLabel(
                row,
                text=hotkey,
                width=layout["action_keycap_width"],
                corner_radius=10,
                fg_color=tokens["card_bg"],
                text_color=tokens["muted"],
                font=(self.font_family_semibold, 12),
            )
            keycap.pack(side="left", padx=(8, 0))

    def open_folder(self) -> None:
        initial = self.source_dir if self.source_dir is not None else Path.cwd()
        selected = choose_directory(initial)
        if selected is None:
            return
        self._set_source_dir(selected)

    def _set_source_dir(self, source_dir: Path) -> None:
        self.source_dir = source_dir.resolve()
        self.target_dirs = {
            name: self.source_dir / name for _, name, _ in CATEGORY_CONFIG
        }
        for path in self.target_dirs.values():
            path.mkdir(parents=True, exist_ok=True)

        self.image_paths = self._load_images()
        self.category_counts = self._load_existing_category_counts()
        self.move_history.clear()
        self.index = 0
        self.folder_var.set(f"Folder Aktif: {truncate_middle(str(self.source_dir))}")
        self._show_current_image()

    def toggle_theme(self) -> None:
        if self._theme_name() == "light":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")
        self._rebuild_ui()

    def toggle_compact_mode(self) -> None:
        self.compact_mode = not self.compact_mode
        self._rebuild_ui()

    def _rebuild_ui(self) -> None:
        if self.render_after_id is not None:
            self.root.after_cancel(self.render_after_id)
            self.render_after_id = None

        for child in self.root.winfo_children():
            child.destroy()

        self._build_ui()
        self._show_current_image()

    def _bind_shortcuts(self) -> None:
        self.root.bind("1", lambda _event: self.move_current("Bagus"))
        self.root.bind("2", lambda _event: self.move_current("Lumayan"))
        self.root.bind("3", lambda _event: self.move_current("Jelek"))
        self.root.bind("0", lambda _event: self.next_image())
        self.root.bind("<Right>", lambda _event: self.next_image())
        self.root.bind("<Left>", lambda _event: self.prev_image())
        self.root.bind("u", lambda _event: self.undo_last_move())
        self.root.bind("U", lambda _event: self.undo_last_move())
        self.root.bind("q", lambda _event: self.root.quit())
        self.root.bind("Q", lambda _event: self.root.quit())
        self.root.bind("<Escape>", lambda _event: self.root.quit())

    def _load_existing_category_counts(self) -> dict[str, int]:
        counts = {name: 0 for _, name, _ in CATEGORY_CONFIG}
        if self.source_dir is None:
            return counts
        for _, name, _ in CATEGORY_CONFIG:
            folder = self.target_dirs[name]
            count = 0
            for path in folder.iterdir():
                if is_image_file(path):
                    count += 1
            counts[name] = count
        return counts

    def _load_images(self) -> list[Path]:
        if self.source_dir is None:
            return []
        category_dirs = {path.resolve() for path in self.target_dirs.values()}
        images = []
        for path in sorted(self.source_dir.iterdir()):
            if path.resolve() in category_dirs:
                continue
            if is_image_file(path):
                images.append(path)
        return images

    def _on_preview_resize(self, _event: tk.Event) -> None:
        self._schedule_render()

    def _schedule_render(self) -> None:
        if self.render_after_id is not None:
            self.root.after_cancel(self.render_after_id)
        self.render_after_id = self.root.after(70, self._render_current_image)

    def _render_current_image(self) -> None:
        self.render_after_id = None
        if self.current_pil is None:
            return

        width = max(self.image_container.winfo_width() - 20, 220)
        height = max(self.image_container.winfo_height() - 20, 220)

        image = self.current_pil.copy()
        image.thumbnail((width, height))
        self.current_photo = ImageTk.PhotoImage(image)
        self.image_container.configure(image=self.current_photo, text="")

    def _refresh_dashboard(self) -> None:
        if self.source_dir is None:
            self.progress_var.set("0/0 selesai")
            self.remaining_var.set("Tersisa 0 foto")
            self.progress_bar.set(0.0)
            for _, name, _ in CATEGORY_CONFIG:
                self.category_count_vars[name].set("0")
            return

        remaining = len(self.image_paths)
        processed = sum(self.category_counts.values())
        total = processed + remaining

        if total <= 0:
            self.progress_var.set("0/0 selesai")
            self.remaining_var.set("Tersisa 0 foto")
            self.progress_bar.set(0.0)
        else:
            self.progress_var.set(f"{processed}/{total} selesai")
            self.remaining_var.set(f"Tersisa {remaining} foto")
            self.progress_bar.set(processed / total)

        for _, name, _ in CATEGORY_CONFIG:
            self.category_count_vars[name].set(str(self.category_counts[name]))

    def _load_with_pillow(self, path: Path) -> tuple[Image.Image | None, str | None]:
        try:
            with Image.open(path) as opened:
                image = ImageOps.exif_transpose(opened)
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGB")
                return image.copy(), None
        except Exception as exc:
            return None, f"Preview tidak tersedia:\n{exc}"

    def _load_with_rawpy(self, path: Path) -> tuple[Image.Image | None, str | None]:
        if rawpy is None:
            return None, "RAW engine belum aktif. Install dulu: pip install rawpy"

        try:
            with rawpy.imread(str(path)) as raw:
                try:
                    rgb = raw.postprocess(
                        use_camera_wb=True,
                        auto_bright=True,
                        output_bps=8,
                        half_size=True,
                    )
                    return Image.fromarray(rgb), None
                except Exception:
                    thumb = raw.extract_thumb()

            if thumb.format == rawpy.ThumbFormat.JPEG:
                with Image.open(io.BytesIO(thumb.data)) as opened:
                    image = ImageOps.exif_transpose(opened)
                    if image.mode not in ("RGB", "RGBA"):
                        image = image.convert("RGB")
                    return image.copy(), None

            if thumb.format == rawpy.ThumbFormat.BITMAP:
                return Image.fromarray(thumb.data), None

            return None, "RAW terbaca, tapi thumbnail internal tidak tersedia."
        except Exception as exc:
            return None, f"Gagal membaca RAW dengan rawpy:\n{exc}"

    def _load_preview_image(self, path: Path) -> tuple[Image.Image | None, str | None]:
        suffix = path.suffix.lower()

        if suffix in RAW_EXTENSIONS:
            image, error_text = self._load_with_rawpy(path)
            if image is not None:
                return image, None

            fallback_image, fallback_error = self._load_with_pillow(path)
            if fallback_image is not None:
                return fallback_image, None

            return (
                None,
                (
                    f"{error_text}\n\n"
                    "Fallback PIL juga gagal:\n"
                    f"{fallback_error}\n\n"
                    "Coba install/upgrade: pip install -r requirements.txt --upgrade"
                ),
            )

        return self._load_with_pillow(path)

    def _show_current_image(self) -> None:
        self._refresh_dashboard()

        if self.source_dir is None:
            self.current_pil = None
            self.current_photo = None
            self.file_var.set("Belum ada folder dipilih")
            self.status_var.set("Klik tombol Open Folder untuk mulai sortir foto.")
            self.image_container.configure(
                image="",
                text=(
                    "Aplikasi siap dipakai.\n"
                    "Klik Open Folder untuk memilih folder foto."
                ),
            )
            return

        if not self.image_paths:
            self.current_pil = None
            self.current_photo = None
            self.file_var.set("Semua foto selesai diproses")
            self.status_var.set("Tidak ada foto tersisa di folder sumber.")
            self.image_container.configure(
                image="",
                text=(
                    "Proses sortir selesai.\n"
                    "Counter folder tetap tersimpan sesuai isi folder Bagus/Lumayan/Jelek."
                ),
            )
            return

        self.index = max(0, min(self.index, len(self.image_paths) - 1))
        current_path = self.image_paths[self.index]

        self.file_var.set(current_path.name)
        self.status_var.set(
            f"Foto {self.index + 1}/{len(self.image_paths)} di antrian | "
            f"Format: {current_path.suffix.lower()}"
        )

        image, error_text = self._load_preview_image(current_path)
        if image is None:
            self.current_pil = None
            self.current_photo = None
            self.image_container.configure(
                image="",
                text=(
                    "Preview tidak tersedia untuk file ini.\n"
                    f"{error_text}\n\n"
                    "Kamu tetap bisa sortir file dengan tombol 1/2/3."
                ),
            )
            return

        self.current_pil = image
        self._render_current_image()

    def next_image(self) -> None:
        if not self.image_paths:
            return
        self.index = (self.index + 1) % len(self.image_paths)
        self._show_current_image()

    def prev_image(self) -> None:
        if not self.image_paths:
            return
        self.index = (self.index - 1) % len(self.image_paths)
        self._show_current_image()

    def move_current(self, category: str) -> None:
        if not self.image_paths:
            return

        src = self.image_paths[self.index]
        dest = resolve_destination(self.target_dirs[category] / src.name)

        try:
            shutil.move(str(src), str(dest))
        except Exception as exc:
            messagebox.showerror(
                "Gagal memindahkan file",
                f"Tidak bisa memindahkan:\n{src}\n\nError: {exc}",
            )
            return

        self.move_history.append(
            {
                "moved": dest,
                "original": src,
                "category": category,
            }
        )
        self.category_counts[category] += 1
        self.image_paths.pop(self.index)

        if self.index >= len(self.image_paths):
            self.index = 0

        self._show_current_image()

    def undo_last_move(self) -> None:
        if not self.move_history:
            messagebox.showinfo("Undo", "Belum ada file yang dipindahkan.")
            return

        history = self.move_history.pop()
        moved_path = history["moved"]
        original_path = history["original"]
        category = history["category"]

        restore_target = resolve_destination(original_path)
        try:
            shutil.move(str(moved_path), str(restore_target))
        except Exception as exc:
            messagebox.showerror(
                "Gagal undo",
                f"Tidak bisa mengembalikan file:\n{moved_path}\n\nError: {exc}",
            )
            return

        self.category_counts[category] = max(0, self.category_counts[category] - 1)

        insert_at = min(self.index, len(self.image_paths))
        self.image_paths.insert(insert_at, restore_target)
        self.index = insert_at
        self._show_current_image()


def choose_directory(initial: Path | None = None) -> Path | None:
    selected = filedialog.askdirectory(
        title="Pilih folder foto yang ingin disortir",
        initialdir=str(initial) if initial else None,
    )
    if not selected:
        return None
    return Path(selected)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sortir foto cepat ke folder Bagus, Lumayan, dan Jelek."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Folder sumber foto. Jika kosong, app akan meminta pilih folder.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = ctk.CTk()

    source_dir = None
    invalid_folder = None
    if args.folder:
        candidate = Path(args.folder).expanduser().resolve()
        if candidate.exists() and candidate.is_dir():
            source_dir = candidate
        else:
            invalid_folder = candidate

    PhotoSorterApp(root, source_dir)
    if invalid_folder is not None:
        messagebox.showwarning(
            "Folder argumen tidak valid",
            (
                "Folder dari argumen tidak bisa dipakai:\n"
                f"{invalid_folder}\n\n"
                "Aplikasi tetap dibuka. Klik Open Folder untuk memilih folder lain."
            ),
        )

    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
