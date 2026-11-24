"""Build 'The Hibah Files: Case File 01 - Scene 2' multi-cam news edit.

Usage: python3 tools/build.py SRC.mp4 OUT.mp4 FONT_DIR WORK_DIR

- Video: original frames, re-framed per edit decision list via a single
  projective warp (scale / offset / rotation / mild keystone). Hard cuts.
- Graphics: rendered with Pillow per frame, piped as RGBA into ffmpeg.
- Audio: original track untouched, plus synthesized quiet SFX and ambience
  bed mixed underneath (no normalisation, so voice level is unchanged).
"""
import json
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import angles  # noqa: E402

SRC, OUT, FONTS, WORK = sys.argv[1:5]
os.makedirs(WORK, exist_ok=True)

W, H, FPS = 1920, 1080, 30
BLACK = (13, 13, 15)
CHARCOAL = (35, 35, 39)
STEEL = (154, 154, 163)
PAPER = (242, 240, 235)
RED = (239, 59, 80)
AMBER = (224, 165, 38)

ANTON = os.path.join(FONTS, "Anton-Regular.ttf")
MBOLD = os.path.join(FONTS, "Montserrat-Bold.ttf")
MSEMI = os.path.join(FONTS, "Montserrat-SemiBold.ttf")

# ---------------------------------------------------------------- timing
dur = float(json.loads(subprocess.check_output(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", SRC]
))["format"]["duration"])
NF = int(round(dur * FPS))
f = lambda t: int(round(t * FPS))  # noqa: E731

EDL = [  # (start s, end s, angle)
    (0, 8, "wide"), (8, 13, "a1"), (13, 14, "wide"), (14, 20, "a2"), (20, None, "wide"),
]
CARD1 = dict(t0=8.0, t1=13.0, stamp=10.0, side="right", label="CLAIM 01",
             text="TH paid the 2017 Hibah even though its liabilities exceeded "
                  "its assets, contrary to the Tabung Haji Act 1995.")
CARD2 = dict(t0=14.0, t1=20.0, stamp=16.0, side="left", label="CLAIM 02",
             text="The RCI shows there was no misappropriation, ‘tiada sakau’, "
                  "only an overpayment of Hibah.")
LT = dict(t0=1.0, t1=5.0)
FADE = 0.2


# ---------------------------------------------------------------- helpers
def font(path, size):
    return ImageFont.truetype(path, size)


def tracked(draw, xy, text, fnt, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x - tracking


def tracked_width(text, fnt, tracking):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    return sum(d.textlength(c, font=fnt) for c in text) + tracking * (len(text) - 1)


def wrap(text, fnt, maxw):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=fnt) <= maxw:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- layers
def corner_label():
    fnt = font(MBOLD, 24)
    tw = tracked_width("CASE FILE 01", fnt, 6)
    im = Image.new("RGBA", (int(tw) + 44, 52), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, im.height], fill=BLACK + (200,))
    d.rectangle([0, 0, 5, im.height], fill=RED)  # small red edge
    tracked(d, (22, 12), "CASE FILE 01", fnt, RED, 6)
    return im, (60, 46)


def lower_third():
    fn, fr = font(MBOLD, 40), font(MBOLD, 24)
    name, role = "[PRESENTER NAME]", "[ROLE]"
    tw = max(tracked_width(name, fn, 1), tracked_width(role, fr, 3))
    bw, bh = int(tw + 2 * 40 + 12), 124
    im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, bw, bh], fill=CHARCOAL + (240,))
    d.rectangle([0, 0, 11, bh], fill=RED)
    tracked(d, (52, 20), name, fn, PAPER, 1)
    tracked(d, (52, 76), role, fr, STEEL, 3)
    return im, (96, 846)


def card(c):
    cw, pad = 700, 46
    STAMP_ZONE = 128  # reserved space so the stamp never hides the claim text
    fl, ft, fs = font(ANTON, 46), font(MSEMI, 35), font(MBOLD, 18)
    lines = wrap(c["text"], ft, cw - 2 * pad)
    lh = 50
    ch = pad + 60 + 26 + len(lines) * lh + STAMP_ZONE + 30 + pad - 10
    im = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, cw, ch], fill=CHARCOAL + (242,))
    d.rectangle([0, 0, cw, 5], fill=RED)  # thin red top rule
    tracked(d, (pad, pad - 6), c["label"], fl, RED, 4)
    y = pad + 60 + 26
    d.rectangle([pad, y - 18, pad + 64, y - 15], fill=STEEL)
    for ln in lines:
        d.text((pad, y), ln, font=ft, fill=PAPER)
        y += lh
    tracked(d, (pad, ch - pad - 4), "Case File 01, claim wording",
            fs, STEEL, 1)
    if c["side"] == "right":
        x = W - 88 - cw
    else:
        x = 88
    return im, (x, (H - ch) // 2 - 10)


def stamp():
    fnt = font(ANTON, 54)
    text = "UNDER INVESTIGATION"
    tw = tracked_width(text, fnt, 4)
    pw, ph = int(tw + 60), 100
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([3, 3, pw - 4, ph - 4], outline=AMBER, width=6)
    d.rectangle([13, 13, pw - 14, ph - 14], outline=AMBER, width=2)
    tracked(d, (30, 14), text, fnt, AMBER, 4)
    # subtle ink texture: knock out a little alpha with fixed-seed noise
    a = np.array(im)
    rng = np.random.default_rng(7)
    mask = rng.random(a.shape[:2]) < 0.08
    a[..., 3] = np.where(mask, (a[..., 3] * 0.55).astype(np.uint8), a[..., 3])
    im = Image.fromarray(a)
    # rotate -3 degrees (clockwise visual tilt down to the right)
    return im.rotate(-3, resample=Image.BICUBIC, expand=True)


def blit(canvas, layer, xy, alpha=1.0):
    if alpha <= 0:
        return
    if alpha < 1:
        a = np.array(layer)
        a[..., 3] = (a[..., 3].astype(np.float32) * alpha).astype(np.uint8)
        layer = Image.fromarray(a)
    canvas.alpha_composite(layer, (int(round(xy[0])), int(round(xy[1]))))


CL, CL_XY = corner_label()
LT_IM, LT_XY = lower_third()
C1_IM, C1_XY = card(CARD1)
C2_IM, C2_XY = card(CARD2)
ST = stamp()


def stamp_frame(canvas, cim, cxy, t, ts):
    if t < ts:
        return
    k = (t - ts) * FPS  # frames since stamp start
    # slam: big & transparent -> lands at frame 4, tiny settle bounce
    if k < 4:
        sc = 1.55 - 0.57 * ease_out(k / 4)
        al = 0.25 + 0.7 * (k / 4)
    elif k < 6:
        sc = 0.98 + 0.01 * (k - 4)
        al = 0.95
    else:
        sc, al = 1.0, 0.95
    im = ST.resize((max(1, int(ST.width * sc)), max(1, int(ST.height * sc))), Image.BICUBIC)
    # centre of stamp over lower-middle of card
    cx = cxy[0] + cim.width / 2
    cy = cxy[1] + cim.height - 132  # middle of the reserved stamp zone
    blit(canvas, im, (cx - im.width / 2, cy - im.height / 2), al)


def graphics(n):
    t = n / FPS
    cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    blit(cv, CL, CL_XY, ease_out(t / FADE))
    if LT["t0"] <= t < LT["t1"]:
        p = ease_out((t - LT["t0"]) / FADE)
        blit(cv, LT_IM, (LT_XY[0] - 40 * (1 - p), LT_XY[1]), p)
    for c, im, xy in ((CARD1, C1_IM, C1_XY), (CARD2, C2_IM, C2_XY)):
        if c["t0"] <= t < c["t1"]:
            p = ease_out((t - c["t0"]) / FADE)
            dx = 50 * (1 - p) * (1 if c["side"] == "right" else -1)
            blit(cv, im, (xy[0] + dx, xy[1]), p)
            stamp_frame(cv, im, xy, t, c["stamp"])
    return cv


# ---------------------------------------------------------------- audio
SR = 48000


def read_voice():
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", SRC, "-f", "f32le",
                                   "-ac", "2", "-ar", str(SR), "-"])
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)


def db(x):
    return 20 * np.log10(max(x, 1e-12))


def fft_band(x, lo, hi):
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    g = ((fr >= lo) & (fr <= hi)).astype(float)
    # soft edges
    g = np.convolve(g, np.hanning(64) / np.hanning(64).sum(), mode="same")
    return np.fft.irfft(X * g, n=len(x))


def sfx_doc_open(rng):
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    noise = fft_band(rng.standard_normal(n), 900, 7000)
    env = np.clip(t / 0.03, 0, 1) * np.exp(-t / 0.16)
    crinkle = 0.6 + 0.4 * (rng.random(n // 400 + 1).repeat(400)[:n])
    slide = noise * env * crinkle
    tap_n = int(0.08 * SR)
    tt = np.arange(tap_n) / SR
    tap = np.sin(2 * math.pi * 180 * tt) * np.exp(-tt / 0.02) * 0.5
    slide[:tap_n] += tap
    return slide / np.max(np.abs(slide))


def sfx_stamp(rng):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    fr = 48 + 70 * np.exp(-t / 0.03)
    ph = 2 * math.pi * np.cumsum(fr) / SR
    body = np.sin(ph) * np.exp(-t / 0.12)
    click = fft_band(rng.standard_normal(n), 200, 3500) * np.exp(-t / 0.008) * 1.4
    s = body + click
    return s / np.max(np.abs(s))


def ambience(n, rng):
    t = np.arange(n) / SR
    # room tone: brown-ish noise, low passed
    wn = rng.standard_normal(n)
    room = fft_band(np.cumsum(wn - wn.mean()) * 0.02 + wn * 0.3, 60, 1200)
    room /= np.std(room)
    # restrained suspense pad: low detuned fifth with slow swell
    lfo = 0.65 + 0.35 * np.sin(2 * math.pi * 0.07 * t - 1.2)
    pad = (np.sin(2 * math.pi * 55 * t) + 0.8 * np.sin(2 * math.pi * 55.35 * t)
           + 0.45 * np.sin(2 * math.pi * 82.4 * t) + 0.25 * np.sin(2 * math.pi * 110.2 * t))
    pad = pad * lfo
    pad /= np.std(pad)
    bed = 0.55 * room + 0.45 * pad
    fade = np.minimum(np.clip(t / 1.5, 0, 1), np.clip((n / SR - t) / 1.5, 0, 1))
    return bed * fade


def build_audio():
    rng = np.random.default_rng(2017)
    voice = read_voice()
    n = len(voice)
    mono = voice.mean(axis=1)
    # active-speech RMS: 50 ms windows above the 60th percentile
    win = int(0.05 * SR)
    rms = np.sqrt(np.mean(mono[: n // win * win].reshape(-1, win) ** 2, axis=1))
    speech_rms = float(np.sqrt(np.mean(rms[rms > np.percentile(rms, 60)] ** 2)))
    speech_db = db(speech_rms)

    bed = ambience(n, rng)
    bed *= 10 ** ((speech_db - 26) / 20) / np.std(bed)  # 26 dB under speech

    fx = np.zeros(n)
    doc, stp = sfx_doc_open(rng), sfx_stamp(rng)
    peak_doc = 10 ** ((speech_db - 14) / 20)  # subtle: peaks ~14 dB under speech RMS
    peak_stp = 10 ** ((speech_db - 9) / 20)
    for ts in (CARD1["t0"], CARD2["t0"]):
        i = int(ts * SR)
        seg = doc[: n - i] * peak_doc
        fx[i:i + len(seg)] += seg
    for ts in (CARD1["stamp"], CARD2["stamp"]):
        i = int((ts + 4 / FPS) * SR)  # thud on stamp impact frame
        seg = stp[: n - i] * peak_stp
        fx[i:i + len(seg)] += seg

    under = np.stack([bed + fx, bed + fx], axis=1).astype(np.float32)
    path = os.path.join(WORK, "under.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(under, -1, 1) * 32767).astype("<i2").tobytes())
    info = dict(speech_active_dbfs=round(speech_db, 1),
                bed_dbfs=round(db(np.std(bed)), 1),
                bed_below_speech_db=round(speech_db - db(np.std(bed)), 1))
    print("audio:", info)
    return path


# ---------------------------------------------------------------- video
def video_filter():
    p1 = ":".join(f"{x:.3f}:{y:.3f}" for x, y in angles.spec("a1")[1])
    p2 = ":".join(f"{x:.3f}:{y:.3f}" for x, y in angles.spec("a2")[1])
    # sharpening on the punch-ins only, to offset the resample softness and
    # keep perceived sharpness consistent with the wide.
    warp = {
        "a1": f"perspective={p1}:interpolation=cubic:sense=source,unsharp=5:5:0.35:5:5:0",
        "a2": f"perspective={p2}:interpolation=cubic:sense=source,unsharp=5:5:0.35:5:5:0",
        "wide": "null",
    }
    parts, labels = [], []
    k = len(EDL)
    parts.append(f"[0:v]setpts=PTS-STARTPTS,fps={FPS},format=yuv420p,split={k}" +
                 "".join(f"[s{i}]" for i in range(k)))
    for i, (a, b, ang) in enumerate(EDL):
        fs, fe = f(a), (NF if b is None else f(b))
        parts.append(f"[s{i}]trim=start_frame={fs}:end_frame={fe},setpts=PTS-STARTPTS,"
                     f"{warp[ang]}[v{i}]")
        labels.append(f"[v{i}]")
    parts.append("".join(labels) + f"concat=n={k}:v=1:a=0,format=yuv420p[base]")
    parts.append("[1:v]format=rgba[gfx]")
    parts.append("[base][gfx]overlay=0:0:format=auto:shortest=1,format=yuv420p[vout]")
    return ";".join(parts)


def main():
    under = build_audio()
    # Mix in its own pass (a shared filtergraph ends audio when video ends).
    # normalize=0 -> the original voice samples pass through at unity gain.
    mix = os.path.join(WORK, "mix.wav")
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-i", under,
                           "-filter_complex",
                           "[0:a][1:a]amix=inputs=2:normalize=0:duration=first",
                           "-c:a", "pcm_f32le", mix])
    cmd = [
        "ffmpeg", "-v", "error", "-stats", "-y",
        "-i", SRC,
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0",
        "-i", mix,
        "-filter_complex", video_filter(),
        "-map", "[vout]", "-map", "2:a",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-color_primaries", "bt709",
        "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
        "-movflags", "+faststart",
        OUT,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(NF):
        proc.stdin.write(graphics(n).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")


if __name__ == "__main__":
    if len(sys.argv) > 5 and sys.argv[5] == "--stills":
        for t in (0.1, 3, 8.1, 9, 10.13, 11, 13.5, 14.1, 16.2, 18, 22):
            graphics(f(t)).save(os.path.join(WORK, f"g_{t}.png"))
    else:
        main()
