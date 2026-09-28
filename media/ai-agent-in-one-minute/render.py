"""《一分钟告诉你 AI Agent 是什么？》逐帧渲染 + 合成配乐。

依赖：numpy pillow imageio-ffmpeg；先运行 music.py 生成 music.wav。
"""
import math
import subprocess
from functools import lru_cache
from multiprocessing import Pool

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1920, 1080, 30, 60.0
BAR = 110  # 电影遮幅
CJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
LAT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# 主题色：深空午夜蓝 → 智能青 → 黎明金
NAVY = np.array([6, 10, 31])
NAVY2 = np.array([12, 22, 58])
CYAN = (62, 230, 255)
BLUE = (79, 123, 255)
GOLD = (255, 200, 87)
WHITE = (245, 247, 255)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ss(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def win(t, a, b, fi=0.7, fo=0.7):
    return ss((t - a) / fi) * ss((b - t) / fo)


def lerp(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def back_out(x):
    x = clamp(x)
    c = 1.4
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------- 文字 ----------
@lru_cache(maxsize=None)
def font(path, size):
    return ImageFont.truetype(path, size)


@lru_cache(maxsize=256)
def text_img(text, size, color, latin=False, spacing=0, glow=18):
    f = font(LAT if latin else CJK, size)
    if spacing:
        widths = [f.getbbox(c)[2] for c in text]
        tw = sum(widths) + spacing * (len(text) - 1)
    else:
        tw = f.getbbox(text)[2]
    th = int(size * 1.3)
    pad = glow * 3
    im = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if spacing:
        x = pad
        for c, w in zip(text, widths):
            d.text((x, pad), c, font=f, fill=color + (255,))
            x += w + spacing
    else:
        d.text((pad, pad), text, font=f, fill=color + (255,))
    g = im.filter(ImageFilter.GaussianBlur(glow)) if glow else None
    return im, g


def with_alpha(im, a):
    if a >= 0.999:
        return im
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return out


def paste(dst, im, x, y):
    """alpha 合成，允许越界。"""
    x, y = int(x), int(y)
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(im.width, W - x), min(im.height, H - y)
    if ex <= sx or ey <= sy:
        return
    dst.alpha_composite(im.crop((sx, sy, ex, ey)), (x + sx, y + sy))


def text(dst, s, size, color, cx, cy, a, latin=False, spacing=0, glow=18, glow_a=0.7):
    if a <= 0.01:
        return
    im, g = text_img(s, size, color, latin, spacing, glow)
    x, y = cx - im.width / 2, cy - im.height / 2
    if g is not None:
        paste(dst, with_alpha(g, a * glow_a), x, y)
    paste(dst, with_alpha(im, a), x, y)


# ---------- 预计算 ----------
LW, LH = 480, 270
yy, xx = np.mgrid[0:LH, 0:LW].astype(np.float32)
GRAD = (NAVY + (NAVY2 - NAVY) * (1 - yy / LH)[..., None] ** 1.5).astype(np.float32)

vy, vx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.55 * (((vx - W / 2) / (W * 0.62)) ** 2 + ((vy - H / 2) / (H * 0.75)) ** 2)).clip(0.25, 1)[..., None]
del vy, vx
GRAIN = [np.random.default_rng(i).normal(0, 3.2, (H, W, 1)).astype(np.float32) for i in range(6)]

rng = np.random.default_rng(42)
NS = 320
STAR_X = rng.uniform(0, W * 1.6, NS)
STAR_Y = rng.uniform(0, H, NS)
STAR_Z = rng.uniform(0.2, 1.0, NS)
STAR_P = rng.uniform(0, 6.28, NS)
NP = 160
PX = rng.uniform(0, W, NP)
PY0 = rng.uniform(0, H, NP)
PV = rng.uniform(40, 140, NP)
PC = rng.uniform(0, 1, NP)

# ---------- 分镜数据 ----------
MILESTONES = [
    ("1950", "图灵提问：机器能思考吗？"),
    ("1956", "达特茅斯会议，“人工智能”诞生"),
    ("1966", "ELIZA，人类第一次与机器对话"),
    ("1997", "深蓝击败国际象棋世界冠军"),
    ("2016", "AlphaGo 攻克围棋"),
    ("2022", "ChatGPT，大模型走向每个人"),
    ("2023", "大模型学会使用工具，Agent 兴起"),
    ("2025", "Agent 元年：写代码、做研究、用电脑"),
]
TL0, TLSTEP, TLGAP = 17.4, 2.0, 560

ACHIEVE = [
    ("研", "科学发现", "蛋白质、新材料、新药加速问世"),
    ("码", "软件开发", "一句话，生成一个应用"),
    ("医", "医疗健康", "辅助诊断，守护更多生命"),
    ("学", "教育", "每个人都有专属导师"),
    ("译", "沟通", "跨越语言的边界"),
    ("效", "生产力", "重复交给机器，创造还给人"),
    ("惠", "普惠", "顶尖能力流向每一个人"),
    ("探", "探索", "从深海到深空"),
]
AC0, ACSTEP = 34.4, 1.35

LOOP = [("感知", -90), ("规划", 0), ("行动", 90), ("反思", 180)]


def cam_x(t):
    """时间轴段的摄像机位置（世界坐标）。"""
    if t < TL0:
        return 0.0
    k = (t - TL0) / TLSTEP
    i = int(k)
    if i >= len(MILESTONES) - 1:
        return (len(MILESTONES) - 1) * TLGAP
    f = k - i
    return (i + ss(clamp((f - 0.45) / 0.55))) * TLGAP


def background(t):
    img = GRAD.copy()
    # 中心青色光晕（开场、智能体循环）
    c_int = 0.55 * win(t, 0.3, 16.5, 2.5, 1.2) + 0.25 * win(t, 33, 49, 1.5, 1.5)
    if c_int > 0.01:
        m = np.exp(-(((xx - LW / 2) / 150) ** 2 + ((yy - LH / 2) / 110) ** 2))
        img += m[..., None] * np.array(CYAN, np.float32) * 0.35 * c_int
    # 时间轴：由蓝向金的色温推移
    tl = win(t, 16, 33, 1, 1)
    if tl > 0.01:
        k = clamp((t - 17) / 15)
        col = np.array(lerp(BLUE, GOLD, k), np.float32)
        m = np.exp(-(((yy - LH * 0.52) / 60) ** 2))
        img += m[..., None] * col * 0.18 * tl
    # 终章：地平线日出
    s = ss((t - 47.5) / 9)
    if s > 0.01:
        cy = LH * (1.45 - 0.5 * s)
        m = np.exp(-(((xx - LW / 2) / 260) ** 2 + ((yy - cy) / 150) ** 2))
        img += m[..., None] * np.array(GOLD, np.float32) * 0.85 * s
        img += (yy / LH)[..., None] ** 3 * np.array([60, 30, 10], np.float32) * s
    img = np.clip(img, 0, 255).astype(np.uint8)
    return Image.fromarray(img).resize((W, H), Image.BILINEAR)


def stars(base, t):
    d = ImageDraw.Draw(base)
    cx = cam_x(t)
    fin = win(t, 0.0, 60, 2.0, 1.0)
    for i in range(NS):
        z = STAR_Z[i]
        x = (STAR_X[i] - t * 6 * z - cx * 0.25 * z) % (W * 1.6) - W * 0.3
        y = STAR_Y[i]
        b = (0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 1.3 + STAR_P[i]))) * z * fin
        r = 0.6 + 1.4 * z
        c = lerp(WHITE, CYAN, 0.3)
        c = tuple(int(v * b * 0.8) for v in c)
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)


def hexagon(cx, cy, r):
    return [(cx + r * math.cos(math.radians(60 * k - 90)), cy + r * math.sin(math.radians(60 * k - 90))) for k in range(6)]


def frame(i):
    t = i / FPS
    base = background(t)
    stars(base, t)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow = Image.new("RGB", (W // 2, H // 2), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    od = ImageDraw.Draw(ov, "RGBA")

    # ===== 第一幕 0–6s：一粒光被点亮 =====
    a = win(t, 0.4, 6.4, 0.8, 0.9)
    if a > 0:
        pulse = 1 + 0.12 * math.sin(t * 2.4)
        r = (6 + 16 * ss((t - 0.4) / 2.5)) * pulse
        cx, cy = W / 2, H / 2 - 150
        gd.ellipse(((cx - r * 3) / 2, (cy - r * 3) / 2, (cx + r * 3) / 2, (cy + r * 3) / 2), fill=lerp((0, 0, 0), CYAN, a))
        gd.ellipse(((cx - 420 * a) / 2, (cy - 3) / 2, (cx + 420 * a) / 2, (cy + 3) / 2), fill=lerp((0, 0, 0), CYAN, 0.8 * a))
        od.ellipse((cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5), fill=WHITE + (int(255 * a),))
        text(ov, "一分钟告诉你", 44, lerp(WHITE, CYAN, 0.35), W / 2, H / 2 + 5 - 12 * (1 - ss((t - 1.2) / 1)), win(t, 1.2, 5.8))
        text(ov, "AI Agent 是什么？", 104, WHITE, W / 2, H / 2 + 115 - 16 * (1 - ss((t - 2.0) / 1)), win(t, 2.0, 5.8), glow=24)

    # ===== 第二幕 6–16s：它不只是会聊天 =====
    text(ov, "它不只是会聊天", 76, WHITE, W / 2, H / 2 - 20, win(t, 6.4, 9.4))
    text(ov, "它会自己把事情做完", 40, CYAN, W / 2, H / 2 + 70, win(t, 7.4, 9.4))
    a = win(t, 9.4, 16.3, 0.9, 0.8)
    if a > 0:
        cx, cy, R = W / 2, 520, 235
        od.ellipse((cx - R, cy - R, cx + R, cy + R), outline=CYAN + (int(90 * a),), width=2)
        # 核心
        cr = 92 * (0.9 + 0.1 * math.sin(t * 2))
        gd.ellipse(((cx - cr) / 2, (cy - cr) / 2, (cx + cr) / 2, (cy + cr) / 2), fill=lerp((0, 0, 0), BLUE, a))
        od.ellipse((cx - 88, cy - 88, cx + 88, cy + 88), fill=(10, 20, 60, int(230 * a)), outline=CYAN + (int(255 * a),), width=3)
        text(ov, "Agent", 44, WHITE, cx, cy, a, latin=True, glow=12)
        # 光脉冲沿环流动：感知 → 规划 → 行动 → 反思
        ang = -90 + (t - 10.0) * 110
        px, py = cx + R * math.cos(math.radians(ang)), cy + R * math.sin(math.radians(ang))
        for k in range(10):
            aa = math.radians(ang - k * 4)
            qx, qy = cx + R * math.cos(aa), cy + R * math.sin(aa)
            rr = 9 - k * 0.7
            gd.ellipse(((qx - rr * 2) / 2, (qy - rr * 2) / 2, (qx + rr * 2) / 2, (qy + rr * 2) / 2), fill=lerp((0, 0, 0), CYAN, a * (1 - k / 10)))
        od.ellipse((px - 6, py - 6, px + 6, py + 6), fill=WHITE + (int(255 * a),))
        for j, (name, deg) in enumerate(LOOP):
            na = a * ss((t - 9.8 - j * 0.55) / 0.6)
            if na <= 0:
                continue
            nx, ny = cx + R * math.cos(math.radians(deg)), cy + R * math.sin(math.radians(deg))
            diff = abs(((ang - deg + 180) % 360) - 180)
            hot = math.exp(-(diff / 28) ** 2) if t > 10 else 0
            nr = 58 * (0.8 + 0.2 * back_out((t - 9.8 - j * 0.55) / 0.7)) + 6 * hot
            col = lerp(CYAN, GOLD, hot)
            gd.ellipse(((nx - nr * 1.2) / 2, (ny - nr * 1.2) / 2, (nx + nr * 1.2) / 2, (ny + nr * 1.2) / 2), fill=lerp((0, 0, 0), col, na * (0.35 + 0.65 * hot)))
            od.ellipse((nx - nr, ny - nr, nx + nr, ny + nr), fill=(8, 16, 48, int(235 * na)), outline=col + (int(255 * na),), width=3)
            text(ov, name, 38, WHITE, nx, ny, na, glow=0)
        text(ov, "给它一个目标，它会理解、拆解、调用工具，然后自主完成", 36, lerp(WHITE, CYAN, 0.2), W / 2, 905, win(t, 11.2, 15.9))

    # ===== 第三幕 16–33s：一条通往今天的路 =====
    a = win(t, 16.2, 32.9, 0.8, 0.8)
    if a > 0:
        text(ov, "一 条 通 往 今 天 的 路", 40, lerp(WHITE, GOLD, 0.2), W / 2, 200, win(t, 16.3, 32.8, 1.0, 0.8))
        cx = cam_x(t)
        ly = 560
        n = len(MILESTONES)
        # 发光的时间线（逐段着色）
        reveal = (t - TL0 + 0.8) / TLSTEP * TLGAP
        x0w, x1w = -700, min((n - 1) * TLGAP + 700, reveal + 200)
        seg = 40
        xw = x0w
        while xw < x1w:
            k = clamp(xw / ((n - 1) * TLGAP))
            col = lerp(BLUE, GOLD, k)
            sx = W / 2 + xw - cx
            fade = clamp(1 - (xw - reveal) / 200) if xw > reveal else 1
            if -50 < sx < W + 50:
                od.line((sx, ly, sx + seg, ly), fill=col + (int(200 * a * fade),), width=3)
                gd.line((sx / 2, ly / 2, (sx + seg) / 2, ly / 2), fill=lerp((0, 0, 0), col, 0.6 * a * fade), width=3)
            xw += seg
        for j, (yr, label) in enumerate(MILESTONES):
            tj = TL0 + j * TLSTEP
            appear = ss((t - tj + 0.6) / 0.8)
            if appear <= 0:
                continue
            sx = W / 2 + j * TLGAP - cx
            if not -400 < sx < W + 400:
                continue
            focus = math.exp(-((sx - W / 2) / 300) ** 2)
            ma = a * appear * (0.35 + 0.65 * focus)
            col = lerp(CYAN, GOLD, j / (n - 1))
            r = 9 + 7 * focus
            gd.ellipse(((sx - r * 3) / 2, (ly - r * 3) / 2, (sx + r * 3) / 2, (ly + r * 3) / 2), fill=lerp((0, 0, 0), col, ma))
            od.ellipse((sx - r, ly - r, sx + r, ly + r), fill=WHITE + (int(255 * ma),))
            text(ov, yr, 92, col, sx, ly - 105 - 12 * (1 - appear), ma, latin=True, glow=22)
            text(ov, label, 36, WHITE, sx, ly + 88, ma, glow=0)

    # ===== 第四幕 33–49s：成就解锁 =====
    a = win(t, 33.2, 48.9, 0.8, 0.7)
    if a > 0:
        text(ov, "它为世界解锁的成就", 50, lerp(WHITE, GOLD, 0.35), W / 2, 185, win(t, 33.4, 45.9, 0.9, 0.6))
        dim = 1 - 0.7 * ss((t - 45.6) / 0.8)
        for k, (ch, name, desc) in enumerate(ACHIEVE):
            tk = AC0 + k * ACSTEP
            p = (t - tk) / 0.7
            if p <= 0:
                continue
            col_i, row = k % 4, k // 4
            cx, cy = W / 2 + (col_i - 1.5) * 390, 400 + row * 315
            sc = back_out(p)
            ba = a * ss(p) * dim
            breathe = 0.5 + 0.5 * math.sin(t * 1.6 + k)
            r = 88 * sc
            # 解锁瞬间的金色冲击波
            if 0 < t - tk < 1.2:
                q = (t - tk) / 1.2
                rr = 90 + 110 * ss(q)
                gd.polygon([(x / 2, y / 2) for x, y in hexagon(cx, cy, rr)], outline=lerp((0, 0, 0), GOLD, (1 - q) * a), width=4)
                od.polygon(hexagon(cx, cy, rr), outline=GOLD + (int(200 * (1 - q) * a),), width=2)
            gd.polygon([(x / 2, y / 2) for x, y in hexagon(cx, cy, r * 1.08)], fill=lerp((0, 0, 0), GOLD, ba * (0.35 + 0.2 * breathe)))
            od.polygon(hexagon(cx, cy, r), fill=(12, 18, 50, int(240 * ba)), outline=GOLD + (int(255 * ba),), width=4)
            od.polygon(hexagon(cx, cy, r * 0.82), outline=CYAN + (int(110 * ba),), width=2)
            text(ov, ch, int(70 * max(sc, 0.3)), WHITE, cx, cy + 2, ba, glow=10, glow_a=0.9)
            ta = a * ss((t - tk - 0.3) / 0.6) * dim
            text(ov, name, 34, GOLD, cx, cy + 128, ta, glow=0)
            text(ov, desc, 24, lerp(WHITE, CYAN, 0.15), cx, cy + 170, ta * 0.9, glow=0)
        text(ov, "而这，只是开始", 84, WHITE, W / 2, H / 2 + 10, win(t, 46.0, 48.8, 0.9, 0.7), glow=26)

    # ===== 第五幕 49–60s：日出 =====
    s = ss((t - 48.5) / 3)
    if s > 0:
        # 上升的光粒子
        for k in range(NP):
            y = (PY0[k] - (t - 48.5) * PV[k]) % (H + 100)
            x = PX[k] + 20 * math.sin(t * 0.8 + k)
            col = lerp(GOLD, CYAN, PC[k] * 0.6)
            rr = 1.5 + 2.5 * (PV[k] / 140)
            fa = s * clamp(y / H + 0.2) * win(t, 48.5, 60, 1, 1.2)
            gd.ellipse(((x - rr * 2) / 2, (y - rr * 2) / 2, (x + rr * 2) / 2, (y + rr * 2) / 2), fill=lerp((0, 0, 0), col, fa))
        # 地平线变形光斑
        fy = H * (1.45 - 0.5 * ss((t - 47.5) / 9)) * (H / H)
        if fy < H + 50:
            fl = s * 0.9
            gd.ellipse(((W / 2 - 900) / 2, (fy - 4) / 2, (W / 2 + 900) / 2, (fy + 4) / 2), fill=lerp((0, 0, 0), (255, 225, 170), fl))
        text(ov, "从回答问题，到完成任务", 70, WHITE, W / 2, H / 2 - 40, win(t, 49.4, 53.1, 0.9, 0.7), glow=24)
        text(ov, "它不取代人，而是放大每一个人", 62, WHITE, W / 2, H / 2 - 40, win(t, 53.4, 56.6, 0.9, 0.7), glow=24)
        fa = win(t, 56.8, 60.5, 1.0, 0.1)
        text(ov, "AI AGENT", 150, WHITE, W / 2, H / 2 - 70 - 10 * (1 - ss((t - 56.8) / 1.5)), fa, latin=True, spacing=22, glow=34, glow_a=0.9)
        text(ov, "未 来 ， 已 经 开 始", 42, GOLD, W / 2, H / 2 + 75, win(t, 57.6, 60.5, 1.0, 0.1))

    glow = glow.filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)
    img = ImageChops.add(base, glow)
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    arr = np.asarray(img, np.float32) * VIG + GRAIN[i % 6]
    arr *= win(t, 0, 60, 0.6, 0.9)  # 首尾淡入淡出
    arr[:BAR] = 0
    arr[H - BAR:] = 0
    return np.clip(arr, 0, 255).astype(np.uint8).tobytes()


if __name__ == "__main__":
    import sys
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    if len(sys.argv) > 1:  # 预览若干时刻：python render.py 3 12 25
        for s in sys.argv[1:]:
            Image.frombytes("RGB", (W, H), frame(int(float(s) * FPS))).save(f"preview_{s}.png")
        sys.exit()
    n = int(DUR * FPS)
    p = subprocess.Popen([ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", "music.wav", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
                          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                          "-movflags", "+faststart", "ai_agent_in_one_minute.mp4"], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, buf in enumerate(pool.imap(frame, range(n), chunksize=8)):
            p.stdin.write(buf)
            if k % 150 == 0:
                print(f"frame {k}/{n}", flush=True)
    p.stdin.close()
    p.wait()
