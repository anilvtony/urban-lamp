"""
Auto Video Creator Studio - Desktop Application
------------------------------------------------
A complete GUI application for generating Shorts & Reels without AI or internet.
Allows you to:
1. Select the Images folder (Image_001.png ... Image_NNN.png)
2. Select the Audio folder (Audio_001.wav ... Audio_NNN.wav)
3. Select Editing_Directions.txt
4. Select transcribe.txt
5. Select output destination MP4 file
6. Toggle Cinematic Typography Animations ON / OFF
7. Validate that image count == audio count
8. Render with a live progress bar and log stream
9. Open video directly upon completion
"""

import os
import sys
import re
import math
import subprocess
import json
import wave
import time
import threading
import numpy as np
from PIL import Image
import cv2

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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

def stamp_badge_cinematic(frame, bgr, alpha, x_center, y_center, 
                           t_sec, t_start, t_end, 
                           anim_style="elastic_pop",
                           enable_anim=True):
    if bgr is None or alpha is None:
        return
    if t_sec < t_start or t_sec > t_end:
        return
        
    duration = t_end - t_start
    elapsed = t_sec - t_start
    rem_time = t_end - t_sec
    
    if not enable_anim:
        scale, opacity, dx, dy = 1.0, 1.0, 0.0, 0.0
        draw_bgr, draw_alpha = bgr.copy(), alpha.copy()
    else:
        ENTRANCE_DUR = min(0.55, duration * 0.25)
        EXIT_DUR = min(0.38, duration * 0.20)
        scale = 1.0
        opacity = 1.0
        dx = 0.0
        dy = 0.0
        draw_bgr = bgr.copy()
        draw_alpha = alpha.copy()
        bh, bw = bgr.shape[:2]
        
        # Entrance
        if elapsed < ENTRANCE_DUR:
            ep = elapsed / ENTRANCE_DUR
            if anim_style == "falling_letters":
                t = ep
                elastic = math.sin(-13.0 * (t + 1.0) * math.pi * 0.5) * math.pow(2.0, -10.0 * t) + 1.0
                dy = -60.0 * (1.0 - ep)
                scale = 0.85 + 0.15 * elastic
                opacity = min(1.0, ep * 2.2)
            elif anim_style == "slam_down":
                overshoot = 1.0 + 0.40 * math.exp(-6.0 * ep) * math.cos(math.pi * 2.5 * ep)
                scale = overshoot
                opacity = min(1.0, ep * 3.0)
            elif anim_style == "wave_unfold":
                mask_w = int(bw * min(1.0, ep * 1.2))
                if mask_w < bw:
                    draw_alpha[:, mask_w:] = 0.0
                scale = 0.95 + 0.05 * ep
                opacity = min(1.0, ep * 2.0)
            elif anim_style == "slide_left_overshoot":
                ease = 1.0 - math.pow(1.0 - ep, 3)
                dx = 80.0 * (1.0 - ease)
                scale = 0.92 + 0.08 * ease
                opacity = min(1.0, ep * 2.5)
            else:
                t = ep
                elastic = math.sin(-13.0 * (t + 1.0) * math.pi * 0.5) * math.pow(2.0, -10.0 * t) + 1.0
                scale = max(0.01, elastic)
                opacity = min(1.0, ep * 2.5)
        # Exit
        elif rem_time < EXIT_DUR:
            xp = (EXIT_DUR - rem_time) / EXIT_DUR
            if anim_style == "falling_letters":
                dy = 45.0 * (xp * xp)
                opacity = max(0.0, 1.0 - xp)
            elif anim_style == "wave_unfold":
                mask_start = int(bw * xp)
                draw_alpha[:, :mask_start] = 0.0
                opacity = max(0.0, 1.0 - xp * 0.8)
            elif anim_style == "slam_down":
                scale = 1.0 + 0.15 * xp
                opacity = max(0.0, 1.0 - xp)
            else:
                dy = -35.0 * xp
                opacity = max(0.0, 1.0 - xp)
        # Continuous Floating
        else:
            mid_t = elapsed - ENTRANCE_DUR
            dy = math.sin(mid_t * 2.8) * 3.5
            scale = 1.0 + math.sin(mid_t * 2.0) * 0.012
            sweep_cycle = (mid_t % 2.4) / 2.4
            if sweep_cycle < 0.65:
                sweep_prog = sweep_cycle / 0.65
                cx = int(-80 + sweep_prog * (bw + 160))
                band_w = 55
                xs = np.arange(bw)
                dist = np.abs(xs - cx)
                intensity = np.clip(1.0 - dist / band_w, 0, 1) ** 2 * 0.28
                shimmer_mask = intensity[np.newaxis, :, np.newaxis]
                draw_bgr = np.clip(draw_bgr.astype(np.float32) + 255.0 * shimmer_mask, 0, 255).astype(np.uint8)

    bh, bw = draw_bgr.shape[:2]
    if scale != 1.0:
        new_w = max(1, int(bw * scale))
        new_h = max(1, int(bh * scale))
        draw_bgr = cv2.resize(draw_bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        draw_alpha = cv2.resize(draw_alpha, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        bh, bw = new_h, new_w

    actual_x = x_center + dx
    actual_y = y_center + dy
    x0 = int(actual_x - bw // 2)
    x1 = x0 + bw
    y0 = int(actual_y - bh // 2)
    y1 = y0 + bh

    if x0 < 0:
        draw_bgr = draw_bgr[:, -x0:]
        draw_alpha = draw_alpha[:, -x0:]
        x0 = 0
    if x1 > WIDTH:
        draw_bgr = draw_bgr[:, :WIDTH - x0]
        draw_alpha = draw_alpha[:, :WIDTH - x0]
        x1 = WIDTH
    if y0 < 0:
        draw_bgr = draw_bgr[-y0:, :]
        draw_alpha = draw_alpha[-y0:, :]
        y0 = 0
    if y1 > HEIGHT:
        draw_bgr = draw_bgr[:HEIGHT - y0, :]
        draw_alpha = draw_alpha[:HEIGHT - y0, :]
        y1 = HEIGHT

    if x1 <= x0 or y1 <= y0:
        return

    eff_alpha = (draw_alpha * opacity)[:, :, np.newaxis]
    target = frame[y0:y1, x0:x1]
    frame[y0:y1, x0:x1] = (target * (1.0 - eff_alpha) + draw_bgr * eff_alpha).astype(np.uint8)

def transform_frame(img, zoom=1.0, pan_x=0.0, pan_y=0.0):
    h, w = img.shape[:2]
    center_x = w / 2.0 + pan_x * w * 0.1
    center_y = h / 2.0 + pan_y * h * 0.1
    M = cv2.getRotationMatrix2D((center_x, center_y), 0, zoom)
    M[0, 2] += (w / 2.0 - center_x)
    M[1, 2] += (h / 2.0 - center_y)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

class AutoVideoEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto Video Creator Studio - 1080p Shorts & Reels")
        self.geometry("820x720")
        self.minsize(780, 680)
        self.configure(bg="#0F172A")
        
        # Style
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("TLabel", background="#0F172A", foreground="#F8FAFC", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#F59E0B")
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#1E293B", foreground="#F8FAFC", borderwidth=1)
        self.style.map("TButton", background=[("active", "#334155")])
        self.style.configure("Action.TButton", font=("Segoe UI", 12, "bold"), background="#F59E0B", foreground="#0F172A")
        self.style.map("Action.TButton", background=[("active", "#D97706")])
        self.style.configure("TEntry", fieldbackground="#1E293B", foreground="#F8FAFC", insertcolor="#F8FAFC")
        self.style.configure("TCheckbutton", background="#0F172A", foreground="#F8FAFC", font=("Segoe UI", 10))

        # Default Paths
        default_proj = r"C:\Users\aanil\Documents\Anxious Anil\Shorts Videos\Projects\Fasting Series\ఆకలి వేసిన వెంటనే మన Body నిజంగా Fatని Burn చేస్తుందా_"
        self.img_dir_var = tk.StringVar(value=os.path.join(default_proj, "Images"))
        self.aud_dir_var = tk.StringVar(value=os.path.join(default_proj, "Audio"))
        self.edit_dir_var = tk.StringVar(value=os.path.join(WORKSPACE, "Editing_Directions.txt"))
        self.trans_var = tk.StringVar(value=os.path.join(WORKSPACE, "transcribe.txt"))
        self.out_video_var = tk.StringVar(value=os.path.join(WORKSPACE, "Fasting_Short_Master_Perfect.mp4"))
        self.cinematic_anim_var = tk.BooleanVar(value=True)
        
        self.is_rendering = False
        self.create_widgets()
        
    def create_widgets(self):
        # Header
        header_frame = tk.Frame(self, bg="#0F172A")
        header_frame.pack(fill=tk.X, padx=25, pady=(20, 10))
        
        lbl_title = ttk.Label(header_frame, text="🎬 Auto Video Creator Studio (Offline & AI-Free)", style="Header.TLabel")
        lbl_title.pack(anchor=tk.W)
        lbl_sub = ttk.Label(header_frame, text="Select your project folders & directions. Verifies image & audio counts automatically.")
        lbl_sub.pack(anchor=tk.W, pady=(4, 0))
        
        # Form Container
        form_frame = tk.LabelFrame(self, text=" Project Assets Configuration ", bg="#1E293B", fg="#F59E0B", font=("Segoe UI", 11, "bold"), padx=15, pady=15)
        form_frame.pack(fill=tk.X, padx=25, pady=10)
        
        # 1. Images Folder
        self.add_browse_row(form_frame, "📁 Images Folder:", self.img_dir_var, self.browse_img_dir, 0)
        # 2. Audio Folder
        self.add_browse_row(form_frame, "🎵 Audio Folder:", self.aud_dir_var, self.browse_aud_dir, 1)
        # 3. Editing Directions
        self.add_browse_row(form_frame, "📝 Editing Directions (.txt):", self.edit_dir_var, self.browse_edit_file, 2)
        # 4. Transcribe File
        self.add_browse_row(form_frame, "🎙️ Transcribe Script (.txt):", self.trans_var, self.browse_trans_file, 3)
        # 5. Output Video
        self.add_browse_row(form_frame, "💾 Output Video (.mp4):", self.out_video_var, self.browse_out_video, 4)
        
        # Feature Options
        opt_frame = tk.Frame(self, bg="#0F172A")
        opt_frame.pack(fill=tk.X, padx=25, pady=5)
        chk_cinematic = ttk.Checkbutton(opt_frame, text="✨ Enable Cinematic Typography Animations (Falling letters, Wave reveal, Shimmer)", variable=self.cinematic_anim_var)
        chk_cinematic.pack(side=tk.LEFT)
        
        # Render Button & Progress
        act_frame = tk.Frame(self, bg="#0F172A")
        act_frame.pack(fill=tk.X, padx=25, pady=10)
        
        self.btn_render = tk.Button(act_frame, text="🚀 START VIDEO RENDER", bg="#F59E0B", fg="#0F172A", font=("Segoe UI", 12, "bold"), relief=tk.FLAT, padx=20, pady=10, command=self.start_render_thread)
        self.btn_render.pack(fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=25, pady=(5, 5))
        
        self.lbl_status = ttk.Label(self, text="Ready. Set folders and click Start Video Render.")
        self.lbl_status.pack(anchor=tk.W, padx=25, pady=(0, 5))
        
        # Log Console
        log_frame = tk.LabelFrame(self, text=" Build Console & Logs ", bg="#1E293B", fg="#94A3B8", font=("Segoe UI", 10), padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 20))
        
        self.txt_log = tk.Text(log_frame, bg="#0F172A", fg="#38BDF8", insertbackground="white", font=("Consolas", 9), relief=tk.FLAT)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.txt_log.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log['yscrollcommand'] = scroll.set

    def add_browse_row(self, parent, label_text, str_var, browse_cmd, row_idx):
        lbl = tk.Label(parent, text=label_text, bg="#1E293B", fg="#E2E8F0", font=("Segoe UI", 10))
        lbl.grid(row=row_idx, column=0, sticky=tk.W, pady=6)
        entry = tk.Entry(parent, textvariable=str_var, bg="#0F172A", fg="#F8FAFC", insertbackground="white", font=("Segoe UI", 10), relief=tk.FLAT, width=54)
        entry.grid(row=row_idx, column=1, padx=8, pady=6, sticky=tk.EW)
        btn = tk.Button(parent, text="Browse...", bg="#334155", fg="#F8FAFC", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, command=browse_cmd)
        btn.grid(row=row_idx, column=2, pady=6)
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

    def start_render_thread(self):
        if self.is_rendering:
            return
        
        # Validation
        img_dir = self.img_dir_var.get()
        aud_dir = self.aud_dir_var.get()
        out_vid = self.out_video_var.get()
        
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
            
        # Count check
        if len(img_files) != len(aud_files):
            msg = f"Count mismatch!\n\nImages found: {len(img_files)}\nAudio files found: {len(aud_files)}\n\nPlease ensure you have the exact same count of images and audio files."
            messagebox.showerror("Count Mismatch Error", msg)
            return

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
            enable_anim = self.cinematic_anim_var.get()
            
            temp_vid = os.path.join(WORKSPACE, "temp_gui_video.mp4")
            temp_aud = os.path.join(WORKSPACE, "temp_gui_audio.wav")
            
            num_scenes = len(img_files)
            self.log(f"Starting Video Generation for {num_scenes} scenes...")
            self.log(f"Images: {img_dir}")
            self.log(f"Audio: {aud_dir}")
            self.log(f"Cinematic Animations: {'ENABLED' if enable_anim else 'DISABLED'}")
            
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
            
            self.log(f"Total Video Duration: {total_dur:.2f} seconds ({total_frames} frames)")
            
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

                    # Dynamic Badges per scene
                    if s_idx == 1:
                        stamp_badge_cinematic(frame, *badges['b1'], WIDTH // 2, 220, t_sec, 0.2, dur, "falling_letters", enable_anim)
                    elif s_idx == 2:
                        stamp_badge_cinematic(frame, *badges['b2'], WIDTH // 2, 220, t_sec, 0.1, dur, "elastic_pop", enable_anim)
                    elif s_idx == 3:
                        stamp_badge_cinematic(frame, *badges['b3'], WIDTH // 2, 200, t_sec, 0.1, dur, "wave_unfold", enable_anim)
                    elif s_idx == 4:
                        stamp_badge_cinematic(frame, *badges['b4'], 220, 630, t_sec, 0.15, dur, "slam_down", enable_anim)
                    elif s_idx == 5:
                        stamp_badge_cinematic(frame, *badges['b5'], WIDTH // 2, 1720, t_sec, 0.2, dur, "slide_left_overshoot", enable_anim)
                    elif s_idx == 6:
                        stamp_badge_cinematic(frame, *badges['b6'], WIDTH // 2, 220, t_sec, 0.1, dur, "wave_unfold", enable_anim)
                    elif s_idx == 7:
                        stamp_badge_cinematic(frame, *badges['b7_1'], WIDTH // 2, 170, t_sec, 0.1, dur, "falling_letters", enable_anim)
                        stamp_badge_cinematic(frame, *badges['b7_2'], WIDTH // 2, 310, t_sec, 2.5, dur, "elastic_pop", enable_anim)
                    elif s_idx == 8:
                        stamp_badge_cinematic(frame, *badges['b8'], WIDTH // 2, 220, t_sec, 0.1, dur, "falling_letters", enable_anim)
                    elif s_idx == 9:
                        stamp_badge_cinematic(frame, *badges['b9_1'], WIDTH // 2, 220, t_sec, 0.1, dur, "wave_unfold", enable_anim)
                        stamp_badge_cinematic(frame, *badges['b9_2'], WIDTH // 2, 1720, t_sec, 2.5, dur, "slam_down", enable_anim)
                    elif s_idx == 10:
                        stamp_badge_cinematic(frame, *badges['b10_1'], 820, 1020, t_sec, 0.1, dur, "falling_letters", enable_anim)
                        stamp_badge_cinematic(frame, *badges['b10_2'], 820, 1160, t_sec, 2.0, dur, "elastic_pop", enable_anim)
                    elif s_idx == 11:
                        stamp_badge_cinematic(frame, *badges['b11'], WIDTH // 2, 200, t_sec, 0.1, dur, "elastic_pop", enable_anim)
                    elif s_idx == 12:
                        stamp_badge_cinematic(frame, *badges['b12'], WIDTH // 2, 220, t_sec, 0.1, dur, "slam_down", enable_anim)
                    elif s_idx == 13:
                        stamp_badge_cinematic(frame, *badges['b13'], WIDTH // 2, 220, t_sec, 0.1, dur, "wave_unfold", enable_anim)
                    elif s_idx == 14:
                        stamp_badge_cinematic(frame, *badges['b14_1'], WIDTH // 2, 220, t_sec, 0.1, dur, "slam_down", enable_anim)
                        stamp_badge_cinematic(frame, *badges['b14_2'], WIDTH // 2, 1720, t_sec, 1.2, dur, "elastic_pop", enable_anim)
                    elif s_idx == 15 and t_sec >= 1.0:
                        stamp_badge_cinematic(frame, *badges['b15'], WIDTH // 2, 1720, t_sec, 1.0, dur, "elastic_pop", enable_anim)

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
            self.log("Muxing original narration track...")
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
            
            # Ask to open file
            if messagebox.askyesno("Success", f"Video render complete in {elapsed_total:.1f}s!\n\nWould you like to open the video now?"):
                os.startfile(out_video)

        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            messagebox.showerror("Render Error", str(e))
        finally:
            self.is_rendering = False
            self.btn_render.config(state=tk.NORMAL, text="🚀 START VIDEO RENDER")

if __name__ == '__main__':
    app = AutoVideoEditorApp()
    app.mainloop()
