"""
25 Cinematic Typography Animation Styles & Shuffle Engine
---------------------------------------------------------
Includes:
1. falling_letters          - Drops smoothly from above with soft settle
2. elastic_pop              - Bouncy 0% -> 115% -> 100% pop
3. wave_unfold              - Progressive horizontal wipe/unfold reveal
4. slam_down                - Heavy 150% -> 100% impact drop with rebound
5. slide_left_overshoot     - Rapid slide in from right with overshoot bounce
6. slide_right_overshoot    - Rapid slide in from left with overshoot bounce
7. push_up_rise             - Rises upward from bottom safe area
8. zoom_spin_in             - Spiral rotation + scale entrance
9. flip_horizontal_3d       - Y-axis simulated 3D card flip
10. flip_vertical_3d        - X-axis simulated 3D perspective fold
11. typewriter_mask         - Stepped character-like mask progression
12. kinetic_tracking        - Wide tracking collapse into position
13. particle_converge       - Soft blur-in and focus converge
14. swing_pendulum          - Top-anchored pendulum swing with damping
15. cascade_drop            - Staggered downward cascade
16. diagonal_glide          - Glides smoothly from top-left diagonal
17. flash_scale_impact      - High-energy flash with punch scale
18. rubber_band_stretch     - Horizontal stretch then snappy recoil
19. glitch_snap             - Rapid multi-frame position offset twitch
20. pop_and_float           - Quick pop followed by pronounced drifting float
21. iris_circle_reveal      - Center outward radial expansion
22. neon_glow_pulse         - Shimmering intensity pulse on entrance
23. smooth_drift_in         - Elegant cinematic documentary slow drift
24. split_curtain_reveal    - Center split opening mask
25. bounce_settle           - Triple bounce floor settle
"""

import math
import numpy as np
import cv2

ANIMATION_STYLES_LIST = [
    "falling_letters",
    "elastic_pop",
    "wave_unfold",
    "slam_down",
    "slide_left_overshoot",
    "slide_right_overshoot",
    "push_up_rise",
    "zoom_spin_in",
    "flip_horizontal_3d",
    "flip_vertical_3d",
    "typewriter_mask",
    "kinetic_tracking",
    "particle_converge",
    "swing_pendulum",
    "cascade_drop",
    "diagonal_glide",
    "flash_scale_impact",
    "rubber_band_stretch",
    "glitch_snap",
    "pop_and_float",
    "iris_circle_reveal",
    "neon_glow_pulse",
    "smooth_drift_in",
    "split_curtain_reveal",
    "bounce_settle"
]

def render_badge_advanced(bgr, alpha, t_sec, t_start, t_end, anim_style="elastic_pop", enable_anim=True, width=1080, height=1920):
    if bgr is None or alpha is None:
        return None, None, 0, 0, 1.0
    if t_sec < t_start or t_sec > t_end:
        return None, None, 0, 0, 0.0

    duration = t_end - t_start
    elapsed = t_sec - t_start
    rem_time = t_end - t_sec

    if not enable_anim:
        return bgr.copy(), alpha.copy(), 0.0, 0.0, 1.0

    ENTRANCE_DUR = min(0.60, duration * 0.28)
    EXIT_DUR = min(0.40, duration * 0.22)

    scale_x, scale_y = 1.0, 1.0
    opacity = 1.0
    dx, dy = 0.0, 0.0
    rot_angle = 0.0

    draw_bgr = bgr.copy()
    draw_alpha = alpha.copy()
    bh, bw = bgr.shape[:2]

    # --- 1. ENTRANCE STAGE ---
    if elapsed < ENTRANCE_DUR:
        ep = elapsed / ENTRANCE_DUR  # 0.0 -> 1.0

        if anim_style == "falling_letters":
            t = ep
            elastic = math.sin(-13.0 * (t + 1.0) * math.pi * 0.5) * math.pow(2.0, -10.0 * t) + 1.0
            dy = -70.0 * (1.0 - ep)
            scale_x = scale_y = 0.85 + 0.15 * elastic
            opacity = min(1.0, ep * 2.2)

        elif anim_style == "elastic_pop":
            t = ep
            elastic = math.sin(-13.0 * (t + 1.0) * math.pi * 0.5) * math.pow(2.0, -10.0 * t) + 1.0
            scale_x = scale_y = max(0.01, elastic)
            opacity = min(1.0, ep * 2.5)

        elif anim_style == "wave_unfold":
            mask_w = int(bw * min(1.0, ep * 1.25))
            if mask_w < bw:
                draw_alpha[:, mask_w:] = 0.0
            scale_x = scale_y = 0.94 + 0.06 * ep
            opacity = min(1.0, ep * 2.0)

        elif anim_style == "slam_down":
            overshoot = 1.0 + 0.45 * math.exp(-6.5 * ep) * math.cos(math.pi * 2.6 * ep)
            scale_x = scale_y = overshoot
            opacity = min(1.0, ep * 3.0)

        elif anim_style == "slide_left_overshoot":
            ease = 1.0 - math.pow(1.0 - ep, 3)
            dx = 110.0 * (1.0 - ease)
            scale_x = scale_y = 0.90 + 0.10 * ease
            opacity = min(1.0, ep * 2.5)

        elif anim_style == "slide_right_overshoot":
            ease = 1.0 - math.pow(1.0 - ep, 3)
            dx = -110.0 * (1.0 - ease)
            scale_x = scale_y = 0.90 + 0.10 * ease
            opacity = min(1.0, ep * 2.5)

        elif anim_style == "push_up_rise":
            ease = 1.0 - math.pow(1.0 - ep, 3)
            dy = 85.0 * (1.0 - ease)
            scale_x = scale_y = 0.92 + 0.08 * ease
            opacity = min(1.0, ep * 2.5)

        elif anim_style == "zoom_spin_in":
            scale_x = scale_y = math.sin(ep * math.pi * 0.5) ** 2
            rot_angle = -18.0 * (1.0 - ep)
            opacity = min(1.0, ep * 2.2)

        elif anim_style == "flip_horizontal_3d":
            scale_x = max(0.01, abs(math.cos((1.0 - ep) * math.pi * 0.5)))
            scale_y = 0.95 + 0.05 * ep
            opacity = min(1.0, ep * 2.5)

        elif anim_style == "flip_vertical_3d":
            scale_y = max(0.01, abs(math.cos((1.0 - ep) * math.pi * 0.5)))
            scale_x = 0.95 + 0.05 * ep
            opacity = min(1.0, ep * 2.5)

        elif anim_style == "typewriter_mask":
            steps = 8
            cur_step = int(ep * steps) / steps
            mask_w = int(bw * cur_step)
            draw_alpha[:, mask_w:] = 0.0
            opacity = 1.0

        elif anim_style == "kinetic_tracking":
            scale_x = 1.25 - 0.25 * ep
            scale_y = 0.90 + 0.10 * ep
            opacity = min(1.0, ep * 2.0)

        elif anim_style == "particle_converge":
            blur_k = int((1.0 - ep) * 12) * 2 + 1
            if blur_k > 1:
                draw_bgr = cv2.GaussianBlur(draw_bgr, (blur_k, blur_k), 0)
            scale_x = scale_y = 1.10 - 0.10 * ep
            opacity = min(1.0, ep * 1.8)

        elif anim_style == "swing_pendulum":
            rot_angle = 12.0 * math.exp(-4.0 * ep) * math.cos(math.pi * 3.0 * ep)
            dy = -25.0 * (1.0 - ep)
            opacity = min(1.0, ep * 2.5)

        elif anim_style == "cascade_drop":
            dy = -80.0 * ((1.0 - ep) ** 2)
            rot_angle = -4.0 * (1.0 - ep)
            opacity = min(1.0, ep * 2.2)

        elif anim_style == "diagonal_glide":
            dx = -70.0 * (1.0 - ep)
            dy = -50.0 * (1.0 - ep)
            scale_x = scale_y = 0.92 + 0.08 * ep
            opacity = min(1.0, ep * 2.2)

        elif anim_style == "flash_scale_impact":
            scale_x = scale_y = 1.35 - 0.35 * ep
            flash_intensity = math.sin(ep * math.pi) * 0.40
            draw_bgr = np.clip(draw_bgr.astype(np.float32) + 255.0 * flash_intensity, 0, 255).astype(np.uint8)
            opacity = min(1.0, ep * 3.0)

        elif anim_style == "rubber_band_stretch":
            scale_x = 1.0 + 0.35 * math.sin(ep * math.pi)
            scale_y = 1.0 - 0.20 * math.sin(ep * math.pi)
            opacity = min(1.0, ep * 2.5)

        elif anim_style == "glitch_snap":
            if ep < 0.7:
                dx = (math.sin(ep * 50.0) * 16.0) * (1.0 - ep)
                dy = (math.cos(ep * 40.0) * 8.0) * (1.0 - ep)
            opacity = min(1.0, ep * 3.0)

        elif anim_style == "pop_and_float":
            scale_x = scale_y = min(1.0, ep * 1.3)
            dy = -20.0 * math.sin(ep * math.pi * 0.5)
            opacity = min(1.0, ep * 2.0)

        elif anim_style == "iris_circle_reveal":
            mask = np.zeros((bh, bw), dtype=np.uint8)
            r = int(math.hypot(bw // 2, bh // 2) * min(1.0, ep * 1.2))
            cv2.circle(mask, (bw // 2, bh // 2), r, 255, -1)
            draw_alpha = draw_alpha * (mask.astype(np.float32) / 255.0)
            opacity = min(1.0, ep * 2.0)

        elif anim_style == "neon_glow_pulse":
            pulse = 0.30 * math.sin(ep * math.pi * 3.0)
            draw_bgr = np.clip(draw_bgr.astype(np.float32) * (1.0 + pulse), 0, 255).astype(np.uint8)
            scale_x = scale_y = 0.95 + 0.05 * ep
            opacity = min(1.0, ep * 2.5)

        elif anim_style == "smooth_drift_in":
            dy = 35.0 * (1.0 - math.sqrt(ep))
            opacity = ep

        elif anim_style == "split_curtain_reveal":
            half_w = int((bw // 2) * min(1.0, ep * 1.3))
            mask = np.zeros((bh, bw), dtype=np.uint8)
            mask[:, bw // 2 - half_w : bw // 2 + half_w] = 255
            draw_alpha = draw_alpha * (mask.astype(np.float32) / 255.0)
            opacity = min(1.0, ep * 2.0)

        else: # "bounce_settle"
            t = ep
            b_val = math.sin(t * math.pi * 3.5) * math.exp(-3.5 * t)
            dy = -45.0 * abs(b_val)
            scale_x = scale_y = 0.95 + 0.05 * ep
            opacity = min(1.0, ep * 2.5)

    # --- 2. EXIT STAGE ---
    elif rem_time < EXIT_DUR:
        xp = (EXIT_DUR - rem_time) / EXIT_DUR  # 0.0 -> 1.0
        if anim_style in ("falling_letters", "cascade_drop", "bounce_settle"):
            dy = 50.0 * (xp * xp)
            opacity = max(0.0, 1.0 - xp)
        elif anim_style in ("wave_unfold", "typewriter_mask", "split_curtain_reveal"):
            mask_start = int(bw * xp)
            draw_alpha[:, :mask_start] = 0.0
            opacity = max(0.0, 1.0 - xp * 0.8)
        elif anim_style in ("slam_down", "flash_scale_impact", "glitch_snap"):
            scale_x = scale_y = 1.0 + 0.18 * xp
            opacity = max(0.0, 1.0 - xp)
        elif anim_style in ("slide_left_overshoot", "slide_right_overshoot"):
            dx = (70.0 if "left" in anim_style else -70.0) * xp
            opacity = max(0.0, 1.0 - xp)
        else:
            dy = -38.0 * xp
            opacity = max(0.0, 1.0 - xp)

    # --- 3. CONTINUOUS MOVEMENT (While Audience Reads) ---
    else:
        mid_t = elapsed - ENTRANCE_DUR
        dy = math.sin(mid_t * 2.8) * 3.5
        scale_x = scale_y = 1.0 + math.sin(mid_t * 2.0) * 0.012

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

    # Apply Scaling
    if scale_x != 1.0 or scale_y != 1.0:
        new_w = max(1, int(bw * scale_x))
        new_h = max(1, int(bh * scale_y))
        draw_bgr = cv2.resize(draw_bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        draw_alpha = cv2.resize(draw_alpha, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        bh, bw = new_h, new_w

    # Apply Rotation if angle != 0
    if abs(rot_angle) > 0.01:
        M = cv2.getRotationMatrix2D((bw / 2.0, bh / 2.0), rot_angle, 1.0)
        draw_bgr = cv2.warpAffine(draw_bgr, M, (bw, bh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        draw_alpha = cv2.warpAffine(draw_alpha, M, (bw, bh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)

    return draw_bgr, draw_alpha, dx, dy, opacity

def stamp_badge_final(frame, draw_bgr, draw_alpha, x_center, y_center, dx, dy, opacity, width=1080, height=1920):
    if draw_bgr is None or draw_alpha is None or opacity <= 0.001:
        return
    bh, bw = draw_bgr.shape[:2]
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
    if x1 > width:
        draw_bgr = draw_bgr[:, :width - x0]
        draw_alpha = draw_alpha[:, :width - x0]
        x1 = width
    if y0 < 0:
        draw_bgr = draw_bgr[-y0:, :]
        draw_alpha = draw_alpha[-y0:, :]
        y0 = 0
    if y1 > height:
        draw_bgr = draw_bgr[:height - y0, :]
        draw_alpha = draw_alpha[:height - y0, :]
        y1 = height

    if x1 <= x0 or y1 <= y0:
        return

    eff_alpha = (draw_alpha * opacity)[:, :, np.newaxis]
    target = frame[y0:y1, x0:x1]
    frame[y0:y1, x0:x1] = (target * (1.0 - eff_alpha) + draw_bgr * eff_alpha).astype(np.uint8)
