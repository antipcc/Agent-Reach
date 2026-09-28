"""《百年企业曼罗兰》视频渲染器 —— PIL 逐帧绘制，ffmpeg 合成音画。

用法: python video.py score.wav out.mp4
"""
from __future__ import annotations

import math
import random
import subprocess
import sys
from multiprocessing import Pool

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
DUR = 82.0

# 主题配色：曼罗兰红 / 石墨 / 钢灰 / 纸白 + 印刷四色点缀
RED = (226, 0, 26)
RED_D = (120, 0, 14)
GRAPH = (22, 24, 28)
STEEL = (140, 146, 156)
WHITE = (242, 242, 238)
CYAN = (0, 174, 239)
MAGENTA = (236, 0, 140)
YELLOW = (255, 225, 0)

EN_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
EN_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
CN = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
_fonts: dict = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


# ------------------------------------------------------------------ 工具
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_io(x):
    return x * x * (3 - 2 * x)


def col(c, a):
    return tuple(int(v * clamp(a)) for v in c)


def text_c(d, xy, s, f, fill, anchor="mm", spacing=0):
    if spacing:
        total = sum(d.textlength(ch, font=f) for ch in s) + spacing * (len(s) - 1)
        x, y = xy
        if anchor[0] == "m":
            x -= total / 2
        for ch in s:
            d.text((x, y), ch, font=f, fill=fill, anchor="l" + anchor[1])
            x += d.textlength(ch, font=f) + spacing
    else:
        d.text(xy, s, font=f, fill=fill, anchor=anchor)


def cylinder(d, cx, cy, r, ang, c, teeth=0, spokes=6, w=3, hub=True):
    if teeth:
        pts = []
        n = teeth * 4
        for i in range(n):
            a = ang + 2 * math.pi * i / n
            rr = r if (i % 4) in (0, 1) else r * 0.9
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, outline=c, width=w)
    else:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=w)
    ri = r * 0.78
    d.ellipse((cx - ri, cy - ri, cx + ri, cy + ri), outline=col(c, 0.6), width=max(1, w - 1))
    for k in range(spokes):
        a = ang + 2 * math.pi * k / spokes
        d.line((cx + r * 0.16 * math.cos(a), cy + r * 0.16 * math.sin(a),
                cx + ri * math.cos(a), cy + ri * math.sin(a)), fill=col(c, 0.7), width=max(1, w - 1))
    rh = r * 0.14
    if hub:
        d.ellipse((cx - rh, cy - rh, cx + rh, cy + rh), fill=c)


# ------------------------------------------------------------------ 背景
def make_bg():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W * 0.62) / W) ** 2 + ((y - H * 0.5) / H) ** 2)
    base = np.clip(1 - r * 1.3, 0, 1)[..., None]
    c0 = np.array([8, 9, 11], np.float32)
    c1 = np.array(GRAPH, np.float32) * 1.4
    img = c0 + (c1 - c0) * base
    rng = np.random.default_rng(7)
    img += rng.normal(0, 2.2, (H, W, 1))
    return np.clip(img, 0, 255).astype(np.uint8)


BG = None

# ------------------------------------------------------------------ 章节
CHAPTERS = [
    # start, end, year, 标题, 副标题, 视觉
    (6, 12, 1844, "奥格斯堡 · 起点", "莱兴巴赫与布茨接手机械厂，开始制造快速印刷机", "gears"),
    (12, 17, 1871, "奥芬巴赫 · 第二条血脉", "Faber & Schleicher 创立，精密印刷的另一源头", "sheets"),
    (17, 22, 1873, "德国第一台卷筒纸轮转机", "纸带如河，报纸从此以工业速度抵达大众", "web"),
    (22, 27, 1897, "柴油机在奥格斯堡诞生", "鲁道夫·狄塞尔在同源工厂点燃动力革命（MAN 共同基因）", "engine"),
    (27, 31, 1911, "第一台 ROLAND 胶印机", "胶印让色彩与精度进入寻常生活", "offset"),
    (31, 35, 1979, "MAN Roland 合流", "两条百年血脉汇为一体", "merge"),
    (35, 39, 1990, "ROLAND 700 问世", "单张纸胶印的全球标杆", "units"),
    (39, 42, 1995, "报业轮转巨擘", "COLORMAN · GEOMAN · LITHOMAN 印遍全球早报", "news"),
    (42, 45, 2008, "DirectDrive 同步换版", "所有印版同时更换，停机时间被压缩到极限", "plates"),
    (45, 48, 2012, "新生", "单张纸与轮转两大业务各自独立，重获新生", "split"),
    (48, 51, 2016, "ROLAND 700 EVOLUTION", "数字化、自动化的新一代单张纸胶印机", "grid"),
    (51, 54, 2018, "manroland Goss", "与 Goss 合并，轮转印刷走向全球", "globe"),
]
MONTAGE = ["报纸", "书籍", "杂志", "包装", "标签", "海报", "课本", "地图",
           "新闻", "知识", "艺术", "商业", "每一天", "每一页", "每个人", "全世界"]


# ------------------------------------------------------------------ 视觉母题
def v_gears(d, lt, dur, cx, cy):
    a = lt * 0.5
    cylinder(d, cx, cy, 260, a, STEEL, teeth=24, spokes=6, w=4)
    cylinder(d, cx + 260 + 120 - 18, cy - 150, 130, -a * 2 + 0.13, RED, teeth=12, spokes=5, w=4)
    cylinder(d, cx - 190, cy + 250, 90, -a * 2.9, col(STEEL, 0.6), teeth=8, spokes=4, w=3)
    rnd = random.Random(1)
    for i in range(50):
        sx = cx + rnd.uniform(-300, 400)
        sp = rnd.uniform(60, 180)
        ph = rnd.uniform(0, 5)
        y = cy + 350 - ((lt + ph) * sp) % 700
        x = sx + 20 * math.sin(lt * 2 + i)
        r = rnd.uniform(1.5, 3.5)
        d.ellipse((x - r, y - r, x + r, y + r), fill=col((255, 120, 40), 0.9))


def v_sheets(d, lt, dur, cx, cy):
    for i in range(14):
        land = 0.25 * i
        p = ease_out(prog(lt, land, land + 0.6))
        if p <= 0:
            continue
        y = cy + 240 - i * 16 - (1 - p) * 700
        x = cx - 20 + (1 - p) * 200 * (1 if i % 2 else -1)
        tilt = (1 - p) * 30
        c = WHITE if i != 13 else RED
        d.polygon([(x - 260, y - 8 + tilt), (x + 260, y - 8 - tilt), (x + 260, y + 8 - tilt), (x - 260, y + 8 + tilt)],
                  outline=col(c, 0.9), width=2)
    # 顶部一张展开的纸
    top = ease_out(prog(lt, 2.8, 3.6))
    if top > 0:
        x0, y0 = cx - 210, cy - 330
        d.rectangle((x0, y0, x0 + 420, y0 + 300 * top), outline=WHITE, width=2)
        for k in range(int(12 * top)):
            ly = y0 + 30 + k * 22
            d.line((x0 + 30, ly, x0 + 30 + (360 if k % 4 else 200), ly), fill=col(STEEL, 0.7), width=4)


def v_web(d, lt, dur, cx, cy):
    speed = 500
    d.rectangle((cx - 700, cy - 36, W + 50, cy + 36), outline=col(WHITE, 0.9), width=2)
    off = (lt * speed) % 180
    for k in range(-5, 14):
        x = cx - 700 + k * 180 + off
        d.rectangle((x, cy - 22, x + 110, cy + 22), fill=col([CYAN, MAGENTA, YELLOW, WHITE][k % 4], 0.7))
    a = lt * speed / 110
    for dx in (-200, 200):
        cylinder(d, cx + dx, cy - 36 - 110, 110, a, STEEL, spokes=8, w=4)
        cylinder(d, cx + dx, cy + 36 + 110, 110, -a, RED, spokes=8, w=4)
    for k in range(20):
        y = cy - 300 + k * 30
        x = (lt * 1400 + k * 311) % (W + 400) - 200
        if abs(y - cy) > 280:
            d.line((x, y, x + 120, y), fill=col(RED, 0.4), width=2)


def v_engine(d, lt, dur, cx, cy):
    rpm = 4.0 + lt * 1.2
    a = lt * rpm * 2 * math.pi / 2
    crank_r = 70
    px = cx
    wy = cy + 200
    cylinder(d, px, wy, 150, a, STEEL, spokes=6, w=4)
    kx, ky = px + crank_r * math.cos(a), wy + crank_r * math.sin(a)
    rod = 260
    py = ky - math.sqrt(max(rod**2 - (kx - px) ** 2, 1))
    d.rectangle((px - 100, cy - 360, px + 100, cy + 30), outline=col(WHITE, 0.8), width=3)
    d.rectangle((px - 90, py - 70, px + 90, py), fill=RED)
    d.line((px, py - 20, kx, ky), fill=WHITE, width=10)
    d.ellipse((kx - 12, ky - 12, kx + 12, ky + 12), fill=WHITE)
    # 点火脉冲
    ph = (a / (2 * math.pi)) % 1
    if ph > 0.7 or ph < 0.05:
        g = 1 - abs(((ph + 0.3) % 1) - 0.1) / 0.25
        rr = 60 + 200 * (1 - g)
        d.ellipse((px - rr, cy - 360 - rr * 0.5, px + rr, cy - 360 + rr * 0.5), outline=col((255, 140, 30), g), width=4)


def v_offset(d, lt, dur, cx, cy):
    a = lt * 2.2
    specs = [(cx - 180, cy - 160, 120, CYAN, "PLATE"), (cx, cy, 120, MAGENTA, "BLANKET"), (cx + 180, cy + 160, 120, STEEL, "IMPRESSION")]
    for i, (x, y, r, c, lbl) in enumerate(specs):
        cylinder(d, x, y, r, a * (1 if i % 2 == 0 else -1), c, spokes=6, w=5)
        d.text((x, y + r + 26), lbl, font=font(EN_REG, 20), fill=col(c, 0.8), anchor="mm")
    for k in range(5):
        x = cx - 380 + k * 60
        y = cy - 330 + (k % 2) * 40
        cylinder(d, x, y, 26, -a * 3 + k, col(YELLOW, 0.8), spokes=3, w=2)
    # 纸张从压印滚筒下方穿过
    p = (lt * 0.7) % 1
    x = cx - 500 + p * 1100
    d.rectangle((x, cy + 290, x + 260, cy + 300), fill=WHITE)
    d.rectangle((x - 1100, cy + 290, x - 840, cy + 300), fill=col(WHITE, 0.5))


def v_merge(d, lt, dur, cx, cy):
    p = ease_io(prog(lt, 0.2, 1.8))
    f = font(EN_BOLD, 120)
    gap = 40 + (1 - p) * 500
    d.text((cx - gap / 2, cy), "MAN", font=f, fill=WHITE if p < 1 else RED, anchor="rm")
    d.text((cx + gap / 2, cy), "ROLAND", font=f, fill=WHITE, anchor="lm")
    if p >= 1:
        q = prog(lt, 1.8, 2.6)
        rr = 100 + q * 900
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=col(RED, 1 - q), width=6)
        d.line((cx - 420, cy + 90, cx - 420 + 840 * ease_out(q), cy + 90), fill=RED, width=6)


def v_units(d, lt, dur, cx, cy):
    n = 7
    w_ = 150
    x0 = cx - (n * w_) / 2 + 60
    colors = [WHITE, CYAN, MAGENTA, YELLOW, (40, 40, 40), RED, STEEL]
    sheet_x = x0 - 200 + ((lt * 600) % (n * w_ + 400))
    for i in range(n):
        x = x0 + i * w_
        lit = prog(lt, 0.3 * i, 0.3 * i + 0.3)
        d.polygon([(x, cy + 120), (x + w_ - 12, cy + 120), (x + w_ - 12, cy - 140), (x + 30, cy - 200), (x, cy - 170)],
                  outline=col(WHITE, 0.4 + 0.5 * lit), width=3)
        cylinder(d, x + w_ / 2 - 6, cy + 30, 46, lt * 4 + i, col(colors[i] if colors[i] != (40, 40, 40) else STEEL, 0.3 + 0.7 * lit), spokes=4, w=3)
        d.rectangle((x + 10, cy - 130, x + w_ - 22, cy - 118), fill=col(colors[i] if i != 4 else STEEL, lit))
    d.rectangle((sheet_x, cy + 130, sheet_x + 120, cy + 138), fill=WHITE)
    d.text((cx, cy + 230), "ROLAND 700", font=font(EN_BOLD, 64), fill=col(RED, prog(lt, 1.5, 2.2)), anchor="mm")


def v_news(d, lt, dur, cx, cy):
    for k in range(34):
        y = cy - 380 + k * 23
        sp = 1600 + (k * 173) % 900
        x = (lt * sp + k * 457) % (W + 800) - 400
        c = RED if k % 7 == 0 else col(WHITE, 0.35)
        d.line((x, y, x + 280 + (k * 37) % 200, y), fill=c, width=3 if k % 7 == 0 else 2)
    f = font(EN_BOLD, 44)
    for i, s in enumerate(["COLORMAN", "GEOMAN", "LITHOMAN"]):
        p = ease_out(prog(lt, 0.3 + 0.4 * i, 0.8 + 0.4 * i))
        d.rectangle((cx - 60 + i * 30 - 10, cy - 120 + i * 90 - 34, cx + 380 + i * 30, cy - 120 + i * 90 + 34), fill=col(GRAPH, p))
        d.text((cx - 60 + i * 30 + (1 - p) * 300, cy - 120 + i * 90), s, font=f, fill=col(WHITE, p), anchor="lm")


def v_plates(d, lt, dur, cx, cy):
    flip = prog(lt, 0.8, 1.6)
    for i in range(2):
        for j in range(4):
            x = cx - 330 + j * 170
            y = cy - 200 + i * 240
            s = abs(math.cos(flip * math.pi))
            c = STEEL if flip < 0.5 else RED
            w2 = 70 * s
            d.rectangle((x - w2, y - 100, x + w2 + 1, y + 100), outline=col(c, 1), width=min(3, int(w2) + 1))
            if flip >= 0.5 and w2 > 12:
                d.rectangle((x - w2 + 10, y - 80, x + w2 - 10, y - 60), fill=col(WHITE, 0.6 * s))
    txt = "00:%02d" % int(max(0, 1.6 - lt) * 60) if lt < 1.6 else "SYNC ✓"
    d.text((cx, cy + 300), "SYNC" if lt >= 1.6 else txt, font=font(EN_BOLD, 56), fill=RED if lt >= 1.6 else WHITE, anchor="mm")


def v_split(d, lt, dur, cx, cy):
    p = ease_out(prog(lt, 0.1, 1.2))
    x0 = cx - 620
    d.line((x0, cy, x0 + 300, cy), fill=WHITE, width=6)
    for sgn, lbl, sub in ((-1, "SHEETFED", "OFFENBACH"), (1, "WEB SYSTEMS", "AUGSBURG")):
        ex = x0 + 300 + 380 * p
        ey = cy + sgn * 220 * p
        d.line((x0 + 300, cy, ex, ey), fill=RED, width=6)
        d.ellipse((ex - 14, ey - 14, ex + 14, ey + 14), fill=RED)
        a = prog(lt, 1.0, 1.6)
        d.text((ex + 30, ey - 18), lbl, font=font(EN_BOLD, 44), fill=col(WHITE, a), anchor="lm")
        d.text((ex + 30, ey + 28), sub, font=font(EN_REG, 26), fill=col(STEEL, a), anchor="lm")


def v_grid(d, lt, dur, cx, cy):
    hy = cy - 80
    for k in range(-14, 15):
        d.line((cx + k * 20, hy, cx + k * 180, H), fill=col(RED, 0.5), width=2)
    for k in range(14):
        z = ((k + lt * 3) % 14) / 14
        y = hy + (H - hy) * z**2
        d.line((cx - 1400 * z - 50, y, cx + 1400 * z + 50, y), fill=col(RED, 0.2 + 0.6 * z), width=2)
    sy = hy - 300 + ((lt * 400) % 300)
    d.line((cx - 400, sy, cx + 400, sy), fill=col(WHITE, 0.6), width=2)
    d.text((cx, hy - 150), "EVOLUTION", font=font(EN_BOLD, 96), fill=WHITE, anchor="mm")


_SPHERE = None


def v_globe(d, lt, dur, cx, cy):
    global _SPHERE
    if _SPHERE is None:
        n = 700
        i = np.arange(n) + 0.5
        phi = np.arccos(1 - 2 * i / n)
        th = np.pi * (1 + 5**0.5) * i
        _SPHERE = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)
    a = lt * 0.8
    R = 330
    x = _SPHERE[:, 0] * math.cos(a) + _SPHERE[:, 2] * math.sin(a)
    z = -_SPHERE[:, 0] * math.sin(a) + _SPHERE[:, 2] * math.cos(a)
    y = _SPHERE[:, 1]
    for k in range(len(x)):
        if z[k] < -0.2:
            continue
        b = 0.3 + 0.7 * (z[k] + 0.2) / 1.2
        px, py = cx + x[k] * R, cy + y[k] * R
        hot = k % 37 == 0
        r = 5 if hot else 2
        c = RED if hot else WHITE
        d.ellipse((px - r, py - r, px + r, py + r), fill=col(c, b))
        if hot:
            pr = 6 + ((lt * 30 + k) % 30)
            d.ellipse((px - pr, py - pr, px + pr, py + pr), outline=col(RED, b * (1 - (pr - 6) / 30)), width=2)
    d.ellipse((cx - R - 20, cy - R - 20, cx + R + 20, cy + R + 20), outline=col(RED, 0.5), width=2)


VIS = {k: globals()["v_" + k] for k in
       ["gears", "sheets", "web", "engine", "offset", "merge", "units", "news", "plates", "split", "grid", "globe"]}


# ------------------------------------------------------------------ HUD
def hud(d, t, year):
    a = prog(t, 6, 7)
    if a <= 0:
        return
    d.text((140, 80), "MANROLAND", font=font(EN_BOLD, 26), fill=col(RED, a), anchor="lm")
    d.text((330, 80), "1844 — 2026", font=font(EN_REG, 24), fill=col(STEEL, a), anchor="lm")
    x0, x1, y = 140, W - 140, H - 70
    d.line((x0, y, x1, y), fill=col(STEEL, 0.4 * a), width=2)
    for c in CHAPTERS:
        x = x0 + (x1 - x0) * (c[2] - 1844) / (2026 - 1844)
        on = year >= c[2]
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=col(RED if on else STEEL, a))
    xp = x0 + (x1 - x0) * clamp((year - 1844) / (2026 - 1844))
    d.line((x0, y, xp, y), fill=col(RED, a), width=4)


# ------------------------------------------------------------------ 帧
def render(fi):
    global BG
    if BG is None:
        BG = make_bg()
    t = fi / FPS
    beat = (t % 0.5) / 0.5
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    base = Image.fromarray(BG)
    flash = 0.0
    shake = (0, 0)
    solid = None

    if t < 6:  # 冷开场
        p1 = prog(t, 0.5, 2.5) * (1 - prog(t, 2.8, 3.2))
        text_c(d, (W / 2, H / 2), "一台机器，能改变世界吗？", font(CN, 56), col(WHITE, p1), spacing=6)
        p2 = ease_out(prog(t, 3.3, 5.2))
        if p2 > 0:
            d.line((W / 2 - 700 * p2, H / 2, W / 2 + 700 * p2, H / 2), fill=RED, width=3)
            text_c(d, (W / 2, H / 2 - 60), "百年企业 · 曼罗兰", font(CN, 64), col(WHITE, prog(t, 4, 5)), spacing=12)
            text_c(d, (W / 2, H / 2 + 60), "MANROLAND · SINCE 1844", font(EN_REG, 28), col(STEEL, prog(t, 4.3, 5.3)), spacing=8)
        fade = 1 - prog(t, 5.6, 6)
        layer = Image.eval(layer, lambda v: int(v * fade)) if fade < 1 else layer
        base = Image.eval(base, lambda v: int(v * (0.4 + 0.6 * prog(t, 0, 5))))
        year = 1844
    elif t < 54:  # 编年史
        idx = next(i for i, c in enumerate(CHAPTERS) if c[0] <= t < c[1])
        s, e, year_c, title, sub, vis = CHAPTERS[idx]
        lt, dur = t - s, e - s
        prev = CHAPTERS[idx - 1][2] if idx else 1800
        roll = ease_out(prog(lt, 0, 0.45))
        year = int(prev + (year_c - prev) * roll)
        intensity = idx / (len(CHAPTERS) - 1)
        VIS[vis](d, lt, dur, 1300, 500)
        # 左侧文字面板
        pin = ease_out(prog(lt, 0.05, 0.55))
        pout = 1 - prog(lt, dur - 0.22, dur)
        a = pin * pout
        dy = (1 - pin) * 50
        d.rectangle((0, 0, 700, H), fill=(0, 0, 0))  # 视觉层遮挡
        d.text((140, 330 + dy), str(year), font=font(EN_BOLD, 200), fill=col(WHITE, a), anchor="ls")
        d.rectangle((146, 360 + dy, 146 + 220 * pin, 368 + dy), fill=col(RED, a))
        text_c(d, (146, 440 + dy), title, font(CN, 50), col(WHITE, a), anchor="ls", spacing=2)
        # 副标题自动换行
        f = font(CN, 28)
        line, lines = "", []
        for ch in sub:
            if d.textlength(line + ch, font=f) > 500:
                lines.append(line)
                line = ""
            line += ch
        lines.append(line)
        for k, ln in enumerate(lines):
            d.text((146, 500 + dy + k * 42), ln, font=f, fill=col(STEEL, a * prog(lt, 0.3, 0.8)), anchor="ls")
        d.text((146, 640 + dy), f"{idx + 1:02d} / {len(CHAPTERS):02d}", font=font(EN_REG, 22), fill=col(RED, a), anchor="ls")
        flash = (1 - prog(lt, 0, 0.12 + 0.1 * intensity)) * (0.25 + 0.5 * intensity)
        if t >= 39:
            flash = max(flash, (1 - beat) ** 6 * 0.12)
            shake = (int(random.Random(fi).uniform(-4, 4) * (1 - beat) ** 4), int(random.Random(fi + 9).uniform(-4, 4) * (1 - beat) ** 4))
    elif t < 62:  # 蒙太奇
        k = int((t - 54) / 0.5)
        lt = (t - 54) % 0.5
        year = 2018 + int(8 * (t - 54) / 8)
        if t >= 61.5:
            solid = (0, 0, 0)
        else:
            solid = [RED, GRAPH, WHITE, RED_D][k % 4] if k % 2 == 0 else (10, 10, 12)
            word = MONTAGE[k]
            fg = GRAPH if solid == WHITE else WHITE
            z = 1 + 0.06 * lt / 0.5
            layer = Image.new("RGB", (W, H), solid)
            d = ImageDraw.Draw(layer)
            text_c(d, (W / 2, H / 2), word, font(CN, int(200 * z)), fg, spacing=20)
            d.text((W / 2, H / 2 + 190), f"{k + 1:02d}", font=font(EN_REG, 24), fill=RED if solid != RED else WHITE, anchor="mm")
            if k % 2:
                for j in range(12):
                    y = (j * 97 + lt * 3000) % H
                    d.line((0, y, W, y), fill=col(RED, 0.25), width=2)
        flash = (1 - prog(lt, 0, 0.08)) * 0.3
    elif t < 72:  # 高潮
        lt = t - 62
        year = 2026
        cx, cy = W / 2, H / 2
        for i in range(8):
            ang = 2 * math.pi * i / 8 + lt * 0.2
            r = 620 + 40 * math.sin(lt * 2 + i)
            cylinder(d, cx + r * math.cos(ang) * 1.3, cy + r * math.sin(ang) * 0.75, 150,
                     lt * (3 + i % 3) * (1 if i % 2 else -1), RED if i % 2 else STEEL, teeth=14 if i % 3 == 0 else 0, w=4)
        rnd = random.Random(62)
        for i in range(260):
            ang = rnd.uniform(0, 2 * math.pi)
            sp = rnd.uniform(200, 1400)
            ph = rnd.uniform(0, 3)
            r = ((lt + ph) % 3) * sp
            x, y = cx + r * math.cos(ang), cy + r * math.sin(ang) * 0.7
            c = [RED, WHITE, CYAN, MAGENTA, YELLOW][i % 5]
            d.line((x, y, x + math.cos(ang) * sp * 0.04, y + math.sin(ang) * sp * 0.03), fill=c, width=3)
        d.ellipse((cx - 460, cy - 260, cx + 460, cy + 260), fill=(0, 0, 0))
        if lt < 3:
            yr = int(1844 + (2026 - 1844) * ease_io(prog(lt, 0, 2.6)))
            d.text((cx, cy), str(yr), font=font(EN_BOLD, 300), fill=WHITE if lt < 2.6 else RED, anchor="mm")
        elif lt < 6.5:
            p = ease_out(prog(lt, 3, 3.5))
            d.text((cx, cy - 40), "182", font=font(EN_BOLD, int(240 + 40 * (1 - p))), fill=RED, anchor="mm")
            text_c(d, (cx, cy + 130), "年 · 把思想印给全世界", font(CN, 56), col(WHITE, p), spacing=10)
        else:
            p = ease_out(prog(lt, 6.5, 7))
            text_c(d, (cx, cy - 30), "未来，正在印刷。", font(CN, int(110 + 20 * (1 - p))), col(WHITE, p), spacing=16)
            d.line((cx - 380 * p, cy + 70, cx + 380 * p, cy + 70), fill=RED, width=5)
        flash = max((1 - prog(lt, 0, 0.5)) * 0.9, (1 - beat) ** 5 * 0.18)
        if lt < 0.1 or 3 <= lt < 3.1 or 6.5 <= lt < 6.6:
            flash = 0.8
        amp = 14 * (1 - beat) ** 3
        rr = random.Random(fi)
        shake = (int(rr.uniform(-amp, amp)), int(rr.uniform(-amp, amp)))
    else:  # 终章
        lt = t - 72
        year = 2026
        cx, cy = W / 2, H / 2 - 30
        p = ease_out(prog(lt, 0.2, 1.8))
        rr = 200 + 50 * math.sin(lt)
        cylinder(d, cx, cy, 480, lt * 0.15, col(RED_D, 0.6 * p), teeth=40, spokes=12, w=2, hub=False)
        d.text((cx, cy), "manroland", font=font(EN_BOLD, int(170 + 20 * (1 - p))), fill=col(RED, p), anchor="mm")
        text_c(d, (cx, cy + 150), "百年企业 · 1844 — ∞", font(CN, 44), col(WHITE, prog(lt, 1.5, 2.5)), spacing=10)
        text_c(d, (cx, cy + 220), "PRINT  ·  POWER  ·  PROGRESS", font(EN_REG, 28), col(STEEL, prog(lt, 2.5, 3.5)), spacing=6)
        flash = (1 - prog(lt, 0, 1.0)) * 0.9
        fade = 1 - prog(t, DUR - 1.8, DUR)
        layer = Image.eval(layer, lambda v: int(v * fade))
        base = Image.eval(base, lambda v: int(v * fade))

    if solid is None:
        if t < 62:
            hud(d, t, year)
        glow = layer.resize((W // 6, H // 6), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR)
        out = ImageChops.screen(base, layer)
        out = ImageChops.add(out, glow, scale=1.0)
    else:
        out = layer if t < 61.5 else Image.new("RGB", (W, H), (0, 0, 0))
    if shake != (0, 0):
        out = ImageChops.offset(out, *shake)
    if flash > 0.01:
        out = Image.blend(out, Image.new("RGB", (W, H), (255, 255, 255)), clamp(flash) * 0.6)
    return out.tobytes()


def main(audio, out):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    n = int(DUR * FPS)
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool() as pool:
        for i, fr in enumerate(pool.imap(render, range(n), chunksize=8)):
            p.stdin.write(fr)
            if i % 300 == 0:
                print(f"frame {i}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
