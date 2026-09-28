"""《百年企业曼罗兰》原创配乐合成器 —— 纯 numpy/scipy 生成，无外部采样。

120 BPM，D 大调，I–V–vi–IV 进行。强度随时间不断递增：
  0–6s    冷开场：暗色 Pad + 低频嗡鸣
  6–22s   琶音进入，轻底鼓
  22–39s  贝斯、军鼓、踩镲加入
  39–54s  主旋律，16 分踩镲
  54–62s  上升段：军鼓滚奏加速 + 噪声扫频
  62–72s  高潮 Drop
  72–82s  终章长和弦与余韵
"""
from __future__ import annotations

import sys
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
DUR = 82.0
BEAT = 0.5
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(1844)


def hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def saw(f, t):
    return 2.0 * ((f * t) % 1.0) - 1.0


def env_curve(points):
    """分段线性包络 [(time, value), ...]"""
    ts, vs = zip(*points)
    return np.interp(T, ts, vs)


def place(buf, sig, start):
    i = int(start * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


PROG = [  # D  A  Bm  G
    [50, 57, 62, 66, 69],
    [45, 52, 57, 61, 64],
    [47, 54, 59, 62, 66],
    [43, 50, 55, 59, 62],
]
BASS = [38, 33, 35, 31]


def chord_at(t):
    return int(t // 2.0) % 4


# ---------------------------------------------------------------- Pad
def make_pad():
    L = np.zeros(N)
    R = np.zeros(N)
    for b in range(int(DUR // 2) + 1):
        t0 = b * 2.0
        if t0 >= 72:
            break
        seg_t = np.arange(int(2.05 * SR)) / SR
        e = np.minimum(1, seg_t / 0.05) * np.minimum(1, (2.05 - seg_t) / 0.05)
        for m in PROG[b % 4]:
            f = hz(m)
            for k, d in enumerate((-0.12, -0.05, 0.0, 0.06, 0.13)):
                s = saw(f * 2 ** (d / 12), seg_t + k * 0.13) * e * 0.05
                place(L if k % 2 else R, s, t0)
                place(R if k % 2 else L, s * 0.6, t0)
    # 终章大和弦（D 大调，含高八度）
    seg_t = np.arange(int(10 * SR)) / SR
    e = np.exp(-seg_t / 4.5)
    for m in [38, 50, 57, 62, 66, 69, 74, 78, 81]:
        for k, d in enumerate((-0.1, 0.0, 0.1)):
            s = saw(hz(m) * 2 ** (d / 12), seg_t + k * 0.2) * e * 0.08
            place(L if k != 1 else R, s, 72)
            place(R if k != 1 else L, s * 0.7, 72)
    mix_dark = np.stack([lp(L, 500), lp(R, 500)])
    mix_bright = np.stack([lp(L, 4200), lp(R, 4200)])
    k = env_curve([(0, 0), (22, 0.15), (39, 0.45), (54, 0.55), (61.5, 1), (62, 0.8), (72, 1), (82, 0.6)])
    vol = env_curve([(0, 0), (4, 0.8), (6, 1), (54, 1), (61.4, 1.2), (61.6, 0.15), (62, 1.35), (72, 1.35), (82, 1.3)])
    return (mix_dark * (1 - k) + mix_bright * k) * vol


# ---------------------------------------------------------------- Arp
def make_arp():
    L = np.zeros(N)
    R = np.zeros(N)
    step = BEAT / 4
    seg_t = np.arange(int(0.3 * SR)) / SR
    e = np.exp(-seg_t / 0.07)
    i = 0
    t = 6.0
    while t < 72:
        if 61.5 <= t < 62:
            t += step
            i += 1
            continue
        notes = PROG[chord_at(t)][1:]
        pattern = [0, 1, 2, 3, 2, 1, 3, 2]
        m = notes[pattern[i % 8]] + 12
        s = (saw(hz(m), seg_t) * 0.6 + np.sign(np.sin(2 * np.pi * hz(m) * seg_t)) * 0.4) * e * 0.09
        place(L if i % 2 else R, s, t)
        place(R if i % 2 else L, s * 0.35, t)
        t += step
        i += 1
    cutoff_env = env_curve([(6, 0.2), (22, 0.5), (54, 0.8), (62, 1.0), (72, 1.0)])
    lo = np.stack([lp(L, 900), lp(R, 900)])
    hi = np.stack([lp(L, 5000), lp(R, 5000)])
    vol = env_curve([(0, 0), (6, 0), (10, 0.7), (22, 0.9), (54, 1), (72, 1), (72.01, 0)])
    return (lo * (1 - cutoff_env) + hi * cutoff_env) * vol


# ---------------------------------------------------------------- Drums
def kick(g=1.0):
    t = np.arange(int(0.45 * SR)) / SR
    f = 45 + 120 * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    click = rng.standard_normal(len(t)) * np.exp(-t / 0.004) * 0.3
    return (np.sin(ph) * np.exp(-t / 0.18) + click) * g


def snare(g=1.0):
    t = np.arange(int(0.3 * SR)) / SR
    noise = bp(rng.standard_normal(len(t)), 1200, 8000) * np.exp(-t / 0.08)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)
    return (noise * 0.8 + tone * 0.5) * g


def hat(g=1.0):
    t = np.arange(int(0.08 * SR)) / SR
    return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t / 0.02) * g


def crash(g=1.0, length=3.0):
    t = np.arange(int(length * SR)) / SR
    return hp(rng.standard_normal(len(t)), 4000) * np.exp(-t / (length / 4)) * g


def impact(g=1.0):
    t = np.arange(int(4 * SR)) / SR
    f = 30 + 90 * np.exp(-t / 0.25)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 1.2)
    noise = lp(rng.standard_normal(len(t)), 900) * np.exp(-t / 0.4) * 0.6
    return (boom + noise) * g


def make_drums():
    M = np.zeros(N)
    W = np.zeros(N)  # 立体声宽度通道（镲片）
    for b in range(int(DUR / BEAT)):
        t = b * BEAT
        beat_in_bar = b % 4
        # 底鼓
        if 12 <= t < 22:
            place(M, kick(0.55), t)
        elif 22 <= t < 61.5 or 62 <= t < 72:
            place(M, kick(0.95 if t >= 39 else 0.8), t)
        # 军鼓 2、4 拍
        if (22 <= t < 54 or 62 <= t < 72) and beat_in_bar in (1, 3):
            place(M, snare(0.55 if t < 39 else 0.7), t)
        # 踩镲
        if 22 <= t < 39:
            place(W, hat(0.25), t + BEAT / 2)
        elif 39 <= t < 61.5 or 62 <= t < 72:
            for k in range(4):
                place(W, hat(0.22 if k % 2 else 0.12), t + k * BEAT / 4)
    # 军鼓滚奏加速
    t = 54.0
    while t < 61.5:
        if t < 58:
            step = BEAT / 2
        elif t < 60:
            step = BEAT / 4
        else:
            step = BEAT / 8
        g = 0.2 + 0.6 * (t - 54) / 7.5
        place(M, snare(g), t)
        t += step
    # 镲 & 冲击
    for ct in (6, 22, 39, 54):
        place(W, crash(0.35), ct)
    for ct in (62, 72):
        place(W, crash(0.6, 5.0), ct)
        place(M, impact(0.9), ct)
    place(M, impact(0.5), 6)
    # 章节节点的小镲
    for ct in (42, 45, 48, 51):
        place(W, crash(0.18, 1.5), ct)
    return M, W


# ---------------------------------------------------------------- Bass
def make_bass():
    B = np.zeros(N)
    seg_t = np.arange(int(0.26 * SR)) / SR
    t = 22.0
    i = 0
    while t < 72:
        if 61.5 <= t < 62:
            t += BEAT / 2
            i += 1
            continue
        root = BASS[chord_at(t)]
        m = root + (12 if (t >= 62 and i % 2) else 0)
        f = hz(m)
        e = np.minimum(1, seg_t / 0.005) * np.exp(-seg_t / 0.18)
        s = (np.sin(2 * np.pi * f * seg_t) + 0.35 * saw(f, seg_t)) * e * 0.35
        place(B, s, t)
        t += BEAT / 2
        i += 1
    return lp(B, 900)


# ---------------------------------------------------------------- Lead
MELODY = [
    [(69, 1), (66, 0.5), (69, 0.5), (74, 2)],
    [(73, 1), (71, 1), (69, 1), (64, 1)],
    [(74, 1.5), (73, 0.5), (71, 1), (66, 1)],
    [(67, 1), (69, 1), (71, 1), (74, 1)],
]


def make_lead():
    L = np.zeros(N)
    for start, end, oct_ in ((39, 54, 0), (62, 72, 12)):
        t = float(start)
        while t < end:
            phrase = MELODY[chord_at(t)]
            for m, beats in phrase:
                d = beats * BEAT
                seg_t = np.arange(int((d + 0.25) * SR)) / SR
                vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * seg_t) * np.minimum(1, seg_t / 0.3)
                f = hz(m + oct_)
                e = np.minimum(1, seg_t / 0.02) * np.clip((d + 0.2 - seg_t) / 0.2, 0, 1)
                s = sum(saw(f * vib * 2 ** (dd / 12), seg_t) for dd in (-0.08, 0, 0.08)) / 3
                place(L, s * e * 0.13, t)
                t += d
    return lp(L, 3800)


# ---------------------------------------------------------------- FX
def make_fx():
    F = np.zeros(N)
    # 开场低频嗡鸣
    drone = np.sin(2 * np.pi * hz(26) * T) + 0.3 * np.sin(2 * np.pi * hz(38) * T)
    F += drone * env_curve([(0, 0), (2, 0.1), (6, 0.12), (8, 0.05), (22, 0)])
    # 开场反向上升
    F += lp(rng.standard_normal(N), 2500) * env_curve([(0, 0), (4.5, 0), (5.95, 0.25), (6.0, 0)])
    # 高潮前噪声扫频 + 音高上升
    seg = (T >= 54) & (T < 61.6)
    x = rng.standard_normal(N) * seg
    lo_ = lp(x, 800)
    hi_ = hp(x, 3000)
    k = np.clip((T - 54) / 7.5, 0, 1)
    F += (lo_ * (1 - k) + hi_ * k) * k * 0.18
    rt = np.clip(T - 54, 0, None)
    f = hz(50) * 2 ** (rt / 7.5 * 2)
    F += saw(1, np.cumsum(f) / SR) * seg * k * 0.06
    return F


def reverb(x, secs=2.6):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((2, n)) * np.exp(-t / (secs / 5))
    ir[:, : int(0.01 * SR)] = 0
    ir = np.stack([lp(ir[0], 6000), lp(ir[1], 6000)])
    ir /= np.sqrt((ir**2).sum(axis=1, keepdims=True))
    return np.stack([fftconvolve(x[0], ir[0])[:N], fftconvolve(x[1], ir[1])[:N]])


def main(out: str):
    pad = make_pad()
    arp = make_arp()
    drums_m, drums_w = make_drums()
    bass = make_bass()
    lead = make_lead()
    fx = make_fx()

    # 底鼓侧链压缩：Drop 段 Pad 随拍“呼吸”
    ph = (T % BEAT) / BEAT
    pump = 1 - env_curve([(0, 0), (38.9, 0), (39, 0.35), (61.5, 0.45), (62, 0.6), (72, 0.6), (72.01, 0)]) * np.exp(-ph * 6)
    pad = pad * pump

    lead_st = np.stack([lead * 0.9, lead])
    dry = pad + arp + lead_st + np.stack([drums_m, drums_m]) + np.stack([bass, bass]) + np.stack([fx, fx])
    dry[0] += drums_w * 0.8
    dry[1] += np.roll(drums_w, int(0.011 * SR)) * 0.8
    send = pad * 0.6 + arp * 0.7 + lead_st * 0.8 + np.stack([drums_m, drums_m]) * 0.12
    wet = reverb(send)
    mix = dry + wet * 0.35
    mix = np.tanh(mix * 1.3)
    fade = env_curve([(0, 0), (0.3, 1), (DUR - 3, 1), (DUR, 0)])
    mix *= fade
    mix /= np.abs(mix).max() / 0.89
    pcm = (mix.T * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "manroland_score.wav")
