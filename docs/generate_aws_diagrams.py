#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS-style architecture diagrams for GreenNode AgentBase — generator.

Render 3 self-contained HTML + SVG diagrams (AWS Architecture Diagram style):
  1. agentbase-network-map.html   — master map (runtime placement + break-out + 3 MCP groups)
  2. usecase-public-cloud.html    — UC1: agent PUBLIC mode (tavily + stock-mcp)
  3. usecase-private-onprem.html  — UC2: agent VPC mode + MCP on-premise qua VPN/Interconnect
"""
import html as H
import pathlib

DOC = pathlib.Path(__file__).resolve().parent

# ── AWS palette ──────────────────────────────────────────────────────────────
INK = "#16191F"        # text chính (AWS Squid Ink)
SLATE = "#545B64"      # text phụ / line
BORDER = "#879596"     # dashed boundary
SUB_BORDER = "#B6C2CF" # subnet border
PANEL = "#232F3E"      # on-prem navy
RED = "#DD344C"
ORANGE = "#ED7100"

GRADS = {
    "compute": ("g-compute", "#FF9900", "#D45B07"),
    "network": ("g-network", "#A166FF", "#8C4FFF"),
    "ml": ("g-ml", "#01C2A8", "#01A88D"),
    "db": ("g-db", "#D324C7", "#9E16B0"),
    "store": ("g-store", "#8FC33A", "#6BA644"),
    "dark": ("g-dark", "#3B4A5A", "#28323E"),
}


def defs() -> str:
    parts = ['<defs>']
    for key, (gid, top, bottom) in GRADS.items():
        parts.append(
            f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>')
    for mid, color in [("mk", SLATE), ("mkd", INK), ("mko", ORANGE), ("mkr", RED)]:
        parts.append(
            f'<marker id="{mid}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7.5" '
            f'markerHeight="7.5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{color}"/></marker>')
    parts.append('</defs>')
    return "".join(parts)


def ttext(x, y, s, size=12, weight=600, color=INK, anchor="start", halo=False, italic=False):
    style = ' paint-order:stroke;stroke:#FFFFFF;stroke-width:3.5;stroke-linejoin:round;' if halo else ''
    font = ' font-style:italic;' if italic else ''
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" '
            f'text-anchor="{anchor}" style="{style}{font}">{H.escape(s)}</text>')


def tile(x, y, grad, glyph, s=52):
    gid = GRADS[grad][0]
    out = [f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="9" fill="url(#{gid})"/>']
    out.append(GLYPHS[glyph](x, y))
    return "".join(out)


def _p(d, w=2.4, fill="none", color="#FFFFFF"):
    return f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


GLYPHS = {
    # compute / runtime — ô vuông có 2 thanh dọc (EC2-ish)
    "compute": lambda x, y: _p(f"M{x+14} {y+15}h24v22h-24z") + _p(f"M{x+22} {y+15}v22", 2) + _p(f"M{x+30} {y+15}v22", 2),
    # database cylinder
    "db": lambda x, y: _p(f"M{x+15} {y+17}a11 4.5 0 0 1 22 0v17a11 4.5 0 0 1 -22 0z")
        + _p(f"M{x+15} {y+17}a11 4.5 0 0 0 22 0") + _p(f"M{x+15} {y+26}a11 4.5 0 0 0 22 0", 1.8),
    # gateway — cổng + mũi tên xuyên qua
    "gateway": lambda x, y: _p(f"M{x+12} {y+26}h26", 2.6) + f'<path d="M{x+40} {y+26}l-7-4.5v9z" fill="#FFFFFF"/>'
        + f'<rect x="{x+20}" y="{y+16}" width="3.6" height="20" fill="#FFFFFF"/><rect x="{x+28}" y="{y+16}" width="3.6" height="20" fill="#FFFFFF"/>',
    # AI — 3 node nối nhau
    "ai": lambda x, y: _p(f"M{x+17} {y+18}L{x+35} {y+18}M{x+17} {y+18}L{x+26} {y+33}M{x+35} {y+18}L{x+26} {y+33}", 2)
        + f'<circle cx="{x+17}" cy="{y+18}" r="3.4" fill="#FFFFFF"/><circle cx="{x+35}" cy="{y+18}" r="3.4" fill="#FFFFFF"/><circle cx="{x+26}" cy="{y+33}" r="3.4" fill="#FFFFFF"/>',
    # globe
    "globe": lambda x, y: _p(f"M{x+26} {y+14}a12 12 0 1 0 0.01 0") + _p(f"M{x+14} {y+26}h24") + _p(f"M{x+26} {y+14}a5.5 12 0 0 0 0 24a5.5 12 0 0 0 0 -24", 1.8),
    # chart tăng
    "chart": lambda x, y: _p(f"M{x+13} {y+36}L{x+20} {y+27}L{x+26} {y+31}L{x+39} {y+15}", 2.6)
        + f'<circle cx="{x+39}" cy="{y+15}" r="2.4" fill="#FFFFFF"/>',
    # vpn — 2 mũi tên ngược chiều
    "vpn": lambda x, y: _p(f"M{x+12} {y+19}h24", 2.4) + f'<path d="M{x+40} {y+19}l-6-4v8z" fill="#FFFFFF"/>'
        + _p(f"M{x+40} {y+31}h-24", 2.4) + f'<path d="M{x+12} {y+31}l6-4v8z" fill="#FFFFFF"/>',
    # db trắng (cho panel navy)
    "db_white": lambda x, y: GLYPHS["db"](x, y),
}


def svc(x_text, y_name, name, sub, color=INK, subcolor=SLATE):
    return ttext(x_text, y_name, name, 12, 600, color) + ttext(x_text, y_name + 16, sub, 9.5, 400, subcolor)


def tab(x, y, title, color=INK, border=BORDER):
    w = int(len(title) * 6.6) + 18
    return (f'<rect x="{x}" y="{y}" width="{w}" height="24" fill="#FFFFFF" stroke="{border}" stroke-width="1"/>'
            + ttext(x + 9, y + 16.5, title, 11, 600, color))


def dashed_box(x, y, w, h, title):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="none" stroke="{BORDER}" '
            f'stroke-width="1.6" stroke-dasharray="7 5"/>') + tab(x + 12, y + 12, title)


def subnet(x, y, w, h, title, private=False):
    t = title + ("  🔒" if False else "")
    out = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#FBFCFD" stroke="{SUB_BORDER}" stroke-width="1.3"/>')
    out += tab(x + 12, y + 12, title)
    if private:
        out += LOCK(x + 12 + int(len(title) * 6.6) + 30, y + 24)
    return out


def LOCK(cx, cy):
    return (f'<rect x="{cx-7}" y="{cy-1}" width="14" height="11" rx="2" fill="{SLATE}"/>'
            + _p(f"M{cx-4.5} {cy-1}v-2.5a4.5 4.5 0 0 1 9 0v2.5", 2.2, color=SLATE))


def navy_panel(x, y, w, h, title, sub):
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{PANEL}"/>'
    out += ttext(x + 16, y + 28, title, 12.5, 700, "#FFFFFF")
    out += ttext(x + 16, y + 46, sub, 10, 400, "#D5DBDB")
    return out


def route_card(x, y, w, h, title, lines):
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#F7F8F9" stroke="{SUB_BORDER}" stroke-width="1.2"/>'
    out += ttext(x + 14, y + 24, title, 11, 700)
    yy = y + 46
    for ln in lines:
        out += ttext(x + 14, yy, ln, 9.8, 400, SLATE)
        yy += 19
    return out


def arrow(pts, variant="default", label=None, lx=None, ly=None, dash=False, anchor="middle"):
    style = {"default": (SLATE, 1.7, "mk"), "emphasis": (INK, 2.5, "mkd"),
             "orange": (ORANGE, 3.6, "mko"), "red": (RED, 2.2, "mkr")}[variant]
    color, width, marker = style
    dashattr = ' stroke-dasharray="7 5"' if dash else ''
    p = " ".join(f"{a},{b}" for a, b in pts)
    out = (f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{width}"{dashattr} marker-end="url(#{marker})"/>')
    if label:
        out += ttext(lx, ly, label, 9.8, 600, SLATE if variant != "emphasis" else INK, anchor, halo=True)
    return out


def person(cx, cy):
    return (f'<circle cx="{cx}" cy="{cy-10}" r="6.5" fill="{SLATE}"/>'
            + f'<path d="M{cx-11} {cy+11}a11 11 0 0 1 22 0z" fill="{SLATE}"/>')


def crossed(x1, y1, x2, y2, cx, cy):
    return (f'<polyline points="{x1},{y1} {x2},{y2}" fill="none" stroke="{SUB_BORDER}" stroke-width="1.7" stroke-dasharray="7 5"/>'
            + f'<circle cx="{cx}" cy="{cy}" r="12" fill="#FFFFFF" stroke="{RED}" stroke-width="2.2"/>'
            + _p(f"M{cx-6} {cy-6}L{cx+6} {cy+6}M{cx+6} {cy-6}L{cx-6} {cy+6}", 2.6, color=RED))


def shell(title, subtitle, svg, w, h, legend, fname):
    lg = "".join(
        f'<span class="chip"><span class="dot" style="background:{c}"></span>{H.escape(t)}</span>'
        for c, t in legend)
    return f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{H.escape(title)} — AWS style</title>
<style>
  body{{margin:0;background:#FAFAFA;color:{INK};font-family:'Segoe UI',Helvetica,Arial,sans-serif}}
  .wrap{{max-width:{w + 80}px;margin:0 auto;padding:28px 40px 48px}}
  h1{{font-size:20px;margin:0 0 4px}} .sub{{font-size:13px;color:{SLATE};margin:0 0 16px}}
  .btns{{display:flex;gap:10px;margin:0 0 18px}}
  button{{border:0;border-radius:6px;padding:8px 16px;font-size:12.5px;font-weight:600;cursor:pointer}}
  .b1{{background:#EC7211;color:#fff}} .b2{{background:#fff;color:{INK};border:1px solid {BORDER}!important}}
  .card{{background:#fff;border:1px solid #E9ECEE;border-radius:10px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,.05)}}
  .legend{{display:flex;flex-wrap:wrap;gap:14px;margin-top:14px;font-size:12px;color:{SLATE}}}
  .chip{{display:inline-flex;align-items:center;gap:6px}}
  .dot{{width:12px;height:12px;border-radius:3px;display:inline-block;border:1px solid rgba(0,0,0,.15)}}
  svg{{display:block;width:100%;height:auto}}
</style></head><body><div class="wrap">
<h1>{H.escape(title)}</h1><p class="sub">{H.escape(subtitle)}</p>
<div class="btns"><button class="b1" onclick="dl('png')">Download PNG (2x)</button><button class="b2" onclick="dl('svg')">Download SVG</button></div>
<div class="card">{svg}<div class="legend">{lg}</div></div>
</div><script>
const NAME='{fname}';
function dl(t){{
 const s=document.querySelector('svg');const x=new XMLSerializer().serializeToString(s);
 const u='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(x);
 if(t==='svg'){{const a=document.createElement('a');a.href=u;a.download=NAME+'.svg';a.click();return;}}
 const i=new Image();i.onload=()=>{{const c=document.createElement('canvas');const k=2;
  c.width=s.width.baseVal.value*k;c.height=s.height.baseVal.value*k;const g=c.getContext('2d');
  g.fillStyle='#fff';g.fillRect(0,0,c.width,c.height);g.drawImage(i,0,0,c.width,c.height);
  c.toBlob(b=>{{const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=NAME+'.png';a.click();}});}};
 i.src=u;}}
</script></body></html>"""


LEGEND = [
    ("#ED7100", "Compute — AgentBase Runtime"),
    ("#8C4FFF", "Networking — MCP Gateway · VPN"),
    ("#01A88D", "AI — LLM AIP"),
    ("#C925D1", "Database — Memory · MCP data"),
    ("#6BA644", "Internet MCP (SaaS)"),
    ("#232F3E", "On-Premise KH"),
]


# ═══════════════════════════ 1. MASTER MAP ═══════════════════════════════════
def build_master() -> str:
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1560" height="1000" viewBox="0 0 1560 1000" font-family="Segoe UI,Helvetica,Arial,sans-serif">', defs()]

    # Users
    s.append(person(110, 250)); s.append(person(145, 244)); s.append(person(180, 250))
    s.append(ttext(145, 292, "Users", 12, 700, anchor="middle"))
    s.append(ttext(145, 308, "browser · webhook · A2A client", 9.5, 400, SLATE, "middle"))

    # GreenNode Cloud + VPC + subnets
    s.append(dashed_box(250, 60, 830, 900, "GreenNode Cloud — vNG Cloud (vServer)"))
    s.append(dashed_box(290, 130, 360, 790, "VPC của KH"))
    s.append(subnet(310, 180, 320, 250, "Public subnet"))
    s.append(tile(400, 270, "compute", "compute"))
    s.append(svc(466, 290, "AgentBase Runtime", "PUBLIC mode · public URL"))
    s.append(ttext(466, 322, "app + LangGraph + AgentBase SDK", 9, 400, SLATE))

    s.append(subnet(310, 460, 320, 220, "Private subnet", private=True))
    s.append(tile(400, 545, "compute", "compute"))
    s.append(svc(466, 565, "AgentBase Runtime", "VPC mode · no egress"))
    s.append(ttext(466, 597, "caller: app nội bộ VPC", 9, 400, SLATE, italic=True))

    s.append(route_card(310, 710, 320, 150, "VPC route table", [
        "local  → trong VPC",
        "0.0.0.0/0  → platform edge (public)",
        "10.60.0.0/16  → VGW (VPN / DX)",
        "= routeCidrs của runtime / gateway"]))

    # Platform managed
    s.append(dashed_box(690, 130, 360, 790, "AgentBase Platform — managed"))
    s.append(tile(720, 200, "ml", "ai"))
    s.append(svc(786, 220, "LLM AIP", "GLM · OpenAI-compat · API key"))
    s.append(tile(720, 340, "db", "db"))
    s.append(svc(786, 360, "Memory + Identity", "SDK · history + facts · secret"))
    s.append(tile(720, 500, "network", "gateway"))
    s.append(svc(786, 520, "MCP Gateway", "policy · outbound auth"))
    s.append(tile(720, 650, "db", "chart"))
    s.append(svc(786, 670, "stock-mcp", "MCP · Cloud · API key inbound"))

    # Internet + tavily
    s.append(dashed_box(1180, 120, 320, 220, "Internet"))
    s.append(tile(1250, 200, "store", "globe"))
    s.append(svc(1316, 220, "MCP · Internet", "Tavily (SaaS) — APIKEY"))

    # On-prem
    s.append(navy_panel(1180, 560, 320, 300, "Corporate Data Center", "On-Premise KH — mạng riêng"))
    s.append(tile(1250, 650, "dark", "db_white"))
    s.append(svc(1316, 670, "MCP On-Premise", "ERP · DB · legacy", "#FFFFFF", "#D5DBDB"))
    s.append(ttext(1196, 830, "không expose Internet · CIDR riêng", 9.5, 400, "#D5DBDB", italic=True))

    # VPN/DX giữa cloud và on-prem
    s.append(tile(1040, 640, "network", "vpn"))
    s.append(ttext(1066, 716, "Direct Connect · Site-to-Site VPN", 9.5, 600, SLATE, "middle", halo=True))

    # Arrows
    s.append(arrow([(170, 240), (400, 296)], "emphasis", "HTTPS · public URL", 280, 256))
    s.append(arrow([(620, 288), (720, 226)], "default", "chat completions · API key", 660, 250))
    s.append(arrow([(620, 302), (720, 366)], "default", "SDK · history + facts", 660, 350))
    s.append(arrow([(620, 316), (720, 526)], "emphasis", "tools/call · IAM", 606, 420))
    s.append(arrow([(620, 570), (720, 532)], "emphasis", "egress duy nhất", 676, 566))
    s.append(arrow([(772, 515), (1250, 240)], "default", "egress Internet · APIKEY", 1010, 372))
    s.append(arrow([(746, 552), (746, 650)], "default", None))
    s.append(ttext(760, 606, "API key", 9.8, 600, SLATE, halo=True))
    s.append(arrow([(772, 526), (1040, 660)], "security-ish" if False else "default", "route CIDRs", 880, 606))
    s.append(arrow([(1092, 654), (1180, 662)], "orange", None))
    s.append(arrow([(1092, 678), (1180, 690)], "red", None, dash=True))

    s.append('</svg>')
    return "".join(s)


# ═══════════════════════════ 2. UC1 PUBLIC ═══════════════════════════════════
def build_uc1() -> str:
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="760" viewBox="0 0 1440 760" font-family="Segoe UI,Helvetica,Arial,sans-serif">', defs()]

    s.append(person(100, 230)); s.append(person(135, 224)); s.append(person(170, 230))
    s.append(ttext(135, 272, "Users", 12, 700, anchor="middle"))
    s.append(ttext(135, 288, "browser · webhook · A2A", 9.5, 400, SLATE, "middle"))

    s.append(dashed_box(240, 60, 840, 640, "GreenNode Cloud — vNG Cloud (vServer)"))
    s.append(dashed_box(280, 120, 320, 520, "VPC của KH"))
    s.append(subnet(300, 170, 290, 420, "Public subnet"))
    s.append(tile(380, 290, "compute", "compute"))
    s.append(svc(446, 308, "AgentBase Runtime", "PUBLIC mode"))
    s.append(ttext(446, 340, "public URL · IAM / API-key", 9.5, 400, SLATE))
    s.append(ttext(445, 565, "demo live: travel-buddy · zalo-bot · agent-c-multi", 9.5, 400, SLATE, "middle", italic=True))

    s.append(dashed_box(640, 120, 420, 520, "AgentBase Platform — managed"))
    s.append(tile(760, 190, "ml", "ai"))
    s.append(svc(826, 210, "LLM AIP", "GLM · OpenAI-compat · API key"))
    s.append(tile(760, 300, "db", "db"))
    s.append(svc(826, 320, "Memory + Identity", "SDK · history + facts"))
    s.append(tile(760, 430, "network", "gateway"))
    s.append(svc(826, 450, "MCP Gateway", "policy · outbound auth · egress point"))
    s.append(tile(760, 560, "db", "chart"))
    s.append(svc(826, 580, "stock-mcp", "MCP · Cloud · API key inbound"))

    s.append(dashed_box(1100, 120, 300, 220, "Internet"))
    s.append(tile(1180, 200, "store", "globe"))
    s.append(svc(1246, 220, "MCP · Internet", "Tavily (SaaS) — APIKEY"))

    s.append(arrow([(160, 220), (380, 310)], "emphasis", "HTTPS · public URL", 262, 260))
    s.append(arrow([(600, 296), (760, 224)], "default", "chat completions · API key", 648, 248))
    s.append(arrow([(600, 318), (760, 326)], "default", "SDK · history + facts", 648, 352))
    s.append(arrow([(406, 342), (760, 466)], "emphasis", "tools/call · IAM", 600, 442))
    s.append(arrow([(812, 440), (1180, 240)], "default", "egress Internet · APIKEY", 1000, 316))
    s.append(arrow([(786, 482), (786, 560)], "default", "API key", 806, 528, anchor="start"))

    s.append('</svg>')
    return "".join(s)


# ═════════════════ 3. UC2 PRIVATE + ON-PREM ══════════════════════════════════
def build_uc2() -> str:
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1520" height="1000" viewBox="0 0 1520 1000" font-family="Segoe UI,Helvetica,Arial,sans-serif">', defs()]

    s.append(dashed_box(240, 60, 860, 900, "GreenNode Cloud — vNG Cloud (vServer)"))
    s.append(dashed_box(280, 120, 350, 800, "VPC của KH — private (không public URL)"))
    s.append(subnet(300, 170, 310, 420, "Private subnet", private=True))
    s.append(tile(350, 250, "db", "chart"))
    s.append(svc(416, 268, "Internal app", "trong VPC KH"))
    s.append(tile(420, 380, "compute", "compute"))
    s.append(svc(486, 398, "AgentBase Runtime", "VPC mode · no egress"))
    s.append(ttext(446, 460, "✗ Không egress Internet", 10.5, 700, RED, "middle"))

    s.append(route_card(300, 640, 310, 150, "VPC route table", [
        "local  → trong VPC",
        "platform services → platform network",
        "10.60.0.0/16 → VGW (VPN / DX)",
        "= routeCidrs của runtime / gateway"]))

    s.append(dashed_box(670, 120, 400, 620, "AgentBase Platform — managed"))
    s.append(tile(790, 190, "ml", "ai"))
    s.append(svc(856, 210, "LLM AIP", "GLM · platform network"))
    s.append(tile(790, 300, "db", "db"))
    s.append(svc(856, 320, "Memory + Identity", "SDK · platform network"))
    s.append(tile(790, 440, "network", "gateway"))
    s.append(svc(856, 460, "MCP Gateway", "policy · egress duy nhất"))

    # no internet
    s.append(ttext(1150, 165, "Internet", 10, 600, SLATE))
    s.append(crossed(1150, 180, 1340, 180, 1245, 180))
    s.append(ttext(1245, 214, "No Internet egress", 10.5, 700, RED, "middle"))

    s.append(navy_panel(1130, 560, 350, 280, "Corporate Data Center", "On-Premise KH — mạng riêng"))
    s.append(tile(1190, 650, "dark", "db_white"))
    s.append(svc(1256, 670, "MCP On-Premise", "ERP · DB · legacy", "#FFFFFF", "#D5DBDB"))
    s.append(ttext(1146, 812, "chỉ nhận traffic từ VPC · không expose Internet", 9.5, 400, "#D5DBDB", italic=True))

    s.append(tile(1000, 600, "network", "vpn"))
    s.append(ttext(1026, 676, "Direct Connect · Site-to-Site VPN", 9.5, 600, SLATE, "middle", halo=True))

    s.append(arrow([(402, 288), (420, 380)], "emphasis", "nội bộ VPC", 352, 344))
    s.append(arrow([(600, 396), (790, 224)], "default", "platform network", 664, 300))
    s.append(arrow([(600, 412), (790, 326)], "default", "platform network", 676, 400))
    s.append(arrow([(456, 432), (790, 466)], "emphasis", "tools/call · IAM — egress duy nhất", 612, 486))
    s.append(arrow([(842, 466), (1000, 620)], "default", "route CIDRs", 922, 544))
    s.append(arrow([(1052, 614), (1130, 636)], "orange", None))
    s.append(arrow([(1052, 638), (1130, 662)], "red", None, dash=True))

    s.append('</svg>')
    return "".join(s)


JOBS = [
    ("agentbase-network-map", "AgentBase Runtime — Network Map",
     "1 block AgentBase Runtime · đặt ở public subnet hoặc VPC của KH (vServer) · break ra LLM AIP / Memory + Identity / MCP Gateway · 3 nhóm MCP: Internet · Cloud · On-Premise (VPN/Interconnect)", build_master),
    ("usecase-public-cloud", "Use case 1 — Agent PUBLIC mode",
     "Runtime ở public subnet · LLM + Memory + Gateway · tools: MCP Internet (Tavily) + MCP Cloud (stock-mcp) — demo live", build_uc1),
    ("usecase-private-onprem", "Use case 2 — Agent PRIVATE (VPC mode) · MCP On-Premise",
     "Không dùng Tavily/Internet: runtime private subnet · egress duy nhất là gateway · route CIDRs qua Direct Connect / Site-to-Site VPN sang MCP on-premise", build_uc2),
]

for fname, title, subtitle, fn in JOBS:
    svg = fn()
    w = int(svg.split('width="')[1].split('"')[0])
    (DOC / f"{fname}.html").write_text(shell(title, subtitle, svg, w, 0, LEGEND, fname), encoding="utf-8")
    print("✓", f"{fname}.html")
