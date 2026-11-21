import subprocess
import os
import json
from PIL import Image

WORKSPACE = r"c:\Users\aanil\Documents\Auto_Video_Editing"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT_DIR = os.path.join(WORKSPACE, "rendered_badges")
os.makedirs(OUT_DIR, exist_ok=True)

badges_data = [
    ('b1', 'SUPER INTERESTING TOPIC!', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
    ('b2', 'ఆకలి = FAT BURN?', '#F4C430', '#1B2A4A', '#1B2A4A', 48, False),
    ('b3', 'LUNCH LATE? / DINNER SKIP?', '#D8E8D4', '#1B2A4A', '#1B2A4A', 44, False),
    ('b4', 'BODY FATని ముట్టుకోదు! 🔒', '#FFF8E7', '#C84B28', '#C84B28', 46, False),
    ('b5', '❓ మరి BODY ఏం చేస్తుంది? ❓', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
    ('b6', 'SIMPLE SCIENCE 👇', '#D8E8D4', '#1B2A4A', '#1B2A4A', 48, False),
    ('b7_1', 'GLUCOSE = CASH 💵', '#D8E8D4', '#1B2A4A', '#1B2A4A', 46, False),
    ('b7_2', 'FAT = BANK FD 🏦', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
    ('b8', 'GLYCOGEN = FRIDGE FOOD 🧊', '#FFF8E7', '#1B2A4A', '#1B2A4A', 46, False),
    ('b9_1', 'PETROL ➔ CNG', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
    ('b9_2', 'INSULIN = FAT LOCK 🔒', '#FDE8D7', '#C84B28', '#C84B28', 48, False),
    ('b10_1', '10–12 HOURS LATER ⏱️', '#FFF8E7', '#1B2A4A', '#1B2A4A', 44, False),
    ('b10_2', 'GLUCAGON = MASTER KEY 🔑', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
    ('b11', 'FATTY ACIDS ➔ <span style="color:#C84B28;">KETONES</span> 🔥', '#FDE8D7', '#1B2A4A', '#1B2A4A', 46, False),
    ('b12', 'ఆకలి = GHRELIN ALARM ⏰', '#F4C430', '#1B2A4A', '#C84B28', 48, False),
    ('b13', 'INSULIN ⬇️ = GAME CHANGER', '#D8E8D4', '#1B2A4A', '#1B2A4A', 46, False),
    ('b14_1', 'ఆకలి ≠ FAT BURN ❌', '#FFF8E7', '#1B2A4A', '#1B2A4A', 48, True),
    ('b14_2', 'INSULIN తగ్గితేనే FAT BURN START! 🔥', '#F4C430', '#1B2A4A', '#1B2A4A', 44, False),
    ('b15', 'SUBSCRIBE & COMMENT 👇', '#F4C430', '#1B2A4A', '#1B2A4A', 46, False),
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
    padding: 25px;
    background: transparent;
    display: inline-block;
}}
.badge {{
    background: {bg};
    border: 3.5px solid {border_col};
    border-radius: 20px;
    padding: 16px 36px;
    box-shadow: 6px 6px 0px {border_col};
    color: {txt_col};
    font-size: {fsize}px;
    display: inline-flex;
    align-items: center;
    gap: 12px;
    font-family: 'Montserrat', 'Noto Sans Telugu', 'Segoe UI Emoji', sans-serif;
    font-weight: 800;
    white-space: nowrap;
    {st_style}
}}
</style>
</head>
<body>
<div class="badge">
    {text}
</div>
</body>
</html>"""
    
    html_file = os.path.join(WORKSPACE, f"badge_{bid}.html")
    png_file = os.path.join(OUT_DIR, f"{bid}.png")
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    cmd = [
        EDGE_PATH,
        '--headless',
        '--disable-gpu',
        '--hide-scrollbars',
        '--default-background-color=00000000',
        f'--screenshot={png_file}',
        '--window-size=1200,300',
        html_file
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if os.path.exists(html_file):
        os.remove(html_file)
        
    # Crop transparent background
    im = Image.open(png_file)
    bbox = im.getbbox()
    if bbox:
        im.crop(bbox).save(png_file)
        
    print(f"Generated {bid}.png: {im.size}")

print("ALL BADGES GENERATED SUCCESSFULLY!")
