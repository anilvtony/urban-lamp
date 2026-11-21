"""
Auto Video Creator Studio - Desktop Application
------------------------------------------------
Features:
1. Dynamic Latest Project Folder Auto-Detection:
   - Detects the latest project folder in 'Fasting Series' with Images/ and Audio/ subfolders.
2. Single Animation Style Per Video with Video-to-Video Shuffle/Cycle:
   - "Auto-Cycle 25 Styles (1 Style Per Video)": Every video has 1 uniform style, and next video cycles to the next style.
   - Or choose any specific style manually.
3. Interactive Real-time Video Preview Player with SYNCHRONIZED AUDIO:
   - Play/Pause with real synchronized sound via pygame.mixer.
   - Rewind (-5s, -10s), Fast Forward (+5s, +10s), live slider scrubbing.
4. Interactive Drag-and-Drop / Click Repositioning Tool:
   - Visually preview any scene frame and reposition the text badge anywhere in clean cream space.
   - Real-time coordinates update so no background artwork or text is ever blocked.
"""

import os
import sys
import re
import math
import subprocess
import json
import wave
import time
import random
import threading
import numpy as np
from PIL import Image, ImageTk
import cv2

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Initialize pygame mixer for synchronized preview audio
try:
    import pygame
    pygame.mixer.init(frequency=44100)
    HAS_PYGAME_AUDIO = True
except Exception:
    HAS_PYGAME_AUDIO = False

from animations_engine import ANIMATION_STYLES_LIST, render_badge_advanced, stamp_badge_final

WIDTH = 1080
HEIGHT = 1920
FPS = 30
SAMPLE_RATE = 44100
WORKSPACE = r"c:\Users\aanil\Documents\Auto_Video_Editing"
BADGE_DIR = os.path.join(WORKSPACE, "rendered_badges")
SERIES_ROOT = r"C:\Users\aanil\Documents\Anxious Anil\Shorts Videos\Projects\Fasting Series"
STATE_FILE = os.path.join(WORKSPACE, "animation_cycle_state.json")
POSITIONS_FILE = os.path.join(WORKSPACE, "manual_badge_positions.json")
PREVIEW_AUDIO_WAV = os.path.join(WORKSPACE, "temp_preview_audio.wav")

def detect_latest_project_folder(root_dir=SERIES_ROOT):
    if not os.path.exists(root_dir):
        return None
    subdirs = [os.path.join(root_dir, d) for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
    valid_subdirs = [
        d for d in subdirs 
        if os.path.isdir(os.path.join(d, "Images")) and os.path.isdir(os.path.join(d, "Audio"))
    ]
    if not valid_subdirs:
        return None
    return max(valid_subdirs, key=os.path.getmtime)

def get_next_cycle_style():
    state = {"last_index": -1}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except Exception:
            state = {"last_index": -1}
    next_idx = (state.get("last_index", -1) + 1) % len(ANIMATION_STYLES_LIST)
    return ANIMATION_STYLES_LIST[next_idx], next_idx

def advance_cycle_style():
    style, next_idx = get_next_cycle_style()
    state = {"last_index": next_idx, "last_style": style}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    return style, next_idx

from badge_catalog_manager import render_single_badge_to_disk

DEFAULT_BADGE_MAP = {
    "1": [("p2_b1.png", "Welcome Back! 👋", "#E8B931", "#1B2A4A", "#1B2A4A", 46, False)],
    "2": [("p2_b2.png", "ఆకలితో ఉండటమే Fasting ఆ?", "#FAF6F0", "#1B2A4A", "#1B2A4A", 44, False)],
    "3": [("p2_b3.png", "Digestive Systemకి Rest ఏదీ?", "#E8B931", "#1B2A4A", "#1B2A4A", 44, False)],
    "4": [("p2_b4.png", "16 HRS = BACKUP SYSTEM ON! ⚡", "#FAF6F0", "#C84B28", "#C84B28", 42, False)],
    "5": [("p2_b5.png", "తినడం ఆపితే లోపల ఏం జరుగుతుంది?", "#E8B931", "#1B2A4A", "#1B2A4A", 42, False)],
    "6": [("p2_b6.png", "Simpleగా Break Down చేద్దాం!", "#5B8C5A", "#1B2A4A", "#1B2A4A", 44, False)],
    "7": [("p2_b7.png", "Glucose = Direct Phone Charger", "#FAF6F0", "#1B2A4A", "#1B2A4A", 42, False)],
    "8_1": [("p2_b8_1.png", "INSULIN ⬇", "#FAF6F0", "#1B2A4A", "#1B2A4A", 44, False)],
    "8_2": [("p2_b8_2.png", "FAT CELLS OPEN 🔑", "#E8B931", "#1B2A4A", "#1B2A4A", 44, False)],
    "9": [("p2_b9.png", "Insulin Down = Fat Unlock Signal", "#FAF6F0", "#1B2A4A", "#1B2A4A", 42, False)],
    "10": [("p2_b10.png", "16 Hours: Autophagy Cleaning!", "#E8B931", "#C84B28", "#1B2A4A", 42, False)],
    "11_1": [("p2_b11_1.png", "GLUCOSE = CASH 💵", "#5B8C5A", "#1B2A4A", "#1B2A4A", 44, False)],
    "11_2": [("p2_b11_2.png", "FAT = BANK FD 🏦", "#E8B931", "#1B2A4A", "#1B2A4A", 44, False)],
    "12": [("p2_b12.png", "నిద్రలోనూ చిన్న Fasting జరుగుతుంది...", "#FAF6F0", "#1B2A4A", "#1B2A4A", 42, False)],
    "13_1": [("p2_b13_1.png", "BODY WEAK అవ్వదు! 💪", "#E8B931", "#1B2A4A", "#1B2A4A", 44, False)],
    "13_2": [("p2_b13_2.png", "FREE CLEANING BREAK!", "#E8B931", "#C84B28", "#1B2A4A", 46, False)],
    "14": [("p2_b14.png", "Subscribe & Comment Below!", "#FAF6F0", "#1B2A4A", "#1B2A4A", 44, False)]
}

def load_manual_positions():
    default_positions = {
        "1": {"x": 540, "y": 95, "scale": 1.0, "text": "Welcome Back! 👋"},
        "2": {"x": 540, "y": 130, "scale": 1.0, "text": "ఆకలితో ఉండటమే Fasting ఆ?"},
        "3": {"x": 540, "y": 170, "scale": 1.0, "text": "Digestive Systemకి Rest ఏదీ?"},
        "4": {"x": 540, "y": 90, "scale": 1.0, "text": "16 HRS = BACKUP SYSTEM ON! ⚡"},
        "5": {"x": 540, "y": 120, "scale": 1.0, "text": "తినడం ఆపితే లోపల ఏం జరుగుతుంది?"},
        "6": {"x": 540, "y": 1600, "scale": 1.0, "text": "Simpleగా Break Down చేద్దాం!"},
        "7": {"x": 540, "y": 120, "scale": 1.0, "text": "Glucose = Direct Phone Charger"},
        "8_1": {"x": 540, "y": 110, "scale": 1.0, "text": "INSULIN ⬇"},
        "8_2": {"x": 540, "y": 250, "scale": 1.0, "text": "FAT CELLS OPEN 🔑"},
        "9": {"x": 540, "y": 170, "scale": 1.0, "text": "Insulin Down = Fat Unlock Signal"},
        "10": {"x": 540, "y": 1600, "scale": 1.0, "text": "16 Hours: Autophagy Cleaning!"},
        "11_1": {"x": 540, "y": 120, "scale": 1.0, "text": "GLUCOSE = CASH 💵"},
        "11_2": {"x": 540, "y": 260, "scale": 1.0, "text": "FAT = BANK FD 🏦"},
        "12": {"x": 540, "y": 160, "scale": 1.0, "text": "నిద్రలోనూ చిన్న Fasting జరుగుతుంది..."},
        "13_1": {"x": 540, "y": 110, "scale": 1.0, "text": "BODY WEAK అవ్వదు! 💪"},
        "13_2": {"x": 540, "y": 250, "scale": 1.0, "text": "FREE CLEANING BREAK!"},
        "14": {"x": 540, "y": 1600, "scale": 1.0, "text": "Subscribe & Comment Below!"}
    }
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, "r") as f:
                saved = json.load(f)
                for k, v in saved.items():
                    if isinstance(v, int):
                        if k in default_positions:
                            default_positions[k]["y"] = v
                        else:
                            default_positions[k] = {"x": 540, "y": v, "scale": 1.0, "text": ""}
                    elif isinstance(v, dict):
                        if k in default_positions:
                            default_positions[k].update(v)
                        else:
                            default_positions[k] = v
        except Exception:
            pass
    return default_positions

def save_manual_positions(positions_dict):
    with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(positions_dict, f, indent=2, ensure_ascii=False)

def read_image_utf8(path):
    pil_im = Image.open(path).convert('RGB')
    return cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)

def get_audio_duration(path):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return float(json.loads(res.stdout)['format']['duration'])

def load_audio_samples(path):
    with wave.open(path, 'rb') as w:
        n_channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        framerate = w.getframerate()
        n_frames = w.getnframes()
        data = w.readframes(n_frames)
    
    if sampwidth == 2:
        dtype = np.int16
    elif sampwidth == 4:
        dtype = np.int32
    else:
        dtype = np.uint8
        
    samples = np.frombuffer(data, dtype=dtype)
    if n_channels == 2:
        samples = samples.reshape(-1, 2)
    else:
        samples = np.column_stack((samples, samples))
        
    if framerate != SAMPLE_RATE:
        new_len = int(len(samples) * SAMPLE_RATE / framerate)
        left = np.interp(np.linspace(0, len(samples), new_len), np.arange(len(samples)), samples[:, 0])
        right = np.interp(np.linspace(0, len(samples), new_len), np.arange(len(samples)), samples[:, 1])
        samples = np.column_stack((left, right)).astype(np.int16)
        
    return samples

class AutoVideoStudioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto Video Creator Studio - Manual Badge Repositioning & Audio Player")
        self.geometry("1160x870")
        self.minsize(1020, 780)
        self.configure(bg="#0F172A")
        
        # Styles
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("TLabel", background="#0F172A", foreground="#F8FAFC", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#F59E0B")
        self.style.configure("TButton", font=("Segoe UI", 9, "bold"), background="#1E293B", foreground="#F8FAFC")
        self.style.map("TButton", background=[("active", "#334155")])
        self.style.configure("TCombobox", fieldbackground="#0F172A", foreground="#F8FAFC", background="#1E293B")

        # Discover latest project folder
        latest_folder = detect_latest_project_folder()
        if latest_folder:
            default_img = os.path.join(latest_folder, "Images")
            default_aud = os.path.join(latest_folder, "Audio")
            # Look for existing mp4 inside folder
            mp4s = [f for f in os.listdir(latest_folder) if f.lower().endswith('.mp4')]
            if mp4s:
                default_out = os.path.join(latest_folder, mp4s[0])
            else:
                default_out = os.path.join(WORKSPACE, "Fasting_Series_Latest.mp4")
        else:
            default_img = ""
            default_aud = ""
            default_out = os.path.join(WORKSPACE, "output.mp4")

        self.img_dir_var = tk.StringVar(value=default_img)
        self.aud_dir_var = tk.StringVar(value=default_aud)
        self.edit_dir_var = tk.StringVar(value=os.path.join(WORKSPACE, "Editing_Directions.txt"))
        self.trans_var = tk.StringVar(value=os.path.join(WORKSPACE, "transcribe.txt"))
        self.out_video_var = tk.StringVar(value=default_out)
        
        next_s, next_idx = get_next_cycle_style()
        self.anim_mode_var = tk.StringVar(value=f"Cycle Style Per Video (Next: {next_s})")
        self.enable_anim_var = tk.BooleanVar(value=True)

        # Badge Positions and Editing
        self.badge_positions = load_manual_positions()
        self.selected_scene_var = tk.StringVar(value="Scene 4")
        self.x_pos_var = tk.IntVar(value=540)
        self.y_pos_var = tk.IntVar(value=90)
        self.scale_var = tk.DoubleVar(value=1.0)
        self.text_edit_var = tk.StringVar(value="16 HRS = BACKUP SYSTEM ON! ⚡")

        # Video Player state
        self.cap = None
        self.is_playing = False
        self.video_total_frames = 0
        self.video_fps = 30.0
        self.current_frame_idx = 0
        self.is_rendering = False
        self.has_audio_loaded = False
        self.play_start_time = 0.0
        self.play_start_frame = 0

        self.create_widgets()
        
        # Auto-load video if available
        if os.path.exists(self.out_video_var.get()):
            self.load_video_file(self.out_video_var.get())

    def create_widgets(self):
        # Header
        hdr = tk.Frame(self, bg="#0F172A")
        hdr.pack(fill=tk.X, padx=20, pady=(12, 6))
        lbl_title = ttk.Label(hdr, text="🎬 Auto Video Creator Studio (Manual Badge Repositioning & Audio Player)", style="Header.TLabel")
        lbl_title.pack(anchor=tk.W)
        lbl_desc = ttk.Label(hdr, text="Reposition badges onto clear background with live visual preview. Video player plays synchronized audio.")
        lbl_desc.pack(anchor=tk.W)

        # Main Split: Left = Config & Repositioning, Right = Preview Player with Audio
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#0F172A", sashwidth=4)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        left_frame = tk.Frame(main_paned, bg="#0F172A")
        right_frame = tk.Frame(main_paned, bg="#1E293B", relief=tk.RIDGE, bd=1)
        main_paned.add(left_frame, minsize=550)
        main_paned.add(right_frame, minsize=400)

        # --- LEFT 1: Project Configuration ---
        cfg_frame = tk.LabelFrame(left_frame, text=" Project Assets (Auto-Detected Latest Folder) ", bg="#1E293B", fg="#F59E0B", font=("Segoe UI", 10, "bold"), padx=10, pady=6)
        cfg_frame.pack(fill=tk.X, pady=(0, 6))

        btn_auto_detect = tk.Button(cfg_frame, text="🔄 Auto-Detect Latest Project Folder", bg="#0284C7", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, pady=2, command=self.refresh_latest_folder)
        btn_auto_detect.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 4))

        self.add_browse_row(cfg_frame, "📁 Images Folder:", self.img_dir_var, self.browse_img_dir, 1)
        self.add_browse_row(cfg_frame, "🎵 Audio Folder:", self.aud_dir_var, self.browse_aud_dir, 2)
        self.add_browse_row(cfg_frame, "💾 Export Video:", self.out_video_var, self.browse_out_video, 3)

        # --- LEFT 2: Manual Badge Repositioning, Text Editing & Size Control Section ---
        pos_box = tk.LabelFrame(left_frame, text=" 📍 Badge Editor (X/Y Movement, Size & Text Editing) ", bg="#1E293B", fg="#10B981", font=("Segoe UI", 10, "bold"), padx=10, pady=6)
        pos_box.pack(fill=tk.X, pady=(0, 6))

        # Row 1: Scene Selector & Sub-badge (if multi)
        row1 = tk.Frame(pos_box, bg="#1E293B")
        row1.pack(fill=tk.X, pady=2)
        lbl_sc = tk.Label(row1, text="Scene:", bg="#1E293B", fg="white", font=("Segoe UI", 9, "bold"))
        lbl_sc.pack(side=tk.LEFT, padx=(0, 4))
        scenes_list = [f"Scene {i}" for i in range(1, 15)]
        self.cmb_scene = ttk.Combobox(row1, values=scenes_list, textvariable=self.selected_scene_var, state="readonly", width=10)
        self.cmb_scene.pack(side=tk.LEFT, padx=4)
        self.cmb_scene.bind("<<ComboboxSelected>>", self.on_scene_selected)

        # Editable Text Field
        lbl_txt = tk.Label(row1, text="Text:", bg="#1E293B", fg="white", font=("Segoe UI", 9, "bold"))
        lbl_txt.pack(side=tk.LEFT, padx=(10, 4))
        self.ent_text = ttk.Entry(row1, textvariable=self.text_edit_var, width=28)
        self.ent_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.ent_text.bind("<KeyRelease>", self.on_text_edited)

        # Row 2: Y-Axis Movement Slider
        row_y = tk.Frame(pos_box, bg="#1E293B")
        row_y.pack(fill=tk.X, pady=2)
        lbl_y = tk.Label(row_y, text="Y-Axis (Up/Down):", bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 8), width=16, anchor=tk.W)
        lbl_y.pack(side=tk.LEFT)
        self.y_slider = ttk.Scale(row_y, from_=50, to=1750, variable=self.y_pos_var, command=self.on_y_slider_moved)
        self.y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.lbl_y_val = tk.Label(row_y, text="90px", bg="#1E293B", fg="#38BDF8", font=("Consolas", 9, "bold"), width=6)
        self.lbl_y_val.pack(side=tk.LEFT)

        # Row 3: X-Axis Movement Slider
        row_x = tk.Frame(pos_box, bg="#1E293B")
        row_x.pack(fill=tk.X, pady=2)
        lbl_x = tk.Label(row_x, text="X-Axis (Left/Right):", bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 8), width=16, anchor=tk.W)
        lbl_x.pack(side=tk.LEFT)
        self.x_slider = ttk.Scale(row_x, from_=100, to=980, variable=self.x_pos_var, command=self.on_x_slider_moved)
        self.x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.lbl_x_val = tk.Label(row_x, text="540px", bg="#1E293B", fg="#38BDF8", font=("Consolas", 9, "bold"), width=6)
        self.lbl_x_val.pack(side=tk.LEFT)

        # Row 4: Size / Scale Slider & Save Button
        row4 = tk.Frame(pos_box, bg="#1E293B")
        row4.pack(fill=tk.X, pady=2)
        lbl_sz = tk.Label(row4, text="Size (Decrease/Scale):", bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 8), width=16, anchor=tk.W)
        lbl_sz.pack(side=tk.LEFT)
        self.scale_slider = ttk.Scale(row4, from_=0.4, to=1.4, variable=self.scale_var, command=self.on_scale_slider_moved)
        self.scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.lbl_scale_val = tk.Label(row4, text="100%", bg="#1E293B", fg="#F59E0B", font=("Consolas", 9, "bold"), width=6)
        self.lbl_scale_val.pack(side=tk.LEFT)

        btn_apply_pos = tk.Button(row4, text="💾 Save Changes for Scene", bg="#059669", fg="white", font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=8, pady=2, command=self.save_current_position)
        btn_apply_pos.pack(side=tk.LEFT, padx=(6, 0))

        # --- LEFT 3: 25 Animation Modes ---
        anim_box = tk.LabelFrame(left_frame, text=" 25 Animation Styles Engine ", bg="#1E293B", fg="#38BDF8", font=("Segoe UI", 10, "bold"), padx=10, pady=6)
        anim_box.pack(fill=tk.X, pady=(0, 6))

        next_s, _ = get_next_cycle_style()
        modes = [f"Cycle Style Per Video (Next: {next_s})"] + ANIMATION_STYLES_LIST
        self.cmb_anim = ttk.Combobox(anim_box, values=modes, textvariable=self.anim_mode_var, state="readonly", width=45)
        self.cmb_anim.pack(fill=tk.X, pady=2)

        # Render Button & Progress
        self.btn_render = tk.Button(left_frame, text="🚀 START VIDEO RENDER", bg="#F59E0B", fg="#0F172A", font=("Segoe UI", 11, "bold"), relief=tk.FLAT, pady=6, command=self.start_render_thread)
        self.btn_render.pack(fill=tk.X, pady=4)

        self.progress_bar = ttk.Progressbar(left_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=2)

        self.lbl_status = ttk.Label(left_frame, text="Ready. Reposition badges or click Start Video Render.")
        self.lbl_status.pack(anchor=tk.W, pady=(0, 4))

        # Log Console
        log_frame = tk.LabelFrame(left_frame, text=" Build Console & Logs ", bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 9), padx=6, pady=4)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_log = tk.Text(log_frame, bg="#0F172A", fg="#38BDF8", insertbackground="white", font=("Consolas", 8), relief=tk.FLAT, height=6)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.txt_log.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log['yscrollcommand'] = scroll.set

        # --- RIGHT: Video Preview Player (9:16 Canvas & Synchronized Audio) ---
        lbl_p_title = tk.Label(right_frame, text="📺 Video Preview Player (Synchronized Audio)", bg="#1E293B", fg="#F59E0B", font=("Segoe UI", 11, "bold"))
        lbl_p_title.pack(pady=(8, 2))

        # 9:16 Canvas
        self.canvas_w = 270
        self.canvas_h = 480
        self.preview_canvas = tk.Canvas(right_frame, width=self.canvas_w, height=self.canvas_h, bg="#000000", highlightthickness=0)
        self.preview_canvas.pack(pady=4)

        # Scrubber Slider
        self.slider_var = tk.DoubleVar()
        self.slider = ttk.Scale(right_frame, orient=tk.HORIZONTAL, from_=0, to=100, variable=self.slider_var, command=self.on_slider_scroll)
        self.slider.pack(fill=tk.X, padx=20, pady=(4, 2))

        # Timecode Label
        self.lbl_timecode = tk.Label(right_frame, text="00:00 / 00:00 (Frame 0)", bg="#1E293B", fg="#94A3B8", font=("Consolas", 9))
        self.lbl_timecode.pack(pady=(0, 4))

        # Player Controls Buttons
        ctrl_frame = tk.Frame(right_frame, bg="#1E293B")
        ctrl_frame.pack(pady=(0, 6))

        btn_r10 = tk.Button(ctrl_frame, text="⏪ -10s", bg="#334155", fg="white", font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=6, command=lambda: self.seek_seconds(-10))
        btn_r10.pack(side=tk.LEFT, padx=3)

        btn_r5 = tk.Button(ctrl_frame, text="◀ -5s", bg="#334155", fg="white", font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=6, command=lambda: self.seek_seconds(-5))
        btn_r5.pack(side=tk.LEFT, padx=3)

        self.btn_play = tk.Button(ctrl_frame, text="▶ PLAY", bg="#F59E0B", fg="#0F172A", font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=14, pady=3, command=self.toggle_play)
        self.btn_play.pack(side=tk.LEFT, padx=5)

        btn_f5 = tk.Button(ctrl_frame, text="+5s ▶", bg="#334155", fg="white", font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=6, command=lambda: self.seek_seconds(5))
        btn_f5.pack(side=tk.LEFT, padx=3)

        btn_f10 = tk.Button(ctrl_frame, text="+10s ⏩", bg="#334155", fg="white", font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=6, command=lambda: self.seek_seconds(10))
        btn_f10.pack(side=tk.LEFT, padx=3)

        btn_open = tk.Button(right_frame, text="📂 Open In Default Player", bg="#334155", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, command=self.open_external_video)
        btn_open.pack(pady=(2, 8))

    def refresh_latest_folder(self):
        latest = detect_latest_project_folder()
        if latest:
            self.img_dir_var.set(os.path.join(latest, "Images"))
            self.aud_dir_var.set(os.path.join(latest, "Audio"))
            mp4s = [f for f in os.listdir(latest) if f.lower().endswith('.mp4')]
            if mp4s:
                self.out_video_var.set(os.path.join(latest, mp4s[0]))
                self.load_video_file(os.path.join(latest, mp4s[0]))
            self.log(f"Auto-detected latest folder: {latest}")
            messagebox.showinfo("Project Detected", f"Auto-selected latest project:\n{os.path.basename(latest)}")
        else:
            messagebox.showwarning("Not Found", "No project directories with Images and Audio found.")

    def add_browse_row(self, parent, label_text, str_var, browse_cmd, row_idx):
        lbl = tk.Label(parent, text=label_text, bg="#1E293B", fg="#E2E8F0", font=("Segoe UI", 9))
        lbl.grid(row=row_idx, column=0, sticky=tk.W, pady=2)
        ent = ttk.Entry(parent, textvariable=str_var, width=44)
        ent.grid(row=row_idx, column=1, sticky=tk.EW, padx=6, pady=2)
        btn = ttk.Button(parent, text="Browse...", command=browse_cmd)
        btn.grid(row=row_idx, column=2, pady=2)
        parent.columnconfigure(1, weight=1)

    def log(self, text):
        self.txt_log.insert(tk.END, text + "\n")
        self.txt_log.see(tk.END)

    def browse_img_dir(self):
        d = filedialog.askdirectory(initialdir=SERIES_ROOT, title="Select Images Directory")
        if d: self.img_dir_var.set(d)

    def browse_aud_dir(self):
        d = filedialog.askdirectory(initialdir=SERIES_ROOT, title="Select Audio Directory")
        if d: self.aud_dir_var.set(d)

    def browse_out_video(self):
        f = filedialog.asksaveasfilename(initialdir=WORKSPACE, defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if f: self.out_video_var.set(f)

    # --- BADGE REPOSITIONING & EDITING LOGIC ---
    def on_scene_selected(self, event=None):
        sc_str = self.selected_scene_var.get()
        sc_num = sc_str.replace("Scene ", "").strip()
        data = self.badge_positions.get(sc_num, {"x": 540, "y": 90, "scale": 1.0, "text": ""})
        if isinstance(data, int):
            data = {"x": 540, "y": data, "scale": 1.0, "text": ""}
        
        self.y_pos_var.set(data.get("y", 90))
        self.lbl_y_val.config(text=f"{data.get('y', 90)}px")
        
        self.x_pos_var.set(data.get("x", 540))
        self.lbl_x_val.config(text=f"{data.get('x', 540)}px")
        
        sc_val = data.get("scale", 1.0)
        self.scale_var.set(sc_val)
        self.lbl_scale_val.config(text=f"{int(sc_val*100)}%")
        
        # Populate text
        cur_text = data.get("text", "")
        if not cur_text and sc_num in DEFAULT_BADGE_MAP:
            cur_text = DEFAULT_BADGE_MAP[sc_num][0][1]
        self.text_edit_var.set(cur_text)
        
        self.preview_repositioned_badge()

    def on_y_slider_moved(self, val):
        y_val = int(float(val))
        self.lbl_y_val.config(text=f"{y_val}px")
        self.preview_repositioned_badge()

    def on_x_slider_moved(self, val):
        x_val = int(float(val))
        self.lbl_x_val.config(text=f"{x_val}px")
        self.preview_repositioned_badge()

    def on_scale_slider_moved(self, val):
        s_val = round(float(val), 2)
        self.lbl_scale_val.config(text=f"{int(s_val*100)}%")
        self.preview_repositioned_badge()

    def on_text_edited(self, event=None):
        self.preview_repositioned_badge()

    def save_current_position(self):
        sc_str = self.selected_scene_var.get()
        sc_num = sc_str.replace("Scene ", "").strip()
        new_x = self.x_pos_var.get()
        new_y = self.y_pos_var.get()
        new_scale = round(self.scale_var.get(), 2)
        new_text = self.text_edit_var.get().strip()

        # Update disk badge PNG if text changed
        if sc_num in DEFAULT_BADGE_MAP and new_text:
            bname, orig_txt, bg, tc, bc, fs, st = DEFAULT_BADGE_MAP[sc_num][0]
            if new_text != orig_txt:
                self.log(f"Re-rendering badge image for {sc_str} with text: '{new_text}'")
                render_single_badge_to_disk(new_text, bg, tc, bc, fs, st, bname, overwrite=True)

        self.badge_positions[sc_num] = {
            "x": new_x,
            "y": new_y,
            "scale": new_scale,
            "text": new_text
        }
        save_manual_positions(self.badge_positions)
        self.log(f"Saved settings for {sc_str}: X={new_x}px, Y={new_y}px, Scale={int(new_scale*100)}%, Text='{new_text}'")
        messagebox.showinfo("Settings Saved", f"{sc_str} settings saved!\nX: {new_x}px | Y: {new_y}px | Scale: {int(new_scale*100)}%\nText: '{new_text}'\nWill be used on next render!")

    def preview_repositioned_badge(self):
        sc_str = self.selected_scene_var.get()
        sc_num = int(sc_str.replace("Scene ", "").strip())
        img_dir = self.img_dir_var.get()
        img_p = os.path.join(img_dir, f"Image_{sc_num:03d}.png")
        if not os.path.exists(img_p):
            return

        im = Image.open(img_p).convert('RGB')
        w, h = im.size
        scale = max(WIDTH / w, HEIGHT / h)
        nw, nh = int(w * scale), int(h * scale)
        im_res = im.resize((nw, nh), Image.LANCZOS).crop(((nw-WIDTH)//2, (nh-HEIGHT)//2, (nw-WIDTH)//2+WIDTH, (nh-HEIGHT)//2+HEIGHT))

        # Check badge
        bname = f"p2_b{sc_num}.png"
        bpath = os.path.join(BADGE_DIR, bname)
        if os.path.exists(bpath):
            b_im = Image.open(bpath).convert('RGBA')
            
            # Apply scale if modified
            sc_factor = self.scale_var.get()
            if abs(sc_factor - 1.0) > 0.02:
                bw = max(10, int(b_im.width * sc_factor))
                bh = max(10, int(b_im.height * sc_factor))
                b_im = b_im.resize((bw, bh), Image.LANCZOS)

            x_cur = self.x_pos_var.get()
            y_cur = self.y_pos_var.get()
            x = x_cur - b_im.width // 2
            y = y_cur - b_im.height // 2
            im_res.paste(b_im, (x, y), b_im)

        # Show on canvas
        rgb_frame = np.array(im_res)
        resized = cv2.resize(rgb_frame, (self.canvas_w, self.canvas_h), interpolation=cv2.INTER_AREA)
        im_pil = Image.fromarray(resized)
        self.tk_photo = ImageTk.PhotoImage(image=im_pil)
        self.preview_canvas.create_image(0, 0, image=self.tk_photo, anchor=tk.NW)

    # --- VIDEO PLAYER CONTROLS (WITH SYNCHRONIZED AUDIO) ---
    def load_video_file(self, video_path):
        if not os.path.exists(video_path):
            return
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            self.log(f"Failed to load video: {video_path}")
            return

        self.video_total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.video_fps = fps if fps > 0 else 30.0
        self.slider.config(to=max(1, self.video_total_frames - 1))
        self.current_frame_idx = 0

        # Extract audio stream for synchronized playback
        if HAS_PYGAME_AUDIO:
            try:
                cmd = ['ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', PREVIEW_AUDIO_WAV]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(PREVIEW_AUDIO_WAV):
                    pygame.mixer.music.load(PREVIEW_AUDIO_WAV)
                    self.has_audio_loaded = True
            except Exception:
                self.has_audio_loaded = False

        self.seek_frame(0)
        self.log(f"Loaded video preview: {os.path.basename(video_path)} ({self.video_total_frames} frames)")

    def seek_frame(self, frame_num):
        if self.cap is None or self.video_total_frames == 0:
            return
        frame_num = max(0, min(self.video_total_frames - 1, frame_num))
        self.current_frame_idx = frame_num
        self.play_start_frame = frame_num
        self.play_start_time = time.perf_counter()
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        if ret:
            self.display_frame(frame)
            self.update_player_ui()

        # Sync audio time
        if HAS_PYGAME_AUDIO and self.has_audio_loaded:
            pos_sec = frame_num / self.video_fps
            try:
                if self.is_playing:
                    pygame.mixer.music.play(start=pos_sec)
                else:
                    pygame.mixer.music.play(start=pos_sec)
                    pygame.mixer.music.pause()
            except Exception:
                pass

    def seek_seconds(self, delta_s):
        if self.cap is None:
            return
        new_frame = int(self.current_frame_idx + delta_s * self.video_fps)
        self.seek_frame(new_frame)

    def on_slider_scroll(self, val):
        if not self.is_playing:
            self.seek_frame(int(float(val)))

    def toggle_play(self):
        if self.cap is None:
            out_vid = self.out_video_var.get()
            if os.path.exists(out_vid):
                self.load_video_file(out_vid)
            else:
                messagebox.showinfo("Player", "No video loaded. Render video first.")
                return

        if self.is_playing:
            self.is_playing = False
            self.btn_play.config(text="▶ PLAY", bg="#F59E0B")
            if HAS_PYGAME_AUDIO and self.has_audio_loaded:
                pygame.mixer.music.pause()
        else:
            self.is_playing = True
            self.btn_play.config(text="⏸ PAUSE", bg="#10B981")
            self.play_start_frame = self.current_frame_idx
            self.play_start_time = time.perf_counter()
            if HAS_PYGAME_AUDIO and self.has_audio_loaded:
                cur_pos = self.current_frame_idx / self.video_fps
                pygame.mixer.music.play(start=cur_pos)
            self.play_loop()

    def play_loop(self):
        if not self.is_playing or self.cap is None:
            return
        
        # Calculate exactly which frame should be shown according to wall-clock time
        elapsed = time.perf_counter() - self.play_start_time
        target_frame = int(self.play_start_frame + elapsed * self.video_fps)
        
        if target_frame >= self.video_total_frames:
            self.is_playing = False
            self.btn_play.config(text="▶ PLAY", bg="#F59E0B")
            if HAS_PYGAME_AUDIO and self.has_audio_loaded:
                pygame.mixer.music.stop()
            self.seek_frame(0)
            return

        # If we need to seek forward because of frame processing overhead
        if abs(target_frame - self.current_frame_idx) > 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        
        ret, frame = self.cap.read()
        if ret:
            self.current_frame_idx = target_frame
            self.display_frame(frame)
            self.update_player_ui()
            
            # Dynamically compute remaining milliseconds until next frame
            next_frame_time = (target_frame + 1 - self.play_start_frame) / self.video_fps
            remaining_sec = next_frame_time - (time.perf_counter() - self.play_start_time)
            delay_ms = max(1, int(remaining_sec * 1000))
            self.after(delay_ms, self.play_loop)
        else:
            self.is_playing = False
            self.btn_play.config(text="▶ PLAY", bg="#F59E0B")
            if HAS_PYGAME_AUDIO and self.has_audio_loaded:
                pygame.mixer.music.stop()
            self.seek_frame(0)

    def display_frame(self, bgr_frame):
        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb_frame, (self.canvas_w, self.canvas_h), interpolation=cv2.INTER_AREA)
        im_pil = Image.fromarray(resized)
        self.tk_photo = ImageTk.PhotoImage(image=im_pil)
        self.preview_canvas.create_image(0, 0, image=self.tk_photo, anchor=tk.NW)

    def update_player_ui(self):
        self.slider_var.set(self.current_frame_idx)
        cur_s = self.current_frame_idx / self.video_fps
        tot_s = self.video_total_frames / self.video_fps
        cur_str = f"{int(cur_s // 60):02d}:{int(cur_s % 60):02d}"
        tot_str = f"{int(tot_s // 60):02d}:{int(tot_s % 60):02d}"
        self.lbl_timecode.config(text=f"{cur_str} / {tot_str} (Frame {self.current_frame_idx})")

    def open_external_video(self):
        out_vid = self.out_video_var.get()
        if os.path.exists(out_vid):
            os.startfile(out_vid)
        else:
            messagebox.showinfo("Info", "File does not exist yet. Please render first.")

    # --- VIDEO GENERATION PROCESS ---
    def start_render_thread(self):
        if self.is_rendering:
            return
        
        img_dir = self.img_dir_var.get()
        aud_dir = self.aud_dir_var.get()
        
        if not os.path.exists(img_dir):
            messagebox.showerror("Error", f"Images folder does not exist:\n{img_dir}")
            return
        if not os.path.exists(aud_dir):
            messagebox.showerror("Error", f"Audio folder does not exist:\n{aud_dir}")
            return
            
        img_files = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        aud_files = sorted([f for f in os.listdir(aud_dir) if f.lower().endswith(('.wav', '.mp3', '.aac'))])
        
        if len(img_files) == 0:
            messagebox.showerror("Error", "No image files found in Images folder!")
            return
        if len(aud_files) == 0:
            messagebox.showerror("Error", "No audio files found in Audio folder!")
            return
            
        if len(img_files) != len(aud_files):
            msg = f"Count mismatch!\n\nImages found: {len(img_files)}\nAudio files found: {len(aud_files)}\n\nPlease ensure you have the exact same count of images and audio files."
            messagebox.showerror("Count Mismatch Error", msg)
            return

        if self.is_playing:
            self.toggle_play()

        self.is_rendering = True
        self.btn_render.config(state=tk.DISABLED, text="RENDERING VIDEO... PLEASE WAIT")
        self.progress_bar['value'] = 0
        self.txt_log.delete('1.0', tk.END)
        
        thread = threading.Thread(target=self.run_render_process, args=(img_files, aud_files), daemon=True)
        thread.start()

    def run_render_process(self, img_files, aud_files):
        try:
            t_start = time.time()
            img_dir = self.img_dir_var.get()
            aud_dir = self.aud_dir_var.get()
            out_video = self.out_video_var.get()
            enable_anim = self.enable_anim_var.get()
            mode_choice = self.anim_mode_var.get()

            # Determine Animation Style for this Video
            if "Cycle Style" in mode_choice or "Shuffle" in mode_choice:
                chosen_style, style_idx = advance_cycle_style()
                self.log(f"Auto-Cycled to Animation Style [{style_idx+1}/25]: '{chosen_style}'")
            else:
                chosen_style = mode_choice
                self.log(f"User Selected Animation Style: '{chosen_style}'")

            self.log(f"Uniformity: Applying '{chosen_style}' across ALL scenes of this video.")

            num_scenes = len(img_files)
            self.log(f"Starting Video Render for {num_scenes} scenes...")

            # Audio durations
            durations = []
            for af in aud_files:
                dur = get_audio_duration(os.path.join(aud_dir, af))
                durations.append(dur)
            total_dur = sum(durations)
            total_frames = int(total_dur * FPS)

            temp_vid = os.path.join(WORKSPACE, "temp_gui_video.mp4")
            temp_aud = os.path.join(WORKSPACE, "temp_gui_audio.wav")

            # Master audio track
            self.log("Concatenating master audio...")
            full_audio_samples = []
            for af in aud_files:
                samples = load_audio_samples(os.path.join(aud_dir, af))
                full_audio_samples.append(samples)
            full_audio = np.concatenate(full_audio_samples, axis=0)
            with wave.open(temp_aud, 'wb') as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(SAMPLE_RATE)
                w.writeframes(full_audio.tobytes())

            # Scenes badge configuration mapping with loaded manual positions
            pos = self.badge_positions
            scenes_cfg = [
                {"badges": [("p2_b1.png", pos.get("1", {"x": 540, "y": 95, "scale": 1.0}), 0.2, 0.25)]},
                {"badges": [("p2_b2.png", pos.get("2", {"x": 540, "y": 130, "scale": 1.0}), 0.2, 0.25)]},
                {"badges": [("p2_b3.png", pos.get("3", {"x": 540, "y": 170, "scale": 1.0}), 0.2, 0.25)]},
                {"badges": [("p2_b4.png", pos.get("4", {"x": 540, "y": 90, "scale": 1.0}), 0.2, 0.25)]},
                {"badges": [("p2_b5.png", pos.get("5", {"x": 540, "y": 120, "scale": 1.0}), 0.2, 0.25)]},
                {"badges": [("p2_b6.png", pos.get("6", {"x": 540, "y": 1600, "scale": 1.0}), 0.2, 0.25)]},
                {"badges": [("p2_b7.png", pos.get("7", {"x": 540, "y": 120, "scale": 1.0}), 0.2, 0.25)]},
                {"badges": [("p2_b8_1.png", pos.get("8_1", {"x": 540, "y": 110, "scale": 1.0}), 0.2, 0.25), ("p2_b8_2.png", pos.get("8_2", {"x": 540, "y": 250, "scale": 1.0}), 1.5, 0.25)]},
                {"badges": [("p2_b9.png", pos.get("9", {"x": 540, "y": 170, "scale": 1.0}), 0.2, 0.25)]},
                {"badges": [("p2_b10.png", pos.get("10", {"x": 540, "y": 1600, "scale": 1.0}), 0.2, 0.25)]},
                {"badges": [("p2_b11_1.png", pos.get("11_1", {"x": 540, "y": 120, "scale": 1.0}), 0.2, 0.25), ("p2_b11_2.png", pos.get("11_2", {"x": 540, "y": 260, "scale": 1.0}), 1.2, 0.25)]},
                {"badges": [("p2_b12.png", pos.get("12", {"x": 540, "y": 160, "scale": 1.0}), 0.2, 0.25)]},
                {"badges": [("p2_b13_1.png", pos.get("13_1", {"x": 540, "y": 110, "scale": 1.0}), 0.2, 0.25), ("p2_b13_2.png", pos.get("13_2", {"x": 540, "y": 250, "scale": 1.0}), 1.0, 0.25)]},
                {"badges": [("p2_b14.png", pos.get("14", {"x": 540, "y": 1600, "scale": 1.0}), 0.2, 0.25)]},
            ]

            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{WIDTH}x{HEIGHT}',
                '-pix_fmt', 'bgr24',
                '-r', str(FPS),
                '-i', '-',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '18',
                '-pix_fmt', 'yuv420p',
                temp_vid
            ]
            pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
            global_frame = 0

            for s_idx in range(num_scenes):
                dur = durations[s_idx]
                scene_frames = int(dur * FPS)
                img_p = os.path.join(img_dir, img_files[s_idx])
                base_bgr = read_image_utf8(img_p)
                orig_h, orig_w = base_bgr.shape[:2]
                
                scale = max(WIDTH / orig_w, HEIGHT / orig_h)
                nw, nh = int(orig_w * scale), int(orig_h * scale)
                scaled_base = cv2.resize(base_bgr, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
                x_off = (nw - WIDTH) // 2
                y_off = (nh - HEIGHT) // 2
                cropped_base = scaled_base[y_off:y_off+HEIGHT, x_off:x_off+WIDTH]

                cfg = scenes_cfg[s_idx] if s_idx < len(scenes_cfg) else {"badges": []}
                loaded_badges = []
                for bname, bcfg, ent_delay, ex_lead in cfg["badges"]:
                    bpath = os.path.join(BADGE_DIR, bname)
                    if os.path.exists(bpath):
                        b_rgba = cv2.imread(bpath, cv2.IMREAD_UNCHANGED)
                        sc_val = bcfg.get("scale", 1.0)
                        if abs(sc_val - 1.0) > 0.01:
                            new_w = max(10, int(b_rgba.shape[1] * sc_val))
                            new_h = max(10, int(b_rgba.shape[0] * sc_val))
                            b_rgba = cv2.resize(b_rgba, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

                        loaded_badges.append({
                            "bgr": b_rgba[:, :, :3],
                            "alpha": (b_rgba[:, :, 3].astype(np.float32) / 255.0),
                            "target_x": bcfg.get("x", 540),
                            "target_y": bcfg.get("y", 90),
                            "t_start": ent_delay,
                            "t_end": max(dur - ex_lead, ent_delay + 0.5)
                        })

                for f in range(scene_frames):
                    t_sec = f / FPS
                    zoom = 1.0 + 0.05 * (f / max(1, scene_frames))
                    cw = int(WIDTH / zoom)
                    ch = int(HEIGHT / zoom)
                    cx, cy = WIDTH // 2, HEIGHT // 2
                    x1 = max(0, cx - cw // 2)
                    y1 = max(0, cy - ch // 2)
                    frame_crop = cropped_base[y1:y1+ch, x1:x1+cw]
                    frame_bgr = cv2.resize(frame_crop, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)

                    for b in loaded_badges:
                        b_bgr = b["bgr"]
                        b_alpha = b["alpha"]
                        target_x = b["target_x"]
                        target_y = b["target_y"]
                        t_start = b["t_start"]
                        t_end = b["t_end"]

                        if t_sec < t_start or t_sec > t_end + 0.3:
                            continue

                        draw_bgr, draw_alpha, dx, dy, opacity = render_badge_advanced(
                            b_bgr, b_alpha, t_sec, t_start, t_end,
                            anim_style=chosen_style, enable_anim=enable_anim,
                            width=WIDTH, height=HEIGHT
                        )

                        stamp_badge_final(
                            frame_bgr, draw_bgr, draw_alpha,
                            x_center=target_x, y_center=target_y,
                            dx=dx, dy=dy, opacity=opacity,
                            width=WIDTH, height=HEIGHT
                        )

                    pipe.stdin.write(frame_bgr.tobytes())
                    global_frame += 1
                    if global_frame % 30 == 0 or global_frame == total_frames:
                        pct = (global_frame / total_frames) * 100
                        self.progress_bar['value'] = pct
                        self.lbl_status.config(text=f"Rendering: {pct:.1f}% ({global_frame}/{total_frames} frames)")

            pipe.stdin.close()
            pipe.wait()

            self.log(f"Muxing MP4 Video -> {out_video}")
            mux_cmd = [
                'ffmpeg', '-y',
                '-i', temp_vid,
                '-i', temp_aud,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',
                out_video
            ]
            subprocess.run(mux_cmd, check=True)

            if os.path.exists(temp_vid): os.remove(temp_vid)
            if os.path.exists(temp_aud): os.remove(temp_aud)

            elapsed_total = time.time() - t_start
            self.progress_bar['value'] = 100
            self.lbl_status.config(text=f"Done! Rendered in {elapsed_total:.1f}s")
            self.log("==================================================")
            self.log(f"🎉 VIDEO COMPLETED SUCCESSFULLY IN {elapsed_total:.1f}s!")
            self.log(f"Output File: {out_video}")
            self.log(f"Animation Style Applied: '{chosen_style}'")
            next_st, _ = get_next_cycle_style()
            self.log(f"Next Video Will Use: '{next_st}'")
            self.log("==================================================")

            # Auto load into preview player with audio
            self.load_video_file(out_video)

        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            messagebox.showerror("Render Error", str(e))
        finally:
            self.is_rendering = False
            self.btn_render.config(state=tk.NORMAL, text="🚀 START VIDEO RENDER")

if __name__ == '__main__':
    app = AutoVideoStudioApp()
    app.mainloop()
