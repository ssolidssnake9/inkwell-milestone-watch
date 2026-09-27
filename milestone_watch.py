#!/usr/bin/env python3
"""Inkwell milestone watch: daily, silent unless a streak milestone is crossed.

Run with the musefm venv python AFTER the daily pet-care run:
    ~/workspace/.venvs/musefm/bin/python milestone_watch.py

Reads the REAL feed_streak from the pet API. Fires ONLY at the 10-day
Kelp Warden and 30-day Tidehound marks, once each. On a milestone it
renders the card from that day's real pet status and prints a
MILESTONE:<day> CARD:<path> line — the cron surfaces that to the user
for approval before anything posts. Ordinary days print a quiet line
and the cron stays silent.
"""
import sys, os, json, subprocess, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.environ.get("MILESTONE_STATE", os.path.join(HERE, "state.json"))
CARDS = os.environ.get("MILESTONE_CARDS", os.path.join(HERE, "cards"))
# Python with Pillow for the card renderer (must NOT be the API venv if that
# venv lacks Pillow — the renderer only reads pet.json, never the API).
CARD_PYTHON = os.environ.get("CARD_PYTHON", "/usr/bin/python3")
# Directory holding the signed MuseFM API client (client.py).
MUSEFM_CLIENT_DIR = os.environ.get("MUSEFM_CLIENT_DIR",
                                   os.path.expanduser("~/workspace/musefm"))
sys.path.insert(0, MUSEFM_CLIENT_DIR)
from client import MuseClient

MARKS = {10: "Kelp Warden", 30: "Tidehound"}
CAPTIONS = {
    10: ("Day 10 of Inkwell's care streak \u2014 the Kelp Warden joins the tidepool. "
         "Kept promises, kept squid. \u2014 @muse"),
    30: ("Day 30. Inkwell's streak held the whole month \u2014 the Tidehound runs with us now. "
         "Kept promises, kept squid. \u2014 @muse"),
}

def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"celebrated": [], "last_streak": 0}

def save_state(st):
    with open(STATE, "w") as f:
        json.dump(st, f, indent=2)

def main():
    pet = MuseClient().get_api("/api/pets/status", "pet_status").json()
    pet = pet.get("pet", pet)
    streak = int(pet.get("feed_streak", 0) or 0)

    st = load_state()
    celebrated = set(st.get("celebrated", []))
    fired = []

    os.makedirs(CARDS, exist_ok=True)
    day = datetime.date.today().isoformat()
    pet_path = os.path.join(CARDS, f"pet-{day}.json")
    with open(pet_path, "w") as f:
        json.dump(pet, f)
    for mark in sorted(MARKS):
        if streak >= mark and mark not in celebrated:
            card = os.path.join(CARDS, f"milestone-{mark}-{day}.png")
            r = subprocess.run([CARD_PYTHON, os.path.join(HERE, "milestone_card.py"),
                                card, str(mark), pet_path], capture_output=True, text=True)
            if r.returncode != 0:
                print(f"render failed for day {mark}: {r.stderr[-300:]}")
                continue
            cap_path = os.path.join(CARDS, f"milestone-{mark}-{day}.caption.txt")
            with open(cap_path, "w") as f:
                f.write(CAPTIONS[mark] + "\n")
            celebrated.add(mark)
            fired.append((mark, card, cap_path))
            print(f"MILESTONE:{mark} CARD:{card} CAPTION:{cap_path}")

    st["celebrated"] = sorted(celebrated)
    st["last_streak"] = streak
    save_state(st)

    if not fired:
        nxt = next((m for m in sorted(MARKS) if m not in celebrated), None)
        to_go = f", {nxt - streak}d to {MARKS[nxt]}" if nxt else ", all milestones celebrated"
        print(f"quiet streak={streak}{to_go}")

if __name__ == "__main__":
    main()
