import os
import sys
import threading
import logging
import urllib.request
import webbrowser
from datetime import datetime
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk

# Import local modules
from downloader import YTDownloader
from history_db import HistoryDB
from queue_manager import DownloadQueueManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Aura Streamline Design Tokens (Frutiger Aero / Glassmorphism theme)
# Fully responsive light/dark mode tuples mapping dark.html & bright.html specifications!
COLORS = {
    "background": ("#f8f9ff", "#050608"),
    "sidebar_bg": ("#e6eeff", "#0a0c10"),
    "surface": ("#ffffff", "#11141a"),
    "surface_dim": ("#ccdbf3", "#0d1c2e"),
    "surface_low": ("#eff4ff", "#0d0f14"),
    "surface_high": ("#dce9ff", "#1a1d24"),
    "surface_highest": ("#d5e3fc", "#23262e"),
    "on_surface": ("#0d1c2e", "#eaf1ff"),
    "on_surface_variant": ("#3f4753", "#bfc7d5"),
    "primary": ("#0061a5", "#3e9eff"),
    "primary_hover": ("#60a5fa", "#0099ff"),
    "on_primary": "#ffffff",
    "secondary": ("#006e2f", "#4ae176"),
    "secondary_bg": ("#e2fbe8", "#005321"),
    "error": ("#ba1a1a", "#ffb4ab"),
    "error_bg": ("#ffdad6", "#93000a"),
    "outline": ("#707884", "#717782"),
    "outline_variant": ("#bfc7d5", "#414750")
}

# Premium Typography Font Families with Windows Fallbacks
FONT_DISPLAY = ("Plus Jakarta Sans", "Segoe UI", "Tahoma", "Arial")
FONT_BODY = ("Be Vietnam Pro", "Segoe UI", "Tahoma", "Arial")

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Try direct path
    path1 = os.path.join(base_path, relative_path)
    if os.path.exists(path1):
        return path1
        
    # Try under _internal (PyInstaller v6+ onedir mode)
    path2 = os.path.join(base_path, "_internal", relative_path)
    if os.path.exists(path2):
        return path2
        
    return path1

class YTDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Initialize backend modules
        self.downloader = YTDownloader()
        self.history_db = HistoryDB()
        self.queue_manager = DownloadQueueManager(self.downloader, self.history_db, self._on_queue_update_callback)

        # Configure Main Window
        self.title("⚡ AURA STREAMLINE YT Downloader - Fast & Resolution Selectable")
        self.geometry("1100x700")
        self.minsize(950, 600)

        # Configure Window Icon
        try:
            ico_path = get_resource_path("logo.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
        except Exception as e:
            logging.error(f"Error setting window icon: {e}")

        # Theme & Styling
        ctk.set_appearance_mode("system")  # Matches OS theme by default, highly cohesive!
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COLORS["background"])
        
        # UI state variables
        self.current_fetched_video = None
        self.current_fetched_playlist = None
        self.thumbnail_image = None
        self.playlist_checkboxes = []  # List of (video_entry, var) tuples
        
        # Active page tracker
        self.active_tab = "single"
        
        # Build UI layout
        self._create_layout()
        
        # Periodically check and trigger UI updates (thread-safe UI queue polling)
        self.update_ui_queue = []
        self._poll_ui_updates()
        
        # Initial check for FFmpeg status
        self._update_ffmpeg_status()

    def _create_layout(self):
        # 1. Main Grid Configuration (Left Sidebar, Right Content)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 2. Sidebar Frame - Aura Streamline Glass/Solid Sidebar Layout
        self.sidebar_frame = ctk.CTkFrame(
            self, 
            width=288, 
            corner_radius=0,
            fg_color=COLORS["sidebar_bg"],
            border_width=1,
            border_color=COLORS["surface_high"]
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        # App Title & Brand (Plus Jakarta Sans) with premium circular image logo
        logo_loaded = False
        start_row = 1
        try:
            logo_path = get_resource_path("logo.png")
            if os.path.exists(logo_path):
                pil_logo = Image.open(logo_path)
                # Resize to standard sidebar size (72x72)
                self.sidebar_logo_img = ctk.CTkImage(
                    light_image=pil_logo, 
                    dark_image=pil_logo, 
                    size=(72, 72)
                )
                self.logo_image_label = ctk.CTkLabel(
                    self.sidebar_frame,
                    image=self.sidebar_logo_img,
                    text=""
                )
                self.logo_image_label.grid(row=0, column=0, padx=20, pady=(25, 5))
                
                # Push the text below the image
                self.logo_label = ctk.CTkLabel(
                    self.sidebar_frame, 
                    text="AURA STREAMLINE", 
                    font=ctk.CTkFont(family=FONT_DISPLAY, size=16, weight="bold"),
                    text_color=COLORS["on_surface"]
                )
                self.logo_label.grid(row=1, column=0, padx=20, pady=(0, 20))
                start_row = 2
                logo_loaded = True
        except Exception as e:
            logging.error(f"Error loading sidebar logo image: {e}")

        if not logo_loaded:
            self.logo_label = ctk.CTkLabel(
                self.sidebar_frame, 
                text="⚡ AURA STREAMLINE", 
                font=ctk.CTkFont(family=FONT_DISPLAY, size=18, weight="bold"),
                text_color=COLORS["on_surface"]
            )
            self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 20))
            start_row = 1

        # Navigation Buttons (Be Vietnam Pro, Rounded Pill layout)
        self.nav_buttons = {}
        nav_items = [
            ("single", "📥  ดาวน์โหลดวิดีโอเดี่ยว", self._show_single_download_page),
            ("playlist", "📋  ดาวน์โหลดเพลย์ลิสต์", self._show_playlist_download_page),
            ("queue", "⏳  คิวดาวน์โหลด", self._show_queue_page),
            ("history", "📜  ประวัติการดาวน์โหลด", self._show_history_page),
            ("settings", "⚙️  ตั้งค่าระบบ", self._show_settings_page)
        ]

        for i, (tab_id, text, command) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self.sidebar_frame, 
                text=text, 
                anchor="w",
                font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
                height=40,
                corner_radius=20, # Pill rounded as per design.md!
                fg_color="transparent",
                text_color=COLORS["on_surface_variant"],
                hover_color=COLORS["surface_low"],
                command=command
            )
            btn.grid(row=i+start_row, column=0, padx=12, pady=5, sticky="ew")
            self.nav_buttons[tab_id] = btn

        # FFmpeg Status Card in Sidebar bottom - Styled as a Level 2 Glass Card
        self.ffmpeg_card = ctk.CTkFrame(
            self.sidebar_frame, 
            fg_color=COLORS["surface"], 
            corner_radius=16,
            border_width=1,
            border_color=COLORS["surface_high"]
        )
        
        # Spacer row is dynamically calculated to push settings/status card to bottom
        spacer_row = len(nav_items) + start_row
        self.sidebar_frame.grid_rowconfigure(spacer_row, weight=1)
        self.ffmpeg_card.grid(row=spacer_row + 1, column=0, padx=12, pady=15, sticky="ew")
        
        self.ffmpeg_status_label = ctk.CTkLabel(
            self.ffmpeg_card, 
            text="กำลังตรวจสอบ FFmpeg...",
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            text_color=COLORS["on_surface_variant"],
            wraplength=170
        )
        self.ffmpeg_status_label.pack(padx=10, pady=(10, 5))
        
        self.ffmpeg_action_btn = ctk.CTkButton(
            self.ffmpeg_card,
            text="ติดตั้ง FFmpeg อัตโนมัติ",
            width=150,
            height=28,
            font=ctk.CTkFont(family=FONT_BODY, size=10, weight="bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["on_primary"],
            corner_radius=14, # Pill
            command=self._trigger_ffmpeg_download
        )
        self.ffmpeg_action_btn.pack(padx=10, pady=(0, 10))
        self.ffmpeg_action_btn.pack_forget()  # Hidden by default

        # 3. Content Frame (Right Side container)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Configure columns and rows inside content frame
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Draw the initial page
        self._show_single_download_page()

    def _set_active_button(self, active_tab_id):
        self.active_tab = active_tab_id
        for tab_id, btn in self.nav_buttons.items():
            if tab_id == active_tab_id:
                # Active styling (Aura Streamline Pill active liquid-blue)
                btn.configure(fg_color=COLORS["primary"], text_color=COLORS["on_primary"], hover_color=COLORS["primary_hover"])
            else:
                # Inactive styling
                btn.configure(fg_color="transparent", text_color=COLORS["on_surface_variant"], hover_color=COLORS["surface_low"])

    def _clear_content_frame(self):
        """Clears all widgets from the content container."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    # --- UI QUEUE FOR THREAD-SAFE UPDATES ---
    def _schedule_ui_update(self, func, *args, **kwargs):
        """Schedules a function to run on the main UI thread."""
        self.update_ui_queue.append((func, args, kwargs))

    def _poll_ui_updates(self):
        """Checks and runs pending UI updates every 100ms."""
        while self.update_ui_queue:
            func, args, kwargs = self.update_ui_queue.pop(0)
            try:
                func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error executing queued UI function: {e}")
        self.after(100, self._poll_ui_updates)

    def _on_queue_update_callback(self):
        """Callback triggered by DownloadQueueManager on progress/status changes."""
        self._schedule_ui_update(self._refresh_queue_view_if_active)

    def _refresh_queue_view_if_active(self):
        """Refreshes the queue tab if the user is currently viewing it."""
        if self.active_tab == "queue":
            self._render_queue_page_content()

    # --- FFMEG AUTO-INSTALL LOGIC ---
    def _update_ffmpeg_status(self):
        """Checks local/system FFmpeg and updates sidebar status indicator."""
        if self.downloader.check_ffmpeg():
            self.ffmpeg_card.configure(fg_color=COLORS["secondary_bg"])
            self.ffmpeg_status_label.configure(text="🟢 FFmpeg: พร้อมทำงาน\n(โหลด 1080p+ ได้สมบูรณ์)", text_color=COLORS["secondary"])
            self.ffmpeg_action_btn.pack_forget()
        else:
            self.ffmpeg_card.configure(fg_color=COLORS["error_bg"])
            self.ffmpeg_status_label.configure(text="⚠️ FFmpeg: ยังไม่ติดตั้ง\n(โหลดได้สูงสุด 720p)", text_color=COLORS["error"])
            self.ffmpeg_action_btn.pack(padx=10, pady=(0, 10))
            self.ffmpeg_action_btn.configure(
                text="ติดตั้ง FFmpeg อัตโนมัติ", 
                fg_color=COLORS["primary"], 
                hover_color=COLORS["primary_hover"]
            )

    def _trigger_ffmpeg_download(self):
        """Downloads FFmpeg in a background thread with progress status."""
        self.ffmpeg_action_btn.configure(state="disabled", text="กำลังเตรียมการ...")
        
        def run():
            def callback(status, percent, msg):
                def update():
                    self.ffmpeg_status_label.configure(text=msg)
                    if status == "downloading":
                        self.ffmpeg_action_btn.configure(text=f"กำลังโหลด {percent}%")
                    elif status == "extracting":
                        self.ffmpeg_action_btn.configure(text="กำลังติดตั้ง...")
                    elif status == "ready":
                        self._update_ffmpeg_status()
                    elif status == "error":
                        self._update_ffmpeg_status()
                        messagebox.showerror("Error Installing FFmpeg", msg)
                self._schedule_ui_update(update)
                
            self.downloader.download_ffmpeg(progress_callback=callback)
            
        threading.Thread(target=run, daemon=True).start()

    # ==========================================
    # 📥 PAGE 1: SINGLE DOWNLOAD PAGE
    # ==========================================
    def _show_single_download_page(self):
        self._set_active_button("single")
        self._clear_content_frame()

        # Top Header (Plus Jakarta Sans)
        self.single_header = ctk.CTkLabel(
            self.content_frame, 
            text="ดาวน์โหลดวิดีโอ YouTube เดี่ยว", 
            font=ctk.CTkFont(family=FONT_DISPLAY, size=24, weight="bold"),
            text_color=COLORS["on_surface"]
        )
        self.single_header.pack(anchor="w", pady=(8, 16))

        # URL Input Row
        self.url_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.url_frame.pack(fill="x", pady=8)
        
        # Recessed Entry widget
        self.url_entry = ctk.CTkEntry(
            self.url_frame, 
            placeholder_text="วางลิงก์วิดีโอ YouTube ของคุณที่นี่... (เช่น https://www.youtube.com/watch?v=...)",
            height=48,
            font=ctk.CTkFont(family=FONT_BODY, size=13),
            fg_color=COLORS["surface_low"],
            border_color=COLORS["outline_variant"],
            border_width=1,
            text_color=COLORS["on_surface"],
            corner_radius=12
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._patch_entry_behavior(self.url_entry)

        # Liquid Primary Pill Button
        self.fetch_btn = ctk.CTkButton(
            self.url_frame, 
            text="🔍  ดึงข้อมูลวิดีโอ", 
            height=48,
            width=140,
            font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["on_primary"],
            corner_radius=24, # Full Pill
            command=self._fetch_single_video_info
        )
        self.fetch_btn.pack(side="right")

        # Container for Fetched Info Cards - Level 2 Glass Card
        self.info_container = ctk.CTkFrame(
            self.content_frame, 
            fg_color=COLORS["surface"], 
            border_width=1,
            border_color=COLORS["surface_high"],
            corner_radius=24
        )
        self.info_container.pack(fill="both", expand=True, pady=(24, 0))
        
        # Display placeholder initially
        self.placeholder_label = ctk.CTkLabel(
            self.info_container,
            text="📥\n\nพร้อมสำหรับการดาวน์โหลดสุดทรงพลัง\n\nวางลิงก์ YouTube ด้านบน แล้วกดปุ่ม 'ดึงข้อมูลวิดีโอ' เพื่อเริ่มงานดาวน์โหลด",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=15, weight="bold"),
            text_color=COLORS["on_surface_variant"],
            justify="center"
        )
        self.placeholder_label.pack(expand=True, pady=100)

    def _fetch_single_video_info(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("คำเตือน", "กรุณากรอกลิงก์ YouTube ก่อนทำรายการครับ")
            return
            
        self.fetch_btn.configure(state="disabled", text="กำลังดึงข้อมูล...")
        
        # Clear container and show loading spinner or status
        for widget in self.info_container.winfo_children():
            widget.destroy()
            
        loading_label = ctk.CTkLabel(
            self.info_container, 
            text="⚡ กำลังดึงข้อมูลวิดีโอและการ์ดความละเอียด กรุณารอสักครู่...",
            font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
            text_color=COLORS["on_surface"]
        )
        loading_label.pack(expand=True)
        
        def run():
            try:
                raw_info = self.downloader.fetch_video_info(url)
                if 'entries' in raw_info:
                    # It's actually a playlist link, offer to redirect to playlist tab
                    def ask_redirect():
                        self.fetch_btn.configure(state="normal", text="🔍  ดึงข้อมูลวิดีโอ")
                        if messagebox.askyesno("ตรวจพบลิงก์เพลย์ลิสต์", "ลิงก์นี้เป็นเพลย์ลิสต์ คุณต้องการสลับไปยังแท็บดาวน์โหลดเพลย์ลิสต์ใช่หรือไม่?"):
                            self._show_playlist_download_page()
                            self.playlist_url_entry.insert(0, url)
                            self._fetch_playlist_info()
                        else:
                            self._show_single_download_page()
                    self._schedule_ui_update(ask_redirect)
                    return

                # Parse formats
                parsed = self.downloader.parse_formats(raw_info)
                self.current_fetched_video = parsed
                self.current_fetched_video['url'] = url
                
                # Fetch and render thumbnail in background
                thumbnail_url = parsed.get("thumbnail")
                img_data = None
                if thumbnail_url:
                    try:
                        # Fetch thumbnail image bytes
                        img_data, _ = urllib.request.urlretrieve(thumbnail_url)
                    except Exception as img_err:
                        logging.error(f"Failed to fetch thumbnail image: {img_err}")
                
                def render():
                    self.fetch_btn.configure(state="normal", text="🔍  ดึงข้อมูลวิดีโอ")
                    self._render_single_video_card(img_data)
                    
                self._schedule_ui_update(render)
                
            except Exception as e:
                def on_error():
                    self.fetch_btn.configure(state="normal", text="🔍  ดึงข้อมูลวิดีโอ")
                    for w in self.info_container.winfo_children():
                        w.destroy()
                    err_placeholder = ctk.CTkLabel(
                        self.info_container,
                        text=f"❌ เกิดข้อผิดพลาดในการดึงข้อมูล:\n{str(e)}\n\nกรุณาตรวจสอบว่าลิงก์ถูกต้องหรืออินเทอร์เน็ตยังใช้งานได้ตามปกติ",
                        font=ctk.CTkFont(family=FONT_BODY, size=13),
                        text_color=COLORS["error"]
                    )
                    err_placeholder.pack(expand=True, pady=50)
                self._schedule_ui_update(on_error)
                
        threading.Thread(target=run, daemon=True).start()

    def _render_single_video_card(self, temp_img_path):
        """Displays beautiful video card containing thumbnail, metadata, and format selector options."""
        for widget in self.info_container.winfo_children():
            widget.destroy()
            
        parsed = self.current_fetched_video
        
        # Main container with nice padding
        card_frame = ctk.CTkFrame(self.info_container, fg_color="transparent")
        card_frame.pack(fill="both", expand=True, padx=24, pady=24)
        
        card_frame.grid_columnconfigure(0, weight=1)
        card_frame.grid_columnconfigure(1, weight=1)
        
        # Left Side: Thumbnail Panel
        thumb_panel = ctk.CTkFrame(card_frame, fg_color="transparent")
        thumb_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        
        # Render image using Pillow
        width, height = 320, 180
        if temp_img_path:
            try:
                pil_img = Image.open(temp_img_path)
                pil_img = pil_img.resize((width, height), Image.Resampling.LANCZOS)
                self.thumbnail_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(width, height))
            except Exception as img_err:
                logging.error(f"Pillow resize failed: {img_err}")
                self.thumbnail_image = None
        else:
            self.thumbnail_image = None
            
        if self.thumbnail_image:
            thumb_label = ctk.CTkLabel(thumb_panel, image=self.thumbnail_image, text="")
        else:
            # Fallback black container
            thumb_label = ctk.CTkLabel(
                thumb_panel, 
                text="📷  ไม่มีรูปภาพหน้าปก", 
                width=width, 
                height=height, 
                fg_color="gray20", 
                corner_radius=8
            )
        thumb_label.pack(anchor="nw", pady=(0, 12))
        
        # Duration formatter
        dur_sec = parsed.get("duration", 0) or 0
        if dur_sec > 3600:
            dur_str = f"{dur_sec // 3600:02d}:{(dur_sec % 3600) // 60:02d}:{dur_sec % 60:02d}"
        else:
            dur_str = f"{dur_sec // 60:02d}:{dur_sec % 60:02d}"
            
        # Metadata below image
        metadata_label = ctk.CTkLabel(
            thumb_panel, 
            text=f"👤 ช่อง: {parsed.get('channel', 'Unknown')}\n⏱️ ความยาว: {dur_str}", 
            justify="left",
            anchor="w",
            font=ctk.CTkFont(family=FONT_BODY, size=12, weight="bold"),
            text_color=COLORS["on_surface_variant"]
        )
        metadata_label.pack(anchor="nw", pady=5)

        # Right Side: Selection Details Panel
        details_panel = ctk.CTkFrame(card_frame, fg_color="transparent")
        details_panel.grid(row=0, column=1, sticky="nsew")
        
        title_label = ctk.CTkLabel(
            details_panel, 
            text=parsed.get("title", "No Title"),
            font=ctk.CTkFont(family=FONT_DISPLAY, size=15, weight="bold"),
            text_color=COLORS["on_surface"],
            wraplength=450,
            justify="left",
            anchor="w"
        )
        title_label.pack(anchor="nw", pady=(0, 15))
        
        # Format Options dropdown configuration
        options_label = ctk.CTkLabel(
            details_panel,
            text="⚙️ เลือกความละเอียดหรือแยกไฟล์เสียง (MP3):",
            font=ctk.CTkFont(family=FONT_BODY, size=12, weight="bold"),
            text_color=COLORS["on_surface"]
        )
        options_label.pack(anchor="nw", pady=(5, 5))
        
        # Generate selector list options
        self.selector_options = []
        self.option_format_map = {}
        
        # Video formats mapping
        for res in parsed.get("resolutions", []):
            label = f"🎬 {res['label']} (MP4 Video) - {res['ext'].upper()}"
            if res['size_mb'] > 0:
                label += f" (~{res['size_mb']:.1f} MB)"
            self.selector_options.append(label)
            self.option_format_map[label] = {
                "format_id": res['format_id'],
                "label": res['label'],
                "is_audio": False,
                "size": f"{res['size_mb']:.1f} MB" if res['size_mb'] > 0 else "Unknown"
            }
            
        # Audio high quality option
        best_audio = parsed.get("best_audio")
        if best_audio:
            audio_size = best_audio['filesize'] / (1024*1024) if best_audio['filesize'] else 0
            audio_label = f"🎵 Audio MP3 - คุณภาพสูง 192kbps"
            if audio_size > 0:
                audio_label += f" (~{audio_size:.1f} MB)"
            self.selector_options.append(audio_label)
            self.option_format_map[audio_label] = {
                "format_id": best_audio['format_id'],
                "label": "Audio MP3",
                "is_audio": True,
                "size": f"{audio_size:.1f} MB" if audio_size > 0 else "Unknown"
            }
            
        if not self.selector_options:
            self.selector_options = ["ไม่พบความละเอียดที่เหมาะสม"]
            
        self.format_dropdown = ctk.CTkOptionMenu(
            details_panel,
            values=self.selector_options,
            width=350,
            height=38,
            font=ctk.CTkFont(family=FONT_BODY, size=13),
            fg_color=COLORS["primary"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"]
        )
        self.format_dropdown.pack(anchor="nw", pady=5)
        self.format_dropdown.set(self.selector_options[0])

        # Bottom buttons inside Selection Panel - Liquid Primary Pill Buttons
        btn_row = ctk.CTkFrame(details_panel, fg_color="transparent")
        btn_row.pack(anchor="nw", fill="x", pady=25)
        
        self.download_now_btn = ctk.CTkButton(
            btn_row,
            text="⚡  ดาวน์โหลดทันที",
            fg_color=COLORS["secondary"],
            hover_color=("#005321", "#36c760"),
            text_color=COLORS["on_primary"],
            width=180,
            height=42,
            corner_radius=21, # Pill
            font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
            command=self._download_single_video_now
        )
        self.download_now_btn.pack(side="left", padx=(0, 10))
        
        self.add_queue_btn = ctk.CTkButton(
            btn_row,
            text="⏳  เพิ่มเข้าคิวดาวน์โหลด",
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["on_primary"],
            width=180,
            height=42,
            corner_radius=21, # Pill
            font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
            command=self._add_single_video_to_queue
        )
        self.add_queue_btn.pack(side="left")

    def _get_selected_format_details(self):
        selected_text = self.format_dropdown.get()
        if selected_text == "ไม่พบความละเอียดที่เหมาะสม":
            messagebox.showerror("Error", "ไม่พบข้อมูลสตรีมที่ถูกต้องสำหรับการดาวน์โหลด")
            return None
        return self.option_format_map.get(selected_text)

    def _download_single_video_now(self):
        """Immediately adds video to download queue and switches to Queue view so user sees progress."""
        details = self._get_selected_format_details()
        if not details: return
        
        # Add to queue
        self.queue_manager.add_item(
            title=self.current_fetched_video["title"],
            url=self.current_fetched_video["url"],
            format_id=details["format_id"],
            format_label=details["label"],
            is_audio=details["is_audio"],
            size=details["size"]
        )
        
        # Automatically switch to Queue tab
        self._show_queue_page()

    def _add_single_video_to_queue(self):
        """Adds video to download queue silently, popping a small success toast, but staying on single page."""
        details = self._get_selected_format_details()
        if not details: return
        
        self.queue_manager.add_item(
            title=self.current_fetched_video["title"],
            url=self.current_fetched_video["url"],
            format_id=details["format_id"],
            format_label=details["label"],
            is_audio=details["is_audio"],
            size=details["size"]
        )
        messagebox.showinfo("สำเร็จ", f"เพิ่ม '{self.current_fetched_video['title']}' ลงในคิวดาวน์โหลดเรียบร้อยแล้ว!")

    # ==========================================
    # 📋 PAGE 2: PLAYLIST DOWNLOAD PAGE
    # ==========================================
    def _show_playlist_download_page(self):
        self._set_active_button("playlist")
        self._clear_content_frame()

        # Top Header (Plus Jakarta Sans)
        self.playlist_header = ctk.CTkLabel(
            self.content_frame, 
            text="ดาวน์โหลดเพลย์ลิสต์ YouTube", 
            font=ctk.CTkFont(family=FONT_DISPLAY, size=24, weight="bold"),
            text_color=COLORS["on_surface"]
        )
        self.playlist_header.pack(anchor="w", pady=(8, 16))

        # URL Input Row
        self.playlist_url_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.playlist_url_frame.pack(fill="x", pady=8)
        
        # Recessed Entry
        self.playlist_url_entry = ctk.CTkEntry(
            self.playlist_url_frame, 
            placeholder_text="วางลิงก์ Playlist ของ YouTube ที่นี่...",
            height=48,
            font=ctk.CTkFont(family=FONT_BODY, size=13),
            fg_color=COLORS["surface_low"],
            border_color=COLORS["outline_variant"],
            border_width=1,
            text_color=COLORS["on_surface"],
            corner_radius=12
        )
        self.playlist_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._patch_entry_behavior(self.playlist_url_entry)

        # Liquid Primary Pill Button
        self.playlist_fetch_btn = ctk.CTkButton(
            self.playlist_url_frame, 
            text="📋  ดึงข้อมูล Playlist", 
            height=48,
            width=160,
            font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["on_primary"],
            corner_radius=24, # Pill
            command=self._fetch_playlist_info
        )
        self.playlist_fetch_btn.pack(side="right")

        # Container for playlist videos - Level 2 Glass Card
        self.playlist_container = ctk.CTkFrame(
            self.content_frame, 
            fg_color=COLORS["surface"], 
            border_width=1,
            border_color=COLORS["surface_high"],
            corner_radius=24
        )
        self.playlist_container.pack(fill="both", expand=True, pady=(24, 0))
        
        # Display placeholder initially
        self.playlist_placeholder = ctk.CTkLabel(
            self.playlist_container,
            text="📋\n\nพร้อมสำหรับการประมวลผลเพลย์ลิสต์ขนาดใหญ่\n\nวางลิงก์ Playlist ด้านบน แล้วกดปุ่ม 'ดึงข้อมูล Playlist' เพื่อเริ่มงานดาวน์โหลด",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=15, weight="bold"),
            text_color=COLORS["on_surface_variant"],
            justify="center"
        )
        self.playlist_placeholder.pack(expand=True, pady=100)

    def _fetch_playlist_info(self):
        url = self.playlist_url_entry.get().strip()
        if not url:
            messagebox.showwarning("คำเตือน", "กรุณากรอกลิงก์ Playlist ของ YouTube ก่อนครับ")
            return
            
        self.playlist_fetch_btn.configure(state="disabled", text="กำลังอ่านเพลย์ลิสต์...")
        
        for w in self.playlist_container.winfo_children():
            w.destroy()
            
        loading_lbl = ctk.CTkLabel(
            self.playlist_container, 
            text="⚡ กำลังดึงรายชื่อวิดีโอทั้งหมดใน Playlist (ขนาดเพลย์ลิสต์ใหญ่อาจใช้เวลาดึงข้อมูลสักครู่)...",
            font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
            text_color=COLORS["on_surface"]
        )
        loading_lbl.pack(expand=True)
        
        def run():
            try:
                raw_info = self.downloader.fetch_video_info(url)
                
                # Check if it was actually a single video link
                if 'entries' not in raw_info:
                    def ask_single_redirect():
                        self.playlist_fetch_btn.configure(state="normal", text="📋  ดึงข้อมูล Playlist")
                        if messagebox.askyesno("ตรวจพบลิงก์วิดีโอเดี่ยว", "ลิงก์นี้เป็นวิดีโอเดี่ยว คุณต้องการสลับไปยังแท็บดาวน์โหลดวิดีโอเดี่ยวใช่หรือไม่?"):
                            self._show_single_download_page()
                            self.url_entry.insert(0, url)
                            self._fetch_single_video_info()
                        else:
                            self._show_playlist_download_page()
                    self._schedule_ui_update(ask_single_redirect)
                    return
                    
                parsed = self.downloader.parse_formats(raw_info)
                self.current_fetched_playlist = parsed
                self.current_fetched_playlist['url'] = url
                
                def render():
                    self.playlist_fetch_btn.configure(state="normal", text="📋  ดึงข้อมูล Playlist")
                    self._render_playlist_panel()
                self._schedule_ui_update(render)
                
            except Exception as e:
                def on_error():
                    self.playlist_fetch_btn.configure(state="normal", text="📋  ดึงข้อมูล Playlist")
                    for w in self.playlist_container.winfo_children():
                        w.destroy()
                    err_lbl = ctk.CTkLabel(
                        self.playlist_container,
                        text=f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลเพลย์ลิสต์:\n{str(e)}\n\nกรุณาตรวจสอบลิงก์อีกครั้ง",
                        font=ctk.CTkFont(family=FONT_BODY, size=13),
                        text_color=COLORS["error"]
                    )
                    err_lbl.pack(expand=True, pady=50)
                self._schedule_ui_update(on_error)
                
        threading.Thread(target=run, daemon=True).start()

    def _render_playlist_panel(self):
        for w in self.playlist_container.winfo_children():
            w.destroy()
            
        playlist = self.current_fetched_playlist
        entries = playlist.get("entries", [])
        
        # 1. Playlist Header (Title, Total count, Control Actions)
        top_ctrl = ctk.CTkFrame(self.playlist_container, fg_color="transparent")
        top_ctrl.pack(fill="x", padx=20, pady=12)
        
        playlist_title = ctk.CTkLabel(
            top_ctrl, 
            text=f"📁 {playlist.get('title', 'No Title')} ({len(entries)} วิดีโอ)",
            font=ctk.CTkFont(family=FONT_DISPLAY, size=14, weight="bold"),
            text_color=COLORS["on_surface"],
            anchor="w"
        )
        playlist_title.pack(side="left")
        
        # Select all / Deselect all
        def toggle_select_all():
            any_unchecked = any(not var.get() for _, var in self.playlist_checkboxes)
            for _, var in self.playlist_checkboxes:
                var.set(1 if any_unchecked else 0)
                
        self.toggle_btn = ctk.CTkButton(
            top_ctrl,
            text="เลือกทั้งหมด / ไม่เลือก",
            width=150,
            height=30,
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["on_primary"],
            corner_radius=15,
            command=toggle_select_all
        )
        self.toggle_btn.pack(side="right")
        
        # 2. Scrollable list of videos
        self.scrollable_playlist = ctk.CTkScrollableFrame(self.playlist_container, fg_color="transparent")
        self.scrollable_playlist.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        
        self.playlist_checkboxes = []
        
        for idx, entry in enumerate(entries):
            if not entry: continue
            
            row = ctk.CTkFrame(self.scrollable_playlist, height=35, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            var = ctk.IntVar(value=1)
            cb = ctk.CTkCheckBox(
                row, 
                text=f"{idx+1}. {entry.get('title', 'Unknown Title')}", 
                variable=var,
                text_color=COLORS["on_surface"],
                font=ctk.CTkFont(family=FONT_BODY, size=12)
            )
            cb.pack(side="left", fill="x", expand=True)
            
            self.playlist_checkboxes.append((entry, var))

        # 3. Bottom controls (Resolution selection, Queue add)
        bottom_ctrl = ctk.CTkFrame(self.playlist_container, fg_color=COLORS["surface_low"], height=60, corner_radius=16)
        bottom_ctrl.pack(fill="x", padx=20, pady=12)
        
        res_lbl = ctk.CTkLabel(
            bottom_ctrl,
            text="⚙️ คุณภาพความละเอียดที่จะบันทึกทุกคลิป:",
            font=ctk.CTkFont(family=FONT_BODY, size=12, weight="bold"),
            text_color=COLORS["on_surface"]
        )
        res_lbl.pack(side="left", padx=15, pady=15)
        
        self.playlist_resolutions = [
            "1080p (ความละเอียดสูง - Best MP4)",
            "720p (ความคมชัดสูงทั่วไป - 720p MP4)",
            "480p (ขนาดปานกลาง - 480p MP4)",
            "360p (ขนาดประหยัดพื้นที่ - 360p MP4)",
            "Audio MP3 (เฉพาะไฟล์เสียงคุณภาพสูง)"
        ]
        
        self.playlist_format_map = {
            "1080p (ความละเอียดสูง - Best MP4)": {"format_id": "bestvideo[height<=1080]+bestaudio[ext=m4a]/bestaudio/best", "label": "1080p", "is_audio": False},
            "720p (ความคมชัดสูงทั่วไป - 720p MP4)": {"format_id": "bestvideo[height<=720]+bestaudio[ext=m4a]/bestaudio/best", "label": "720p", "is_audio": False},
            "480p (ขนาดปานกลาง - 480p MP4)": {"format_id": "bestvideo[height<=480]+bestaudio[ext=m4a]/bestaudio/best", "label": "480p", "is_audio": False},
            "360p (ขนาดประหยัดพื้นที่ - 360p MP4)": {"format_id": "bestvideo[height<=360]+bestaudio[ext=m4a]/bestaudio/best", "label": "360p", "is_audio": False},
            "Audio MP3 (เฉพาะไฟล์เสียงคุณภาพสูง)": {"format_id": "bestaudio", "label": "Audio MP3", "is_audio": True}
        }
        
        self.playlist_res_dropdown = ctk.CTkOptionMenu(
            bottom_ctrl,
            values=self.playlist_resolutions,
            width=260,
            height=32,
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            fg_color=COLORS["primary"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"]
        )
        self.playlist_res_dropdown.pack(side="left", padx=10, pady=15)
        self.playlist_res_dropdown.set(self.playlist_resolutions[0])
        
        self.playlist_dl_btn = ctk.CTkButton(
            bottom_ctrl,
            text="⚡  ดาวน์โหลดรายการที่เลือก",
            fg_color=COLORS["secondary"],
            hover_color=("#005321", "#36c760"),
            text_color=COLORS["on_primary"],
            height=36,
            corner_radius=18, # Pill
            font=ctk.CTkFont(family=FONT_BODY, size=12, weight="bold"),
            command=self._download_selected_playlist_videos
        )
        self.playlist_dl_btn.pack(side="right", padx=15, pady=12)

    def _download_selected_playlist_videos(self):
        """Queues all selected videos in the playlist and redirects to Queue Page."""
        selected_entries = [entry for entry, var in self.playlist_checkboxes if var.get() == 1]
        
        if not selected_entries:
            messagebox.showwarning("คำเตือน", "กรุณาติ๊กเลือกวิดีโออย่างน้อย 1 รายการก่อนดาวน์โหลดครับ")
            return
            
        selected_format_text = self.playlist_res_dropdown.get()
        details = self.playlist_format_map.get(selected_format_text)
        
        # Add to download queue one by one
        for entry in selected_entries:
            video_url = entry.get('url')
            if not video_url:
                v_id = entry.get('id')
                if v_id:
                    video_url = f"https://www.youtube.com/watch?v={v_id}"
                else:
                    continue
                    
            self.queue_manager.add_item(
                title=entry.get('title', 'YouTube Video'),
                url=video_url,
                format_id=details["format_id"],
                format_label=details["label"],
                is_audio=details["is_audio"],
                size="Unknown"
            )
            
        messagebox.showinfo("สำเร็จ", f"เพิ่มวิดีโอ {len(selected_entries)} คลิปเข้าสู่คิวดาวน์โหลดเรียบร้อยแล้ว!")
        self._show_queue_page()

    # ==========================================
    # ⏳ PAGE 3: DOWNLOAD QUEUE PAGE
    # ==========================================
    def _show_queue_page(self):
        self._set_active_button("queue")
        self._clear_content_frame()
        
        # Header (Plus Jakarta Sans)
        self.queue_header = ctk.CTkLabel(
            self.content_frame, 
            text="คิวการดาวน์โหลดที่ทำงานอยู่เบื้องหลัง", 
            font=ctk.CTkFont(family=FONT_DISPLAY, size=24, weight="bold"),
            text_color=COLORS["on_surface"]
        )
        self.queue_header.pack(anchor="w", pady=(8, 16))
        
        # Main scrollable list containing active download cards - Level 2 Glass Card
        self.queue_scrollable = ctk.CTkScrollableFrame(
            self.content_frame, 
            fg_color=COLORS["surface"], 
            border_width=1,
            border_color=COLORS["surface_high"],
            corner_radius=24
        )
        self.queue_scrollable.pack(fill="both", expand=True)
        
        self._render_queue_page_content()

    def _render_queue_page_content(self):
        # Clear existing elements inside the scrollable container
        for widget in self.queue_scrollable.winfo_children():
            widget.destroy()
            
        items = self.queue_manager.items
        
        if not items:
            empty_lbl = ctk.CTkLabel(
                self.queue_scrollable,
                text="⏳\n\nยังไม่มีรายการดาวน์โหลดในขณะนี้\n\nคุณสามารถเพิ่มรายการดาวน์โหลดจากหน้า 'ดาวน์โหลดวิดีโอเดี่ยว' หรือ 'ดาวน์โหลดเพลย์ลิสต์' ได้ครับ",
                font=ctk.CTkFont(family=FONT_DISPLAY, size=14, weight="bold"),
                text_color=COLORS["on_surface_variant"],
                justify="center"
            )
            empty_lbl.pack(expand=True, pady=120)
            return

        for item in reversed(items):
            # Render a nice queue item card - Glassy Level 2
            card = ctk.CTkFrame(
                self.queue_scrollable, 
                fg_color=COLORS["surface_low"], 
                border_width=1,
                border_color=COLORS["surface_high"],
                corner_radius=16
            )
            card.pack(fill="x", pady=6, padx=8)
            
            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=0)
            
            info_sub = ctk.CTkFrame(card, fg_color="transparent")
            info_sub.grid(row=0, column=0, sticky="nsew", padx=20, pady=12)
            
            # Title using Display font for premium styling
            t_lbl = ctk.CTkLabel(
                info_sub, 
                text=item["title"],
                font=ctk.CTkFont(family=FONT_DISPLAY, size=13, weight="bold"),
                text_color=COLORS["on_surface"],
                anchor="w",
                justify="left",
                wraplength=600
            )
            t_lbl.pack(anchor="w", pady=(0, 6))
            
            # Progress status bar and progress stats
            stats_frame = ctk.CTkFrame(info_sub, fg_color="transparent")
            stats_frame.pack(fill="x", pady=2)
            
            # Glassmorphic status badges config
            badge_config = {
                "Waiting": {"text": "⏳  รอคิว", "bg": COLORS["surface_high"], "fg": COLORS["on_surface_variant"]},
                "Starting": {"text": "⚙️  กำลังเตรียมการ", "bg": "#ffe5d0", "fg": "#d35400"},
                "Downloading": {"text": f"⚡  กำลังดาวน์โหลด {item['progress']}%", "bg": "#d2e4ff", "fg": COLORS["primary"]},
                "Processing...": {"text": "🔄  กำลังรวมไฟล์ (FFmpeg)", "bg": "#f3e5f5", "fg": "#7b1fa2"},
                "Completed": {"text": "🟢  สำเร็จ", "bg": COLORS["secondary_bg"], "fg": COLORS["secondary"]},
                "Failed": {"text": "❌  ล้มเหลว", "bg": COLORS["error_bg"], "fg": COLORS["error"]},
                "Cancelled": {"text": "🛑  ยกเลิก", "bg": "#e9ecef", "fg": "#495057"}
            }
            config = badge_config.get(item["status"], {"text": item["status"], "bg": COLORS["surface_high"], "fg": COLORS["on_surface"]})
            
            # Create Badge with rounded corners
            badge_lbl = ctk.CTkLabel(
                stats_frame,
                text=f"  {config['text']}  ",
                font=ctk.CTkFont(family=FONT_BODY, size=10, weight="bold"),
                fg_color=config["bg"],
                text_color=config["fg"],
                corner_radius=8,
                height=22
            )
            badge_lbl.pack(side="left")
            
            # Create details labels (speed, eta, size, etc.) next to badge
            detail_parts = []
            if item["status"] == "Downloading":
                if item["speed"] and item["speed"] != "0B/s":
                    detail_parts.append(f"⚡  ความเร็ว: {item['speed']}")
                if item["eta"]:
                    detail_parts.append(f"⏱️  เวลาที่เหลือ: {item['eta']}")
            elif item["status"] == "Completed":
                detail_parts.append(f"📁  ขนาดไฟล์: {item['size']}")
            elif item["status"] == "Failed" and item["error_msg"]:
                detail_parts.append(f"⚠️  {item['error_msg']}")
                
            if detail_parts:
                detail_text = "  |  " + "  •  ".join(detail_parts)
                detail_lbl = ctk.CTkLabel(
                    stats_frame,
                    text=detail_text,
                    font=ctk.CTkFont(family=FONT_BODY, size=11),
                    text_color=COLORS["on_surface_variant"]
                )
                detail_lbl.pack(side="left", padx=5)
            
            # Progress bar for active downloads
            if item["status"] in ("Downloading", "Processing...", "Starting", "Completed"):
                pb = ctk.CTkProgressBar(info_sub, height=8, corner_radius=4)
                pb.pack(fill="x", pady=(8, 0))
                pb.set(item["progress"] / 100.0)
                
                # Active progress colors - Aura Streamline style matching statuses
                if item["status"] == "Completed":
                    pb.configure(progress_color=COLORS["secondary"])
                elif item["status"] == "Processing...":
                    pb.configure(progress_color="#7b1fa2")
                else:
                    pb.configure(progress_color=COLORS["primary"])

            # Control buttons on the right side of the card
            btn_sub = ctk.CTkFrame(card, fg_color="transparent")
            btn_sub.grid(row=0, column=1, sticky="ns", padx=20)
            
            # Show Cancel button if download is Active or Waiting
            if item["status"] in ("Waiting", "Downloading", "Starting", "Processing..."):
                cancel_btn = ctk.CTkButton(
                    btn_sub,
                    text="❌  ยกเลิก",
                    width=80,
                    height=28,
                    fg_color=COLORS["error"],
                    hover_color=("#93000a", "#ff8980"),
                    text_color=COLORS["on_primary"],
                    font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
                    corner_radius=14,
                    command=lambda i_id=item["id"]: self.queue_manager.cancel_item(i_id)
                )
                cancel_btn.pack(expand=True)
            elif item["status"] == "Completed" and item["file_path"]:
                # Open directory button (Pill shaped success color)
                open_btn = ctk.CTkButton(
                    btn_sub,
                    text="📁  เปิดไฟล์",
                    width=80,
                    height=28,
                    fg_color=COLORS["secondary"],
                    hover_color=("#005321", "#36c760"),
                    text_color=COLORS["on_primary"],
                    font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
                    corner_radius=14,
                    command=lambda path=item["file_path"]: self._open_file_location(path)
                )
                open_btn.pack(expand=True)

    def _open_file_location(self, file_path):
        """Opens Windows Explorer and highlights the downloaded file."""
        if not file_path: return
        
        # Verify file exists
        if not os.path.exists(file_path):
            messagebox.showerror("Error", "ไม่พบไฟล์ความขัดข้องนี้ในเครื่อง (อาจถูกย้ายหรือลบไปแล้ว)")
            return
            
        try:
            # On Windows, select the specific file in explorer
            if sys.platform == "win32":
                os.system(f'explorer /select,"{os.path.normpath(file_path)}"')
            else:
                # Fallback to parent directory opening
                parent = os.path.dirname(file_path)
                webbrowser.open(parent)
        except Exception as e:
            logging.error(f"Failed to open file path: {e}")

    # ==========================================
    # 📜 PAGE 4: HISTORY PAGE
    # ==========================================
    def _show_history_page(self):
        self._set_active_button("history")
        self._clear_content_frame()
        
        # Header Row
        h_row = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        h_row.pack(fill="x", pady=(8, 16))
        
        # Plus Jakarta Sans Title
        self.history_header = ctk.CTkLabel(
            h_row, 
            text="ประวัติรายการดาวน์โหลดสำเร็จ", 
            font=ctk.CTkFont(family=FONT_DISPLAY, size=24, weight="bold"),
            text_color=COLORS["on_surface"]
        )
        self.history_header.pack(side="left")
        
        # Clear all history button (Pill shaped, error red)
        self.clear_hist_btn = ctk.CTkButton(
            h_row,
            text="🧹  ล้างประวัติทั้งหมด",
            fg_color=COLORS["error"],
            hover_color=("#93000a", "#ff8980"),
            text_color=COLORS["on_primary"],
            width=140,
            height=36,
            corner_radius=18,
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            command=self._clear_all_history
        )
        self.clear_hist_btn.pack(side="right")
        
        # Main history container - Level 2 Glass Card
        self.history_scrollable = ctk.CTkScrollableFrame(
            self.content_frame, 
            fg_color=COLORS["surface"], 
            border_width=1,
            border_color=COLORS["surface_high"],
            corner_radius=24
        )
        self.history_scrollable.pack(fill="both", expand=True)
        
        self._render_history_list()

    def _render_history_list(self):
        for widget in self.history_scrollable.winfo_children():
            widget.destroy()
            
        records = self.history_db.get_all_records()
        
        if not records:
            empty_lbl = ctk.CTkLabel(
                self.history_scrollable,
                text="📜\n\nยังไม่มีประวัติการดาวน์โหลดสำเร็จในเครื่องนี้\n\nดาวน์โหลดสำเร็จรายการแรกแล้วจะมาแสดงที่นี่ครับ!",
                font=ctk.CTkFont(family=FONT_DISPLAY, size=14, weight="bold"),
                text_color=COLORS["on_surface_variant"],
                justify="center"
            )
            empty_lbl.pack(expand=True, pady=120)
            return

        for rec in records:
            # Aura Streamline Level 2 Glass Panel card
            card = ctk.CTkFrame(
                self.history_scrollable, 
                fg_color=COLORS["surface_low"], 
                border_width=1,
                border_color=COLORS["surface_high"],
                corner_radius=16
            )
            card.pack(fill="x", pady=6, padx=8)
            
            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=0)
            
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
            
            t_lbl = ctk.CTkLabel(
                info_frame, 
                text=rec["title"],
                font=ctk.CTkFont(family=FONT_DISPLAY, size=12, weight="bold"),
                text_color=COLORS["on_surface"],
                anchor="w",
                justify="left",
                wraplength=600
            )
            t_lbl.pack(anchor="w", pady=(0, 4))
            
            # Format datetime
            try:
                from datetime import datetime
                dt = datetime.strptime(rec["timestamp"], "%Y-%m-%d %H:%M:%S")
                dt_str = dt.strftime("%d/%m/%Y %H:%M")
            except:
                dt_str = rec["timestamp"]
                
            # Render visual badges for format and size
            stats_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
            stats_frame.pack(fill="x", pady=2)
            
            is_audio = "Audio" in rec["format_name"] or "MP3" in rec["format_name"]
            fmt_icon = "🎵 " if is_audio else "🎬 "
            fmt_bg = COLORS["secondary_bg"] if is_audio else "#d2e4ff"
            fmt_fg = COLORS["secondary"] if is_audio else COLORS["primary"]
            
            # 1. Format badge
            fmt_lbl = ctk.CTkLabel(
                stats_frame,
                text=f"  {fmt_icon}{rec['format_name']}  ",
                font=ctk.CTkFont(family=FONT_BODY, size=9, weight="bold"),
                fg_color=fmt_bg,
                text_color=fmt_fg,
                corner_radius=6,
                height=18
            )
            fmt_lbl.pack(side="left")
            
            # 2. Size badge
            size_lbl = ctk.CTkLabel(
                stats_frame,
                text=f"  📁 {rec['file_size']}  ",
                font=ctk.CTkFont(family=FONT_BODY, size=9, weight="bold"),
                fg_color=COLORS["surface_high"],
                text_color=COLORS["on_surface_variant"],
                corner_radius=6,
                height=18
            )
            size_lbl.pack(side="left", padx=5)
            
            # 3. Timestamp text
            time_lbl = ctk.CTkLabel(
                stats_frame,
                text=f"  ⏱️ บันทึกเมื่อ: {dt_str}",
                font=ctk.CTkFont(family=FONT_BODY, size=11),
                text_color=COLORS["on_surface_variant"]
            )
            time_lbl.pack(side="left", padx=5)
            
            # Right side actions
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=0, column=1, sticky="ns", padx=20)
            
            # Open file button (Pill-shaped primary color)
            open_btn = ctk.CTkButton(
                btn_frame,
                text="📁  เปิดไฟล์",
                width=80,
                height=28,
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"],
                text_color=COLORS["on_primary"],
                corner_radius=14,
                font=ctk.CTkFont(family=FONT_BODY, size=10, weight="bold"),
                command=lambda path=rec["file_path"]: self._open_file_location(path)
            )
            open_btn.pack(side="left", padx=(0, 5))
            
            # Delete individual record row from db
            del_btn = ctk.CTkButton(
                btn_frame,
                text="🗑️",
                width=30,
                height=28,
                fg_color=COLORS["error"],
                hover_color=("#93000a", "#ff8980"),
                text_color=COLORS["on_primary"],
                corner_radius=14,
                font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
                command=lambda r_id=rec["id"]: self._delete_individual_history(r_id)
            )
            del_btn.pack(side="left")

    def _delete_individual_history(self, rec_id):
        self.history_db.delete_record(rec_id)
        self._render_history_list()

    def _clear_all_history(self):
        if not self.history_db.get_all_records(): return
        if messagebox.askyesno("ยืนยันการล้างประวัติ", "คุณแน่ใจหรือไม่ว่าต้องการล้างประวัติการดาวน์โหลดทั้งหมด? (ไฟล์วิดีโอตัวจริงในเครื่องจะไม่ถูกลบ)"):
            self.history_db.clear_all()
            self._render_history_list()

    def _show_settings_page(self):
        self._set_active_button("settings")
        self._clear_content_frame()
        
        # Header (Plus Jakarta Sans)
        self.settings_header = ctk.CTkLabel(
            self.content_frame, 
            text="ตั้งค่าความปลอดภัยและโฟลเดอร์ดาวน์โหลด", 
            font=ctk.CTkFont(family=FONT_DISPLAY, size=24, weight="bold"),
            text_color=COLORS["on_surface"]
        )
        self.settings_header.pack(anchor="w", pady=(8, 16))
        
        # Settings frame container - Level 2 Glass Card
        settings_box = ctk.CTkFrame(
            self.content_frame, 
            fg_color=COLORS["surface"], 
            border_width=1,
            border_color=COLORS["surface_high"],
            corner_radius=24
        )
        settings_box.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Padding content inside settings box
        inner_box = ctk.CTkFrame(settings_box, fg_color="transparent")
        inner_box.pack(fill="both", expand=True, padx=25, pady=25)
        
        # Row 1: Folder selection path
        dir_lbl = ctk.CTkLabel(
            inner_box,
            text="📁 โฟลเดอร์ปลายทางหลักสำหรับการดาวน์โหลดสำเร็จ:",
            font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
            text_color=COLORS["on_surface"]
        )
        dir_lbl.pack(anchor="w", pady=(0, 5))
        
        dir_row = ctk.CTkFrame(inner_box, fg_color="transparent")
        dir_row.pack(fill="x", pady=(0, 20))
        
        # Recessed Entry
        self.dir_entry = ctk.CTkEntry(
            dir_row,
            height=36,
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            fg_color=COLORS["surface_low"],
            border_color=COLORS["outline_variant"],
            border_width=1,
            text_color=COLORS["on_surface"],
            corner_radius=12
        )
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.dir_entry.insert(0, self.downloader.download_dir)
        self.dir_entry.configure(state="disabled") # Only allow folder picker to edit
        
        # Liquid Primary Pill Button
        browse_btn = ctk.CTkButton(
            dir_row,
            text="📁  เลือกโฟลเดอร์",
            width=140,
            height=36,
            font=ctk.CTkFont(family=FONT_BODY, size=12, weight="bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["on_primary"],
            corner_radius=18, # Pill
            command=self._browse_download_folder
        )
        browse_btn.pack(side="right")
 
        # Row 2: Theme appearance
        theme_lbl = ctk.CTkLabel(
            inner_box,
            text="🎨 ธีมหน้าต่าง GUI แอปพลิเคชัน:",
            font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
            text_color=COLORS["on_surface"]
        )
        theme_lbl.pack(anchor="w", pady=(5, 5))
        
        self.theme_dropdown = ctk.CTkOptionMenu(
            inner_box,
            values=["ระบบหลัก (System default)", "มืดสลัว (Dark theme)", "สว่างอบอุ่น (Light theme)"],
            width=260,
            height=32,
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            fg_color=COLORS["primary"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            command=self._change_ui_appearance
        )
        self.theme_dropdown.pack(anchor="w", pady=(0, 20))
        
        # Initialize dropdown based on customtkinter actual state
        actual_mode = ctk.get_appearance_mode()
        if actual_mode == "Dark":
            self.theme_dropdown.set("มืดสลัว (Dark theme)")
        elif actual_mode == "Light":
            self.theme_dropdown.set("สว่างอบอุ่น (Light theme)")
        else:
            self.theme_dropdown.set("ระบบหลัก (System default)")
 
        # Row 3: Info & Credits - Recessed Panel
        info_frame = ctk.CTkFrame(
            inner_box, 
            fg_color=COLORS["surface_low"], 
            corner_radius=16,
            border_width=1,
            border_color=COLORS["surface_high"]
        )
        info_frame.pack(fill="x", pady=15)
        
        info_content = ctk.CTkLabel(
            info_frame,
            text="ℹ️ เกี่ยวกับโปรแกรม:\n"
                 "- พัฒนาเป็นกรณีพิเศษเพื่อความรวดเร็วและความปลอดภัยสูงสุด\n"
                 "- ดึงขุมพลังจากเอนจิ้น yt-dlp และ FFmpeg ประมวลผลลื่นไหล 100%\n"
                 "- รองรับการดาวน์โหลด Playlist ครบวงจร และแปลงไฟล์เสียงความละเอียดสูง\n"
                 "- โครงการคู่มือการใช้งานและรายงานมีให้เปิดอ่านที่ README.md เสนอ",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            text_color=COLORS["on_surface_variant"]
        )
        info_content.pack(padx=15, pady=15)

    def _browse_download_folder(self):
        selected_dir = filedialog.askdirectory(initialdir=self.downloader.download_dir)
        if selected_dir:
            self.downloader.download_dir = selected_dir
            self.dir_entry.configure(state="normal")
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, selected_dir)
            self.dir_entry.configure(state="disabled")

    def _change_ui_appearance(self, value):
        if "Dark" in value or "มืด" in value:
            ctk.set_appearance_mode("dark")
        elif "Light" in value or "สว่าง" in value:
            ctk.set_appearance_mode("light")
        else:
            ctk.set_appearance_mode("system")

    def _patch_entry_behavior(self, entry):
        """Patches entry widget to support layout-independent shortcuts (Ctrl+C, Ctrl+V, etc. on non-English layouts) and adds a modern right-click context menu."""
        
        # 1. Keyboard layout independent shortcuts (Windows Virtual Keycodes)
        def handle_control_key(event):
            # event.state & 4 checks if Control key is held down
            # Keycodes: A=65, C=67, V=86, X=88
            if event.state & 4:
                keycode = event.keycode
                if keycode == 86:  # V (Paste)
                    try:
                        text = entry.clipboard_get()
                        try:
                            # Delete selected text first if any
                            entry.delete("sel.first", "sel.last")
                        except:
                            pass
                        entry.insert("insert", text)
                    except Exception as e:
                        logging.error(f"Clipboard paste error: {e}")
                    return "break"
                    
                elif keycode == 67:  # C (Copy)
                    try:
                        text = entry.selection_get()
                        entry.clipboard_clear()
                        entry.clipboard_append(text)
                    except Exception as e:
                        pass
                    return "break"
                    
                elif keycode == 88:  # X (Cut)
                    try:
                        text = entry.selection_get()
                        entry.clipboard_clear()
                        entry.clipboard_append(text)
                        entry.delete("sel.first", "sel.last")
                    except Exception as e:
                        pass
                    return "break"
                    
                elif keycode == 65:  # A (Select All)
                    entry.select_range(0, "end")
                    entry.icursor("end")
                    return "break"
                    
        entry.bind("<Control-KeyPress>", handle_control_key)
        
        # 2. Modern Right-click context menu (Copy / Paste / Cut / Select All)
        import tkinter as tk
        
        # Determine current color based on active appearance mode (for standard tk.Menu initialization)
        is_dark = ctk.get_appearance_mode() == "Dark"
        idx = 1 if is_dark else 0
        bg_color = COLORS["surface"][idx]
        fg_color = COLORS["on_surface"][idx]
        active_bg = COLORS["surface_high"][idx]
        
        menu = tk.Menu(
            entry, 
            tearoff=0, 
            fg=fg_color, 
            bg=bg_color, 
            activebackground=active_bg, 
            activeforeground=fg_color, 
            borderwidth=1,
            relief="flat"
        )
        
        # Implement same direct commands for the context menu to be 100% reliable
        def menu_paste():
            try:
                text = entry.clipboard_get()
                try: entry.delete("sel.first", "sel.last")
                except: pass
                entry.insert("insert", text)
            except: pass
            
        def menu_copy():
            try:
                text = entry.selection_get()
                entry.clipboard_clear()
                entry.clipboard_append(text)
            except: pass
            
        def menu_cut():
            try:
                text = entry.selection_get()
                entry.clipboard_clear()
                entry.clipboard_append(text)
                entry.delete("sel.first", "sel.last")
            except: pass
            
        menu.add_command(label="📋 วาง (Paste)", command=menu_paste)
        menu.add_command(label="📝 คัดลอก (Copy)", command=menu_copy)
        menu.add_command(label="✂️ ตัด (Cut)", command=menu_cut)
        menu.add_separator()
        menu.add_command(label="🔍 เลือกทั้งหมด (Select All)", command=lambda: entry.select_range(0, "end"))
        
        def show_menu(event):
            entry.focus_set()
            # Dynamically update menu colors to match current theme before posting
            is_dark_now = ctk.get_appearance_mode() == "Dark"
            idx_now = 1 if is_dark_now else 0
            menu.configure(
                fg=COLORS["on_surface"][idx_now], 
                bg=COLORS["surface"][idx_now], 
                activebackground=COLORS["surface_high"][idx_now], 
                activeforeground=COLORS["on_surface"][idx_now]
            )
            menu.post(event.x_root, event.y_root)
            
        entry.bind("<Button-3>", show_menu)


# Main execution loop
if __name__ == "__main__":
    app = YTDownloaderApp()
    app.mainloop()
