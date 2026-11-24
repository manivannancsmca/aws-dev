# -----------------------------------------------------------------------------
# Draws docs/12-aws-sketchbook.html: hand-drawn infographics (felt-pen style on paper)
# that explain how Jenkins + Terraform create each AWS service of product-app.
# Every board has the same layout, like a page drawn by hand:
#
#   title in a cloud bubble
#   input box -> green frame "Terraform creates" (resources in order) -> "then used by" -> result with a check mark
#   orange dashed strip "how it works inside" (little pictures with arrows)
#   "Step-by-Step Flow" (numbered, two columns) + "Key Points" box
#
#   python scripts/sketchbook/generate.py                 # writes docs/12-aws-sketchbook.html
#   python scripts/sketchbook/generate.py --png           # ... and one PNG per board in docs/images/ (needs Edge or Chrome)
#   python scripts/sketchbook/generate.py <output.html>   # writes somewhere else
#
# Needs only Python 3 (no packages). Lines get a small random wobble so they look hand drawn;
# the random numbers use a fixed seed per board, so the output is always the same.
#
# Where to change things:
#   - colours, fonts, dark theme ............ sketchbook.css (next to this file)
#   - the text of a board ................... the BOARDS list (one dict per board)
#   - the fixed layout ...................... standard_board()
#   - little pictures ....................... the I_... functions
# The script prints "WARN ..." when a text does not fit its box or two labels overlap.
# -----------------------------------------------------------------------------
import math, random, html, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DEFAULT = HERE.parent.parent / 'docs' / '12-aws-sketchbook.html'
W = 1000
TAU = 2 * math.pi
WARN = []

def esc(s): return html.escape(str(s), quote=True)
def f(v):
    s = f"{v:.1f}"
    if s.endswith(".0"): s = s[:-2]
    return "0" if s == "-0" else s

# Advance widths of Patrick Hand in em, measured once in a browser (canvas measureText at 100px).
GLYPH_W = {' ': 0.23, '!': 0.25, '"': 0.3, '#': 0.46, '$': 0.51, '%': 0.64, '&': 0.53, "'": 0.16, '(': 0.33, ')': 0.36, '*': 0.4, '+': 0.48, ',': 0.2, '-': 0.4, '.': 0.21, '/': 0.42, '0': 0.45, '1': 0.36, '2': 0.47, '3': 0.45, '4': 0.38, '5': 0.42, '6': 0.4, '7': 0.5, '8': 0.43, '9': 0.37, ':': 0.23, ';': 0.23, '<': 0.4, '=': 0.57, '>': 0.4, '?': 0.37, '@': 0.55, 'A': 0.49, 'B': 0.51, 'C': 0.55, 'D': 0.48, 'E': 0.44, 'F': 0.38, 'G': 0.48, 'H': 0.47, 'I': 0.24, 'J': 0.37, 'K': 0.52, 'L': 0.37, 'M': 0.6, 'N': 0.53, 'O': 0.56, 'P': 0.48, 'Q': 0.66, 'R': 0.45, 'S': 0.46, 'T': 0.47, 'U': 0.55, 'V': 0.56, 'W': 0.62, 'X': 0.6, 'Y': 0.44, 'Z': 0.51, '[': 0.3, '\\': 0.42, ']': 0.3, '^': 0.37, '_': 0.57, '`': 0.22, 'a': 0.39, 'b': 0.41, 'c': 0.39, 'd': 0.39, 'e': 0.4, 'f': 0.36, 'g': 0.45, 'h': 0.42, 'i': 0.22, 'j': 0.24, 'k': 0.42, 'l': 0.27, 'm': 0.68, 'n': 0.45, 'o': 0.4, 'p': 0.43, 'q': 0.46, 'r': 0.39, 's': 0.39, 't': 0.34, 'u': 0.4, 'v': 0.4, 'w': 0.46, 'x': 0.45, 'y': 0.42, 'z': 0.43, '{': 0.34, '|': 0.18, '}': 0.33, '~': 0.53, '·': 0.2, '–': 0.5, '—': 0.8, '…': 0.6, '←': 1, '→': 1, '≈': 0.55, '①': 1, '②': 1, '③': 1, '④': 1, '⑤': 1, '⑥': 1, '✓': 0.75}

def est(s, size):
    """Width in px of a text in Patrick Hand (unknown characters count as 0.5 em)."""
    return sum(GLYPH_W.get(c, .5) for c in s) * size

def wrap(text, size, width):
    out, cur = [], ''
    for word in text.split(' '):
        trial = (cur + ' ' + word).strip()
        if cur and est(trial, size) > width: out.append(cur); cur = word
        else: cur = trial
    if cur: out.append(cur)
    return out

# =============================================================================
class Board:
    def __init__(self, name, seed):
        self.name = name; self.r = random.Random(seed); self.el = []; self.maxy = 0; self.labels = []
    def j(self, a): return self.r.uniform(-a, a)
    def add(self, s): self.el.append(s)
    def bump(self, y): self.maxy = max(self.maxy, y)

    # ---- strokes ----
    def path(self, d, c='N', w='w2', dash=False):
        self.add(f'<path class="s{c} {w}{" dash" if dash else ""}" d="{d}"/>')
    def seg(self, x1, y1, x2, y2, rough=.5):
        L = math.hypot(x2 - x1, y2 - y1) or 1
        nx, ny = -(y2 - y1) / L, (x2 - x1) / L
        b1, b2 = self.j(min(1.6, .2 + L * .004) * rough * 2), self.j(min(1.6, .2 + L * .004) * rough * 2)
        sx, sy, ex, ey = x1 + self.j(.4), y1 + self.j(.4), x2 + self.j(.4), y2 + self.j(.4)
        return (f"M{f(sx)} {f(sy)}C{f(sx + (ex - sx) * .33 + nx * b1)} {f(sy + (ey - sy) * .33 + ny * b1)} "
                f"{f(sx + (ex - sx) * .67 + nx * b2)} {f(sy + (ey - sy) * .67 + ny * b2)} {f(ex)} {f(ey)}")
    def line(self, x1, y1, x2, y2, c='N', w='w2', dash=False):
        self.path(self.seg(x1, y1, x2, y2), c, w, dash); self.bump(max(y1, y2))
    def poly(self, pts, c='N', w='w2', closed=False, dash=False):
        segs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if closed else [])
        self.path(''.join(self.seg(a[0], a[1], b[0], b[1]) for a, b in segs), c, w, dash)
    def smooth(self, pts, c='N', w='w2', closed=False, jit=.5, dash=False):
        q = [(x + self.j(jit), y + self.j(jit)) for x, y in pts]
        if closed: q = q + q[:2]; s = f"M{f((q[0][0] + q[1][0]) / 2)} {f((q[0][1] + q[1][1]) / 2)}"
        else: s = f"M{f(q[0][0])} {f(q[0][1])}"
        for i in range(1, len(q) - 1):
            s += f"Q{f(q[i][0])} {f(q[i][1])} {f((q[i][0] + q[i + 1][0]) / 2)} {f((q[i][1] + q[i + 1][1]) / 2)}"
        if not closed: s += f"L{f(q[-1][0])} {f(q[-1][1])}"
        self.path(s, c, w, dash)
    def fill(self, pts, cls):
        self.add(f'<path class="{cls}" d="M' + 'L'.join(f'{f(x)} {f(y)}' for x, y in pts) + 'Z"/>')
    def ell(self, cx, cy, rx, ry, a0=0, a1=TAU, n=20):
        return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    def ellipse(self, cx, cy, rx, ry, c='N', w='w2', fill=None):
        if fill: self.fill(self.ell(cx, cy, rx, ry), fill)
        st = self.r.uniform(0, TAU); self.smooth(self.ell(cx, cy, rx, ry, st, st + TAU * 1.04, 22), c, w, jit=.35)
    def arc(self, cx, cy, rx, ry, a0, a1, c='N', w='w2'): self.smooth(self.ell(cx, cy, rx, ry, a0, a1, 10), c, w, jit=.3)
    def rr_pts(self, x, y, w_, h_, r, step=16):
        r = min(r, w_ / 2, h_ / 2); pts = []
        def edge(x0, y0, x1, y1):
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step)); return [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n)]
        def corner(cx, cy, a0): return [(cx + r * math.cos(a0 + math.pi / 2 * i / 4), cy + r * math.sin(a0 + math.pi / 2 * i / 4)) for i in range(4)]
        pts += edge(x + r, y, x + w_ - r, y) + corner(x + w_ - r, y + r, -math.pi / 2) + edge(x + w_, y + r, x + w_, y + h_ - r)
        pts += corner(x + w_ - r, y + h_ - r, 0) + edge(x + w_ - r, y + h_, x + r, y + h_) + corner(x + r, y + h_ - r, math.pi / 2)
        pts += edge(x, y + h_ - r, x, y + r) + corner(x + r, y + r, math.pi)
        return pts
    def rbox(self, x, y, w_, h_, c='N', fill='fW', w='w2', r=12, dash=False):
        pts = self.rr_pts(x, y, w_, h_, r)
        if fill: self.fill(pts, fill)
        self.smooth(pts, c, w, True, .7, dash); self.bump(y + h_ + 3)
    def bubble(self, x, y, w_, h_, c='B', fill='fW', lobe=64, amp=5):
        base = self.rr_pts(x, y, w_, h_, h_ / 2.2, 6); pts = []; s = 0
        for i, (px, py) in enumerate(base):
            nxp, nyp = base[(i + 1) % len(base)]; pvx, pvy = base[i - 1]
            tx, ty = nxp - pvx, nyp - pvy; L = math.hypot(tx, ty) or 1
            if i: s += math.hypot(px - base[i - 1][0], py - base[i - 1][1])
            bul = amp * abs(math.sin(math.pi * s / lobe))
            pts.append((px + ty / L * bul, py - tx / L * bul))
        if fill: self.fill(pts, fill)
        self.smooth(pts, c, 'w2', True, .4); self.bump(y + h_ + amp)
    def dot(self, x, y, r=2.4, cls='fN'): self.add(f'<circle class="{cls}" cx="{f(x)}" cy="{f(y)}" r="{f(r)}"/>')

    # ---- text ----
    def t(self, x, y, s, c=None, size=16, anchor='start', fit=None, check=True):
        cls = f' class="t{c}"' if c else ''
        a = '' if anchor == 'start' else f' text-anchor="{anchor}"'
        tl = f' textLength="{f(fit)}" lengthAdjust="spacing"' if fit else ''
        self.add(f'<text{cls} x="{f(x)}" y="{f(y)}" font-size="{size}"{a}{tl}>{esc(s)}</text>')
        wd = fit or est(s, size); x0 = x if anchor == 'start' else (x - wd / 2 if anchor == 'middle' else x - wd)
        if check: self.labels.append((x0, y - size * .72, x0 + wd, y + size * .2, s))
        if x0 < 4 or x0 + wd > W - 4: WARN.append(f"{self.name}: '{s}' runs off the sheet")
        self.bump(y + size * .3)
        return x0 + wd
    def block(self, cx, top, w_, h_, title, body, tsize=18, bsize=14.5, tc=None, bc=None):
        """Centred title + wrapped body inside a box; warns when it does not fit."""
        tl = wrap(title, tsize, w_ - 18) if title else []
        bl = []
        for b_ in ([body] if isinstance(body, str) else body or []): bl += wrap(b_, bsize, w_ - 18)
        hh = len(tl) * tsize * 1.15 + (6 if tl and bl else 0) + len(bl) * bsize * 1.25
        if hh > h_ - 10: WARN.append(f"{self.name}: text too tall for box '{title}'")
        y = top + (h_ - hh) / 2 + tsize * .85
        for s in tl: self.t(cx, y, s, tc, tsize, 'middle', check=False); y += tsize * 1.15
        if tl and bl: y += 6
        y += (bsize - tsize) * .85 if tl else (bsize * .85 - tsize * .85)
        for s in bl: self.t(cx, y, s, bc, bsize, 'middle', check=False); y += bsize * 1.25

    # ---- arrows ----
    def head(self, tip, frm, c='N', w='w2', size=12):
        a = math.atan2(tip[1] - frm[1], tip[0] - frm[0]); d = ''
        for sg in (1, -1):
            b = a + math.pi + sg * .45; d += self.seg(tip[0], tip[1], tip[0] + size * math.cos(b), tip[1] + size * math.sin(b), .2)
        self.path(d, c, w)
    def arrow(self, pts, c='N', w='w2', dash=False, label=None, lpos=None, lc=None, lsize=15, anchor='middle', head=True):
        self.poly(pts, c, w, False, dash)
        if head: self.head(pts[-1], pts[-2], c, w)
        if label:
            lx, ly = lpos or ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2 - 8)
            self.t(lx, ly, label, lc or c, lsize, anchor)
        self.bump(max(p[1] for p in pts))

    def svg(self, label):
        L = self.labels
        for i in range(len(L)):
            for k in range(i + 1, len(L)):
                p, q = L[i], L[k]
                if min(p[2], q[2]) - max(p[0], q[0]) > 2 and min(p[3], q[3]) - max(p[1], q[1]) > 2:
                    WARN.append(f"{self.name}: '{p[4]}' overlaps '{q[4]}'")
        H = math.ceil(self.maxy + 22)
        return f'<svg class="hd" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}">' + ''.join(self.el) + '</svg>'

# =============================================================================
# Little pictures: I_x(board, centre_x, centre_y, scale)
# drawn like the reference: blue outlines with a pale blue fill
# =============================================================================
def I_user(b, cx, cy, s=1, c='B'):
    b.ellipse(cx, cy - 14 * s, 11 * s, 11 * s, c, 'w2', 'fB')
    sh = [(cx - 20 * s, cy + 24 * s)] + b.ell(cx, cy + 22 * s, 20 * s, 20 * s, math.pi, TAU, 10) + [(cx + 20 * s, cy + 24 * s)]
    b.fill(sh, 'fB'); b.poly([sh[0], sh[1]], c); b.smooth(sh[1:-1], c, 'w2', jit=.3); b.poly([sh[-2], sh[-1], sh[0]], c)
def I_doc(b, cx, cy, s=1, c='B', label=None):
    pts = [(cx - 17 * s, cy - 23 * s), (cx + 8 * s, cy - 23 * s), (cx + 17 * s, cy - 14 * s), (cx + 17 * s, cy + 23 * s), (cx - 17 * s, cy + 23 * s)]
    b.fill(pts, 'fB'); b.poly(pts, c, 'w2', True); b.poly([(cx + 8 * s, cy - 23 * s), (cx + 8 * s, cy - 14 * s), (cx + 17 * s, cy - 14 * s)], c, 'w1')
    if label: b.t(cx, cy + 6 * s, label, c, 14 * s, 'middle', check=False)
    else:
        for dy in (-6, 1, 8, 15): b.line(cx - 10 * s, cy + dy * s, cx + (10 if dy < 15 else 3) * s, cy + dy * s, c, 'w1')
def I_tf(b, cx, cy, s=1, c='G'): I_doc(b, cx, cy, s, c, '.tf')
def I_docs(b, cx, cy, s=1, c='B'):
    for k in (2, 1, 0): I_doc(b, cx + 6 * k * s - 6 * s, cy - 6 * k * s + 6 * s, s * .9, c)
def I_db(b, cx, cy, s=1, c='B'):
    rx, ry, h = 22 * s, 7 * s, 44 * s; y0 = cy - h / 2
    body = [(cx - rx, y0)] + [(cx - rx, y0 + h)] + b.ell(cx, y0 + h, rx, ry, math.pi, 0, 10)[::-1][::-1] + [(cx + rx, y0)]
    b.fill([(cx - rx, y0), (cx - rx, y0 + h)] + b.ell(cx, y0 + h, rx, ry, math.pi, 0, 10) + [(cx + rx, y0)], 'fB')
    b.ellipse(cx, y0, rx, ry, c, 'w2', 'fB'); b.line(cx - rx, y0, cx - rx, y0 + h, c); b.line(cx + rx, y0, cx + rx, y0 + h, c)
    for k in (1, 2, 3): b.arc(cx, y0 + h * k / 3, rx, ry, 0, math.pi, c, 'w2')
def I_gear(b, cx, cy, s=1, c='B'):
    pts = [(cx + (18 if i % 4 in (0, 1) else 13) * s * math.cos(i * TAU / 32), cy + (18 if i % 4 in (0, 1) else 13) * s * math.sin(i * TAU / 32)) for i in range(32)]
    b.fill(pts, 'fB'); b.poly(pts, c, 'w2', True); b.ellipse(cx, cy, 5.5 * s, 5.5 * s, c, 'w2', 'fW')
def I_badge(b, cx, cy, s=1, c='B'):
    b.rbox(cx - 17 * s, cy - 22 * s, 34 * s, 46 * s, c, 'fB', 'w2', 5 * s); b.rbox(cx - 6 * s, cy - 28 * s, 12 * s, 8 * s, c, 'fW', 'w1', 2)
    b.ellipse(cx, cy - 6 * s, 6 * s, 6 * s, c, 'w2', 'fW'); b.arc(cx, cy + 10 * s, 10 * s, 7 * s, math.pi, TAU, c)
    b.line(cx - 9 * s, cy + 16 * s, cx + 9 * s, cy + 16 * s, c, 'w1')
def I_key(b, cx, cy, s=1, c='B'):
    b.ellipse(cx - 12 * s, cy, 8 * s, 8 * s, c, 'w2', 'fB'); b.line(cx - 4 * s, cy, cx + 20 * s, cy, c, 'w3')
    b.line(cx + 12 * s, cy, cx + 12 * s, cy + 7 * s, c, 'w2'); b.line(cx + 18 * s, cy, cx + 18 * s, cy + 6 * s, c, 'w2')
def I_lock(b, cx, cy, s=1, c='B'):
    b.arc(cx, cy - 3 * s, 9 * s, 12 * s, math.pi, TAU, c, 'w3'); b.rbox(cx - 14 * s, cy - 3 * s, 28 * s, 23 * s, c, 'fB', 'w2', 4)
    b.dot(cx, cy + 7 * s, 2.6 * s, 'fBd')
def I_shield(b, cx, cy, s=1, c='B'):
    pts = [(cx - 17 * s, cy - 18 * s), (cx, cy - 23 * s), (cx + 17 * s, cy - 18 * s), (cx + 17 * s, cy), (cx + 10 * s, cy + 14 * s), (cx, cy + 22 * s), (cx - 10 * s, cy + 14 * s), (cx - 17 * s, cy)]
    b.fill(pts, 'fB'); b.smooth(pts, c, 'w2', True, .3); b.poly([(cx - 7 * s, cy), (cx - 1 * s, cy + 6 * s), (cx + 8 * s, cy - 6 * s)], 'G', 'w3')
def I_box(b, cx, cy, s=1, c='B'):
    w_, h_ = 48 * s, 30 * s; x, y = cx - w_ / 2, cy - h_ / 2
    b.rbox(x, y, w_, h_, c, 'fB', 'w2', 3)
    for i in range(1, 6): b.line(x + w_ * i / 6, y + 5 * s, x + w_ * i / 6, y + h_ - 5 * s, c, 'w1')
def I_shelf(b, cx, cy, s=1, c='B'):
    for dx, dy in ((-16, 5), (16, 5), (0, -13)): I_box(b, cx + dx * s, cy + dy * s, .62 * s, c)
    b.line(cx - 36 * s, cy + 16 * s, cx + 36 * s, cy + 16 * s, c, 'w3')
def I_safe(b, cx, cy, s=1, c='B'):
    b.rbox(cx - 22 * s, cy - 20 * s, 44 * s, 40 * s, c, 'fB', 'w3', 4); b.ellipse(cx - 3 * s, cy, 8 * s, 8 * s, c, 'w2', 'fW')
    b.line(cx + 12 * s, cy - 7 * s, cx + 12 * s, cy + 7 * s, c, 'w3')
def I_dice(b, cx, cy, s=1, c='B'):
    b.rbox(cx - 17 * s, cy - 14 * s, 30 * s, 30 * s, c, 'fB', 'w2', 4)
    for dx, dy in ((-9, -6), (-2, 1), (5, 8), (5, -6), (-9, 8)): b.dot(cx + dx * s, cy + dy * s, 2.4 * s, 'fBd')
def I_cloud(b, cx, cy, s=1, c='B'):
    pts = []
    for i in range(34):
        a = i * TAU / 34; sa = math.sin(a); bump = 1 + (.16 * abs(math.sin(3.5 * a)) if sa < .3 else .04)
        pts.append((cx + 26 * s * math.cos(a) * bump, cy + 16 * s * sa * bump * (.8 if sa > 0 else 1)))
    b.fill(pts, 'fB'); b.smooth(pts, c, 'w2', True, .3)
def I_door(b, cx, cy, s=1, c='B'):
    b.rbox(cx - 14 * s, cy - 22 * s, 28 * s, 44 * s, c, 'fW', 'w2', 2)
    lf = [(cx - 14 * s, cy - 22 * s), (cx + 6 * s, cy - 18 * s), (cx + 6 * s, cy + 18 * s), (cx - 14 * s, cy + 22 * s)]
    b.fill(lf, 'fB'); b.poly(lf, c, 'w1', True); b.dot(cx + 2 * s, cy + 1 * s, 2 * s, 'fBd')
def I_sign(b, cx, cy, s=1, c='B'):
    b.line(cx, cy - 22 * s, cx, cy + 24 * s, c, 'w3')
    for pts in ([(cx - 2 * s, cy - 20 * s), (cx + 24 * s, cy - 20 * s), (cx + 31 * s, cy - 13 * s), (cx + 24 * s, cy - 6 * s), (cx - 2 * s, cy - 6 * s)],
                [(cx + 2 * s, cy - 1 * s), (cx - 24 * s, cy - 1 * s), (cx - 31 * s, cy + 6 * s), (cx - 24 * s, cy + 13 * s), (cx + 2 * s, cy + 13 * s)]):
        b.fill(pts, 'fB'); b.poly(pts, c, 'w2', True)
def I_rooms(b, cx, cy, s=1, c='B'):
    b.rbox(cx - 26 * s, cy - 18 * s, 24 * s, 36 * s, c, 'fB', 'w2', 3, dash=True); b.rbox(cx + 2 * s, cy - 18 * s, 24 * s, 36 * s, c, 'fB', 'w2', 3, dash=True)
def I_nat(b, cx, cy, s=1, c='B'):
    b.rbox(cx - 26 * s, cy - 16 * s, 52 * s, 32 * s, c, 'fB', 'w2', 5); b.t(cx, cy + 6 * s, 'NAT', 'B', 16 * s, 'middle', check=False)
def I_alb(b, cx, cy, s=1, c='B'):
    b.rbox(cx - 24 * s, cy - 18 * s, 48 * s, 36 * s, c, 'fB', 'w2', 5)
    for dy in (-10, 0, 10): b.line(cx - 13 * s, cy, cx + 13 * s, cy + dy * s, c, 'w1'); b.dot(cx + 14 * s, cy + dy * s, 2.2 * s, 'fBd')
    b.dot(cx - 14 * s, cy, 2.6 * s, 'fBd')
def I_heart(b, cx, cy, s=1, c='R'):
    pts = [(cx + s * 16 * math.sin(t) ** 3, cy + 3 * s - s * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))) for t in [i * TAU / 26 for i in range(26)]]
    b.fill(pts, 'fP'); b.smooth(pts, c, 'w2', True, .3)
def I_mag(b, cx, cy, s=1, c='B'):
    b.ellipse(cx - 4 * s, cy - 4 * s, 12 * s, 12 * s, c, 'w2', 'fB'); b.line(cx + 5 * s, cy + 5 * s, cx + 17 * s, cy + 17 * s, c, 'w3')
def I_folder(b, cx, cy, s=1, c='B'):
    pts = [(cx - 24 * s, cy - 16 * s), (cx - 8 * s, cy - 16 * s), (cx - 3 * s, cy - 10 * s), (cx + 24 * s, cy - 10 * s), (cx + 24 * s, cy + 17 * s), (cx - 24 * s, cy + 17 * s)]
    b.fill(pts, 'fB'); b.poly(pts, c, 'w2', True)
def I_bucket(b, cx, cy, s=1, c='B'):
    rt, rb, h = 22 * s, 16 * s, 40 * s; y0 = cy - h / 2
    body = [(cx - rt, y0), (cx - rb, y0 + h)] + b.ell(cx, y0 + h, rb, 5 * s, math.pi, 0, 10) + [(cx + rt, y0)]
    b.fill(body, 'fB'); b.ellipse(cx, y0, rt, 6 * s, c, 'w2', 'fW'); b.line(cx - rt, y0, cx - rb, y0 + h, c); b.line(cx + rt, y0, cx + rb, y0 + h, c)
    b.arc(cx, y0 + h, rb, 5 * s, 0, math.pi, c)
def I_check(b, cx, cy, s=1):
    b.add(f'<circle class="fC" cx="{f(cx)}" cy="{f(cy)}" r="{f(15 * s)}"/>')
    b.poly([(cx - 7 * s, cy + 1 * s), (cx - 2 * s, cy + 6 * s), (cx + 8 * s, cy - 6 * s)], 'W', 'w3')
def tick(b, x, y, c='G'): b.poly([(x, y), (x + 5, y + 6), (x + 15, y - 8)], c, 'w3')
def cross(b, x, y, s=1, c='R'): b.line(x - 8 * s, y - 8 * s, x + 8 * s, y + 8 * s, c, 'w3'); b.line(x + 8 * s, y - 8 * s, x - 8 * s, y + 8 * s, c, 'w3')

# =============================================================================
# The fixed layout of one board
# =============================================================================
def title_bubble(b, title):
    words = title.split(' '); size = 40; gap = est(' ', size) + 5
    parts = [[wd, est(wd.strip('*'), size), False] for wd in words]
    on = False                                   # underline the words between *...*
    for p in parts:
        if p[0].startswith('*'): on = True
        p[2] = on
        if p[0].endswith('*'): on = False
        p[0] = p[0].strip('*')
    total = sum(p[1] for p in parts) + gap * (len(parts) - 1)
    x = 500 - total / 2; y = 70
    b.bubble(x - 42, 16, total + 84, 80, 'B', 'fW', 70, 6)
    for wd, wdt, ul in parts:
        b.t(x, y, wd, None, size, fit=wdt)
        if ul: b.smooth([(x + 1, y + 10), (x + wdt * .5, y + 11.5), (x + wdt - 1, y + 9)], 'B', 'w3', jit=.4)
        x += wdt + gap

def steps_and_keys(b, steps, keys, y0):
    b.bubble(14, y0, 292, 56, 'V', 'fL', 62, 4); b.t(38, y0 + 39, 'Step-by-Step Flow :', None, 29)
    cols = [(18, 448, steps[:3], 1), (476, 800, steps[3:], 4)]
    ybot = y0 + 80
    for x0, x1, items, n0 in cols:
        y = y0 + 106
        for i, it in enumerate(items):
            text, bullets = (it, []) if isinstance(it, str) else it
            col = 'V' if n0 == 1 else 'B'
            b.ellipse(x0 + 15, y - 7, 14, 14, col, 'w2'); b.t(x0 + 15, y - 1, str(n0 + i), col, 18, 'middle', check=False)
            for ln in wrap(text, 21, x1 - x0 - 44):
                b.t(x0 + 40, y, ln, 'B' if n0 == 1 else None, 21); y += 28
            for bl in bullets:
                for k, ln in enumerate(wrap(bl, 19, x1 - x0 - 74)):
                    if k == 0: b.dot(x0 + 52, y - 6, 2.8, 'fN')
                    b.t(x0 + 66, y, ln, None, 19); y += 25
            y += 14
        ybot = max(ybot, y)
    b.line(461, y0 + 74, 463, ybot - 8, 'N', 'w2')
    y = y0 + 22; ks = [wrap(k, 20, 126) for k in keys]
    hh = 64 + sum(len(k) * 25 + 16 for k in ks)
    b.rbox(812, y, 176, hh, 'G', 'fW', 'w2', 16)
    b.t(828, y + 38, 'Key Points :', 'G', 25); yy = y + 78
    for lines in ks:
        tick(b, 826, yy - 7)
        for ln in lines: b.t(852, yy, ln, None, 20); yy += 25
        yy += 16
    b.bump(max(ybot, y + hh))

def standard_board(spec):
    b = Board(spec['id'], spec['seed']); title_bubble(b, spec['title'])
    # input: icon + blue box
    icon, ilabel = spec['need_icon']; icon(b, 40, 196, 1.05); b.t(40, 262, ilabel, None, 18, 'middle')
    b.rbox(82, 132, 178, 132, 'B', 'fW'); b.block(171, 132, 178, 132, spec['need'][0], spec['need'][1], 23, 18)
    b.arrow([(262, 198), (288, 198)])
    # green frame with the resources in order
    b.rbox(290, 104, 420, 198, 'G', 'fW', 'w2', 18)
    (spec.get('group_icon') or I_tf)(b, 308, 132, .62, 'G'); b.t(328, 142, spec['group'], 'G', 23)
    (t1, d1), (t2, d2) = spec['box1'], spec['box2']
    b.rbox(304, 160, 184, 128, 'P', 'fP'); b.block(396, 160, 184, 128, t1, d1, 23, 17.5)
    b.rbox(520, 160, 176, 128, 'V', 'fV'); b.block(608, 160, 176, 128, t2, d2, 23, 17.5)
    b.arrow([(490, 224), (517, 224)])
    # then used by -> result
    b.arrow([(698, 224), (723, 224)])
    b.rbox(726, 104, 262, 198, 'G', 'fW'); b.block(857, 104, 262, 198, spec['used'][0], spec['used'][1], 24, 19)
    b.arrow([(857, 304), (857, 338)])
    b.rbox(750, 340, 238, 110, 'V', 'fW'); I_check(b, 784, 395, 1.2)
    b.block(884, 340, 184, 110, None, spec['result'], 23, 23)
    # orange dashed strip: how it works inside
    b.arrow([(396, 290), (396, 338)], label=spec.get('link'), lpos=(408, 320), anchor='start', lsize=19)
    b.rbox(290, 340, 446, 188, 'O', 'fO', 'w2', 16, dash=True); b.t(310, 374, spec['how_title'], 'O', 24)
    if spec.get('how_draw'): spec['how_draw'](b)
    else: chain(b, spec['how'], spec.get('how_arrows'))
    # note on the left (red handwriting)
    if spec.get('note'):
        y = 336
        for ln in spec['note']: b.t(18, y, ln, 'R', 19.5); y += 25
    if spec.get('extra'): spec['extra'](b)
    steps_and_keys(b, spec['steps'], spec['keys'], max(b.maxy, 528) + 24)
    return b.svg(spec['caption'])

def chain(b, items, arrows=None, x0=346, dx=112, y=434):
    n = len(items)
    for i, (icon, label) in enumerate(items):
        x = x0 + i * dx; icon(b, x, y, 1.0)
        yy = y + 50
        for ln in wrap(label, 17.5, 108): b.t(x, yy, ln, None, 17.5, 'middle'); yy += 21
        if i < n - 1:
            lab, col, rev, xx = (arrows or [None] * n)[i] or ('', 'N', False, False)
            a, z = (x + 34, y), (x + dx - 34, y)
            b.arrow([z, a] if rev else [a, z], col, 'w2', dash=rev)
            if lab: b.t(x + dx / 2, y - 14, lab, col, 18, 'middle')
            if xx: cross(b, x + dx / 2, y + 1, .7)

# =============================================================================
# Overview: the finished system (own layout, same drawing style)
# =============================================================================
def architecture():
    b = Board('arch', 11); title_bubble(b, 'How *product-app* Runs on *AWS* ?')
    I_user(b, 40, 196, 1.05); b.t(40, 262, 'users', None, 18, 'middle')
    b.rbox(82, 132, 178, 132, 'B', 'fW'); b.block(171, 132, 178, 132, 'Internet', 'http://<alb-dns-name> via the internet gateway', 23, 18)
    b.arrow([(262, 198), (288, 198)])
    b.rbox(290, 104, 420, 424, 'G', 'fW', 'w2', 18); I_tf(b, 308, 132, .62, 'G'); b.t(328, 142, 'VPC 10.0.0.0/16 · step 02', 'G', 23)
    b.rbox(304, 160, 190, 98, 'P', 'fP'); b.block(399, 160, 190, 98, 'Load balancer', 'step 11 · public · alb-sg', 23, 17.5)
    b.rbox(304, 294, 190, 98, 'V', 'fV'); b.block(399, 294, 190, 98, 'ECS task', 'step 12 · private-app · ecs-sg', 23, 17.5)
    b.rbox(304, 428, 190, 90, 'B', 'fB'); b.block(399, 428, 190, 90, 'RDS MySQL', 'step 09 · private-db · rds-sg', 23, 17.5)
    b.rbox(526, 160, 170, 98, 'O', 'fO'); b.block(611, 160, 170, 98, 'NAT gateway', 'step 10 · out only', 23, 17.5)
    b.arrow([(399, 260), (399, 292)]); b.t(410, 282, ':8080 + health', 'G', 17)
    b.arrow([(399, 394), (399, 426)]); b.t(410, 416, ':3306', 'G', 17)
    b.arrow([(496, 343), (611, 343), (611, 260)]); b.t(510, 334, 'outbound', 'G', 17)
    b.arrow([(698, 209), (723, 209)])
    b.rbox(726, 104, 262, 198, 'G', 'fW'); b.block(857, 104, 262, 198, 'AWS services', ['ECR image · steps 05 + 06', 'Secrets Manager · step 07', 'CloudWatch Logs · step 08', 'IAM roles · step 04'], 24, 19)
    b.arrow([(857, 304), (857, 338)])
    b.rbox(750, 340, 238, 110, 'V', 'fW'); I_check(b, 784, 395, 1.2); b.block(884, 340, 184, 110, None, 'Only the load balancer is public', 23, 23)
    b.rbox(14, 334, 262, 194, 'O', 'fO', 'w2', 16, dash=True); b.t(30, 366, 'Built at build time', 'O', 23)
    for icon, lab, x in ((I_gear, 'Jenkins', 60), (I_tf, 'Terraform', 145), (I_bucket, 'S3 · 01', 230)):
        icon(b, x, 420, .9, 'B'); b.t(x, 468, lab, None, 17.5, 'middle')
    b.arrow([(84, 420), (118, 420)]); b.arrow([(170, 420), (204, 420)])
    b.t(145, 508, 'destroy-all removes the rest', 'M', 16.5, 'middle')
    steps_and_keys(b, ['A user opens http://<alb-dns-name>/swagger-ui.',
                       'The load balancer forwards to the ECS task on port 8080.',
                       'The task reads and writes MySQL on port 3306.',
                       'It pulls the image, reads the secret and sends logs out through the NAT.',
                       'Jenkins and Terraform built all of it; the state lives in S3.',
                       'destroy-all removes everything except the state bucket.'],
                   ['only the ALB is public', '45 resources in 12 steps', '≈ $3.50 per day running'], max(b.maxy, 528) + 24)
    return b.svg('The finished system: users reach the load balancer, which forwards to the ECS task; the task talks to MySQL and reaches ECR, '
                 'Secrets Manager and CloudWatch Logs only outbound through the NAT gateway. Jenkins and Terraform built it all.')

# =============================================================================
# The boards (text only; the layout is the same for all)
# =============================================================================
def red_back(b):     # step 10: the internet can never call in
    b.arrow([(682, 398), (346, 398)], 'R', 'w2', dash=True); cross(b, 514, 398, .7); b.t(536, 392, 'in: never', 'R', 18)

BOARDS = [
    dict(id='pipeline', seed=7, title='How One *Jenkins Step* Works ?', need_icon=(I_user, 'you'),
         need=('Build with Parameters', 'pick STEP and ACTION'), group='Jenkins job · product-app-aws-terraform', group_icon=I_gear,
         box1=('① terraform plan', 'only this step (-target)'), box2=('② terraform apply', 'after you approve'),
         used=('AWS · Mumbai', ["creates only this step's resources"]), result='Check the console, then the next STEP',
         link='behind the scenes', how_title='Behind the scenes',
         how=[(I_folder, 'copy the project'), (I_badge, 'who am I? mani-dev'), (I_tf, 'init: state from S3'), (I_bucket, 'new state saved in S3')],
         note=['same loop for', 'all 12 steps:', 'only the STEP', 'changes'],
         steps=['You choose STEP and ACTION, then click Build.', 'Jenkins copies the project and checks who it is in AWS.',
                'terraform init + plan, only for this step.',
                ('You approve within 60 minutes:', ['ACTION = plan stops before this', 'no click → ABORTED, nothing changes']),
                'terraform apply runs exactly that plan; the state goes to S3.', 'You check the console, then start the next STEP.'],
         keys=['plan alone changes nothing', 'no approval, no change', 'destroy-all = plan -destroy'],
         caption='One Jenkins step: you start a build, Jenkins plans only that step, waits for your approval, applies it and saves the state in S3; then you check the console.'),
    dict(id='01', seed=101, title='How the *S3 State Bucket* Works ?', need_icon=(I_gear, 'Jenkins'),
         need=('Jenkins runs', 'STEP = 01-state-bucket'), group='Terraform creates · step 01',
         box1=('① S3 bucket', 'product-app-tfstate- <account-id>'), box2=('② settings', 'versioning, AES256, no public access'),
         used=('Then used by', ['steps 02–12 keep their terraform.tfstate here', 'every build holds a .tflock while it runs']),
         result='Terraform gets a safe memory', link='stores', how_title='What the bucket keeps',
         how=[(I_doc, 'terraform.tfstate'), (I_docs, 'every old version'), (I_lock, 'encrypted SSE-S3'), (I_shield, 'never public')],
         note=['comes FIRST.', "Its own small state", 'stays in Jenkins', 'home (a bucket', "can't hold its own)"],
         steps=['In Jenkins: STEP = 01-state-bucket, ACTION = apply.', 'terraform init keeps this one small state in Jenkins home.',
                'terraform plan shows: 4 to add.', 'You click Yes, apply.',
                ('Terraform creates:', ['the bucket first', 'then versioning, encryption and the public access block']),
                'Check S3 › bucket: versioning on, SSE-S3, public access blocked.'],
         keys=['≈ $0 per month', 'about 1 minute', 'needed by every later step'],
         caption='Step 01: one S3 bucket with versioning, encryption and blocked public access. Steps 02 to 12 keep their Terraform state in it.'),
    dict(id='02', seed=202, title='How the *VPC Network* Works ?', need_icon=(I_tf, 'inputs'),
         need=('Inputs', 'vpc_cidr 10.0.0.0/16, zones 1a + 1b'), group='Terraform creates · step 02',
         box1=('① VPC', '10.0.0.0/16, DNS on'), box2=('② gateway + subnets', 'IGW, 6 subnets in 2 zones'),
         used=('Then used by', ['03 firewalls · 09 RDS (db subnets)', '10 NAT · 11 ALB (public subnets)', '12 ECS (private-app subnets)']),
         result='A private network in two zones', link='then ③ ④', how_title='③ route tables + ④ their links',
         how=[(I_cloud, 'internet'), (I_door, 'internet gateway'), (I_sign, 'public route 0.0.0.0/0'), (I_rooms, 'public subnets 1a + 1b')],
         note=['db subnets get', 'only the local', 'route: no internet', 'at all'],
         steps=['In Jenkins: STEP = 02-network, ACTION = apply.', 'terraform plan shows: 14 to add.', 'You click Yes, apply.',
                ('Terraform creates the VPC, then:', ['the internet gateway and the 6 subnets', 'the public and DB route tables and their links']),
                'The first state file lands in the S3 bucket.', 'Check VPC › Resource map: subnets → route tables → gateway.'],
         keys=['free', 'about 1 minute', '2 zones: one may fail'],
         caption='Step 02: the VPC, an internet gateway, six subnets in two zones and the route tables that decide who reaches the internet.'),
    dict(id='03', seed=303, title='How the *Security Groups* Work ?', need_icon=(I_rooms, 'step 02'),
         need=('From step 02', 'the VPC (vpc_id)'), group='Terraform creates · step 03',
         box1=('① 3 empty groups', 'alb-sg, ecs-sg, rds-sg'), box2=('② 5 rules', 'they name groups, not IPs'),
         used=('Then worn by', ['11 the load balancer → alb-sg', '12 the ECS tasks → ecs-sg', '09 the database → rds-sg']),
         result='Only ALB → ECS → RDS traffic', link='forms', how_title='The firewall chain',
         how=[(I_cloud, 'internet'), (I_shield, 'alb-sg'), (I_shield, 'ecs-sg'), (I_shield, 'rds-sg')],
         how_arrows=[(':80', 'G', False, False), (':8080', 'G', False, False), (':3306', 'G', False, False)],
         note=['groups first,', 'rules second:', 'alb-sg and ecs-sg', 'point at each other'],
         steps=['In Jenkins: STEP = 03-security-groups, ACTION = apply.', 'terraform plan shows: 8 to add (no HTTPS rule: count = 0).',
                'You click Yes, apply.', 'Terraform creates the 3 empty groups first.',
                ('Then the 5 rules:', ['in :80 from anywhere, out :8080 to ecs-sg', 'in :8080 from alb-sg, in :3306 from ecs-sg']),
                'Check EC2 › Security Groups (filter product-app).'],
         keys=['free', 'new task IPs need no rule change', 'the internet never reaches the DB'],
         caption='Step 03: three security groups and five rules; traffic may only flow internet → ALB on 80, ALB → ECS on 8080, ECS → RDS on 3306.'),
    dict(id='04', seed=404, title='How the *IAM Roles* Work ?', need_icon=(I_badge, 'mani-dev'),
         need=("mani-dev's policy", 'may create roles named product-app-*'), group='Terraform creates · step 04',
         box1=('① execution role', '+ ② AWS policy: pull image, write logs'), box2=('① task role', 'no permissions'),
         used=('Then used by', ['12 the ECS task definition (both ARNs)', '07 adds: read ONE secret']),
         result='No AWS keys in the container', link='ECS wears them', how_title='How ECS uses the badges',
         how=[(I_box, 'the task starts'), (I_badge, 'assumes both roles'), (I_key, 'temporary keys, ~1 hour'), (I_shelf, 'pulls the image')],
         note=['a role has no', 'stored keys: ECS', 'borrows them for', 'a short while'],
         steps=['In Jenkins: STEP = 04-iam-roles, ACTION = apply.', 'terraform plan shows: 3 to add.', 'You click Yes, apply.',
                'Terraform creates both roles; only ecs-tasks.amazonaws.com may assume them.',
                'It attaches AmazonECSTaskExecutionRolePolicy to the execution role.', 'Check IAM › Roles (IAM is global: no region).'],
         keys=['free', 'only ECS tasks can use them', 'mani-dev may pass them to ECS only'],
         caption='Step 04: an execution role with the AWS managed policy and an empty task role, both usable only by ECS tasks.'),
    dict(id='05', seed=505, title='How the *ECR Repository* Works ?', need_icon=(I_badge, 'mani-dev'),
         need=('mani-dev', 'ecr:* in Mumbai'), group='Terraform creates · step 05',
         box1=('① repository', 'product-app, scan on push'), box2=('② lifecycle policy', 'keep the last 10 images'),
         used=('Then used by', ['06 Jenkins pushes product-app:latest', '12 ECS pulls it with the execution role']),
         result='A private shelf for the image', link='gives', how_title='The image address, piece by piece',
         how_draw=lambda b: address(b), note=['tags can move:', 'push :latest again', 'and it points to', 'the new image'],
         steps=['In Jenkins: STEP = 05-ecr, ACTION = apply.', 'terraform plan shows: 2 to add.', 'You click Yes, apply.',
                'Terraform creates the repository: tags MUTABLE, AES-256, scan on push.',
                'Then the lifecycle rule that expires images beyond the newest 10.', 'Check ECR › Repositories › product-app (Images: empty).'],
         keys=['≈ $0.10 per GB-month', 'old images clean up by themselves', 'every push is scanned'],
         caption='Step 05: the private ECR repository product-app and its lifecycle rule. Jenkins pushes into it, ECS pulls from it.'),
    dict(id='06', seed=606, title='How the *Image* Gets to *ECR* ?', need_icon=(I_doc, 'Dockerfile'),
         need=('Dockerfile', 'the same one Docker Compose uses'), group='Jenkins runs · step 06 (no Terraform)', group_icon=I_gear,
         box1=('① docker build', 'for linux/amd64'), box2=('② docker push', 'after Yes, push'),
         used=('Then used by', ['12 ECS pulls product-app:latest', 'through the NAT gateway (10)']),
         result='Image in ECR, scan: 0 findings', link='inside', how_title='Inside the build and the push',
         how=[(I_gear, 'Maven builds the jar'), (I_box, 'JRE alpine + apk upgrade'), (I_key, 'ECR login, 12-hour token'), (I_shelf, 'ECR scans it')],
         note=['first scan found', '1 CRITICAL in zlib:', 'apk upgrade', 'fixed it'],
         steps=['In Jenkins: STEP = 06-push-image, ACTION = apply, IMAGE_TAG = latest.', 'Jenkins checks that the repository from step 05 exists.',
                ('docker build for linux/amd64 (2–5 min):', ['stage 1: Maven compiles the jar', 'stage 2: JRE alpine + apk upgrade, user app']),
                'You click Yes, push.', 'Login with a 12-hour token, push, logout.', 'Check ECR › product-app › Images: latest, 0 findings.'],
         keys=['same image locally and on AWS', 'no AWS keys in the image', '2–5 minutes'],
         caption='Step 06: Jenkins builds the image from the same Dockerfile as Docker Compose, waits for your approval, pushes it to ECR, and ECR scans it.'),
    dict(id='07', seed=707, title='How the *Database Secret* Works ?', need_icon=(I_badge, 'step 04'),
         need=('From step 04', 'the execution role'), group='Terraform creates · step 07',
         box1=('① random password', '24 characters, by Terraform'), box2=('② secret + value', 'user name + password'),
         used=('Then used by', ['09 RDS: the master password', '12 ECS: DB_USERNAME + DB_PASSWORD']),
         result='Nobody ever types the password', link='locks it', how_title='Who may open the safe',
         how=[(I_dice, 'random password'), (I_safe, 'db-credentials'), (I_key, 'read policy: this one only'), (I_badge, 'execution role')],
         note=['the state file', 'holds it too, so', 'the S3 bucket', 'is encrypted'],
         steps=['In Jenkins: STEP = 07-secrets, ACTION = apply.', 'terraform plan shows: 4 to add (values print as sensitive).', 'You click Yes, apply.',
                'Terraform rolls the password and stores it with the user name.', 'It lets the execution role read this one secret.',
                'Check Secrets Manager › Retrieve secret value.'],
         keys=['≈ $0.40 per month', 'encrypted at rest', 'destroy-all deletes it at once'],
         caption='Step 07: a random password and the user name stored in Secrets Manager; only the execution role may read this one secret.'),
    dict(id='08', seed=808, title='How the *Log Group* Works ?', need_icon=(I_tf, 'inputs'),
         need=('variables.tf', 'log_retention_days = 7'), group='Terraform creates · step 08',
         box1=('① log group', '/ecs/product-app-dev'), box2=('kept 7 days', 'not forever (the default)'),
         used=('Then used by', ['12 ECS: the awslogs driver', 'writes with the execution role']),
         result='You can read the app logs', link='later', how_title='What arrives in step 12',
         how=[(I_box, 'the task prints logs'), (I_nat, 'out via the NAT'), (I_docs, 'one stream per task'), (I_mag, 'search: Started')],
         note=['Fargate has no', 'server to SSH into:', 'logs are', 'your eyes'],
         steps=['In Jenkins: STEP = 08-cloudwatch-logs, ACTION = apply.', 'terraform plan shows: 1 to add.', 'You click Yes, apply.',
                'Terraform creates the log group with 7-day retention.', 'In step 12, ECS adds one stream per task.',
                'Check CloudWatch › Log groups › /ecs/product-app-dev.'],
         keys=['≈ $0 until logs arrive', 'JSON lines, easy to search', 'destroy-all removes it'],
         caption='Step 08: one CloudWatch log group kept seven days; in step 12 ECS writes one stream per task into it.'),
    dict(id='09', seed=909, title='How the *RDS Database* Works ?', need_icon=(I_rooms, 'subnets'),
         need=('From earlier steps', 'db subnets, rds-sg, the password'), group='Terraform creates · step 09',
         box1=('① DB subnet group', 'private-db 1a + 1b'), box2=('② MySQL instance', '8.4, db.t4g.micro, 20 GiB'),
         used=('Then used by', ['12 ECS: DB_HOST = the endpoint', 'Flyway creates the products table']),
         result='Private MySQL on port 3306', link='protects', how_title='Who can reach it',
         how=[(I_box, 'ECS task'), (I_shield, 'rds-sg'), (I_db, 'MySQL'), (I_cloud, 'internet')],
         how_arrows=[(':3306', 'G', False, False), ('', 'G', False, False), ('blocked', 'R', True, True)],
         note=['~8 minutes of', '"Still creating…":', "don't abort", 'the build!'],
         steps=['In Jenkins: STEP = 09-rds, ACTION = apply.', 'terraform plan shows: 2 to add.', 'You click Yes, apply.',
                'Terraform creates the subnet group, then the instance (about 8 minutes).', 'RDS goes Creating → Backing-up → Available.',
                'Check RDS › Connectivity: Publicly accessible = No; copy the endpoint.'],
         keys=['≈ $0.50 per day', 'encrypted, backups 1 day', 'single-AZ (dev setting)'],
         caption='Step 09: a DB subnet group over both private-db subnets, then the MySQL instance behind rds-sg. Only ECS can reach it, on 3306.'),
    dict(id='10', seed=1010, title='How the *NAT Gateway* Works ?', need_icon=(I_rooms, 'step 02'),
         need=('From step 02', 'public subnet 1a, internet gateway, app subnets'), group='Terraform creates · step 10',
         box1=('① Elastic IP', '+ ② NAT gateway in public 1a'), box2=('③ route table', '+ ④ links to the app subnets'),
         used=('Then used by', ['12 ECS tasks reach ECR,', 'Secrets Manager and CloudWatch']),
         result='Out: yes. In: never.', link='opens', how_title='The one-way door',
         how=[(I_box, 'ECS task, no public IP'), (I_nat, 'NAT gateway'), (I_door, 'internet gateway'), (I_cloud, 'ECR, Secrets, Logs')],
         how_arrows=[('out', 'G', False, False), ('', 'G', False, False), ('', 'G', False, False)], extra=red_back,
         note=["Terraform can't", 'see that ECS', 'needs this door,', 'so it gets its', 'own step'],
         steps=['In Jenkins: STEP = 10-nat-gateway, ACTION = apply.', 'terraform plan shows: 5 to add.', 'You click Yes, apply.',
                'Terraform creates the Elastic IP, then the NAT gateway (about 1 minute).', 'Then the private-app route table (0.0.0.0/0 → NAT) and its 2 links.',
                'Check VPC › NAT gateways: Available, in public subnet 1a.'],
         keys=['≈ $1.50 per day: the priciest part', 'without it, tasks cannot start', 'one NAT only (dev)'],
         caption='Step 10: an Elastic IP, a NAT gateway in public subnet 1a and a route that sends the app subnets to it. Tasks can call out; nothing can call in.'),
    dict(id='11', seed=1111, title='How the *Load Balancer* Works ?', need_icon=(I_user, 'users'),
         need=('From steps 02 + 03', 'public subnets and alb-sg'), group='Terraform creates · step 11',
         box1=('① load balancer', 'internet-facing, 2 public subnets'), box2=('① target group', 'HTTP :8080 + health check'),
         used=('Then used by', ['12 ECS registers each task IP:8080', 'users open http://<alb-dns-name>']),
         result='One stable public address', link='② listener :80', how_title="A request's path",
         how=[(I_user, 'a user'), (I_alb, 'listener :80'), (I_box, 'target group :8080'), (I_heart, 'health 200')],
         how_arrows=[('HTTP', 'G', False, False), ('forward', 'G', False, False), ('checks', 'R', False, False)],
         note=['until step 12 the', 'target group is', 'empty: the browser', 'gets 503'],
         steps=['In Jenkins: STEP = 11-load-balancer, ACTION = apply.', 'terraform plan shows: 3 to add.', 'You click Yes, apply.',
                'Terraform creates the ALB and the target group, then the listener (2–3 min).',
                'Health check: GET /actuator/health, 2 ok → healthy, 3 fails → out.', 'Open http://<DNS name>: 503 for now, which is correct.'],
         keys=['≈ $0.80 per day', 'the only public entry point', 'sick tasks get no traffic'],
         caption='Step 11: the load balancer and its target group, joined by an HTTP listener on 80. The target group stays empty until step 12.'),
    dict(id='12', seed=1212, title='How *ECS* Runs the *App* ?', need_icon=(I_shelf, 'all steps'),
         need=('From steps 04–11', 'roles, image, secret, logs, RDS, NAT, ALB'), group='Terraform creates · step 12',
         box1=('① task definition', '+ cluster: the recipe'), box2=('② service', 'keeps 1 task running'),
         used=('Then used by', ['users through the load balancer:', '/swagger-ui and /api/products']),
         result='product-app is live!', link='starts', how_title='When the task starts',
         how=[(I_shelf, 'pulls the image via NAT'), (I_safe, 'reads the password'), (I_db, 'Flyway → RDS :3306'), (I_heart, 'healthy in the ALB')],
         note=['if new tasks keep', 'failing, the circuit', 'breaker rolls back'],
         steps=['In Jenkins: STEP = 12-ecs, ACTION = apply.', 'terraform plan shows: 3 to add.', 'You click Yes, apply.',
                'Terraform creates the cluster and the task definition, then the service.',
                ('The task starts in a private-app subnet:', ['pulls the image, reads the secret, writes logs', 'Flyway creates the table, the ALB marks it healthy']),
                'Jenkins waits until stable; open /swagger-ui through the ALB.'],
         keys=['≈ $0.70 per day', '0.5 vCPU, 1 GB, Fargate', 'failed deploys roll back'],
         caption='Step 12: the task definition, the cluster and the service. When the task starts it uses everything built in steps 01 to 11.'),
]

def address(b):
    rows = [[('<account-id>', 'your account'), ('.dkr.ecr.', None), ('ap-south-1', 'region')],
            [('.amazonaws.com/', None), ('product-app', 'repository'), (':latest', 'tag')]]
    size = 22
    for r, parts in enumerate(rows):
        ws = [est(p, size) for p, _ in parts]; x = 513 - sum(ws) / 2; y = 420 + r * 64
        for (p, lab), wd in zip(parts, ws):
            b.t(x, y, p, None, size, fit=wd, check=False)
            if lab:
                b.poly([(x + 2, y + 9), (x + 2, y + 15), (x + wd - 2, y + 15), (x + wd - 2, y + 9)], 'O', 'w2')
                b.t(x + wd / 2, y + 34, lab, 'O', 17, 'middle')
            x += wd

# =============================================================================
STEPS = [
    ('01', 'Amazon S3', 'Terraform state bucket', 'terraform/bootstrap/main.tf · 4 resources · about 1 min · ≈ $0',
     "Terraform's memory. Every later step reads and writes its state file here, so this bucket comes first."),
    ('02', 'Amazon VPC', 'the network', 'terraform/vpc.tf · 14 resources · about 1 min · free',
     'The private network everything else lives in: one VPC, three kinds of subnet in two zones, and the routes that decide who reaches the internet.'),
    ('03', 'Security groups', 'the firewall chain', 'terraform/security_groups.tf · 8 resources · free',
     'Three firewalls that form a chain. Each layer only accepts traffic from the layer in front of it.'),
    ('04', 'AWS IAM', 'roles for ECS', 'terraform/iam.tf · 3 resources · free · IAM is global',
     "Two ID badges for ECS with no stored keys: one prepares the container, the other is the app's own."),
    ('05', 'Amazon ECR', 'the image repository', 'terraform/ecr.tf · 2 resources · storage ≈ $0.10 per GB-month',
     'The private shelf the Docker image is pushed to and ECS pulls from.'),
    ('06', 'Image to ECR', 'build and push', 'jenkins/Jenkinsfile + product-app/Dockerfile · no Terraform · 2–5 min',
     'Jenkins builds the same Dockerfile you use locally and uploads it. No Terraform runs in this step.'),
    ('07', 'AWS Secrets Manager', 'the database password', 'terraform/secrets.tf + iam.tf · 4 resources · ≈ $0.40 per month',
     'Terraform invents the database password and locks it in a safe. Nobody ever types it.'),
    ('08', 'Amazon CloudWatch Logs', 'the log group', 'terraform/cloudwatch.tf · 1 resource · ≈ $0 until logs arrive',
     "Where the container's output goes, because Fargate has no server you can log in to."),
    ('09', 'Amazon RDS', 'the MySQL database', 'terraform/rds.tf · 2 resources · 8–12 min · ≈ $0.50 per day',
     "The managed MySQL database, reachable only from the app's security group."),
    ('10', 'NAT gateway', 'the way out', 'terraform/vpc.tf · 5 resources · 1–2 min · ≈ $1.50 per day',
     'The one-way door that lets tasks in private subnets reach AWS APIs.'),
    ('11', 'Application Load Balancer', 'the front door', 'terraform/alb.tf · 3 resources · 2–3 min · ≈ $0.80 per day',
     'The only public entry point. It forwards requests to healthy tasks and checks /actuator/health.'),
    ('12', 'Amazon ECS on Fargate', 'the app starts', 'terraform/ecs.tf + ecs_service.tf · 3 resources · ≈ $0.70 per day',
     'Where every earlier step meets: the recipe, the supervisor, and the app starting up.'),
]
CSS = (HERE / 'sketchbook.css').read_text(encoding='utf-8')

THUMB_W = 480   # width of the small PNGs in docs/images/thumbs/ (overview grid of the page)

def sheet(svg, caption, key):
    # each board is also saved as a PNG next to this page (python generate.py --png)
    png = f'images/sketchbook-{PNG_NAMES[key]}.png'
    return (f'<figure><div class="sheet"><div class="scroll">{svg}</div></div><figcaption>{esc(caption)} '
            f'<a class="png" href="{png}" target="_blank" rel="noopener">Open this board as a PNG image</a></figcaption></figure>')

def thumb(key, svg, href, number, label):
    H = int(re.search(r'viewBox="0 0 \d+ (\d+)"', svg).group(1))
    alt = html.unescape(svg.split('aria-label="', 1)[1].split('"', 1)[0])
    return (f'<a href="{href}"><img src="images/thumbs/sketchbook-{PNG_NAMES[key]}.png" width="{THUMB_W}" '
            f'height="{round(H * THUMB_W / W)}" alt="{esc(alt)}" decoding="async"><span><b>{number}</b>{esc(label)}</span></a>')

def page():
    by_id = {d['id']: d for d in BOARDS}
    pipe = standard_board(by_id['pipeline']); arch = architecture()
    steps = {n: standard_board(by_id[n]) for n, *_ in STEPS}
    chips = ''.join(f'<a href="#step-{n}"><b>{n}</b>{esc(svc)}</a>' for n, svc, *_ in STEPS)
    thumbs = (thumb('pipeline', pipe, '#how-a-step-runs', '▶', 'how one step runs') + thumb('arch', arch, '#big-picture', '◎', 'the finished picture')
              + ''.join(thumb(n, steps[n], f'#step-{n}', n, svc) for n, svc, *_ in STEPS))
    secs = []
    for n, svc, what, meta, purpose in STEPS:
        spec = by_id[n]
        secs.append(f'''
<section id="step-{n}">
  <h2><span class="no">{n}</span><span>{esc(svc)}</span><span class="what">{esc(what)}</span></h2>
  <p class="meta">{esc(meta)}</p>
  <p class="purpose">{esc(purpose)}</p>
  {sheet(steps[n], spec['caption'], n)}
</section>''')
    return f'''<title>product-app AWS Sketchbook</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Patrick+Hand&family=JetBrains+Mono:wght@400&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header>
  <p class="kicker">product-app · Spring Boot + MySQL · Terraform · Jenkins · ap-south-1</p>
  <h1><span>product-app AWS Sketchbook</span></h1>
  <p class="lede">How Terraform builds each AWS service for product-app, one Jenkins step at a time, drawn by hand on one page per step: what goes in, what gets created and in which order, what it is used for, and the steps to run it.</p>
  <div class="legend">
    <span><i style="--c: var(--blue); --f: var(--paper)"></i>what goes in</span>
    <span><i style="--c: var(--green); --f: var(--paper)"></i>what Terraform creates</span>
    <span><i style="--c: var(--pink); --f: var(--f-pink)"></i><i style="--c: var(--purple); --f: var(--f-purple)"></i>the resources, in order ① ②</span>
    <span><i class="dash" style="--c: var(--orange); --f: var(--f-orange)"></i>how it works inside</span>
    <span><i style="--c: var(--purple); --f: var(--paper)"></i>the result</span>
  </div>
  <nav class="steps" aria-label="Jump to a step">
    <a href="#how-a-step-runs"><b>▶</b>how a step runs</a>
    <a href="#big-picture"><b>◎</b>big picture</a>
    {chips}
  </nav>
</header>
<section id="overview">
  <h2><span>All 14 boards at a glance</span></h2>
  <p class="purpose">Click a board to jump to it. Every board is also saved as a PNG image in <code>docs/images/</code>, used in the other guides; the link under each board opens it.</p>
  <div class="thumbs">{thumbs}</div>
</section>
<section id="how-a-step-runs">
  <h2><span>How one step runs</span></h2>
  <p class="meta">jenkins/Jenkinsfile · job product-app-aws-terraform · parameters STEP and ACTION</p>
  <p class="purpose">The same loop, twelve times. Only the STEP parameter changes, and with it the Terraform resources that are targeted.</p>
  {sheet(pipe, by_id['pipeline']['caption'], 'pipeline')}
</section>
<section id="big-picture">
  <h2><span>The finished picture</span></h2>
  <p class="meta">45 resources in the main state + 4 in the bootstrap state</p>
  <p class="purpose">Where every service sits once step 12 is done, and which way the traffic flows.</p>
  {sheet(arch, 'Requests come through the internet gateway to the load balancer (11), which forwards to the ECS task (12) in a private subnet. The task talks to MySQL (09) on 3306 and reaches ECR, Secrets Manager and CloudWatch Logs only outbound through the NAT gateway (10).', 'arch')}
</section>
{"".join(secs)}
<footer>
  <h2>Tearing it down</h2>
  <p>The Jenkins step <b>destroy-all</b> runs the same loop with <code>terraform plan -destroy</code>; you approve by typing <b>destroy</b>. Terraform deletes the 45 resources in reverse order: the ECS service first, the VPC last. The S3 state bucket from step 01 lives in its own configuration and stays until you delete it yourself.</p>
  <p class="src">Drawn by scripts/sketchbook/generate.py from terraform/*.tf, terraform/bootstrap/main.tf, jenkins/Jenkinsfile and docs/11-jenkins-terraform-step-by-step.md.</p>
</footer>
</div>'''

def standalone(content):
    # page() starts with <title>, <link> and <style>; they belong in <head>, the rest in <body>
    i = content.index('<div class="wrap">')
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + content[:i] + '\n</head>\n<body>\n' + content[i:] + '\n</body>\n</html>\n')

# ---- PNG export (python generate.py --png) ------------------------------------
PNG_DIR = OUT_DEFAULT.parent / 'images'
PNG_NAMES = {'pipeline': '00a-how-a-step-runs', 'arch': '00b-big-picture', '01': '01-s3-state-bucket', '02': '02-vpc-network',
             '03': '03-security-groups', '04': '04-iam-roles', '05': '05-ecr-repository', '06': '06-image-to-ecr',
             '07': '07-database-secret', '08': '08-log-group', '09': '09-rds-database', '10': '10-nat-gateway',
             '11': '11-load-balancer', '12': '12-ecs-app'}

def find_browser():
    """Edge or Chrome, used headless to turn each board into a PNG. Set SKETCH_BROWSER to override."""
    import os, shutil
    for c in (os.environ.get('SKETCH_BROWSER'),
              r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
              r'C:\Program Files\Google\Chrome\Application\chrome.exe', shutil.which('msedge'), shutil.which('google-chrome'),
              shutil.which('chromium'), shutil.which('chrome')):
        if c and Path(c).exists(): return c
    return None

def export_pngs(out_dir=PNG_DIR, width=1600):
    """One PNG per board, light 'paper' theme, `width` pixels wide (the drawing is 1000 units wide)."""
    import subprocess, tempfile
    browser = find_browser()
    if not browser:
        print('PNG export skipped: no Edge or Chrome found (set SKETCH_BROWSER to the browser .exe).'); return
    out_dir.mkdir(parents=True, exist_ok=True)
    by_id = {d['id']: d for d in BOARDS}
    boards = [('pipeline', standard_board(by_id['pipeline'])), ('arch', architecture())] + [(n, standard_board(by_id[n])) for n, *_ in STEPS]
    head = ('<meta charset="utf-8"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap">'
            f'<style>{CSS} html, body {{ margin: 0; background: var(--paper); }} svg {{ display: block; width: {width}px; height: auto; }}</style>')
    with tempfile.TemporaryDirectory() as tmp:
        for key, svg in boards:
            h = math.ceil(int(re.search(r'viewBox="0 0 \d+ (\d+)"', svg).group(1)) * width / W)
            src = Path(tmp) / f'{key}.html'
            src.write_text(f'<!doctype html><html lang="en" data-theme="light"><head>{head}</head><body>{svg}</body></html>', encoding='utf-8')
            png = out_dir / f'sketchbook-{PNG_NAMES[key]}.png'
            subprocess.run([browser, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
                            '--virtual-time-budget=8000', f'--window-size={width},{h}', f'--screenshot={png}', src.as_uri()],
                           check=True, capture_output=True, timeout=120)
            print(f"wrote {png} ({png.stat().st_size // 1024} KB)")

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')   # Windows consoles default to cp1252
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = Path(args[0]) if args else OUT_DEFAULT
    html_out = standalone(page())
    out.write_text(html_out, encoding='utf-8', newline='\n')
    print(f"wrote {out} ({len(html_out) // 1024} KB)")
    for w in WARN: print("WARN", w)
    if '--png' in sys.argv:
        export_pngs()                               # full size, used by the guides and the README
        export_pngs(PNG_DIR / 'thumbs', THUMB_W)    # small, used by the overview grid of the sketchbook page
