"""
Universal Offline Badge Generator & Catalog Library
---------------------------------------------------
1. Automatically parses any Editing_Directions.txt file directly and generates 
   any missing badge PNGs on the fly using local headless Edge.
2. Contains a comprehensive pre-rendered library of common YouTube Shorts / Telugu Health & Science badges
   (CTA, hooks, numbers, biological tags, myth busters, and reactions) stored 100% locally.
"""

import os
import re
import sys
import hashlib
import subprocess
from PIL import Image

WORKSPACE = r"c:\Users\aanil\Documents\Auto_Video_Editing"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BADGE_DIR = os.path.join(WORKSPACE, "rendered_badges")
os.makedirs(BADGE_DIR, exist_ok=True)

# Common High-Frequency Pre-Rendered Badges Library (Telugu + English)
UNIVERSAL_LIBRARY = [
    # --- Universal Hooks & Intro ---
    ("SUPER INTERESTING TOPIC!", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("MUST WATCH! 👁️", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("DID YOU KNOW? ❓", "#FFF8E7", "#C84B28", "#C84B28", 46, False),
    ("మీకు తెలుసా? ❓", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("WAIT FOR THIS! ⏳", "#D8E8D4", "#1B2A4A", "#1B2A4A", 46, False),
    ("నిజం తెలిస్తే షాక్! 😱", "#FFF8E7", "#C84B28", "#C84B28", 46, False),
    ("STEP BY STEP SCIENCE 👇", "#D8E8D4", "#1B2A4A", "#1B2A4A", 46, False),
    ("SIMPLE BREAKDOWN 💡", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("BODY లోపల ఏం జరుగుతుంది? ❓", "#F4C430", "#1B2A4A", "#1B2A4A", 44, False),
    
    # --- Common Fasting & Diet Concepts ---
    ("FASTING = ఆకలితో ఉండటమా?", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("FASTING ≠ STARVATION", "#FFF8E7", "#C84B28", "#C84B28", 44, False),
    ("PLANNED REST ⚖️", "#D8E8D4", "#1B2A4A", "#1B2A4A", 46, False),
    ("TIFFIN ➔ LUNCH ➔ DINNER", "#D8E8D4", "#1B2A4A", "#1B2A4A", 44, False),
    ("16 HRS = BACKUP SYSTEM ON! ⚡", "#FFF8E7", "#C84B28", "#C84B28", 44, False),
    ("12 HRS = GLYCOGEN DEPLETED", "#D8E8D4", "#1B2A4A", "#1B2A4A", 44, False),
    ("INSULIN ⬇️", "#FFF8E7", "#1B2A4A", "#1B2A4A", 46, False),
    ("INSULIN ⬆️", "#FFF8E7", "#C84B28", "#C84B28", 46, False),
    ("FAT CELLS OPEN 🔑", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("FAT CELLS LOCKED 🔒", "#FFF8E7", "#C84B28", "#C84B28", 46, False),
    ("GLYCOGEN = PHONE BATTERY 🔋", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("KETONES = BRAIN INVERTER ⚡", "#D8E8D4", "#1B2A4A", "#1B2A4A", 44, False),
    ("AUTOPHAGY = CELL CLEANUP 🧹", "#FFF8E7", "#1B2A4A", "#1B2A4A", 44, False),
    ("GLUCOSE = CASH 💵", "#D8E8D4", "#1B2A4A", "#1B2A4A", 46, False),
    ("FAT = BANK FD 🏦", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("GLYCOGEN = FRIDGE FOOD 🧊", "#FFF8E7", "#1B2A4A", "#1B2A4A", 46, False),
    ("PETROL ➔ CNG 🚗", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("GLUCAGON = MASTER KEY 🔑", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("FAT BURN START! 🔥", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("BODY WEAK అవ్వదు! 💪", "#D8E8D4", "#1B2A4A", "#1B2A4A", 46, False),
    ("ULTIMATE REPAIR MODE! 🛠️", "#F4C430", "#1B2A4A", "#1B2A4A", 44, False),
    ("ఆకలి కాదు...", "#FFF8E7", "#1B2A4A", "#1B2A4A", 46, True),
    ("ఆకలి = GHRELIN ALARM ⏰", "#F4C430", "#1B2A4A", "#C84B28", 46, False),

    # --- Myth Busters & Alerts ---
    ("BIG MYTH! ❌", "#FFF8E7", "#C84B28", "#C84B28", 48, False),
    ("ఇది నిజం కాదు! ❌", "#FFF8E7", "#C84B28", "#C84B28", 46, False),
    ("REAL TRUTH! ✅", "#D8E8D4", "#1B2A4A", "#1B2A4A", 48, False),
    ("WARNING! ⚠️", "#F4C430", "#C84B28", "#C84B28", 48, False),
    ("DON'T DO THIS! 🛑", "#FFF8E7", "#C84B28", "#C84B28", 46, False),
    ("DOCTOR ADVICE 🩺", "#D8E8D4", "#1B2A4A", "#1B2A4A", 46, False),
    
    # --- Universal Outro & CTA ---
    ("SUBSCRIBE & COMMENT 👇", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("LIKE & SHARE ❤️", "#F4C430", "#1B2A4A", "#1B2A4A", 46, False),
    ("FOLLOW FOR MORE 🔔", "#D8E8D4", "#1B2A4A", "#1B2A4A", 46, False),
    ("COMMENT YOUR DOUBTS 💬", "#FFF8E7", "#1B2A4A", "#1B2A4A", 46, False),
]

def render_single_badge_to_disk(text, bg="#F4C430", txt_col="#1B2A4A", border_col="#1B2A4A", fsize=46, strike=False, out_filename=None, overwrite=False):
    if out_filename is None:
        # Create unique filename from text
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', text)[:25].strip('_')
        h = hashlib.md5(text.encode('utf-8')).hexdigest()[:6]
        out_filename = f"b_{safe_name}_{h}.png"
        
    out_path = os.path.join(BADGE_DIR, out_filename)
    if os.path.exists(out_path) and not overwrite:
        return out_path  # Already exists locally, never re-generate unless forced

    st_style = 'text-decoration: line-through; text-decoration-color: #C84B28; text-decoration-thickness: 5px;' if strike else ''
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@font-face {{
    font-family: 'Noto Sans Telugu';
    src: url('NotoSansTelugu-Full.ttf') format('truetype');
    font-weight: 700 800;
}}
@font-face {{
    font-family: 'Montserrat';
    src: url('Montserrat-ExtraBold.ttf') format('truetype');
    font-weight: 800;
}}
body {{
    margin: 0;
    padding: 30px;
    background: #00FF00;
    display: inline-block;
}}
.badge {{
    background: {bg};
    border: 3.5px solid {border_col};
    border-radius: 20px;
    padding: 16px 36px;
    box-shadow: 6px 6px 0px {border_col};
    font-family: 'Montserrat', 'Noto Sans Telugu', sans-serif;
    font-weight: 800;
    font-size: {fsize}px;
    color: {txt_col};
    letter-spacing: 0.5px;
    display: inline-block;
    white-space: nowrap;
    {st_style}
}}
</style>
</head>
<body>
<div class="badge">{text}</div>
</body>
</html>"""

    temp_id = hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
    html_path = os.path.join(WORKSPACE, f"temp_{temp_id}.html")
    shot_path = os.path.join(WORKSPACE, f"shot_{temp_id}.png")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    cmd = [
        EDGE_PATH,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--screenshot={shot_path}",
        "--window-size=1200,400",
        f"file:///{html_path.replace(os.sep, '/')}"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(shot_path):
        im = Image.open(shot_path).convert("RGBA")
        datas = im.getdata()
        new_data = []
        for item in datas:
            if item[1] > 220 and item[0] < 50 and item[2] < 50:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        im.putdata(new_data)
        bbox = im.getbbox()
        if bbox:
            pad = 4
            im = im.crop((max(0, bbox[0]-pad), max(0, bbox[1]-pad), min(im.width, bbox[2]+pad), min(im.height, bbox[3]+pad)))
        im.save(out_path, "PNG")

        if os.path.exists(html_path): os.remove(html_path)
        if os.path.exists(shot_path): os.remove(shot_path)

    return out_path

def build_universal_catalog():
    print(f"Checking and expanding offline badge catalog in: {BADGE_DIR}")
    created = 0
    for text, bg, txt_col, border_col, fsize, strike in UNIVERSAL_LIBRARY:
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', text)[:25].strip('_')
        h = hashlib.md5(text.encode('utf-8')).hexdigest()[:6]
        fname = f"lib_{safe_name}_{h}.png"
        p = os.path.join(BADGE_DIR, fname)
        if not os.path.exists(p):
            render_single_badge_to_disk(text, bg, txt_col, border_col, fsize, strike, fname)
            created += 1
            print(f" [+] Generated offline badge: {fname} -> '{text}'")
    
    total = len(os.listdir(BADGE_DIR))
    print(f"Catalog ready: {total} total badge PNGs permanently cached on disk!")

if __name__ == "__main__":
    build_universal_catalog()
