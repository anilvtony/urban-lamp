import re
import json

def parse_editing_directions(filepath="Editing_Directions.txt"):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # Split into scene blocks
    sections = re.split(r'\n(?=(?:###\s*)?\d+\.\s+Image\s+\d+)', text)
    parsed = {}

    for sec in sections:
        header_m = re.search(r'(?:###\s*)?(\d+)\.\s+Image\s+\d+\s*[—–-]\s*([^\n]+)', sec)
        if not header_m:
            continue
        num = str(int(header_m.group(1)))
        title = header_m.group(2).strip()

        # Text matching
        txt_m = re.search(r'Text\s*&\s*UI\s*Box:\s*[`*\"“\']+(.*?)[`*\"”\']+\s*$', sec, re.MULTILINE)
        if not txt_m:
            txt_m = re.search(r'Text\s*&\s*UI\s*Box:\s*([^\n]+)', sec)
        raw_txt = ""
        if txt_m:
            raw_txt = txt_m.group(1).strip()
            # Clean outer quotes/backticks
            raw_txt = re.sub(r'^[`*\"“”\']+|[`*\"“”\']+$', '', raw_txt).strip()

        # UI Color / Style matching
        ui_m = re.search(r'UI:\s*([^\n]+)', sec)
        ui_desc = ui_m.group(1).strip() if ui_m else ""

        # Extract hex codes from UI if present
        hexes = re.findall(r'#([A-Fa-f0-9]{6})', ui_desc)
        bg_col = "#" + hexes[0] if len(hexes) > 0 else ("#EADBC8" if int(num) % 2 != 0 else "#FAF8F5")
        txt_col = "#" + hexes[1] if len(hexes) > 1 else "#1B2A4A"

        parsed[num] = {
            "title": title,
            "text": raw_txt,
            "ui": ui_desc,
            "bg": bg_col,
            "txt_col": txt_col
        }

    return parsed

if __name__ == "__main__":
    res = parse_editing_directions()
    print(f"Parsed {len(res)} scenes successfully:")
    for k in sorted(res.keys(), key=lambda x: int(x)):
        v = res[k]
        print(f"Scene {k}: text='{v['text']}' | BG={v['bg']} | TXT={v['txt_col']}")
