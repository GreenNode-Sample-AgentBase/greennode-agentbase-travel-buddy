#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS-style architecture diagrams for GreenNode AgentBase — generator (v2, orthogonal).

Mọi mũi tên đi theo lưới vuông góc (thẳng hoặc 1 góc rẽ) — không đường chéo.
  1. agentbase-network-map.html   — master map
  2. usecase-public-cloud.html    — UC1: agent PUBLIC mode
  3. usecase-private-onprem.html  — UC2: agent VPC mode + MCP on-premise
"""
import html as H
import pathlib

DOC = pathlib.Path(__file__).resolve().parent

INK = "#16191F"
SLATE = "#545B64"
BORDER = "#879596"
SUB_BORDER = "#B6C2CF"
PANEL = "#232F3E"
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


def _p(d, w=2.4, fill="none", color="#FFFFFF"):
    return f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


GLYPHS = {
    "compute": lambda x, y: _p(f"M{x+14} {y+15}h24v22h-24z") + _p(f"M{x+22} {y+15}v22", 2) + _p(f"M{x+30} {y+15}v22", 2),
    "db": lambda x, y: _p(f"M{x+15} {y+17}a11 4.5 0 0 1 22 0v17a11 4.5 0 0 1 -22 0z")
        + _p(f"M{x+15} {y+17}a11 4.5 0 0 0 22 0") + _p(f"M{x+15} {y+26}a11 4.5 0 0 0 22 0", 1.8),
    "gateway": lambda x, y: _p(f"M{x+12} {y+26}h26", 2.6) + f'<path d="M{x+40} {y+26}l-7-4.5v9z" fill="#FFFFFF"/>'
        + f'<rect x="{x+20}" y="{y+16}" width="3.6" height="20" fill="#FFFFFF"/><rect x="{x+28}" y="{y+16}" width="3.6" height="20" fill="#FFFFFF"/>',
    "ai": lambda x, y: _p(f"M{x+17} {y+18}L{x+35} {y+18}M{x+17} {y+18}L{x+26} {y+33}M{x+35} {y+18}L{x+26} {y+33}", 2)
        + f'<circle cx="{x+17}" cy="{y+18}" r="3.4" fill="#FFFFFF"/><circle cx="{x+35}" cy="{y+18}" r="3.4" fill="#FFFFFF"/><circle cx="{x+26}" cy="{y+33}" r="3.4" fill="#FFFFFF"/>',
    "globe": lambda x, y: _p(f"M{x+26} {y+14}a12 12 0 1 0 0.01 0") + _p(f"M{x+14} {y+26}h24") + _p(f"M{x+26} {y+14}a5.5 12 0 0 0 0 24a5.5 12 0 0 0 0 -24", 1.8),
    "chart": lambda x, y: _p(f"M{x+13} {y+36}L{x+20} {y+27}L{x+26} {y+31}L{x+39} {y+15}", 2.6)
        + f'<circle cx="{x+39}" cy="{y+15}" r="2.4" fill="#FFFFFF"/>',
    "vpn": lambda x, y: _p(f"M{x+12} {y+19}h24", 2.4) + f'<path d="M{x+40} {y+19}l-6-4v8z" fill="#FFFFFF"/>'
        + _p(f"M{x+40} {y+31}h-24", 2.4) + f'<path d="M{x+12} {y+31}l6-4v8z" fill="#FFFFFF"/>',
    "db_white": lambda x, y: GLYPHS["db"](x, y),
}


def tile(x, y, grad, glyph, s=52):
    gid = GRADS[grad][0]
    return f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="9" fill="url(#{gid})"/>' + GLYPHS[glyph](x, y)


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
    out = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#FBFCFD" stroke="{SUB_BORDER}" stroke-width="1.3"/>')
    out += tab(x + 12, y + 12, title)
    if private:
        out += LOCK(x + 12 + int(len(title) * 6.6) + 30, y + 24)
    return out


def LOCK(cx, cy):
    return (f'<rect x="{cx-7}" y="{cy-1}" width="14" height="11" rx="2" fill="{SLATE}"/>'
            + _p(f"M{cx-4.5} {cy-1}v-2.5a4.5 4.5 0 0 1 9 0v2.5", 2.2, color=SLATE))


def navy_panel(x, y, w, h, title, sub):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{PANEL}"/>'
            + ttext(x + 16, y + 28, title, 12.5, 700, "#FFFFFF")
            + ttext(x + 16, y + 46, sub, 10, 400, "#D5DBDB"))


def route_card(x, y, w, h, title, lines):
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#F7F8F9" stroke="{SUB_BORDER}" stroke-width="1.2"/>'
    out += ttext(x + 14, y + 24, title, 11, 700)
    yy = y + 46
    for ln in lines:
        out += ttext(x + 14, yy, ln, 9.8, 400, SLATE)
        yy += 19
    return out


def arrow(pts, variant="default", label=None, lx=None, ly=None, anchor="middle", dash=False):
    """pts = orthogonal waypoints — line vuông góc, không chéo."""
    style = {"default": (SLATE, 1.7, "mk"), "emphasis": (INK, 2.5, "mkd"),
             "orange": (ORANGE, 3.6, "mko"), "red": (RED, 2.2, "mkr")}[variant]
    color, width, marker = style
    dashattr = ' stroke-dasharray="7 5"' if dash else ''
    p = " ".join(f"{a},{b}" for a, b in pts)
    out = (f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{width}"{dashattr} '
           f'stroke-linejoin="round" marker-end="url(#{marker})"/>')
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


def shell(title, subtitle, svg, w, legend, fname):
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

# ── Lưới chung ───────────────────────────────────────────────────────────────
# Users cy=279 · VPC x 290..640 · Platform x 700..1120 · Right col x 1180..1500
# Hàng tile: LLM cy 273 · Memory cy 288+? — dùng ROW_* tuyệt đối
ROW_LLM, ROW_MEM, ROW_GW, ROW_STOCK = 431, 519, 607, 707
# tile y = ROW - 26


def users_group(cx=135, cy=431):
    return (person(cx - 35, cy) + person(cx, cy - 6) + person(cx + 35, cy)
            + ttext(cx, cy + 40, "Users", 12, 700, anchor="middle")
            + ttext(cx, cy + 56, "browser · webhook · A2A client", 9.5, 400, SLATE, "middle"))


def platform_column(s, llm_sub="GLM · OpenAI-compat · API key", mem_sub="SDK · history + facts · secret",
                    gw_sub="policy · outbound auth", with_stock=True):
    s.append(tile(740, ROW_LLM - 26, "ml", "ai"));          s.append(svc(806, ROW_LLM - 6, "LLM AIP", llm_sub))
    s.append(tile(740, ROW_MEM - 26, "db", "db"));          s.append(svc(806, ROW_MEM - 6, "Memory + Identity", mem_sub))
    s.append(tile(740, ROW_GW - 26, "network", "gateway")); s.append(svc(806, ROW_GW - 6, "MCP Gateway", gw_sub))
    if with_stock:
        s.append(tile(740, ROW_STOCK - 26, "db", "chart")); s.append(svc(806, ROW_STOCK - 6, "stock-mcp", "MCP · Cloud · API key inbound"))


# ═══════════════════════════ 1. MASTER MAP ═══════════════════════════════════
def build_master() -> str:
    W, HGT = 1560, 990
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{HGT}" viewBox="0 0 {W} {HGT}" font-family="Segoe UI,Helvetica,Arial,sans-serif">', defs()]

    s.append(users_group())
    s.append(dashed_box(250, 240, 870, 700, "GreenNode Cloud — vNG Cloud (vServer)"))
    s.append(dashed_box(290, 305, 350, 610, "VPC của KH"))
    # public subnet + runtime (tile cy = ROW_LLM → thẳng hàng LLM)
    s.append(subnet(310, 360, 310, 170, "Public subnet"))
    s.append(tile(350, 405, "compute", "compute"))
    s.append(svc(416, 420, "AgentBase Runtime", "PUBLIC mode · public URL"))
    # private subnet + runtime
    s.append(subnet(310, 560, 310, 160, "Private subnet", private=True))
    s.append(tile(350, 605, "compute", "compute"))
    s.append(svc(416, 620, "AgentBase Runtime", "VPC mode · no egress"))
    s.append(ttext(416, 652, "caller: app nội bộ VPC", 9, 400, SLATE, italic=True))
    # route table
    s.append(route_card(310, 750, 310, 140, "VPC route table", [
        "local  → trong VPC",
        "0.0.0.0/0  → platform edge (public)",
        "10.60.0.0/16  → VGW (VPN / DX)",
        "= routeCidrs của runtime / gateway"]))

    s.append(dashed_box(700, 305, 420, 475, "AgentBase Platform — managed"))
    platform_column(s)

    # Internet (cùng hàng LLM)
    s.append(dashed_box(1180, 305, 320, 155, "Internet"))
    s.append(tile(1240, 405, "store", "globe"))
    s.append(svc(1306, 420, "MCP · Internet", "Tavily (SaaS) — APIKEY"))

    # VPN tile (cùng hàng Gateway) + on-prem panel
    s.append(tile(1180, 581, "network", "vpn"))
    s.append(navy_panel(1180, 700, 320, 240, "Corporate Data Center", "On-Premise KH — mạng riêng"))
    s.append(tile(1250, 765, "dark", "db_white"))
    s.append(svc(1316, 785, "MCP On-Premise", "ERP · DB · legacy", "#FFFFFF", "#D5DBDB"))
    s.append(ttext(1196, 918, "không expose Internet · CIDR riêng", 9.5, 400, "#D5DBDB", italic=True))

    # ── arrows (orthogonal, cùng lưới hàng) ──
    s.append(arrow([(205, ROW_LLM), (350, ROW_LLM)], "emphasis", "HTTPS · public URL", 262, 419))
    s.append(arrow([(575, 425), (740, 425)], "default", "chat completions · API key", 655, 413))
    s.append(arrow([(575, 437), (676, 437), (676, ROW_MEM), (740, ROW_MEM)], "default", "SDK · history + facts", 706, 507))
    s.append(arrow([(575, 449), (694, 449), (694, ROW_GW), (740, ROW_GW)], "emphasis", "tools/call · IAM", 706, 595))
    # runtime VPC → gateway (thẳng hàng ngang, vào mép trái dưới)
    s.append(arrow([(560, 631), (740, 631)], "emphasis", "egress duy nhất", 648, 649))
    # gateway → stock (dọc)
    s.append(arrow([(766, ROW_GW + 26), (766, ROW_STOCK - 26)], "default"))
    s.append(ttext(780, 661, "API key", 9.8, 600, SLATE, halo=True))
    # gateway → tavily (lên 1 cấp qua hành lang x=1010)
    s.append(arrow([(950, 601), (1010, 601), (1010, ROW_LLM), (1240, ROW_LLM)], "default", "egress Internet · APIKEY", 1108, 419))
    # gateway → VPN (ngang thẳng)
    s.append(arrow([(950, 613), (1180, 613)], "default", "route CIDRs", 1060, 601))
    # VPN → on-prem: 2 line song song
    s.append(arrow([(1194, 633), (1194, 700)], "orange"))
    s.append(arrow([(1220, 633), (1220, 700)], "red", dash=True))
    s.append(ttext(1234, 658, "Direct Connect / Interconnect", 9.5, 600, SLATE))
    s.append(ttext(1234, 676, "Site-to-Site VPN", 9.5, 600, SLATE))

    s.append('</svg>')
    return "".join(s)

def build_uc1() -> str:
    W, HGT = 1560, 820
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{HGT}" viewBox="0 0 {W} {HGT}" font-family="Segoe UI,Helvetica,Arial,sans-serif">', defs()]

    s.append(users_group())
    s.append(dashed_box(250, 240, 870, 535, "GreenNode Cloud — vNG Cloud (vServer)"))
    s.append(dashed_box(290, 305, 350, 470, "VPC của KH"))
    s.append(subnet(310, 360, 310, 300, "Public subnet"))
    s.append(tile(350, 405, "compute", "compute"))
    s.append(svc(416, 420, "AgentBase Runtime", "PUBLIC mode"))
    s.append(ttext(416, 452, "public URL · IAM / API-key", 9.5, 400, SLATE))
    s.append(ttext(465, 630, "demo live: travel-buddy · zalo-bot · agent-c-multi", 9.5, 400, SLATE, "middle", italic=True))

    s.append(dashed_box(700, 305, 420, 475, "AgentBase Platform — managed"))
    platform_column(s)

    s.append(dashed_box(1180, 305, 320, 155, "Internet"))
    s.append(tile(1240, 405, "store", "globe"))
    s.append(svc(1306, 420, "MCP · Internet", "Tavily (SaaS) — APIKEY"))

    s.append(arrow([(205, ROW_LLM), (350, ROW_LLM)], "emphasis", "HTTPS · public URL", 262, 419))
    s.append(arrow([(575, 425), (740, 425)], "default", "chat completions · API key", 655, 413))
    s.append(arrow([(575, 437), (676, 437), (676, ROW_MEM), (740, ROW_MEM)], "default", "SDK · history + facts", 706, 507))
    s.append(arrow([(575, 449), (694, 449), (694, ROW_GW), (740, ROW_GW)], "emphasis", "tools/call · IAM", 706, 595))
    s.append(arrow([(766, ROW_GW + 26), (766, ROW_STOCK - 26)], "default"))
    s.append(ttext(780, 661, "API key", 9.8, 600, SLATE, halo=True))
    s.append(arrow([(950, 601), (1010, 601), (1010, ROW_LLM), (1240, ROW_LLM)], "default", "egress Internet · APIKEY", 1108, 419))

    s.append('</svg>')
    return "".join(s)

def build_uc2() -> str:
    W, HGT = 1560, 990
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{HGT}" viewBox="0 0 {W} {HGT}" font-family="Segoe UI,Helvetica,Arial,sans-serif">', defs()]

    s.append(dashed_box(250, 240, 870, 700, "GreenNode Cloud — vNG Cloud (vServer)"))
    s.append(dashed_box(290, 305, 370, 610, "VPC của KH — private (không public URL)"))
    s.append(subnet(310, 360, 330, 420, "Private subnet", private=True))
    s.append(tile(350, 405, "db", "chart"))
    s.append(svc(416, 420, "Internal app", "trong VPC KH"))
    s.append(tile(350, 520, "compute", "compute"))
    s.append(svc(416, 535, "AgentBase Runtime", "VPC mode · no egress"))
    s.append(ttext(475, 745, "✗ Không egress Internet", 10.5, 700, RED, "middle"))

    s.append(route_card(310, 800, 330, 110, "VPC route table", [
        "local  → trong VPC",
        "platform services → platform network",
        "10.60.0.0/16 → VGW (VPN / DX)",
        "= routeCidrs của runtime / gateway"]))

    s.append(dashed_box(700, 305, 420, 475, "AgentBase Platform — managed"))
    platform_column(s, llm_sub="GLM · platform network", mem_sub="SDK · platform network",
                    gw_sub="policy · egress duy nhất", with_stock=False)

    s.append(ttext(1160, 330, "Internet", 10, 600, SLATE))
    s.append(crossed(1160, 345, 1345, 345, 1252, 345))
    s.append(ttext(1252, 379, "No Internet egress", 10.5, 700, RED, "middle"))

    s.append(tile(1180, 581, "network", "vpn"))
    s.append(navy_panel(1180, 700, 320, 240, "Corporate Data Center", "On-Premise KH — mạng riêng"))
    s.append(tile(1250, 765, "dark", "db_white"))
    s.append(svc(1316, 785, "MCP On-Premise", "ERP · DB · legacy", "#FFFFFF", "#D5DBDB"))
    s.append(ttext(1196, 918, "chỉ nhận traffic từ VPC · không expose Internet", 9.5, 400, "#D5DBDB", italic=True))

    # ── arrows (orthogonal) ──
    s.append(arrow([(376, 457), (376, 520)], "emphasis", "nội bộ VPC", 392, 492, anchor="start"))
    s.append(arrow([(560, 540), (660, 540), (660, ROW_LLM), (740, ROW_LLM)], "default", "platform network", 700, 419))
    s.append(arrow([(560, 552), (676, 552), (676, ROW_MEM), (740, ROW_MEM)], "default", "platform network", 706, 507))
    s.append(arrow([(560, 564), (690, 564), (690, ROW_GW - 8), (740, ROW_GW - 8)], "emphasis", "tools/call · IAM — egress duy nhất", 620, 585))
    # gateway → VPN (ngang thẳng)
    s.append(arrow([(950, 613), (1180, 613)], "default", "route CIDRs", 1060, 601))
    s.append(arrow([(1194, 633), (1194, 700)], "orange"))
    s.append(arrow([(1220, 633), (1220, 700)], "red", dash=True))
    s.append(ttext(1234, 658, "Direct Connect / Interconnect", 9.5, 600, SLATE))
    s.append(ttext(1234, 676, "Site-to-Site VPN", 9.5, 600, SLATE))

    s.append('</svg>')
    return "".join(s)

JOBS = [
    ("agentbase-network-map", "AgentBase Runtime — Network Map",
     "1 block AgentBase Runtime · đặt ở public subnet hoặc VPC của KH · break ra LLM AIP / Memory + Identity / MCP Gateway · 3 nhóm MCP: Internet · Cloud · On-Premise (VPN/Interconnect)", build_master),
    ("usecase-public-cloud", "Use case 1 — Agent PUBLIC mode",
     "Runtime ở public subnet · LLM + Memory + Gateway · tools: MCP Internet (Tavily) + MCP Cloud (stock-mcp) — demo live", build_uc1),
    ("usecase-private-onprem", "Use case 2 — Agent PRIVATE (VPC mode) · MCP On-Premise",
     "Không dùng Tavily/Internet: runtime ở private subnet · egress duy nhất là gateway · route CIDRs qua Direct Connect / Site-to-Site VPN sang MCP on-premise", build_uc2),
]

for fname, title, subtitle, fn in JOBS:
    svg = fn()
    w = int(svg.split('width="')[1].split('"')[0])
    (DOC / f"{fname}.html").write_text(shell(title, subtitle, svg, w, LEGEND, fname), encoding="utf-8")
    print("✓", f"{fname}.html")
