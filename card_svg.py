"""Completion card as a crafted SVG — neon "Futuristic Cyberpunk Dashboard" style.

HUD / sci-fi corner frame, faint hex background, glowing gradient trophy-shield,
electric-blue palette (master) / neon-green (beginner). Rendered inline on the
page and for PNG/SVG download so they're identical. Deterministic, dep-free.
"""
from __future__ import annotations
import html

W, H = 1200, 800

THEMES = {
    "master": {
        "navy1": "#050A14", "navy2": "#081327",
        "acc": "#009DFF", "azure": "#2A6CFF", "bright": "#48C8FF",
        "glow": "#009DFF", "tA": "#7FD4FF", "tB": "#2A6CFF", "shield": "#0A2murky",
    },
    "beginner": {
        "navy1": "#03130C", "navy2": "#06210F",
        "acc": "#12E08A", "azure": "#0BB56A", "bright": "#7CFFC0",
        "glow": "#12E08A", "tA": "#9CFFD0", "tB": "#0BB56A", "shield": "#08latch",
    },
}
MUTED, DIM, TEXT = "#93A6C9", "#63748F", "#FFFFFF"
FONT = "'Segoe UI',system-ui,-apple-system,Arial,sans-serif"
MONO = "'JetBrains Mono',ui-monospace,'Courier New',monospace"


def _e(s):
    return html.escape(str(s), quote=True)


def _name_lines(name):
    name = (name or "Player").strip()[:10]
    if len(name) <= 7:
        return [(name, 92)]
    return [(name, 76)]


def _corner(acc):
    return (
        f'<path d="M148 30 L74 30 L30 74 L30 148" fill="none" stroke="{acc}" stroke-width="3.5" stroke-linecap="round"/>'
        f'<path d="M176 30 L206 30" stroke="{acc}" stroke-width="3.5" stroke-linecap="round" opacity="0.85"/>'
        f'<path d="M30 176 L30 206" stroke="{acc}" stroke-width="3.5" stroke-linecap="round" opacity="0.85"/>'
        f'<rect x="20" y="20" width="9" height="9" fill="{acc}"/>'
        f'<path d="M44 70 L70 44 M52 82 L82 52" stroke="{acc}" stroke-width="1.6" opacity="0.7"/>'
    )


def _robot(x, y, acc, s=1.0):
    return (f'<g transform="translate({x},{y}) scale({s})" fill="none" stroke="{acc}" stroke-width="3">'
            f'<line x1="24" y1="4" x2="24" y2="12" stroke-linecap="round"/><circle cx="24" cy="4" r="3" fill="{acc}"/>'
            f'<rect x="7" y="12" width="34" height="27" rx="8"/>'
            f'<circle cx="17.5" cy="26" r="3.6" fill="{acc}"/><circle cx="30.5" cy="26" r="3.6" fill="{acc}"/>'
            f'<line x1="17.5" y1="33" x2="30.5" y2="33" stroke-linecap="round"/>'
            f'<line x1="2" y1="21" x2="2" y2="30" stroke-linecap="round"/><line x1="46" y1="21" x2="46" y2="30" stroke-linecap="round"/>'
            f'</g>')


def _github(x, y, fill, s=1.0):
    return (f'<path transform="translate({x},{y}) scale({s})" fill="{fill}" d="M12 .5A11.5 11.5 0 0 0 8.4 22.9'
            f'c.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.4-3.9-1.4-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.1.1 1.7 1.2 1.7 1.2'
            f' 1 1.7 2.6 1.2 3.3.9.1-.7.4-1.2.7-1.5-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.4-2.3 1.1-3.1-.1-.3-.5-1.5.1-3.1'
            f' 0 0 .9-.3 3 1.2a10.4 10.4 0 0 1 5.5 0c2.1-1.5 3-1.2 3-1.2.6 1.6.2 2.8.1 3.1.7.8 1.1 1.8 1.1 3.1'
            f' 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A11.5 11.5 0 0 0 12 .5Z"/>')


def _badge(level, acc, bright, right_x, y=64, h=54):
    w = 60 + len(level) * 15.5
    x = right_x - w
    cy = y + h / 2
    icon = (f'<g transform="translate({x+18},{cy-11})">'
            f'<path d="M11 0 2 3v6c0 6 4 9.5 9 11 5-1.5 9-5 9-11V3L11 0Z" fill="{acc}" fill-opacity="0.3" stroke="{bright}" stroke-width="1.6"/>'
            f'<path d="m7 10.5 2.6 2.6L15 7.5" fill="none" stroke="{bright}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></g>')
    txt = (f'<text x="{x+52}" y="{cy+7:.0f}" fill="{TEXT}" font-size="21" font-weight="700" '
           f'letter-spacing="2" font-family="{FONT}">{_e(level)}</text>')
    rect = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{acc}" fill-opacity="0.14" '
            f'stroke="{acc}" stroke-opacity="0.7" stroke-width="1.6" filter="url(#softglow)"/>')
    return rect + icon + txt


def _trophy(cx, cy, acc, bright, sfx):
    """Filled glowing shield + trophy + laurel + stars + circuits, with soft background glow."""
    lp = [(-64, 50), (-76, 26), (-80, 0), (-77, -26), (-66, -48)]
    laurel = ""
    for side in (-1, 1):
        pts = " ".join(f"{x*side:.0f},{y}" for x, y in lp)
        laurel += (f'<polyline points="{-20*side},56 {pts}" fill="none" stroke="{acc}" '
                   f'stroke-width="2" opacity="0.75"/>')
        for x, y in lp:
            cxl = x * side
            laurel += (f'<ellipse cx="{cxl:.0f}" cy="{y}" rx="10" ry="4.6" '
                       f'transform="rotate({side*-52} {cxl:.0f} {y})" fill="{acc}" fill-opacity="0.6"/>')
    return f'''<g transform="translate({cx},{cy})">
      <ellipse cx="0" cy="6" rx="148" ry="150" fill="{acc}" opacity="0.16" filter="url(#blur_{sfx})"/>
      <g filter="url(#glow_{sfx})">
        <g stroke="{acc}" stroke-width="2" opacity="0.6" fill="none">
          <path d="M-128 -30 H-176 M-176 -30 V-60 H-202"/><path d="M-128 10 H-192"/><path d="M-128 50 H-176 M-176 50 V80 H-202"/>
          <circle cx="-202" cy="-60" r="3.4" fill="{acc}"/><circle cx="-192" cy="10" r="3.4" fill="{acc}"/><circle cx="-202" cy="80" r="3.4" fill="{acc}"/>
        </g>
        <path d="M0 -140 L-128 -106 L-128 26 C-128 92 -70 132 0 158 C70 132 128 92 128 26 L128 -106 Z"
              fill="url(#shg_{sfx})" stroke="{acc}" stroke-width="4"/>
        <path d="M0 -120 L-108 -90 L-108 22 C-108 82 -58 116 0 138 C58 116 108 82 108 22 L108 -90 Z"
              fill="none" stroke="{bright}" stroke-width="1.6" opacity="0.45"/>
        <g fill="{bright}">
          <path d="M-52 -74l3 6 6 .9-4.5 4.2 1.1 6-5.6-3-5.6 3 1.1-6-4.5-4.2 6-.9 3-6Z"/>
          <path d="M0 -88l3.6 7.4 8 1.1-5.8 5.4 1.4 8-7.2-3.8-7.2 3.8 1.4-8-5.8-5.4 8-1.1 3.6-7.4Z"/>
          <path d="M52 -74l3 6 6 .9-4.5 4.2 1.1 6-5.6-3-5.6 3 1.1-6-4.5-4.2 6-.9 3-6Z"/>
        </g>
        {laurel}
        <path d="M-48 -40 H48 v20 c0 26-22 46-48 46 s-48-20-48-46 v-20Z" fill="url(#tg_{sfx})" stroke="{bright}" stroke-width="2.6"/>
        <path d="M-48 -34 H-70 c-14 0-14 30 18 34 M48 -34 H70 c14 0 14 30-18 34" fill="none" stroke="{bright}" stroke-width="2.6" stroke-linecap="round"/>
        <path d="M0 32 v26 M-28 74 h56 M-22 60 h44 l-5 14 h-34 Z" fill="url(#tg_{sfx})" stroke="{bright}" stroke-width="2.6" stroke-linejoin="round"/>
        <g transform="translate(-15,-26) scale(0.62)"><path fill="#FFFFFF" fill-opacity="0.92" d="M24 2l6.6 13.4 14.8 2.1-10.7 10.4 2.5 14.7L24 35.7 10.8 42.6l2.5-14.7L2.6 17.5l14.8-2.1L24 2Z"/></g>
      </g>
    </g>'''


def _flag(x, y, acc):
    return (f'<g transform="translate({x},{y})">'
            f'<path d="M3 0 V60" stroke="{acc}" stroke-width="4" stroke-linecap="round"/>'
            f'<path d="M8 4 H50 V34 H8 Z" fill="{acc}" fill-opacity="0.85"/>'
            f'<g fill="{acc}"><rect x="8" y="4" width="14" height="10"/><rect x="36" y="4" width="14" height="10"/>'
            f'<rect x="22" y="14" width="14" height="10"/><rect x="8" y="24" width="14" height="10"/><rect x="36" y="24" width="14" height="10"/></g>'
            f'</g>')


def _star(x, y, acc, s=1.0):
    return (f'<path transform="translate({x},{y}) scale({s})" fill="{acc}" '
            f'd="M24 2l6.6 13.4 14.8 2.1-10.7 10.4 2.5 14.7L24 35.7 10.8 42.6l2.5-14.7L2.6 17.5l14.8-2.1L24 2Z"/>')


def _bullets(items, acc, start_y):
    out, x, y = [], 66, start_y
    for b in items:
        w = 22 + len(b) * 9.2 + 30
        if x + w > 780 and x > 66:
            x = 66; y += 34
        out.append(f'<circle cx="{x+4:.0f}" cy="{y-5:.0f}" r="3" fill="{acc}"/>')
        out.append(f'<text x="{x+18:.0f}" y="{y:.0f}" fill="#DBE6F7" font-size="17">{_e(b)}</text>')
        x += w
    return "\n".join(out)


def render(variant, level, name, count, score, desc, bullets, date, repo_display, author, app_name):
    t = THEMES.get(variant, THEMES["master"])
    acc, bright, glow = t["acc"], t["bright"], t["glow"]
    sfx = variant

    corners = "".join([
        f'<g>{_corner(acc)}</g>',
        f'<g transform="translate({W},0) scale(-1,1)">{_corner(acc)}</g>',
        f'<g transform="translate(0,{H}) scale(1,-1)">{_corner(acc)}</g>',
        f'<g transform="translate({W},{H}) scale(-1,-1)">{_corner(acc)}</g>',
    ])

    lines = _name_lines(name)
    name_svg, ny = "", 268 + lines[0][1]
    for i, (ln, size) in enumerate(lines):
        if i > 0:
            ny += size + 8
        name_svg += (f'<text x="62" y="{ny}" fill="{TEXT}" font-size="{size}" font-weight="800" '
                     f'font-family="{FONT}" filter="url(#softglow)">{_e(ln)}</text>')
    desc_y = ny + 36
    bullets_svg = _bullets(bullets, acc, desc_y + 44)

    right_x = W - 54
    badge = _badge(level, acc, bright, right_x)
    urlw = len(repo_display) * 8.4
    gh_x = (W - 78) - urlw - 26

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
  <defs>
    <linearGradient id="bg_{sfx}" x1="0" y1="0" x2="0.6" y2="1">
      <stop offset="0" stop-color="{t['navy1']}"/><stop offset="1" stop-color="{t['navy2']}"/></linearGradient>
    <radialGradient id="rg_{sfx}" cx="80%" cy="44%" r="50%">
      <stop offset="0" stop-color="{glow}" stop-opacity="0.20"/><stop offset="1" stop-color="{glow}" stop-opacity="0"/></radialGradient>
    <linearGradient id="word_{sfx}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{acc}"/><stop offset="1" stop-color="{bright}"/></linearGradient>
    <linearGradient id="tg_{sfx}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{t['tA']}"/><stop offset="1" stop-color="{t['tB']}"/></linearGradient>
    <linearGradient id="shg_{sfx}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{acc}" stop-opacity="0.16"/><stop offset="1" stop-color="{acc}" stop-opacity="0.03"/></linearGradient>
    <pattern id="hex_{sfx}" width="72" height="41.57" patternUnits="userSpaceOnUse">
      <g fill="none" stroke="{acc}" stroke-opacity="0.055" stroke-width="1">
        <path d="M-24 0 L-12 -20.785 L12 -20.785 L24 0 L12 20.785 L-12 20.785 Z"/>
        <path d="M12 20.785 L24 0 L48 0 L60 20.785 L48 41.57 L24 41.57 Z"/>
      </g>
    </pattern>
    <filter id="glow_{sfx}" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="2.8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <filter id="softglow_{sfx}" x="-20%" y="-40%" width="140%" height="180%">
      <feGaussianBlur stdDeviation="1" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <filter id="blur_{sfx}" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="22"/></filter>
  </defs>

  <rect width="{W}" height="{H}" rx="18" fill="url(#bg_{sfx})"/>
  <rect width="{W}" height="{H}" rx="18" fill="url(#hex_{sfx})"/>
  <rect width="{W}" height="{H}" rx="18" fill="url(#rg_{sfx})"/>
  <rect x="2" y="2" width="{W-4}" height="{H-4}" rx="17" fill="none" stroke="{acc}" stroke-opacity="0.16" stroke-width="1.1"/>
  <g stroke="{acc}" fill="none" stroke-linecap="round" filter="url(#softglow_{sfx})">
    <path d="M158 20 H{W-158} M158 {H-20} H{W-158} M20 158 V{H-158} M{W-20} 158 V{H-158}" stroke-width="1.8" opacity="0.6"/>
    <path d="M168 30 H{W-168} M168 {H-30} H{W-168} M30 168 V{H-168} M{W-30} 168 V{H-168}" stroke-width="0.9" opacity="0.3"/>
  </g>
  <g filter="url(#glow_{sfx})">{corners}</g>

  {_robot(62, 58, acc, 1.15)}
  <text x="140" y="106" fill="url(#word_{sfx})" font-size="46" font-weight="800" filter="url(#softglow_{sfx})">{_e(app_name)}</text>

  {badge}
  <rect x="{right_x-326}" y="134" width="326" height="50" rx="12" fill="{t['navy1']}" fill-opacity="0.4" stroke="{acc}" stroke-width="2"/>
  <rect x="{right_x-321}" y="139" width="316" height="40" rx="9" fill="none" stroke="{bright}" stroke-opacity="0.35" stroke-width="1"/>
  <text x="{right_x-163}" y="166" fill="{bright}" font-size="21" font-weight="700" letter-spacing="1" text-anchor="middle">OWASP LLM TOP 10 &#8226; 2025</text>

  <text x="66" y="234" font-size="19">&#128275;</text><text x="98" y="232" fill="{MUTED}" font-size="17" letter-spacing="7" font-family="{MONO}">ACHIEVEMENT UNLOCKED</text>
  <text x="66" y="272" fill="{acc}" font-size="25" font-weight="700" letter-spacing="2" filter="url(#softglow_{sfx})">MILESTONE ACHIEVED</text>
  {name_svg}
  <text x="66" y="{desc_y}" fill="{MUTED}" font-size="17">{_e(desc)}</text>
  {bullets_svg}

  {_flag(70, 620, acc)}
  <text x="150" y="670" fill="{TEXT}" font-size="66" font-weight="800" font-family="{FONT}">{_e(count)}</text>
  <text x="152" y="696" fill="{MUTED}" font-size="15" letter-spacing="3" font-family="{MONO}">LABS CLEARED</text>
  <line x1="330" y1="620" x2="330" y2="684" stroke="{acc}" stroke-opacity="0.4" stroke-width="2"/>
  {_star(372, 620, acc, 1.15)}
  <text x="452" y="670" fill="{TEXT}" font-size="66" font-weight="800" font-family="{FONT}">{_e(score)}</text>
  <text x="454" y="696" fill="{MUTED}" font-size="15" letter-spacing="3" font-family="{MONO}">SCORE</text>

  <line x1="66" y1="722" x2="{W-66}" y2="722" stroke="{acc}" stroke-opacity="0.25" stroke-width="1.5"/>
  <g transform="translate(94,739)"><rect x="0" y="0" width="18" height="17" rx="3" fill="none" stroke="{DIM}" stroke-width="1.6"/><line x1="0" y1="5.5" x2="18" y2="5.5" stroke="{DIM}" stroke-width="1.6"/><line x1="5" y1="0" x2="5" y2="-3" stroke="{DIM}" stroke-width="1.6"/><line x1="13" y1="0" x2="13" y2="-3" stroke="{DIM}" stroke-width="1.6"/></g>
  <text x="120" y="752" fill="{DIM}" font-size="14" font-family="{MONO}">{_e(date)}</text>
  <text x="{W//2}" y="752" fill="{DIM}" font-size="14" text-anchor="middle" font-family="{MONO}">built by&#160;<tspan fill="{bright}" font-weight="700">{_e(author)}</tspan></text>
  {_github(gh_x, 739, DIM, 0.8)}
  <text x="{gh_x+26}" y="752" fill="{DIM}" font-size="14" font-family="{MONO}">{_e(repo_display)}</text>

  {_trophy(972, 384, acc, bright, sfx)}
</svg>'''
