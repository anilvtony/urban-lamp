# Cinematic Typography & Motion Graphics Engine Guide

This engine replaces static text overlays with professional, documentary-grade kinetic typography.

---

## 🎛️ How to Enable or Disable This Feature (On-Demand Toggle)

At the top of [auto_render_cinematic.py](file:///c:/Users/aanil/Documents/Auto_Video_Editing/auto_render_cinematic.py):

```python
# Set to True for cinematic motion; Set to False for static cards
ENABLE_CINEMATIC_TEXT_ANIMATIONS = True
```

- When `True`: The entire 3-stage life-cycle animation system runs automatically.
- When `False`: Text renders as clean, static badges without motion.

---

## 🎬 3-Stage Cinematic Life-Cycle Architecture

Every text element follows three stages:

### 1. Entrance Transitions (Selected per context):
- **Falling Letters & Cascade:** Soft drop from above with an elastic settle (Scene 1, Scene 7, Scene 8, Scene 10).
- **Wave & Mask Unfold Reveal:** Progressive wipe unfold across the card (Scene 3, Scene 6, Scene 9, Scene 13).
- **Slam-Down Dynamic Impact:** Fast drop from 140% scale with a micro-rebound for shocking facts and warnings (Scene 4, Scene 12, Scene 14).
- **Elastic Pop & Bounce:** 0% → 110% → 100% elastic entrance for questions and key takeaways (Scene 2, Scene 11, Scene 15).

### 2. Continuous Motion (While Audience Reads):
- **Sinusoidal Breathing Bob:** Subtle vertical micro-floating ($\pm 3.5\text{px}$) so text never looks frozen.
- **Micro-Scale Pulse:** Subtle organic breathing ($1.0 \leftrightarrow 1.012$) keeping text alive.
- **Cinematic Shimmer Beam:** A traveling light sweep moving across the letters every 2.4 seconds.

### 3. Elegant Exit Transitions:
- **Upward Float Dissolve:** Smooth vertical drift into opacity zero.
- **Wave Wipe-Out:** Progressive wipe from left to right preceding slide cuts.
- **Gravity Drop Fade:** Soft downwards settle into transparent alpha.

---

## 🚀 Running the Script Offline
```powershell
python auto_render_cinematic.py
```
Output target: `Fasting_Short_Cinematic_Motion.mp4` (1080x1920 30FPS).
