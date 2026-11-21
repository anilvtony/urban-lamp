import subprocess
import os
import json
from PIL import Image

WORKSPACE = r"c:\Users\aanil\Documents\Auto_Video_Editing"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT_DIR = os.path.join(WORKSPACE, "rendered_badges")
os.makedirs(OUT_DIR, exist_ok=True)

badges_data = [
    ('p2_b1', 'SUPER INTERESTING TOPIC!', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
    ('p2_b2', 'FASTING = ఆకలితో ఉండటమా?', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
    ('p2_b3', 'TIFFIN ➔ LUNCH ➔ DINNER', '#D8E8D4', '#1B2A4A', '#1B2A4A', 44, False),
    ('p2_b4', '16 HRS = BACKUP SYSTEM ON! ⚡', '#FFF8E7', '#C84B28', '#C84B28', 44, False),
    ('p2_b5', 'BODY లోపల ఏం జరుగుతుంది? ❓', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
    ('p2_b6', 'STEP BY STEP SCIENCE 👇', '#D8E8D4', '#1B2A4A', '#1B2A4A', 46, False),
    ('p2_b7', 'GLYCOGEN = PHONE BATTERY 🔋', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
    ('p2_b8_1', 'INSULIN ⬇️', '#FFF8E7', '#1B2A4A', '#1B2A4A', 46, False),
    ('p2_b8_2', 'FAT CELLS OPEN 🔑', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
    ('p2_b9', 'KETONES = BRAIN INVERTER ⚡', '#D8E8D4', '#1B2A4A', '#1B2A4A', 44, False),
    ('p2_b10', 'AUTOPHAGY = CELL CLEANUP 🧹', '#FFF8E7', '#1B2A4A', '#1B2A4A', 44, False),
    ('p2_b11_1', 'FASTING ≠ STARVATION', '#FFF8E7', '#C84B28', '#C84B28', 44, False),
    ('p2_b11_2', 'PLANNED REST ⚖️', '#D8E8D4', '#1B2A4A', '#1B2A4A', 44, False),
    ('p2_b12', 'BODY WEAK అవ్వదు! 💪', '#D8E8D4', '#1B2A4A', '#1B2A4A', 46, False),
    ('p2_b13_1', 'ఆకలి కాదు...', '#FFF8E7', '#1B2A4A', '#1B2A4A', 46, True),
    ('p2_b13_2', 'ULTIMATE REPAIR MODE! 🛠️', '#F4C430', '#1B2A4A', '#1B2A4A', 44, False),
    ('p2_b14', 'SUBSCRIBE & COMMENT 👇', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
]

for bid, text, bg, txt_col, border_col, fsize, strike in badges_data:
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
<div class="badge" id="target">{text}</div>
</body>
</html>"""
    
    html_path = os.path.join(WORKSPACE, f"temp_{bid}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    shot_path = os.path.join(WORKSPACE, f"shot_{bid}.png")
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
        # Chroma key on pure green background (#00FF00)
        datas = im.getdata()
        width, height = im.size
        min_x, min_y, max_x, max_y = width, height, 0, 0
        new_data = []
        for item in datas:
            # Check if green
            if item[1] > 220 and item[0] < 50 and item[2] < 50:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
                
        im.putdata(new_data)
        
        # Bounding box of non-transparent pixels
        bbox = im.getbbox()
        if bbox:
            pad = 4
            x0 = max(0, bbox[0] - pad)
            y0 = max(0, bbox[1] - pad)
            x1 = min(width, bbox[2] + pad)
            y1 = min(height, bbox[3] + pad)
            cropped = im.crop((x0, y0, x1, y1))
        else:
            cropped = im
            
        final_badge_path = os.path.join(OUT_DIR, f"{bid}.png")
        cropped.save(final_badge_path, "PNG")
        print(f"Rendered {final_badge_path} ({cropped.size[0]}x{cropped.size[1]})")
        
        if os.path.exists(html_path): os.remove(html_path)
        if os.path.exists(shot_path): os.remove(shot_path)

print("Batch complete!")
