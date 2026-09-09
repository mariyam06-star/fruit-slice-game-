"""
Cute Fruit Slice — Hand Tracking Edition
==========================================
Slice cute floating fruits using just your finger, tracked live through your webcam!

Controls
--------
- Show your hand to the camera. Your INDEX FINGERTIP is the "blade".
- Move your finger quickly through a fruit to slice it.
- Press SPACE to start / restart after game over.
- Press Q or ESC to quit.

Requirements
------------
pip install opencv-python mediapipe numpy

Run
---
python hand_fruit_slice.py
"""

import cv2
import numpy as np
import mediapipe as mp
import random
import time
import math
from collections import deque

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
CAM_INDEX = 0
FRAME_W, FRAME_H = 960, 720
MAX_FRUITS_ON_SCREEN = 6
BASE_SPAWN_INTERVAL = 1.0       # seconds, decreases over time
MIN_SPAWN_INTERVAL = 0.45
FRUIT_LIFETIME_RANGE = (3.2, 4.8)
STARTING_LIVES = 3
TRAIL_MAX_POINTS = 10
TRAIL_POINT_TTL = 0.18          # seconds a trail point stays visible
SLICE_HIT_PADDING = 8           # extra px of forgiveness around fruit radius
SHOW_HAND_SKELETON = True       # toggle the colorful 21-point hand overlay (press H to toggle)

FRUIT_TYPES = [
    # name, base_color(BGR), accent_color(BGR), radius, points
    dict(name="strawberry", color=(90, 70, 255),  accent=(70, 180, 60),  r=42, points=10),
    dict(name="watermelon", color=(90, 210, 90),  accent=(110, 90, 255), r=52, points=12),
    dict(name="orange",     color=(30, 150, 255), accent=(30, 110, 255), r=44, points=10),
    dict(name="kiwi",       color=(70, 150, 110), accent=(200, 240, 230),r=38, points=14),
    dict(name="peach",      color=(160, 190, 255),accent=(130, 150, 255),r=44, points=10),
    dict(name="blueberry",  color=(210, 120, 90), accent=(230, 160, 130),r=36, points=16),
]

BG_TOP = (255, 235, 200)     # BGR (light sky blue-ish)
BG_BOTTOM = (215, 245, 255)  # BGR (warm cream)

FONT = cv2.FONT_HERSHEY_DUPLEX


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def draw_gradient_background(canvas):
    h, w = canvas.shape[:2]
    top = np.array(BG_TOP, dtype=np.float32)
    bottom = np.array(BG_BOTTOM, dtype=np.float32)
    grad = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1, 1)
    row = top.reshape(1, 1, 3) * (1 - grad) + bottom.reshape(1, 1, 3) * grad
    canvas[:, :, :] = np.broadcast_to(row, (h, w, 3)).astype(np.uint8)


def blend_frame_with_bg(cam_frame, bg_canvas, opacity=0.35):
    """Show the camera feed softly blended under the cute background so the
    player can still see themself, but the game reads as its own world."""
    return cv2.addWeighted(cam_frame, opacity, bg_canvas, 1 - opacity, 0)


def draw_alpha_circle(img, center, radius, color, alpha=1.0):
    if alpha >= 1.0:
        cv2.circle(img, center, radius, color, -1, lineType=cv2.LINE_AA)
        return
    overlay = img.copy()
    cv2.circle(overlay, center, radius, color, -1, lineType=cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


def draw_cute_face(img, cx, cy, r, seed):
    happy = seed > 0.5
    eye_dx = int(r * 0.32)
    eye_y = cy - int(r * 0.05)
    dark = (60, 45, 55)

    if happy:
        for side in (-1, 1):
            ex = cx + side * eye_dx
            cv2.ellipse(img, (ex, eye_y + int(r * 0.05)), (int(r * 0.13), int(r * 0.13)),
                        0, 200, 340, dark, max(2, int(r * 0.09)), cv2.LINE_AA)
    else:
        for side in (-1, 1):
            ex = cx + side * eye_dx
            cv2.ellipse(img, (ex, eye_y), (int(r * 0.09), int(r * 0.13)), 0, 0, 360, dark, -1, cv2.LINE_AA)
            cv2.circle(img, (ex + int(r * 0.03), eye_y - int(r * 0.05)), max(1, int(r * 0.03)), (255, 255, 255), -1, cv2.LINE_AA)

    # blush
    blush_color = (150, 140, 255)
    for side in (-1, 1):
        bx = cx + side * int(eye_dx * 1.7)
        by = eye_y + int(r * 0.28)
        draw_alpha_circle(img, (bx, by), int(r * 0.13), blush_color, alpha=0.35)

    # smile
    cv2.ellipse(img, (cx, eye_y + int(r * 0.2)), (int(r * 0.14), int(r * 0.1)),
                0, 20, 160, dark, max(2, int(r * 0.06)), cv2.LINE_AA)


def draw_fruit(img, fruit):
    cx, cy = int(fruit["x"]), int(fruit["y"])
    r = int(fruit["r"] * fruit.get("scale", 1.0))
    color = fruit["color"]
    accent = fruit["accent"]
    name = fruit["type"]

    # soft shadow
    draw_alpha_circle(img, (cx, cy + int(r * 0.15)), int(r * 0.85), (60, 60, 60), alpha=0.12)

    if name == "watermelon":
        draw_alpha_circle(img, (cx, cy), r, color, alpha=1.0)
        for i in range(-2, 3):
            x = cx + int(i * r * 0.28)
            cv2.line(img, (x, cy - r + 4), (x, cy + r - 4), accent, max(2, int(r * 0.06)), cv2.LINE_AA)
    elif name == "strawberry":
        cv2.ellipse(img, (cx, cy), (int(r * 0.9), r), 0, 0, 360, color, -1, cv2.LINE_AA)
        rng = random.Random(fruit["seed_int"])
        for _ in range(8):
            ang = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(0.25, 0.75) * r
            sx = cx + int(math.cos(ang) * rr * 0.7)
            sy = cy + int(math.sin(ang) * rr * 0.9)
            cv2.ellipse(img, (sx, sy), (max(1, int(r * 0.05)), max(1, int(r * 0.08))),
                        math.degrees(ang), 0, 360, (100, 220, 255), -1, cv2.LINE_AA)
        # leaf
        cv2.ellipse(img, (cx, cy - r), (int(r * 0.35), int(r * 0.18)), 0, 0, 360, accent, -1, cv2.LINE_AA)
    elif name == "orange":
        draw_alpha_circle(img, (cx, cy), r, color, alpha=1.0)
        cv2.ellipse(img, (cx + int(r * 0.15), cy - r), (int(r * 0.16), int(r * 0.28)), -25, 0, 360, (90, 190, 90), -1, cv2.LINE_AA)
    elif name == "kiwi":
        draw_alpha_circle(img, (cx, cy), r, (90, 170, 90), alpha=1.0)
        rng = random.Random(fruit["seed_int"])
        for _ in range(25):
            ang = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(0.2, 0.95) * r
            sx = cx + int(math.cos(ang) * rr)
            sy = cy + int(math.sin(ang) * rr)
            cv2.circle(img, (sx, sy), 1, (230, 245, 235), -1, cv2.LINE_AA)
    elif name == "peach":
        draw_alpha_circle(img, (cx, cy), r, color, alpha=1.0)
        cv2.line(img, (cx, cy - r + 4), (cx, cy - int(r * 0.2)), (240, 235, 255), max(1, int(r * 0.04)), cv2.LINE_AA)
        cv2.ellipse(img, (cx - int(r * 0.1), cy - r), (int(r * 0.14), int(r * 0.26)), 20, 0, 360, (90, 190, 90), -1, cv2.LINE_AA)
    elif name == "blueberry":
        offsets = [(-0.5, -0.1), (0.5, -0.1), (0, -0.55), (-0.25, 0.4), (0.25, 0.4)]
        for ox, oy in offsets:
            bx, by = cx + int(ox * r), cy + int(oy * r)
            draw_alpha_circle(img, (bx, by), int(r * 0.42), color, alpha=1.0)
            cv2.circle(img, (bx, by), int(r * 0.42), accent, max(1, int(r * 0.02)), cv2.LINE_AA)

    draw_cute_face(img, cx, cy, r, fruit["seed"])

    # life ring (shrinks as fruit is about to vanish)
    frac = clamp(fruit["life"] / fruit["max_life"], 0, 1)
    ring_color = (60, 60, 255) if frac < 0.25 else (255, 255, 255)
    start_angle = -90
    end_angle = start_angle + int(360 * frac)
    cv2.ellipse(img, (cx, cy), (r + 10, r + 10), 0, start_angle, end_angle, ring_color, 3, cv2.LINE_AA)


def draw_fruit_half(img, half):
    cx, cy = int(half["x"]), int(half["y"])
    r = int(half["r"])
    alpha = clamp(half["life"], 0, 1)
    fake_fruit = dict(half)
    fake_fruit["x"], fake_fruit["y"] = cx, cy
    fake_fruit["scale"] = 1.0
    overlay = img.copy()
    draw_fruit(overlay, fake_fruit)

    # mask to only the half in the direction of clip_angle
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    ang = half["clip_angle"]
    p1 = (int(cx - math.cos(ang) * r * 2), int(cy - math.sin(ang) * r * 2))
    p2 = (int(cx + math.cos(ang) * r * 2), int(cy + math.sin(ang) * r * 2))
    perp = ang + math.pi / 2
    p3 = (int(p2[0] + math.cos(perp) * r * 3), int(p2[1] + math.sin(perp) * r * 3))
    p4 = (int(p1[0] + math.cos(perp) * r * 3), int(p1[1] + math.sin(perp) * r * 3))
    cv2.fillPoly(mask, [np.array([p1, p2, p3, p4])], 255)

    masked = cv2.bitwise_and(overlay, overlay, mask=mask)
    inv_mask = cv2.bitwise_not(mask)
    bg_kept = cv2.bitwise_and(img, img, mask=inv_mask)
    combined = cv2.add(bg_kept, masked)
    cv2.addWeighted(combined, alpha, img, 1 - alpha, 0, img)


def draw_particle(img, p):
    alpha = clamp(p["life"], 0, 1)
    draw_alpha_circle(img, (int(p["x"]), int(p["y"])), max(1, int(p["size"] * alpha)), p["color"], alpha=alpha)


def draw_floater(img, f):
    alpha = clamp(f["life"], 0, 1)
    text = f["text"]
    scale = f["size"] / 30.0
    thickness = 2
    (tw, th), _ = cv2.getTextSize(text, FONT, scale, thickness)
    x, y = int(f["x"] - tw / 2), int(f["y"])
    overlay = img.copy()
    cv2.putText(overlay, text, (x, y), FONT, scale, (255, 255, 255), thickness + 3, cv2.LINE_AA)
    cv2.putText(overlay, text, (x, y), FONT, scale, f["color"], thickness, cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


def draw_trail(img, trail):
    now = time.time()
    pts = [(p, now - p["t"]) for p in trail]
    pts = [(p, age) for p, age in pts if age < TRAIL_POINT_TTL]
    for i in range(1, len(pts)):
        (p0, _), (p1, age1) = pts[i - 1], pts[i]
        alpha = clamp(1 - age1 / TRAIL_POINT_TTL, 0, 1)
        if alpha <= 0:
            continue
        thickness = max(1, int(10 * alpha))
        overlay = img.copy()
        cv2.line(overlay, (int(p0["x"]), int(p0["y"])), (int(p1["x"]), int(p1["y"])),
                 (255, 255, 255), thickness, cv2.LINE_AA)
        cv2.line(overlay, (int(p0["x"]), int(p0["y"])), (int(p1["x"]), int(p1["y"])),
                 (180, 130, 255), max(1, thickness // 2), cv2.LINE_AA)
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    return [p for p, age in pts]


def point_segment_distance(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab_len2 = abx * abx + aby * aby
    t = 0.0 if ab_len2 == 0 else clamp((apx * abx + apy * aby) / ab_len2, 0, 1)
    cx, cy = ax + abx * t, ay + aby * t
    return math.hypot(px - cx, py - cy)


def rounded_rect(img, pt1, pt2, color, radius=14, alpha=1.0):
    x1, y1 = pt1
    x2, y2 = pt2
    overlay = img.copy()
    cv2.rectangle(overlay, (x1 + radius, y1), (x2 - radius, y2), color, -1)
    cv2.rectangle(overlay, (x1, y1 + radius), (x2, y2 - radius), color, -1)
    for cx, cy in [(x1 + radius, y1 + radius), (x2 - radius, y1 + radius),
                   (x1 + radius, y2 - radius), (x2 - radius, y2 - radius)]:
        cv2.circle(overlay, (cx, cy), radius, color, -1, cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


# ----------------------------------------------------------------------------
# Game
# ----------------------------------------------------------------------------
class FruitSliceGame:
    def __init__(self):
        self.fruits = []
        self.halves = []
        self.particles = []
        self.floaters = []
        self.trail = deque(maxlen=TRAIL_MAX_POINTS)
        self.score = 0
        self.lives = STARTING_LIVES
        self.best = 0
        self.state = "start"   # start | playing | over
        self.last_spawn = 0.0
        self.start_time = 0.0
        self.combo = 0
        self.combo_timer = 0.0

    # ---- lifecycle ----
    def reset(self):
        self.fruits.clear()
        self.halves.clear()
        self.particles.clear()
        self.floaters.clear()
        self.trail.clear()
        self.score = 0
        self.lives = STARTING_LIVES
        self.last_spawn = time.time()
        self.start_time = time.time()
        self.combo = 0
        self.combo_timer = 0.0
        self.state = "playing"

    def game_over(self):
        if self.state == "over":
            return
        self.state = "over"
        self.best = max(self.best, self.score)

    # ---- spawning ----
    def maybe_spawn(self):
        now = time.time()
        elapsed = now - self.start_time
        interval = max(MIN_SPAWN_INTERVAL, BASE_SPAWN_INTERVAL - elapsed * 0.01)
        if now - self.last_spawn < interval:
            return
        if len([f for f in self.fruits]) >= MAX_FRUITS_ON_SCREEN:
            return
        self.last_spawn = now
        self.spawn_fruit()

    def spawn_fruit(self):
        ft = random.choice(FRUIT_TYPES)
        r = int(ft["r"] * random.uniform(0.9, 1.15))
        x = random.uniform(r + 20, FRAME_W - r - 20)
        y = random.uniform(r + 120, FRAME_H - r - 40)
        speed = random.uniform(40, 100)
        ang = random.uniform(0, 2 * math.pi)
        life = random.uniform(*FRUIT_LIFETIME_RANGE)
        self.fruits.append(dict(
            type=ft["name"], color=ft["color"], accent=ft["accent"],
            x=x, y=y, r=r, vx=math.cos(ang) * speed, vy=math.sin(ang) * speed,
            life=life, max_life=life, points=ft["points"],
            seed=random.random(), seed_int=random.randint(0, 100000),
            spawn_t=0.0, spawn_dur=0.25, scale=0.0,
        ))

    # ---- update ----
    def update(self, dt):
        if self.state != "playing":
            return
        self.maybe_spawn()
        self.combo_timer -= dt
        if self.combo_timer <= 0:
            self.combo = 0

        for f in self.fruits:
            f["spawn_t"] = min(f["spawn_t"] + dt, f["spawn_dur"])
            f["scale"] = self._ease_out_back(f["spawn_t"] / f["spawn_dur"])
            f["life"] -= dt
            f["x"] += f["vx"] * dt
            f["y"] += f["vy"] * dt
            r = f["r"]
            if f["x"] - r < 10:
                f["x"] = r + 10
                f["vx"] *= -1
            if f["x"] + r > FRAME_W - 10:
                f["x"] = FRAME_W - r - 10
                f["vx"] *= -1
            if f["y"] - r < 90:
                f["y"] = r + 90
                f["vy"] *= -1
            if f["y"] + r > FRAME_H - 10:
                f["y"] = FRAME_H - r - 10
                f["vy"] *= -1

        missed = [f for f in self.fruits if f["life"] <= 0]
        for f in missed:
            self.lives -= 1
            self.floaters.append(self._make_floater(f["x"], f["y"], "missed!", (180, 160, 170), 20))
        if missed:
            self.fruits = [f for f in self.fruits if f["life"] > 0]
            if self.lives <= 0:
                self.game_over()

        for h in self.halves:
            h["vy"] += 900 * dt
            h["x"] += h["vx"] * dt
            h["y"] += h["vy"] * dt
            h["life"] -= dt * 0.7
        self.halves = [h for h in self.halves if h["life"] > 0]

        for p in self.particles:
            p["vy"] += 500 * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt * p["decay"]
        self.particles = [p for p in self.particles if p["life"] > 0]

        for fl in self.floaters:
            fl["y"] += fl["vy"] * dt
            fl["life"] -= dt * 1.1
        self.floaters = [fl for fl in self.floaters if fl["life"] > 0]

    @staticmethod
    def _ease_out_back(t):
        c1, c3 = 1.70158, 2.70158
        return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

    def _make_floater(self, x, y, text, color, size):
        return dict(x=x, y=y, text=text, color=color, size=size, life=1.0, vy=-55)

    # ---- slicing ----
    def add_trail_point(self, x, y):
        self.trail.append(dict(x=x, y=y, t=time.time()))

    def check_slices(self):
        if self.state != "playing" or len(self.trail) < 2:
            return
        a, b = self.trail[-2], self.trail[-1]
        seg_angle = math.atan2(b["y"] - a["y"], b["x"] - a["x"])
        for f in list(self.fruits):
            if f["spawn_t"] < f["spawn_dur"]:
                continue
            d = point_segment_distance(f["x"], f["y"], a["x"], a["y"], b["x"], b["y"])
            if d < f["r"] + SLICE_HIT_PADDING:
                self.slice_fruit(f, seg_angle)

    def slice_fruit(self, fruit, dir_angle):
        self.fruits.remove(fruit)
        self.score += fruit["points"]
        self.combo += 1
        self.combo_timer = 0.6

        for _ in range(14):
            ang = dir_angle + random.uniform(-1.4, 1.4)
            speed = random.uniform(160, 480)
            self.particles.append(dict(
                x=fruit["x"], y=fruit["y"], color=fruit["accent"],
                vx=math.cos(ang) * speed, vy=math.sin(ang) * speed,
                size=random.uniform(3, 7), life=1.0, decay=random.uniform(0.9, 1.5),
            ))

        perp = dir_angle + math.pi / 2
        for clip_ang in (perp, perp + math.pi):
            speed = random.uniform(160, 320)
            half = dict(fruit)
            half["vx"] = math.cos(clip_ang) * speed + fruit["vx"] * 0.4
            half["vy"] = math.sin(clip_ang) * speed + fruit["vy"] * 0.4 - 60
            half["clip_angle"] = clip_ang
            half["life"] = 1.0
            self.halves.append(half)

        if self.combo >= 2:
            self.floaters.append(self._make_floater(fruit["x"], fruit["y"] - 40, f"{self.combo}x COMBO!", (150, 90, 255), 26 + self.combo))
        else:
            self.floaters.append(self._make_floater(fruit["x"], fruit["y"] - 30, f"+{fruit['points']}", (90, 190, 100), 22))

    # ---- drawing ----
    def draw(self, img):
        for f in self.fruits:
            draw_fruit(img, f)
        for h in self.halves:
            draw_fruit_half(img, h)
        for p in self.particles:
            draw_particle(img, p)
        for fl in self.floaters:
            draw_floater(img, fl)
        if self.state == "playing":
            self.trail = deque(draw_trail(img, self.trail), maxlen=TRAIL_MAX_POINTS)
        self.draw_hud(img)

    def draw_hud(self, img):
        rounded_rect(img, (14, 14), (170, 58), (240, 250, 255), radius=16, alpha=0.85)
        cv2.putText(img, f"Score {self.score}", (28, 46), FONT, 0.75, (90, 60, 90), 2, cv2.LINE_AA)

        hearts_x = FRAME_W - 20
        for i in range(STARTING_LIVES):
            color = (60, 210, 255) if i < self.lives else (150, 150, 150)
            cv2.circle(img, (hearts_x - i * 34, 36), 13, color, -1, cv2.LINE_AA)
            cv2.circle(img, (hearts_x - i * 34, 36), 13, (255, 255, 255), 2, cv2.LINE_AA)

        if self.state == "start":
            self._center_card(img, "Cute Fruit Slice", "Show your hand & swipe your finger through fruits!",
                               "Press SPACE to start")
        elif self.state == "over":
            self._center_card(img, "Game Over!", f"Score: {self.score}   Best: {self.best}",
                               "Press SPACE to play again  |  Q to quit")

    def _center_card(self, img, title, subtitle, footer):
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (60, 40, 50), -1)
        cv2.addWeighted(overlay, 0.35, img, 0.65, 0, img)

        cx = FRAME_W // 2
        cy = FRAME_H // 2
        rounded_rect(img, (cx - 320, cy - 110), (cx + 320, cy + 110), (250, 250, 255), radius=24, alpha=0.95)

        (tw, _), _ = cv2.getTextSize(title, FONT, 1.3, 3)
        cv2.putText(img, title, (cx - tw // 2, cy - 40), FONT, 1.3, (150, 90, 220), 3, cv2.LINE_AA)

        (sw, _), _ = cv2.getTextSize(subtitle, FONT, 0.65, 1)
        cv2.putText(img, subtitle, (cx - sw // 2, cy + 5), FONT, 0.65, (90, 70, 90), 1, cv2.LINE_AA)

        (fw, _), _ = cv2.getTextSize(footer, FONT, 0.6, 1)
        cv2.putText(img, footer, (cx - fw // 2, cy + 60), FONT, 0.6, (200, 110, 90), 2, cv2.LINE_AA)


# ----------------------------------------------------------------------------
# Hand tracking
# ----------------------------------------------------------------------------
class HandTracker:
    """Wraps MediaPipe Hands and exposes the index fingertip position."""
    INDEX_TIP = 8

    def __init__(self):
        if not hasattr(mp, "solutions"):
            raise RuntimeError(
                "Your installed mediapipe version doesn't include `mp.solutions` "
                "(this API was removed in mediapipe 0.10.30+). "
                "Fix with:  pip install mediapipe==0.10.21"
            )
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            model_complexity=0,
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )
        self.mp_draw = mp.solutions.drawing_utils

    def process(self, rgb_frame):
        """Returns (x, y) pixel coords of the index fingertip, or None."""
        results = self.hands.process(rgb_frame)
        if not results.multi_hand_landmarks:
            return None, None
        hand = results.multi_hand_landmarks[0]
        lm = hand.landmark[self.INDEX_TIP]
        h, w = rgb_frame.shape[:2]
        return (int(lm.x * w), int(lm.y * h)), hand

    def close(self):
        self.hands.close()


# Rainbow palette so every landmark dot gets a distinct, punchy color —
# matches the colorful hand-skeleton look from hand-tracking demos.
LANDMARK_COLORS = [
    (255, 90, 200), (255, 140, 60), (60, 210, 255), (140, 255, 90), (255, 90, 90),
    (255, 200, 40), (90, 255, 180), (200, 90, 255), (60, 160, 255), (255, 120, 200),
    (120, 255, 60), (255, 90, 140), (90, 200, 255), (255, 170, 60), (180, 90, 255),
    (60, 255, 140), (255, 60, 60), (255, 230, 70), (90, 140, 255), (200, 255, 90),
    (255, 90, 255),
]

HAND_CONNECTIONS = mp.solutions.hands.HAND_CONNECTIONS


def draw_hand_skeleton(img, hand_landmarks):
    """Draws the full 21-point hand skeleton with colorful dots and glowing
    connective lines, like the classic MediaPipe hand-landmark visualization."""
    h, w = img.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks.landmark]

    # connections first (drawn underneath the dots)
    for a, b in HAND_CONNECTIONS:
        cv2.line(img, pts[a], pts[b], (255, 255, 255), 2, cv2.LINE_AA)

    # colorful landmark dots
    for i, (x, y) in enumerate(pts):
        color = LANDMARK_COLORS[i % len(LANDMARK_COLORS)]
        cv2.circle(img, (x, y), 9, color, -1, cv2.LINE_AA)
        cv2.circle(img, (x, y), 9, (255, 255, 255), 1, cv2.LINE_AA)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    global SHOW_HAND_SKELETON
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    if not cap.isOpened():
        print("Could not open webcam. Check CAM_INDEX or camera permissions.")
        return

    tracker = HandTracker()
    game = FruitSliceGame()
    bg_canvas = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
    draw_gradient_background(bg_canvas)

    last_time = time.time()
    window_name = "Cute Fruit Slice - Hand Tracking"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    while True:
        ok, cam_frame = cap.read()
        if not ok:
            print("Failed to read frame from webcam.")
            break

        cam_frame = cv2.flip(cam_frame, 1)  # mirror for natural interaction
        cam_frame = cv2.resize(cam_frame, (FRAME_W, FRAME_H))

        rgb = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
        fingertip, hand_landmarks = tracker.process(rgb)

        now = time.time()
        dt = min(now - last_time, 0.033)
        last_time = now

        # compose scene: cute background softly blended with the live camera
        canvas = blend_frame_with_bg(cam_frame, bg_canvas, opacity=0.32)

        if fingertip and game.state == "playing":
            game.add_trail_point(*fingertip)
            game.check_slices()

        game.update(dt)
        game.draw(canvas)

        # draw the full colorful hand skeleton (all 21 landmarks) on top
        if hand_landmarks is not None and SHOW_HAND_SKELETON:
            draw_hand_skeleton(canvas, hand_landmarks)

        # draw fingertip cursor (the "blade")
        if fingertip:
            cv2.circle(canvas, fingertip, 14, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.circle(canvas, fingertip, 5, (150, 90, 255), -1, cv2.LINE_AA)

        cv2.imshow(window_name, canvas)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord('q'), 27):  # q or ESC
            break
        elif key == 32:  # SPACE
            if game.state in ("start", "over"):
                game.reset()
        elif key == ord('h'):  # toggle hand skeleton overlay
            SHOW_HAND_SKELETON = not SHOW_HAND_SKELETON

    cap.release()
    tracker.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
