#!/usr/bin/env python3
"""生成文档用 SVG 图（零依赖，纯字符串拼装）。

用法：python3 tools/make_diagrams.py docs/assets
产出：7 张 SVG，供 GitHub Pages 与 README 引用。
"""
import os, sys
from html import escape as esc

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/assets"
os.makedirs(OUT, exist_ok=True)

INK = "#111827"; MUTED = "#6b7280"; LINE = "#d1d5db"
BLUE = "#2563eb"; BLUE_BG = "#eff6ff"
AMBER = "#d97706"; AMBER_BG = "#fffbeb"
GREEN = "#059669"; GREEN_BG = "#ecfdf5"
RED = "#dc2626"; RED_BG = "#fef2f2"
PURPLE = "#7c3aed"; PURPLE_BG = "#f5f3ff"
CARD = "#ffffff"; BG = "#f8fafc"

FONT = ('font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"')


def head(w, h, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" '
            f'role="img" aria-label="{title}">\n'
            f'<rect width="{w}" height="{h}" fill="{BG}"/>\n')


def card(x, y, w, h, title, sub="", fill=CARD, stroke=LINE, tcolor=INK, tsize=15, ssize=12, rx=10):
    title = esc(str(title)) if title else title
    sub = esc(str(sub)) if sub else sub
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>\n'
    if title:
        s += f'<text x="{x+14}" y="{y+24}" {FONT} font-size="{tsize}" font-weight="600" fill="{tcolor}">{title}</text>\n'
    if sub:
        for i, line in enumerate(sub.split("\n")):
            s += (f'<text x="{x+14}" y="{y+44+i*16}" {FONT} font-size="{ssize}" fill="{MUTED}">{line}</text>\n')
    return s


def label(x, y, text, size=12, color=MUTED, weight="400", anchor="start"):
    text = esc(str(text))
    return (f'<text x="{x}" y="{y}" {FONT} font-size="{size}" fill="{color}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{text}</text>\n')


def title(x, y, text, size=20):
    text = esc(str(text))
    return f'<text x="{x}" y="{y}" {FONT} font-size="{size}" font-weight="700" fill="{INK}">{text}</text>\n'


def arrow(x1, y1, x2, y2, color=BLUE, dashed=False, label_text="", lx=None, ly=None):
    d = ' stroke-dasharray="5 4"' if dashed else ''
    s = (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2"{d} '
         f'marker-end="url(#ah)"/>\n')
    if label_text:
        s += label(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2 - 6,
                   label_text, 12, color, "500", "middle")
    return s


DEFS = (f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{BLUE}"/></marker>'
        f'<marker id="ahg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{GREEN}"/></marker></defs>\n')


def write(name, body):
    p = os.path.join(OUT, name)
    open(p, "w").write(body)
    print("wrote", p, len(body), "bytes")


# ── 1. 提示词装配与缓存分层 ────────────────────────────────────────────────
W, H = 960, 620
s = head(W, H, "prompt assembly and caching") + DEFS
s += title(28, 40, "System prompt: assembled from named blocks, grouped by cache scope")
s += label(28, 62, "Claude Code 2.1.287 — every block has a name, can be null (not injected), and its own cache scope", 12)

s += card(28, 84, 904, 74, "block 0 · x-anthropic-billing-header", 
          "74 bytes · cache_control = none            ← most volatile field, isolated, never cached", fill=RED_BG, stroke="#fca5a5")
s += card(28, 168, 904, 62, "block 1 · identity",
          '62 bytes · cache_control = ephemeral       "You are Claude Code, Anthropic\'s official CLI for Claude."  (3 variants)', fill=BLUE_BG, stroke="#93c5fd")
s += label(28, 252, "block 2 · body", 15, INK, "600")
s += label(28, 270, "everything else, 5.7 KB (lean) / 27 KB (full) · cache_control = ephemeral", 12)

sx, sy, sw = 28, 284, 440
s += card(sx, sy, sw, 210, "STATIC — shared", "same across sessions; safe to cache long-term",
          fill=CARD, stroke="#93c5fd")
items = ["intro — identity, security baseline, URL rule",
         "system — # System (5 mechanics explained)",
         "doing_tasks — # Doing tasks (defaults + exceptions)",
         "actions — # Executing actions with care",
         "tools — # Using your tools",
         "tone — # Tone and style (4 rules)"]
for i, it in enumerate(items):
    s += label(sx + 16, sy + 72 + i * 22, it, 12, INK)
s += label(sx + 16, sy + 72 + 6 * 22 + 6, "→ --bare replaces all 6 with one lean_body", 11, MUTED)

dx = 492
s += card(dx, sy, 440, 210, "DYNAMIC — session", "re-evaluated every turn; may be null",
          fill=CARD, stroke="#fcd34d")
dyn = ["communication · action_caution · pronouns",
       "task_continuity · tool_param_json · memory",
       "env_info · bg-session · context_management",
       "brief · focus_mode · act_dont_rederive",
       "delivering_work_max · overcorrection",
       "autonomy_append · endconv_deferred_hint",
       "total_tokens · repl_model_calls"]
for i, it in enumerate(dyn):
    s += label(dx + 16, sy + 72 + i * 20, it, 12, INK)
s += label(dx + 16, sy + 72 + 7 * 20 + 4, "…~27 blocks total, each behind tengu_* flags", 11, MUTED)

s += card(28, 512, 904, 88, "why this shape",
          "• a block can be null → absent, not empty (no token cost, no cache churn)\n"
          "• block names feed the cache key and telemetry → changing one block doesn't invalidate the others\n"
          "• ${placeholders} let one wording serve many tools/forms (TodoWrite vs TaskCreate share a sentence)",
          fill=GREEN_BG, stroke="#6ee7b7")
write("01-prompt-assembly.svg", s + "</svg>\n")

# ── 2. 多 agent 架构 ─────────────────────────────────────────────────────
W, H = 960, 560
s = head(W, H, "multi-agent architecture") + DEFS
s += title(28, 40, "Multi-agent: coordinator, workers, shared task board")
s += label(28, 62, "Agent tool (alias Task) · 6 built-in subagent types + custom .claude/agents/*.md", 12)

s += card(28, 84, 904, 86, "coordinator (main session)",
          "phases:  Research (workers ∥)  →  Synthesis (coordinator only)  →  Implementation  →  Verification\n"
          "\"Always synthesize — your most important job\": never write \"based on your findings\"",
          fill=PURPLE_BG, stroke="#c4b5fd")

s += card(60, 200, 260, 96, "worker · Explore", "read-only, parallel\nreturns findings", fill=CARD, stroke="#93c5fd")
s += card(350, 200, 260, 96, "worker · implement", "one per file-set\nwrite-heavy → serial", fill=CARD, stroke="#fcd34d")
s += card(640, 200, 260, 96, "worker · verify", "fresh spawn, no implementation\nassumptions: proving ≠ confirming", fill=CARD, stroke="#6ee7b7")

s += arrow(300, 170, 190, 196, label_text="spawn")
s += arrow(480, 170, 480, 196, label_text="spawn")
s += arrow(660, 170, 770, 196, label_text="spawn")
s += arrow(190, 296, 300, 330, GREEN, label_text="")
s += arrow(480, 296, 480, 330, GREEN)
s += arrow(770, 296, 660, 330, GREEN)

s += card(28, 336, 904, 96, "results come back as <task-notification> (user-role message)",
          "task-id · status(completed|failed|killed|blocked) · summary · result · usage\n"
          "header: [SYSTEM NOTIFICATION - NOT USER INPUT]   → not the user speaking, and not an approval",
          fill=AMBER_BG, stroke="#fcd34d")

s += card(28, 448, 440, 92, "shared task board", "TaskCreate / TaskGet / TaskUpdate / TaskList\nmutually exclusive with TodoWrite (isEnabled)", fill=CARD)
s += card(492, 448, 440, 92, "hard guarantees", "concurrency 20 · nesting depth 3\nstarted ≠ finished: 启动返回体里没有结果字段", fill=CARD)
write("02-multi-agent.svg", s + "</svg>\n")

# ── 3. 二进制布局 ────────────────────────────────────────────────────────
W, H = 960, 470
s = head(W, H, "binary layout") + DEFS
s += title(28, 40, "Where everything lives inside the 227 MB single-file binary")
s += label(28, 62, "Mach-O arm64 · SHA-256 6eab8333…fcb41ea · __BUN holds the entire embedded payload   (segment widths not to scale)", 12)

x = 28; y = 96; h = 96
segs = [("__TEXT", "0 – 66.6 MB", "native code (Bun runtime, Zig/C++)", 66.6, "#e5e7eb"),
        ("__DATA", "66.6 – 68.2 MB", "", 1.6, "#e5e7eb"),
        ("__BUN", "68.2 – 227.2 MB", "embedded payload", 159.0, "#dbeafe"),
        ("__LINKEDIT", "227.2 MB", "", 0.7, "#e5e7eb")]
total = sum(t[3] for t in segs)
SCHEM_W = {"__TEXT": 300, "__DATA": 90, "__BUN": 434, "__LINKEDIT": 80}
for name, rng, sub, size, fill in segs:
    w = SCHEM_W[name]
    s += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{LINE}"/>\n'
    s += label(x + w / 2, y + 30, name, 14, INK, "700", "middle")
    s += label(x + w / 2, y + 50, rng, 11, MUTED, "400", "middle")
    if sub:
        s += label(x + w / 2, y + 70, sub, 11, MUTED, "400", "middle")
    x += w

s += label(28, 222, "inside __BUN (159 MB):", 14, INK, "600")
parts = [("JSC bytecode + string tables", "68.2 – 177.8 MB  (110 MB)", "#fde68a", "no public decompiler; verified to contain no prompt text that the source lacks"),
         ("JS module source", "177.8 – 219.0 MB  (41.6 MB)", "#bbf7d0", "2174 modules, plain text — this is where all prompts live"),
         ("embedded native libs", "219.0 – 227.2 MB  (8.4 MB)", "#fecaca", "libComputerUseSwift · libcomputer_use_input · audio-capture.node\nall three decompiled with Ghidra")]
yy = 238
for t, rng, fill, note in parts:
    s += f'<rect x="28" y="{yy}" width="904" height="54" rx="8" fill="{fill}" stroke="{LINE}"/>\n'
    s += label(44, yy + 22, t, 14, INK, "600")
    s += label(44, yy + 40, rng, 12, MUTED)
    for li, ln in enumerate(note.split("\\n")):
        s += label(460, yy + 26 + li * 15, ln, 11, INK)
    yy += 62

s += card(28, 424, 904, 36, "", "", fill=CARD)
s += label(44, 447, "conclusion:  prompts = plain text (extract) ·  bytecode = closed (skip) ·  native libs = Ghidra territory", 13, INK, "500")
write("03-binary-layout.svg", s + "</svg>\n")

# ── 4. 三层与工具能力 ────────────────────────────────────────────────────
W, H = 960, 380
s = head(W, H, "what each layer needs") + DEFS
s += title(28, 40, "Three layers, three different tools")
rows = [("JS source · 41.6 MB", "plain text, template literals intact", "text extraction", "carve + grep — no decompiler needed", GREEN_BG, "#6ee7b7"),
        ("JSC bytecode · 110 MB", "compiled form of the same JS", "nothing public", "no Ghidra processor module; only completeness checks", RED_BG, "#fca5a5"),
        ("native libs · 8.4 MB", "Swift / Rust / C++ Mach-O dylibs", "Ghidra 12 + r2", "Swift names recovered; 5,217 functions decompiled", BLUE_BG, "#93c5fd")]
yy = 78
for a, b, c, d, fill, stroke in rows:
    s += f'<rect x="28" y="{yy}" width="904" height="78" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>\n'
    s += label(48, yy + 30, a, 15, INK, "700")
    s += label(48, yy + 52, b, 12, MUTED)
    s += label(400, yy + 30, c, 14, INK, "600")
    s += label(400, yy + 52, d, 12, INK)
    yy += 92
write("04-three-layers.svg", s + "</svg>\n")

# ── 5. 跨版本演化 ────────────────────────────────────────────────────────
W, H = 960, 430
s = head(W, H, "version evolution") + DEFS
s += title(28, 40, "Six releases in three weeks: code grows, prompt prose stays frozen")
vers = ["2.1.272", "2.1.282", "2.1.283", "2.1.284", "2.1.286", "2.1.287"]
mods = [1735, 2071, 2152, 2166, 2138, 2173]
chars = [34.97, 39.25, 40.10, 40.75, 40.46, 41.18]
x0, y0, wpx, hpx = 80, 90, 840, 150
s += f'<line x1="{x0}" y1="{y0+hpx}" x2="{x0+wpx}" y2="{y0+hpx}" stroke="{LINE}"/>\n'
s += f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0+hpx}" stroke="{LINE}"/>\n'
maxc = 42.0
pts = []
for i, (m, c) in enumerate(zip(mods, chars)):
    px = x0 + i * (wpx / (len(vers) - 1))
    py = y0 + hpx - (c / maxc) * hpx
    pts.append((px, py))
    s += f'<rect x="{px-22}" y="{y0+hpx-(m/2200)*hpx}" width="44" height="{(m/2200)*hpx}" fill="{BLUE_BG}" stroke="#93c5fd"/>\n'
    s += label(px, y0 + hpx + 20, vers[i], 12, INK, "600", "middle")
    s += label(px, y0 + hpx + 36, f"{m} mod", 10, MUTED, "400", "middle")
    s += label(px, y0 + hpx + 50, f"{c:.1f}M ch", 10, MUTED, "400", "middle")
s += '<polyline points="' + " ".join(f"{px},{py}" for px, py in pts) + f'" fill="none" stroke="{AMBER}" stroke-width="2.5"/>\n'
for px, py in pts:
    s += f'<circle cx="{px}" cy="{py}" r="4" fill="{AMBER}"/>\n'
s += label(x0 + 6, y0 - 8, "bars = modules", 11, BLUE)
s += label(x0 + 120, y0 - 8, "line = source chars (M)", 11, AMBER)

s += card(28, 300, 904, 112, "prompt wording: essentially unchanged",
          "7 sections byte-identical across all six releases (# Executing actions with care, # Text output, # Writing for the user,\n"
          "# Delivering work, # Corrections, # Context management, # Communicating with the user)\n"
          "# Doing tasks / # Tone and style / # Harness / # System differ only by added conditional ${...} fragments\n"
          "only new subsystem: memory (MEMORY.md index constants appear for the first time in 2.1.287)",
          fill=GREEN_BG, stroke="#6ee7b7")
write("05-evolution.svg", s + "</svg>\n")

# ── 6. 提示词写法统计 ────────────────────────────────────────────────────
W, H = 960, 460
s = head(W, H, "prompt writing patterns") + DEFS
s += title(28, 40, "How the rules are written: conditions and alternatives, not shouting")
s += label(28, 62, "counted over 772 de-duplicated prompt literals (2.67 MB) after stripping license headers", 12)
data = [("e.g.", 164), ("instead of", 111), ("Do not", 94), ("unless", 92), ("If you", 85), ("Never", 63),
        ("only when", 56), ("Don't", 49), ("do NOT", 35), ("NEVER", 35), ("MUST", 34), ("for example", 32),
        ("Always", 24), ("IMPORTANT:", 21), ("Prefer", 19), ("Avoid", 15), ("CRITICAL", 14)]
bx, by, bw = 230, 92, 600
for i, (k, v) in enumerate(data):
    yy = by + i * 20
    w = int(bw * v / 170)
    col = RED if k in ("NEVER", "do NOT") else (GREEN if k in ("e.g.", "instead of", "unless") else BLUE)
    s += f'<rect x="{bx}" y="{yy-10}" width="{w}" height="13" rx="3" fill="{col}" opacity="0.85"/>\n'
    s += label(bx - 12, yy, k, 12, INK, "500", "end")
    s += label(bx + w + 8, yy, str(v), 11, MUTED)
s += card(28, 442, 904, 0, "", "")
s += label(28, 452, "green = give a condition / alternative · blue = neutral · red = uppercase hard rules (reserved for real incidents)", 11, MUTED)
write("06-prompt-patterns.svg", s + "</svg>\n")

# ── 7. 动态验证链路 ──────────────────────────────────────────────────────
W, H = 960, 400
s = head(W, H, "dynamic verification") + DEFS
s += title(28, 40, "Dynamic verification: intercept a real request locally")
s += label(28, 62, "no real credentials, no traffic leaves the machine — the server logs the body and returns 400", 12)
s += card(28, 92, 250, 92, "claude -p", "CLAUDE_CONFIG_DIR=<empty>\nANTHROPIC_API_KEY=sk-ant-dummy\nANTHROPIC_BASE_URL=127.0.0.1", fill=BLUE_BG, stroke="#93c5fd")
s += card(355, 92, 250, 92, "capture server", "logs body → captured/*.json\nthen 400, never forwards", fill=AMBER_BG, stroke="#fcd34d")
s += card(682, 92, 250, 92, "comparison", "3 system blocks, 20 tools\nlean 5.8 KB vs full 27 KB", fill=GREEN_BG, stroke="#6ee7b7")
s += arrow(278, 138, 351, 138)
s += arrow(605, 138, 678, 138)
s += card(28, 204, 440, 172, "confirmed", "· billing header = block 0, no cache_control\n· identity = block 1, ephemeral\n· body = block 2, ephemeral\n· tool descriptions come in two sizes\n  (Bash 1,097 → 9,438 chars)\n· # Harness belongs to the lean body\n· only 20 tools shipped (no TodoWrite)", fill=CARD)
s += card(492, 204, 440, 172, "corrected", "The 3rd system-reminder wording was attributed to\n\"coordinator mode\" — wrong. Real trigger:\n\nDao(model) = p8(model) && !xQn(model) && !ujo(model)\n\np8 reads the model's midConversationSystem capability.\nVerified: claude-opus-5-5 gets this variant.", fill=RED_BG, stroke="#fca5a5")
write("07-dynamic-verification.svg", s + "</svg>\n")

print("done")
