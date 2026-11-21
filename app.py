"""
Auto Video Creator Studio - Desktop Application
------------------------------------------------
Features:
1. Dynamic Latest Project Folder Auto-Detection:
   - Detects the latest project folder in 'Fasting Series' with Images/ and Audio/ subfolders.
2. Single Animation Style Per Video with Video-to-Video Shuffle/Cycle:
   - "Auto-Cycle 25 Styles (1 Style Per Video)": Every video has 1 uniform style, and next video cycles to the next style.
   - Or choose any specific style manually.
3. Interactive Real-time Video Preview Player:
   - Play/Pause, Rewind (-5s, -10s), Fast Forward (+5s, +10s), live slider scrubbing.
4. Auto-Loads Newly Rendered Video immediately.
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

from animations_engine import ANIMATION_STYLES_LIST, render_badge_advanced, stamp_badge_final

WIDTH = 1080
HEIGHT = 1920
FPS = 30
SAMPLE_RATE = 44100
WORKSPACE = r"c:\Users\aanil\Documents\Auto_Video_Editing"
BADGE_DIR = os.path.join(WORKSPACE, "rendered_badges")
SERIES_ROOT = r"C:\Users\aanil\Documents\Anxious Anil\Shorts Videos\Projects\Fasting Series"
STATE_FILE = os.path.join(WORKSPACE, "animation_cycle_state.json")

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
        self.title("Auto Video Creator Studio - 25 Shuffled Styles & Video Player")
        self.geometry("1120x840")
        self.minsize(980, 750)
        self.configure(bg="#0F172A")
        
        # Styles
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("TLabel", background="#0F172A", foreground="#F8FAFC", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 15, "bold"), foreground="#F59E0B")
        self.style.configure("TButton", font=("Segoe UI", 9, "bold"), background="#1E293B", foreground="#F8FAFC")
        self.style.map("TButton", background=[("active", "#334155")])
        self.style.configure("Action.TButton", font=("Segoe UI", 11, "bold"), background="#F59E0B", foreground="#0F172A")
        self.style.map("Action.TButton", background=[("active", "#D97706")])
        self.style.configure("TCombobox", fieldbackground="#0F172A", foreground="#F8FAFC", background="#1E293B")

        # Discover latest project folder
        latest_folder = detect_latest_project_folder()
        if latest_folder:
            default_img = os.path.join(latest_folder, "Images")
            default_aud = os.path.join(latest_folder, "Audio")
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

        # Video Player state
        self.cap = None
        self.is_playing = False
        self.video_total_frames = 0
        self.video_fps = 30.0
        self.current_frame_idx = 0
        self.is_rendering = False

        self.create_widgets()
        
        # Auto-load latest rendered video if available
        rendered_candidates = [
            os.path.join(WORKSPACE, "Fasting_Series_3_wave_unfold.mp4"),
            os.path.join(WORKSPACE, "Fasting_Series_2_elastic_pop.mp4"),
            self.out_video_var.get()
        ]
        for cand in rendered_candidates:
            if os.path.exists(cand):
                self.load_video_file(cand)
                break

    def create_widgets(self):
        # Header
        hdr = tk.Frame(self, bg="#0F172A")
        hdr.pack(fill=tk.X, padx=20, pady=(15, 8))
        lbl_title = ttk.Label(hdr, text="🎬 Auto Video Creator Studio (1 Style Per Video • Auto-Shuffle)", style="Header.TLabel")
        lbl_title.pack(anchor=tk.W)
        lbl_desc = ttk.Label(hdr, text="Auto-detects latest Fasting Series folder. Renders 1 style per video and shuffles to the next style for each video.")
        lbl_desc.pack(anchor=tk.W)

        # Main Split: Left = Controls & Logs, Right = Video Player
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#0F172A", sashwidth=4)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        left_frame = tk.Frame(main_paned, bg="#0F172A")
        right_frame = tk.Frame(main_paned, bg="#1E293B", relief=tk.RIDGE, bd=1)
        main_paned.add(left_frame, minsize=540)
        main_paned.add(right_frame, minsize=380)

        # --- LEFT: Project Configuration ---
        cfg_frame = tk.LabelFrame(left_frame, text=" Project Assets (Auto-Detected Latest Folder) ", bg="#1E293B", fg="#F59E0B", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        cfg_frame.pack(fill=tk.X, pady=(0, 8))

        btn_auto_detect = tk.Button(cfg_frame, text="🔄 Auto-Detect Latest Project Folder", bg="#0284C7", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, pady=3, command=self.refresh_latest_folder)
        btn_auto_detect.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 6))

        self.add_browse_row(cfg_frame, "📁 Images Folder:", self.img_dir_var, self.browse_img_dir, 1)
        self.add_browse_row(cfg_frame, "🎵 Audio Folder:", self.aud_dir_var, self.browse_aud_dir, 2)
        self.add_browse_row(cfg_frame, "📝 Directions:", self.edit_dir_var, self.browse_edit_file, 3)
        self.add_browse_row(cfg_frame, "🎙️ Transcribe:", self.trans_var, self.browse_trans_file, 4)
        self.add_browse_row(cfg_frame, "💾 Export Video:", self.out_video_var, self.browse_out_video, 5)

        # 25-Style Animation Selection
        anim_box = tk.LabelFrame(left_frame, text=" 25 Animation Styles (1 Uniform Style Per Video • Auto-Shuffle) ", bg="#1E293B", fg="#38BDF8", font=("Segoe UI", 10, "bold"), padx=12, pady=8)
        anim_box.pack(fill=tk.X, pady=(0, 8))

        chk_en = ttk.Checkbutton(anim_box, text="Enable Kinetic Typography Animations", variable=self.enable_anim_var)
        chk_en.pack(anchor=tk.W)

        next_s, _ = get_next_cycle_style()
        modes = [f"Cycle Style Per Video (Next: {next_s})"] + ANIMATION_STYLES_LIST
        lbl_m = ttk.Label(anim_box, text="Animation Mode:")
        lbl_m.pack(anchor=tk.W, pady=(4, 2))
        self.cmb_anim = ttk.Combobox(anim_box, values=modes, textvariable=self.anim_mode_var, state="readonly", width=45)
        self.cmb_anim.pack(fill=tk.X, pady=(0, 4))

        # Render Button & Progress
        self.btn_render = tk.Button(left_frame, text="🚀 START VIDEO RENDER", bg="#F59E0B", fg="#0F172A", font=("Segoe UI", 11, "bold"), relief=tk.FLAT, pady=8, command=self.start_render_thread)
        self.btn_render.pack(fill=tk.X, pady=4)

        self.progress_bar = ttk.Progressbar(left_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=3)

        self.lbl_status = ttk.Label(left_frame, text="Ready. Verify count and click Start Video Render.")
        self.lbl_status.pack(anchor=tk.W, pady=(0, 5))

        # Log Console
        log_frame = tk.LabelFrame(left_frame, text=" Build Console & Logs ", bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 9), padx=8, pady=6)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_log = tk.Text(log_frame, bg="#0F172A", fg="#38BDF8", insertbackground="white", font=("Consolas", 8), relief=tk.FLAT, height=8)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.txt_log.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log['yscrollcommand'] = scroll.set

        # --- RIGHT: Video Preview Player ---
        lbl_p_title = tk.Label(right_frame, text="📺 Interactive Video Preview Player", bg="#1E293B", fg="#F59E0B", font=("Segoe UI", 11, "bold"))
        lbl_p_title.pack(pady=(10, 4))

        # 9:16 Canvas
        self.canvas_w = 270
        self.canvas_h = 480
        self.preview_canvas = tk.Canvas(right_frame, width=self.canvas_w, height=self.canvas_h, bg="#000000", highlightthickness=0)
        self.preview_canvas.pack(pady=4)

        # Scrubber Slider
        self.slider_var = tk.DoubleVar()
        self.slider = ttk.Scale(right_frame, orient=tk.HORIZONTAL, from_=0, to=100, variable=self.slider_var, command=self.on_slider_scroll)
        self.slider.pack(fill=tk.X, padx=20, pady=(6, 2))

        # Timecode Label
        self.lbl_timecode = tk.Label(right_frame, text="00:00 / 00:00 (Frame 0)", bg="#1E293B", fg="#94A3B8", font=("Consolas", 9))
        self.lbl_timecode.pack(pady=(0, 6))

        # Player Controls Buttons
        ctrl_frame = tk.Frame(right_frame, bg="#1E293B")
        ctrl_frame.pack(pady=(0, 10))

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

        btn_open = tk.Button(right_frame, text="📂 Open External Player", bg="#334155", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, command=self.open_external_video)
        btn_open.pack(pady=(2, 10))

    def refresh_latest_folder(self):
        latest = detect_latest_project_folder()
        if latest:
            self.img_dir_var.set(os.path.join(latest, "Images"))
            self.aud_dir_var.set(os.path.join(latest, "Audio"))
            self.log(f"Auto-detected latest folder: {latest}")
            messagebox.showinfo("Project Detected", f"Auto-selected latest project:\n{os.path.basename(latest)}")
        else:
            messagebox.showwarning("Not Found", "No project directories with Images and Audio found.")

    def add_browse_row(self, parent, label_text, str_var, browse_cmd, row_idx):
        lbl = tk.Label(parent, text=label_text, bg="#1E293B", fg="#E2E8F0", font=("Segoe UI", 9))
        lbl.grid(row=row_idx, column=0, sticky=tk.W, pady=3)
        ent = ttk.Entry(parent, textvariable=str_var, width=42)
        ent.grid(row=row_idx, column=1, sticky=tk.EW, padx=6, pady=3)
        btn = ttk.Button(parent, text="Browse...", command=browse_cmd)
        btn.grid(row=row_idx, column=2, pady=3)
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

    def browse_edit_file(self):
        f = filedialog.askopenfilename(initialdir=WORKSPACE, filetypes=[("Text Files", "*.txt")])
        if f: self.edit_dir_var.set(f)

    def browse_trans_file(self):
        f = filedialog.askopenfilename(initialdir=WORKSPACE, filetypes=[("Text Files", "*.txt")])
        if f: self.trans_var.set(f)

    def browse_out_video(self):
        f = filedialog.asksaveasfilename(initialdir=WORKSPACE, defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if f: self.out_video_var.set(f)

    # --- VIDEO PLAYER CONTROLS ---
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
        self.seek_frame(0)
        self.log(f"Loaded video preview: {os.path.basename(video_path)} ({self.video_total_frames} frames)")

    def seek_frame(self, frame_num):
        if self.cap is None or self.video_total_frames == 0:
            return
        frame_num = max(0, min(self.video_total_frames - 1, frame_num))
        self.current_frame_idx = frame_num
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        if ret:
            self.display_frame(frame)
            self.update_player_ui()

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
        else:
            self.is_playing = True
            self.btn_play.config(text="⏸ PAUSE", bg="#10B981")
            self.play_loop()

    def play_loop(self):
        if not self.is_playing or self.cap is None:
            return
        
        ret, frame = self.cap.read()
        if ret:
            self.current_frame_idx += 1
            self.display_frame(frame)
            self.update_player_ui()
            delay_ms = int(1000 / self.video_fps)
            self.after(delay_ms, self.play_loop)
        else:
            self.is_playing = False
            self.btn_play.config(text="▶ PLAY", bg="#F59E0B")
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

            # Scenes badge configuration mapping strictly in verified clean cream space
            scenes_cfg = [
                # Scene 1: Welcome signboard is at y=800; top cream space (0-200)
                {"badges": [("p2_b1.png", 95, 0.2, 0.25)]},
                # Scene 2: Stomach layers starts at y=263; top cream space (0-263)
                {"badges": [("p2_b2.png", 130, 0.2, 0.25)]},
                # Scene 3: Nonstop digestion signboard at y=368; top cream space (0-368)
                {"badges": [("p2_b3.png", 170, 0.2, 0.25)]},
                # Scene 4: Backup System signboard at y=187; top cream space (0-187)
                {"badges": [("p2_b4.png", 90, 0.2, 0.25)]},
                # Scene 5: Inside Torso chalkboard starts at y=280; top cream space (0-280)
                {"badges": [("p2_b5.png", 120, 0.2, 0.25)]},
                # Scene 6: Simple Breakdown chalkboard at top; clean cream floor at bottom (1498-1899)
                {"badges": [("p2_b6.png", 1600, 0.2, 0.25)]},
                # Scene 7: Glycogen Battery sign starts at y=241; top cream space (0-241)
                {"badges": [("p2_b7.png", 120, 0.2, 0.25)]},
                # Scene 8: Cupboard starts at y=454; top cream space (0-454) for both chips
                {"badges": [("p2_b8_1.png", 110, 0.2, 0.25), ("p2_b8_2.png", 250, 1.5, 0.25)]},
                # Scene 9: Brain Ketone cutaway starts at y=434; top cream space (0-434)
                {"badges": [("p2_b9.png", 170, 0.2, 0.25)]},
                # Scene 10: Cell Autophagy sign at top; clean cream floor below table at bottom (1526-1899)
                {"badges": [("p2_b10.png", 1600, 0.2, 0.25)]},
                # Scene 11: Scale & Armchair starts at y=448; top cream space (0-448) for both badges
                {"badges": [("p2_b11_1.png", 120, 0.2, 0.25), ("p2_b11_2.png", 260, 1.2, 0.25)]},
                # Scene 12: Mitochondria starts at y=414; top cream space (58-414)
                {"badges": [("p2_b12.png", 160, 0.2, 0.25)]},
                # Scene 13: Repaired cell starts at y=343; top cream space (0-343) for both badges
                {"badges": [("p2_b13_1.png", 110, 0.2, 0.25), ("p2_b13_2.png", 250, 1.0, 0.25)]},
                # Scene 14: Outro chalkboard at top; clean cream floor at bottom (1492-1709)
                {"badges": [("p2_b14.png", 1600, 0.2, 0.25)]},
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
                for bname, cy, ent_delay, ex_lead in cfg["badges"]:
                    bpath = os.path.join(BADGE_DIR, bname)
                    if os.path.exists(bpath):
                        b_rgba = cv2.imread(bpath, cv2.IMREAD_UNCHANGED)
                        loaded_badges.append({
                            "bgr": b_rgba[:, :, :3],
                            "alpha": (b_rgba[:, :, 3].astype(np.float32) / 255.0),
                            "target_y": cy,
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
                            x_center=WIDTH // 2, y_center=target_y,
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

            # Auto load into preview player
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
