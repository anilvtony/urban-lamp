"""
Auto Video Generator with 25 Shuffled Cinematic Typography Animations
----------------------------------------------------------------------
"""

import os
import sys
import math
import subprocess
import json
import wave
import time
import random
import numpy as np
from PIL import Image
import cv2

from animations_engine import ANIMATION_STYLES_LIST, render_badge_advanced, stamp_badge_final

ENABLE_CINEMATIC_TEXT_ANIMATIONS = True

WIDTH = 1080
HEIGHT = 1920
FPS = 30
SAMPLE_RATE = 44100

WORKSPACE = r"c:\Users\aanil\Documents\Auto_Video_Editing"
BADGE_DIR = os.path.join(WORKSPACE, "rendered_badges")
PROJECT_ROOT = r"C:\Users\aanil\Documents\Anxious Anil\Shorts Videos\Projects\Fasting Series\ఆకలి వేసిన వెంటనే మన Body నిజంగా Fatని Burn చేస్తుందా_"
IMG_DIR = os.path.join(PROJECT_ROOT, "Images")
AUD_DIR = os.path.join(PROJECT_ROOT, "Audio")

OUTPUT_VIDEO = os.path.join(WORKSPACE, "Fasting_Short_25_Animations.mp4")
TEMP_VIDEO = os.path.join(WORKSPACE, "temp_render_25.mp4")
TEMP_AUDIO = os.path.join(WORKSPACE, "temp_audio_25.wav")

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

def print_progress(current, total, start_time):
    percent = float(current) / total
    filled = int(round(30 * percent))
    bar = '█' * filled + '░' * (30 - filled)
    elapsed = time.time() - start_time
    fps_render = current / elapsed if elapsed > 0 else 0
    rem = (total - current) / fps_render if fps_render > 0 else 0
    m, s = divmod(int(rem), 60)
    print(f"\rRendering Video (25 Shuffled Styles): [{bar}] {percent*100:5.1f}% ({current}/{total}) | {fps_render:4.1f} fps | ETA: {m:02d}:{s:02d}", end='', flush=True)

def main():
    print("==================================================================")
    print(" 25 CINEMATIC TYPOGRAPHY ANIMATIONS SHUFFLE RENDER ")
    print("==================================================================")
    t_start = time.time()

    # 1. Load scene images and audio
    print("1. Loading scene assets...")
    base_images = []
    audio_durations = []
    audio_samples_list = []
    
    for i in range(1, 16):
        img_p = os.path.join(IMG_DIR, f"Image_{i:03d}.png")
        aud_p = os.path.join(AUD_DIR, f"Audio_{i:03d}.wav")
        im = read_image_utf8(img_p)
        im_res = cv2.resize(im, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
        base_images.append(im_res)
        dur = get_audio_duration(aud_p)
        audio_durations.append(dur)
        samples = load_audio_samples(aud_p)
        audio_samples_list.append(samples)

    total_duration = sum(audio_durations)
    scene_frames = [int(dur * FPS) for dur in audio_durations]
    total_frames = sum(scene_frames)
    print(f"Total video duration: {total_duration:.2f}s ({total_frames} frames across 15 scenes)")

    # 2. Load all high-fidelity badges
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

    # 3. 25-Style Shuffled Allocation for YouTube Uniqueness
    # Shuffles across the 25 distinct animation algorithms
    shuffled_styles = random.sample(ANIMATION_STYLES_LIST, len(ANIMATION_STYLES_LIST))
    print(f"2. Randomly selected unique animation pool: {shuffled_styles[:8]}...")

    # Assign each scene element a distinct animation from the 25 styles
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

    # 4. Transitions
    TRANS_FRAMES = 8
    motions = [
        'zoom_in', 'zoom_in', 'pan_right', 'zoom_in', 'pan_left', 
        'zoom_in', 'pan_right', 'zoom_in', 'zoom_in', 'pan_right', 
        'zoom_in', 'pan_up', 'zoom_in', 'zoom_out', 'zoom_out'
    ]

    # 5. FFmpeg Video Pipe
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
        TEMP_VIDEO
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    rendered_frames = 0
    render_start = time.time()
    
    print("3. Rendering frames with dynamic 25-style typography motion & transitions...")

    for i in range(15):
        s_idx = i + 1
        n_frames = scene_frames[i]
        dur = audio_durations[i]
        cur_img = base_images[i]
        next_img = base_images[i + 1] if i + 1 < 15 else None
        motion = motions[i]

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

            # Apply Dynamic 25-Style Animation to Badge Overlays
            def apply_badge(bid, x, y, t_in, t_out, style_key):
                bgr, alpha = badges[bid]
                draw_bgr, draw_alpha, dx, dy, op = render_badge_advanced(
                    bgr, alpha, t_sec, t_in, t_out, scene_anims[style_key], ENABLE_CINEMATIC_TEXT_ANIMATIONS
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
                print_progress(rendered_frames, total_frames, render_start)

    proc.stdin.close()
    proc.wait()
    print("\n\nVideo frames rendered successfully!")

    # 6. Master Narration Audio
    print("Muxing master clean narration audio...")
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
    with wave.open(TEMP_AUDIO, 'wb') as w:
        w.setnchannels(1)
        w.setframerate(SAMPLE_RATE)
        w.setsampwidth(2)
        w.writeframes(int_audio.tobytes())

    # 7. Final MP4 Mux
    print("Generating cinematic MP4 video...")
    mux_cmd = [
        'ffmpeg', '-y',
        '-i', TEMP_VIDEO,
        '-i', TEMP_AUDIO,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        OUTPUT_VIDEO
    ]
    subprocess.run(mux_cmd, check=True)

    if os.path.exists(TEMP_VIDEO): os.remove(TEMP_VIDEO)
    if os.path.exists(TEMP_AUDIO): os.remove(TEMP_AUDIO)
        
    total_time = time.time() - t_start
    print("==================================================================")
    print(f"🎉 25-STYLE SHUFFLED VIDEO READY IN {total_time:.1f}s!")
    print(f"File: {OUTPUT_VIDEO}")
    print("==================================================================")

if __name__ == '__main__':
    main()
