"""原创配乐：80 BPM，D 大调 vi–IV–I–V，120 秒，温暖、渐进、充满希望。"""
import wave
import numpy as np

SR = 44100
DUR = 120.0
BEAT = 60 / 80          # 0.75s
BAR = 4 * BEAT          # 3s
N = int(SR * DUR)
rng = np.random.default_rng(7)

L = np.zeros(N)
R = np.zeros(N)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 - pan))
    R[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 + pan))


def env_adsr(n, a, r):
    t = np.arange(n) / SR
    e = np.minimum(1, t / a) if a > 0 else np.ones(n)
    rel = int(r * SR)
    if rel:
        e[-rel:] *= np.linspace(1, 0, rel) ** 2
    return e


def pad(m, dur):
    n = int((dur + 1.5) * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for det in (-0.004, 0.0, 0.004):
        f = hz(m) * (1 + det)
        for k, amp in ((1, 1), (2, 0.35), (3, 0.15), (4, 0.06)):
            s += amp * np.sin(2 * np.pi * f * k * t + rng.uniform(0, 6.28))
    s *= 1 + 0.15 * np.sin(2 * np.pi * 0.2 * t)
    return s * env_adsr(n, 1.4, 1.6) / 6


def pluck(m, tau=0.9):
    n = int(2.5 * SR)
    t = np.arange(n) / SR
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return s * np.exp(-t / tau) * np.minimum(1, t / 0.004)


def bell(m, dur):
    n = int((dur + 2.0) * SR)
    t = np.arange(n) / SR
    f = hz(m)
    s = np.sin(2 * np.pi * f * t + 1.1 * np.exp(-t / 0.5) * np.sin(2 * np.pi * 2 * f * t))
    return s * np.exp(-t / 1.6) * np.minimum(1, t / 0.01)


def bass(m, dur):
    n = int((dur + 0.4) * SR)
    t = np.arange(n) / SR
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    return s * env_adsr(n, 0.03, 0.4)


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 45 + 80 * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18)


def swell(dur):
    n = int(dur * SR)
    s = rng.standard_normal(n)
    s = np.convolve(s, np.ones(24) / 24, mode="same")  # 柔化高频
    return s * np.linspace(0, 1, n) ** 3


# 和弦：(低音, 铺底音)  D 大调 Bm–G–D–A
Bm = (47, [59, 62, 66, 71])
G = (43, [55, 59, 62, 67])
D = (38, [57, 62, 66, 69])
A = (45, [57, 61, 64, 69])
prog = [Bm, G, D, A] * 10
prog[-1] = D  # 最后回到主和弦
arp_a = [0, 1, 2, 3, 2, 1, 2, 3]
arp_b = [0, 2, 1, 3, 0, 2, 3, 2]

melody = [  # (音, 起拍, 时值) 每 4 小节循环
    [(78, 0, 1.5), (76, 1.5, .5), (74, 2, 2)],
    [(74, 0, 1), (76, 1, 1), (79, 2, 2)],
    [(81, 0, 1.5), (78, 1.5, .5), (76, 2, 2)],
    [(76, 0, 1), (78, 1, 1), (73, 2, 2)],
]
NB = len(prog)
for b, (root, notes) in enumerate(prog):
    t0 = b * BAR
    last = b == NB - 1
    brk = b in (29, 34)  # 呼吸小节
    for m in notes:
        add(pad(m, BAR * (1.8 if last else 1)), t0, (0.5 if b < 3 else 0.4) * (1.3 if last else 1))
    if 3 <= b < NB - 1:
        g = 0.13 if b < 10 else 0.16
        pat = arp_a if b < 22 else arp_b
        for k, idx in enumerate(pat):
            add(pluck(notes[idx] + 12), t0 + k * BEAT / 2, g * (1.0 if k % 2 == 0 else 0.75),
                pan=-0.35 if k % 2 == 0 else 0.35)
    if 10 <= b < NB - 1:
        add(bass(root, BAR * 0.9), t0, 0.32)
    if 18 <= b < NB - 1 and not brk:
        beats = [0, 2] if b < 26 else [0, 1, 2, 3]
        for k in beats:
            add(kick(), t0 + k * BEAT, 0.34 if b >= 26 else 0.26)
    if 26 <= b < NB - 1 and not brk:
        for m, st, du in melody[(b - 26) % 4]:
            add(bell(m, du * BEAT), t0 + st * BEAT, 0.16, pan=0.1)
    if last:
        for m in (74, 81, 86):
            add(bell(m, 3), t0, 0.12)

# 开场“翻开技能卡”的一声，与画面同步
add(bell(86, 2), 0.6, 0.14)
add(bell(93, 2), 0.6, 0.06)
# 段落前的上升气流
add(swell(3.0), 75.0, 0.04)
add(swell(3.0), 99.0, 0.05)

# 混响：衰减噪声脉冲卷积
def reverb(x, seed):
    r = np.random.default_rng(seed)
    n = int(3.2 * SR)
    t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t / 1.1)
    ir = np.convolve(ir, np.ones(8) / 8, mode="same")
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return y

wetL, wetR = reverb(L, 1), reverb(R, 2)
outL = L * 0.75 + wetL * 0.45
outR = R * 0.75 + wetR * 0.45

t = np.arange(N) / SR
fade = np.minimum(1, t / 0.8) * np.clip((DUR - t) / 3.0, 0, 1)
out = np.stack([outL, outR], 1) * fade[:, None]
out = np.tanh(out / np.max(np.abs(out)) * 1.2) / np.tanh(1.2) * 0.89

with wave.open("music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((out * 32767).astype("<i2").tobytes())
print("music.wav written")
