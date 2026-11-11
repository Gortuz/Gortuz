"""Builds the profile README poster panels as SVG, in the gortuz.dev Swiss poster system.

GitHub strips CSS from READMEs, so every piece of the design (Archivo at its
width axis, the 12-column grid, 2px rules, the diamond, purple and lime) lives
inside SVG panels with the font subset and embedded. One panel per section,
per language (es/en), per theme (light/dark).

Usage:
    python scripts/build.py [path/to/archivo-latin-standard-normal.woff2]

Requires: pip install fonttools brotli
"""

import base64
import io
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets'
FONT = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    ROOT.parent / 'gortuzdev/node_modules/@fontsource-variable/archivo/files/archivo-latin-standard-normal.woff2'
)
ICONS = json.loads((ROOT / 'scripts/icons.json').read_text())

# ---------------------------------------------------------------- tokens

THEMES = {
    'light': dict(
        ground='#fbf9f5', ground_alt='#f2ede4', ink='#1a0933', ink_soft='#2f2645', ink_muted='#625a78',
        action='#673ab7', rule='#1a0933', rule_quiet='rgba(26,9,51,0.16)', live='#8bd450', live_ink='#3d7a12',
        facet_dark='#1a0933',
    ),
    'dark': dict(
        ground='#121212', ground_alt='#1c1c1c', ink='#f5f5f5', ink_soft='#d4d4d4', ink_muted='#a3a3a3',
        action='#b39ddb', rule='#f5f5f5', rule_quiet='rgba(255,255,255,0.14)', live='#8bd450', live_ink='#8bd450',
        facet_dark='#311b92',
    ),
}
PLANE, PLANE_DEEP, EDGE = '#673ab7', '#311b92', '#161616'

# One face, varied by weight and width axis
STYLES = {
    'x': (800, 100),   # display, titles, email
    'w': (800, 125),   # section heads
    'c': (800, 75),    # figures, hero facts
    'r': (400, 100),   # body
    'm': (500, 100),   # labels, stack
    's': (600, 100),   # status, record titles, links
    'b': (700, 100),   # period, block titles, action
}

W, M, G = 960, 40, 24                     # canvas, margin, gutter (8px module)
C = (W - 2 * M - 11 * G) / 12             # column


def colx(i):
    return M + (i - 1) * (C + G)


def span(n):
    return n * C + (n - 1) * G


# ---------------------------------------------------------------- fonts

_base = TTFont(FONT)
_inst = {}


def inst(style):
    if style not in _inst:
        wght, wdth = STYLES[style]
        f = TTFont(FONT)
        _inst[style] = instantiateVariableFont(f, {'wght': wght, 'wdth': wdth})
    return _inst[style]


def measure(text, style, size, ls=0.0):
    f = inst(style)
    cmap, hmtx, upm = f.getBestCmap(), f['hmtx'], f['head'].unitsPerEm
    adv = sum(hmtx[cmap.get(ord(ch), cmap[ord('?')])][0] for ch in text)
    return adv * size / upm + ls * max(len(text) - 1, 0)


def wrap(text, style, size, width, ls=0.0):
    lines, cur = [], ''
    for word in text.split(' '):
        trial = f'{cur} {word}' if cur else word
        if cur and measure(trial, style, size, ls) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def font_face(style, chars):
    f = TTFont(io.BytesIO(_dump(inst(style))))
    opts = Options()
    opts.flavor = 'woff2'
    opts.layout_features = ['kern', 'liga', 'tnum', 'lnum']
    sub = Subsetter(opts)
    sub.populate(text=''.join(sorted(chars)) + ' ')
    sub.subset(f)
    f.flavor = 'woff2'
    data = base64.b64encode(_dump(f)).decode()
    return f"@font-face{{font-family:A{style};src:url(data:font/woff2;base64,{data}) format('woff2')}}"


def _dump(f):
    buf = io.BytesIO()
    f.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- canvas


class Panel:
    def __init__(self, theme):
        self.t = THEMES[theme]
        self.el = []
        self.chars = {}

    def text(self, x, y, s, style, size, fill, ls=0.0, anchor='start', features=''):
        self.chars.setdefault(style, set()).update(s)
        extra = f' text-anchor="{anchor}"' if anchor != 'start' else ''
        feat = f' style="font-feature-settings:{features}"' if features else ''
        self.el.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="A{style}" font-size="{size}" '
            f'letter-spacing="{ls:.2f}" fill="{fill}"{extra}{feat}>{escape(s)}</text>'
        )

    def lines(self, x, y, lines, style, size, fill, step, ls=0.0):
        for i, line in enumerate(lines):
            self.text(x, y + i * step, line, style, size, fill, ls)
        return y + (len(lines) - 1) * step

    def rect(self, x, y, w, h, fill):
        self.el.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"/>')

    def rule(self, x, y, w, h, color, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.el.append(
            f'<line x1="{x:.1f}" y1="{y + h / 2:.1f}" x2="{x + w:.1f}" y2="{y + h / 2:.1f}" '
            f'stroke="{color}" stroke-width="{h}"{d}/>'
        )

    def raw(self, s):
        self.el.append(s)

    def svg(self, height, bg, title):
        faces = ''.join(font_face(s, c) for s, c in sorted(self.chars.items()))
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height:.0f}" '
            f'viewBox="0 0 {W} {height:.0f}" role="img" aria-label="{escape(title)}">'
            f'<title>{escape(title)}</title><style>{faces}text{{white-space:pre}}</style>'
            f'<rect width="100%" height="100%" fill="{bg}"/>' + ''.join(self.el) + '</svg>'
        )


def diamond(cx, cy, size, edge=3):
    """The real logo, geometry copied from src/assets/logo.svg."""
    s = size / 214.95363
    outer = 'matrix(-0.0078539,-0.99996916,-0.99996916,0.0078539,215.79775,214.10943)'
    inner = 'matrix(-0.01570732,-0.99987663,-0.99987663,0.01570732,216.63516,213.25872)'
    return (
        f'<g transform="translate({cx - size / 2:.1f},{cy - size / 2:.1f}) scale({s:.5f})">'
        f'<g transform="{outer}">'
        f'<g transform="{inner}"><path d="M 1.41418,107.48 107.48,1.41422 213.546,107.48 107.48,213.546 Z" fill="{PLANE}"/>'
        f'<path d="M 94.86204,136.11506 107.22946,13.773675 209.90132,105.35664 Z" fill="{PLANE_DEEP}"/></g>'
        f'<path d="M 3.8411927,110.09462 108.63195,211.69365 79.441449,121.79808 Z" fill="#1a0933"/>'
        f'<g transform="{inner}"><path d="M 108.0748,75.685514 107.6121,1.5800008 209.91737,105.46337 Z" fill="#fff"/>'
        f'<path d="m 105.66542,76.596945 0.85649,2.464215 -103.4797363,28.93633 z m -4.89473,1.531191 6.39215,-1.969059 -0.70207,134.828093 z" fill="#fff"/></g>'
        f'<path d="M 105.81419,1.427285 213.5329,105.81419 109.14621,213.53294 1.4272879,109.14621 Z M 109.14621,213.53294 138.88977,107.02519 105.81419,1.427285 M 213.5329,105.81419 139.13369,106.94453 1.4272879,109.14621" '
        f'fill="none" stroke="{EDGE}" stroke-width="{edge}" stroke-miterlimit="16" vector-effect="non-scaling-stroke"/>'
        f'</g></g>'
    )


def arrow(x, y, color, size=18, diagonal=False):
    """Straight arrow, 2px square-capped strokes, miter joins. Diagonal = rotated 45°."""
    h = size / 2
    rot = f' rotate(-45 {h:.1f} 0)' if diagonal else ''
    return (
        f'<g transform="translate({x:.1f},{y:.1f}){rot}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="square" stroke-linejoin="miter"><path d="M0 0 H{size - 1}"/>'
        f'<path d="M{size - 7} -6 L{size - 1} 0 L{size - 7} 6"/></g>'
    )


# ---------------------------------------------------------------- panels


def hero(c, theme):
    p, t = Panel(theme), THEMES[theme]

    # Header strip: mark, domain, language switch
    p.raw(diamond(M + 14, 36, 28, edge=0.75))
    p.text(M + 38, 42, 'gortuz.dev', 'b', 16, t['ink'])
    lw = measure(c['lang'], 'b', 13, 0.52) + 16
    p.raw(f'<rect x="{W - M - lw:.1f}" y="21" width="{lw:.1f}" height="30" fill="none" stroke="{t["rule"]}" stroke-width="2"/>')
    p.text(W - M - lw / 2, 41, c['lang'], 'b', 13, t['ink'], 0.52, anchor='middle')
    p.rule(0, 71, W, 1, t['rule_quiet'])

    # The diamond at poster scale, cropped by the right edge
    p.raw(diamond(900, 400, 600))

    # Name
    p.text(M - 4, 219, 'Alan', 'x', 104, t['ink'], -4.16)
    p.text(M - 4, 310, 'Sandoval', 'x', 104, t['ink'], -4.16)

    # Role
    y = p.lines(M, 366, wrap(c['role'], 'r', 22, span(6)), 'r', 22, t['ink'], 29)

    # Status: the lime square is live state
    y += 40
    p.rect(M, y - 10, 8, 8, t['live'])
    p.raw(f'<rect x="{M - 2.5}" y="{y - 12.5}" width="13" height="13" fill="none" stroke="{t["live_ink"]}" stroke-width="1"/>')
    p.text(M + 20, y, c['status'], 's', 15, t['ink_soft'])

    # Three shipped facts, each on a 2px rule
    y += 40
    fw = (span(8) - 2 * G) / 3
    bottom = y
    for i, (value, label) in enumerate(c['facts']):
        x = M + i * (fw + G)
        p.rule(x, y, fw, 2, t['rule'])
        vy = p.lines(x, y + 36, wrap(value, 'c', 25, fw, -0.5), 'c', 25, t['action'], 26, -0.5)
        ly = p.lines(x, vy + 30, wrap(label, 'r', 14, fw), 'r', 14, t['ink_soft'], 20)
        bottom = max(bottom, ly)

    # The action: the email over a 3px purple rule
    y = bottom + 40
    p.rule(M, y, span(8), 3, t['action'])
    p.text(M, y + 38, c['email'], 'b', 20, t['ink'])
    gx = M + span(8) - 18
    p.raw(arrow(gx - 1, y + 31, t['action']))
    p.text(gx - 12, y + 38, c['write'], 'b', 20, t['action'], anchor='end')

    h = y + 80
    return p.svg(h, t['ground'], c['alt_hero'])


def work(c, theme):
    p, t = Panel(theme), THEMES[theme]

    p.text(M - 3, 128, c['work_heading'], 'w', 88, t['ink'], -3.52)
    intro = wrap(c['work_intro'], 'r', 18, span(5))
    p.lines(colx(8), 122 - (len(intro) - 1) * 26, intro, 'r', 18, t['ink_soft'], 26)

    y = 184
    sizes = {3: 46, 2: 38, 1: 30}
    for item in c['work']:
        # Past work: a broken rule (24px dash, 8px gap)
        p.rule(M, y, W - 2 * M, 2, t['rule'], dash='24 8')
        top = y + 40

        # Meta, columns 1-3
        mw = span(3)
        my = top + 12
        p.text(M, my, item['period'], 'b', 15, t['ink'], features="'tnum'")
        my = p.lines(M, my + 30, wrap(item['org'], 'r', 15, mw), 'r', 15, t['ink_soft'], 22)
        p.text(M, my + 22, item['place'], 'r', 15, t['ink_muted'])
        my += 22 + 20
        p.rule(M, my, mw, 1, t['rule_quiet'])
        my = p.lines(M, my + 24, wrap(item['role'], 'r', 15, mw), 'r', 15, t['ink_soft'], 22)

        # Body, columns 4-12: billed by weight
        bx, bw = colx(4), span(9)
        size = sizes[item['weight']]
        ls = -0.035 * size
        by = p.lines(bx - 2, top + 0.72 * size, wrap(item['title'], 'x', size, bw, ls), 'x', size, t['ink'], size, ls)
        by = p.lines(bx, by + 40, wrap(item['summary'], 'r', 18, bw), 'r', 18, t['ink'], 26)

        if item.get('figures'):
            fx, fy = bx, by + 64
            for value, label in item['figures']:
                p.text(fx - 1, fy, value, 'c', 46, t['action'], -1.38, features="'tnum','lnum'")
                p.text(fx, fy + 26, label, 'r', 13, t['ink_muted'])
                fx += max(144, measure(value, 'c', 46, -1.38), measure(label, 'r', 13)) + 48
            by = fy + 26

        for point in item['points']:
            lines = wrap(point, 'r', 15, bw - 32)
            p.rect(bx, by + 34 - 6, 16, 2, t['action'])
            by = p.lines(bx + 32, by + 34, lines, 'r', 15, t['ink_soft'], 22)

        by += 28
        p.rule(bx, by, bw, 1, t['rule_quiet'])
        p.text(bx, by + 28, ' / '.join(item['stack']), 'm', 15, t['ink_muted'])
        by += 28

        y = max(my, by) + 56

    return p.svg(y + 8, t['ground'], c['alt_work'])


def profile(c, theme):
    p, t = Panel(theme), THEMES[theme]
    p.rule(0, 0, W, 2, t['rule'])

    p.text(M - 3, 72 + 63, c['profile_heading'], 'w', 88, t['ink'], -3.52)

    bx, bw = colx(7), span(6)
    by = 72 + 18
    for i, para in enumerate(c['bio']):
        by = p.lines(bx, by + (0 if i == 0 else 42), wrap(para, 'r', 18, bw), 'r', 18, t['ink'], 27)
    by += 30
    p.rule(bx, by, bw, 1, t['rule_quiet'])
    p.text(bx, by + 28, c['languages'], 'r', 15, t['ink_muted'])
    y = max(by + 28, 140) + 80

    # Record: title on columns 1-3, rows on 4-12
    p.lines(M, y + 30, wrap(c['record_heading'], 'b', 18, span(3) - 8), 'b', 18, t['ink'], 24, -0.18)
    rx, rw = colx(4), span(9)
    p.rule(rx, y, rw, 2, t['rule'])
    cw = (rw - 2 * G) / 9.4
    w1, w2 = 5 * cw, 3 * cw
    ry = y + 2
    for title, detail, date in c['record']:
        a = wrap(title, 's', 16, w1)
        b = wrap(detail, 'r', 16, w2)
        p.lines(rx, ry + 30, a, 's', 16, t['ink'], 22)
        p.lines(rx + w1 + G, ry + 30, b, 'r', 16, t['ink_soft'], 22)
        if date:
            p.text(rx + rw, ry + 30, date, 'r', 16, t['ink_muted'], anchor='end')
        ry += 30 + (max(len(a), len(b)) - 1) * 22 + 18
        p.rule(rx, ry, rw, 1, t['rule_quiet'])
    y = ry + 72

    # Stack: five groups across the grid, each on a 2px rule, marks in currentColor
    p.text(M, y, c['stack_heading'], 'b', 18, t['ink'], -0.18)
    y += 28
    gw = (W - 2 * M - 4 * G) / 5
    bottom = y
    for i, (group, items) in enumerate(c['stack']):
        gx = M + i * (gw + G)
        p.rule(gx, y, gw, 2, t['rule'])
        gy = p.lines(gx, y + 30, wrap(group, 'b', 15, gw), 'b', 15, t['ink'], 20) + 12
        for name in items:
            lines = wrap(name, 'm', 15, gw - 26)
            gy += 26
            if name in ICONS:
                p.raw(f'<svg x="{gx:.1f}" y="{gy - 13:.1f}" width="16" height="16" viewBox="0 0 24 24">'
                      f'<path d="{ICONS[name]}" fill="{t["ink"]}"/></svg>')
            else:
                p.raw(f'<polygon points="{gx + 8:.1f},{gy - 11.5:.1f} {gx + 14.5:.1f},{gy - 5:.1f} '
                      f'{gx + 8:.1f},{gy + 1.5:.1f} {gx + 1.5:.1f},{gy - 5:.1f}" fill="none" '
                      f'stroke="{t["ink_muted"]}" stroke-width="1.5"/>')
            gy = p.lines(gx + 26, gy, lines, 'm', 15, t['ink_soft'], 20)
        bottom = max(bottom, gy)

    return p.svg(bottom + 96, t['ground_alt'], c['alt_profile'])


def contact(c, theme):
    p, t = Panel(theme), THEMES[theme]

    # Pre-compute heights so the 45° facet can fill the band in a fixed 1:2 box
    head = wrap(c['contact_heading'], 'w', 80, span(8), -3.2)
    body = wrap(c['contact_body'], 'r', 20, span(6))
    size = 44
    while measure(c['email'], 'x', size, -0.03 * size) > span(8) and size > 20:
        size -= 1
    hh = 96 + 58 + (len(head) - 1) * 74 + 52 + (len(body) - 1) * 29 + 52 + 3 + 24 + 0.72 * size + 52 + 96
    fx = W - hh / 2
    s = hh / 1000
    p.raw(f'<polygon points="{W},0 {W},{hh:.1f} {fx:.1f},{hh / 2:.1f}" fill="{PLANE}"/>')
    p.raw(f'<polygon points="{W},0 {fx:.1f},{hh / 2:.1f} {fx + 260 * s:.1f},{470 * s:.1f}" fill="{t["facet_dark"]}"/>')
    p.raw(f'<polyline points="{W},0 {fx:.1f},{hh / 2:.1f} {W},{hh:.1f}" fill="none" stroke="{EDGE}" stroke-width="3"/>')
    p.rule(0, 0, W, 2, t['rule'])

    y = p.lines(M - 3, 96 + 58, head, 'w', 80, t['ink'], 74, -3.2)
    y = p.lines(M, y + 52, body, 'r', 20, t['ink'], 29)

    y += 52
    p.rule(M, y, span(8), 3, t['ink'])
    p.text(M - 1, y + 3 + 24 + 0.72 * size, c['email'], 'x', size, t['action'], -0.03 * size)
    y += 3 + 24 + 0.72 * size + 52

    x = M
    for label in ('LinkedIn', 'GitHub'):
        p.text(x, y, label, 's', 19, t['ink'])
        x += measure(label, 's', 19) + 8
        p.raw(arrow(x, y - 7, t['ink'], size=15, diagonal=True))
        x += 40
    y += 96

    # Footer band
    p.rect(0, y, W, 72, t['ground_alt'])
    p.rule(0, y, W, 1, t['rule_quiet'])
    p.text(M, y + 41, c['footer'], 'm', 15, t['ink_soft'])
    p.text(W - M, y + 41, 'gortuz.dev', 'm', 15, t['ink_soft'], anchor='end')

    return p.svg(y + 72, t['ground'], c['alt_contact'])


# ---------------------------------------------------------------- run

if __name__ == '__main__':
    content = json.loads((ROOT / 'scripts/content.json').read_text())
    OUT.mkdir(exist_ok=True)
    for lang, c in content.items():
        for theme in THEMES:
            for name, fn in (('hero', hero), ('work', work), ('profile', profile), ('contact', contact)):
                path = OUT / f'{name}-{lang}-{theme}.svg'
                path.write_text(fn(c, theme))
                print(f'{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB')
