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

# User Direction:
# - Clean Pure White (#FFFFFF) background only
# - Deep Indigo (#2B3A67) or Terracotta (#C85A32) text and border
# - Auto-wrap long text across 2 neat lines (max-width: 620px)

SCENE_BADGES = [
    (1, "Intermittent Fasting పూర్తి వివరణ", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 44, "card"),
    (2, "ఇది Diet కాదు — Eating Schedule!", "#FFFFFF", "#C85A32", "#2B3A67", "#2B3A67", 44, "card"),
    (3, "16/8, 5:2, OMAD — ఇన్ని రకాలా?", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 44, "card"),
    (4, "తప్పు Method ఎంచుకుంటే నీరసం!", "#FFFFFF", "#C85A32", "#2B3A67", "#2B3A67", 44, "card"),
    (5, "మీ Bodyకి ఏది సరిపోతుంది?", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 44, "card"),
    (6, "Simpleగా Break Down చేద్దాం!", "#FFFFFF", "#2E7D7B", "#2B3A67", "#2B3A67", 44, "card"),
    (7, "కడుపుకి Fixed Opening & Closing Time", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 42, "card"),
    (8, "Food ఆగిపోయాకే Body Cleaning!", "#FFFFFF", "#2E7D7B", "#2B3A67", "#2B3A67", 44, "card"),
    (9, "కడుపు మాడ్చుకోవడం కాదు — Smart Routine", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 42, "card"),
    (10, "16/8 Method: 16 Hrs Off, 8 Hrs On", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 42, "card"),
    (11, "8 Hours నిద్రలోనే గడిచిపోతాయి!", "#FFFFFF", "#2E7D7B", "#2B3A67", "#2B3A67", 44, "card"),
    (12, "అందరి ఫస్ట్ ఛాయిస్: 16/8", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 44, "card"),
    (13, "Beginners కోసం 12/12 Method", "#FFFFFF", "#2E7D7B", "#2B3A67", "#2B3A67", 44, "card"),
    (14, "మెల్లగా 14/10 కి Step Up!", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 44, "card"),
    (15, "12/12 తో స్టార్ట్ చేయడం Safe!", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 44, "card"),
    (16, "5:2 Diet: 5 Days Normal, 2 Days Low", "#FFFFFF", "#C85A32", "#2B3A67", "#2B3A67", 42, "card"),
    (17, "రెండు రోజుల మధ్య Gap తప్పనిసరి!", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 44, "card"),
    (18, "రోజూ కుదరని వాళ్లకి 5:2 Best", "#FFFFFF", "#2E7D7B", "#2B3A67", "#2B3A67", 44, "card"),
    (19, "Eat-Stop-Eat: 24 Hours Deep Reset", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 42, "card"),
    (20, "Alternate Day: రోజు విడిచి రోజు", "#FFFFFF", "#C85A32", "#2B3A67", "#2B3A67", 44, "card"),
    (21, "Beginners ఇవి వెంటనే Try చేయొద్దు!", "#FFFFFF", "#C85A32", "#2B3A67", "#2B3A67", 44, "card"),
    (22, "Warrior Diet: 20 Hrs Fast / 4 Hrs Eat", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 42, "card"),
    (23, "OMAD: రోజుకి ఒక్కసారే భోజనం!", "#FFFFFF", "#C85A32", "#2B3A67", "#2B3A67", 44, "card"),
    (24, "పోషకాలు అందకపోయే Risk ఉంది", "#FFFFFF", "#C85A32", "#2B3A67", "#2B3A67", 44, "card"),
    (25, "అందరికీ ఒకే Method సరిపోదు!", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 44, "card"),
    (26, "డాక్టర్ సలహా లేకుండా Risk వద్దు!", "#FFFFFF", "#C85A32", "#2B3A67", "#2B3A67", 44, "card"),
    (27, "Protein + Fiber + Water మర్చిపోవద్దు", "#FFFFFF", "#2E7D7B", "#2B3A67", "#2B3A67", 42, "card"),
    (28, "అసలు నిజం ఏంటంటే...", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 44, "card"),
    (29, "లాంగ్ టర్మ్‌లో ఫాలో అయ్యేదే BEST!", "#FFFFFF", "#C85A32", "#2B3A67", "#2B3A67", 44, "card"),
    (30, "Subscribe & Comment Below!", "#FFFFFF", "#2B3A67", "#2B3A67", "#2B3A67", 44, "card"),
]

def render_badge(num, text, bg="#FFFFFF", txt_col="#2B3A67", border_col="#2B3A67", shadow_col="#2B3A67", fsize=44, shape="card", wrap_width=620):
    radius = "18px"
    wrap_css = f"max-width: {wrap_width}px; white-space: normal; word-break: keep-all; text-align: center; line-height: 1.35;" if (wrap_width and len(text) > 22) else "white-space: nowrap;"
    
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
    {wrap_css}
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
        "--window-size=1600,600",
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
    print("Done generating all 30 badges in pure white background with text wrapping!")
