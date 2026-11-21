"""
Auto Video Creator Studio - Desktop Application (with Video Preview & 25-Style Animation Engine)
-------------------------------------------------------------------------------------------------
Features:
1. File & Folder Selectors:
   - Images Folder, Audio Folder, Editing Directions, Transcribe file, Output MP4.
2. Image & Audio Count Verification:
   - Verifies that count(images) == count(audio) before allowing render.
3. 25-Style Shuffled Animation Engine:
   - Automatically picks from 25 distinct kinetic typography algorithms on every build so YouTube never flags repetitive templates.
   - Can also be set to Shuffled, Specific Style, or Disabled.
4. Built-in Real-time Video Preview Player:
   - Play / Pause
   - Fast Forward (+5s, +10s)
   - Rewind (-5s, -10s)
   - Frame-by-frame scrubbing slider
   - Live timecode & preview canvas before exporting or after rendering
5. Output Destination & Filename Renamer:
   - Choose any folder and type any filename for your exported video.
6. 100% Offline & AI-Free.
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
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        samples = np.frombuffer(data, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        samples = np.frombuffer(data, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
        
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)
        
    if framerate != SAMPLE_RATE:
        new_len = int(len(samples) * SAMPLE_RATE / framerate)
        indices = np.linspace(0, len(samples) - 1, new_len)
        samples = np.interp(indices, np.arange(len(samples)), samples)
        
    return samples

def load_badge_cv(name):
    p = os.path.join(BADGE_DIR, f"{name}.png")
    if not os.path.exists(p):
        return None, None
    im = Image.open(p)
    arr = np.array(im)
    bgr = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
    alpha = arr[:, :, 3].astype(np.float32) / 255.0
    return bgr, alpha

def transform_frame(img, zoom=1.0, pan_x=0.0, pan_y=0.0):
    h, w = img.shape[:2]
    center_x = w / 2.0 + pan_x * w * 0.1
    center_y = h / 2.0 + pan_y * h * 0.1
    M = cv2.getRotationMatrix2D((center_x, center_y), 0, zoom)
    M[0, 2] += (w / 2.0 - center_x)
    M[1, 2] += (h / 2.0 - center_y)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

class AutoVideoStudioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto Video Creator Studio - 25 Shuffled Styles & Video Player")
        self.geometry("1100x820")
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

        # Variables
        default_proj = r"C:\Users\aanil\Documents\Anxious Anil\Shorts Videos\Projects\Fasting Series\ఆకలి వేసిన వెంటనే మన Body నిజంగా Fatని Burn చేస్తుందా_"
        self.img_dir_var = tk.StringVar(value=os.path.join(default_proj, "Images"))
        self.aud_dir_var = tk.StringVar(value=os.path.join(default_proj, "Audio"))
        self.edit_dir_var = tk.StringVar(value=os.path.join(WORKSPACE, "Editing_Directions.txt"))
        self.trans_var = tk.StringVar(value=os.path.join(WORKSPACE, "transcribe.txt"))
        self.out_video_var = tk.StringVar(value=os.path.join(WORKSPACE, "Fasting_Short_25_Animations.mp4"))
        
        self.anim_mode_var = tk.StringVar(value="Shuffle 25 Styles (Recommended for YouTube)")
        self.enable_anim_var = tk.BooleanVar(value=True)

        # Video Player state
        self.cap = None
        self.is_playing = False
        self.video_total_frames = 0
        self.video_fps = 30.0
        self.current_frame_idx = 0
        self.is_rendering = False

        self.create_widgets()
        
        # Auto-load existing video into player if available
        if os.path.exists(self.out_video_var.get()):
            self.load_video_file(self.out_video_var.get())

    def create_widgets(self):
        # Header
        hdr = tk.Frame(self, bg="#0F172A")
        hdr.pack(fill=tk.X, padx=20, pady=(15, 8))
        lbl_title = ttk.Label(hdr, text="🎬 Auto Video Creator Studio (25 Shuffled Typography Styles)", style="Header.TLabel")
        lbl_title.pack(anchor=tk.W)
        lbl_desc = ttk.Label(hdr, text="Zero AI, 100% Offline. Includes live video player controls: Play, Pause, Rewind, Fast-Forward, and Scrubbing.")
        lbl_desc.pack(anchor=tk.W)

        # Main Split: Left = Controls & Logs, Right = Video Player
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#0F172A", sashwidth=4)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        left_frame = tk.Frame(main_paned, bg="#0F172A")
        right_frame = tk.Frame(main_paned, bg="#1E293B", relief=tk.RIDGE, bd=1)
        main_paned.add(left_frame, minsize=520)
        main_paned.add(right_frame, minsize=380)

        # --- LEFT: Project Configuration ---
        cfg_frame = tk.LabelFrame(left_frame, text=" Project Assets Configuration ", bg="#1E293B", fg="#F59E0B", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        cfg_frame.pack(fill=tk.X, pady=(0, 8))

        self.add_browse_row(cfg_frame, "📁 Images Folder:", self.img_dir_var, self.browse_img_dir, 0)
        self.add_browse_row(cfg_frame, "🎵 Audio Folder:", self.aud_dir_var, self.browse_aud_dir, 1)
        self.add_browse_row(cfg_frame, "📝 Directions:", self.edit_dir_var, self.browse_edit_file, 2)
        self.add_browse_row(cfg_frame, "🎙️ Transcribe:", self.trans_var, self.browse_trans_file, 3)
        self.add_browse_row(cfg_frame, "💾 Export Video:", self.out_video_var, self.browse_out_video, 4)

        # 25-Style Animation Selection
        anim_box = tk.LabelFrame(left_frame, text=" 25 Cinematic Typography Animation Engine ", bg="#1E293B", fg="#38BDF8", font=("Segoe UI", 10, "bold"), padx=12, pady=8)
        anim_box.pack(fill=tk.X, pady=(0, 8))

        chk_en = ttk.Checkbutton(anim_box, text="Enable Kinetic Animations", variable=self.enable_anim_var)
        chk_en.pack(anchor=tk.W)

        modes = ["Shuffle 25 Styles (Recommended for YouTube)"] + ANIMATION_STYLES_LIST
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

    def add_browse_row(self, parent, label_text, str_var, browse_cmd, row_idx):
        lbl = tk.Label(parent, text=label_text, bg="#1E293B", fg="#E2E8F0", font=("Segoe UI", 9))
        lbl.grid(row=row_idx, column=0, sticky=tk.W, pady=3)
        entry = tk.Entry(parent, textvariable=str_var, bg="#0F172A", fg="#F8FAFC", insertbackground="white", font=("Segoe UI", 9), relief=tk.FLAT, width=38)
        entry.grid(row=row_idx, column=1, padx=6, pady=3, sticky=tk.EW)
        btn = tk.Button(parent, text="Browse...", bg="#334155", fg="#F8FAFC", font=("Segoe UI", 8, "bold"), relief=tk.FLAT, command=browse_cmd)
        btn.grid(row=row_idx, column=2, pady=3)
        parent.columnconfigure(1, weight=1)

    def browse_img_dir(self):
        d = filedialog.askdirectory(title="Select Images Folder", initialdir=self.img_dir_var.get())
        if d: self.img_dir_var.set(d)

    def browse_aud_dir(self):
        d = filedialog.askdirectory(title="Select Audio Folder", initialdir=self.aud_dir_var.get())
        if d: self.aud_dir_var.set(d)

    def browse_edit_file(self):
        f = filedialog.askopenfilename(title="Select Editing Directions File", filetypes=[("Text files", "*.txt")])
        if f: self.edit_dir_var.set(f)

    def browse_trans_file(self):
        f = filedialog.askopenfilename(title="Select Transcribe File", filetypes=[("Text files", "*.txt")])
        if f: self.trans_var.set(f)

    def browse_out_video(self):
        current_path = self.out_video_var.get()
        init_dir = os.path.dirname(current_path) if current_path else WORKSPACE
        init_file = os.path.basename(current_path) if current_path else "My_Short_Video.mp4"
        f = filedialog.asksaveasfilename(
            title="Choose Name and Destination for Export Video", 
            initialdir=init_dir,
            initialfile=init_file,
            defaultextension=".mp4", 
            filetypes=[("MP4 Video (*.mp4)", "*.mp4"), ("All files (*.*)", "*.*")]
        )
        if f: 
            self.out_video_var.set(f)
            self.log(f"Export filename set to: {os.path.basename(f)}")

    def log(self, text):
        self.txt_log.insert(tk.END, text + "\n")
        self.txt_log.see(tk.END)

    # --- VIDEO PLAYER LOGIC ---
    def load_video_file(self, video_path):
        if not os.path.exists(video_path):
            return
        if self.cap:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(video_path)
        self.video_total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.slider.config(to=max(1, self.video_total_frames - 1))
        self.current_frame_idx = 0
        self.show_frame(0)
        self.update_timecode()

    def show_frame(self, frame_idx):
        if not self.cap or not self.cap.isOpened():
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if ret:
            # Resize for 9:16 canvas
            h, w = frame.shape[:2]
            scaled = cv2.resize(frame, (self.canvas_w, self.canvas_h), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(scaled, cv2.COLOR_BGR2RGB)
            self.photo = ImageTk.PhotoImage(image=Image.fromarray(rgb))
            self.preview_canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

    def update_timecode(self):
        cur_sec = self.current_frame_idx / self.video_fps if self.video_fps > 0 else 0
        tot_sec = self.video_total_frames / self.video_fps if self.video_fps > 0 else 0
        c_m, c_s = divmod(int(cur_sec), 60)
        t_m, t_s = divmod(int(tot_sec), 60)
        self.lbl_timecode.config(text=f"{c_m:02d}:{c_s:02d} / {t_m:02d}:{t_s:02d} (Frame {self.current_frame_idx}/{self.video_total_frames})")

    def toggle_play(self):
        if not self.cap or not self.cap.isOpened():
            target_vid = self.out_video_var.get()
            if os.path.exists(target_vid):
                self.load_video_file(target_vid)
            else:
                messagebox.showinfo("Preview", "No video loaded yet. Render the video or select an existing output video file.")
                return

        if self.is_playing:
            self.is_playing = False
            self.btn_play.config(text="▶ PLAY", bg="#F59E0B")
        else:
            self.is_playing = True
            self.btn_play.config(text="⏸ PAUSE", bg="#EF4444")
            self.play_loop()

    def play_loop(self):
        if not self.is_playing:
            return
        if self.current_frame_idx >= self.video_total_frames - 1:
            self.is_playing = False
            self.btn_play.config(text="▶ PLAY", bg="#F59E0B")
            return

        self.current_frame_idx += 1
        self.slider_var.set(self.current_frame_idx)
        self.show_frame(self.current_frame_idx)
        self.update_timecode()
        
        delay_ms = int(1000 / self.video_fps)
        self.after(delay_ms, self.play_loop)

    def on_slider_scroll(self, val):
        if not self.cap or not self.cap.isOpened():
            return
        target = int(float(val))
        self.current_frame_idx = target
        self.show_frame(target)
        self.update_timecode()

    def seek_seconds(self, delta_s):
        if not self.cap or not self.cap.isOpened():
            return
        delta_f = int(delta_s * self.video_fps)
        new_f = max(0, min(self.video_total_frames - 1, self.current_frame_idx + delta_f))
        self.current_frame_idx = new_f
        self.slider_var.set(new_f)
        self.show_frame(new_f)
        self.update_timecode()

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

        # Pause preview if playing
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

            temp_vid = os.path.join(WORKSPACE, "temp_gui_video.mp4")
            temp_aud = os.path.join(WORKSPACE, "temp_gui_audio.wav")

            num_scenes = len(img_files)
            self.log(f"Starting Video Render for {num_scenes} scenes...")
            self.log(f"Images: {img_dir}")
            self.log(f"Audio: {aud_dir}")

            # 25 Shuffled Styles Selection
            if "Shuffle 25" in mode_choice:
                shuffled_styles = random.sample(ANIMATION_STYLES_LIST, len(ANIMATION_STYLES_LIST))
                self.log(f"Dynamic Shuffled Animation Pool: {shuffled_styles[:6]}...")
            else:
                shuffled_styles = [mode_choice] * 25
                self.log(f"Single Selected Animation Style: {mode_choice}")

            scene_anims = {
                1: shuffled_styles[0],
                2: shuffled_styles[1],
                3: shuffled_styles[2],
                4: shuffled_styles[3],
                5: shuffled_styles[4],
                6: shuffled_styles[5],
                '7_1': shuffled_styles[6],
                '7_2': shuffled_styles[7],
                8: shuffled_styles[8],
                '9_1': shuffled_styles[9],
                '9_2': shuffled_styles[10],
                '10_1': shuffled_styles[11],
                '10_2': shuffled_styles[12],
                11: shuffled_styles[13],
                12: shuffled_styles[14],
                13: shuffled_styles[15],
                '14_1': shuffled_styles[16],
                '14_2': shuffled_styles[17],
                15: shuffled_styles[18],
            }

            # 1. Load assets
            base_images = []
            audio_durations = []
            audio_samples_list = []
            
            for i in range(num_scenes):
                im_p = os.path.join(img_dir, img_files[i])
                au_p = os.path.join(aud_dir, aud_files[i])
                
                im = read_image_utf8(im_p)
                im_res = cv2.resize(im, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
                base_images.append(im_res)
                
                dur = get_audio_duration(au_p)
                audio_durations.append(dur)
                
                samples = load_audio_samples(au_p)
                audio_samples_list.append(samples)
                
            total_dur = sum(audio_durations)
            scene_frames = [int(d * FPS) for d in audio_durations]
            total_frames = sum(scene_frames)
            
            self.log(f"Total Video Duration: {total_dur:.2f}s ({total_frames} frames)")

            # 2. Badges
            badges = {
                'b1': load_badge_cv('b1'),
                'b2': load_badge_cv('b2'),
                'b3': load_badge_cv('b3'),
                'b4': load_badge_cv('b4_stacked'),
                'b5': load_badge_cv('b5'),
                'b6': load_badge_cv('b6'),
                'b7_1': load_badge_cv('b7_1'),
                'b7_2': load_badge_cv('b7_2'),
                'b8': load_badge_cv('b8'),
                'b9_1': load_badge_cv('b9_1'),
                'b9_2': load_badge_cv('b9_2'),
                'b10_1': load_badge_cv('b10_1_wrapped'),
                'b10_2': load_badge_cv('b10_2_wrapped'),
                'b11': load_badge_cv('b11'),
                'b12': load_badge_cv('b12'),
                'b13': load_badge_cv('b13'),
                'b14_1': load_badge_cv('b14_1'),
                'b14_2': load_badge_cv('b14_2'),
                'b15': load_badge_cv('b15'),
            }

            # 3. Transitions
            TRANS_FRAMES = 8
            motions = [
                'zoom_in', 'zoom_in', 'pan_right', 'zoom_in', 'pan_left', 
                'zoom_in', 'pan_right', 'zoom_in', 'zoom_in', 'pan_right', 
                'zoom_in', 'pan_up', 'zoom_in', 'zoom_out', 'zoom_out'
            ]

            # 4. FFmpeg Video Pipe
            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{WIDTH}x{HEIGHT}',
                '-pix_fmt', 'bgr24',
                '-r', str(FPS),
                '-i', '-',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '18',
                '-pix_fmt', 'yuv420p',
                temp_vid
            ]
            proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
            rendered_frames = 0
            
            for i in range(num_scenes):
                s_idx = i + 1
                n_frames = scene_frames[i]
                dur = audio_durations[i]
                cur_img = base_images[i]
                next_img = base_images[i + 1] if i + 1 < num_scenes else None
                motion = motions[i % len(motions)]
                
                for f in range(n_frames):
                    prog = f / max(1, n_frames - 1)
                    t_sec = prog * dur
                    
                    zoom, px, py = 1.0, 0.0, 0.0
                    if motion == 'zoom_in':
                        zoom = 1.0 + 0.035 * prog
                    elif motion == 'zoom_out':
                        zoom = 1.035 - 0.035 * prog
                    elif motion == 'pan_right':
                        zoom = 1.025
                        px = -0.015 + 0.03 * prog
                    elif motion == 'pan_left':
                        zoom = 1.025
                        px = 0.015 - 0.03 * prog
                    elif motion == 'pan_up':
                        zoom = 1.025
                        py = 0.015 - 0.03 * prog

                    is_trans = (next_img is not None) and (f >= n_frames - TRANS_FRAMES)
                    if is_trans:
                        tf = f - (n_frames - TRANS_FRAMES)
                        tp = (tf + 1) / (TRANS_FRAMES + 1)
                        ease = 0.5 - 0.5 * math.cos(math.pi * tp)
                        frame_a = transform_frame(cur_img, zoom=zoom, pan_x=px, pan_y=py)
                        frame_b = transform_frame(next_img, zoom=1.0, pan_x=0.0, pan_y=0.0)
                        
                        if s_idx in (1, 5, 14):
                            shift = int(WIDTH * ease)
                            frame = np.zeros_like(frame_a)
                            frame[:, :WIDTH - shift] = frame_a[:, shift:]
                            frame[:, WIDTH - shift:] = frame_b[:, :shift]
                            blur_k = int(abs(math.sin(tp * math.pi)) * 14) * 2 + 1
                            if blur_k > 1:
                                frame = cv2.GaussianBlur(frame, (blur_k, 1), 0)
                        elif s_idx == 2:
                            shift = int(HEIGHT * ease)
                            frame = np.zeros_like(frame_a)
                            frame[:HEIGHT - shift, :] = frame_a[shift:, :]
                            frame[HEIGHT - shift:, :] = frame_b[:shift, :]
                        elif s_idx == 3:
                            frame = transform_frame(next_img if tp > 0.5 else cur_img, zoom=1.06)
                        elif s_idx == 4:
                            scale = 1.0 - 0.3 * tp
                            h_s, w_s = int(HEIGHT * scale), int(WIDTH * scale)
                            scaled_a = cv2.resize(frame_a, (w_s, h_s))
                            frame = frame_b.copy()
                            y_off, x_off = (HEIGHT - h_s) // 2, (WIDTH - w_s) // 2
                            frame[y_off:y_off + h_s, x_off:x_off + w_s] = scaled_a
                        elif s_idx == 6:
                            half_w = int((WIDTH / 2) * tp)
                            frame = frame_b.copy()
                            frame[:, half_w:WIDTH - half_w] = frame_a[:, half_w:WIDTH - half_w]
                        elif s_idx == 7:
                            shift = int(WIDTH * ease)
                            frame = np.zeros_like(frame_a)
                            frame[:, shift:] = frame_a[:, :WIDTH - shift]
                            frame[:, :shift] = frame_b[:, WIDTH - shift:]
                        elif s_idx == 8:
                            shift = int(HEIGHT * ease)
                            frame = np.zeros_like(frame_a)
                            frame[:HEIGHT - shift, :] = frame_a[shift:, :]
                            frame[HEIGHT - shift:, :] = frame_b[:shift, :]
                        elif s_idx == 9:
                            frame_a_z = transform_frame(cur_img, zoom=1.0 + 0.3 * tp)
                            frame = cv2.addWeighted(frame_a_z, 1.0 - tp, frame_b, tp, 0)
                        elif s_idx == 10:
                            blend = cv2.addWeighted(frame_a, 1.0 - tp, frame_b, tp, 0)
                            flash = np.full_like(blend, int(math.sin(math.pi * tp) * 110), dtype=np.uint8)
                            frame = cv2.add(blend, flash)
                        elif s_idx == 11:
                            shake_x = int(math.sin(tp * 20) * 12)
                            M = np.float32([[1, 0, shake_x], [0, 1, 0]])
                            frame = cv2.warpAffine(frame_b, M, (WIDTH, HEIGHT))
                        elif s_idx == 12:
                            shift = int(HEIGHT * ease)
                            frame = np.zeros_like(frame_a)
                            frame[shift:, :] = frame_a[:HEIGHT - shift, :]
                            frame[:shift, :] = frame_b[HEIGHT - shift:, :]
                        elif s_idx == 13:
                            frame = transform_frame(next_img, zoom=1.10 - 0.10 * tp)
                        else:
                            frame = cv2.addWeighted(frame_a, 1.0 - ease, frame_b, ease, 0)
                    else:
                        frame = transform_frame(cur_img, zoom=zoom, pan_x=px, pan_y=py)

                    # Dynamic 25-Style Shuffled Badge Application
                    def apply_badge(bid, x, y, t_in, t_out, style_key):
                        bgr, alpha = badges[bid]
                        st = scene_anims.get(style_key, "elastic_pop")
                        draw_bgr, draw_alpha, dx, dy, op = render_badge_advanced(
                            bgr, alpha, t_sec, t_in, t_out, st, enable_anim
                        )
                        stamp_badge_final(frame, draw_bgr, draw_alpha, x, y, dx, dy, op)

                    if s_idx == 1:
                        apply_badge('b1', WIDTH // 2, 220, 0.2, dur, 1)
                    elif s_idx == 2:
                        apply_badge('b2', WIDTH // 2, 220, 0.1, dur, 2)
                    elif s_idx == 3:
                        apply_badge('b3', WIDTH // 2, 200, 0.1, dur, 3)
                    elif s_idx == 4:
                        apply_badge('b4', 220, 630, 0.15, dur, 4)
                    elif s_idx == 5:
                        apply_badge('b5', WIDTH // 2, 1720, 0.2, dur, 5)
                    elif s_idx == 6:
                        apply_badge('b6', WIDTH // 2, 220, 0.1, dur, 6)
                    elif s_idx == 7:
                        apply_badge('b7_1', WIDTH // 2, 170, 0.1, dur, '7_1')
                        apply_badge('b7_2', WIDTH // 2, 310, 2.5, dur, '7_2')
                    elif s_idx == 8:
                        apply_badge('b8', WIDTH // 2, 220, 0.1, dur, 8)
                    elif s_idx == 9:
                        apply_badge('b9_1', WIDTH // 2, 220, 0.1, dur, '9_1')
                        apply_badge('b9_2', WIDTH // 2, 1720, 2.5, dur, '9_2')
                    elif s_idx == 10:
                        apply_badge('b10_1', 820, 1020, 0.1, dur, '10_1')
                        apply_badge('b10_2', 820, 1160, 2.0, dur, '10_2')
                    elif s_idx == 11:
                        apply_badge('b11', WIDTH // 2, 200, 0.1, dur, 11)
                    elif s_idx == 12:
                        apply_badge('b12', WIDTH // 2, 220, 0.1, dur, 12)
                    elif s_idx == 13:
                        apply_badge('b13', WIDTH // 2, 220, 0.1, dur, 13)
                    elif s_idx == 14:
                        apply_badge('b14_1', WIDTH // 2, 220, 0.1, dur, '14_1')
                        apply_badge('b14_2', WIDTH // 2, 1720, 1.2, dur, '14_2')
                    elif s_idx == 15 and t_sec >= 1.0:
                        apply_badge('b15', WIDTH // 2, 1720, 1.0, dur, 15)

                    proc.stdin.write(frame.tobytes())
                    rendered_frames += 1
                    
                    if rendered_frames % 25 == 0 or rendered_frames == total_frames:
                        pct = (rendered_frames / total_frames) * 100
                        self.progress_bar['value'] = pct
                        self.lbl_status.config(text=f"Rendering: {pct:.1f}% ({rendered_frames}/{total_frames} frames)")
            
            proc.stdin.close()
            proc.wait()
            self.log("Video frames rendered successfully!")

            # Master Narration Audio
            self.log("Muxing narration audio...")
            total_audio_len = int(sum(audio_durations) * SAMPLE_RATE) + SAMPLE_RATE
            full_audio = np.zeros(total_audio_len, dtype=np.float32)
            cur_pos = 0
            for samples in audio_samples_list:
                full_audio[cur_pos:cur_pos + len(samples)] += samples
                cur_pos += len(samples)

            max_amp = np.max(np.abs(full_audio))
            if max_amp > 0.95:
                full_audio = (full_audio / max_amp) * 0.95
                
            int_audio = (full_audio * 32767).astype(np.int16)
            with wave.open(temp_aud, 'wb') as w:
                w.setnchannels(1)
                w.setframerate(SAMPLE_RATE)
                w.setsampwidth(2)
                w.writeframes(int_audio.tobytes())
                
            self.log(f"Finalizing MP4 Video -> {out_video}")
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
            self.lbl_status.config(text=f"Done! Video generated in {elapsed_total:.1f}s")
            self.log("==================================================")
            self.log(f"🎉 VIDEO COMPLETED SUCCESSFULLY IN {elapsed_total:.1f}s!")
            self.log(f"File Saved: {out_video}")
            self.log("==================================================")

            # Auto load into built-in player
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
