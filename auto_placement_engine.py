import os
import numpy as np
from PIL import Image

def find_clean_cream_y(img_np, badge_w=800, badge_h=110, prefer_top=True):
    """
    Scans a 1080x1920 image to find a pure background cream/white horizontal space
    where zero artwork, zero text, zero black lines, and zero colored shapes exist.
    """
    h, w = img_np.shape[:2]
    x0 = max(0, (w - badge_w) // 2)
    x1 = min(w, x0 + badge_w)
    
    cream_ref = np.array([247, 243, 232])
    
    strip = img_np[:, x0:x1]
    diff = np.abs(strip.astype(int) - cream_ref).sum(axis=2)
    # Row is pure background only if maximum difference across width is tiny
    row_is_pure_bg = (diff < 35).all(axis=1)
    
    valid_intervals = []
    start = None
    for y in range(h):
        if row_is_pure_bg[y]:
            if start is None: start = y
        else:
            if start is not None:
                if y - start >= badge_h:
                    valid_intervals.append((start, y))
                start = None
    if start is not None and h - start >= badge_h:
        valid_intervals.append((start, h))
        
    if not valid_intervals:
        return 95 if prefer_top else 1600
        
    if prefer_top:
        # Check if there is space right at top (0 to 300)
        top_candidates = [iv for iv in valid_intervals if iv[0] < 250]
        if top_candidates:
            c_start, c_end = top_candidates[0]
            # Center badge safely within the clean space with margin
            return (c_start + min(c_end, c_start + badge_h + 30)) // 2
        else:
            # If top has no large space, pick bottom
            bottom_candidates = [iv for iv in valid_intervals if iv[0] >= 1400]
            if bottom_candidates:
                c_start, c_end = bottom_candidates[0]
                return (c_start + c_end) // 2
            c_start, c_end = valid_intervals[0]
            return (c_start + c_end) // 2
    else:
        bottom_candidates = [iv for iv in valid_intervals if iv[0] >= 1400]
        if bottom_candidates:
            c_start, c_end = bottom_candidates[0]
            return (c_start + c_end) // 2
        else:
            c_start, c_end = valid_intervals[0]
            return (c_start + c_end) // 2

def get_clean_placement_for_scene(img_path, scene_index, badge_count=1):
    im = Image.open(img_path).convert('RGB')
    w, h = im.size
    scale = max(1080 / w, 1920 / h)
    nw, nh = int(w * scale), int(h * scale)
    res = im.resize((nw, nh), Image.LANCZOS)
    arr = np.array(res)[(nh-1920)//2:(nh-1920)//2+1920, (nw-1080)//2:(nw-1080)//2+1080]
    
    # Check whether top has ample space or bottom is preferred
    # Scan top 0-250 for clean cream
    strip_top = arr[0:250, 200:880]
    cream_ref = np.array([247, 243, 232])
    diff_top = np.abs(strip_top.astype(int) - cream_ref).sum(axis=2)
    top_clean_rows = np.sum((diff_top < 35).all(axis=1))
    
    # If top has at least 120 clean rows, prefer top; otherwise bottom
    prefer_top = (top_clean_rows >= 120)
    
    if badge_count == 1:
        y_center = find_clean_cream_y(arr, badge_w=800, badge_h=110, prefer_top=prefer_top)
        return [y_center]
    else:
        # Two badges stacked
        y1 = find_clean_cream_y(arr, badge_w=800, badge_h=100, prefer_top=prefer_top)
        y2 = y1 + 135
        return [y1, y2]

if __name__ == "__main__":
    img_dir = r"C:\Users\aanil\Documents\Anxious Anil\Shorts Videos\Projects\Fasting Series\Fasting చేస్తే మన Bodyలో అసలు ఏం జరుగుతుంది_\Images"
    for i in range(1, 15):
        fname = f"Image_{i:03d}.png"
        p = os.path.join(img_dir, fname)
        count = 2 if i in (8, 11, 13) else 1
        coords = get_clean_placement_for_scene(p, i, count)
        print(f"Scene {i:02d} ({fname}): Auto-detected clean white/cream coordinates -> {coords}")
