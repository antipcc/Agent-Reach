"""《两分钟告诉你 Skill 是什么？》逐帧渲染 + 合成配乐。

依赖：numpy pillow imageio-ffmpeg；先运行 music.py 生成 music.wav。
"""
import math
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1920, 1080, 30, 120.0
BAR = 110  # 电影遮幅
CJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
LAT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# 主题色：墨紫夜色 → 手艺陶土橙 → 琥珀金，薄荷绿表示“技能已加载”
BG1 = np.array([10, 7, 22])
BG2 = np.array([36, 18, 52])
CORAL = (234, 128, 94)
AMBER = (255, 196, 112)
MINT = (112, 232, 186)
MUTED = (150, 138, 176)
WHITE = (248, 244, 250)
BLACK = (0, 0, 0)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ss(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def win(t, a, b, fi=0.7, fo=0.7):
    return ss((t - a) / fi) * ss((b - t) / fo)


def lerp(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def rise(t, a, d=16):
    return d * (1 - ss((t - a) / 0.9))


def back_out(x):
    x = clamp(x)
    c = 1.4
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------- 文字 ----------
@lru_cache(maxsize=None)
def font(kind, size):
    if kind == "lat":
        return ImageFont.truetype(LAT, size)
    return ImageFont.truetype(CJK, size, index=1 if kind == "mono" else 0)


@lru_cache(maxsize=4096)
def text_img(s, size, color, kind="cjk", spacing=0, glow=18):
    f = font(kind, size)
    if spacing:
        widths = [f.getlength(c) for c in s]
        tw = int(sum(widths) + spacing * (len(s) - 1)) + 2
    else:
        tw = int(f.getlength(s)) + 2
    th = int(size * 1.3)
    pad = max(glow * 3, 4)
    im = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if spacing:
        x = pad
        for c, w in zip(s, widths):
            d.text((x, pad), c, font=f, fill=color + (255,))
            x += w + spacing
    else:
        d.text((pad, pad), s, font=f, fill=color + (255,))
    g = im.filter(ImageFilter.GaussianBlur(glow)) if glow else None
    return im, g, pad


def with_alpha(im, a):
    if a >= 0.999:
        return im
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return out


def paste(dst, im, x, y):
    x, y = int(x), int(y)
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(im.width, W - x), min(im.height, H - y)
    if ex <= sx or ey <= sy:
        return
    dst.alpha_composite(im.crop((sx, sy, ex, ey)), (x + sx, y + sy))


def text(dst, s, size, color, cx, cy, a, kind="cjk", spacing=0, glow=18, glow_a=0.7, left=False):
    if a <= 0.01 or not s:
        return
    im, g, pad = text_img(s, size, color, kind, spacing, glow)
    x = cx - pad if left else cx - im.width / 2
    y = cy - im.height / 2
    if g is not None:
        paste(dst, with_alpha(g, a * glow_a), x, y)
    paste(dst, with_alpha(im, a), x, y)


def tw(s, size, kind="cjk"):
    return font(kind, size).getlength(s)


# ---------- 预计算 ----------
LW, LH = 480, 270
yy, xx = np.mgrid[0:LH, 0:LW].astype(np.float32)
GRAD = (BG1 + (BG2 - BG1) * (1 - yy / LH)[..., None] ** 1.6).astype(np.float32)
vy, vx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.55 * (((vx - W / 2) / (W * 0.62)) ** 2 + ((vy - H / 2) / (H * 0.75)) ** 2)).clip(0.25, 1)[..., None]
del vy, vx
GRAIN = [np.random.default_rng(i).normal(0, 3.2, (H, W, 1)).astype(np.float32) for i in range(6)]

rng = np.random.default_rng(11)
NS = 300
STAR_X = rng.uniform(0, W * 1.4, NS)
STAR_Y = rng.uniform(0, H, NS)
STAR_Z = rng.uniform(0.2, 1.0, NS)
STAR_P = rng.uniform(0, 6.28, NS)
NP = 170
PX = rng.uniform(0, W, NP)
PY0 = rng.uniform(0, H, NP)
PV = rng.uniform(40, 140, NP)
PC = rng.uniform(0, 1, NP)

# ---------- 分镜数据 ----------
QUESTIONS = ["公司规范？", "报告模板？", "审批流程？", "品牌配色？", "代码风格？", "行业术语？"]
TREE = [("scripts/", "可执行的脚本"), ("references/", "参考资料"), ("assets/", "模板与素材")]
CODE = [
    ("---", MUTED),
    ("name: weekly-report", CORAL),
    ("description: 按公司模板生成每周工作周报，", AMBER),
    ("  当用户提到“周报”时使用。", AMBER),
    ("---", MUTED),
    ("# 步骤", WHITE),
    ("1. 汇总本周的数据与进展", WHITE),
    ("2. 套用 assets/ 中的周报模板", WHITE),
    ("3. 运行 scripts/check.py 检查格式", WHITE),
]
CODE_T0, CPS = 38.2, 15.0
SHELF = ["PPT 制作", "Excel 分析", "PDF 处理", "周报生成", "品牌规范", "代码审查",
         "投标书", "海报设计", "深度调研", "数据可视化", "会议纪要", "合同审阅",
         "邮件回复", "招聘筛选", "财务对账", "客服话术", "产品文档", "测试用例"]
PICK = {1: 60.2, 0: 61.0}
LAYERS = [("① 名称 + 描述", "始终在线 · 每个只占几十个 token"),
          ("② 完整的 SKILL.md", "任务相关时才读取"),
          ("③ 脚本与参考资料", "真正需要时才打开")]
COMPARE = [("Prompt", "一次性的叮嘱", "说完就忘", MUTED),
           ("MCP", "连接工具与数据", "给它手和眼", AMBER),
           ("Skill", "沉淀做事的方法", "给它经验与手艺", MINT)]
ACHIEVE = [
    ("文", "办公文档", "Word · PPT · Excel · PDF"),
    ("品", "品牌一致", "每份产出都符合规范"),
    ("审", "代码审查", "团队标准，自动执行"),
    ("研", "深度调研", "多源检索，成文成报告"),
    ("标", "招投标", "从招标文件到投标书"),
    ("图", "数据可视化", "数据秒变图表"),
    ("创", "创意设计", "海报、动图与生成艺术"),
    ("流", "任何流程", "可重复的，都能沉淀"),
]
AC0, ACSTEP = 90.4, 1.4


def background(t):
    img = GRAD.copy()
    c_int = 0.5 * win(t, 0.3, 21, 2.5, 1.2) + 0.3 * win(t, 52, 78, 1.5, 1.5) + 0.25 * win(t, 89, 106, 1.5, 1.5)
    if c_int > 0.01:
        m = np.exp(-(((xx - LW / 2) / 160) ** 2 + ((yy - LH / 2) / 110) ** 2))
        img += m[..., None] * np.array(CORAL, np.float32) * 0.3 * c_int
    mid = win(t, 21, 52, 1.5, 1.5)
    if mid > 0.01:
        m = np.exp(-(((xx - LW * 0.5) / 220) ** 2 + ((yy - LH * 0.5) / 120) ** 2))
        img += m[..., None] * np.array(AMBER, np.float32) * 0.12 * mid
    s = ss((t - 104) / 12)
    if s > 0.01:
        cy = LH * (1.45 - 0.5 * s)
        m = np.exp(-(((xx - LW / 2) / 260) ** 2 + ((yy - cy) / 150) ** 2))
        img += m[..., None] * np.array(AMBER, np.float32) * 0.85 * s
        img += (yy / LH)[..., None] ** 3 * np.array([70, 30, 12], np.float32) * s
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)


def stars(base, t):
    d = ImageDraw.Draw(base)
    fin = win(t, 0, DUR, 2, 1)
    for i in range(NS):
        z = STAR_Z[i]
        x = (STAR_X[i] - t * 7 * z) % (W * 1.4) - W * 0.2
        y = STAR_Y[i]
        b = (0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 1.3 + STAR_P[i]))) * z * fin
        r = 0.6 + 1.4 * z
        c = tuple(int(v * b * 0.75) for v in lerp(WHITE, AMBER, 0.3))
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)


class G:
    """半分辨率辉光层。"""

    def __init__(self):
        self.im = Image.new("RGB", (W // 2, H // 2), BLACK)
        self.d = ImageDraw.Draw(self.im)

    def ellipse(self, cx, cy, rx, ry, col, a):
        if a > 0.01:
            self.d.ellipse(((cx - rx) / 2, (cy - ry) / 2, (cx + rx) / 2, (cy + ry) / 2), fill=lerp(BLACK, col, clamp(a)))

    def rrect(self, x0, y0, x1, y1, r, col, a, width=0):
        if a > 0.01:
            box = (x0 / 2, y0 / 2, x1 / 2, y1 / 2)
            if width:
                self.d.rounded_rectangle(box, r / 2, outline=lerp(BLACK, col, clamp(a)), width=width)
            else:
                self.d.rounded_rectangle(box, r / 2, fill=lerp(BLACK, col, clamp(a)))

    def poly(self, pts, col, a, width=0):
        if a > 0.01:
            pts = [(x / 2, y / 2) for x, y in pts]
            if width:
                self.d.polygon(pts, outline=lerp(BLACK, col, clamp(a)), width=width)
            else:
                self.d.polygon(pts, fill=lerp(BLACK, col, clamp(a)))


def A(col, a):
    return col + (int(255 * clamp(a)),)


def hexagon(cx, cy, r):
    return [(cx + r * math.cos(math.radians(60 * k - 90)), cy + r * math.sin(math.radians(60 * k - 90))) for k in range(6)]


def skill_card(od, g, cx, cy, s, a, t):
    """一张发光的技能卡（开场主视觉）。"""
    w, h = 150 * s, 196 * s
    g.rrect(cx - w * 0.7, cy - h * 0.7, cx + w * 0.7, cy + h * 0.7, 30, CORAL, 0.8 * a)
    od.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 18 * s, fill=A((28, 16, 40), 0.95 * a), outline=A(CORAL, a), width=4)
    od.rounded_rectangle((cx - w / 2 + 20 * s, cy - h / 2 + 24 * s, cx + w / 2 - 20 * s, cy - h / 2 + 58 * s), 8, fill=A(CORAL, 0.9 * a))
    for k in range(4):
        ly = cy - h / 2 + (86 + k * 24) * s
        lw = (w - 40 * s) * (0.95 - 0.15 * (k % 2))
        od.rounded_rectangle((cx - w / 2 + 20 * s, ly, cx - w / 2 + 20 * s + lw, ly + 8 * s), 4, fill=A(MUTED, 0.8 * a))
    # 右上角的星芒
    sx, sy, sr = cx + w / 2 - 6 * s, cy - h / 2 + 6 * s, (18 + 5 * math.sin(t * 3)) * s
    od.polygon([(sx, sy - sr), (sx + sr * 0.25, sy - sr * 0.25), (sx + sr, sy), (sx + sr * 0.25, sy + sr * 0.25),
                (sx, sy + sr), (sx - sr * 0.25, sy + sr * 0.25), (sx - sr, sy), (sx - sr * 0.25, sy - sr * 0.25)], fill=A(AMBER, a))
    g.ellipse(sx, sy, sr * 1.6, sr * 1.6, AMBER, a)


def agent_core(od, g, ov, cx, cy, a, t, col=CORAL):
    cr = 96 * (0.93 + 0.07 * math.sin(t * 2))
    g.ellipse(cx, cy, cr * 1.3, cr * 1.3, col, a)
    od.ellipse((cx - 90, cy - 90, cx + 90, cy + 90), fill=A((30, 16, 44), 0.95 * a), outline=A(col, a), width=3)
    text(ov, "Agent", 44, WHITE, cx, cy, a, kind="lat", glow=12)


def frame(i):
    t = i / FPS
    base = background(t)
    stars(base, t)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov, "RGBA")
    g = G()

    # ===== 1. 0–8s 开场：一张技能卡被点亮 =====
    a = win(t, 0.4, 8.2, 0.9, 0.9)
    if a > 0:
        s = 0.7 + 0.3 * back_out((t - 0.4) / 1.4)
        skill_card(od, g, W / 2, 360 + 8 * math.sin(t * 1.4), s, a, t)
        text(ov, "两分钟告诉你", 44, lerp(WHITE, AMBER, 0.35), W / 2, 590 + rise(t, 1.6, 12), win(t, 1.6, 7.8))
        text(ov, "Skill 是什么？", 110, WHITE, W / 2, 700 + rise(t, 2.4), win(t, 2.4, 7.8), glow=24)

    # ===== 2. 8–21s 痛点：聪明，但不懂你的做事方式 =====
    a = win(t, 8.4, 21, 0.9, 0.8)
    if a > 0:
        cx, cy = W / 2, 540
        agent_core(od, g, ov, cx, cy, a, t)
        text(ov, "Agent 已经很聪明", 60, WHITE, W / 2, 230 + rise(t, 8.6), win(t, 8.6, 20.6), glow=20)
        for k, q in enumerate(QUESTIONS):
            qa = a * ss((t - 12.6 - k * 0.45) / 0.7)
            if qa <= 0:
                continue
            ang = math.radians(-150 + k * 60 + 6 * math.sin(t * 0.6 + k))
            qx, qy = cx + 420 * math.cos(ang), cy + 210 * math.sin(ang) + 6 * math.sin(t * 1.1 + k)
            wq = tw(q, 32) + 48
            od.rounded_rectangle((qx - wq / 2, qy - 30, qx + wq / 2, qy + 30), 30, fill=A((40, 26, 58), 0.9 * qa), outline=A(MUTED, 0.8 * qa), width=2)
            text(ov, q, 32, lerp(WHITE, MUTED, 0.3), qx, qy, qa, glow=0)
        text(ov, "但它不懂 你的 做事方式", 40, lerp(WHITE, CORAL, 0.25), W / 2, 900, win(t, 13.3, 17.0))
        text(ov, "每一次，你都要从头解释一遍", 40, lerp(WHITE, CORAL, 0.25), W / 2, 900, win(t, 17.3, 20.6))

    # ===== 3. 21–37s 定义：技能包就是一个文件夹 =====
    a = win(t, 21.2, 37.2, 0.9, 0.8)
    if a > 0:
        text(ov, "Skill：一个装进 Agent 的专业技能包", 54, WHITE, W / 2, 200 + rise(t, 21.4), win(t, 21.4, 36.8), glow=22)
        # 文件夹
        fx, fy = 540, 560
        fa = a * ss((t - 22) / 0.8)
        g.rrect(fx - 150, fy - 110, fx + 150, fy + 110, 30, CORAL, 0.6 * fa)
        od.polygon([(fx - 140, fy - 100), (fx - 50, fy - 100), (fx - 30, fy - 75), (fx + 140, fy - 75), (fx + 140, fy + 100), (fx - 140, fy + 100)],
                   fill=A((52, 26, 40), fa), outline=A(CORAL, fa), width=4)
        od.rounded_rectangle((fx - 140, fy - 50, fx + 140, fy + 100), 10, fill=A(CORAL, 0.85 * fa))
        text(ov, "技能包", 36, (40, 20, 30), fx, fy + 25, fa, glow=0)
        # 目录树
        x0, y0, step = 800, 360, 100
        ta = a * ss((t - 23.0) / 0.6)
        text(ov, "weekly-report/", 44, AMBER, x0, y0, ta, kind="mono", glow=12, left=True)
        items = [("SKILL.md", "说明书：何时用、怎么做")] + TREE
        for k, (name, desc) in enumerate(items):
            tk = 24.6 + k * 1.7
            ia = a * ss((t - tk) / 0.6)
            if ia <= 0:
                continue
            y = y0 + (k + 1) * step
            od.line((x0 + 22, y - step + 34, x0 + 22, y), fill=A(MUTED, 0.7 * ia), width=3)
            od.line((x0 + 22, y, x0 + 60, y), fill=A(MUTED, 0.7 * ia), width=3)
            hot = k == 0
            col = MINT if hot else WHITE
            if hot:
                g.ellipse(x0 + 140, y, 140, 30, MINT, 0.35 * ia)
            text(ov, name, 40, col, x0 + 78 - 8 * (1 - ia), y, ia, kind="mono", glow=10 if hot else 0, left=True)
            text(ov, desc, 32, lerp(WHITE, MUTED, 0.4), x0 + 430, y, ia, glow=0, left=True)
        text(ov, "本质上，它就是一个文件夹", 40, lerp(WHITE, AMBER, 0.3), W / 2, 905, win(t, 32.0, 36.8))

    # ===== 4. 37–52s SKILL.md 解剖 =====
    a = win(t, 37.2, 52.2, 0.9, 0.8)
    if a > 0:
        X0, Y0, X1, Y1 = 400, 250, 1420, 820
        g.rrect(X0, Y0, X1, Y1, 30, CORAL, 0.25 * a)
        od.rounded_rectangle((X0, Y0, X1, Y1), 22, fill=A((22, 14, 34), 0.96 * a), outline=A(CORAL, 0.6 * a), width=2)
        od.rounded_rectangle((X0, Y0, X1, Y0 + 56), 22, fill=A((40, 24, 56), a))
        od.rectangle((X0, Y0 + 34, X1, Y0 + 56), fill=A((40, 24, 56), a))
        for k, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            od.ellipse((X0 + 26 + k * 30, Y0 + 20, X0 + 42 + k * 30, Y0 + 36), fill=A(c, a))
        text(ov, "SKILL.md", 28, lerp(WHITE, MUTED, 0.3), (X0 + X1) / 2, Y0 + 28, a, kind="mono", glow=0)
        typed = max(0, (t - CODE_T0) * CPS)
        cur = None
        for k, (line, col) in enumerate(CODE):
            if typed <= 0:
                break
            n = min(len(line), int(typed))
            typed -= len(line) + 3  # 行尾稍作停顿
            y = Y0 + 100 + k * 54
            text(ov, line[:n], 34, col, X0 + 50, y, a, kind="mono", glow=8 if col in (CORAL, AMBER) else 0, glow_a=0.5, left=True)
            cur = (X0 + 50 + tw(line[:n], 34, "mono") + 4, y)
        if cur and (int(t * 2.2) % 2 == 0 or t < CODE_T0 + 9):
            od.rectangle((cur[0], cur[1] - 20, cur[0] + 16, cur[1] + 20), fill=A(MINT, a))
        # 右侧标注
        for (ya, yb, title, sub, tt) in [(Y0 + 80, Y0 + 340, "元数据", "告诉它何时该用", 46.6), (Y0 + 370, Y0 + 560, "正文", "一步步的操作手册", 47.6)]:
            la = a * ss((t - tt) / 0.7)
            if la <= 0:
                continue
            bx = X1 + 30
            od.line((bx, ya, bx + 14, ya), fill=A(MINT, la), width=3)
            od.line((bx + 14, ya, bx + 14, yb), fill=A(MINT, la), width=3)
            od.line((bx, yb, bx + 14, yb), fill=A(MINT, la), width=3)
            g.rrect(bx, ya, bx + 20, yb, 10, MINT, 0.5 * la)
            text(ov, title, 38, MINT, bx + 44, (ya + yb) / 2 - 26, la, glow=12, left=True)
            text(ov, sub, 28, WHITE, bx + 44, (ya + yb) / 2 + 22, la, glow=0, left=True)
        text(ov, "一段元数据 + 一份清晰的操作手册", 40, lerp(WHITE, AMBER, 0.3), W / 2, 905, win(t, 48.2, 51.8))

    # ===== 5. 52–66s 技能书架：按需匹配 =====
    a = win(t, 52.2, 66.2, 0.9, 0.8)
    if a > 0:
        text(ov, "它可以同时装上很多 Skill", 54, WHITE, W / 2, 225 + rise(t, 52.4), win(t, 52.4, 58.0, 0.9, 0.6), glow=20)
        qa = win(t, 58.4, 65.8, 0.8, 0.8)
        if qa > 0:
            q = "“帮我把这份数据做成季度汇报 PPT”"
            wq = tw(q, 38) + 80
            g.rrect(W / 2 - wq / 2, 190, W / 2 + wq / 2, 262, 36, AMBER, 0.45 * qa)
            od.rounded_rectangle((W / 2 - wq / 2, 190, W / 2 + wq / 2, 262), 36, fill=A((58, 36, 40), 0.95 * qa), outline=A(AMBER, qa), width=2)
            text(ov, q, 38, WHITE, W / 2, 226, qa, glow=0)
        for k, name in enumerate(SHELF):
            c, r = k % 6, k // 6
            cx, cy = W / 2 + (c - 2.5) * 236, 420 + r * 132
            ca = a * ss((t - 52.8 - k * 0.09) / 0.6)
            if ca <= 0:
                continue
            pick = PICK.get(k)
            hot = ss((t - pick) / 0.6) if pick else 0
            dim = 1 - 0.6 * ss((t - 59.8) / 0.8) * (1 - hot)
            s = 1 + 0.12 * back_out((t - pick) / 0.6) if pick and t > pick else 1
            w2, h2 = 104 * s, 50 * s
            col = lerp(MUTED, MINT, hot)
            if hot:
                g.rrect(cx - w2 - 10, cy - h2 - 10, cx + w2 + 10, cy + h2 + 10, 24, MINT, 0.8 * hot * a)
            od.rounded_rectangle((cx - w2, cy - h2, cx + w2, cy + h2), 14, fill=A((34, 22, 50), 0.95 * ca * dim), outline=A(col, ca * dim), width=3 if hot else 2)
            text(ov, name, 30, lerp(WHITE, MINT, hot), cx, cy, ca * dim, glow=10 if hot else 0)
            if hot:
                text(ov, "已加载", 22, MINT, cx + w2 - 36, cy - h2 - 16, a * hot, glow=0)
        text(ov, "只看名字和描述，它就知道该用哪一个", 40, lerp(WHITE, MINT, 0.3), W / 2, 870, win(t, 61.2, 65.8))

    # ===== 6. 66–78s 渐进式加载 =====
    a = win(t, 66.2, 78.2, 0.9, 0.8)
    if a > 0:
        text(ov, "渐进式加载", 60, WHITE, W / 2, 205 + rise(t, 66.4), win(t, 66.4, 77.8), glow=22)
        for k, (l, r) in enumerate(LAYERS):
            la = a * ss((t - 67.0 - k * 1.7) / 0.7)
            if la <= 0:
                continue
            y = 370 + k * 160
            col = lerp(MINT, CORAL, k / 2)
            x0, x1 = 430 + k * 40, 1490 - k * 40
            g.rrect(x0, y - 60, x1, y + 60, 30, col, 0.35 * la)
            od.rounded_rectangle((x0, y - 60 + 10 * (1 - la), x1, y + 60), 20, fill=A((30, 18, 46), 0.95 * la), outline=A(col, la), width=3)
            text(ov, l, 40, col, x0 + 50, y, la, glow=10, left=True)
            text(ov, r, 30, WHITE, x1 - 50 - tw(r, 30), y, la, glow=0, left=True)
        # 一粒光向下探入更深层
        p = ss((t - 72.0) / 2.4)
        if 72 < t < 77.8:
            py = 300 + p * 440
            g.ellipse(W / 2, py, 26, 26, WHITE, a)
            od.ellipse((W / 2 - 7, py - 7, W / 2 + 7, py + 7), fill=A(WHITE, a))
        text(ov, "装上一百个技能，也不会让它变慢", 40, lerp(WHITE, AMBER, 0.3), W / 2, 880, win(t, 73.8, 77.8))

    # ===== 7. 78–89s 对比 =====
    a = win(t, 78.2, 89.2, 0.9, 0.8)
    if a > 0:
        text(ov, "它和 Prompt、MCP 有什么不同？", 54, WHITE, W / 2, 205 + rise(t, 78.4), win(t, 78.4, 88.8), glow=20)
        for k, (name, l1, l2, col) in enumerate(COMPARE):
            ca = a * ss((t - 79.0 - k * 1.0) / 0.7)
            if ca <= 0:
                continue
            cx = W / 2 + (k - 1) * 450
            hot = k == 2
            x0, y0, x1, y1 = cx - 190, 350 - 12 * (1 - ca), cx + 190, 730
            if hot:
                g.rrect(x0 - 10, y0 - 10, x1 + 10, y1 + 10, 34, MINT, (0.55 + 0.2 * math.sin(t * 2)) * ca)
            od.rounded_rectangle((x0, y0, x1, y1), 24, fill=A((30, 18, 46), 0.95 * ca), outline=A(col, ca), width=4 if hot else 2)
            text(ov, name, 62, col, cx, 450, ca, kind="lat", glow=18 if hot else 0)
            od.line((cx - 60, 520, cx + 60, 520), fill=A(col, 0.6 * ca), width=2)
            text(ov, l1, 36, WHITE, cx, 585, ca, glow=0)
            text(ov, l2, 30, lerp(WHITE, MUTED, 0.4), cx, 645, ca, glow=0)
        text(ov, "MCP 让它拿得到，Skill 让它做得好", 42, lerp(WHITE, MINT, 0.3), W / 2, 880, win(t, 83.0, 88.8))

    # ===== 8. 89–106s 能力解锁 =====
    a = win(t, 89.2, 106.2, 0.9, 0.8)
    if a > 0:
        text(ov, "Skill 为 Agent 解锁的能力", 52, lerp(WHITE, AMBER, 0.35), W / 2, 185, win(t, 89.4, 101.8, 0.9, 0.6))
        dim = 1 - 0.72 * ss((t - 101.6) / 0.8)
        for k, (ch, name, desc) in enumerate(ACHIEVE):
            tk = AC0 + k * ACSTEP
            p = (t - tk) / 0.7
            if p <= 0:
                continue
            cx, cy = W / 2 + (k % 4 - 1.5) * 390, 400 + (k // 4) * 315
            sc = back_out(p)
            ba = a * ss(p) * dim
            breathe = 0.5 + 0.5 * math.sin(t * 1.6 + k)
            r = 88 * sc
            if 0 < t - tk < 1.2:
                q = (t - tk) / 1.2
                rr = 90 + 110 * ss(q)
                g.poly(hexagon(cx, cy, rr), AMBER, (1 - q) * a, width=4)
                od.polygon(hexagon(cx, cy, rr), outline=A(AMBER, 0.8 * (1 - q) * a), width=2)
            g.poly(hexagon(cx, cy, r * 1.08), CORAL, ba * (0.35 + 0.2 * breathe))
            od.polygon(hexagon(cx, cy, r), fill=A((30, 16, 42), 0.95 * ba), outline=A(AMBER, ba), width=4)
            od.polygon(hexagon(cx, cy, r * 0.82), outline=A(MINT, 0.45 * ba), width=2)
            text(ov, ch, int(70 * max(sc, 0.3)), WHITE, cx, cy + 2, ba, glow=10, glow_a=0.9)
            ta = a * ss((t - tk - 0.3) / 0.6) * dim
            text(ov, name, 34, AMBER, cx, cy + 128, ta, glow=0)
            text(ov, desc, 24, lerp(WHITE, MUTED, 0.3), cx, cy + 170, ta * 0.9, glow=0)
        text(ov, "一次编写 · 处处复用 · 团队共享", 66, WHITE, W / 2, H / 2 + 10, win(t, 102.2, 105.8, 0.9, 0.7), glow=26)

    # ===== 9. 106–120s 终章 =====
    s = ss((t - 105.5) / 3)
    if s > 0:
        for k in range(NP):
            y = (PY0[k] - (t - 105.5) * PV[k]) % (H + 100)
            x = PX[k] + 20 * math.sin(t * 0.8 + k)
            rr = 1.5 + 2.5 * (PV[k] / 140)
            fa = s * clamp(y / H + 0.2) * win(t, 105.5, DUR, 1, 1.2)
            g.ellipse(x, y, rr * 2, rr * 2, lerp(AMBER, CORAL, PC[k] * 0.7), fa)
        fy = H * (1.45 - 0.5 * ss((t - 104) / 12))
        if fy < H + 50:
            g.ellipse(W / 2, fy, 900, 4, (255, 225, 170), 0.9 * s)
        text(ov, "2025 年，Agent Skills 诞生，并成为开放标准", 52, WHITE, W / 2, H / 2 - 60, win(t, 106.4, 110.3, 0.9, 0.7), glow=22)
        text(ov, "越来越多的 Agent 平台开始支持", 36, AMBER, W / 2, H / 2 + 20, win(t, 107.2, 110.3, 0.9, 0.7))
        text(ov, "把经验写下来，它就成了 AI 的能力", 64, WHITE, W / 2, H / 2 - 40, win(t, 110.6, 114.5, 0.9, 0.7), glow=24)
        fa = win(t, 114.8, DUR + 0.5, 1.0, 0.1)
        text(ov, "SKILLS", 160, WHITE, W / 2, H / 2 - 70 - rise(t, 114.8, 10), fa, kind="lat", spacing=28, glow=34, glow_a=0.9)
        text(ov, "教 会  A I  一 门 手 艺", 42, AMBER, W / 2, H / 2 + 80, win(t, 115.6, DUR + 0.5, 1.0, 0.1))

    glow = g.im.filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)
    img = ImageChops.add(base, glow)
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    arr = np.asarray(img, np.float32) * VIG + GRAIN[i % 6]
    arr *= win(t, 0, DUR, 0.6, 0.9)
    arr[:BAR] = 0
    arr[H - BAR:] = 0
    return np.clip(arr, 0, 255).astype(np.uint8).tobytes()


if __name__ == "__main__":
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    if len(sys.argv) > 1:  # 预览：python render.py 5 30 60
        for s in sys.argv[1:]:
            Image.frombytes("RGB", (W, H), frame(int(float(s) * FPS))).save(f"preview_{s}.png")
        sys.exit()
    n = int(DUR * FPS)
    p = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", "music.wav", "-c:v", "libx264", "-preset", "slow", "-crf", "22",
                          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                          "-movflags", "+faststart", "skill_in_two_minutes.mp4"], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, buf in enumerate(pool.imap(frame, range(n), chunksize=8)):
            p.stdin.write(buf)
            if k % 300 == 0:
                print(f"frame {k}/{n}", flush=True)
    p.stdin.close()
    p.wait()
