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
from PIL import Image, ImageTk, ImageDraw, ImageFont

def render_dynamic_preview_badge(text, wrap_width=620, fsize=44, bg='#FFFFFF', txt_col='#2B3A67', border_col='#2B3A67', shadow_col='#2B3A67'):
    # Prioritize ExtraBold font files for punchy text
    font = None
    for f_cand in ['NotoSansTelugu-ExtraBold.ttf', 'NotoSansTelugu-Bold.ttf', 'NotoSansTelugu-Full.ttf']:
        if os.path.exists(f_cand):
            try:
                font = ImageFont.truetype(f_cand, fsize)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    # Font specifically for Unicode symbols like arrows (→, ←, etc.) and English bold text
    arrow_font = None
    for sys_font in ['C:/Windows/Fonts/segoeuib.ttf', 'C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arialbd.ttf', 'C:/Windows/Fonts/arial.ttf']:
        if os.path.exists(sys_font):
            try:
                arrow_font = ImageFont.truetype(sys_font, fsize)
                break
            except Exception:
                pass
    if arrow_font is None:
        arrow_font = font

    def get_token_w(token):
        if any(c in '→←↑↓↔↕' for c in token):
            return arrow_font.getbbox(token)[2] - arrow_font.getbbox(token)[0]
        return font.getbbox(token)[2] - font.getbbox(token)[0]

    words = text.split()
    lines = []
    cur_tokens = []
    cur_w = 0
    space_w = font.getbbox(' ')[2] - font.getbbox(' ')[0]

    for w in words:
        tw = get_token_w(w)
        cand_w = tw if not cur_tokens else (cur_w + space_w + tw)
        if wrap_width and cand_w > wrap_width and cur_tokens:
            lines.append(cur_tokens)
            cur_tokens = [w]
            cur_w = tw
        else:
            cur_tokens.append(w)
            cur_w = cand_w
    if cur_tokens:
        lines.append(cur_tokens)

    # Calculate dimensions
    line_metrics = []
    for line_tokens in lines:
        lw = sum(get_token_w(t) for t in line_tokens) + max(0, len(line_tokens) - 1) * space_w
        lh = fsize
        for t in line_tokens:
            use_f = arrow_font if any(c in '→←↑↓↔↕' for c in t) else font
            bb = use_f.getbbox(t)
            lh = max(lh, bb[3] - bb[1])
        line_metrics.append((lw, lh))

    max_w = max([m[0] for m in line_metrics]) if line_metrics else 100
    line_h = max([m[1] for m in line_metrics]) if line_metrics else fsize
    spacing = int(fsize * 0.35)
    total_text_h = len(lines) * line_h + (len(lines) - 1) * spacing

    pad_x = 36
    pad_y = 16
    box_w = max_w + pad_x * 2
    box_h = total_text_h + pad_y * 2
    
    shadow_offset = 6
    border_w = 4
    radius = 18

    im_w = box_w + shadow_offset + border_w * 2 + 10
    im_h = box_h + shadow_offset + border_w * 2 + 10
    im = Image.new('RGBA', (im_w, im_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    sx0 = 5 + shadow_offset
    sy0 = 5 + shadow_offset
    draw.rounded_rectangle([sx0, sy0, sx0 + box_w, sy0 + box_h], radius=radius, fill=shadow_col)

    bx0 = 5
    by0 = 5
    draw.rounded_rectangle([bx0, by0, bx0 + box_w, by0 + box_h], radius=radius, fill=bg, outline=border_col, width=border_w)

    cur_y = by0 + pad_y
    for i, line_tokens in enumerate(lines):
        lw = line_metrics[i][0]
        cur_x = bx0 + (box_w - lw) // 2
        for t in line_tokens:
            use_f = arrow_font if any(c in '→←↑↓↔↕' for c in t) else font
            draw.text((cur_x, cur_y), t, font=use_f, fill=txt_col)
            cur_x += get_token_w(t) + space_w
        cur_y += line_h + spacing

    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im
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

WIDTH = 1920
HEIGHT = 1080
FPS = 30
SAMPLE_RATE = 44100
WORKSPACE = r"c:\Users\aanil\Documents\Auto_Video_Editing"
BADGE_DIR = os.path.join(WORKSPACE, "rendered_badges")
LONG_FORMAT_ROOT = r"C:\Users\aanil\Documents\Anxious Anil\Long Format Videos\Projects\Fasting Series"
SHORTS_ROOT = r"C:\Users\aanil\Documents\Anxious Anil\Shorts Videos\Projects\Fasting Series"
STATE_FILE = os.path.join(WORKSPACE, "animation_cycle_state.json")
POSITIONS_FILE = os.path.join(WORKSPACE, "manual_badge_positions.json")
PREVIEW_AUDIO_WAV = os.path.join(WORKSPACE, "temp_preview_audio.wav")

def detect_latest_project_folder(root_dir=LONG_FORMAT_ROOT):
    # Try Long Format first as requested, then fallback to Shorts if not found
    for r in [root_dir, LONG_FORMAT_ROOT, SHORTS_ROOT]:
        if os.path.exists(r):
            subdirs = [os.path.join(r, d) for d in os.listdir(r) if os.path.isdir(os.path.join(r, d))]
            valid_subdirs = [
                d for d in subdirs 
                if os.path.isdir(os.path.join(d, "Images")) and os.path.isdir(os.path.join(d, "Audio"))
            ]
            if valid_subdirs:
                return max(valid_subdirs, key=os.path.getmtime)
    return None

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
    "1": [("p2_b1.png", "Intermittent Fasting పూర్తి వివరణ", "#EADBC8", "#2B3A67", "#2B3A67", 46, False)],
    "2": [("p2_b2.png", "ఇది Diet కాదు — Eating Schedule!", "#FAF8F5", "#C85A32", "#2B3A67", 46, False)],
    "3": [("p2_b3.png", "16/8, 5:2, OMAD — ఇన్ని రకాలా?", "#EADBC8", "#2B3A67", "#2B3A67", 46, False)],
    "4": [("p2_b4.png", "తప్పు Method ఎంచుకుంటే నీరసం!", "#FAF8F5", "#C85A32", "#2B3A67", 46, False)],
    "5": [("p2_b5.png", "మీ Bodyకి ఏది సరిపోతుంది?", "#EADBC8", "#2B3A67", "#2B3A67", 46, False)],
    "6": [("p2_b6.png", "Simpleగా Break Down చేద్దాం!", "#FAF8F5", "#2E7D7B", "#2B3A67", 46, False)],
    "7": [("p2_b7.png", "కడుపుకి Fixed Opening & Closing Time", "#EADBC8", "#2B3A67", "#2B3A67", 44, False)],
    "8": [("p2_b8.png", "Food ఆగిపోయాకే Body Cleaning!", "#FAF8F5", "#2E7D7B", "#2B3A67", 46, False)],
    "9": [("p2_b9.png", "కడుపు మాడ్చుకోవడం కాదు — Smart Routine", "#EADBC8", "#2B3A67", "#2B3A67", 44, False)],
    "10": [("p2_b10.png", "16/8 Method: 16 Hrs Off, 8 Hrs On", "#EADBC8", "#2B3A67", "#2B3A67", 44, False)],
    "11": [("p2_b11.png", "8 Hours నిద్రలోనే గడిచిపోతాయి!", "#FAF8F5", "#2E7D7B", "#2B3A67", 46, False)],
    "12": [("p2_b12.png", "అందరి ఫస్ట్ ఛాయిస్: 16/8", "#EADBC8", "#2B3A67", "#2B3A67", 46, False)],
    "13": [("p2_b13.png", "Beginners కోసం 12/12 Method", "#FAF8F5", "#2E7D7B", "#2B3A67", 46, False)],
    "14": [("p2_b14.png", "మెల్లగా 14/10 కి Step Up!", "#EADBC8", "#2B3A67", "#2B3A67", 46, False)],
    "15": [("p2_b15.png", "12/12 తో స్టార్ట్ చేయడం Safe!", "#FAF8F5", "#2B3A67", "#2B3A67", 46, False)],
    "16": [("p2_b16.png", "5:2 Diet: 5 Days Normal, 2 Days Low", "#EADBC8", "#C85A32", "#2B3A67", 44, False)],
    "17": [("p2_b17.png", "రెండు రోజుల మధ్య Gap తప్పనిసరి!", "#FAF8F5", "#2B3A67", "#2B3A67", 46, False)],
    "18": [("p2_b18.png", "రోజూ కుదరని వాళ్లకి 5:2 Best", "#EADBC8", "#2E7D7B", "#2B3A67", 46, False)],
    "19": [("p2_b19.png", "Eat-Stop-Eat: 24 Hours Deep Reset", "#FAF8F5", "#2B3A67", "#2B3A67", 44, False)],
    "20": [("p2_b20.png", "Alternate Day: రోజు విడిచి రోజు", "#EADBC8", "#C85A32", "#2B3A67", 46, False)],
    "21": [("p2_b21.png", "Beginners ఇవి వెంటనే Try చేయొద్దు!", "#FAF8F5", "#C85A32", "#2B3A67", 46, False)],
    "22": [("p2_b22.png", "Warrior Diet: 20 Hrs Fast / 4 Hrs Eat", "#EADBC8", "#2B3A67", "#2B3A67", 44, False)],
    "23": [("p2_b23.png", "OMAD: రోజుకి ఒక్కసారే భోజనం!", "#FAF8F5", "#C85A32", "#2B3A67", 46, False)],
    "24": [("p2_b24.png", "పోషకాలు అందకపోయే Risk ఉంది", "#EADBC8", "#C85A32", "#2B3A67", 46, False)],
    "25": [("p2_b25.png", "అందరికీ ఒకే Method సరిపోదు!", "#FAF8F5", "#2B3A67", "#2B3A67", 46, False)],
    "26": [("p2_b26.png", "డాక్టర్ సలహా లేకుండా Risk వద్దు!", "#EADBC8", "#C85A32", "#2B3A67", 46, False)],
    "27": [("p2_b27.png", "Protein + Fiber + Water మర్చిపోవద్దు", "#FAF8F5", "#2E7D7B", "#2B3A67", 44, False)],
    "28": [("p2_b28.png", "అసలు నిజం ఏంటంటే...", "#EADBC8", "#2B3A67", "#2B3A67", 46, False)],
    "29": [("p2_b29.png", "లాంగ్ టర్మ్‌లో ఫాలో అయ్యేదే BEST!", "#EADBC8", "#C85A32", "#2B3A67", 46, False)],
    "30": [("p2_b30.png", "Subscribe & Comment Below!", "#FAF8F5", "#2B3A67", "#2B3A67", 46, False)],
}

def load_manual_positions():
    default_positions = {}
    for i in range(1, 35):
        s_i = str(i)
        t_val = DEFAULT_BADGE_MAP[s_i][0][1] if s_i in DEFAULT_BADGE_MAP else ""
        default_positions[s_i] = {"x": 960, "y": 120, "scale": 1.0, "text": t_val}
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
                default_out = os.path.join(latest_folder, "Fasting_Series_LongFormat.mp4")
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

        # Detect scenes from images
        init_scenes = self.get_detected_scenes(default_img)
        self.scenes_list = init_scenes if init_scenes else [f"Scene {i}" for i in range(1, 31)]

        # Badge Positions and Editing
        self.badge_positions = load_manual_positions()
        self.selected_scene_var = tk.StringVar(value=self.scenes_list[0] if self.scenes_list else "Scene 1")
        self.x_pos_var = tk.IntVar(value=960)
        self.y_pos_var = tk.IntVar(value=120)
        self.scale_var = tk.DoubleVar(value=1.0)
        self.font_size_var = tk.IntVar(value=46)
        self.text_edit_var = tk.StringVar(value="")

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
        self.update_scene_editor_fields()
        
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

        top_btn_row = tk.Frame(cfg_frame, bg="#1E293B")
        top_btn_row.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 4))

        btn_auto_detect = tk.Button(top_btn_row, text="🔄 Auto-Detect Latest Project Folder", bg="#0284C7", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, pady=2, padx=6, command=self.refresh_latest_folder)
        btn_auto_detect.pack(side=tk.LEFT, padx=(0, 6))

        btn_sync = tk.Button(top_btn_row, text="⚡ SYNC EDITING DIRECTIONS & ASSETS", bg="#10B981", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, pady=2, padx=8, command=self.sync_all_from_editing_directions)
        btn_sync.pack(side=tk.LEFT)

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
        self.cmb_scene = ttk.Combobox(row1, values=self.scenes_list, textvariable=self.selected_scene_var, state="readonly", width=12)
        self.cmb_scene.pack(side=tk.LEFT, padx=4)
        self.cmb_scene.bind("<<ComboboxSelected>>", self.on_scene_selected)

        # Editable Text Field
        lbl_txt = tk.Label(row1, text="Text:", bg="#1E293B", fg="white", font=("Segoe UI", 9, "bold"))
        lbl_txt.pack(side=tk.LEFT, padx=(8, 4))
        self.ent_text = ttk.Entry(row1, textvariable=self.text_edit_var, width=24)
        self.ent_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.ent_text.bind("<KeyRelease>", self.on_text_edited)

        # Row 2: Text Wrapping Controls (Max Width & Auto-Wrap)
        row_wrap = tk.Frame(pos_box, bg="#1E293B")
        row_wrap.pack(fill=tk.X, pady=2)
        self.enable_wrap_var = tk.BooleanVar(value=True)
        chk_wrap = tk.Checkbutton(row_wrap, text="Auto-Wrap Text (Pure White BG)", variable=self.enable_wrap_var, bg="#1E293B", fg="#38BDF8", selectcolor="#0F172A", activebackground="#1E293B", activeforeground="#38BDF8", font=("Segoe UI", 8, "bold"), command=self.on_wrap_toggled)
        chk_wrap.pack(side=tk.LEFT)

        lbl_w_lim = tk.Label(row_wrap, text="Wrap Width:", bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 8))
        lbl_w_lim.pack(side=tk.LEFT, padx=(10, 4))
        self.wrap_width_var = tk.IntVar(value=620)
        self.wrap_slider = ttk.Scale(row_wrap, from_=350, to=900, variable=self.wrap_width_var, command=self.on_wrap_slider_moved)
        self.wrap_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.lbl_wrap_val = tk.Label(row_wrap, text="620px", bg="#1E293B", fg="#38BDF8", font=("Consolas", 8, "bold"), width=6)
        self.lbl_wrap_val.pack(side=tk.LEFT)

        # Row 3: Y-Axis Movement Slider
        row_y = tk.Frame(pos_box, bg="#1E293B")
        row_y.pack(fill=tk.X, pady=2)
        lbl_y = tk.Label(row_y, text="Y-Axis (Up/Down):", bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 8), width=16, anchor=tk.W)
        lbl_y.pack(side=tk.LEFT)
        self.y_slider = ttk.Scale(row_y, from_=40, to=1040, variable=self.y_pos_var, command=self.on_y_slider_moved)
        self.y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.lbl_y_val = tk.Label(row_y, text="120px", bg="#1E293B", fg="#38BDF8", font=("Consolas", 9, "bold"), width=6)
        self.lbl_y_val.pack(side=tk.LEFT)

        # Row 4: X-Axis Movement Slider
        row_x = tk.Frame(pos_box, bg="#1E293B")
        row_x.pack(fill=tk.X, pady=2)
        lbl_x = tk.Label(row_x, text="X-Axis (Left/Right):", bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 8), width=16, anchor=tk.W)
        lbl_x.pack(side=tk.LEFT)
        self.x_slider = ttk.Scale(row_x, from_=80, to=1840, variable=self.x_pos_var, command=self.on_x_slider_moved)
        self.x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.lbl_x_val = tk.Label(row_x, text="960px", bg="#1E293B", fg="#38BDF8", font=("Consolas", 9, "bold"), width=6)
        self.lbl_x_val.pack(side=tk.LEFT)

        # Row 5: Size / Scale Slider & Font Size
        row4 = tk.Frame(pos_box, bg="#1E293B")
        row4.pack(fill=tk.X, pady=2)
        lbl_sz = tk.Label(row4, text="Scale (%):", bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 8), width=10, anchor=tk.W)
        lbl_sz.pack(side=tk.LEFT)
        self.scale_slider = ttk.Scale(row4, from_=0.4, to=1.6, variable=self.scale_var, command=self.on_scale_slider_moved)
        self.scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.lbl_scale_val = tk.Label(row4, text="100%", bg="#1E293B", fg="#F59E0B", font=("Consolas", 9, "bold"), width=5)
        self.lbl_scale_val.pack(side=tk.LEFT, padx=(0, 6))

        # Font Size Slider
        lbl_fsize = tk.Label(row4, text="Font Size:", bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 8), width=8, anchor=tk.W)
        lbl_fsize.pack(side=tk.LEFT)
        self.fsize_slider = ttk.Scale(row4, from_=32, to=72, variable=self.font_size_var, command=self.on_fsize_slider_moved)
        self.fsize_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.lbl_fsize_val = tk.Label(row4, text="46px", bg="#1E293B", fg="#38BDF8", font=("Consolas", 9, "bold"), width=5)
        self.lbl_fsize_val.pack(side=tk.LEFT)

        # Action Buttons: Save Current Scene & Save ALL Scenes At Once
        row_btns = tk.Frame(pos_box, bg="#1E293B")
        row_btns.pack(fill=tk.X, pady=(4, 2))
        btn_apply_pos = tk.Button(row_btns, text="💾 Save Current Scene", bg="#059669", fg="white", font=("Segoe UI", 8, "bold"), relief=tk.FLAT, padx=8, pady=3, command=self.save_current_position)
        btn_apply_pos.pack(side=tk.LEFT, padx=(0, 6))

        btn_save_all = tk.Button(row_btns, text="💾 SAVE ALL SCENES AT ONCE", bg="#3B82F6", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=12, pady=3, command=self.save_all_scenes)
        btn_save_all.pack(side=tk.LEFT, fill=tk.X, expand=True)

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

        # --- RIGHT: Video Preview Player (16:9 Canvas & Synchronized Audio) ---
        lbl_p_title = tk.Label(right_frame, text="📺 16:9 Video Preview Player (Synchronized Audio)", bg="#1E293B", fg="#F59E0B", font=("Segoe UI", 11, "bold"))
        lbl_p_title.pack(pady=(8, 2))

        # 16:9 Canvas (480x270)
        self.canvas_w = 480
        self.canvas_h = 270
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

    def get_detected_scenes(self, img_folder):
        if not img_folder or not os.path.exists(img_folder):
            return []
        imgs = sorted([f for f in os.listdir(img_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        return [f"Scene {i+1}" for i in range(len(imgs))]

    def refresh_scene_list(self):
        img_folder = self.img_dir_var.get()
        detected = self.get_detected_scenes(img_folder)
        if detected:
            self.scenes_list = detected
            self.cmb_scene['values'] = self.scenes_list
            cur = self.selected_scene_var.get()
            if cur not in self.scenes_list:
                self.selected_scene_var.set(self.scenes_list[0])
            self.update_scene_editor_fields()

    def update_scene_editor_fields(self):
        sc_str = self.selected_scene_var.get()
        if not sc_str:
            return
        sc_num = sc_str.replace("Scene ", "").strip()
        self.current_scene_loaded = sc_num
        data = self.badge_positions.get(sc_num, {"x": WIDTH // 2, "y": 120, "scale": 1.0, "text": ""})
        if isinstance(data, int):
            data = {"x": WIDTH // 2, "y": data, "scale": 1.0, "text": ""}

        self.y_pos_var.set(data.get("y", 120))
        self.lbl_y_val.config(text=f"{data.get('y', 120)}px")

        self.x_pos_var.set(data.get("x", WIDTH // 2))
        self.lbl_x_val.config(text=f"{data.get('x', WIDTH // 2)}px")

        sc_val = data.get("scale", 1.0)
        self.scale_var.set(sc_val)
        self.lbl_scale_val.config(text=f"{int(sc_val*100)}%")

        wrap_val = data.get("wrap_width", 620)
        if hasattr(self, 'wrap_width_var'):
            self.wrap_width_var.set(wrap_val if wrap_val else 620)
            self.lbl_wrap_val.config(text=f"{wrap_val if wrap_val else 620}px")
            self.enable_wrap_var.set(bool(wrap_val > 0))

        fsize_val = data.get("font_size", 46)
        if hasattr(self, 'font_size_var'):
            self.font_size_var.set(fsize_val if fsize_val else 46)
            self.lbl_fsize_val.config(text=f"{fsize_val if fsize_val else 46}px")

        cur_text = data.get("text", "")
        if not cur_text and sc_num in DEFAULT_BADGE_MAP:
            cur_text = DEFAULT_BADGE_MAP[sc_num][0][1]
        self.text_edit_var.set(cur_text)
        self.preview_repositioned_badge()

    def sync_all_from_editing_directions(self):
        """
        One-click Sync:
        1. Auto-detects the latest project folder (Images and Audio).
        2. Parses Editing_Directions.txt to load all scenes, updated titles, text lines, and color themes.
        3. Clears stale cached positions from previous videos and replaces them with fresh parsed texts.
        4. Refreshes the scene list dropdown and immediately updates the preview with new video assets.
        """
        # Step 1: Detect and load latest project assets
        latest = detect_latest_project_folder()
        if latest:
            self.img_dir_var.set(os.path.join(latest, "Images"))
            self.aud_dir_var.set(os.path.join(latest, "Audio"))
            mp4s = [f for f in os.listdir(latest) if f.lower().endswith('.mp4')]
            if mp4s:
                self.out_video_var.set(os.path.join(latest, mp4s[0]))
                self.load_video_file(os.path.join(latest, mp4s[0]))
            else:
                self.out_video_var.set(os.path.join(latest, "Fasting_Series_LongFormat.mp4"))

        # Step 2: Parse current Editing_Directions.txt
        ed_file = os.path.join(WORKSPACE, "Editing_Directions.txt")
        parsed_scenes = {}
        if os.path.exists(ed_file):
            try:
                import parse_editing_directions
                parsed_scenes = parse_editing_directions.parse_editing_directions(ed_file)
            except Exception as e:
                self.log(f"Error parsing Editing_Directions.txt: {e}")

        # Step 3: Refresh scene dropdown from images
        img_folder = self.img_dir_var.get()
        detected = self.get_detected_scenes(img_folder)
        if detected:
            self.scenes_list = detected
        elif parsed_scenes:
            self.scenes_list = [f"Scene {k}" for k in sorted(parsed_scenes.keys(), key=lambda x: int(x))]

        self.cmb_scene['values'] = self.scenes_list

        # Step 4: Sync badge texts and colors from parsed Editing Directions into active memory
        for sc_key, sc_data in parsed_scenes.items():
            if sc_key not in self.badge_positions:
                self.badge_positions[sc_key] = {
                    "x": WIDTH // 2,
                    "y": 120,
                    "scale": 1.0,
                    "font_size": 46,
                    "wrap_width": 620,
                    "text": sc_data.get("text", "")
                }
            else:
                # Update text if changed
                self.badge_positions[sc_key]["text"] = sc_data.get("text", "")
                if "font_size" not in self.badge_positions[sc_key]:
                    self.badge_positions[sc_key]["font_size"] = 46

        save_manual_positions(self.badge_positions)

        # Select first scene and refresh preview canvas immediately
        if self.scenes_list:
            self.selected_scene_var.set(self.scenes_list[0])
        self.update_scene_editor_fields()
        self.preview_repositioned_badge()

        folder_name = os.path.basename(latest) if latest else "Current Folder"
        self.log(f"⚡ Synced {len(self.scenes_list)} scenes from Editing_Directions.txt into {folder_name}!")
        messagebox.showinfo(
            "Sync Complete",
            f"Successfully synced with Editing Directions!\n\n"
            f"• Project Folder: {folder_name}\n"
            f"• Total Scenes: {len(self.scenes_list)}\n"
            f"• All texts and assets updated for current video preview."
        )

    def refresh_latest_folder(self):
        latest = detect_latest_project_folder()
        if latest:
            self.img_dir_var.set(os.path.join(latest, "Images"))
            self.aud_dir_var.set(os.path.join(latest, "Audio"))
            mp4s = [f for f in os.listdir(latest) if f.lower().endswith('.mp4')]
            if mp4s:
                self.out_video_var.set(os.path.join(latest, mp4s[0]))
                self.load_video_file(os.path.join(latest, mp4s[0]))
            else:
                self.out_video_var.set(os.path.join(latest, "Fasting_Series_LongFormat.mp4"))
            self.refresh_scene_list()
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
        d = filedialog.askdirectory(initialdir=LONG_FORMAT_ROOT, title="Select Images Directory")
        if d:
            self.img_dir_var.set(d)
            self.refresh_scene_list()

    def browse_aud_dir(self):
        d = filedialog.askdirectory(initialdir=LONG_FORMAT_ROOT, title="Select Audio Directory")
        if d: self.aud_dir_var.set(d)

    def browse_out_video(self):
        f = filedialog.asksaveasfilename(initialdir=WORKSPACE, defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if f: self.out_video_var.set(f)

    # --- BADGE REPOSITIONING & EDITING LOGIC ---
    def save_current_scene_in_memory(self):
        """Silently auto-commit whatever the user tweaked for the currently active scene."""
        if hasattr(self, 'current_scene_loaded') and self.current_scene_loaded:
            sc_num = self.current_scene_loaded
            new_x = self.x_pos_var.get()
            new_y = self.y_pos_var.get()
            new_scale = round(self.scale_var.get(), 2)
            new_text = self.text_edit_var.get().strip()
            wrap_w = self.wrap_width_var.get() if (hasattr(self, 'enable_wrap_var') and self.enable_wrap_var.get()) else 0
            
            self.badge_positions[sc_num] = {
                "x": new_x,
                "y": new_y,
                "scale": new_scale,
                "text": new_text,
                "wrap_width": wrap_w
            }

    def on_scene_selected(self, event=None):
        # Auto-save current scene in memory before switching so edits are NEVER lost/undone!
        self.save_current_scene_in_memory()
        self.update_scene_editor_fields()

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

    def on_wrap_slider_moved(self, val):
        w_val = int(float(val))
        self.lbl_wrap_val.config(text=f"{w_val}px")
        self.preview_repositioned_badge()

    def on_fsize_slider_moved(self, val):
        fs_val = int(float(val))
        self.lbl_fsize_val.config(text=f"{fs_val}px")
        self.preview_repositioned_badge()

    def on_wrap_toggled(self):
        self.preview_repositioned_badge()

    def on_text_edited(self, event=None):
        self.preview_repositioned_badge()

    def save_current_position(self, show_msg=True):
        sc_str = self.selected_scene_var.get()
        if not sc_str:
            return
        sc_num = sc_str.replace("Scene ", "").strip()
        new_x = self.x_pos_var.get()
        new_y = self.y_pos_var.get()
        new_scale = round(self.scale_var.get(), 2)
        new_text = self.text_edit_var.get().strip()
        fsize = self.font_size_var.get() if hasattr(self, 'font_size_var') else 46

        # Update disk badge PNG with text wrapping and font size
        bname = f"p2_b{sc_num}.png"
        wrap_w = self.wrap_width_var.get() if (hasattr(self, 'enable_wrap_var') and self.enable_wrap_var.get()) else 0

        if new_text:
            orig_txt = ""
            if sc_num in DEFAULT_BADGE_MAP:
                orig_txt = DEFAULT_BADGE_MAP[sc_num][0][1]
            # Use original theme colors from Editing Directions based on scene number
            try:
                sc_int = int(sc_num)
            except Exception:
                sc_int = 1
            bg_col = "#EADBC8" if (sc_int % 2 != 0) else "#FAF8F5"

            self.log(f"Rendering high-precision badge image for {sc_str}: '{new_text}' (BG={bg_col}, Font={fsize}px, Wrap={wrap_w}px)")
            render_single_badge_to_disk(new_text, bg=bg_col, txt_col="#2B3A67", border_col="#2B3A67", shadow_col="#2B3A67", fsize=fsize, strike=False, out_filename=bname, overwrite=True, wrap_width=wrap_w)
            self.preview_repositioned_badge()

        self.badge_positions[sc_num] = {
            "x": new_x,
            "y": new_y,
            "scale": new_scale,
            "font_size": fsize,
            "text": new_text,
            "wrap_width": wrap_w
        }
        save_manual_positions(self.badge_positions)
        self.log(f"Saved settings for {sc_str}: X={new_x}px, Y={new_y}px, Scale={int(new_scale*100)}%, Text='{new_text}'")
        if show_msg:
            messagebox.showinfo("Settings Saved", f"{sc_str} settings saved!\nX: {new_x}px | Y: {new_y}px | Scale: {int(new_scale*100)}%\nText: '{new_text}'\nWill be used on next render!")

    def save_all_scenes(self):
        # First save current active scene from sliders and text field
        self.save_current_position(show_msg=False)
        
        # Save all scenes into manual_badge_positions.json
        save_manual_positions(self.badge_positions)
        total_saved = len(self.badge_positions)
        self.log(f"SUCCESS: Saved all settings across all {total_saved} scenes to manual_badge_positions.json!")
        messagebox.showinfo("All Scenes Saved", f"Successfully saved settings across all {total_saved} scenes!\n\nAll X/Y coordinates, scaling, and text entries are permanently stored and ready for video rendering.")

    def preview_repositioned_badge(self):
        sc_str = self.selected_scene_var.get()
        if not sc_str:
            return
        sc_num = int(sc_str.replace("Scene ", "").strip())
        img_dir = self.img_dir_var.get()
        
        # Locate image file
        img_p = os.path.join(img_dir, f"Image_{sc_num:03d}.png")
        if not os.path.exists(img_p):
            # Check other image extensions or listing
            all_imgs = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]) if os.path.exists(img_dir) else []
            if sc_num - 1 < len(all_imgs):
                img_p = os.path.join(img_dir, all_imgs[sc_num - 1])
            else:
                return

        im = Image.open(img_p).convert('RGB')
        w, h = im.size
        scale = max(WIDTH / w, HEIGHT / h)
        nw, nh = int(w * scale), int(h * scale)
        im_res = im.resize((nw, nh), Image.LANCZOS).crop(((nw-WIDTH)//2, (nh-HEIGHT)//2, (nw-WIDTH)//2+WIDTH, (nh-HEIGHT)//2+HEIGHT))

        cur_text = self.text_edit_var.get().strip() if hasattr(self, 'text_edit_var') else ""
        wrap_w = self.wrap_width_var.get() if (hasattr(self, 'enable_wrap_var') and self.enable_wrap_var.get()) else 0
        fsize = self.font_size_var.get() if hasattr(self, 'font_size_var') else 46
        try:
            sc_int = int(sc_num)
        except Exception:
            sc_int = 1
        bg_col = "#EADBC8" if (sc_int % 2 != 0) else "#FAF8F5"

        b_im = None
        # Check if disk badge exists
        candidates = [f"p2_b{sc_num}.png", f"b{sc_num}.png"]
        bpath = None
        for cand in candidates:
            p = os.path.join(BADGE_DIR, cand)
            if os.path.exists(p):
                bpath = p
                break

        # Load badge image:
        # If user enabled wrap (< 850px) or modified text, generate wrapped badge on-the-fly with authentic styling.
        # Otherwise, load pre-rendered Edge badge from disk.
        is_wrap_active = (wrap_w > 0 and wrap_w < 850)
        
        # Look up colors from parsed editing directions or default palette
        txt_col = "#2B2D6E" if (sc_int % 2 != 0) else "#7A1F3D"
        border_col = "#141414"
        shadow_col = "#7A1F3D" if (sc_int % 2 != 0) else "#2B2D6E"

        if is_wrap_active and cur_text:
            b_im = render_dynamic_preview_badge(cur_text, wrap_width=wrap_w, fsize=fsize, bg=bg_col, txt_col=txt_col, border_col=border_col, shadow_col=shadow_col)
        elif bpath and os.path.exists(bpath):
            try:
                b_im = Image.open(bpath).convert('RGBA')
            except Exception:
                b_im = None

        if b_im is None and cur_text:
            b_im = render_dynamic_preview_badge(cur_text, wrap_width=wrap_w, fsize=fsize, bg=bg_col, txt_col=txt_col, border_col=border_col, shadow_col=shadow_col)

        if b_im is not None:
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

        # Show on canvas (16:9 480x270)
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
            scenes_cfg = []
            for s_idx in range(num_scenes):
                sc_num = str(s_idx + 1)
                bcfg = pos.get(sc_num, {"x": WIDTH // 2, "y": 120, "scale": 1.0})
                
                # Check for available badge image
                bname = f"p2_b{sc_num}.png"
                if not os.path.exists(os.path.join(BADGE_DIR, bname)):
                    if os.path.exists(os.path.join(BADGE_DIR, f"b{sc_num}.png")):
                        bname = f"b{sc_num}.png"
                
                # If scene has a sub-badge configuration (e.g. 8_1, 8_2 or 11_1, 11_2)
                if f"{sc_num}_1" in pos and f"{sc_num}_2" in pos:
                    cfg_1 = pos.get(f"{sc_num}_1", {"x": WIDTH // 2, "y": 110, "scale": 1.0})
                    cfg_2 = pos.get(f"{sc_num}_2", {"x": WIDTH // 2, "y": 250, "scale": 1.0})
                    scenes_cfg.append({"badges": [
                        (f"p2_b{sc_num}_1.png", cfg_1, 0.2, 0.25),
                        (f"p2_b{sc_num}_2.png", cfg_2, 1.2, 0.25)
                    ]})
                else:
                    scenes_cfg.append({"badges": [(bname, bcfg, 0.2, 0.25)]})

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
