import os
import sys
import re
import json
import subprocess
from PIL import Image

WORKSPACE = r"c:\Users\aanil\Documents\Auto_Video_Editing"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BADGE_DIR = os.path.join(WORKSPACE, "rendered_badges")
os.makedirs(BADGE_DIR, exist_ok=True)

# Colors from Editing_Directions.txt Style Guide:
# Backgrounds: Soft Sand (#EADBC8), Off-White (#FAF8F5)
# Texts: Deep Indigo (#2B3A67), Burnt Sienna (#C85A32), Teal Slate (#2E7D7B)
# Borders: 3.5px Deep Indigo (#2B3A67)
# Shadows: Flat 6px 6px 0px Teal Slate (#2E7D7B), Burnt Sienna (#C85A32), or Deep Indigo (#2B3A67)

SCENE_BADGES = [
    (1, "Intermittent Fasting పూర్తి వివరణ", "#EADBC8", "#2B3A67", "#2B3A67", "#2E7D7B", 46, "pill"),
    (2, "ఇది Diet కాదు — Eating Schedule!", "#FAF8F5", "#C85A32", "#2B3A67", "#2B3A67", 46, "card"),
    (3, "16/8, 5:2, OMAD — ఇన్ని రకాలా?", "#EADBC8", "#2B3A67", "#2B3A67", "#C85A32", 46, "pill"),
    (4, "తప్పు Method ఎంచుకుంటే నీరసం!", "#FAF8F5", "#C85A32", "#2B3A67", "#2E7D7B", 46, "card"),
    (5, "మీ Bodyకి ఏది సరిపోతుంది?", "#EADBC8", "#2B3A67", "#2B3A67", "#2E7D7B", 46, "card"),
    (6, "Simpleగా Break Down చేద్దాం!", "#FAF8F5", "#2E7D7B", "#2B3A67", "#C85A32", 46, "pill"),
    (7, "కడుపుకి Fixed Opening & Closing Time", "#EADBC8", "#2B3A67", "#2B3A67", "#2E7D7B", 44, "card"),
    (8, "Food ఆగిపోయాకే Body Cleaning!", "#FAF8F5", "#2E7D7B", "#2B3A67", "#2B3A67", 46, "card"),
    (9, "కడుపు మాడ్చుకోవడం కాదు — Smart Routine", "#EADBC8", "#2B3A67", "#2B3A67", "#C85A32", 44, "pill"),
    (10, "16/8 Method: 16 Hrs Off, 8 Hrs On", "#EADBC8", "#2B3A67", "#2B3A67", "#2E7D7B", 44, "card"),
    (11, "8 Hours నిద్రలోనే గడిచిపోతాయి!", "#FAF8F5", "#2E7D7B", "#2B3A67", "#2B3A67", 46, "pill"),
    (12, "అందరి ఫస్ట్ ఛాయిస్: 16/8", "#EADBC8", "#2B3A67", "#2B3A67", "#C85A32", 46, "pill"),
    (13, "Beginners కోసం 12/12 Method", "#FAF8F5", "#2E7D7B", "#2B3A67", "#2E7D7B", 46, "card"),
    (14, "మెల్లగా 14/10 కి Step Up!", "#EADBC8", "#2B3A67", "#2B3A67", "#C85A32", 46, "pill"),
    (15, "12/12 తో స్టార్ట్ చేయడం Safe!", "#FAF8F5", "#2B3A67", "#2B3A67", "#2E7D7B", 46, "pill"),
    (16, "5:2 Diet: 5 Days Normal, 2 Days Low", "#EADBC8", "#C85A32", "#2B3A67", "#2B3A67", 44, "card"),
    (17, "రెండు రోజుల మధ్య Gap తప్పనిసరి!", "#FAF8F5", "#2B3A67", "#2B3A67", "#C85A32", 46, "card"),
    (18, "రోజూ కుదరని వాళ్లకి 5:2 Best", "#EADBC8", "#2E7D7B", "#2B3A67", "#2B3A67", 46, "pill"),
    (19, "Eat-Stop-Eat: 24 Hours Deep Reset", "#FAF8F5", "#2B3A67", "#2B3A67", "#2E7D7B", 44, "card"),
    (20, "Alternate Day: రోజు విడిచి రోజు", "#EADBC8", "#C85A32", "#2B3A67", "#2B3A67", 46, "card"),
    (21, "Beginners ఇవి వెంటనే Try చేయొద్దు!", "#FAF8F5", "#C85A32", "#2B3A67", "#C85A32", 46, "pill"),
    (22, "Warrior Diet: 20 Hrs Fast / 4 Hrs Eat", "#EADBC8", "#2B3A67", "#2B3A67", "#C85A32", 44, "card"),
    (23, "OMAD: రోజుకి ఒక్కసారే భోజనం!", "#FAF8F5", "#C85A32", "#2B3A67", "#2B3A67", 46, "card"),
    (24, "పోషకాలు అందకపోయే Risk ఉంది", "#EADBC8", "#C85A32", "#2B3A67", "#2E7D7B", 46, "pill"),
    (25, "అందరికీ ఒకే Method సరిపోదు!", "#FAF8F5", "#2B3A67", "#2B3A67", "#2E7D7B", 46, "card"),
    (26, "డాక్టర్ సలహా లేకుండా Risk వద్దు!", "#EADBC8", "#C85A32", "#2B3A67", "#2B3A67", 46, "card"),
    (27, "Protein + Fiber + Water మర్చిపోవద్దు", "#FAF8F5", "#2E7D7B", "#2B3A67", "#2B3A67", 44, "pill"),
    (28, "అసలు నిజం ఏంటంటే...", "#EADBC8", "#2B3A67", "#2B3A67", "#2E7D7B", 46, "card"),
    (29, "లాంగ్ టర్మ్‌లో ఫాలో అయ్యేదే BEST!", "#EADBC8", "#C85A32", "#2B3A67", "#2E7D7B", 46, "card"),
    (30, "Subscribe & Comment Below!", "#FAF8F5", "#2B3A67", "#2B3A67", "#C85A32", 46, "pill"),
]

def render_badge(num, text, bg, txt_col, border_col, shadow_col, fsize, shape):
    radius = "50px" if shape == "pill" else "16px"
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
    border-radius: {radius};
    padding: 16px 36px;
    box-shadow: 6px 6px 0px {shadow_col};
    font-family: 'Montserrat', 'Noto Sans Telugu', sans-serif;
    font-weight: 800;
    font-size: {fsize}px;
    color: {txt_col};
    letter-spacing: 0.5px;
    display: inline-block;
    white-space: nowrap;
}}
</style>
</head>
<body>
<div class="badge">{text}</div>
</body>
</html>"""

    html_path = os.path.join(WORKSPACE, f"gen_temp_{num}.html")
    shot_path = os.path.join(WORKSPACE, f"gen_shot_{num}.png")
    out_path = os.path.join(BADGE_DIR, f"p2_b{num}.png")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    cmd = [
        EDGE_PATH,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--screenshot={shot_path}",
        "--window-size=1600,400",
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
        print(f"Rendered p2_b{num}.png: '{text}' ({im.size})")

if __name__ == "__main__":
    for item in SCENE_BADGES:
        render_badge(*item)
    print("Done generating all 30 badges according to Editing_Directions.txt!")
