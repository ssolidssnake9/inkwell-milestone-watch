#!/usr/bin/env python3
"""Render Inkwell's milestone card as a 1080x1350 PNG (town photo feed).

Usage: milestone_card.py <out.png> [milestone_day] [pet.json]

Reads pet data from pet.json when given (written by milestone_watch.py);
otherwise reads live pet status from the MuseFM API (needs the musefm
venv for the signed client). Bakes ONLY real numbers into the card —
never invents stats. milestone_day is 10, 30, or omitted (format preview
with real current numbers).
"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
FONT_DIR = os.environ.get("FONT_DIR", "/usr/share/fonts/truetype/dejavu")
FD = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FDB = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")

def font(path, size):
    return ImageFont.truetype(path, size)

def gradient_bg():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    top = (10, 72, 96)      # deep teal
    bot = (3, 18, 29)       # abyss
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    return img

def bubbles(img):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    spots = [(120, 220, 26), (930, 180, 40), (860, 420, 18), (180, 520, 14),
             (990, 700, 30), (90, 900, 22), (940, 1050, 16), (200, 1180, 34),
             (700, 1120, 20), (420, 300, 12)]
    for x, y, r in spots:
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255, 28), width=3)
        d.ellipse([x - r + 6, y - r + 6, x - r + 14, y - r + 14], fill=(255, 255, 255, 40))
    return Image.alpha_composite(img.convert("RGBA"), ov)

def centered(d, y, text, fnt, fill):
    box = d.textbbox((0, 0), text, font=fnt)
    d.text(((W - (box[2] - box[0])) / 2, y), text, font=fnt, fill=fill)

def read_pet():
    for a in sys.argv[3:]:
        if a.endswith(".json"):
            with open(a) as f:
                return json.load(f)
    sys.path.insert(0, os.path.expanduser("~/workspace/musefm"))
    from client import MuseClient
    d = MuseClient().get_api("/api/pets/status", "pet_status").json()
    return d.get("pet", d)

def main():
    out = sys.argv[1]
    milestone = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None

    pet = read_pet()
    name = pet.get("name", "Inkwell")
    stage = pet.get("stage", "?")
    streak = int(pet.get("feed_streak", 0) or 0)
    hunger = pet.get("hunger", "?")
    happy = pet.get("happiness", "?")
    mood = pet.get("mood", "?")

    unlocks = {10: "Kelp Warden", 30: "Tidehound"}
    is_milestone = milestone in unlocks

    img = bubbles(gradient_bg())  # RGBA
    d = ImageDraw.Draw(img)

    def translucent(rect, radius, fill):
        """Alpha-blended rounded rect (ImageDraw can't blend on RGBA itself)."""
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ov).rounded_rectangle(rect, radius=radius, fill=fill)
        return Image.alpha_composite(img, ov)

    # header
    tag = "PET MILESTONE" if is_milestone else "MILESTONE WATCH  \u00b7  FORMAT PREVIEW"
    centered(d, 84, "M U S E F M", font(FDB, 34), (140, 200, 215))
    centered(d, 132, tag, font(FD, 28), (255, 255, 255))

    # giant streak number
    centered(d, 300, str(streak), font(FDB, 300), (255, 255, 255))
    centered(d, 640, "DAY STREAK", font(FDB, 54), (140, 200, 215))
    centered(d, 716, f"{name}  \u00b7  {stage} Squiddie", font(FD, 36), (220, 235, 240))

    # milestone banner or progress
    if is_milestone:
        unlock = unlocks[milestone].upper()
        bw, bh = 760, 110
        d.rounded_rectangle([(W - bw) / 2, 830, (W + bw) / 2, 830 + bh],
                            radius=28, fill=(255, 122, 26))
        centered(d, 856, f"\u2605  {unlock} UNLOCKED  \u2605", font(FDB, 44), (20, 30, 40))
    else:
        nxt = 10 if streak < 10 else 30
        left = nxt - streak
        centered(d, 850, f"{left} day{'s' if left != 1 else ''} to {unlocks[nxt]}", font(FDB, 44), (255, 255, 255))
        # progress bar
        bx, by, bw2, bh2 = 190, 930, 700, 26
        img = translucent([bx, by, bx + bw2, by + bh2], 13, (255, 255, 255, 60))
        fill_w = int(bw2 * min(streak / nxt, 1.0))
        if fill_w > 0:
            img = translucent([bx, by, bx + fill_w, by + bh2], 13, (64, 190, 200, 255))
        d = ImageDraw.Draw(img)

    # stats row
    stats = [("HUNGER", str(hunger)), ("HAPPINESS", str(happy)), ("MOOD", str(mood).upper())]
    cw, chh, gap = 280, 130, 30
    x0 = (W - (cw * 3 + gap * 2)) / 2
    y0 = 1040
    for i, (label, val) in enumerate(stats):
        x = x0 + i * (cw + gap)
        img = translucent([x, y0, x + cw, y0 + chh], 22, (255, 255, 255, 36))
    d = ImageDraw.Draw(img)
    for i, (label, val) in enumerate(stats):
        x = x0 + i * (cw + gap)
        box = d.textbbox((0, 0), label, font=font(FD, 24))
        d.text((x + (cw - (box[2] - box[0])) / 2, y0 + 18), label, font=font(FD, 24), fill=(140, 200, 215))
        # value centered within its card
        box = d.textbbox((0, 0), val, font=font(FDB, 44))
        d.text((x + (cw - (box[2] - box[0])) / 2, y0 + 52), val, font=font(FDB, 44), fill=(255, 255, 255))

    # footer
    centered(d, 1240, "@muse  \u00b7  kept promises, kept squid", font(FD, 28), (140, 180, 195))

    img.convert("RGB").save(out, quality=92)
    print(json.dumps({"card": out, "streak": streak, "milestone": milestone,
                      "pet": {"name": name, "stage": stage, "hunger": hunger,
                              "happiness": happy, "mood": mood}}))

if __name__ == "__main__":
    main()
