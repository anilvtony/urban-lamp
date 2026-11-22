"""
Render Engine: Single Consistent Animation Style Per Video with Automatic Video-to-Video Shuffle/Cycle.
Dynamically detects the latest project folder in 'Fasting Series' containing Images and Audio.
"""

import os
import sys
import json
import wave
import subprocess
import cv2
import numpy as np
from PIL import Image

from animations_engine import ANIMATION_STYLES_LIST, render_badge_advanced, stamp_badge_final

WIDTH = 1920
HEIGHT = 1080
FPS = 30
SAMPLE_RATE = 44100
WORKSPACE = r"c:\Users\aanil\Documents\Auto_Video_Editing"
BADGE_DIR = os.path.join(WORKSPACE, "rendered_badges")
SERIES_ROOT = r"C:\Users\aanil\Documents\Anxious Anil\Long Format Videos\Projects\Fasting Series"
STATE_FILE = os.path.join(WORKSPACE, "animation_cycle_state.json")
POSITIONS_FILE = os.path.join(WORKSPACE, "manual_badge_positions.json")

def load_manual_positions():
    default_positions = {}
    for i in range(1, 35):
        default_positions[str(i)] = {"x": 960, "y": 120, "scale": 1.0}
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, "r") as f:
                saved = json.load(f)
                for k, v in saved.items():
                    if isinstance(v, int):
                        default_positions[k] = {"x": 960, "y": v, "scale": 1.0}
                    elif isinstance(v, dict):
                        default_positions[k] = {
                            "x": v.get("x", 960),
                            "y": v.get("y", 120),
                            "scale": v.get("scale", 1.0)
                        }
        except Exception:
            pass
    return default_positions

def get_latest_project_folder(root_dir):
    subdirs = [os.path.join(root_dir, d) for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
    valid_subdirs = [
        d for d in subdirs 
        if os.path.isdir(os.path.join(d, "Images")) and os.path.isdir(os.path.join(d, "Audio"))
    ]
    if not valid_subdirs:
        raise RuntimeError("No valid project directories found with Images and Audio subfolders.")
    latest = max(valid_subdirs, key=os.path.getmtime)
    return latest

def get_next_video_animation_style():
    state = {"last_index": -1}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except Exception:
            state = {"last_index": -1}
    
    next_idx = (state.get("last_index", -1) + 1) % len(ANIMATION_STYLES_LIST)
    chosen_style = ANIMATION_STYLES_LIST[next_idx]
    
    state["last_index"] = next_idx
    state["last_style"] = chosen_style
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
        
    return chosen_style, next_idx

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

def main():
    latest_proj = get_latest_project_folder(SERIES_ROOT)
    proj_name = os.path.basename(latest_proj)
    img_dir = os.path.join(latest_proj, "Images")
    aud_dir = os.path.join(latest_proj, "Audio")
    
    chosen_style, style_idx = get_next_video_animation_style()
    print("=" * 65)
    print(f"Project Folder Detected : {latest_proj}")
    print(f"Total Animation Styles Available : {len(ANIMATION_STYLES_LIST)}")
    print(f"Current Video Selected Style     : [{style_idx + 1}/25] -> '{chosen_style}'")
    print(f"Style Uniformity                 : ONE single style applied to ALL 14 scenes")
    print("=" * 65)

    img_files = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    aud_files = sorted([f for f in os.listdir(aud_dir) if f.lower().endswith('.wav')])
    num_scenes = min(len(img_files), len(aud_files))
    
    print(f"Discovered {len(img_files)} images and {len(aud_files)} audio files. Rendering {num_scenes} scenes.")
    
    # Pre-load audio durations
    durations = []
    total_duration = 0.0
    for i in range(num_scenes):
        dur = get_audio_duration(os.path.join(aud_dir, aud_files[i]))
        durations.append(dur)
        total_duration += dur
    
    print(f"Total Video Runtime: {total_duration:.2f} seconds ({int(total_duration * FPS)} frames)")
    
    pos = load_manual_positions()
    # Configure scenes and badges positioned dynamically
    scenes_cfg = []
    for s_idx in range(num_scenes):
        sc_num = str(s_idx + 1)
        bcfg = pos.get(sc_num, {"x": WIDTH // 2, "y": 120, "scale": 1.0})
        bname = f"p2_b{sc_num}.png"
        if not os.path.exists(os.path.join(BADGE_DIR, bname)) and os.path.exists(os.path.join(BADGE_DIR, f"b{sc_num}.png")):
            bname = f"b{sc_num}.png"
        
        if f"{sc_num}_1" in pos and f"{sc_num}_2" in pos:
            cfg_1 = pos.get(f"{sc_num}_1", {"x": WIDTH // 2, "y": 110, "scale": 1.0})
            cfg_2 = pos.get(f"{sc_num}_2", {"x": WIDTH // 2, "y": 250, "scale": 1.0})
            scenes_cfg.append({"badges": [
                (f"p2_b{sc_num}_1.png", cfg_1, 0.2, 0.25),
                (f"p2_b{sc_num}_2.png", cfg_2, 1.2, 0.25)
            ]})
        else:
            scenes_cfg.append({"badges": [(bname, bcfg, 0.2, 0.25)]})

    out_mp4 = os.path.join(WORKSPACE, f"Fasting_Series_{style_idx+1}_{chosen_style}.mp4")
    temp_video = os.path.join(WORKSPACE, "temp_video_stream.mp4")
    temp_wav = os.path.join(WORKSPACE, "temp_audio_stream.wav")
    
    # Pre-render audio concatenation
    print("Concatenating audio samples...")
    full_audio_samples = []
    for i in range(num_scenes):
        a_path = os.path.join(aud_dir, aud_files[i])
        samples = load_audio_samples(a_path)
        full_audio_samples.append(samples)
    
    full_audio = np.concatenate(full_audio_samples, axis=0)
    with wave.open(temp_wav, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(full_audio.tobytes())
    print(f"Master audio track generated: {len(full_audio) / SAMPLE_RATE:.2f}s")
    
    # Start Video Encoding Pipeline via FFmpeg sub-process for highest efficiency
    cmd_ffmpeg = [
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
        temp_video
    ]
    pipe = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE)
    
    global_frame = 0
    total_frames = int(total_duration * FPS)
    
    for s_idx in range(num_scenes):
        dur = durations[s_idx]
        scene_frames = int(dur * FPS)
        img_p = os.path.join(img_dir, img_files[s_idx])
        base_bgr = read_image_utf8(img_p)
        orig_h, orig_w = base_bgr.shape[:2]
        
        # Scale image to 1080x1920
        scale = max(WIDTH / orig_w, HEIGHT / orig_h)
        nw, nh = int(orig_w * scale), int(orig_h * scale)
        scaled_base = cv2.resize(base_bgr, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
        
        x_off = (nw - WIDTH) // 2
        y_off = (nh - HEIGHT) // 2
        cropped_base = scaled_base[y_off:y_off+HEIGHT, x_off:x_off+WIDTH]
        
        # Load badge RGBA images for this scene
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
                
                b_bgr = b_rgba[:, :, :3]
                b_alpha = (b_rgba[:, :, 3].astype(np.float32) / 255.0)
                loaded_badges.append({
                    "bgr": b_bgr,
                    "alpha": b_alpha,
                    "target_x": bcfg.get("x", 540),
                    "target_y": bcfg.get("y", 90),
                    "t_start": ent_delay,
                    "t_end": max(dur - ex_lead, ent_delay + 0.5),
                    "style": chosen_style
                })
        
        # Render scene frames
        for f in range(scene_frames):
            t_sec = f / FPS
            zoom = 1.0 + 0.05 * (f / max(1, scene_frames)) # Gentle Ken Burns zoom
            cw = int(WIDTH / zoom)
            ch = int(HEIGHT / zoom)
            cx, cy = WIDTH // 2, HEIGHT // 2
            x1 = max(0, cx - cw // 2)
            y1 = max(0, cy - ch // 2)
            frame_crop = cropped_base[y1:y1+ch, x1:x1+cw]
            frame_bgr = cv2.resize(frame_crop, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)
            
            # Composite badge(s) with single uniform animation style
            for b in loaded_badges:
                b_bgr = b["bgr"]
                b_alpha = b["alpha"]
                target_x = b["target_x"]
                target_y = b["target_y"]
                t_start = b["t_start"]
                t_end = b["t_end"]
                
                if t_sec < t_start or t_sec > t_end + 0.3:
                    continue
                
                # Render using unified 25-style kinetic engine
                draw_bgr, draw_alpha, dx, dy, opacity = render_badge_advanced(
                    b_bgr, b_alpha, t_sec, t_start, t_end,
                    anim_style=chosen_style, enable_anim=True,
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
            if global_frame % 90 == 0:
                print(f"Render progress: {global_frame}/{total_frames} frames ({(global_frame/total_frames)*100:.1f}%)")
    
    pipe.stdin.close()
    pipe.wait()
    print("Video track rendering complete!")
    
    # Merge audio + video track
    print(f"Muxing video with master audio to {out_mp4}...")
    cmd_mux = [
        'ffmpeg', '-y',
        '-i', temp_video,
        '-i', temp_wav,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        out_mp4
    ]
    subprocess.run(cmd_mux, check=True)
    
    # Clean up temporary streams
    if os.path.exists(temp_video): os.remove(temp_video)
    if os.path.exists(temp_wav): os.remove(temp_wav)
    
    print("=" * 65)
    print(f"SUCCESS! Rendered Video: {out_mp4}")
    print(f"Animation Style used for all scenes: '{chosen_style}'")
    print(f"Next video render will automatically cycle to: '{ANIMATION_STYLES_LIST[(style_idx + 1) % len(ANIMATION_STYLES_LIST)]}'")
    print("=" * 65)

if __name__ == "__main__":
    main()
