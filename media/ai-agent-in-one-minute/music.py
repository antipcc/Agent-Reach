"""原创配乐：80 BPM，C 大调 I–V–vi–IV，60 秒，平缓上扬、充满希望。"""
import wave
import numpy as np

SR = 44100
DUR = 60.0
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


# 和弦：(低音, 铺底音)
C = (36, [60, 64, 67, 72])
G = (43, [55, 59, 62, 67])
Am = (45, [57, 60, 64, 69])
F = (41, [53, 57, 60, 65])
prog = [C, G, Am, F] * 5
prog[-1] = C  # 最后一小节回到主和弦
arp_idx = [0, 1, 2, 3, 2, 1, 2, 3]

melody = [  # (音, 起拍, 时值) 每 4 小节循环
    [(76, 0, 1.5), (74, 1.5, .5), (72, 2, 2)],
    [(74, 0, 1.5), (76, 1.5, .5), (79, 2, 2)],
    [(81, 0, 1.5), (79, 1.5, .5), (76, 2, 2)],
    [(77, 0, 1), (76, 1, 1), (72, 2, 2)],
]

for b, (root, notes) in enumerate(prog):
    t0 = b * BAR
    last = b == len(prog) - 1
    # 铺底
    pgain = 0.5 if b < 2 else 0.42
    for m in notes:
        add(pad(m, BAR * (1.8 if last else 1)), t0, pgain * (1.3 if last else 1), pan=0)
    # 分解和弦
    if 2 <= b < 19:
        g = 0.14 if b < 6 else 0.17
        for k, idx in enumerate(arp_idx):
            add(pluck(notes[idx] + 12), t0 + k * BEAT / 2, g * (1.0 if k % 2 == 0 else 0.75),
                pan=-0.35 if k % 2 == 0 else 0.35)
    # 低音
    if 6 <= b < 19:
        add(bass(root, BAR * 0.9), t0, 0.32)
    # 鼓
    if 8 <= b < 16 or 17 <= b < 19:
        beats = [0, 2] if b < 11 else [0, 1, 2, 3]
        for k in beats:
            add(kick(), t0 + k * BEAT, 0.34 if b >= 11 else 0.26)
    # 主旋律
    if 11 <= b < 19:
        for m, st, du in melody[(b - 11) % 4]:
            add(bell(m, du * BEAT), t0 + st * BEAT, 0.16, pan=0.1)
    if last:
        for m in (72, 79, 84):
            add(bell(m, 3), t0, 0.12)

# 开场的一声"点亮"，与画面光点同步
add(bell(84, 2), 0.6, 0.14)
add(bell(91, 2), 0.6, 0.06)
# 高潮前的上升气流
add(swell(3.0), 45.0, 0.05)
add(swell(2.0), 31.0, 0.03)

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
